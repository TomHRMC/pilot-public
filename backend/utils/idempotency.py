"""
utils/idempotency.py

Natural-key fallback deduplication for offline-capable operations.

Implements the 7-day/30-day dedup window described in mvp-arch §7.6 and §15.4.
Called by service layer AFTER the 24-hour idempotency middleware has already
determined the idempotency key is expired or absent.

Consumed by:
    - All B7a offline-capable endpoints (time_entry, expense, photo, job_note)
    - All B7b offline-capable endpoints (loto_check, job_status_change, change_order)
    - B8/A51 background sync infrastructure

Distinct from core/idempotency.py (the HTTP middleware layer for the 24h window).
This module is the service-layer backstop for the 7–30 day offline window.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Natural-key dedup window definitions (authoritative source for B7a/B7b/B8)
# ─────────────────────────────────────────────────────────────────────────────

NATURAL_KEY_WINDOWS: dict[str, timedelta] = {
    "time_entry": timedelta(days=7),
    "expense": timedelta(days=7),
    "photo": timedelta(days=30),
    "job_note": timedelta(days=7),
    # Deferred to B7b — tables not yet in DB; registered here as future values
    "job_status_change": timedelta(days=7),
    "loto_check": timedelta(days=7),
    "change_order": timedelta(days=7),
    "voice_audio": timedelta(days=7),
}

# Required natural-key fields per operation type (used for validation)
_REQUIRED_NATURAL_KEY_FIELDS: dict[str, list[str]] = {
    "time_entry": ["user_id", "job_id", "started_at"],
    "expense": ["user_id", "job_id", "incurred_at", "cost_cents"],
    "photo": ["created_by", "job_id", "client_capture_at"],
    "job_note": ["created_by", "job_id", "created_at"],
}


def check_natural_key_dedup(
    db: Session,
    operation_type: str,
    natural_key_fields: dict,
    window_days: int | None = None,
) -> dict | None:
    """
    Check whether a duplicate offline operation exists based on natural-key fields.

    Called after the primary idempotency-key lookup (24h window) fails to find
    a match. Provides the backstop dedup for the 72-hour offline scenario where
    the idempotency key has expired.

    When a natural-key match is found, the caller must return the existing record
    with HTTP 200 and header `X-Idempotency-Replay: true` — same semantics as a
    primary idempotency-key hit.

    Args:
        db: SQLModel session (injected via Depends(get_db))
        operation_type: One of NATURAL_KEY_WINDOWS keys (e.g., 'time_entry')
        natural_key_fields: Dict of field name → value for the natural key tuple.
            time_entry:  {'user_id': UUID, 'job_id': UUID, 'started_at': datetime}
            expense:     {'user_id': UUID, 'job_id': UUID, 'incurred_at': datetime,
                          'cost_cents': int}
            photo:       {'created_by': UUID, 'job_id': UUID,
                          'client_capture_at': datetime}
            job_note:    {'created_by': UUID, 'job_id': UUID, 'created_at': datetime}
        window_days: Override the default window from NATURAL_KEY_WINDOWS. Use only
            for testing or tenant-configurable window settings (future).

    Returns:
        dict with keys {'id': UUID, 'record': <ORM row>} if a duplicate exists,
        None if no duplicate found within the window.

    Raises:
        ValueError: If operation_type is not in NATURAL_KEY_WINDOWS.
        ValueError: If required natural_key_fields for the operation_type are missing.

    Example:
        existing = check_natural_key_dedup(
            db=db,
            operation_type='time_entry',
            natural_key_fields={
                'user_id': current_user.user_id,
                'job_id': job_id,
                'started_at': body.started_at,
            },
        )
        if existing:
            return JSONResponse(
                content=existing['record'].model_dump(),
                headers={'X-Idempotency-Replay': 'true'},
            )
    """
    if operation_type not in NATURAL_KEY_WINDOWS:
        raise ValueError(
            f"Unknown operation_type '{operation_type}'. "
            f"Must be one of: {list(NATURAL_KEY_WINDOWS.keys())}"
        )

    # Validate required fields are present for B7a-implemented operation types
    required = _REQUIRED_NATURAL_KEY_FIELDS.get(operation_type)
    if required:
        missing = [f for f in required if f not in natural_key_fields]
        if missing:
            raise ValueError(
                f"Missing required natural_key_fields for '{operation_type}': {missing}"
            )

    # Determine dedup window
    if window_days is not None:
        window = timedelta(days=window_days)
    else:
        window = NATURAL_KEY_WINDOWS[operation_type]

    cutoff = datetime.now(UTC) - window

    # ── Dispatch to model-specific lookup ────────────────────────────────────
    if operation_type == "time_entry":
        return _dedup_time_entry(db, natural_key_fields, cutoff)
    elif operation_type == "expense":
        return _dedup_expense(db, natural_key_fields, cutoff)
    elif operation_type == "photo":
        return _dedup_photo(db, natural_key_fields, cutoff)
    elif operation_type == "job_note":
        return _dedup_job_note(db, natural_key_fields, cutoff)
    else:
        # B7b operation types deferred — no dedup check yet
        logger.debug(
            "check_natural_key_dedup: operation_type '%s' dedup deferred to B7b",
            operation_type,
        )
        return None


def _dedup_time_entry(db: Session, fields: dict, cutoff: datetime) -> dict | None:
    """Natural-key dedup for time_entry: (user_id, job_id, started_at)."""
    from app.models.fulfillment import JobTimeEntry

    stmt = (
        select(JobTimeEntry)
        .where(JobTimeEntry.user_id == fields["user_id"])
        .where(JobTimeEntry.job_id == fields["job_id"])
        .where(JobTimeEntry.started_at == fields["started_at"])
        .where(JobTimeEntry.created_at >= cutoff)
    )
    record = db.exec(stmt).first()
    if record:
        return {"id": record.id, "record": record}
    return None


def _dedup_expense(db: Session, fields: dict, cutoff: datetime) -> dict | None:
    """Natural-key dedup for expense: (user_id, job_id, incurred_at, cost_cents)."""
    from app.models.fulfillment import JobExpense

    # job_expense has no user_id; use created_by as author field
    stmt = (
        select(JobExpense)
        .where(JobExpense.job_id == fields["job_id"])
        .where(JobExpense.incurred_at == fields["incurred_at"])
        .where(JobExpense.cost_cents == fields["cost_cents"])
        .where(JobExpense.created_at >= cutoff)
    )
    # Filter by user_id if available (created_by stores the author)
    if "user_id" in fields:
        stmt = stmt.where(JobExpense.created_by == fields["user_id"])
    record = db.exec(stmt).first()
    if record:
        return {"id": record.id, "record": record}
    return None


def _dedup_photo(db: Session, fields: dict, cutoff: datetime) -> dict | None:
    """
    Natural-key dedup for photo: primary (created_by, job_id, file_hash),
    fallback (created_by, job_id, client_capture_at) when file_hash is None.
    """
    from app.models.fulfillment import JobAttachment

    file_hash = fields.get("file_hash")

    if file_hash:
        # Strong dedup: match by content hash
        stmt = (
            select(JobAttachment)
            .where(JobAttachment.created_by == fields["created_by"])
            .where(JobAttachment.job_id == fields["job_id"])
            .where(JobAttachment.file_hash == file_hash)
            .where(JobAttachment.created_at >= cutoff)
        )
    else:
        # Fallback dedup: match by client capture timestamp (§F.3)
        client_capture_at = fields.get("client_capture_at")
        if not client_capture_at:
            return None

        stmt = (
            select(JobAttachment)
            .where(JobAttachment.created_by == fields["created_by"])
            .where(JobAttachment.job_id == fields["job_id"])
            .where(JobAttachment.client_capture_at == client_capture_at)
            .where(JobAttachment.created_at >= cutoff)
        )

    record = db.exec(stmt).first()
    if record:
        return {"id": record.id, "record": record}
    return None


def _dedup_job_note(db: Session, fields: dict, cutoff: datetime) -> dict | None:
    """Natural-key dedup for job_note: (created_by, job_id, created_at)."""
    from app.models.fulfillment import JobNotes

    stmt = (
        select(JobNotes)
        .where(JobNotes.created_by == fields["created_by"])
        .where(JobNotes.job_id == fields["job_id"])
        .where(JobNotes.created_at == fields["created_at"])
        .where(JobNotes.created_at >= cutoff)
    )
    record = db.exec(stmt).first()
    if record:
        return {"id": record.id, "record": record}
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Sync event recorder (append-only log into mobile_sync_event)
# ─────────────────────────────────────────────────────────────────────────────


def record_sync_event(
    db: Session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    device_id: str,
    operation_type: str,
    idempotency_uuid: uuid.UUID,
    client_capture_at: datetime,
    status: str,
    operation_payload_summary: dict | None = None,
    conflict_severity: str | None = None,
    synced_at: datetime | None = None,
    error_detail: dict | None = None,
) -> None:
    """
    Insert a new row into mobile_sync_event (append-only — never updates).

    Called at each sync-attempt status transition: pending, syncing, succeeded,
    failed, or conflict. Multiple calls for the same operation produce multiple
    rows — this is intentional for the full audit trail.

    This function swallows exceptions and logs them. Sync-event recording must
    never cause the originating sync operation to fail. The audit trail is
    important but not worth dropping a tech's time entry over.

    Args:
        db: SQLModel session
        tenant_id: Tenant UUID (from current_user.tenant_id)
        user_id: Tech's user UUID
        device_id: Client-reported device identifier (opaque string)
        operation_type: Must be in NATURAL_KEY_WINDOWS keys
        idempotency_uuid: The client-generated UUID v4 from the Idempotency-Key header
        client_capture_at: The client_capture_at from the request body
        status: One of 'pending' | 'syncing' | 'succeeded' | 'failed' | 'conflict'
        operation_payload_summary: Non-PII summary dict (e.g., {'job_id': str, 'hours': float})
        conflict_severity: One of the 4 severity classes, or None if not a conflict
        synced_at: Set when status is 'succeeded'
        error_detail: Set when status is 'failed'; structured error info

    Returns:
        None (fire-and-forget log; never raises on failure — log and swallow)
    """
    try:
        # Lazy import: MobileSyncEvent is created in A38 (executed after A39)
        from app.models.sync import MobileSyncEvent

        event = MobileSyncEvent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            device_id=device_id,
            operation_type=operation_type,
            idempotency_uuid=idempotency_uuid,
            client_capture_at=client_capture_at,
            status=status,
            operation_payload_summary=operation_payload_summary,
            conflict_severity=conflict_severity,
            synced_at=synced_at,
            error_detail=error_detail,
        )
        db.add(event)
        db.flush()  # Use flush not commit — caller owns the transaction
        logger.debug(
            "record_sync_event: recorded %s status=%s idempotency_uuid=%s",
            operation_type,
            status,
            idempotency_uuid,
        )

    except Exception:
        # NEVER let sync logging crash the calling operation
        logger.exception(
            "record_sync_event: failed to log sync event for operation_type=%s "
            "user_id=%s — swallowing to protect caller",
            operation_type,
            user_id,
        )
