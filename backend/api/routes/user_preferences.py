"""
User Preferences API — A7 Field Mode Backend Support (B2).

Endpoint:
  PATCH /api/v1/users/me/preferences  — update user preferences (incl. field_mode_enabled)

field_mode_enabled is stored in user_preference.preferences JSONB (no migration needed).
Decision: F.3 of batch-b2-design.md — JSONB storage avoids touching the user table.

Follows dual-endpoint architecture (§8.2): authenticated + test variants.
"""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select

from app.models.core import UserPreference
from core.auth import AuthenticatedUser
from core.db import get_db
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context

router = APIRouter()


# ==================== REQUEST / RESPONSE SCHEMAS ====================


class UserPreferencePatch(BaseModel):
    """Request body for PATCH /api/v1/users/me/preferences"""

    field_mode_enabled: bool | None = None
    # Additional preferences can be added here in future batches


class UserPreferenceResponse(BaseModel):
    """Response for PATCH /api/v1/users/me/preferences"""

    user_id: str
    tenant_id: str
    preferences: dict[str, Any]
    updated_at: str


# ==================== SHARED BUSINESS LOGIC ====================


def _update_preferences_impl(
    patch: UserPreferencePatch,
    user_context: AuthenticatedUser | TestUserContext,
    db: Session,
) -> UserPreferenceResponse:
    """
    Shared logic for PATCH /users/me/preferences.

    Reads existing UserPreference row for this user+tenant, merges the patch
    into the JSONB preferences dict, and upserts. Creates a new row if none exists.
    """
    # Look up existing preference record (user + tenant scoped)
    pref = db.exec(
        select(UserPreference)
        .where(UserPreference.user_id == user_context.id)
        .where(UserPreference.tenant_id == user_context.tenant_id)
    ).first()

    if pref is None:
        # Create new preferences record
        pref = UserPreference(
            user_id=user_context.id,
            tenant_id=user_context.tenant_id,
            preferences={},
            created_by=user_context.id,
            updated_by=user_context.id,
        )
        db.add(pref)
        db.flush()

    # Merge patch fields into preferences JSONB
    current_prefs: dict[str, Any] = dict(pref.preferences or {})

    if patch.field_mode_enabled is not None:
        current_prefs["field_mode_enabled"] = patch.field_mode_enabled

    pref.preferences = current_prefs
    pref.updated_by = user_context.id
    db.add(pref)
    db.commit()
    db.refresh(pref)

    return UserPreferenceResponse(
        user_id=str(user_context.id),
        tenant_id=str(user_context.tenant_id),
        preferences=pref.preferences,
        updated_at=pref.updated_at.isoformat(),
    )


def _get_preferences_impl(
    user_context: AuthenticatedUser | TestUserContext,
    db: Session,
) -> UserPreferenceResponse:
    """
    Shared logic for GET /users/me/preferences.
    """
    pref = db.exec(
        select(UserPreference)
        .where(UserPreference.user_id == user_context.id)
        .where(UserPreference.tenant_id == user_context.tenant_id)
    ).first()

    preferences = pref.preferences if pref else {}
    updated_at = pref.updated_at.isoformat() if pref else "N/A"

    return UserPreferenceResponse(
        user_id=str(user_context.id),
        tenant_id=str(user_context.tenant_id),
        preferences=preferences,
        updated_at=updated_at,
    )


# ==================== TEST ENDPOINTS (register FIRST) ====================


@router.patch("/me/preferences/test", response_model=UserPreferenceResponse)
def update_preferences_test(
    patch: UserPreferencePatch,
    db: Session = Depends(get_db),
):
    """Test endpoint — update user preferences (field_mode_enabled etc.)."""
    test_context = get_test_context()
    return _update_preferences_impl(patch, test_context, db)


@router.get("/me/preferences/test", response_model=UserPreferenceResponse)
def get_preferences_test(
    db: Session = Depends(get_db),
):
    """Test endpoint — get current user preferences."""
    test_context = get_test_context()
    return _get_preferences_impl(test_context, db)


# ==================== AUTHENTICATED ENDPOINTS ====================


@router.patch("/me/preferences", response_model=UserPreferenceResponse)
def update_preferences(
    patch: UserPreferencePatch,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("voice.use")),
):
    """
    Update user preferences including field_mode_enabled.

    Auth: JWT required — `voice.use` permission (all authenticated users)
    RBAC: `require_permission("voice.use")`

    Request body:
      - field_mode_enabled (bool): enable/disable field mode for hands-free operation

    field_mode_enabled is stored in user_preference.preferences JSONB.
    No migration required — user_preference.preferences already exists.
    """
    return _update_preferences_impl(patch, current_user, db)


@router.get("/me/preferences", response_model=UserPreferenceResponse)
def get_preferences(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("voice.use")),
):
    """
    Get current user preferences.

    Auth: JWT required — `voice.use` permission
    """
    return _get_preferences_impl(current_user, db)
