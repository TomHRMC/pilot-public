"""
Notification Preference Matrix Endpoints — B10/A57

GET    /api/v1/notifications/preferences                          — full user preference matrix
PUT    /api/v1/notifications/preferences/{category_id}/{channel}  — set user preference
DELETE /api/v1/notifications/preferences/{category_id}/{channel}  — clear user preference
PUT    /api/v1/notifications/tenant-policy/{category_id}/{channel}— set tenant default
DELETE /api/v1/notifications/tenant-policy/{category_id}/{channel}— clear tenant default
POST   /api/v1/notifications/preferences/mute-all-push-non-critical
POST   /api/v1/notifications/preferences/mute-all-email
POST   /api/v1/notifications/preferences/reset-to-tenant-defaults

Pattern: dual-endpoint architecture (§8.2).
Permission: notification_preference.user_override.edit (all roles).
             notification_preference.tenant_default.edit (owner only).
"""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import Session, select

from api.schemas.schemas import (
    NotificationPreferenceClearResponse,
    NotificationPreferenceResponse,
)
from app.models.system import (
    NotificationCategory,
    NotificationCategorySubTrigger,
    NotificationDefaultPolicy,
    NotificationPreference,
)
from core.auth import AuthenticatedUser
from core.db import get_db, set_audit_context_sync
from core.permissions import require_permission
from core.test_context import TestUserContext, get_test_context

router = APIRouter()
logger = logging.getLogger(__name__)

VALID_CHANNELS = {"push", "email", "in_app"}


# ─── Pydantic Schemas ────────────────────────────────────────────────────────


class PreferenceUpdate(BaseModel):
    enabled: bool


# BE-UI-NAV-S1: Bulk tenant-policy schemas
class TenantPolicyEntry(BaseModel):
    category_id: str
    channel: str
    enabled: bool


class TenantPolicyListResponse(BaseModel):
    policies: list[TenantPolicyEntry]


class TenantPolicyResetResponse(BaseModel):
    deleted_count: int


# ─── Shared Business Logic ───────────────────────────────────────────────────


def _get_user_id_param(
    user_id_param: UUID | None,
    user_context: AuthenticatedUser | TestUserContext,
) -> UUID:
    """Resolve user_id from query param or default to requesting user."""
    if user_id_param is not None:
        return user_id_param
    return user_context.id if hasattr(user_context, "id") else user_context.user_id


def _get_forced_minimum_for_user(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    category_id: str,
    channel: str,
) -> tuple[bool, bool]:
    """
    Return (forced_minimum, can_disable) for a given category × channel × user.

    forced_minimum: True if any sub-trigger in this category forces push delivery.
    can_disable: False only when forced_minimum is True and channel == 'push'.

    For B10 scope: forced-minimum-push-recipient-only cannot be statically
    determined without knowing which specific outbox row triggered this check.
    We err on the side of showing can_disable=True for those cases.
    """
    if channel != "push":
        return False, True

    # Check for uniform forced-minimum sub-triggers in this category
    uniform_trigger = db.exec(
        select(NotificationCategorySubTrigger).where(
            NotificationCategorySubTrigger.category_id == category_id,
            NotificationCategorySubTrigger.forced_minimum_push_uniform == True,
        )
    ).first()

    if uniform_trigger:
        return True, False

    return False, True


def _build_full_matrix(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
) -> dict[str, Any]:
    """
    Build the 8 × 3 = 24 cell preference matrix for a user.

    For each cell, returns:
      - enabled: effective resolved value
      - scope: 'user' | 'tenant' | 'system' | 'fallback'
      - forced_minimum: bool
      - can_disable: bool
    """
    categories = db.exec(
        select(NotificationCategory).order_by(NotificationCategory.display_order)
    ).all()

    # Load user prefs keyed by (category_id, channel)
    user_prefs: dict[tuple, NotificationPreference] = {}
    for row in db.exec(
        select(NotificationPreference).where(
            NotificationPreference.tenant_id == tenant_id,
            NotificationPreference.user_id == user_id,
        )
    ).all():
        user_prefs[(row.category_id, row.channel)] = row

    # Load tenant-level prefs (user_id IS NULL)
    tenant_prefs: dict[tuple, NotificationPreference] = {}
    for row in db.exec(
        select(NotificationPreference).where(
            NotificationPreference.tenant_id == tenant_id,
            NotificationPreference.user_id == None,
        )
    ).all():
        tenant_prefs[(row.category_id, row.channel)] = row

    # Load system defaults (tenant_id IS NULL)
    system_defaults: dict[tuple, bool] = {}
    for row in db.exec(
        select(NotificationDefaultPolicy).where(
            NotificationDefaultPolicy.tenant_id == None
        )
    ).all():
        system_defaults[(row.category_id, row.channel)] = row.enabled

    # Load tenant policy overrides
    tenant_defaults: dict[tuple, bool] = {}
    for row in db.exec(
        select(NotificationDefaultPolicy).where(
            NotificationDefaultPolicy.tenant_id == tenant_id
        )
    ).all():
        tenant_defaults[(row.category_id, row.channel)] = row.enabled

    channels = ["push", "email", "in_app"]
    preferences = []

    for cat in categories:
        for ch in channels:
            # FIND-169: cat.category_id → cat.code (PK renamed on NotificationCategory)
            key = (cat.code, ch)
            forced_min, can_disable = _get_forced_minimum_for_user(
                db, tenant_id, user_id, cat.code, ch
            )

            # Determine scope and effective value
            if key in user_prefs:
                scope = "user"
                enabled = user_prefs[key].enabled
            elif key in tenant_prefs:
                scope = "tenant"
                enabled = tenant_prefs[key].enabled
            elif key in tenant_defaults:
                scope = "tenant"
                enabled = tenant_defaults[key]
            elif key in system_defaults:
                scope = "system"
                enabled = system_defaults[key]
            else:
                scope = "fallback"
                enabled = False

            preferences.append(
                {
                    # FIND-169: cat.category_id → cat.code
                    "category_id": cat.code,
                    "channel": ch,
                    "enabled": enabled,
                    "scope": scope,
                    "forced_minimum": forced_min,
                    "can_disable": can_disable,
                }
            )

    return {"user_id": str(user_id), "preferences": preferences}


def _upsert_user_preference(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    category_id: str,
    channel: str,
    enabled: bool,
    actor_id: UUID,
) -> dict[str, Any]:
    """Upsert a user-level notification preference row."""
    # Validate category exists
    cat = db.exec(
        # FIND-169: category_id → code on NotificationCategory
        select(NotificationCategory).where(NotificationCategory.code == category_id)
    ).first()
    if not cat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category '{category_id}' not found",
        )

    if channel not in VALID_CHANNELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid channel '{channel}'. Valid values: {sorted(VALID_CHANNELS)}",
        )

    # Check forced-minimum block on push disable
    if channel == "push" and not enabled:
        forced_min, can_disable = _get_forced_minimum_for_user(
            db, tenant_id, user_id, category_id, channel
        )
        if not can_disable:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Cannot disable push for '{category_id}' — "
                    "a forced-minimum sub-trigger requires push delivery."
                ),
            )

    # Upsert
    existing = db.exec(
        select(NotificationPreference).where(
            NotificationPreference.tenant_id == tenant_id,
            NotificationPreference.user_id == user_id,
            NotificationPreference.category_id == category_id,
            NotificationPreference.channel == channel,
        )
    ).first()

    set_audit_context_sync(db, actor_id)
    if existing:
        existing.enabled = enabled
        existing.updated_by = actor_id
        db.add(existing)
    else:
        pref = NotificationPreference(
            tenant_id=tenant_id,
            user_id=user_id,
            category_id=category_id,
            channel=channel,
            enabled=enabled,
            created_by=actor_id,
            updated_by=actor_id,
        )
        db.add(pref)

    db.commit()
    return {
        "category_id": category_id,
        "channel": channel,
        "enabled": enabled,
        "scope": "user",
    }


def _clear_user_preference(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    category_id: str,
    channel: str,
    actor_id: UUID,
) -> dict[str, Any]:
    """Delete a user-level preference row; revert to tenant/system default."""
    existing = db.exec(
        select(NotificationPreference).where(
            NotificationPreference.tenant_id == tenant_id,
            NotificationPreference.user_id == user_id,
            NotificationPreference.category_id == category_id,
            NotificationPreference.channel == channel,
        )
    ).first()

    if existing:
        db.delete(existing)
        db.commit()

    # Determine what scope they've reverted to
    from services.notification_resolver import _resolve_preference

    _ = _resolve_preference(
        db, tenant_id, user_id, category_id, channel
    )  # just for scope detection
    tenant_pref = db.exec(
        select(NotificationPreference).where(
            NotificationPreference.tenant_id == tenant_id,
            NotificationPreference.user_id == None,
            NotificationPreference.category_id == category_id,
            NotificationPreference.channel == channel,
        )
    ).first()
    reverted_scope = "tenant" if tenant_pref else "system"

    return {"cleared": True, "reverted_to_scope": reverted_scope}


# ─── Test Endpoints (register FIRST per §8.2) ────────────────────────────────


@router.get("/test/preferences")
def get_preferences_test(
    user_id: UUID | None = Query(None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    test_context = get_test_context()
    resolved_user_id = _get_user_id_param(user_id, test_context)
    return _build_full_matrix(db, test_context.tenant_id, resolved_user_id)


@router.put(
    "/test/preferences/{category_id}/{channel}",
    response_model=NotificationPreferenceResponse,
)
def set_preference_test(
    category_id: str,
    channel: str,
    data: PreferenceUpdate,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    test_context = get_test_context()
    return _upsert_user_preference(
        db,
        test_context.tenant_id,
        test_context.id,
        category_id,
        channel,
        data.enabled,
        test_context.id,
    )


@router.delete(
    "/test/preferences/{category_id}/{channel}",
    response_model=NotificationPreferenceClearResponse,
)
def clear_preference_test(
    category_id: str,
    channel: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    test_context = get_test_context()
    return _clear_user_preference(
        db,
        test_context.tenant_id,
        test_context.id,
        category_id,
        channel,
        test_context.id,
    )


@router.put("/test/tenant-policy/{category_id}/{channel}")
def set_tenant_policy_test(
    category_id: str,
    channel: str,
    data: PreferenceUpdate,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    test_context = get_test_context()
    return _upsert_tenant_policy(
        db, test_context.tenant_id, category_id, channel, data.enabled, test_context.id
    )


@router.delete("/test/tenant-policy/{category_id}/{channel}")
def clear_tenant_policy_test(
    category_id: str,
    channel: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    test_context = get_test_context()
    return _clear_tenant_policy(
        db, test_context.tenant_id, category_id, channel, test_context.id
    )


@router.post("/test/preferences/mute-all-push-non-critical")
def mute_all_push_non_critical_test(db: Session = Depends(get_db)) -> dict[str, Any]:
    test_context = get_test_context()
    return _mute_all_push_non_critical(db, test_context.tenant_id, test_context.id)


@router.post("/test/preferences/mute-all-email")
def mute_all_email_test(db: Session = Depends(get_db)) -> dict[str, Any]:
    test_context = get_test_context()
    return _mute_all_email(db, test_context.tenant_id, test_context.id)


@router.post("/test/preferences/reset-to-tenant-defaults")
def reset_to_defaults_test(db: Session = Depends(get_db)) -> dict[str, Any]:
    test_context = get_test_context()
    return _reset_to_tenant_defaults(db, test_context.tenant_id, test_context.id)


# BE-UI-NAV-S1: Bulk tenant-policy test endpoints (registered before authenticated per §8.2)
@router.get("/test/tenant-policy", response_model=TenantPolicyListResponse)
def get_tenant_policy_test(
    db: Session = Depends(get_db),
) -> TenantPolicyListResponse:
    """[TEST] Get all tenant notification policy overrides — no auth."""
    ctx = get_test_context()
    return _get_tenant_policy_impl(ctx.tenant_id, db)


@router.delete("/test/tenant-policy", response_model=TenantPolicyResetResponse)
def reset_tenant_policy_test(
    db: Session = Depends(get_db),
) -> TenantPolicyResetResponse:
    """[TEST] Reset all tenant notification policy overrides — no auth."""
    ctx = get_test_context()
    return _reset_tenant_policy_impl(ctx.tenant_id, db)


# ─── Shared Tenant-Policy Logic ──────────────────────────────────────────────


def _upsert_tenant_policy(
    db: Session,
    tenant_id: UUID,
    category_id: str,
    channel: str,
    enabled: bool,
    actor_id: UUID,
) -> dict[str, Any]:
    cat = db.exec(
        # FIND-169: category_id → code on NotificationCategory
        select(NotificationCategory).where(NotificationCategory.code == category_id)
    ).first()
    if not cat:
        raise HTTPException(
            status_code=404, detail=f"Category '{category_id}' not found"
        )
    if channel not in VALID_CHANNELS:
        raise HTTPException(status_code=400, detail=f"Invalid channel '{channel}'")

    existing = db.exec(
        select(NotificationDefaultPolicy).where(
            NotificationDefaultPolicy.tenant_id == tenant_id,
            NotificationDefaultPolicy.category_id == category_id,
            NotificationDefaultPolicy.channel == channel,
        )
    ).first()

    set_audit_context_sync(db, actor_id)
    if existing:
        existing.enabled = enabled
        existing.updated_by = actor_id
        db.add(existing)
    else:
        policy = NotificationDefaultPolicy(
            tenant_id=tenant_id,
            category_id=category_id,
            channel=channel,
            enabled=enabled,
            created_by=actor_id,
            updated_by=actor_id,
        )
        db.add(policy)

    db.commit()
    return {
        "category_id": category_id,
        "channel": channel,
        "enabled": enabled,
        "scope": "tenant",
    }


def _clear_tenant_policy(
    db: Session,
    tenant_id: UUID,
    category_id: str,
    channel: str,
    actor_id: UUID,
) -> dict[str, Any]:
    existing = db.exec(
        select(NotificationDefaultPolicy).where(
            NotificationDefaultPolicy.tenant_id == tenant_id,
            NotificationDefaultPolicy.category_id == category_id,
            NotificationDefaultPolicy.channel == channel,
        )
    ).first()
    if existing:
        db.delete(existing)
        db.commit()
    return {"cleared": True, "reverted_to_scope": "system"}


def _mute_all_push_non_critical(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
) -> dict[str, Any]:
    """Mute push for all categories without forced-minimum-push sub-triggers."""
    categories = db.exec(select(NotificationCategory)).all()
    muted_count = 0

    for cat in categories:
        # Skip categories with recipient-only forced-minimum (cannot determine statically)
        recipient_only = db.exec(
            select(NotificationCategorySubTrigger).where(
                # FK child column category_id stays; cat.category_id → cat.code (FIND-169)
                NotificationCategorySubTrigger.category_id == cat.code,
                NotificationCategorySubTrigger.forced_minimum_push_recipient_only
                == True,
            )
        ).first()
        if recipient_only:
            continue

        # Skip categories with uniform forced-minimum
        uniform = db.exec(
            select(NotificationCategorySubTrigger).where(
                # FK child column category_id stays; cat.category_id → cat.code (FIND-169)
                NotificationCategorySubTrigger.category_id == cat.code,
                NotificationCategorySubTrigger.forced_minimum_push_uniform == True,
            )
        ).first()
        if uniform:
            continue

        # Upsert disabled push preference
        existing = db.exec(
            select(NotificationPreference).where(
                NotificationPreference.tenant_id == tenant_id,
                NotificationPreference.user_id == user_id,
                # FIND-169: cat.category_id → cat.code
                NotificationPreference.category_id == cat.code,
                NotificationPreference.channel == "push",
            )
        ).first()

        if existing:
            existing.enabled = False
            existing.updated_by = user_id
            db.add(existing)
        else:
            db.add(
                NotificationPreference(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    # FIND-169: cat.category_id → cat.code
                    category_id=cat.code,
                    channel="push",
                    enabled=False,
                    created_by=user_id,
                    updated_by=user_id,
                )
            )
        muted_count += 1

    db.commit()
    return {"muted_count": muted_count}


def _mute_all_email(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
) -> dict[str, Any]:
    """Mute email for all 8 categories."""
    categories = db.exec(select(NotificationCategory)).all()
    muted_count = 0

    for cat in categories:
        existing = db.exec(
            select(NotificationPreference).where(
                NotificationPreference.tenant_id == tenant_id,
                NotificationPreference.user_id == user_id,
                # FIND-169: cat.category_id → cat.code
                NotificationPreference.category_id == cat.code,
                NotificationPreference.channel == "email",
            )
        ).first()

        if existing:
            existing.enabled = False
            existing.updated_by = user_id
            db.add(existing)
        else:
            db.add(
                NotificationPreference(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    # FIND-169: cat.category_id → cat.code
                    category_id=cat.code,
                    channel="email",
                    enabled=False,
                    created_by=user_id,
                    updated_by=user_id,
                )
            )
        muted_count += 1

    db.commit()
    return {"muted_count": muted_count}


def _reset_to_tenant_defaults(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
) -> dict[str, Any]:
    """Delete all user-level preference rows for this user."""
    prefs = db.exec(
        select(NotificationPreference).where(
            NotificationPreference.tenant_id == tenant_id,
            NotificationPreference.user_id == user_id,
        )
    ).all()

    cleared_count = len(prefs)
    for pref in prefs:
        db.delete(pref)
    db.commit()

    return {"cleared_count": cleared_count}


# ─── BE-UI-NAV-S1: Bulk Tenant-Policy Shared Logic ───────────────────────────


def _get_tenant_policy_impl(
    tenant_id: UUID,
    db: Session,
) -> TenantPolicyListResponse:
    """Return all tenant-override policy rows for this tenant (tenant_id IS NOT NULL)."""
    rows = db.exec(
        select(NotificationDefaultPolicy).where(
            NotificationDefaultPolicy.tenant_id == tenant_id
        )
    ).all()
    return TenantPolicyListResponse(
        policies=[
            TenantPolicyEntry(
                category_id=r.category_id,
                channel=r.channel,
                enabled=r.enabled,
            )
            for r in rows
        ]
    )


def _reset_tenant_policy_impl(
    tenant_id: UUID,
    db: Session,
    user_id: UUID | None = None,
) -> TenantPolicyResetResponse:
    """Delete all tenant-override rows. System defaults (tenant_id=NULL) are never touched."""
    if user_id:
        set_audit_context_sync(db, user_id=user_id)

    rows = db.exec(
        select(NotificationDefaultPolicy).where(
            NotificationDefaultPolicy.tenant_id == tenant_id
        )
    ).all()
    deleted_count = len(rows)
    for row in rows:
        db.delete(row)
    db.commit()
    return TenantPolicyResetResponse(deleted_count=deleted_count)


# ─── Authenticated Endpoints ──────────────────────────────────────────────────


@router.get("/preferences")
def get_preferences(
    user_id: UUID | None = Query(None),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("notification_preference.user_override.edit")
    ),
) -> dict[str, Any]:
    """
    Return the full 24-cell preference matrix for a user.

    Defaults to requesting user; pass user_id to view another user's preferences.
    """
    resolved_user_id = _get_user_id_param(user_id, current_user)
    return _build_full_matrix(db, current_user.tenant_id, resolved_user_id)


@router.put(
    "/preferences/{category_id}/{channel}",
    response_model=NotificationPreferenceResponse,
)
def set_preference(
    category_id: str,
    channel: str,
    data: PreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("notification_preference.user_override.edit")
    ),
) -> dict[str, Any]:
    """Set a user-level notification preference override."""
    return _upsert_user_preference(
        db,
        current_user.tenant_id,
        current_user.id,
        category_id,
        channel,
        data.enabled,
        current_user.id,
    )


@router.delete(
    "/preferences/{category_id}/{channel}",
    response_model=NotificationPreferenceClearResponse,
)
def clear_preference(
    category_id: str,
    channel: str,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("notification_preference.user_override.edit")
    ),
) -> dict[str, Any]:
    """Delete a user-level preference row; falls back to tenant/system default."""
    return _clear_user_preference(
        db,
        current_user.tenant_id,
        current_user.id,
        category_id,
        channel,
        current_user.id,
    )


@router.put("/tenant-policy/{category_id}/{channel}")
def set_tenant_policy(
    category_id: str,
    channel: str,
    data: PreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("notification_preference.tenant_default.edit")
    ),
) -> dict[str, Any]:
    """Upsert a tenant-level notification default policy (owner only)."""
    return _upsert_tenant_policy(
        db, current_user.tenant_id, category_id, channel, data.enabled, current_user.id
    )


@router.delete("/tenant-policy/{category_id}/{channel}")
def clear_tenant_policy(
    category_id: str,
    channel: str,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("notification_preference.tenant_default.edit")
    ),
) -> dict[str, Any]:
    """Delete tenant-level policy row; reverts to system default."""
    return _clear_tenant_policy(
        db, current_user.tenant_id, category_id, channel, current_user.id
    )


@router.post("/preferences/mute-all-push-non-critical")
def mute_all_push_non_critical(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("notification_preference.user_override.edit")
    ),
) -> dict[str, Any]:
    """Mute push notifications for all non-forced-minimum categories."""
    return _mute_all_push_non_critical(db, current_user.tenant_id, current_user.id)


@router.post("/preferences/mute-all-email")
def mute_all_email(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("notification_preference.user_override.edit")
    ),
) -> dict[str, Any]:
    """Mute email notifications for all 8 categories."""
    return _mute_all_email(db, current_user.tenant_id, current_user.id)


@router.post("/preferences/reset-to-tenant-defaults")
def reset_to_tenant_defaults(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("notification_preference.user_override.edit")
    ),
) -> dict[str, Any]:
    """Delete all user-level preference overrides; revert to tenant/system defaults."""
    return _reset_to_tenant_defaults(db, current_user.tenant_id, current_user.id)


# BE-UI-NAV-S1: Bulk tenant-policy authenticated endpoints


@router.get("/tenant-policy", response_model=TenantPolicyListResponse)
def get_tenant_policy(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("notification_preference.tenant_default.edit")
    ),
) -> TenantPolicyListResponse:
    """
    GET /api/v1/notifications/tenant-policy

    Return all tenant-level notification default policy rows for the requesting tenant.
    Empty list = no overrides (all defaults come from system rows where tenant_id IS NULL).
    Used by the frontend to pre-populate the team notification defaults matrix.

    Permission: notification_preference.tenant_default.edit (owner/operator only)
    """
    return _get_tenant_policy_impl(current_user.tenant_id, db)


@router.delete("/tenant-policy", response_model=TenantPolicyResetResponse)
def reset_tenant_policy(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("notification_preference.tenant_default.edit")
    ),
) -> TenantPolicyResetResponse:
    """
    DELETE /api/v1/notifications/tenant-policy

    Remove all tenant-level notification default policy overrides.
    Reverts the tenant to system defaults (notification_default_policy rows where tenant_id IS NULL).
    System default rows are NEVER deleted by this endpoint.

    Permission: notification_preference.tenant_default.edit (owner/operator only)
    """
    set_audit_context_sync(db, user_id=current_user.id)
    return _reset_tenant_policy_impl(
        current_user.tenant_id, db, user_id=current_user.id
    )
