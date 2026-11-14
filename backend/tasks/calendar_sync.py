"""
Celery background tasks for Google Calendar synchronization.  Task 1-D-2.

Two workers:
  push_job_to_calendar_task(tenant_id, job_id)
      — Creates or updates a Google Calendar event for a scheduled job.
        Stores the returned event ID back on ``job.external_calendar_event_id``.
        Logs each action (success / error) to ``calendar_sync_log``.

  pull_calendar_blocks_task(tenant_id)
      — Fetches events from the tenant's Google Calendar that were NOT
        created by Pilot for Trades, and inserts them as ``tech_availability`` rows
        (availability_type='unavailable').
        Updates ``tenant_calendar_integration.last_sync_cursor`` to enable
        incremental pulls on the next run.
        Logs each action to ``calendar_sync_log``.

Beat schedule: added to core/celery_app.py.

Token refresh:
  _get_valid_access_token() checks token_expires_at and, if within 5 minutes
  of expiry, calls the Google token endpoint using the stored (encrypted)
  refresh token before returning a fresh plaintext access token.
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta

import httpx
from sqlmodel import Session, select

from app.models.fulfillment import Job
from app.models.scheduling import (
    CalendarSyncLog,
    TechAvailability,
    TenantCalendarIntegration,
)
from core.celery_app import celery_app
from core.config import settings
from core.db import engine as db_engine
from core.db import set_audit_context_sync
from core.encryption import decrypt_token, encrypt_token

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Google Calendar API constants
# ---------------------------------------------------------------------------

_GCAL_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/{cal_id}/events"
_GCAL_EVENT_URL = (
    "https://www.googleapis.com/calendar/v3/calendars/{cal_id}/events/{event_id}"
)
_GCAL_LIST_URL = "https://www.googleapis.com/calendar/v3/calendars/{cal_id}/events"
_TOKEN_REFRESH_BUFFER_SECONDS = 300  # refresh if expiring within 5 minutes


# ---------------------------------------------------------------------------
# Token management helpers
# ---------------------------------------------------------------------------


def _get_integration(db: Session, tenant_id: uuid.UUID) -> TenantCalendarIntegration:
    """Return the active TenantCalendarIntegration or raise ValueError."""
    record = db.exec(
        select(TenantCalendarIntegration).where(
            TenantCalendarIntegration.tenant_id == tenant_id,
            TenantCalendarIntegration.sync_status == "active",
        )
    ).first()
    if not record:
        raise ValueError(
            f"No active Google Calendar integration for tenant {tenant_id}"
        )
    return record


async def _refresh_google_token(refresh_token_plain: str) -> dict:
    """Call Google's token endpoint to obtain a fresh access token.

    Returns the raw JSON response from Google.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.GOOGLE_CALENDAR_TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_CALENDAR_CLIENT_ID,
                "client_secret": settings.GOOGLE_CALENDAR_CLIENT_SECRET,
                "refresh_token": refresh_token_plain,
                "grant_type": "refresh_token",
            },
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        return response.json()


def _get_valid_access_token(
    db: Session,
    integration: TenantCalendarIntegration,
    system_user_id: uuid.UUID,
) -> str:
    """Return a valid plaintext access token for the integration.

    If the stored token expires within ``_TOKEN_REFRESH_BUFFER_SECONDS``, a
    refresh is attempted via Google's token endpoint and the new tokens are
    persisted back to ``tenant_calendar_integration``.

    Args:
        db: Active SQLModel session.
        integration: The ``TenantCalendarIntegration`` row.
        system_user_id: UUID used as ``updated_by`` when refreshing tokens.

    Returns:
        Plaintext access token string.

    Raises:
        ValueError: If decryption fails or refresh is not possible.
    """
    now = datetime.now(UTC)
    needs_refresh = (
        integration.token_expires_at - now
    ).total_seconds() < _TOKEN_REFRESH_BUFFER_SECONDS

    access_token_plain = decrypt_token(integration.access_token_encrypted.decode())

    if needs_refresh and integration.refresh_token_encrypted:
        try:
            refresh_token_plain = decrypt_token(
                integration.refresh_token_encrypted.decode()
            )
            token_data = asyncio.run(_refresh_google_token(refresh_token_plain))
            new_access = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)

            # Persist refreshed token
            set_audit_context_sync(db, system_user_id)
            integration.access_token_encrypted = encrypt_token(new_access).encode()
            integration.token_expires_at = now + timedelta(seconds=expires_in)
            integration.updated_by = system_user_id
            db.add(integration)
            db.commit()
            db.refresh(integration)

            access_token_plain = new_access
            logger.info(
                "Refreshed Google Calendar access token for tenant %s",
                integration.tenant_id,
            )
        except Exception as exc:
            logger.warning(
                "Could not refresh Google Calendar token for tenant %s: %s",
                integration.tenant_id,
                exc,
            )
            # Fall through — use the (possibly stale) existing token

    return access_token_plain


# ---------------------------------------------------------------------------
# Sync log helper
# ---------------------------------------------------------------------------


def _write_sync_log(
    db: Session,
    tenant_id: uuid.UUID,
    direction: str,
    entity_type: str,
    entity_id: uuid.UUID,
    sync_status: str,
    external_event_id: str | None = None,
    error_detail: dict | None = None,
    payload_snapshot: dict | None = None,
    created_by: uuid.UUID | None = None,
) -> None:
    """Insert a single row into ``calendar_sync_log`` (append-only)."""
    log_entry = CalendarSyncLog(
        tenant_id=tenant_id,
        direction=direction,
        entity_type=entity_type,
        entity_id=entity_id,
        external_event_id=external_event_id,
        status=sync_status,
        error_detail=error_detail,
        payload_snapshot=payload_snapshot,
        created_by=created_by,
    )
    db.add(log_entry)
    db.commit()


# ---------------------------------------------------------------------------
# Google Calendar API helpers (async)
# ---------------------------------------------------------------------------


async def _push_event_to_google(
    access_token: str,
    calendar_id: str,
    job: Job,
    existing_event_id: str | None,
) -> dict:
    """Create or update a Google Calendar event for a Job.

    Uses INSERT if ``existing_event_id`` is None, otherwise PATCH.

    Returns the Google Calendar event resource dict.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # Build event body
    event_body = {
        "summary": f"Pilot Job — {job.id}",
        "description": f"Managed by Pilot for Trades. Job ID: {job.id}",
        "start": {
            "dateTime": job.scheduled_start_at.isoformat(),
            "timeZone": "UTC",
        },
        "end": {
            "dateTime": job.scheduled_end_at.isoformat(),
            "timeZone": "UTC",
        },
        "extendedProperties": {
            "private": {
                "pilot_job_id": str(job.id),
                "pilot_tenant_id": str(job.tenant_id),
            }
        },
    }

    async with httpx.AsyncClient() as client:
        if existing_event_id:
            url = _GCAL_EVENT_URL.format(cal_id=calendar_id, event_id=existing_event_id)
            response = await client.patch(url, json=event_body, headers=headers)
        else:
            url = _GCAL_EVENTS_URL.format(cal_id=calendar_id)
            response = await client.post(url, json=event_body, headers=headers)
        response.raise_for_status()
        return response.json()


async def _list_google_calendar_events(
    access_token: str,
    calendar_id: str,
    sync_token: str | None,
) -> dict:
    """Fetch calendar events using an incremental sync token or a 30-day lookback.

    Returns the Google Calendar Events list response dict.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    params: dict = {
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": 250,
    }

    if sync_token:
        params["syncToken"] = sync_token
    else:
        # Bootstrap: fetch the next 30 days
        params["timeMin"] = datetime.now(UTC).isoformat()
        params["timeMax"] = (datetime.now(UTC) + timedelta(days=30)).isoformat()

    url = _GCAL_LIST_URL.format(cal_id=calendar_id)
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()


# ---------------------------------------------------------------------------
# Celery tasks
# ---------------------------------------------------------------------------


@celery_app.task(name="push_job_to_calendar", bind=True, max_retries=3)
def push_job_to_calendar_task(self, tenant_id: str, job_id: str) -> dict:
    """Push a scheduled Pilot for Trades job to Google Calendar.

    Args:
        tenant_id: String UUID of the tenant.
        job_id: String UUID of the Job to push.

    Returns:
        Dict with sync result metadata.

    Behaviour:
        - If ``job.external_calendar_event_id`` is set, the existing Google
          Calendar event is PATCH-updated.
        - Otherwise a new event is created and the returned event ID is stored
          back on the Job row.
        - All outcomes (success / error) are written to ``calendar_sync_log``.
    """
    tenant_uuid = uuid.UUID(tenant_id)
    job_uuid = uuid.UUID(job_id)

    # Use a UUID sentinel for audit context (system task)
    system_user_id = uuid.UUID(settings.TEST_USER_ID)

    with Session(db_engine) as db:
        # --- Fetch integration ---
        try:
            integration = _get_integration(db, tenant_uuid)
        except ValueError as exc:
            logger.error("push_job_to_calendar: %s", exc)
            return {"status": "error", "detail": str(exc)}

        # --- Fetch job ---
        job = db.exec(
            select(Job).where(
                Job.id == job_uuid,
                Job.tenant_id == tenant_uuid,
                Job.is_active == True,
            )
        ).first()

        if not job:
            detail = f"Job {job_id} not found for tenant {tenant_id}"
            _write_sync_log(
                db,
                tenant_uuid,
                "push",
                "job",
                job_uuid,
                "error",
                error_detail={"message": detail},
            )
            return {"status": "error", "detail": detail}

        if not job.scheduled_start_at or not job.scheduled_end_at:
            detail = "Job has no scheduled time — skipping push"
            _write_sync_log(
                db,
                tenant_uuid,
                "push",
                "job",
                job_uuid,
                "error",
                error_detail={"message": detail},
            )
            return {"status": "error", "detail": detail}

        # --- Get valid access token ---
        try:
            access_token = _get_valid_access_token(db, integration, system_user_id)
        except Exception as exc:
            detail = f"Token error: {exc}"
            _write_sync_log(
                db,
                tenant_uuid,
                "push",
                "job",
                job_uuid,
                "error",
                error_detail={"message": detail},
            )
            return {"status": "error", "detail": detail}

        # --- Push to Google Calendar ---
        try:
            event = asyncio.run(
                _push_event_to_google(
                    access_token,
                    integration.external_calendar_id,
                    job,
                    job.external_calendar_event_id,
                )
            )
        except httpx.HTTPStatusError as exc:
            detail = f"Google API error {exc.response.status_code}: {exc.response.text}"
            logger.error("push_job_to_calendar %s: %s", job_id, detail)
            _write_sync_log(
                db,
                tenant_uuid,
                "push",
                "job",
                job_uuid,
                "error",
                error_detail={"message": detail},
            )
            try:
                self.retry(exc=exc, countdown=2**self.request.retries * 60)
            except self.MaxRetriesExceededError:
                pass
            return {"status": "error", "detail": detail}
        except Exception as exc:
            detail = str(exc)
            logger.error("push_job_to_calendar unexpected error %s: %s", job_id, detail)
            _write_sync_log(
                db,
                tenant_uuid,
                "push",
                "job",
                job_uuid,
                "error",
                error_detail={"message": detail},
            )
            return {"status": "error", "detail": detail}

        # --- Store event ID back on Job ---
        event_id = event.get("id")
        if event_id and job.external_calendar_event_id != event_id:
            set_audit_context_sync(db, system_user_id)
            job.external_calendar_event_id = event_id
            job.updated_by = system_user_id
            db.add(job)

        # --- Update last_sync_at on integration ---
        integration.last_sync_at = datetime.now(UTC)
        integration.updated_by = system_user_id
        db.add(integration)

        db.commit()

        # --- Log success ---
        with Session(db_engine) as log_db:
            _write_sync_log(
                log_db,
                tenant_uuid,
                "push",
                "job",
                job_uuid,
                "success",
                external_event_id=event_id,
                payload_snapshot={
                    "event_id": event_id,
                    "summary": event.get("summary"),
                    "start": event.get("start"),
                    "end": event.get("end"),
                },
            )

        logger.info(
            "push_job_to_calendar: tenant=%s job=%s event_id=%s",
            tenant_id,
            job_id,
            event_id,
        )
        return {"status": "success", "job_id": job_id, "event_id": event_id}


@celery_app.task(name="pull_calendar_blocks", bind=True, max_retries=3)
def pull_calendar_blocks_task(self, tenant_id: str) -> dict:
    """Pull external Google Calendar events as unavailable tech blocks.

    Fetches events from the tenant's Google Calendar that were NOT created
    by Pilot for Trades (identified by the absence of the ``pilot_job_id`` private
    extended property) and upserts them into ``tech_availability`` with
    ``availability_type='unavailable'``.

    Uses the Google Calendar incremental sync (``syncToken``) to avoid
    reprocessing events on subsequent runs.

    Args:
        tenant_id: String UUID of the tenant.

    Returns:
        Dict with counts: blocks_created, skipped, errors.
    """
    tenant_uuid = uuid.UUID(tenant_id)
    system_user_id = uuid.UUID(settings.TEST_USER_ID)

    blocks_created = 0
    skipped = 0
    errors = 0

    with Session(db_engine) as db:
        # --- Fetch integration ---
        try:
            integration = _get_integration(db, tenant_uuid)
        except ValueError as exc:
            logger.error("pull_calendar_blocks: %s", exc)
            return {"status": "error", "detail": str(exc)}

        # --- Get valid access token ---
        try:
            access_token = _get_valid_access_token(db, integration, system_user_id)
        except Exception as exc:
            detail = f"Token error: {exc}"
            return {"status": "error", "detail": detail}

        # --- List events from Google Calendar ---
        try:
            cal_response = asyncio.run(
                _list_google_calendar_events(
                    access_token,
                    integration.external_calendar_id,
                    integration.last_sync_cursor,
                )
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 410:
                # Sync token expired — clear cursor and retry fresh
                logger.warning(
                    "pull_calendar_blocks: sync token expired for tenant %s, resetting",
                    tenant_id,
                )
                set_audit_context_sync(db, system_user_id)
                integration.last_sync_cursor = None
                integration.updated_by = system_user_id
                db.add(integration)
                db.commit()
            detail = f"Google API error: {exc}"
            logger.error("pull_calendar_blocks %s: %s", tenant_id, detail)
            try:
                self.retry(exc=exc, countdown=2**self.request.retries * 60)
            except self.MaxRetriesExceededError:
                pass
            return {"status": "error", "detail": detail}
        except Exception as exc:
            return {"status": "error", "detail": str(exc)}

        events = cal_response.get("items", [])
        next_sync_token = cal_response.get("nextSyncToken")

        for event in events:
            # Skip events that Pilot for Trades created (identified by private property)
            private_props = event.get("extendedProperties", {}).get("private", {})
            if "pilot_job_id" in private_props:
                skipped += 1
                continue

            # Skip cancelled events
            if event.get("status") == "cancelled":
                skipped += 1
                continue

            # Parse times
            start_raw = event.get("start", {})
            end_raw = event.get("end", {})
            starts_at_str = start_raw.get("dateTime") or start_raw.get("date")
            ends_at_str = end_raw.get("dateTime") or end_raw.get("date")

            if not starts_at_str or not ends_at_str:
                skipped += 1
                continue

            try:
                starts_at = datetime.fromisoformat(starts_at_str)
                ends_at = datetime.fromisoformat(ends_at_str)
                # Ensure timezone-aware (Google returns UTC 'Z' or offset)
                if starts_at.tzinfo is None:
                    starts_at = starts_at.replace(tzinfo=UTC)
                if ends_at.tzinfo is None:
                    ends_at = ends_at.replace(tzinfo=UTC)
            except (ValueError, TypeError):
                errors += 1
                continue

            google_event_id = event.get("id", "")

            # Upsert: check if a TechAvailability row already exists for this event
            existing_avail = db.exec(
                select(TechAvailability).where(
                    TechAvailability.tenant_id == tenant_uuid,
                    TechAvailability.notes == google_event_id,  # used as external key
                    TechAvailability.availability_type == "unavailable",
                )
            ).first()

            if existing_avail:
                # Update times if event was modified
                set_audit_context_sync(db, system_user_id)
                existing_avail.starts_at = starts_at
                existing_avail.ends_at = ends_at
                existing_avail.updated_by = system_user_id
                db.add(existing_avail)
            else:
                # Insert new unavailable block
                # user_id defaults to the connected_by_user_id (company-level block)
                set_audit_context_sync(db, system_user_id)
                avail = TechAvailability(
                    tenant_id=tenant_uuid,
                    user_id=integration.connected_by_user_id,
                    availability_type="unavailable",
                    starts_at=starts_at,
                    ends_at=ends_at,
                    notes=google_event_id,  # store event ID for dedup
                    is_active=True,
                    created_by=system_user_id,
                    updated_by=system_user_id,
                )
                db.add(avail)
                blocks_created += 1

                # Log each new block
                _write_sync_log(
                    db,
                    tenant_uuid,
                    "pull",
                    "availability",
                    avail.id,
                    "success",
                    external_event_id=google_event_id,
                    payload_snapshot={
                        "event_id": google_event_id,
                        "summary": event.get("summary"),
                        "starts_at": starts_at.isoformat(),
                        "ends_at": ends_at.isoformat(),
                    },
                    created_by=system_user_id,
                )

        # --- Update sync cursor + last_sync_at ---
        set_audit_context_sync(db, system_user_id)
        if next_sync_token:
            integration.last_sync_cursor = next_sync_token
        integration.last_sync_at = datetime.now(UTC)
        integration.updated_by = system_user_id
        db.add(integration)
        db.commit()

    logger.info(
        "pull_calendar_blocks: tenant=%s created=%d skipped=%d errors=%d",
        tenant_id,
        blocks_created,
        skipped,
        errors,
    )
    return {
        "status": "success",
        "tenant_id": tenant_id,
        "blocks_created": blocks_created,
        "skipped": skipped,
        "errors": errors,
    }


@celery_app.task(name="pull_calendar_blocks_all_tenants", bind=True)
def pull_calendar_blocks_all_tenants_task(self) -> dict:
    """Fan-out: trigger pull_calendar_blocks_task for every active tenant.

    Runs every 15 minutes via Celery Beat.  Skips tenants that have no active
    Google Calendar integration.
    """
    with Session(db_engine) as db:
        integrations = db.exec(
            select(TenantCalendarIntegration).where(
                TenantCalendarIntegration.sync_status == "active"
            )
        ).all()

    queued = 0
    for integration in integrations:
        pull_calendar_blocks_task.delay(str(integration.tenant_id))
        queued += 1

    logger.info("pull_calendar_blocks_all_tenants: queued %d tenants", queued)
    return {"status": "success", "tenants_queued": queued}
