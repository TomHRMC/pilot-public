"""
Voice Persona API Routes — B12/A67

7 endpoints for reading and managing the voice persona tone setting.
All mounted at prefix /api/v1/settings (registered in app/main.py).

Endpoint summary:
  GET  /voice-persona-tone                          — effective tone for calling user
  PUT  /voice-persona-tone                          — set user-level tone override
  DELETE /voice-persona-tone                        — remove user-level tone override
  GET  /tenant/voice-persona-tone                   — tenant default (any role, read-only)
  PUT  /tenant/voice-persona-tone                   — set tenant default (owner)
  DELETE /tenant/voice-persona-tone                 — reset tenant default to NULL (owner)
  PUT  /tenant/voice-persona-tone-user-override-allowed — toggle per-user overrides (owner)

Pattern: §8.2 Dual-Endpoint Architecture (test endpoints registered FIRST).
Cache invalidation imported from api/routes/settings.py per design doc §D1.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, field_validator
from sqlmodel import Session, select

from app.models.settings import UserSettingOverride
from core.auth import AuthenticatedUser
from core.db import get_db, set_audit_context_sync
from core.permissions import require_permission
from core.test_context import get_test_context
from services.setting_resolver import (
    get_effective_setting_for_user,
    setting_allows_user_override_for_tenant,
)
from services.voice_persona_renderer import VALID_TONES, get_preview_audio_urls

router = APIRouter()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SYSTEM_DEFAULT_TONE = "balanced"
AVAILABLE_TONES: list[str] = list(VALID_TONES)


# ---------------------------------------------------------------------------
# Cache invalidation helpers (re-export from settings.py pattern)
# ---------------------------------------------------------------------------


def _invalidate_settings_catalog_cache(tenant_id: UUID) -> None:
    """Invalidate all role-variant cache keys for a tenant after a settings write."""
    from api.routes.settings import _invalidate_settings_catalog_cache as _impl

    _impl(tenant_id)


def _invalidate_user_settings_cache(
    tenant_id: UUID, user_id: UUID, role_code: str
) -> None:
    """Invalidate user-specific cache key after a user override write."""
    from api.routes.settings import _invalidate_user_settings_cache as _impl

    _impl(tenant_id, user_id, role_code)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class VoicePersonaToneUserRequest(BaseModel):
    """Request body for PUT /voice-persona-tone (user override)."""

    value: str

    @field_validator("value")
    @classmethod
    def validate_tone(cls, v: str) -> str:
        if v not in VALID_TONES:
            raise ValueError(
                f"Invalid tone '{v}'. Must be one of: {', '.join(VALID_TONES)}"
            )
        return v


class VoicePersonaToneTenantRequest(BaseModel):
    """Request body for PUT /tenant/voice-persona-tone (tenant default)."""

    value: str

    @field_validator("value")
    @classmethod
    def validate_tone(cls, v: str) -> str:
        if v not in VALID_TONES:
            raise ValueError(
                f"Invalid tone '{v}'. Must be one of: {', '.join(VALID_TONES)}"
            )
        return v


class VoicePersonaToneUserOverridePolicyRequest(BaseModel):
    """Request body for PUT /tenant/voice-persona-tone-user-override-allowed."""

    value: bool


class VoicePersonaToneEffectiveResponse(BaseModel):
    """Response for GET /voice-persona-tone — effective tone resolution."""

    model_config = ConfigDict(from_attributes=True)

    effective_tone: str
    effective_scope: str
    user_override: str | None
    tenant_default: str | None
    system_default: str
    user_override_allowed: bool
    available_tones: list[str]
    preview_audio_urls: dict[str, str]


class VoicePersonaToneTenantResponse(BaseModel):
    """Response for GET /tenant/voice-persona-tone."""

    model_config = ConfigDict(from_attributes=True)

    tenant_default: str | None
    tenant_default_scope: str
    system_default: str
    user_override_policy: bool
    available_tones: list[str]
    preview_audio_urls: dict[str, str]


class VoicePersonaToneWriteResponse(BaseModel):
    """Response for PUT (user and tenant write) endpoints."""

    setting_key: str
    value: Any
    scope: str
    updated_at: datetime


# ---------------------------------------------------------------------------
# Shared business logic
# ---------------------------------------------------------------------------


def _get_user_override(
    db: Session, tenant_id: UUID, user_id: UUID
) -> UserSettingOverride | None:
    return db.exec(
        select(UserSettingOverride)
        .where(UserSettingOverride.tenant_id == tenant_id)
        .where(UserSettingOverride.user_id == user_id)
        .where(UserSettingOverride.setting_key == "voice_persona_tone")
    ).first()


def _get_effective_tone_response(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
) -> VoicePersonaToneEffectiveResponse:
    """Shared impl for GET /voice-persona-tone."""
    effective_tone, scope = get_effective_setting_for_user(
        db=db,
        tenant_id=tenant_id,
        user_id=user_id,
        setting_key="voice_persona_tone",
        fallback=SYSTEM_DEFAULT_TONE,
    )

    user_override_allowed = setting_allows_user_override_for_tenant(
        db, tenant_id, "voice_persona_tone"
    )
    user_override_row = _get_user_override(db, tenant_id, user_id)

    # Read tenant-level default from platform_setting (tenant_id NOT NULL row only)
    from sqlmodel import select as _select

    from app.models.platform_setting import PlatformSetting

    tenant_ps_row = db.exec(
        _select(PlatformSetting)
        .where(PlatformSetting.key == "voice_persona_tone")
        .where(PlatformSetting.tenant_id == tenant_id)
    ).first()
    tenant_default = tenant_ps_row.value if tenant_ps_row else None

    return VoicePersonaToneEffectiveResponse(
        effective_tone=effective_tone or SYSTEM_DEFAULT_TONE,
        effective_scope=scope,
        user_override=user_override_row.value if user_override_row else None,
        tenant_default=tenant_default,
        system_default=SYSTEM_DEFAULT_TONE,
        user_override_allowed=user_override_allowed,
        available_tones=AVAILABLE_TONES,
        preview_audio_urls=get_preview_audio_urls(),
    )


def _set_user_tone_override(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    role_code: str,
    new_value: str,
) -> VoicePersonaToneWriteResponse:
    """Upsert user tone override in user_setting_override. Calls cache invalidation."""
    # Check meta-toggle FIRST — 403 if tenant has disabled user overrides
    if not setting_allows_user_override_for_tenant(db, tenant_id, "voice_persona_tone"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://pilotfortrades.com/errors/forbidden",
                "title": "User Override Disabled",
                "status": 403,
                "detail": (
                    "Your account administrator has disabled per-user voice persona "
                    "overrides. All users use the team default tone."
                ),
            },
        )

    now = datetime.now(UTC)
    existing = _get_user_override(db, tenant_id, user_id)

    if existing:
        existing.value = new_value
        existing.updated_at = now
        existing.updated_by = user_id
        db.add(existing)
    else:
        override = UserSettingOverride(
            tenant_id=tenant_id,
            user_id=user_id,
            setting_key="voice_persona_tone",
            value=new_value,
            created_at=now,
            updated_at=now,
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(override)

    db.commit()
    _invalidate_user_settings_cache(tenant_id, user_id, role_code)

    return VoicePersonaToneWriteResponse(
        setting_key="voice_persona_tone",
        value=new_value,
        scope="user",
        updated_at=now,
    )


def _delete_user_tone_override(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    role_code: str,
) -> None:
    """Delete user tone override (idempotent). Calls cache invalidation."""
    existing = _get_user_override(db, tenant_id, user_id)
    if existing:
        db.delete(existing)
        db.commit()
    _invalidate_user_settings_cache(tenant_id, user_id, role_code)


def _set_tenant_tone_default(
    db: Session,
    tenant_id: UUID,
    new_value: str | None,
) -> VoicePersonaToneWriteResponse:
    """Upsert tenant voice_persona_tone in platform_setting. Calls cache invalidation."""
    from api.routes.settings import _upsert_platform_setting

    now = datetime.now(UTC)
    if new_value is not None:
        _upsert_platform_setting(db, tenant_id, "voice_persona_tone", new_value)
    else:
        # Deleting the tenant override — remove row from platform_setting
        from app.models.platform_setting import PlatformSetting

        row = db.exec(
            select(PlatformSetting)
            .where(PlatformSetting.key == "voice_persona_tone")
            .where(PlatformSetting.tenant_id == tenant_id)
        ).first()
        if row:
            db.delete(row)
            db.commit()
    _invalidate_settings_catalog_cache(tenant_id)

    return VoicePersonaToneWriteResponse(
        setting_key="voice_persona_tone",
        value=new_value,
        scope="tenant",
        updated_at=now,
    )


def _set_user_override_policy(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    new_value: bool,
) -> VoicePersonaToneWriteResponse:
    """Toggle voice_persona_tone_user_override_allowed in platform_setting."""
    from api.routes.settings import _upsert_platform_setting

    now = datetime.now(UTC)
    set_audit_context_sync(db, user_id)
    _upsert_platform_setting(
        db, tenant_id, "voice_persona_tone_user_override_allowed", new_value
    )
    _invalidate_settings_catalog_cache(tenant_id)

    return VoicePersonaToneWriteResponse(
        setting_key="voice_persona_tone_user_override_allowed",
        value=new_value,
        scope="tenant",
        updated_at=now,
    )


def _get_tenant_tone_response(
    db: Session,
    tenant_id: UUID,
) -> VoicePersonaToneTenantResponse:
    """Shared impl for GET /tenant/voice-persona-tone (post-FIND-086)."""
    from app.models.platform_setting import PlatformSetting
    from services.setting_resolver import get_effective_setting

    # Tenant-only override row (not the NULL platform default)
    tenant_ps_row = db.exec(
        select(PlatformSetting)
        .where(PlatformSetting.key == "voice_persona_tone")
        .where(PlatformSetting.tenant_id == tenant_id)
    ).first()
    tenant_default = tenant_ps_row.value if tenant_ps_row else None

    override_val, _ = get_effective_setting(
        db, tenant_id, "voice_persona_tone_user_override_allowed", fallback=True
    )
    user_override_policy = bool(override_val)

    return VoicePersonaToneTenantResponse(
        tenant_default=tenant_default,
        tenant_default_scope="tenant" if tenant_default else "system",
        system_default=SYSTEM_DEFAULT_TONE,
        user_override_policy=user_override_policy,
        available_tones=AVAILABLE_TONES,
        preview_audio_urls=get_preview_audio_urls(),
    )


# ---------------------------------------------------------------------------
# C1: GET /voice-persona-tone  — effective tone for calling user
# ---------------------------------------------------------------------------


@router.get(
    "/voice-persona-tone/test", response_model=VoicePersonaToneEffectiveResponse
)
def get_effective_voice_persona_tone_test(db: Session = Depends(get_db)):
    """Test endpoint — no auth required. Blocked in staging/production."""
    ctx = get_test_context()
    return _get_effective_tone_response(db, ctx.tenant_id, ctx.id)


@router.get("/voice-persona-tone", response_model=VoicePersonaToneEffectiveResponse)
def get_effective_voice_persona_tone(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("voice.view")),
):
    """
    Return the effective voice persona tone for the authenticated user.

    Resolves through the three-tier chain: user override → tenant default → system default.
    No explicit permission required beyond any authenticated role (voice.view).
    """
    return _get_effective_tone_response(db, current_user.tenant_id, current_user.id)


# ---------------------------------------------------------------------------
# C2: PUT /voice-persona-tone  — set user-level tone override
# ---------------------------------------------------------------------------


@router.put(
    "/voice-persona-tone/test",
    response_model=VoicePersonaToneWriteResponse,
    status_code=status.HTTP_200_OK,
)
def set_user_voice_persona_tone_test(
    body: VoicePersonaToneUserRequest,
    db: Session = Depends(get_db),
):
    """Test endpoint — no auth required. Blocked in staging/production."""
    ctx = get_test_context()
    return _set_user_tone_override(db, ctx.tenant_id, ctx.id, "owner", body.value)


@router.put(
    "/voice-persona-tone",
    response_model=VoicePersonaToneWriteResponse,
    status_code=status.HTTP_200_OK,
)
def set_user_voice_persona_tone(
    body: VoicePersonaToneUserRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("voice_persona_tone.user_override.edit")
    ),
):
    """
    Set the calling user's voice persona tone override.

    Requires: voice_persona_tone.user_override.edit (all roles when tenant allows).
    Returns 403 if tenant has disabled user overrides via the meta-toggle.
    Returns 422 if value is not in ["conservative", "balanced", "playful"].
    """
    return _set_user_tone_override(
        db,
        current_user.tenant_id,
        current_user.id,
        current_user.role_code,
        body.value,
    )


# ---------------------------------------------------------------------------
# C3: DELETE /voice-persona-tone  — remove user-level tone override
# ---------------------------------------------------------------------------


@router.delete(
    "/voice-persona-tone/test",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_user_voice_persona_tone_test(db: Session = Depends(get_db)):
    """Test endpoint — no auth required. Blocked in staging/production."""
    ctx = get_test_context()
    _delete_user_tone_override(db, ctx.tenant_id, ctx.id, "owner")
    return None


@router.delete(
    "/voice-persona-tone",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_user_voice_persona_tone(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("voice_persona_tone.user_override.edit")
    ),
):
    """
    Remove the calling user's voice persona tone override (idempotent).

    No error if no override exists. After deletion, effective tone falls back
    to tenant default or system default ('balanced').
    """
    _delete_user_tone_override(
        db, current_user.tenant_id, current_user.id, current_user.role_code
    )
    return None


# ---------------------------------------------------------------------------
# C4: GET /tenant/voice-persona-tone  — tenant default (any role, read-only)
# ---------------------------------------------------------------------------


@router.get(
    "/tenant/voice-persona-tone/test",
    response_model=VoicePersonaToneTenantResponse,
)
def get_tenant_voice_persona_tone_test(db: Session = Depends(get_db)):
    """Test endpoint — no auth required. Blocked in staging/production."""
    ctx = get_test_context()
    return _get_tenant_tone_response(db, ctx.tenant_id)


@router.get("/tenant/voice-persona-tone", response_model=VoicePersonaToneTenantResponse)
def get_tenant_voice_persona_tone(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("voice.view")),
):
    """
    Return the tenant-level voice persona tone default and policy.

    No explicit permission beyond authenticated user (read-only for non-owners).
    """
    return _get_tenant_tone_response(db, current_user.tenant_id)


# ---------------------------------------------------------------------------
# C5: PUT /tenant/voice-persona-tone  — set tenant default (owner only)
# ---------------------------------------------------------------------------


@router.put(
    "/tenant/voice-persona-tone/test",
    response_model=VoicePersonaToneWriteResponse,
    status_code=status.HTTP_200_OK,
)
def set_tenant_voice_persona_tone_test(
    body: VoicePersonaToneTenantRequest,
    db: Session = Depends(get_db),
):
    """Test endpoint — no auth required. Blocked in staging/production."""
    ctx = get_test_context()
    return _set_tenant_tone_default(db, ctx.tenant_id, body.value)


@router.put(
    "/tenant/voice-persona-tone",
    response_model=VoicePersonaToneWriteResponse,
    status_code=status.HTTP_200_OK,
)
def set_tenant_voice_persona_tone(
    body: VoicePersonaToneTenantRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("voice_persona_tone.tenant_default.edit")
    ),
):
    """
    Set the tenant-level voice persona tone default.

    Requires: voice_persona_tone.tenant_default.edit (owner only).
    Returns 422 if value is not in ["conservative", "balanced", "playful"].
    """
    set_audit_context_sync(db, current_user.id)
    return _set_tenant_tone_default(db, current_user.tenant_id, body.value)


# ---------------------------------------------------------------------------
# C6: DELETE /tenant/voice-persona-tone  — reset to NULL (owner only)
# ---------------------------------------------------------------------------


@router.delete(
    "/tenant/voice-persona-tone/test",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_tenant_voice_persona_tone_test(db: Session = Depends(get_db)):
    """Test endpoint — no auth required. Blocked in staging/production."""
    ctx = get_test_context()
    _set_tenant_tone_default(db, ctx.tenant_id, None)
    return None


@router.delete(
    "/tenant/voice-persona-tone",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_tenant_voice_persona_tone(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("voice_persona_tone.tenant_default.edit")
    ),
):
    """
    Reset the tenant voice persona tone to NULL (falls back to system default 'balanced').

    Requires: voice_persona_tone.tenant_default.edit (owner only).
    """
    set_audit_context_sync(db, current_user.id)
    _set_tenant_tone_default(db, current_user.tenant_id, None)
    return None


# ---------------------------------------------------------------------------
# C7: PUT /tenant/voice-persona-tone-user-override-allowed (owner only)
# ---------------------------------------------------------------------------


@router.put(
    "/tenant/voice-persona-tone-user-override-allowed/test",
    response_model=VoicePersonaToneWriteResponse,
    status_code=status.HTTP_200_OK,
)
def set_user_override_policy_test(
    body: VoicePersonaToneUserOverridePolicyRequest,
    db: Session = Depends(get_db),
):
    """Test endpoint — no auth required. Blocked in staging/production."""
    ctx = get_test_context()
    return _set_user_override_policy(db, ctx.tenant_id, ctx.id, body.value)


@router.put(
    "/tenant/voice-persona-tone-user-override-allowed",
    response_model=VoicePersonaToneWriteResponse,
    status_code=status.HTTP_200_OK,
)
def set_user_override_policy(
    body: VoicePersonaToneUserOverridePolicyRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("voice_persona_tone.user_override_policy.edit")
    ),
):
    """
    Toggle whether team members can set their own voice persona tone.

    Requires: voice_persona_tone.user_override_policy.edit (owner only).

    When set to FALSE:
    - User-level overrides are silently ignored by the resolver.
    - Existing user_setting_override rows are preserved (not deleted).
    - If re-enabled, each user's previous preference is immediately restored.

    Writes an audit log entry (A67 Decision 9).
    """
    return _set_user_override_policy(
        db, current_user.tenant_id, current_user.id, body.value
    )
