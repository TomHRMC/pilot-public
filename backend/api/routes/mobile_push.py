"""
api/routes/mobile_push.py

B8/A51: Background Sync Infrastructure — Push token registry + sync session telemetry.

Endpoints:
    POST   /api/v1/mobile/push-tokens                           Register/refresh push token
    DELETE /api/v1/mobile/push-tokens/{device_id}               Revoke push token
    POST   /api/v1/mobile/sync-sessions/{session_id}/complete   Report sync session completion

Auth: Any authenticated user (no explicit permission — implicit by valid JWT).
Tenant isolation: All operations are scoped to current_user.tenant_id + current_user.id.
"""

import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session, select

from app.models.sync import MobileSyncSession
from core.auth import AuthenticatedUser, get_current_user
from core.db import get_db
from core.test_context import TestUserContext, get_test_context
from services.mobile_background_sync import (
    register_or_refresh_push_token,
    revoke_push_token,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────────────


class PushTokenRegisterRequest(BaseModel):
    """POST /push-tokens request body."""

    device_id: uuid.UUID
    platform: str  # 'ios' | 'android'
    push_token: str = Field(
        ..., min_length=1
    )  # MOB-B8: empty token rejected at schema level
    app_version: str | None = None
    os_version: str | None = None
    notification_permission_granted: bool = True


class PushTokenRegisterResponse(BaseModel):
    """POST /push-tokens response body."""

    model_config = ConfigDict(from_attributes=True)

    device_id: uuid.UUID
    registered_at: datetime
    last_seen_at: datetime


class SyncSessionCompleteRequest(BaseModel):
    """POST /sync-sessions/{id}/complete request body."""

    outcome: str  # 'success' | 'partial' | 'failed' | 'throttled'
    items_attempted: int = 0
    items_committed: int = 0
    items_deferred: int = 0
    items_failed: int = 0
    failure_reason: str | None = None


class SyncSessionCompleteResponse(BaseModel):
    """POST /sync-sessions/{id}/complete response body."""

    model_config = ConfigDict(from_attributes=True)

    session_id: uuid.UUID
    outcome: str | None
    completed_at: datetime | None


# ─────────────────────────────────────────────────────────────────────────────
# Shared implementation
# ─────────────────────────────────────────────────────────────────────────────


def _register_push_token_impl(
    data: PushTokenRegisterRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> PushTokenRegisterResponse:
    """Register or refresh a push token for the current user's device."""
    if data.platform not in ("ios", "android"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid platform '{data.platform}'. Valid values: ios, android",
        )

    token_row = register_or_refresh_push_token(
        db=db,
        tenant_id=user_context.tenant_id,
        user_id=user_context.id,
        device_id=data.device_id,
        platform=data.platform,
        push_token=data.push_token,
        app_version=data.app_version,
        os_version=data.os_version,
        notification_permission_granted=data.notification_permission_granted,
    )

    return PushTokenRegisterResponse(
        device_id=token_row.device_id,
        registered_at=token_row.registered_at,
        last_seen_at=token_row.last_seen_at,
    )


def _revoke_push_token_impl(
    device_id: uuid.UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> None:
    """Revoke a device push token for the current user."""
    found = revoke_push_token(db=db, user_id=user_context.id, device_id=device_id)
    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Push token not found",
        )


def _complete_sync_session_impl(
    session_id: uuid.UUID,
    data: SyncSessionCompleteRequest,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> SyncSessionCompleteResponse:
    """Mark a sync session as complete with telemetry."""
    valid_outcomes = {"success", "partial", "failed", "throttled"}
    if data.outcome not in valid_outcomes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid outcome '{data.outcome}'. Valid values: {sorted(valid_outcomes)}",
        )

    # Find existing session — create if not found (client may POST completion without prior session)
    session_row = db.exec(
        # FIND-169: session_id → id on MobileSyncSession
        select(MobileSyncSession)
        .where(MobileSyncSession.id == session_id)
        .where(MobileSyncSession.tenant_id == user_context.tenant_id)
        .where(MobileSyncSession.user_id == user_context.id)
    ).first()

    now = datetime.now(UTC)

    if session_row is None:
        # Client reporting a session the server didn't initiate (OS-scheduled foreground)
        # FIND-169: session_id → id on MobileSyncSession
        session_row = MobileSyncSession(
            id=session_id,
            tenant_id=user_context.tenant_id,
            user_id=user_context.id,
            device_id=uuid.UUID(
                "00000000-0000-0000-0000-000000000000"
            ),  # Unknown device
            triggered_by="foreground",
            started_at=now,
        )

    session_row.outcome = data.outcome
    session_row.items_attempted = data.items_attempted
    session_row.items_committed = data.items_committed
    session_row.items_deferred = data.items_deferred
    session_row.items_failed = data.items_failed
    session_row.failure_reason = data.failure_reason
    session_row.completed_at = now

    db.add(session_row)
    db.commit()
    db.refresh(session_row)

    # FIND-169: session_id → id on MobileSyncSession
    return SyncSessionCompleteResponse(
        session_id=session_row.id,
        outcome=session_row.outcome,
        completed_at=session_row.completed_at,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test endpoints (register BEFORE authenticated endpoints)
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/push-tokens/test",
    response_model=PushTokenRegisterResponse,
    status_code=status.HTTP_200_OK,
    summary="[Test] Register push token",
)
def register_push_token_test(
    data: PushTokenRegisterRequest,
    db: Session = Depends(get_db),
):
    """Test endpoint — no auth required. Blocked in staging/production."""
    test_context = get_test_context()
    return _register_push_token_impl(data, db, test_context)


@router.delete(
    "/push-tokens/{device_id}/test",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="[Test] Revoke push token",
)
def revoke_push_token_test(
    device_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Test endpoint — no auth required. Blocked in staging/production."""
    test_context = get_test_context()
    _revoke_push_token_impl(device_id, db, test_context)


@router.post(
    "/sync-sessions/{session_id}/complete/test",
    response_model=SyncSessionCompleteResponse,
    status_code=status.HTTP_200_OK,
    summary="[Test] Complete sync session",
)
def complete_sync_session_test(
    session_id: uuid.UUID,
    data: SyncSessionCompleteRequest,
    db: Session = Depends(get_db),
):
    """Test endpoint — no auth required. Blocked in staging/production."""
    test_context = get_test_context()
    return _complete_sync_session_impl(session_id, data, db, test_context)


# ─────────────────────────────────────────────────────────────────────────────
# Authenticated endpoints
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/push-tokens",
    response_model=PushTokenRegisterResponse,
    status_code=status.HTTP_200_OK,
    summary="Register or refresh a device push token",
)
def register_push_token(
    data: PushTokenRegisterRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Register or refresh a push token for the calling user's device.

    Idempotent — upserts on (tenant_id, user_id, device_id).
    Called on every app launch. On token change, updates the stored token
    and clears revoked_at. On same token, updates last_seen_at only.
    """
    return _register_push_token_impl(data, db, current_user)


@router.delete(
    "/push-tokens/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a device push token",
)
def revoke_push_token_endpoint(
    device_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Revoke a push token for the calling user's device.

    Called on logout or explicit token invalidation.
    Returns 204 on success, 404 if (user_id, device_id) not found.
    """
    _revoke_push_token_impl(device_id, db, current_user)


@router.post(
    "/sync-sessions/{session_id}/complete",
    response_model=SyncSessionCompleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Report sync session completion telemetry",
)
def complete_sync_session(
    session_id: uuid.UUID,
    data: SyncSessionCompleteRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Client reports background sync session telemetry on completion.

    Only the user who owns the session can report on it (tenant + user scoped).
    Creates the session row if it doesn't exist (OS-scheduled foreground syncs
    may not have a server-side row yet).
    """
    return _complete_sync_session_impl(session_id, data, db, current_user)
