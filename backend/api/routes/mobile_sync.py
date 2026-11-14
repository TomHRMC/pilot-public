"""
api/routes/mobile_sync.py

B7a/A38: Sync Queue State Model (Server-Side Visibility)

Endpoint:
    GET /api/v1/mobile-sync/state/{user_id}

Purpose:
    Owner/admin view of a tech's server-side sync state for troubleshooting
    and oversight. Cursor-based pagination, ordered by created_at DESC.

RBAC:
    Requires mobile_sync.view permission (owner, operator roles only).
    Technicians do NOT have this permission — sync state is surfaced to techs
    via client-side queue, not this admin endpoint.

Tenant isolation:
    The queried user_id must belong to the same tenant as the caller.
    Returns 404 (not 403) for cross-tenant or nonexistent user_ids.
"""

import base64
import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select

from app.models.sync import MobileSyncEvent
from core.auth import AuthenticatedUser
from core.db import get_db
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context

router = APIRouter()
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Response schemas
# ─────────────────────────────────────────────────────────────────────────────


class MobileSyncEventResponse(BaseModel):
    """Single mobile sync event row."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    device_id: str
    operation_type: str
    operation_payload_summary: dict | None = None
    status: str
    conflict_severity: str | None = None
    client_capture_at: Any  # AwareDatetime — serialized as ISO string
    synced_at: Any | None = None
    error_detail: dict | None = None
    idempotency_uuid: uuid.UUID
    created_at: Any  # AwareDatetime


class MobileSyncStateResponse(BaseModel):
    """Paginated response for GET /mobile-sync/state/{user_id}."""

    user_id: uuid.UUID
    items: list[MobileSyncEventResponse]
    cursor: str | None = None
    has_more: bool


# ─────────────────────────────────────────────────────────────────────────────
# Cursor helpers (opaque Base64-encoded JSON cursor)
# ─────────────────────────────────────────────────────────────────────────────

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 50


def _encode_cursor(last_id: uuid.UUID) -> str:
    """Encode the last row ID into an opaque cursor string."""
    payload = json.dumps({"id": str(last_id)})
    return base64.urlsafe_b64encode(payload.encode()).decode()


def _decode_cursor(cursor: str) -> uuid.UUID | None:
    """Decode a cursor string back to a UUID. Returns None if invalid."""
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        return uuid.UUID(payload["id"])
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Shared implementation
# ─────────────────────────────────────────────────────────────────────────────


def _get_sync_state_impl(
    path_user_id: uuid.UUID,
    cursor: str | None,
    limit: int,
    status_filter: str | None,
    db: Session,
    caller_tenant_id: uuid.UUID,
) -> MobileSyncStateResponse:
    """
    Shared business logic — accepts both AuthenticatedUser and TestUserContext callers.

    Validates that path_user_id belongs to caller's tenant (tenant isolation).
    Queries mobile_sync_event ordered by created_at DESC with cursor pagination.
    """
    from app.models.core import User

    # Tenant isolation: verify the target user exists within the caller's tenant
    target_user = db.exec(
        select(User).where(User.id == path_user_id).where(User.is_active == True)
    ).first()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {path_user_id} not found",
        )

    # Check tenant isolation — target user must be a tenant_user of the caller's tenant
    from app.models.auth import TenantUser

    tenant_membership = db.exec(
        select(TenantUser)
        .where(TenantUser.user_id == path_user_id)
        .where(TenantUser.tenant_id == caller_tenant_id)
    ).first()

    if not tenant_membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {path_user_id} not found",
        )

    # Clamp limit
    effective_limit = min(max(1, limit), _MAX_LIMIT)

    # Build base query — always filter by tenant_id and user_id
    stmt = (
        select(MobileSyncEvent)
        .where(MobileSyncEvent.tenant_id == caller_tenant_id)
        .where(MobileSyncEvent.user_id == path_user_id)
    )

    # Optional status filter
    if status_filter:
        valid_statuses = {"pending", "syncing", "succeeded", "failed", "conflict"}
        if status_filter not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "type": "https://pilotfortrades.com/errors/invalid-parameter",
                    "title": "Invalid status filter",
                    "status": 400,
                    "detail": f"status must be one of: {sorted(valid_statuses)}",
                },
            )
        stmt = stmt.where(MobileSyncEvent.status == status_filter)

    # Cursor-based pagination (created_at DESC, id for tie-breaking)
    if cursor:
        cursor_id = _decode_cursor(cursor)
        if cursor_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "type": "https://pilotfortrades.com/errors/invalid-cursor",
                    "title": "Invalid cursor",
                    "status": 400,
                    "detail": "Cursor is malformed or expired",
                },
            )
        # Get the created_at of the cursor row for keyset pagination
        cursor_row = db.exec(
            select(MobileSyncEvent).where(MobileSyncEvent.id == cursor_id)
        ).first()
        if cursor_row:
            stmt = stmt.where(MobileSyncEvent.created_at < cursor_row.created_at)

    stmt = stmt.order_by(MobileSyncEvent.created_at.desc()).limit(effective_limit + 1)

    rows = db.exec(stmt).all()

    has_more = len(rows) > effective_limit
    items = rows[:effective_limit]

    next_cursor = _encode_cursor(items[-1].id) if has_more and items else None

    return MobileSyncStateResponse(
        user_id=path_user_id,
        items=[MobileSyncEventResponse.model_validate(r) for r in items],
        cursor=next_cursor,
        has_more=has_more,
    )


# ─────────────────────────────────────────────────────────────────────────────
# TEST endpoint (register BEFORE authenticated to avoid /test route conflict)
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/state/test/{user_id}",
    response_model=MobileSyncStateResponse,
    summary="[TEST] Get sync state for a user — no auth required",
)
def get_sync_state_test(
    user_id: uuid.UUID,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Test endpoint — no auth required. Blocked in staging/production."""
    test_ctx = get_test_context()
    return _get_sync_state_impl(
        path_user_id=user_id,
        cursor=cursor,
        limit=limit,
        status_filter=status,
        db=db,
        caller_tenant_id=test_ctx.tenant_id,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Authenticated endpoint
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/state/{user_id}",
    response_model=MobileSyncStateResponse,
    summary="Get sync state for a tech (owner/admin only)",
)
def get_sync_state(
    user_id: uuid.UUID,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("mobile_sync.view")),
):
    """
    Owner/admin view of a tech's server-side sync state.

    Returns a cursor-paginated list of sync events ordered by created_at DESC.
    Use cursor from response to get the next page.
    """
    return _get_sync_state_impl(
        path_user_id=user_id,
        cursor=cursor,
        limit=limit,
        status_filter=status,
        db=db,
        caller_tenant_id=current_user.tenant_id,
    )


# ============================================================
# B7b/A45 — Tech-Resolvable Conflict UI Endpoints
# ============================================================

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.system import MobileSyncOwnerEscalation
from services.mobile_sync_conflict import (
    build_escalation_explainer,
    classify_sync_conflict,
    compute_field_diffs,
)
from utils.staleness_check import assert_not_stale


class ConflictDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    conflict_id: uuid.UUID
    operation_type: str
    status: str
    conflict_severity: str | None
    classification_reason: str | None
    tech_version: Any | None
    server_version: Any | None
    field_diffs: list[Any] | None
    client_capture_at: Any
    created_at: Any


class ConflictResolveRequest(BaseModel):
    resolution: str  # use_local | use_server | escalate_to_owner
    expected_server_version_at: datetime | None = None


class ConflictResolveResponse(BaseModel):
    conflict_id: uuid.UUID
    resolution: str
    resolved_at: datetime
    escalation_id: uuid.UUID | None


# ---- Shared logic ----


def _get_conflict_detail_impl(
    conflict_id: uuid.UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> ConflictDetailResponse:
    """Get conflict detail for a mobile_sync_event row with status='conflict'."""
    event = db.exec(
        select(MobileSyncEvent)
        .where(MobileSyncEvent.id == conflict_id)
        .where(MobileSyncEvent.tenant_id == user_context.tenant_id)
        .where(MobileSyncEvent.user_id == user_context.id)
    ).first()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conflict not found"
        )

    # Classify severity from the matrix
    trigger_condition = (event.error_detail or {}).get("trigger_condition", "unknown")
    resolution = classify_sync_conflict(
        operation_type=event.operation_type,
        trigger_condition=trigger_condition,
        tenant_id=user_context.tenant_id,
        db=db,
    )

    # Compute field diffs (server_version is None since we don't fetch live state here)
    field_diffs = compute_field_diffs(event.operation_payload_summary, None)

    return ConflictDetailResponse(
        conflict_id=event.id,
        operation_type=event.operation_type,
        status=event.status,
        conflict_severity=event.conflict_severity or resolution.severity,
        classification_reason=resolution.classification_reason,
        tech_version=event.operation_payload_summary,
        server_version=None,
        field_diffs=field_diffs,
        client_capture_at=event.client_capture_at,
        created_at=event.created_at,
    )


def _resolve_conflict_impl(
    conflict_id: uuid.UUID,
    data: ConflictResolveRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> ConflictResolveResponse:
    """Resolve a conflict: insert result row, optionally create owner escalation."""
    valid_resolutions = {"use_local", "use_server", "escalate_to_owner"}
    if data.resolution not in valid_resolutions:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid resolution. Must be one of: {sorted(valid_resolutions)}",
        )

    conflict_event = db.exec(
        select(MobileSyncEvent)
        .where(MobileSyncEvent.id == conflict_id)
        .where(MobileSyncEvent.tenant_id == user_context.tenant_id)
        .where(MobileSyncEvent.user_id == user_context.id)
    ).first()

    if not conflict_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conflict not found"
        )

    # Staleness check — uses created_at as version anchor (mobile_sync_event is append-only)
    assert_not_stale(
        expected_updated_at=data.expected_server_version_at,
        actual_updated_at=conflict_event.created_at,
        refreshed_payload=_get_conflict_detail_impl(
            conflict_id, db, user_context
        ).model_dump(),
        entity_label="conflict",
    )

    escalation_id = None

    if data.resolution == "escalate_to_owner":
        # Derive trigger_condition from error_detail
        trigger_condition = (conflict_event.error_detail or {}).get(
            "trigger_condition", "unknown"
        )
        resolution_obj = classify_sync_conflict(
            operation_type=conflict_event.operation_type,
            trigger_condition=trigger_condition,
            tenant_id=user_context.tenant_id,
            db=db,
        )
        explainer = build_escalation_explainer(
            operation_type=conflict_event.operation_type,
            trigger_condition=trigger_condition,
            classification_reason=resolution_obj.classification_reason,
        )
        escalation = MobileSyncOwnerEscalation(
            tenant_id=user_context.tenant_id,
            originating_user_id=user_context.id,
            conflict_id=conflict_event.id,
            escalation_reason="tech_chose",
            escalation_reason_explainer=explainer,
            status="pending",
        )
        db.add(escalation)
        db.flush()
        escalation_id = escalation.id

    # Insert resolution result row (append-only pattern)
    resolved_event = MobileSyncEvent(
        tenant_id=user_context.tenant_id,
        user_id=user_context.id,
        device_id=conflict_event.device_id,
        operation_type=conflict_event.operation_type,
        operation_payload_summary=conflict_event.operation_payload_summary,
        status="succeeded" if data.resolution != "escalate_to_owner" else "conflict",
        conflict_severity=conflict_event.conflict_severity,
        client_capture_at=conflict_event.client_capture_at,
        idempotency_uuid=conflict_event.idempotency_uuid,
        resolution_action=data.resolution,
        synced_at=datetime.now(UTC),
    )
    db.add(resolved_event)
    db.commit()

    return ConflictResolveResponse(
        conflict_id=conflict_id,
        resolution=data.resolution,
        resolved_at=datetime.now(UTC),
        escalation_id=escalation_id,
    )


# ---- TEST endpoints (registered FIRST per §8.2) ----


@router.get(
    "/conflicts/{conflict_id}/test",
    response_model=ConflictDetailResponse,
    summary="[TEST] Get conflict detail (no JWT)",
)
def get_conflict_detail_test(
    conflict_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    test_context = get_test_context()
    return _get_conflict_detail_impl(conflict_id, db, test_context)


@router.post(
    "/conflicts/{conflict_id}/resolve/test",
    response_model=ConflictResolveResponse,
    summary="[TEST] Resolve conflict (no JWT)",
)
def resolve_conflict_test(
    conflict_id: uuid.UUID,
    data: ConflictResolveRequest,
    db: Session = Depends(get_db),
):
    test_context = get_test_context()
    return _resolve_conflict_impl(conflict_id, data, db, test_context)


# ---- AUTHENTICATED endpoints ----


@router.get(
    "/conflicts/{conflict_id}",
    response_model=ConflictDetailResponse,
    summary="Get conflict detail for tech resolution",
)
def get_conflict_detail(
    conflict_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("mobile_sync.view")),
):
    """
    Get full conflict detail for a mobile_sync_event row with status='conflict'.
    IDOR prevention: user_id must match current_user.id (returns 404 otherwise).
    """
    return _get_conflict_detail_impl(conflict_id, db, current_user)


@router.post(
    "/conflicts/{conflict_id}/resolve",
    response_model=ConflictResolveResponse,
    summary="Resolve a tech-resolvable conflict",
)
def resolve_conflict(
    conflict_id: uuid.UUID,
    data: ConflictResolveRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("mobile_sync.resolve")
    ),
):
    """
    Resolve a conflict: use_local, use_server, or escalate_to_owner.
    Staleness check via expected_server_version_at.
    For escalate_to_owner: creates MobileSyncOwnerEscalation row.
    """
    return _resolve_conflict_impl(conflict_id, data, db, current_user)
