"""
User Color API — B3/A18 Tech Color Assignment.

Endpoints:
  PATCH /api/v1/users/{user_id}/color  — owner/admin sets a tech's display color

Permission: users.update (owner/admin only; tech cannot set their own color)

Follows dual-endpoint architecture (§8.2): authenticated + test variants.
RFC 7807 error format for 422/404.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlmodel import Session, select

from app.models.core import User
from core.auth import AuthenticatedUser
from core.db import get_db, set_audit_context_sync
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context
from services.tech_color_service import is_valid_hex_color

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== REQUEST / RESPONSE SCHEMAS ====================


class UserColorPatch(BaseModel):
    """Request body for PATCH /api/v1/users/{user_id}/color"""

    display_color: str

    @field_validator("display_color")
    @classmethod
    def validate_hex_color(cls, v: str) -> str:
        if not is_valid_hex_color(v):
            raise ValueError(
                "display_color must be a 6-digit hex color string (e.g. #3B43D6)"
            )
        return v.upper()  # normalize to uppercase


class UserColorResponse(BaseModel):
    """Response for PATCH /api/v1/users/{user_id}/color"""

    user_id: str
    display_color: str
    updated_at: str


# ==================== SHARED BUSINESS LOGIC ====================


def _patch_user_color_impl(
    user_id: UUID,
    patch: UserColorPatch,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> UserColorResponse:
    """Shared logic — accepts both AuthenticatedUser and TestUserContext.

    Tenant-scoped lookup via TenantUser join to prevent IDOR (§16.3).
    """
    from app.models.auth import TenantUser

    # Tenant-scoped load — IDOR-safe (§16.3)
    user = db.exec(
        select(User)
        .join(TenantUser, TenantUser.user_id == User.id)
        .where(User.id == user_id)
        .where(TenantUser.tenant_id == user_context.tenant_id)
        .where(TenantUser.is_active == True)
        .where(User.is_active == True)
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://pilotfortrades.com/errors/not-found",
                "title": "User Not Found",
                "status": 404,
                "detail": f"User {user_id} not found in this tenant.",
            },
        )

    set_audit_context_sync(db, user_context.id)
    user.display_color = patch.display_color
    db.add(user)
    db.commit()
    db.refresh(user)

    updated_at = (
        user.updated_at.isoformat()
        if user.updated_at
        else datetime.now(UTC).isoformat()
    )

    return UserColorResponse(
        user_id=str(user.id),
        display_color=user.display_color,
        updated_at=updated_at,
    )


# ==================== TEST ENDPOINTS (register FIRST) ====================


@router.patch(
    "/test/{user_id}/color",
    response_model=UserColorResponse,
    status_code=status.HTTP_200_OK,
    summary="[TEST] Set user display color — no auth required",
)
def patch_user_color_test(
    user_id: UUID,
    patch: UserColorPatch,
    db: Session = Depends(get_db),
) -> UserColorResponse:
    """Test endpoint — no auth required. Blocked in staging/production."""
    test_context = get_test_context()
    return _patch_user_color_impl(user_id, patch, db, test_context)


# ==================== AUTHENTICATED ENDPOINTS ====================


@router.patch(
    "/{user_id}/color",
    response_model=UserColorResponse,
    status_code=status.HTTP_200_OK,
    summary="Set user display color for dispatch board",
)
def patch_user_color(
    user_id: UUID,
    patch: UserColorPatch,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("users.update")),
) -> UserColorResponse:
    """Owner/admin sets a tech's display color (hex, e.g. #3B43D6).

    Permission: users.update — tech cannot set their own color.
    """
    return _patch_user_color_impl(user_id, patch, db, current_user)
