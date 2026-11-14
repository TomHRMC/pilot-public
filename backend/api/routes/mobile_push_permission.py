"""
B14/A78 — Mobile Push Permission State routes.
PUT /api/v1/users/me/devices/{device_id}/push-permission
GET /api/v1/users/me/devices/{device_id}/push-permission
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select

from app.models.mobile_push_permission import MobilePushPermissionState
from core.auth import AuthenticatedUser
from core.db import get_db, set_audit_context_sync
from core.permissions import require_permission
from core.test_context import get_test_context

router = APIRouter()

VALID_STATES = {
    "not_asked",
    "granted",
    "denied_by_user_choice",
    "denied_by_os",
    "revoked_in_settings",
}
BANNER_REAPPEAR_DAYS = 7


# ==================== SCHEMAS ====================


class PushPermissionUpdateRequest(BaseModel):
    permission_state: str


class PushPermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    device_id: UUID
    permission_state: str
    last_state_change_at: str
    dismissable_banner_dismissed_at: str | None
    banner_should_appear: bool


# ==================== SHARED LOGIC ====================


def _compute_banner_should_appear(record: MobilePushPermissionState) -> bool:
    """
    banner_should_appear = True when:
    - permission_state in (denied_by_user_choice, denied_by_os, revoked_in_settings)
    - AND (dismissable_banner_dismissed_at IS NULL
           OR dismissable_banner_dismissed_at < now() - 7 days)
    """
    denied_states = {"denied_by_user_choice", "denied_by_os", "revoked_in_settings"}
    if record.permission_state not in denied_states:
        return False

    if record.dismissable_banner_dismissed_at is None:
        return True

    cutoff = datetime.now(UTC) - timedelta(days=BANNER_REAPPEAR_DAYS)
    return record.dismissable_banner_dismissed_at < cutoff


def _upsert_permission_impl(
    tenant_id: UUID,
    user_id: UUID,
    device_id: UUID,
    permission_state: str,
    db: Session,
) -> PushPermissionResponse:
    """Upsert mobile push permission state for a device."""
    if permission_state not in VALID_STATES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid permission_state. Must be one of: {sorted(VALID_STATES)}",
        )

    now = datetime.now(UTC)

    existing = db.exec(
        select(MobilePushPermissionState)
        .where(MobilePushPermissionState.tenant_id == tenant_id)
        .where(MobilePushPermissionState.user_id == user_id)
        .where(MobilePushPermissionState.device_id == device_id)
    ).first()

    if existing:
        existing.permission_state = permission_state
        existing.last_state_change_at = now
        db.add(existing)
        db.commit()
        db.refresh(existing)
        record = existing
    else:
        record = MobilePushPermissionState(
            tenant_id=tenant_id,
            user_id=user_id,
            device_id=device_id,
            permission_state=permission_state,
            last_state_change_at=now,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

    return PushPermissionResponse(
        device_id=record.device_id,
        permission_state=record.permission_state,
        last_state_change_at=record.last_state_change_at.isoformat(),
        dismissable_banner_dismissed_at=(
            record.dismissable_banner_dismissed_at.isoformat()
            if record.dismissable_banner_dismissed_at
            else None
        ),
        banner_should_appear=_compute_banner_should_appear(record),
    )


def _get_permission_impl(
    tenant_id: UUID,
    user_id: UUID,
    device_id: UUID,
    db: Session,
) -> PushPermissionResponse:
    """Get mobile push permission state for a device."""
    record = db.exec(
        select(MobilePushPermissionState)
        .where(MobilePushPermissionState.tenant_id == tenant_id)
        .where(MobilePushPermissionState.user_id == user_id)
        .where(MobilePushPermissionState.device_id == device_id)
    ).first()

    if not record:
        # Return default not_asked state if not found
        from datetime import UTC, datetime

        fake = MobilePushPermissionState(
            tenant_id=tenant_id,
            user_id=user_id,
            device_id=device_id,
            permission_state="not_asked",
            last_state_change_at=datetime.now(UTC),
        )
        return PushPermissionResponse(
            device_id=device_id,
            permission_state="not_asked",
            last_state_change_at=fake.last_state_change_at.isoformat(),
            dismissable_banner_dismissed_at=None,
            banner_should_appear=False,
        )

    return PushPermissionResponse(
        device_id=record.device_id,
        permission_state=record.permission_state,
        last_state_change_at=record.last_state_change_at.isoformat(),
        dismissable_banner_dismissed_at=(
            record.dismissable_banner_dismissed_at.isoformat()
            if record.dismissable_banner_dismissed_at
            else None
        ),
        banner_should_appear=_compute_banner_should_appear(record),
    )


# ==================== TEST ENDPOINTS ====================


@router.put(
    "/test/devices/{device_id}/push-permission",
    response_model=PushPermissionResponse,
    status_code=status.HTTP_200_OK,
)
def update_push_permission_test(
    device_id: UUID,
    payload: PushPermissionUpdateRequest,
    db: Session = Depends(get_db),
):
    test_ctx = get_test_context()
    return _upsert_permission_impl(
        tenant_id=test_ctx.tenant_id,
        user_id=test_ctx.id,
        device_id=device_id,
        permission_state=payload.permission_state,
        db=db,
    )


@router.get(
    "/test/devices/{device_id}/push-permission",
    response_model=PushPermissionResponse,
    status_code=status.HTTP_200_OK,
)
def get_push_permission_test(device_id: UUID, db: Session = Depends(get_db)):
    test_ctx = get_test_context()
    return _get_permission_impl(
        tenant_id=test_ctx.tenant_id,
        user_id=test_ctx.id,
        device_id=device_id,
        db=db,
    )


# ==================== AUTHENTICATED ENDPOINTS ====================


@router.put(
    "/me/devices/{device_id}/push-permission",
    response_model=PushPermissionResponse,
    status_code=status.HTTP_200_OK,
)
def update_push_permission(
    device_id: UUID,
    payload: PushPermissionUpdateRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("mobile_push_permission.update")
    ),
):
    """Update mobile push permission state for own device."""
    set_audit_context_sync(db, current_user.id)
    return _upsert_permission_impl(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        device_id=device_id,
        permission_state=payload.permission_state,
        db=db,
    )


@router.get(
    "/me/devices/{device_id}/push-permission",
    response_model=PushPermissionResponse,
    status_code=status.HTTP_200_OK,
)
def get_push_permission(
    device_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("mobile_push_permission.update")
    ),
):
    """Get mobile push permission state for own device."""
    return _get_permission_impl(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        device_id=device_id,
        db=db,
    )
