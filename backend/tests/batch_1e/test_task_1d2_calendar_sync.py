"""
Task 1-D-2: Calendar Sync Workers — unit tests.

Coverage:
  1. _get_integration raises ValueError when tenant has no active integration
  2. _get_valid_access_token returns plain access token without refresh when not near expiry
  3. _get_valid_access_token refreshes and persists new token when near expiry
  4. _write_sync_log inserts a CalendarSyncLog row
  5. push_job_to_calendar_task — no integration → error result
  6. push_job_to_calendar_task — job not found → error result
  7. push_job_to_calendar_task — job has no scheduled time → error result
  8. push_job_to_calendar_task — success: event created, event_id stored on Job,
     sync log written
  9. pull_calendar_blocks_task — no integration → error result
 10. pull_calendar_blocks_task — success: external event inserted as TechAvailability,
     sync cursor updated, sync log written
 11. pull_calendar_blocks_task — Pilot for Trades-owned events are skipped
 12. pull_calendar_blocks_all_tenants_task — fans out once per active integration

Strategy:
  - Inner helpers (_get_integration, _get_valid_access_token, _write_sync_log)
    accept ``db`` directly → tested with ``db_session`` fixture ✓
  - Celery task functions open ``Session(db_engine)`` internally.  We patch
    ``tasks.calendar_sync.Session`` to return a context manager that yields
    ``db_session``, making task-level data visible.
  - HTTP calls (Google APIs) are always mocked with AsyncMock.
"""

import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlmodel import select

from app.models.fulfillment import Job, JobStatus
from app.models.scheduling import (
    CalendarSyncLog,
    TechAvailability,
    TenantCalendarIntegration,
)
from core.encryption import decrypt_token, encrypt_token
from tasks.calendar_sync import (
    _get_integration,
    _get_valid_access_token,
    _write_sync_log,
    pull_calendar_blocks_all_tenants_task,
    pull_calendar_blocks_task,
    push_job_to_calendar_task,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_integration(
    db,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    sync_status: str = "active",
    expires_in_seconds: int = 7200,
) -> TenantCalendarIntegration:
    """Insert a TenantCalendarIntegration with Fernet-encrypted dummy tokens."""
    now = datetime.now(UTC)
    integration = TenantCalendarIntegration(
        tenant_id=tenant_id,
        provider_code="google",
        external_calendar_id="primary",
        access_token_encrypted=encrypt_token("access_tok_v1").encode(),
        refresh_token_encrypted=encrypt_token("refresh_tok_v1").encode(),
        token_expires_at=now + timedelta(seconds=expires_in_seconds),
        sync_status=sync_status,
        connected_by_user_id=user_id,
        connected_at=now,
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(integration)
    db.commit()
    db.refresh(integration)
    return integration


def _create_job(
    db,
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
    site_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    scheduled: bool = True,
) -> Job:
    """Insert a minimal Job row using real customer/site IDs."""
    js = db.exec(select(JobStatus)).first()
    assert js is not None, "No JobStatus seed row found — conftest setup issue"

    now = datetime.now(UTC)
    job = Job(
        tenant_id=tenant_id,
        customer_id=customer_id,
        site_id=site_id,
        status_id=js.id,
        scheduled_start_at=now + timedelta(hours=1) if scheduled else None,
        scheduled_end_at=now + timedelta(hours=3) if scheduled else None,
        is_active=True,
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def make_session_patcher(db_session):
    """Return a context-manager Session class that yields ``db_session``.

    Usage::
        with patch("tasks.calendar_sync.Session", make_session_patcher(db_session)):
            result = some_task(...)
    """

    @contextmanager
    def _fake_session_cm(_engine):
        yield db_session

    class _FakeSession:
        def __init__(self, _engine):
            self._cm = _fake_session_cm(_engine)

        def __enter__(self):
            return self._cm.__enter__()

        def __exit__(self, *args):
            return self._cm.__exit__(*args)

    return _FakeSession


# ---------------------------------------------------------------------------
# 1. _get_integration — no active record
# ---------------------------------------------------------------------------


def test_get_integration_raises_when_missing(db_session, test_tenant):
    with pytest.raises(ValueError, match="No active Google Calendar integration"):
        _get_integration(db_session, test_tenant.id)


# ---------------------------------------------------------------------------
# 2. _get_valid_access_token — token not near expiry
# ---------------------------------------------------------------------------


def test_get_valid_access_token_returns_plaintext_no_refresh(
    db_session, test_tenant, test_user
):
    integration = _create_integration(
        db_session, test_tenant.id, test_user.id, expires_in_seconds=7200
    )
    token = _get_valid_access_token(db_session, integration, test_user.id)
    assert token == "access_tok_v1"


# ---------------------------------------------------------------------------
# 3. _get_valid_access_token — near expiry, refresh succeeds
# ---------------------------------------------------------------------------


def test_get_valid_access_token_refreshes_when_near_expiry(
    db_session, test_tenant, test_user
):
    integration = _create_integration(
        db_session, test_tenant.id, test_user.id, expires_in_seconds=60
    )

    fake_google_response = {
        "access_token": "new_access_tok",
        "expires_in": 3600,
        "token_type": "Bearer",
    }

    with patch(
        "tasks.calendar_sync._refresh_google_token",
        new_callable=AsyncMock,
        return_value=fake_google_response,
    ):
        token = _get_valid_access_token(db_session, integration, test_user.id)

    assert token == "new_access_tok"
    db_session.refresh(integration)
    assert (
        decrypt_token(integration.access_token_encrypted.decode()) == "new_access_tok"
    )


# ---------------------------------------------------------------------------
# 4. _write_sync_log — inserts a row
# ---------------------------------------------------------------------------


def test_write_sync_log_inserts_row(db_session, test_tenant, test_user):
    entity_id = uuid.uuid4()
    _write_sync_log(
        db_session,
        test_tenant.id,
        "push",
        "job",
        entity_id,
        "success",
        external_event_id="google_event_abc",
        payload_snapshot={"foo": "bar"},
        created_by=test_user.id,
    )

    log = db_session.exec(
        select(CalendarSyncLog).where(
            CalendarSyncLog.entity_id == entity_id,
            CalendarSyncLog.tenant_id == test_tenant.id,
        )
    ).first()

    assert log is not None
    assert log.status == "success"
    assert log.external_event_id == "google_event_abc"
    assert log.direction == "push"
    assert log.entity_type == "job"


# ---------------------------------------------------------------------------
# 5. push_job_to_calendar_task — no integration (fresh DB state)
# ---------------------------------------------------------------------------


def test_push_job_no_integration(db_session, test_tenant):
    with patch("tasks.calendar_sync.Session", make_session_patcher(db_session)):
        result = push_job_to_calendar_task(str(test_tenant.id), str(uuid.uuid4()))
    assert result["status"] == "error"
    assert "No active Google Calendar integration" in result["detail"]


# ---------------------------------------------------------------------------
# 6. push_job_to_calendar_task — job not found
# ---------------------------------------------------------------------------


def test_push_job_not_found(db_session, test_tenant, test_user):
    _create_integration(db_session, test_tenant.id, test_user.id)
    with patch("tasks.calendar_sync.Session", make_session_patcher(db_session)):
        result = push_job_to_calendar_task(str(test_tenant.id), str(uuid.uuid4()))
    assert result["status"] == "error"
    assert "not found" in result["detail"]


# ---------------------------------------------------------------------------
# 7. push_job_to_calendar_task — job has no schedule
# ---------------------------------------------------------------------------


def test_push_job_no_schedule(
    db_session, test_tenant, test_user, test_customer, test_site
):
    _create_integration(db_session, test_tenant.id, test_user.id)
    job = _create_job(
        db_session,
        test_tenant.id,
        test_customer.id,
        test_site.id,
        test_user.id,
        scheduled=False,
    )
    with patch("tasks.calendar_sync.Session", make_session_patcher(db_session)):
        result = push_job_to_calendar_task(str(test_tenant.id), str(job.id))
    assert result["status"] == "error"
    assert "no scheduled time" in result["detail"]


# ---------------------------------------------------------------------------
# 8. push_job_to_calendar_task — success
# ---------------------------------------------------------------------------


def test_push_job_success(db_session, test_tenant, test_user, test_customer, test_site):
    _create_integration(db_session, test_tenant.id, test_user.id)
    job = _create_job(
        db_session,
        test_tenant.id,
        test_customer.id,
        test_site.id,
        test_user.id,
        scheduled=True,
    )

    fake_event = {
        "id": "gcal_event_xyz",
        "summary": f"Pilot for Trades Job — {job.id}",
        "start": {"dateTime": job.scheduled_start_at.isoformat()},
        "end": {"dateTime": job.scheduled_end_at.isoformat()},
    }

    with (
        patch("tasks.calendar_sync.Session", make_session_patcher(db_session)),
        patch(
            "tasks.calendar_sync._push_event_to_google",
            new_callable=AsyncMock,
            return_value=fake_event,
        ),
    ):
        result = push_job_to_calendar_task(str(test_tenant.id), str(job.id))

    assert result["status"] == "success"
    assert result["event_id"] == "gcal_event_xyz"

    db_session.refresh(job)
    assert job.external_calendar_event_id == "gcal_event_xyz"

    log = db_session.exec(
        select(CalendarSyncLog).where(
            CalendarSyncLog.entity_id == job.id,
            CalendarSyncLog.status == "success",
        )
    ).first()
    assert log is not None
    assert log.external_event_id == "gcal_event_xyz"


# ---------------------------------------------------------------------------
# 9. pull_calendar_blocks_task — no integration
# ---------------------------------------------------------------------------


def test_pull_blocks_no_integration(db_session, test_tenant):
    with patch("tasks.calendar_sync.Session", make_session_patcher(db_session)):
        result = pull_calendar_blocks_task(str(test_tenant.id))
    assert result["status"] == "error"
    assert "No active Google Calendar integration" in result["detail"]


# ---------------------------------------------------------------------------
# 10. pull_calendar_blocks_task — success: new block created + cursor updated
# ---------------------------------------------------------------------------


def test_pull_blocks_creates_tech_availability(db_session, test_tenant, test_user):
    integration = _create_integration(db_session, test_tenant.id, test_user.id)

    fake_event_id = "ext_event_001"
    now = datetime.now(UTC)
    fake_cal_response = {
        "items": [
            {
                "id": fake_event_id,
                "status": "confirmed",
                "summary": "External meeting",
                "start": {"dateTime": (now + timedelta(hours=5)).isoformat()},
                "end": {"dateTime": (now + timedelta(hours=6)).isoformat()},
                "extendedProperties": {"private": {}},
            }
        ],
        "nextSyncToken": "tok_abc123",
    }

    with (
        patch("tasks.calendar_sync.Session", make_session_patcher(db_session)),
        patch(
            "tasks.calendar_sync._list_google_calendar_events",
            new_callable=AsyncMock,
            return_value=fake_cal_response,
        ),
    ):
        result = pull_calendar_blocks_task(str(test_tenant.id))

    assert result["status"] == "success"
    assert result["blocks_created"] == 1
    assert result["skipped"] == 0

    avail = db_session.exec(
        select(TechAvailability).where(
            TechAvailability.tenant_id == test_tenant.id,
            TechAvailability.notes == fake_event_id,
        )
    ).first()
    assert avail is not None
    assert avail.availability_type == "unavailable"

    db_session.refresh(integration)
    assert integration.last_sync_cursor == "tok_abc123"


# ---------------------------------------------------------------------------
# 11. pull_calendar_blocks_task — Pilot for Trades-owned events are skipped
# ---------------------------------------------------------------------------


def test_pull_blocks_skips_pilot_events(
    db_session, test_tenant, test_user, test_customer, test_site
):
    _create_integration(db_session, test_tenant.id, test_user.id)
    job = _create_job(
        db_session,
        test_tenant.id,
        test_customer.id,
        test_site.id,
        test_user.id,
        scheduled=True,
    )

    now = datetime.now(UTC)
    fake_cal_response = {
        "items": [
            {
                "id": "pilot_owned_event",
                "status": "confirmed",
                "summary": f"Pilot for Trades Job — {job.id}",
                "start": {"dateTime": (now + timedelta(hours=1)).isoformat()},
                "end": {"dateTime": (now + timedelta(hours=2)).isoformat()},
                "extendedProperties": {
                    "private": {
                        "pilot_job_id": str(job.id),
                        "pilot_tenant_id": str(test_tenant.id),
                    }
                },
            }
        ],
        "nextSyncToken": "tok_zzz",
    }

    with (
        patch("tasks.calendar_sync.Session", make_session_patcher(db_session)),
        patch(
            "tasks.calendar_sync._list_google_calendar_events",
            new_callable=AsyncMock,
            return_value=fake_cal_response,
        ),
    ):
        result = pull_calendar_blocks_task(str(test_tenant.id))

    assert result["status"] == "success"
    assert result["blocks_created"] == 0
    assert result["skipped"] == 1


# ---------------------------------------------------------------------------
# 12. pull_calendar_blocks_all_tenants_task — fans out per active integration
# ---------------------------------------------------------------------------


def test_pull_all_tenants_fans_out(db_session, test_tenant, test_user):
    _create_integration(db_session, test_tenant.id, test_user.id)

    with (
        patch("tasks.calendar_sync.Session", make_session_patcher(db_session)),
        patch("tasks.calendar_sync.pull_calendar_blocks_task") as mock_task,
    ):
        mock_task.delay = MagicMock()
        result = pull_calendar_blocks_all_tenants_task()

    assert result["status"] == "success"
    assert result["tenants_queued"] >= 1
    mock_task.delay.assert_called()
