"""
Calendar Conflict Resolution API — B6 (A32, A33)

Endpoints:
  GET  /api/v1/integrations/calendar/conflicts           — list pending/all conflicts (A32)
  GET  /api/v1/integrations/calendar/conflicts/{id}      — detail with field-level diff (A32)
  POST /api/v1/integrations/calendar/conflicts/{id}/resolve — resolve with staleness guard (A33)

Test endpoints registered BEFORE authenticated endpoints (path priority rule §8.2).

RBAC: integrations.manage (owner/accountant tier)
"""

from __future__ import annotations

import base64
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select

from app.models.fulfillment import Job
from app.models.scheduling import CalendarSyncConflict
from core.auth import AuthenticatedUser
from core.db import get_db, set_audit_context_sync
from core.permissions import require_permission
from core.test_context import get_test_context
from services.calendar_conflict_service import CalendarConflictService

router = APIRouter(
    prefix="/integrations/calendar/conflicts",
    tags=["integrations"],
)

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class FieldDiffResponse(BaseModel):
    """Single field-level diff entry (§16.2)."""

    field_name: str
    pilot_value: Any | None = None
    external_value: Any | None = None
    base_value: Any | None = None
    pilot_change: str  # unchanged | modified | added | removed
    external_change: str


class ConflictListItem(BaseModel):
    """Summary row for the conflicts list endpoint (A32)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conflict_type: str
    job_id: uuid.UUID
    job_title: str | None = None
    scheduled_start_at: datetime | None = None
    urgency_score: int | None = None
    pilot_modified_at: datetime
    external_modified_at: datetime
    resolution: str | None = None
    detected_at: datetime  # exposed as created_at alias


class ConflictDetailResponse(BaseModel):
    """Full detail view with field_diffs (A32)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conflict_type: str
    job_id: uuid.UUID
    job_title: str | None = None
    scheduled_start_at: datetime | None = None
    urgency_score: int | None = None
    pilot_modified_by_user_id: uuid.UUID | None = None
    pilot_modified_by_name: str | None = None
    pilot_modified_at: datetime
    external_modified_at: datetime
    resolution: str | None = None
    resolved_by_user_id: uuid.UUID | None = None
    resolved_at: datetime | None = None
    auto_resolved_stale: bool
    pilot_snapshot: dict[str, Any] | None = None
    external_snapshot: dict[str, Any] | None = None
    base_snapshot: dict[str, Any] | None = None
    field_diffs: list[FieldDiffResponse]
    detected_at: datetime


class ConflictListResponse(BaseModel):
    """Paginated list response (A32)."""

    conflicts: list[ConflictListItem]
    next_cursor: str | None = None
    total_pending: int


class ConflictResolveRequest(BaseModel):
    """Request body for the resolve endpoint (A33)."""

    resolution: str
    expected_pilot_modified_at: datetime
    expected_external_modified_at: datetime


class ConflictResolveResponse(BaseModel):
    """Success response from the resolve endpoint (A33)."""

    id: uuid.UUID
    resolution: str
    resolved_at: datetime
    resolved_by_user_id: uuid.UUID


# ---------------------------------------------------------------------------
# Shared business logic
# ---------------------------------------------------------------------------


def _build_conflict_list_item(
    conflict: CalendarSyncConflict, job: Job | None
) -> ConflictListItem:
    """Build a ConflictListItem from ORM objects."""
    job_title: str | None = None
    scheduled_start_at: datetime | None = None

    if job is not None:
        job_title = getattr(job, "title", None) or getattr(job, "name", None)
        scheduled_start_at = getattr(job, "scheduled_start_at", None)
    else:
        # Fall back to snapshot data
        snapshot = conflict.local_snapshot or {}
        job_title = snapshot.get("title") or snapshot.get("summary")
        scheduled_start_at = snapshot.get("scheduled_start_at")

    return ConflictListItem(
        id=conflict.id,
        conflict_type=conflict.conflict_type,
        job_id=conflict.job_id,
        job_title=job_title,
        scheduled_start_at=scheduled_start_at,
        urgency_score=conflict.urgency_score,
        pilot_modified_at=conflict.pilot_modified_at,
        external_modified_at=conflict.external_modified_at,
        resolution=conflict.resolution,
        detected_at=conflict.created_at,
    )


def _build_conflict_detail(
    conflict: CalendarSyncConflict,
    job: Job | None,
    db: Session,
) -> ConflictDetailResponse:
    """Build a ConflictDetailResponse from ORM objects, computing field_diffs."""
    # Resolve job metadata
    job_title: str | None = None
    scheduled_start_at: datetime | None = None
    if job is not None:
        job_title = getattr(job, "title", None) or getattr(job, "name", None)
        scheduled_start_at = getattr(job, "scheduled_start_at", None)
    else:
        snapshot = conflict.local_snapshot or {}
        job_title = snapshot.get("title") or snapshot.get("summary")
        scheduled_start_at = snapshot.get("scheduled_start_at")

    # Resolve modifier name
    pilot_modified_by_name: str | None = None
    if conflict.pilot_modified_by_user_id:
        from app.models.core import User

        modifier = db.exec(
            select(User).where(User.id == conflict.pilot_modified_by_user_id)
        ).first()
        if modifier:
            parts = [modifier.first_name or "", modifier.last_name or ""]
            pilot_modified_by_name = " ".join(p for p in parts if p).strip() or None

    # Compute field diffs
    raw_diffs = CalendarConflictService.compute_field_diffs(
        pilot_snapshot=conflict.local_snapshot or {},
        external_snapshot=conflict.remote_snapshot or {},
        base_snapshot=conflict.base_snapshot,
    )
    field_diffs = [FieldDiffResponse(**d) for d in raw_diffs]

    return ConflictDetailResponse(
        id=conflict.id,
        conflict_type=conflict.conflict_type,
        job_id=conflict.job_id,
        job_title=job_title,
        scheduled_start_at=scheduled_start_at,
        urgency_score=conflict.urgency_score,
        pilot_modified_by_user_id=conflict.pilot_modified_by_user_id,
        pilot_modified_by_name=pilot_modified_by_name,
        pilot_modified_at=conflict.pilot_modified_at,
        external_modified_at=conflict.external_modified_at,
        resolution=conflict.resolution,
        resolved_by_user_id=conflict.resolved_by_user_id,
        resolved_at=conflict.resolved_at,
        auto_resolved_stale=conflict.auto_resolved_stale,
        pilot_snapshot=conflict.local_snapshot,
        external_snapshot=conflict.remote_snapshot,
        base_snapshot=conflict.base_snapshot,
        field_diffs=field_diffs,
        detected_at=conflict.created_at,
    )


def _list_conflicts_impl(
    tenant_id: uuid.UUID,
    db: Session,
    status_filter: str = "pending",
    cursor: str | None = None,
    limit: int = 20,
) -> ConflictListResponse:
    """Shared list logic — urgency-sorted, cursor-paginated."""
    # Build base query
    query = select(CalendarSyncConflict).where(
        CalendarSyncConflict.tenant_id == tenant_id
    )

    if status_filter == "pending":
        query = query.where(CalendarSyncConflict.resolution.is_(None))  # type: ignore[union-attr]
    elif status_filter == "resolved":
        query = query.where(CalendarSyncConflict.resolution.is_not(None))  # type: ignore[union-attr]
    # 'all' applies no additional filter

    # Cursor decode: base64-encoded "<urgency_score>|<id>"
    if cursor:
        try:
            decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
            _cursor_score_str, cursor_id_str = decoded.split("|", 1)
            cursor_id = uuid.UUID(cursor_id_str)
            query = query.where(CalendarSyncConflict.id != cursor_id)
        except Exception:
            pass  # Malformed cursor — ignore, return from start

    # Order: urgency_score ASC NULLS LAST (lower score = more urgent), then created_at DESC
    query = (
        query.order_by(
            CalendarSyncConflict.urgency_score.asc().nullslast(),  # type: ignore[union-attr]
            CalendarSyncConflict.created_at.desc(),  # type: ignore[union-attr]
        ).limit(limit + 1)  # fetch one extra to detect next page
    )

    conflicts = db.exec(query).all()

    # Detect next page
    has_next = len(conflicts) > limit
    if has_next:
        conflicts = conflicts[:limit]

    # Count total pending
    total_pending = CalendarConflictService.get_pending_conflicts_count(db, tenant_id)

    # Build list items (batch-fetch jobs for efficiency)
    job_ids = {c.job_id for c in conflicts}
    jobs_by_id: dict[uuid.UUID, Job] = {}
    if job_ids:
        jobs = db.exec(select(Job).where(Job.id.in_(job_ids))).all()  # type: ignore[union-attr]
        jobs_by_id = {j.id: j for j in jobs}

    items = [_build_conflict_list_item(c, jobs_by_id.get(c.job_id)) for c in conflicts]

    # Build next cursor
    next_cursor: str | None = None
    if has_next and conflicts:
        last = conflicts[-1]
        score_str = (
            str(last.urgency_score) if last.urgency_score is not None else "null"
        )
        raw = f"{score_str}|{last.id}"
        next_cursor = base64.urlsafe_b64encode(raw.encode()).decode()

    return ConflictListResponse(
        conflicts=items,
        next_cursor=next_cursor,
        total_pending=total_pending,
    )


def _get_conflict_detail_impl(
    conflict_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: Session,
) -> ConflictDetailResponse:
    """Shared detail logic — fetches conflict + job, computes diffs."""
    conflict = db.exec(
        select(CalendarSyncConflict).where(
            CalendarSyncConflict.id == conflict_id,
            CalendarSyncConflict.tenant_id == tenant_id,
        )
    ).first()

    if not conflict:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar conflict not found",
        )

    job = db.exec(select(Job).where(Job.id == conflict.job_id)).first()
    return _build_conflict_detail(conflict, job, db)


def _resolve_conflict_impl(
    conflict_id: uuid.UUID,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: ConflictResolveRequest,
    db: Session,
) -> ConflictResolveResponse:
    """
    A33 resolve logic with staleness guard (§D.2, §16.4).

    Returns ConflictResolveResponse on success.
    Raises 409 if stale, 422 if resolution invalid for conflict_type, 404 if not found.
    """
    # Tenant-scoped fetch (IDOR guard)
    conflict = db.exec(
        select(CalendarSyncConflict).where(
            CalendarSyncConflict.id == conflict_id,
            CalendarSyncConflict.tenant_id == tenant_id,
        )
    ).first()

    if not conflict:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar conflict not found",
        )

    # Check already resolved
    if conflict.resolution is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "https://pilotfortrades.com/errors/conflict-already-resolved",
                "title": "Conflict Already Resolved",
                "status": 409,
                "detail": f"This conflict was already resolved with '{conflict.resolution}'.",
            },
        )

    # Validate resolution is legal for conflict_type
    if not CalendarConflictService.validate_resolution_for_conflict_type(
        conflict.conflict_type, payload.resolution
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Resolution '{payload.resolution}' is not valid for "
                f"conflict_type '{conflict.conflict_type}'. "
                f"Valid values: {sorted(list(__import__('services.calendar_conflict_service', fromlist=['LEGAL_RESOLUTIONS']).LEGAL_RESOLUTIONS.get(conflict.conflict_type, [])))}"
            ),
        )

    # A33 staleness check
    if CalendarConflictService.check_staleness(
        conflict,
        payload.expected_pilot_modified_at,
        payload.expected_external_modified_at,
    ):
        # Re-fetch detail for refreshed payload
        job = db.exec(select(Job).where(Job.id == conflict.job_id)).first()
        refreshed = _build_conflict_detail(conflict, job, db)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "https://pilotfortrades.com/errors/conflict-stale",
                "title": "Conflict State Has Changed",
                "status": 409,
                "detail": (
                    "The conflict was modified since you last viewed it. "
                    "Review the updated diff and re-submit."
                ),
                "refreshed_conflict": refreshed.model_dump(mode="json"),
            },
        )

    # Apply resolution
    now = datetime.now(UTC)
    set_audit_context_sync(db, user_id)
    conflict.resolution = payload.resolution
    conflict.resolved_by_user_id = user_id
    conflict.resolved_at = now
    conflict.updated_by = user_id
    db.add(conflict)
    db.commit()
    db.refresh(conflict)

    return ConflictResolveResponse(
        id=conflict.id,
        resolution=conflict.resolution,
        resolved_at=conflict.resolved_at,
        resolved_by_user_id=conflict.resolved_by_user_id,
    )


# ---------------------------------------------------------------------------
# Test endpoints — registered FIRST (path priority)
# ---------------------------------------------------------------------------


@router.get("/test", response_model=ConflictListResponse)
def list_conflicts_test(
    status_filter: str = Query("pending", alias="status"),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ConflictListResponse:
    """TEST ENDPOINT: List calendar conflicts — no JWT required."""
    test_context = get_test_context()
    return _list_conflicts_impl(
        test_context.tenant_id, db, status_filter, cursor, limit
    )


@router.get("/{conflict_id}/test", response_model=ConflictDetailResponse)
def get_conflict_detail_test(
    conflict_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ConflictDetailResponse:
    """TEST ENDPOINT: Get conflict detail — no JWT required."""
    test_context = get_test_context()
    return _get_conflict_detail_impl(conflict_id, test_context.tenant_id, db)


@router.post("/{conflict_id}/resolve/test", response_model=ConflictResolveResponse)
def resolve_conflict_test(
    conflict_id: uuid.UUID,
    payload: ConflictResolveRequest,
    db: Session = Depends(get_db),
) -> ConflictResolveResponse:
    """TEST ENDPOINT: Resolve a conflict — no JWT required."""
    test_context = get_test_context()
    return _resolve_conflict_impl(
        conflict_id, test_context.tenant_id, test_context.id, payload, db
    )


# ---------------------------------------------------------------------------
# Authenticated endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=ConflictListResponse)
def list_conflicts(
    status_filter: str = Query("pending", alias="status"),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("integrations.manage")
    ),
) -> ConflictListResponse:
    """
    List calendar sync conflicts for the caller's tenant (A32).

    Urgency-sorted (lower urgency_score = more urgent), cursor-paginated.

    Query params:
      - status: pending (default) | resolved | all
      - cursor: opaque pagination cursor
      - limit: 1–100 (default 20)
    """
    return _list_conflicts_impl(
        current_user.tenant_id, db, status_filter, cursor, limit
    )


@router.get("/{conflict_id}", response_model=ConflictDetailResponse)
def get_conflict_detail(
    conflict_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("integrations.manage")
    ),
) -> ConflictDetailResponse:
    """
    Get conflict detail with server-computed field-level diff (A32).

    The `field_diffs` array uses §16.2 vocabulary:
      pilot_change / external_change: unchanged | modified | added | removed
    """
    return _get_conflict_detail_impl(conflict_id, current_user.tenant_id, db)


@router.post("/{conflict_id}/resolve", response_model=ConflictResolveResponse)
def resolve_conflict(
    conflict_id: uuid.UUID,
    payload: ConflictResolveRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("integrations.manage")
    ),
) -> ConflictResolveResponse:
    """
    Resolve a calendar conflict with pre-commit staleness guard (A33).

    The client must echo back `expected_pilot_modified_at` and
    `expected_external_modified_at` from the detail response.
    If either timestamp has changed since the client last fetched the conflict,
    HTTP 409 is returned with a refreshed conflict payload.

    Resolution must be legal for the conflict_type:
      - modified_modified  → accept_local | accept_remote
      - deleted_modified   → restore_from_calendar | delete_calendar_too
      - modified_deleted   → recreate_calendar_event | delete_pilot_job
    """
    return _resolve_conflict_impl(
        conflict_id, current_user.tenant_id, current_user.user_id, payload, db
    )
