"""
Notification SSE Stream + In-App Notification Endpoints — B10/A57

GET    /sse/notifications                — SSE stream of in_app_notification events
POST   /api/v1/notifications/in-app/mark-read   — mark notification(s) as read
GET    /api/v1/notifications/in-app/recent      — bell panel (last 50 unread/recent)

SSE pattern per §18 of pilot-python-engineer-methods.md.
Channel key: (tenant_id, user_id) — user-scoped (not tenant-scoped like dispatch board).
"""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from app.models.system import InAppNotification
from core.auth import AuthenticatedUser
from core.db import get_db
from core.permissions import require_permission

router = APIRouter()
logger = logging.getLogger(__name__)

# ─── SSE Channel Registry ─────────────────────────────────────────────────────
# Channel key: (tenant_id, user_id) → set of asyncio.Queue
# One queue per connected session per user. In production, back by Redis Pub/Sub
# for multi-instance; in MVP/B10, in-process queue (same as dispatch board).
_sse_notification_channels: dict[tuple[str, str], set[asyncio.Queue]] = {}


def emit_to_user(tenant_id: str, user_id: str, event_type: str, payload: dict) -> None:
    """
    Broadcast an SSE event to all connections for a specific user within a tenant.

    Called from the dispatcher (A58) AFTER db.commit() — never before.
    Per §18.4 anti-pattern: always emit AFTER commit succeeds.

    Args:
        tenant_id:  Tenant scope (events never cross tenant boundaries).
        user_id:    Target user_id.
        event_type: e.g., 'in_app_notification'.
        payload:    Event-specific data dict.
    """
    channel_key = (str(tenant_id), str(user_id))
    event = {"type": event_type, **payload}
    queues = _sse_notification_channels.get(channel_key, set())

    for queue in list(queues):
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning(
                f"SSE queue full for tenant={tenant_id} user={user_id}, dropping event"
            )


async def _notification_event_generator(
    request: Request,
    tenant_id: str,
    user_id: str,
) -> AsyncGenerator[str, None]:
    """Generate SSE events for a user's notification stream."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    channel_key = (tenant_id, user_id)

    if channel_key not in _sse_notification_channels:
        _sse_notification_channels[channel_key] = set()
    _sse_notification_channels[channel_key].add(queue)

    try:
        while True:
            if await request.is_disconnected():
                break

            try:
                event = await asyncio.wait_for(queue.get(), timeout=15.0)
                yield f"data: {json.dumps(event)}\n\n"
            except TimeoutError:
                # Heartbeat to keep connection alive through proxies
                yield ": heartbeat\n\n"

    finally:
        _sse_notification_channels.get(channel_key, set()).discard(queue)
        if not _sse_notification_channels.get(channel_key):
            _sse_notification_channels.pop(channel_key, None)


# ─── SSE Endpoint ────────────────────────────────────────────────────────────


@router.get(
    "/sse/notifications",
    response_class=StreamingResponse,
    summary="SSE stream for in-app notifications (user-scoped)",
    tags=["notifications"],
)
async def notification_sse_stream(
    request: Request,
    token: str | None = Query(
        None, description="JWT token for SSE clients that cannot set headers"
    ),
    current_user: AuthenticatedUser = Depends(
        require_permission("notification_preference.user_override.edit")
    ),
):
    """
    Server-Sent Events endpoint for in-app notifications.

    Authenticated via JWT in Authorization header, or via ?token= query param
    for SSE clients that cannot set custom headers (token discarded after auth).

    Emits in_app_notification rows in real-time when the dispatcher writes them.
    """
    return StreamingResponse(
        _notification_event_generator(
            request,
            str(current_user.tenant_id),
            str(current_user.id),
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ─── In-App Notification Endpoints ───────────────────────────────────────────


class MarkReadRequest(BaseModel):
    notification_ids: list[UUID]


def _mark_read_impl(
    notification_ids: list[UUID],
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
) -> dict[str, Any]:
    """Set read_at = now() on each in_app_notification owned by this user."""
    now = datetime.now(UTC)
    marked_count = 0

    for nid in notification_ids:
        notif = db.exec(
            # FIND-169: notification_id → id
            select(InAppNotification).where(
                InAppNotification.id == nid,
                InAppNotification.tenant_id == tenant_id,
                InAppNotification.user_id == user_id,
                InAppNotification.read_at == None,
            )
        ).first()
        if notif:
            notif.read_at = now
            db.add(notif)
            marked_count += 1

    if marked_count > 0:
        db.commit()

    return {"marked_count": marked_count}


def _get_recent_impl(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    limit: int = 50,
) -> dict[str, Any]:
    """Return up to `limit` recent in-app notifications with unread count."""
    notifications = db.exec(
        select(InAppNotification)
        .where(
            InAppNotification.tenant_id == tenant_id,
            InAppNotification.user_id == user_id,
        )
        .order_by(InAppNotification.created_at.desc())
        .limit(limit)
    ).all()

    unread_count = db.exec(
        select(InAppNotification).where(
            InAppNotification.tenant_id == tenant_id,
            InAppNotification.user_id == user_id,
            InAppNotification.read_at == None,
        )
    )
    unread_count_val = len(list(unread_count))

    return {
        "notifications": [
            {
                # FIND-169: notification_id → id on InAppNotification
                "notification_id": str(n.id),
                "category_id": n.category_id,
                "body": n.body,
                "deep_link_target": n.deep_link_target,
                "priority": n.priority,
                "created_at": n.created_at.isoformat(),
                "read_at": n.read_at.isoformat() if n.read_at else None,
            }
            for n in notifications
        ],
        "unread_count": unread_count_val,
    }


# Test endpoints (registered FIRST per §8.2)


@router.post("/test/in-app/mark-read")
def mark_read_test(
    data: MarkReadRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    test_context = get_test_context()
    return _mark_read_impl(
        data.notification_ids, db, test_context.tenant_id, test_context.id
    )


@router.get("/test/in-app/recent")
def get_recent_test(
    limit: int = Query(50, le=50, ge=1),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    from core.test_context import get_test_context

    test_context = get_test_context()
    return _get_recent_impl(db, test_context.tenant_id, test_context.id, limit)


# Authenticated endpoints


@router.post("/in-app/mark-read")
def mark_read(
    data: MarkReadRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("notification_preference.user_override.edit")
    ),
) -> dict[str, Any]:
    """Mark one or more in-app notifications as read."""
    return _mark_read_impl(
        data.notification_ids, db, current_user.tenant_id, current_user.id
    )


@router.get("/in-app/recent")
def get_recent(
    limit: int = Query(50, le=50, ge=1),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("notification_preference.user_override.edit")
    ),
) -> dict[str, Any]:
    """Return recent in-app notifications for the bell panel (max 50)."""
    return _get_recent_impl(db, current_user.tenant_id, current_user.id, limit)


# Fix missing import at top of file
from core.test_context import get_test_context  # noqa: E402
