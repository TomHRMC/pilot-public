"""
api/routes/owner_escalations.py

Owner escalation routing endpoints (B7b/A46 base; extended by B8/A47, B8/A48).

Endpoints:
    GET  /api/v1/owner/mobile-sync-escalations             — List pending escalations (A47)
    GET  /api/v1/owner/mobile-sync-escalations/history     — History of resolved escalations (A47)
    GET  /api/v1/owner/mobile-sync-escalations/{id}        — Escalation detail (A47)
    POST /api/v1/owner/mobile-sync-escalations/{id}/resolve — Owner resolve (A48)
    (+ /test equivalents for each)

Pattern: §16.11 Mobile-to-Web Escalation Pattern.
Established in B7b/A46. Extended by B8/A47 (enhanced list+history) and B8/A48 (7 resolution variants).
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, func, select

from app.models.core import User
from app.models.sync import MobileSyncEvent, MobileSyncEventAudit
from app.models.system import MobileSyncOwnerEscalation
from core.auth import AuthenticatedUser
from core.db import get_db, set_audit_context_sync
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context
from services.mobile_background_sync import dispatch_loop_closure_push
from services.mobile_sync_conflict import (
    compute_field_diffs,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Schemas
# ─────────────────────────────────────────────────────────────────────────────

# A47: 7 A48 resolution variants + B7b compat aliases
A48_VALID_RESOLUTIONS = {
    # A48 canonical variants
    "use_tech",
    "use_server",
    "restore_and_accept",
    "override_with_tech",
    "discard_tech",
    "accept_authorized_at_capture",
    "reject_unauthorized",
    # B7b compat aliases (continue to work)
    "used_local",
    "used_server",
    "manual_edit",
    "rejected",
}


class EscalationListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    originating_user_id: uuid.UUID
    originating_user_name: str | None = None
    operation_type: str | None = None
    conflict_severity: str | None = None
    escalation_reason: str
    escalation_reason_explainer: str
    status: str
    escalated_at: datetime
    # A47 additions
    server_state_summary: Any | None = None


class EscalationListResponse(BaseModel):
    items: list[EscalationListItem]
    next_cursor: str | None
    total_pending: int


class EscalationHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    originating_user_id: uuid.UUID
    operation_type: str | None = None
    conflict_severity: str | None = None
    escalation_reason: str
    status: str
    escalated_at: datetime
    resolved_at: datetime | None
    resolved_by_user_id: uuid.UUID | None
    resolution_action: str | None
    resolution_channel: str | None = None


class EscalationHistoryResponse(BaseModel):
    items: list[EscalationHistoryItem]
    total: int
    offset: int
    limit: int


class EscalationDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    originating_user_id: uuid.UUID
    conflict_id: uuid.UUID
    escalation_reason: str
    escalation_reason_explainer: str
    # A47: escalation_type field
    escalation_type: str | None = None
    status: str
    escalated_at: datetime
    resolved_by_user_id: uuid.UUID | None
    resolved_at: datetime | None
    resolution_action: str | None
    resolution_payload: Any | None
    resolution_channel: str | None = None
    # Nested conflict context
    operation_type: str | None = None
    conflict_severity: str | None = None
    tech_local_snapshot: Any | None = None
    server_state_snapshot: Any | None = None
    field_diffs: list[Any] | None = None
    available_resolutions: list[str] | None = None


class EscalationResolveRequest(BaseModel):
    # A48: expanded to 7 canonical variants + B7b compat
    # resolution is Optional for backward compat (B7b used resolution_action)
    resolution: str | None = None
    expected_server_state_at_view_time: datetime | None = None
    # B7b compat: resolution_action alias
    resolution_action: str | None = None
    resolution_payload: Any | None = None
    expected_escalation_updated_at: datetime | None = None


class EscalationResolveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    committed: bool
    resolution_outcome: str
    post_commit_state: Any | None = None
    originator_notification_dispatched: bool = False
    # B7b compat fields
    id: uuid.UUID | None = None
    status: str | None = None
    resolution_action: str | None = None
    resolved_at: datetime | None = None
    resolved_by_user_id: uuid.UUID | None = None


class FieldIssuesSummaryResponse(BaseModel):
    """Response schema for GET /api/v1/owner/field-issues/summary."""

    model_config = ConfigDict(from_attributes=True)
    pending_count: int


# ─────────────────────────────────────────────────────────────────────────────
# Shared implementation helpers
# ─────────────────────────────────────────────────────────────────────────────


def _get_available_resolutions(escalation: MobileSyncOwnerEscalation) -> list[str]:
    """Return resolution options available for this escalation type."""
    reason = escalation.escalation_reason
    if reason == "auto_severity":
        return [
            "use_tech",
            "use_server",
            "restore_and_accept",
            "override_with_tech",
            "discard_tech",
        ]
    elif reason == "tech_chose":
        return [
            "use_tech",
            "use_server",
            "accept_authorized_at_capture",
            "reject_unauthorized",
        ]
    return ["use_tech", "use_server", "reject_unauthorized"]


def _build_list_item(
    row: MobileSyncOwnerEscalation,
    conflict_event: MobileSyncEvent | None,
    user_name: str | None = None,
) -> EscalationListItem:
    return EscalationListItem(
        id=row.id,
        originating_user_id=row.originating_user_id,
        originating_user_name=user_name,
        escalation_reason=row.escalation_reason,
        escalation_reason_explainer=row.escalation_reason_explainer,
        status=row.status,
        escalated_at=row.escalated_at,
        operation_type=conflict_event.operation_type if conflict_event else None,
        conflict_severity=conflict_event.conflict_severity if conflict_event else None,
        server_state_summary=None,  # populated by live state in A47 future iteration
    )


def _list_escalations_impl(
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
    escalation_status: str = "pending",
    operation_type: str | None = None,
    sort: str = "-escalated_at",
    cursor: str | None = None,
    limit: int = 25,
) -> EscalationListResponse:
    """List owner escalations — paginated with A47 filters."""
    # Validate status filter
    valid_statuses = {"pending", "auto_recovered", "stale", "all"}
    if escalation_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Valid values: {sorted(valid_statuses)}",
        )

    query = select(MobileSyncOwnerEscalation).where(
        MobileSyncOwnerEscalation.tenant_id == user_context.tenant_id
    )

    if escalation_status != "all":
        query = query.where(MobileSyncOwnerEscalation.status == escalation_status)

    if cursor:
        query = query.where(MobileSyncOwnerEscalation.id > uuid.UUID(cursor))

    # A47: sort ordering
    if sort == "-escalated_at":
        query = query.order_by(MobileSyncOwnerEscalation.escalated_at.desc())
    elif sort == "escalated_at":
        query = query.order_by(MobileSyncOwnerEscalation.escalated_at.asc())
    else:
        query = query.order_by(MobileSyncOwnerEscalation.escalated_at.desc())

    # Count total pending for badge display
    count_query = (
        select(func.count())
        .select_from(MobileSyncOwnerEscalation)
        .where(
            MobileSyncOwnerEscalation.tenant_id == user_context.tenant_id,
            MobileSyncOwnerEscalation.status == "pending",
        )
    )
    total_pending = db.exec(count_query).one()

    rows = db.exec(query.limit(limit + 1)).all()

    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]

    next_cursor = str(rows[-1].id) if has_more and rows else None

    # Pre-fetch user names for all originating users in one query
    user_ids = list(
        {row.originating_user_id for row in rows if row.originating_user_id}
    )
    user_name_map: dict[uuid.UUID, str] = {}
    if user_ids:
        users = db.exec(select(User).where(User.id.in_(user_ids))).all()
        for u in users:
            full_name = " ".join(filter(None, [u.first_name, u.last_name])) or None
            user_name_map[u.id] = full_name

    # Load conflict events for each escalation
    items = []
    for row in rows:
        conflict_event = (
            db.exec(
                select(MobileSyncEvent).where(MobileSyncEvent.id == row.conflict_id)
            ).first()
            if row.conflict_id
            else None
        )

        # A47: filter by operation_type if provided
        if (
            operation_type
            and conflict_event
            and conflict_event.operation_type != operation_type
        ):
            continue

        user_name = (
            user_name_map.get(row.originating_user_id)
            if row.originating_user_id
            else None
        )
        items.append(_build_list_item(row, conflict_event, user_name=user_name))

    return EscalationListResponse(
        items=items,
        next_cursor=next_cursor,
        total_pending=total_pending,
    )


def _list_escalation_history_impl(
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
    resolved_at_after: datetime | None = None,
    resolved_at_before: datetime | None = None,
    operation_type: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> EscalationHistoryResponse:
    """A47: Historical archive of resolved escalations."""
    query = (
        select(MobileSyncOwnerEscalation)
        .where(MobileSyncOwnerEscalation.tenant_id == user_context.tenant_id)
        .where(MobileSyncOwnerEscalation.status.in_(["resolved", "rejected"]))
    )

    if resolved_at_after:
        query = query.where(MobileSyncOwnerEscalation.resolved_at >= resolved_at_after)
    if resolved_at_before:
        query = query.where(MobileSyncOwnerEscalation.resolved_at <= resolved_at_before)

    count_query = (
        select(func.count())
        .select_from(MobileSyncOwnerEscalation)
        .where(MobileSyncOwnerEscalation.tenant_id == user_context.tenant_id)
        .where(MobileSyncOwnerEscalation.status.in_(["resolved", "rejected"]))
    )
    total = db.exec(count_query).one()

    rows = db.exec(
        query.order_by(MobileSyncOwnerEscalation.resolved_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    items = []
    for row in rows:
        conflict_event = (
            db.exec(
                select(MobileSyncEvent).where(MobileSyncEvent.id == row.conflict_id)
            ).first()
            if row.conflict_id
            else None
        )

        if (
            operation_type
            and conflict_event
            and conflict_event.operation_type != operation_type
        ):
            continue

        # Check for audit log to get resolution_channel
        audit_row = db.exec(
            select(MobileSyncEventAudit)
            .where(MobileSyncEventAudit.escalation_id == row.id)
            .order_by(MobileSyncEventAudit.resolved_at.desc())
        ).first()

        items.append(
            EscalationHistoryItem(
                id=row.id,
                originating_user_id=row.originating_user_id,
                escalation_reason=row.escalation_reason,
                status=row.status,
                escalated_at=row.escalated_at,
                resolved_at=row.resolved_at,
                resolved_by_user_id=row.resolved_by_user_id,
                resolution_action=row.resolution_action,
                operation_type=conflict_event.operation_type
                if conflict_event
                else None,
                conflict_severity=conflict_event.conflict_severity
                if conflict_event
                else None,
                resolution_channel=audit_row.resolution_channel if audit_row else None,
            )
        )

    return EscalationHistoryResponse(
        items=items, total=total, offset=offset, limit=limit
    )


def _get_escalation_detail_impl(
    escalation_id: uuid.UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> EscalationDetailResponse:
    """Get escalation detail with nested conflict context."""
    escalation = db.exec(
        select(MobileSyncOwnerEscalation)
        .where(MobileSyncOwnerEscalation.id == escalation_id)
        .where(MobileSyncOwnerEscalation.tenant_id == user_context.tenant_id)
    ).first()

    if not escalation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Escalation not found",
        )

    # Load the originating conflict event
    conflict_event = db.exec(
        select(MobileSyncEvent).where(MobileSyncEvent.id == escalation.conflict_id)
    ).first()

    field_diffs = None
    tech_local_snapshot = None
    server_state_snapshot = None
    operation_type = None
    conflict_severity = None

    if conflict_event:
        operation_type = conflict_event.operation_type
        conflict_severity = conflict_event.conflict_severity
        tech_local_snapshot = conflict_event.operation_payload_summary
        field_diffs = compute_field_diffs(tech_local_snapshot, server_state_snapshot)

    # Audit log for resolution_channel
    audit_row = db.exec(
        select(MobileSyncEventAudit)
        .where(MobileSyncEventAudit.escalation_id == escalation_id)
        .order_by(MobileSyncEventAudit.resolved_at.desc())
    ).first()

    available = _get_available_resolutions(escalation)

    return EscalationDetailResponse(
        id=escalation.id,
        originating_user_id=escalation.originating_user_id,
        conflict_id=escalation.conflict_id,
        escalation_reason=escalation.escalation_reason,
        escalation_reason_explainer=escalation.escalation_reason_explainer,
        escalation_type=conflict_event.conflict_severity if conflict_event else None,
        status=escalation.status,
        escalated_at=escalation.escalated_at,
        resolved_by_user_id=escalation.resolved_by_user_id,
        resolved_at=escalation.resolved_at,
        resolution_action=escalation.resolution_action,
        resolution_payload=escalation.resolution_payload,
        resolution_channel=audit_row.resolution_channel if audit_row else None,
        operation_type=operation_type,
        conflict_severity=conflict_severity,
        tech_local_snapshot=tech_local_snapshot,
        server_state_snapshot=server_state_snapshot,
        field_diffs=field_diffs,
        available_resolutions=available,
    )


def _resolve_escalation_impl(
    escalation_id: uuid.UUID,
    data: EscalationResolveRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
    resolution_channel: str = "web",
) -> EscalationResolveResponse:
    """
    A48: Owner resolves an escalation with any of 7 resolution variants.
    Three distinct 409 shapes:
      - server_changed (staleness)
      - auto_recovered (already auto-resolved)
      - stale (tech data too old)
    """
    # A48: resolve via `resolution` field; B7b compat: fall back to `resolution_action`
    resolution = data.resolution or data.resolution_action
    if not resolution:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'resolution' is required",
        )

    if resolution not in A48_VALID_RESOLUTIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid resolution. Must be one of: {sorted(A48_VALID_RESOLUTIONS)}",
        )

    escalation = db.exec(
        select(MobileSyncOwnerEscalation)
        .where(MobileSyncOwnerEscalation.id == escalation_id)
        .where(MobileSyncOwnerEscalation.tenant_id == user_context.tenant_id)
    ).first()

    if not escalation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Escalation not found",
        )

    # A48: 409 shape 2 — auto_recovered
    if escalation.status == "auto_recovered":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "staleness_type": "auto_recovered",
                "auto_recovery_outcome": escalation.resolution_action,
                "message": "This conflict was auto-recovered before you acted. No further action is needed.",
            },
        )

    # A48: 409 shape 3 — stale (tech data discarded)
    if escalation.status == "stale":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "staleness_type": "stale",
                "tech_force_discarded": True,
                "message": "The tech's data is too old and has been discarded. No further action is needed.",
            },
        )

    if escalation.status not in ("pending",):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "stale_escalation",
                "message": f"Escalation is already in status: {escalation.status}",
                "refreshed_escalation": _get_escalation_detail_impl(
                    escalation_id, db, user_context
                ).model_dump(),
            },
        )

    # A48: 409 shape 1 — server_changed (staleness check)
    # Inline check instead of assert_not_stale() to avoid recursive detail fetch on mismatch
    expected_at = (
        data.expected_server_state_at_view_time or data.expected_escalation_updated_at
    )
    if expected_at is not None:
        expected_stripped = expected_at.replace(microsecond=0)
        actual_stripped = escalation.updated_at.replace(microsecond=0)
        if expected_stripped != actual_stripped:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "type": "https://pilotfortrades.com/errors/stale-state",
                    "staleness_type": "server_changed",
                    "title": "Escalation Updated",
                    "status": 409,
                    "detail": "This escalation was updated since you last viewed it. Please refresh and re-submit.",
                    "refreshed_escalation": {
                        "id": str(escalation_id),
                        "status": escalation.status,
                        "updated_at": escalation.updated_at.isoformat(),
                    },
                },
            )

    now = datetime.now(UTC)

    # Map B7b compat aliases to canonical A48 names for storage
    canonical_action = {
        "used_local": "use_tech",
        "rejected": "reject_unauthorized",
    }.get(resolution, resolution)

    escalation.status = (
        "resolved"
        if resolution != "reject_unauthorized" and resolution != "rejected"
        else "rejected"
    )
    escalation.resolved_by_user_id = user_context.id
    escalation.resolved_at = now
    escalation.resolution_action = canonical_action
    escalation.resolution_payload = data.resolution_payload

    db.add(escalation)

    # A48: Insert audit log row (append-only)
    audit_entry = MobileSyncEventAudit(
        tenant_id=user_context.tenant_id,
        escalation_id=escalation_id,
        originator_user_id=escalation.originating_user_id,
        resolver_user_id=user_context.id,
        resolution_action=canonical_action,
        resolution_channel=resolution_channel,
        post_commit_state={
            "status": escalation.status,
            "resolution_action": canonical_action,
        },
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(escalation)

    logger.info(
        "Escalation %s resolved by user %s with action %s (channel=%s)",
        escalation_id,
        user_context.id,
        canonical_action,
        resolution_channel,
    )

    # A48: Loop-closure push dispatch to originating tech
    notification_dispatched = False
    try:
        push_results = dispatch_loop_closure_push(
            db=db,
            tenant_id=user_context.tenant_id,
            originator_user_id=escalation.originating_user_id,
            escalation_id=escalation_id,
            resolution_action=canonical_action,
        )
        notification_dispatched = any(r.dispatched for r in push_results)
    except Exception as exc:
        logger.warning(
            "Loop-closure push failed for escalation %s: %s", escalation_id, exc
        )

    return EscalationResolveResponse(
        committed=True,
        resolution_outcome=canonical_action,
        post_commit_state={"status": escalation.status},
        originator_notification_dispatched=notification_dispatched,
        # B7b compat fields
        id=escalation.id,
        status=escalation.status,
        resolution_action=escalation.resolution_action,
        resolved_at=escalation.resolved_at,
        resolved_by_user_id=escalation.resolved_by_user_id,
    )


# ─────────────────────────────────────────────────────────────────────────────
# SHARED BUSINESS LOGIC — field-issues/summary (B1/BETA)
# ─────────────────────────────────────────────────────────────────────────────


def _get_field_issues_summary_impl(
    db: Session,
    user_context,  # AuthenticatedUser | TestUserContext
) -> FieldIssuesSummaryResponse:
    """Count pending owner escalations for this tenant.

    Uses mobile_sync_owner_escalation.status = 'pending'.
    Verified via MCP: status CHECK constraint allows 'pending'|'resolved'|'rejected'|'auto_recovered'|'stale'.
    """
    pending_count = db.exec(
        select(func.count(MobileSyncOwnerEscalation.id))
        .where(MobileSyncOwnerEscalation.tenant_id == user_context.tenant_id)
        .where(MobileSyncOwnerEscalation.status == "pending")
    ).one()
    return FieldIssuesSummaryResponse(pending_count=pending_count)


# ─────────────────────────────────────────────────────────────────────────────
# TEST endpoints (registered FIRST per §8.2)
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/mobile-sync-escalations/test",
    response_model=EscalationListResponse,
    summary="[TEST] List escalations (no JWT)",
)
def list_escalations_test(
    escalation_status: str = "pending",
    operation_type: str | None = None,
    sort: str = "-escalated_at",
    limit: int = 25,
    db: Session = Depends(get_db),
):
    test_context = get_test_context()
    return _list_escalations_impl(
        db,
        test_context,
        escalation_status=escalation_status,
        operation_type=operation_type,
        sort=sort,
        limit=limit,
    )


@router.get(
    "/mobile-sync-escalations/history/test",
    response_model=EscalationHistoryResponse,
    summary="[TEST] List escalation history (no JWT)",
)
def list_escalation_history_test(
    resolved_at_after: datetime | None = None,
    resolved_at_before: datetime | None = None,
    operation_type: str | None = None,
    limit: int = 25,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    test_context = get_test_context()
    return _list_escalation_history_impl(
        db,
        test_context,
        resolved_at_after=resolved_at_after,
        resolved_at_before=resolved_at_before,
        operation_type=operation_type,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/mobile-sync-escalations/{escalation_id}/test",
    response_model=EscalationDetailResponse,
    summary="[TEST] Get escalation detail (no JWT)",
)
def get_escalation_detail_test(
    escalation_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    test_context = get_test_context()
    return _get_escalation_detail_impl(escalation_id, db, test_context)


@router.get(
    "/field-issues/summary/test",
    response_model=FieldIssuesSummaryResponse,
    summary="[TEST] Pending field issues count (no JWT)",
)
def get_field_issues_summary_test(
    db: Session = Depends(get_db),
) -> FieldIssuesSummaryResponse:
    """Test endpoint — no auth required. Returns pending escalated field issue count."""
    test_context = get_test_context()
    return _get_field_issues_summary_impl(db, test_context)


@router.post(
    "/mobile-sync-escalations/{escalation_id}/resolve/test",
    response_model=EscalationResolveResponse,
    summary="[TEST] Resolve escalation (no JWT)",
)
def resolve_escalation_test(
    escalation_id: uuid.UUID,
    data: EscalationResolveRequest,
    db: Session = Depends(get_db),
):
    test_context = get_test_context()
    return _resolve_escalation_impl(
        escalation_id, data, db, test_context, resolution_channel="web"
    )


# ─────────────────────────────────────────────────────────────────────────────
# AUTHENTICATED endpoints
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/mobile-sync-escalations",
    response_model=EscalationListResponse,
    summary="List mobile sync owner escalations (A47)",
)
def list_escalations(
    escalation_status: str = "pending",
    operation_type: str | None = None,
    sort: str = "-escalated_at",
    cursor: str | None = None,
    limit: int = 25,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("field_issue.view")),
):
    """
    List owner escalations with A47 enhanced filtering.

    - status: pending | auto_recovered | stale | all
    - operation_type: filter by operation type
    - sort: -escalated_at | escalated_at
    """
    return _list_escalations_impl(
        db,
        current_user,
        escalation_status=escalation_status,
        operation_type=operation_type,
        sort=sort,
        cursor=cursor,
        limit=limit,
    )


@router.get(
    "/mobile-sync-escalations/history",
    response_model=EscalationHistoryResponse,
    summary="Historical archive of resolved escalations (A47)",
)
def list_escalation_history(
    resolved_at_after: datetime | None = None,
    resolved_at_before: datetime | None = None,
    operation_type: str | None = None,
    limit: int = 25,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("field_issue.view")),
):
    """A47: Historical archive of resolved escalations."""
    return _list_escalation_history_impl(
        db,
        current_user,
        resolved_at_after=resolved_at_after,
        resolved_at_before=resolved_at_before,
        operation_type=operation_type,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/mobile-sync-escalations/{escalation_id}",
    response_model=EscalationDetailResponse,
    summary="Get escalation detail (A47)",
)
def get_escalation_detail(
    escalation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("field_issue.view")),
):
    """Get full escalation detail including nested conflict context and available resolutions."""
    return _get_escalation_detail_impl(escalation_id, db, current_user)


@router.post(
    "/mobile-sync-escalations/{escalation_id}/resolve",
    response_model=EscalationResolveResponse,
    summary="Resolve an owner escalation (A48)",
)
def resolve_escalation(
    escalation_id: uuid.UUID,
    data: EscalationResolveRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("field_issue.resolve")
    ),
):
    """
    A48: Owner resolves a mobile sync conflict escalation.

    7 canonical resolution variants:
      use_tech | use_server | restore_and_accept | override_with_tech |
      discard_tech | accept_authorized_at_capture | reject_unauthorized

    Three distinct 409 shapes:
      - server_changed: staleness (another user already acted)
      - auto_recovered: conflict auto-resolved before owner acted
      - stale: tech data too old and discarded

    On success: inserts audit log, dispatches loop-closure push to originating tech.
    """
    set_audit_context_sync(db, current_user.id)
    return _resolve_escalation_impl(
        escalation_id, data, db, current_user, resolution_channel="web"
    )


@router.get(
    "/field-issues/summary",
    response_model=FieldIssuesSummaryResponse,
    summary="Pending field issues count for owner dashboard (BETA-B1)",
)
def get_field_issues_summary(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("field_issue.view")),
) -> FieldIssuesSummaryResponse:
    """Returns the count of pending escalated field issues awaiting owner resolution."""
    return _get_field_issues_summary_impl(db, current_user)
