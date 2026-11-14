"""
B15/A79 — Unified Pending-Count Exposure

GET /api/v1/sync/{surface}/status
  Auth: JWT required; RBAC: settings.view

Returns a unified sync-status payload for the four supported surfaces:
  calendar   → calendar_sync_conflict (unresolved rows)
  quickbooks → integration_sync_conflict (pending rows)
  mobile_data / background → mobile_sync_session (last session)

SSE event sync_status_changed is emitted by write-path endpoints
(calendar/QB conflict resolution routes, mobile sync session creation).
The emit helper emit_sync_status_changed() is defined here and imported
by those write-path endpoints.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select

from app.models.scheduling import CalendarSyncConflict
from app.models.system import IntegrationSyncConflict
from core.auth import AuthenticatedUser
from core.db import get_db
from core.permissions import require_permission

logger = logging.getLogger(__name__)

router = APIRouter()

# ─────────────────────────────────────────────────────────────────────────────
# SSE channel registry  (tenant_id → set of asyncio.Queue)
# ─────────────────────────────────────────────────────────────────────────────
_sync_sse_channels: dict[str, set[asyncio.Queue]] = {}

ALLOWED_SURFACES = {"calendar", "quickbooks", "mobile_data", "background"}


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic schemas
# ─────────────────────────────────────────────────────────────────────────────


class PendingItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: str
    label: str


class SyncStatusResponse(BaseModel):
    surface: str
    state: str  # synced_pending | syncing | sync_error | sync_paused | synced_idle
    pending_count: int
    pending_items: list[PendingItem]
    last_sync_at: datetime | None
    next_sync_at: datetime | None
    manual_trigger_supported: bool
    resolve_target: str | None
    amber_threshold: int


# ─────────────────────────────────────────────────────────────────────────────
# Internal aggregation helpers
# ─────────────────────────────────────────────────────────────────────────────


def _get_calendar_status(
    db: Session, tenant_id: UUID, amber_threshold: int
) -> dict[str, Any]:
    """Count unresolved calendar_sync_conflict rows; derive state."""

    conflicts = db.exec(
        select(CalendarSyncConflict)
        .where(CalendarSyncConflict.tenant_id == tenant_id)
        .where(CalendarSyncConflict.resolved_at == None)
        .limit(6)  # cap at 6 so we can detect > 5 without full scan
    ).all()

    pending_count = len(conflicts)
    items = [
        PendingItem(
            type=c.conflict_type or "conflict",
            label=f"Conflict #{str(c.id)[:8]} — {c.conflict_type or 'calendar conflict'}",
        )
        for c in conflicts[:5]
    ]

    if pending_count == 0:
        state = "synced_idle"
    elif pending_count >= amber_threshold:
        state = "synced_pending"
    else:
        state = "synced_pending"

    return {
        "state": state,
        "pending_count": pending_count,
        "pending_items": items,
        "last_sync_at": None,
        "next_sync_at": None,
        "manual_trigger_supported": False,
        "resolve_target": "/api/v1/calendar/conflicts",
    }


def _get_quickbooks_status(
    db: Session, tenant_id: UUID, amber_threshold: int
) -> dict[str, Any]:
    """Count pending integration_sync_conflict rows for quickbooks surface."""

    conflicts = db.exec(
        select(IntegrationSyncConflict)
        .where(IntegrationSyncConflict.tenant_id == tenant_id)
        .where(IntegrationSyncConflict.status == "pending")
        .limit(6)
    ).all()

    pending_count = len(conflicts)
    items = [
        PendingItem(
            type=c.entity_type_code or "conflict",
            label=f"{c.entity_type_code or 'QB'} conflict #{str(c.id)[:8]}",
        )
        for c in conflicts[:5]
    ]

    if pending_count == 0:
        state = "synced_idle"
    else:
        state = "synced_pending"

    return {
        "state": state,
        "pending_count": pending_count,
        "pending_items": items,
        "last_sync_at": None,
        "next_sync_at": None,
        "manual_trigger_supported": True,
        "resolve_target": "/api/v1/qb/conflicts",
    }


def _get_mobile_status(db: Session, tenant_id: UUID, surface: str) -> dict[str, Any]:
    """Derive state from the most recent mobile_sync_session for this tenant."""
    # Import here to avoid circular refs
    from sqlalchemy import text as sa_text

    # FIND-169: session_id → id on mobile_sync_session
    row = db.exec(
        sa_text(
            "SELECT id AS session_id, outcome, items_deferred, items_failed, "
            "started_at, completed_at "
            "FROM mobile_sync_session "
            "WHERE tenant_id = :tid "
            "ORDER BY started_at DESC LIMIT 1"
        ).bindparams(tid=str(tenant_id))
    ).first()

    if row is None:
        return {
            "state": "synced_idle",
            "pending_count": 0,
            "pending_items": [],
            "last_sync_at": None,
            "next_sync_at": None,
            "manual_trigger_supported": True,
            "resolve_target": None,
        }

    # Derive state from session outcome
    outcome = row.outcome
    items_deferred = row.items_deferred or 0
    items_failed = row.items_failed or 0
    pending_count = items_deferred + items_failed

    if outcome == "failed" or items_failed > 0:
        state = "sync_error"
    elif items_deferred > 0:
        state = "synced_pending"
    elif outcome == "completed":
        state = "synced_idle"
    else:
        state = "syncing"

    return {
        "state": state,
        "pending_count": pending_count,
        "pending_items": [],  # mobile items are opaque — no label available
        "last_sync_at": row.completed_at or row.started_at,
        "next_sync_at": None,
        "manual_trigger_supported": True,
        "resolve_target": None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Shared implementation
# ─────────────────────────────────────────────────────────────────────────────


def _get_sync_status_impl(
    surface: str,
    db: Session,
    tenant_id: UUID,
) -> SyncStatusResponse:
    if surface not in ALLOWED_SURFACES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid surface '{surface}'. Allowed: {sorted(ALLOWED_SURFACES)}",
        )

    # Resolve amber threshold from platform_setting (post-FIND-086)
    from services.setting_resolver import get_effective_setting

    amber_val, _ = get_effective_setting(
        db, tenant_id, "tenant_sync_indicator_pending_amber_threshold", fallback=5
    )
    amber_threshold: int = int(amber_val)

    if surface == "calendar":
        data = _get_calendar_status(db, tenant_id, amber_threshold)
    elif surface == "quickbooks":
        data = _get_quickbooks_status(db, tenant_id, amber_threshold)
    else:  # mobile_data | background
        data = _get_mobile_status(db, tenant_id, surface)

    return SyncStatusResponse(
        surface=surface,
        amber_threshold=amber_threshold,
        **data,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test endpoint (register FIRST to avoid /{surface} matching /test)
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/test/{surface}/status",
    response_model=SyncStatusResponse,
    summary="[TEST] Sync status — no auth required",
)
def get_sync_status_test(
    surface: str,
    db: Session = Depends(get_db),
):
    """Test endpoint — no auth required. Blocked in staging/production."""
    from core.test_context import get_test_context

    ctx = get_test_context()
    return _get_sync_status_impl(surface, db, ctx.tenant_id)


# ─────────────────────────────────────────────────────────────────────────────
# Authenticated endpoint
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/{surface}/status",
    response_model=SyncStatusResponse,
    summary="Unified sync-surface status",
)
def get_sync_status(
    surface: str,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("settings.view")),
):
    """
    Return the pending-count and state for a named sync surface.

    Path parameter ``surface``: calendar | quickbooks | mobile_data | background
    """
    return _get_sync_status_impl(surface, db, current_user.tenant_id)


# ─────────────────────────────────────────────────────────────────────────────
# SSE helper — called by write-path endpoints to broadcast state changes
# ─────────────────────────────────────────────────────────────────────────────


def emit_sync_status_changed(
    tenant_id: str, surface: str, state: str, pending_count: int
) -> None:
    """
    Broadcast a sync_status_changed SSE event to all connected clients for a tenant.

    Called from write-path endpoints after committing changes (never before commit).

    Args:
        tenant_id: Target tenant UUID as string.
        surface: The surface whose state changed.
        state: New state string.
        pending_count: Updated pending item count.
    """
    event = {
        "event": "sync_status_changed",
        "data": {"surface": surface, "state": state, "pending_count": pending_count},
    }
    channels = _sync_sse_channels.get(str(tenant_id), set())
    for queue in list(channels):
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning(
                f"SSE queue full for tenant {tenant_id} surface {surface}, dropping event"
            )
