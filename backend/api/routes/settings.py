"""
Settings API routes for Pilot for Trades.

Covers all four B9 items:
  A53 — GET /settings/{key}/effective (three-tier resolver endpoint)
  A52 — GET /settings/catalog (full catalog with resolved values + Redis cache)
  A54 — PUT /settings/{key}, DELETE /settings/{key}/tenant-override, PUT /settings/bulk (tenant writes)
  A55 — PUT /settings/{key}/user-override, DELETE /settings/{key}/user-override (user overrides)

Route registration order: /test endpoints BEFORE authenticated endpoints;
static paths (/catalog, /bulk) BEFORE parameterized paths (/{key}).
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, select

from app.models.platform_setting import PlatformSetting, PlatformSettingCatalog
from app.models.quoting import Quote, QuoteStatus
from app.models.settings import UserSettingOverride
from core.auth import AuthenticatedUser
from core.db import get_db, set_audit_context_sync
from core.permissions import require_permission
from core.test_context import get_test_context
from services.setting_resolver import (
    get_effective_setting,
    get_effective_setting_for_user,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Redis helper (graceful degradation if Redis is unavailable)
# ---------------------------------------------------------------------------


def _get_settings_redis_client():
    """Return a synchronous Redis client for settings cache (db=4).

    Returns None if redis is unavailable — callers must handle None gracefully.
    """
    try:
        import redis

        from core.config import settings as app_settings

        base_url = app_settings.REDIS_URL
        redis_url = re.sub(r"/\d+$", "/4", base_url)
        return redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
    except Exception:
        return None


def _invalidate_settings_catalog_cache(tenant_id: UUID) -> None:
    """Delete all role-variant cache keys for a tenant after a settings write."""
    client = _get_settings_redis_client()
    if client is None:
        return
    try:
        pattern = f"settings_catalog:{tenant_id}:*"
        keys = list(client.scan_iter(pattern))
        if keys:
            client.delete(*keys)
    except Exception as exc:
        logger.warning(
            "Failed to invalidate settings cache for tenant %s: %s", tenant_id, exc
        )


def _invalidate_user_settings_cache(
    tenant_id: UUID, user_id: UUID, role_code: str
) -> None:
    """Delete user-specific cache key after a user override write."""
    client = _get_settings_redis_client()
    if client is None:
        return
    try:
        key = f"settings_catalog:{tenant_id}:{user_id}:{role_code}"
        client.delete(key)
    except Exception as exc:
        logger.warning("Failed to invalidate user settings cache: %s", exc)


# ---------------------------------------------------------------------------
# Per-setting value validation
# ---------------------------------------------------------------------------


def _validate_setting_value(
    setting_key: str, value: Any, db: Session | None = None
) -> None:
    """
    Validate a value against the catalog's validation_rules for this key.

    Post-FIND-086: reads catalog from DB when db is provided.
    Raises HTTP 422 with a structured detail dict if validation fails.
    """
    if db is not None:
        catalog_row = db.exec(
            select(PlatformSettingCatalog).where(
                PlatformSettingCatalog.key == setting_key
            )
        ).first()
        if catalog_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "type": "https://pilotfortrades.com/errors/setting-not-found",
                    "title": "Setting Not Found",
                    "status": 404,
                    "detail": f"Setting key '{setting_key}' does not exist in the catalog.",
                },
            )
        rules = {}
        if catalog_row.min_value is not None:
            rules["min"] = catalog_row.min_value
        if catalog_row.max_value is not None:
            rules["max"] = catalog_row.max_value
        if catalog_row.allowed_values is not None:
            rules["allowed_values"] = catalog_row.allowed_values
        data_type = catalog_row.value_type
    else:
        # Fallback — no validation when DB not provided
        return

    rules = rules
    data_type = data_type

    # Type check
    if data_type == "boolean" and not isinstance(value, bool):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "https://pilotfortrades.com/errors/validation-failed",
                "title": "Validation Failed",
                "status": 422,
                "detail": f"Setting '{setting_key}' requires a boolean value.",
            },
        )
    if data_type in ("integer",) and not isinstance(value, int):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "https://pilotfortrades.com/errors/validation-failed",
                "title": "Validation Failed",
                "status": 422,
                "detail": f"Setting '{setting_key}' requires an integer value.",
            },
        )
    if data_type == "decimal" and not isinstance(value, (int, float)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "https://pilotfortrades.com/errors/validation-failed",
                "title": "Validation Failed",
                "status": 422,
                "detail": f"Setting '{setting_key}' requires a numeric value.",
            },
        )

    # Range checks
    if "min" in rules and value is not None and value < rules["min"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "https://pilotfortrades.com/errors/validation-failed",
                "title": "Validation Failed",
                "status": 422,
                "detail": f"Setting '{setting_key}' must be >= {rules['min']}.",
                "violated_rule": "min",
                "min": rules["min"],
            },
        )
    if "max" in rules and value is not None and value > rules["max"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "https://pilotfortrades.com/errors/validation-failed",
                "title": "Validation Failed",
                "status": 422,
                "detail": f"Setting '{setting_key}' must be <= {rules['max']}.",
                "violated_rule": "max",
                "max": rules["max"],
            },
        )

    # Allowed values check (string enums)
    if (
        "allowed_values" in rules
        and value is not None
        and value not in rules["allowed_values"]
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "https://pilotfortrades.com/errors/validation-failed",
                "title": "Validation Failed",
                "status": 422,
                "detail": f"Setting '{setting_key}' must be one of {rules['allowed_values']}.",
                "violated_rule": "allowed_values",
            },
        )

    # Save-on-group-complete: single-key write that requires group is rejected
    if "save_on_group_complete" in rules and value is True:
        # This key requires its companions to be set atomically via /bulk
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "type": "https://pilotfortrades.com/errors/validation-failed",
                "title": "Use Bulk Endpoint",
                "status": 422,
                "detail": (
                    f"Setting '{setting_key}' must be saved together with "
                    f"{rules['save_on_group_complete']}. Use PUT /api/v1/settings/bulk."
                ),
                "violated_rule": "save_on_group_complete",
                "required_companions": rules["save_on_group_complete"],
            },
        )


def _upsert_platform_setting(
    db: Session,
    tenant_id: UUID,
    key: str,
    value: Any,
    user_id: UUID | None = None,
) -> PlatformSetting:
    """
    Upsert a tenant override row in platform_setting (post-FIND-086).
    If user_id supplied, sets audit context first.

    Uses pure ORM upsert to avoid pg_insert/exec() compatibility issues.
    """
    if user_id:
        set_audit_context_sync(db, user_id)

    existing = db.exec(
        select(PlatformSetting)
        .where(PlatformSetting.key == key)
        .where(PlatformSetting.tenant_id == tenant_id)
    ).first()

    if existing is not None:
        existing.value = value
        db.add(existing)
    else:
        existing = PlatformSetting(key=key, value=value, tenant_id=tenant_id)
        db.add(existing)

    db.commit()
    db.refresh(existing)
    _invalidate_settings_catalog_cache(tenant_id)
    return existing


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class EffectiveSettingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    value: Any
    scope: str  # 'user' | 'tenant' | 'system' | 'fallback'
    tenant_override_exists: bool
    user_override_exists: bool
    allows_user_override: bool


class CatalogEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    label: str
    description: str
    sub_surface_path: str
    data_type: str
    validation_rules: dict[str, Any]
    system_default: Any
    current_effective_value: Any
    current_scope: str
    revertible: bool
    requires_role: str | None
    allows_user_override: bool


class CatalogResponse(BaseModel):
    settings: list[CatalogEntryResponse]


class TenantSettingWriteRequest(BaseModel):
    value: Any
    expected_updated_at: datetime | None = None


class TenantSettingWriteResponse(BaseModel):
    key: str
    value: Any
    effective_value: Any
    scope: str
    updated_at: datetime
    pending_quote_count: int | None = (
        None  # Only for require_approval_for_tech_quotes toggle OFF
    )


class BulkSettingWriteRequest(BaseModel):
    values: dict[str, Any]


class BulkSettingWriteResponse(BaseModel):
    updated: list[str]
    results: list[TenantSettingWriteResponse]


class UserOverrideWriteRequest(BaseModel):
    value: Any


class UserOverrideWriteResponse(BaseModel):
    key: str
    value: Any
    effective_value: Any
    scope: str
    updated_at: datetime


class LotoPolicyResponse(BaseModel):
    loto_confirmation_required: bool


# ---------------------------------------------------------------------------
# Shared implementation functions
# ---------------------------------------------------------------------------


def _get_or_404_catalog_entry(setting_key: str, db: Session | None = None) -> dict:
    """Return catalog entry dict or raise 404. DB-based post-FIND-086."""
    if db is not None:
        row = db.exec(
            select(PlatformSettingCatalog).where(
                PlatformSettingCatalog.key == setting_key
            )
        ).first()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "type": "https://pilotfortrades.com/errors/setting-not-found",
                    "title": "Setting Not Found",
                    "status": 404,
                    "detail": f"Setting key '{setting_key}' does not exist in the catalog.",
                },
            )
        return {
            "label": row.label,
            "data_type": row.value_type,
            "allows_user_override": row.allows_user_override,
            "tenant_editable": row.tenant_editable,
            "validation_rules": {
                k: v
                for k, v in [
                    ("min", row.min_value),
                    ("max", row.max_value),
                    ("allowed_values", row.allowed_values),
                ]
                if v is not None
            },
            "revertible": True,
        }
    # fallback — shouldn't be reached after FIND-086
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"detail": f"Setting key '{setting_key}' not found."},
    )


def _check_tenant_override_exists(
    db: Session, tenant_id: UUID, setting_key: str
) -> bool:
    """Return True if a tenant-specific platform_setting row exists for this key."""
    row = db.exec(
        select(PlatformSetting)
        .where(PlatformSetting.key == setting_key)
        .where(PlatformSetting.tenant_id == tenant_id)
    ).first()
    return row is not None


def _check_user_override_exists(
    db: Session, tenant_id: UUID, user_id: UUID, setting_key: str
) -> bool:
    """Return True if a UserSettingOverride row exists for this (tenant, user, key)."""
    row = db.exec(
        select(UserSettingOverride)
        .where(UserSettingOverride.tenant_id == tenant_id)
        .where(UserSettingOverride.user_id == user_id)
        .where(UserSettingOverride.setting_key == setting_key)
    ).first()
    return row is not None


def _get_effective_impl(
    key: str,
    resolve_user_id: UUID,
    db: Session,
    current_tenant_id: UUID,
) -> EffectiveSettingResponse:
    """Shared implementation for GET /settings/{key}/effective."""
    entry = _get_or_404_catalog_entry(key, db=db)

    value, scope = get_effective_setting_for_user(
        db=db,
        tenant_id=current_tenant_id,
        user_id=resolve_user_id,
        setting_key=key,
        fallback=None,
    )

    tenant_override_exists = _check_tenant_override_exists(db, current_tenant_id, key)
    user_override_exists = _check_user_override_exists(
        db, current_tenant_id, resolve_user_id, key
    )

    return EffectiveSettingResponse(
        key=key,
        value=value,
        scope=scope,
        tenant_override_exists=tenant_override_exists,
        user_override_exists=user_override_exists,
        allows_user_override=entry.get("allows_user_override", False),
    )


def _get_catalog_impl(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    role_code: str,
) -> CatalogResponse:
    """Shared implementation for GET /settings/catalog."""
    # Try Redis cache first
    client = _get_settings_redis_client()
    cache_key = f"settings_catalog:{tenant_id}:{user_id}:{role_code}"

    if client is not None:
        try:
            import json

            cached = client.get(cache_key)
            if cached:
                data = json.loads(cached)
                return CatalogResponse(**data)
        except Exception as exc:
            logger.warning("Settings catalog cache read failed: %s", exc)

    # Post-FIND-086: read catalog from platform_setting_catalog DB table
    catalog_rows = db.exec(
        select(PlatformSettingCatalog)
        .where(PlatformSettingCatalog.is_active == True)
        .order_by(PlatformSettingCatalog.sort_order)
    ).all()
    entries: list[CatalogEntryResponse] = []

    for catalog_row in catalog_rows:
        # Filter: non-staff roles only see tenant-editable settings
        if not catalog_row.tenant_editable and role_code not in ("staff", "superadmin"):
            continue

        effective_value, scope = get_effective_setting_for_user(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            setting_key=catalog_row.key,
            fallback=None,
        )

        validation_rules = {}
        if catalog_row.min_value is not None:
            validation_rules["min"] = catalog_row.min_value
        if catalog_row.max_value is not None:
            validation_rules["max"] = catalog_row.max_value
        if catalog_row.allowed_values is not None:
            validation_rules["allowed_values"] = catalog_row.allowed_values

        # Read platform default value (NULL tenant_id row)
        default_row = db.exec(
            select(PlatformSetting)
            .where(PlatformSetting.key == catalog_row.key)
            .where(PlatformSetting.tenant_id.is_(None))
        ).first()
        system_default = default_row.value if default_row else None

        entries.append(
            CatalogEntryResponse(
                key=catalog_row.key,
                label=catalog_row.label,
                description=catalog_row.description or "",
                sub_surface_path=f"/settings/{catalog_row.category or 'general'}/{catalog_row.key}",
                data_type=catalog_row.value_type,
                validation_rules=validation_rules,
                system_default=system_default,
                current_effective_value=effective_value,
                current_scope=scope,
                revertible=True,
                requires_role=None if catalog_row.tenant_editable else "staff",
                allows_user_override=catalog_row.allows_user_override,
            )
        )

    response = CatalogResponse(settings=entries)

    # Cache result in Redis
    if client is not None:
        try:
            import json

            client.setex(
                cache_key, 3600, json.dumps(response.model_dump(), default=str)
            )
        except Exception as exc:
            logger.warning("Settings catalog cache write failed: %s", exc)

    return response


def _put_setting_impl(
    key: str,
    payload: TenantSettingWriteRequest,
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
) -> TenantSettingWriteResponse:
    """Shared implementation for PUT /settings/{key} (post-FIND-086: upsert platform_setting)."""
    _get_or_404_catalog_entry(key, db=db)
    _validate_setting_value(key, payload.value, db=db)

    # Optimistic staleness check: if expected_updated_at is provided, verify the
    # effective setting row has not been updated since that timestamp.
    # Check tenant override first; fall back to platform default (NULL tenant_id).
    if payload.expected_updated_at is not None:
        current_row = db.exec(
            select(PlatformSetting)
            .where(PlatformSetting.key == key)
            .where(PlatformSetting.tenant_id == tenant_id)
        ).first()
        if current_row is None:
            # No tenant override — check platform default row
            current_row = db.exec(
                select(PlatformSetting)
                .where(PlatformSetting.key == key)
                .where(PlatformSetting.tenant_id.is_(None))
            ).first()
        if current_row is not None:
            row_updated_at = current_row.updated_at
            # Make both timezone-aware for comparison
            expected = payload.expected_updated_at
            if hasattr(expected, "tzinfo") and expected.tzinfo is None:
                expected = expected.replace(tzinfo=UTC)
            if hasattr(row_updated_at, "tzinfo") and row_updated_at.tzinfo is None:
                row_updated_at = row_updated_at.replace(tzinfo=UTC)
            if row_updated_at > expected:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "type": "https://pilotfortrades.com/errors/conflict",
                        "title": "Conflict",
                        "status": 409,
                        "detail": (
                            f"Setting '{key}' was modified after your snapshot "
                            f"(expected_updated_at={payload.expected_updated_at.isoformat()})."
                        ),
                    },
                )

    # Upsert tenant override row (FIND-086: replaces setattr on TenantSettings)
    _upsert_platform_setting(db, tenant_id, key, payload.value, user_id=user_id)

    # Compute effective value after write
    effective_value, scope = get_effective_setting(db, tenant_id, key, fallback=None)

    response = TenantSettingWriteResponse(
        key=key,
        value=payload.value,
        effective_value=effective_value,
        scope=scope,
        updated_at=datetime.now(),
    )

    # Special case: require_approval_for_tech_quotes toggled OFF
    # Count quotes whose QuoteStatus.code is 'submitted_for_approval'
    if key == "require_approval_for_tech_quotes" and payload.value is False:
        submitted_status = db.exec(
            select(QuoteStatus).where(
                QuoteStatus.tenant_id == tenant_id,
                QuoteStatus.code == "submitted_for_approval",
            )
        ).first()
        if submitted_status is not None:
            pending_quotes = db.exec(
                select(Quote).where(
                    Quote.tenant_id == tenant_id,
                    Quote.status_id == submitted_status.id,
                )
            ).all()
            response.pending_quote_count = len(pending_quotes)
        else:
            response.pending_quote_count = 0

    return response


def _delete_setting_impl(
    key: str,
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
) -> TenantSettingWriteResponse:
    """Shared implementation for DELETE /settings/{key} (revert to system default)."""
    entry = _get_or_404_catalog_entry(key, db=db)

    # Check revertible flag
    if not entry.get("revertible", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://pilotfortrades.com/errors/not-revertible",
                "title": "Setting Not Revertible",
                "status": 400,
                "detail": f"Setting '{key}' cannot be reverted to system default.",
            },
        )

    # Post-FIND-086: deleting a tenant override = DELETE platform_setting row for this (key, tenant_id)
    set_audit_context_sync(db, user_id)
    existing = db.exec(
        select(PlatformSetting)
        .where(PlatformSetting.key == key)
        .where(PlatformSetting.tenant_id == tenant_id)
    ).first()

    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://pilotfortrades.com/errors/setting-not-found",
                "title": "No Tenant Override",
                "status": 404,
                "detail": f"No tenant override exists for setting '{key}'.",
            },
        )

    db.delete(existing)
    db.commit()
    _invalidate_settings_catalog_cache(tenant_id)

    effective_value, scope = get_effective_setting(db, tenant_id, key, fallback=None)

    return TenantSettingWriteResponse(
        key=key,
        value=None,
        effective_value=effective_value,
        scope=scope,
        updated_at=datetime.now(),
    )


def _bulk_write_impl(
    payload: BulkSettingWriteRequest,
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
) -> BulkSettingWriteResponse:
    """Shared implementation for PUT /settings/bulk (post-FIND-086)."""
    # Validate all keys and values first (fail-fast before any writes)
    for key, value in payload.values.items():
        _get_or_404_catalog_entry(key, db=db)
        _validate_setting_value(key, value, db=db)

    # Write each key as an upsert in platform_setting
    set_audit_context_sync(db, user_id)
    for key, value in payload.values.items():
        _upsert_platform_setting(db, tenant_id, key, value, user_id=user_id)

    _invalidate_settings_catalog_cache(tenant_id)

    results = []
    now = datetime.now()
    for key, value in payload.values.items():
        effective_value, scope = get_effective_setting(
            db, tenant_id, key, fallback=None
        )
        results.append(
            TenantSettingWriteResponse(
                key=key,
                value=value,
                effective_value=effective_value,
                scope=scope,
                updated_at=now,
            )
        )

    return BulkSettingWriteResponse(
        updated=list(payload.values.keys()), results=results
    )


def _validate_bulk_value(key: str, value: Any, rules: dict) -> None:
    """Simplified validation for bulk writes — no save_on_group_complete check."""
    data_type = rules.get("data_type", "")

    if data_type == "boolean" and not isinstance(value, bool):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"detail": f"Setting '{key}' requires a boolean value."},
        )
    if data_type == "integer" and not isinstance(value, int):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"detail": f"Setting '{key}' requires an integer value."},
        )
    if "min" in rules and value is not None and value < rules["min"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"detail": f"Setting '{key}' must be >= {rules['min']}."},
        )
    if "max" in rules and value is not None and value > rules["max"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"detail": f"Setting '{key}' must be <= {rules['max']}."},
        )
    if (
        "allowed_values" in rules
        and value is not None
        and value not in rules["allowed_values"]
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "detail": f"Setting '{key}' must be one of {rules['allowed_values']}."
            },
        )


def _put_user_override_impl(
    key: str,
    payload: UserOverrideWriteRequest,
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
) -> UserOverrideWriteResponse:
    """Shared implementation for PUT /settings/{key}/user-override."""
    entry = _get_or_404_catalog_entry(key, db=db)

    if not entry.get("allows_user_override", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://pilotfortrades.com/errors/user-override-not-allowed",
                "title": "User Override Not Allowed",
                "status": 403,
                "detail": f"Setting '{key}' does not allow per-user overrides.",
            },
        )

    _validate_setting_value(key, payload.value)
    set_audit_context_sync(db, user_id)

    # Upsert: check if row exists
    existing = db.exec(
        select(UserSettingOverride)
        .where(UserSettingOverride.tenant_id == tenant_id)
        .where(UserSettingOverride.user_id == user_id)
        .where(UserSettingOverride.setting_key == key)
    ).first()

    if existing is not None:
        existing.value = payload.value
        existing.updated_by = user_id
        db.add(existing)
        db.commit()
        db.refresh(existing)
        updated_at = existing.updated_at
    else:
        new_row = UserSettingOverride(
            tenant_id=tenant_id,
            user_id=user_id,
            setting_key=key,
            value=payload.value,
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(new_row)
        db.commit()
        db.refresh(new_row)
        updated_at = new_row.updated_at

    _invalidate_user_settings_cache(tenant_id, user_id, "user")

    effective_value, scope = get_effective_setting_for_user(
        db=db, tenant_id=tenant_id, user_id=user_id, setting_key=key, fallback=None
    )

    return UserOverrideWriteResponse(
        key=key,
        value=payload.value,
        effective_value=effective_value,
        scope=scope,
        updated_at=updated_at,
    )


def _delete_user_override_impl(
    key: str,
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
) -> UserOverrideWriteResponse:
    """Shared implementation for DELETE /settings/{key}/user-override."""
    _get_or_404_catalog_entry(key, db=db)
    set_audit_context_sync(db, user_id)

    existing = db.exec(
        select(UserSettingOverride)
        .where(UserSettingOverride.tenant_id == tenant_id)
        .where(UserSettingOverride.user_id == user_id)
        .where(UserSettingOverride.setting_key == key)
    ).first()

    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://pilotfortrades.com/errors/user-override-not-found",
                "title": "No Override Found",
                "status": 404,
                "detail": f"No user override exists for setting '{key}'.",
            },
        )

    deleted_at = existing.updated_at
    db.delete(existing)
    db.commit()

    _invalidate_user_settings_cache(tenant_id, user_id, "user")

    # After deletion, resolve falls through to tenant/system
    effective_value, scope = get_effective_setting(
        db=db, tenant_id=tenant_id, setting_key=key, fallback=None
    )

    return UserOverrideWriteResponse(
        key=key,
        value=None,
        effective_value=effective_value,
        scope=scope,
        updated_at=deleted_at,
    )


# ===========================================================================
# TEST ENDPOINTS (registered FIRST to avoid /{key} swallowing /catalog etc.)
# ===========================================================================


@router.get(
    "/test/catalog",
    response_model=CatalogResponse,
    summary="[TEST] Get settings catalog — no auth required",
)
def get_catalog_test(db: Session = Depends(get_db)):
    """Test endpoint — no auth required. Blocked in staging/production."""
    test_ctx = get_test_context()
    return _get_catalog_impl(
        db=db,
        tenant_id=test_ctx.tenant_id,
        user_id=test_ctx.id,
        role_code="owner",
    )


@router.get(
    "/test/{key}/effective",
    response_model=EffectiveSettingResponse,
    summary="[TEST] Get effective setting value — no auth required",
)
def get_effective_setting_test(
    key: str,
    db: Session = Depends(get_db),
):
    """Test endpoint — no auth required. Blocked in staging/production."""
    test_ctx = get_test_context()
    return _get_effective_impl(
        key=key,
        resolve_user_id=test_ctx.id,
        db=db,
        current_tenant_id=test_ctx.tenant_id,
    )


@router.put(
    "/test/bulk",
    response_model=BulkSettingWriteResponse,
    summary="[TEST] Bulk write tenant settings — no auth required",
)
def bulk_put_settings_test(
    payload: BulkSettingWriteRequest,
    db: Session = Depends(get_db),
):
    """Test endpoint — no auth required. Blocked in staging/production."""
    test_ctx = get_test_context()
    return _bulk_write_impl(
        payload=payload, db=db, tenant_id=test_ctx.tenant_id, user_id=test_ctx.id
    )


@router.put(
    "/test/{key}",
    response_model=TenantSettingWriteResponse,
    summary="[TEST] Write tenant setting — no auth required",
)
def put_setting_test(
    key: str,
    payload: TenantSettingWriteRequest,
    db: Session = Depends(get_db),
):
    """Test endpoint — no auth required. Blocked in staging/production."""
    test_ctx = get_test_context()
    return _put_setting_impl(
        key=key,
        payload=payload,
        db=db,
        tenant_id=test_ctx.tenant_id,
        user_id=test_ctx.id,
    )


# FIND-158: renamed from /test/{key} → /test/{key}/tenant-override for symmetry with user-override pattern
@router.delete(
    "/test/{key}/tenant-override",
    response_model=TenantSettingWriteResponse,
    summary="[TEST] Revert tenant setting override — no auth required",
)
def delete_setting_test(
    key: str,
    db: Session = Depends(get_db),
):
    """Test endpoint — no auth required. Blocked in staging/production."""
    test_ctx = get_test_context()
    return _delete_setting_impl(
        key=key,
        db=db,
        tenant_id=test_ctx.tenant_id,
        user_id=test_ctx.id,
    )


@router.put(
    "/test/{key}/user-override",
    response_model=UserOverrideWriteResponse,
    summary="[TEST] Write user setting override — no auth required",
)
def put_user_override_test(
    key: str,
    payload: UserOverrideWriteRequest,
    db: Session = Depends(get_db),
):
    """Test endpoint — no auth required. Blocked in staging/production."""
    test_ctx = get_test_context()
    return _put_user_override_impl(
        key=key,
        payload=payload,
        db=db,
        tenant_id=test_ctx.tenant_id,
        user_id=test_ctx.id,
    )


@router.delete(
    "/test/{key}/user-override",
    response_model=UserOverrideWriteResponse,
    summary="[TEST] Delete user setting override — no auth required",
)
def delete_user_override_test(
    key: str,
    db: Session = Depends(get_db),
):
    """Test endpoint — no auth required. Blocked in staging/production."""
    test_ctx = get_test_context()
    return _delete_user_override_impl(
        key=key,
        db=db,
        tenant_id=test_ctx.tenant_id,
        user_id=test_ctx.id,
    )


# ===========================================================================
# AUTHENTICATED ENDPOINTS
# ===========================================================================


@router.get(
    "/catalog",
    response_model=CatalogResponse,
    summary="Get full settings catalog with resolved effective values",
)
def get_catalog(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("settings.read")),
):
    """
    Returns the full catalog of configurable settings for the requesting user's tenant,
    with current effective values resolved for the requesting user's role.
    Results are cached per-tenant per-user in Redis; invalidated on any settings write.
    """
    return _get_catalog_impl(
        db=db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        role_code=current_user.role_code,
    )


@router.get(
    "/{key}/effective",
    response_model=EffectiveSettingResponse,
    summary="Get resolved effective value for a single setting key",
)
def get_effective_setting_endpoint(
    key: str,
    user_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("settings.read")),
):
    """
    Returns the resolved effective value for a single setting key using the
    three-tier resolver (user → tenant → system → fallback).

    Optional query param `user_id` resolves for a specific user; if omitted,
    resolves for the requesting user. Callers without owner/accountant role
    cannot resolve for other users (403).
    """
    if user_id is not None and user_id != current_user.id:
        if current_user.role_code not in ("owner", "accountant"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "type": "https://pilotfortrades.com/errors/forbidden",
                    "title": "Forbidden",
                    "status": 403,
                    "detail": "You cannot resolve settings for another user without owner or accountant role.",
                },
            )

    resolve_user_id = user_id if user_id is not None else current_user.id
    return _get_effective_impl(
        key=key,
        resolve_user_id=resolve_user_id,
        db=db,
        current_tenant_id=current_user.tenant_id,
    )


@router.put(
    "/bulk",
    response_model=BulkSettingWriteResponse,
    summary="Atomically write multiple tenant settings in one commit",
)
def bulk_put_settings(
    payload: BulkSettingWriteRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("settings.tenant.write")
    ),
):
    """
    Write multiple tenant settings in a single DB commit. Required for
    'save_on_group_complete' keys (e.g., QB per-entity enabled+direction pairs).
    """
    return _bulk_write_impl(
        payload=payload,
        db=db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )


@router.put(
    "/{key}",
    response_model=TenantSettingWriteResponse,
    summary="Write a tenant-level setting override",
)
def put_setting(
    key: str,
    payload: TenantSettingWriteRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("settings.tenant.write")
    ),
):
    """
    Write a tenant-level setting. Validates the value against the catalog's
    validation_rules. Optional `expected_updated_at` triggers optimistic locking.
    Special case: `require_approval_for_tech_quotes` toggled OFF returns
    `pending_quote_count` for the UI confirmation dialog.
    """
    return _put_setting_impl(
        key=key,
        payload=payload,
        db=db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )


# FIND-158: renamed from /{key} → /{key}/tenant-override for symmetry with DELETE /{key}/user-override
@router.delete(
    "/{key}/tenant-override",
    response_model=TenantSettingWriteResponse,
    summary="Revert a tenant setting override to its system default",
)
def delete_setting(
    key: str,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("settings.tenant.write")
    ),
):
    """
    Revert a tenant setting override to its system default.

    ARCH-DECISION (FIND-158): Path renamed from DELETE /{key} to DELETE /{key}/tenant-override
    to create symmetry with DELETE /{key}/user-override. Both paths now follow the same
    "delete the override at this scope" convention:
      PUT  /{key}                  — write tenant override
      DELETE /{key}/tenant-override — remove tenant override (fall back to platform default)
      PUT  /{key}/user-override    — write user override
      DELETE /{key}/user-override  — remove user override

    For nullable columns: sets to NULL (resolver returns system default).
    For NOT NULL columns: sets to the SYSTEM_DEFAULTS constant value.
    Returns 400 if the catalog marks the setting as revertible: false.
    """
    return _delete_setting_impl(
        key=key,
        db=db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )


@router.put(
    "/{key}/user-override",
    response_model=UserOverrideWriteResponse,
    summary="Write a per-user setting override",
)
def put_user_override(
    key: str,
    payload: UserOverrideWriteRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("settings.user_override.write")
    ),
):
    """
    Write a user-level setting override (upsert). Only available for settings
    where `allows_user_override: True` in the catalog. Writes for the requesting
    user only — no admin write-on-behalf-of-user in MVP.
    """
    return _put_user_override_impl(
        key=key,
        payload=payload,
        db=db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )


@router.delete(
    "/{key}/user-override",
    response_model=UserOverrideWriteResponse,
    summary="Remove a per-user setting override (revert to tenant/system default)",
)
def delete_user_override(
    key: str,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(
        require_permission("settings.user_override.write")
    ),
):
    """
    Remove the user's override for a setting. The user falls back to the
    tenant or system default. Returns 404 if no override exists.
    """
    return _delete_user_override_impl(
        key=key,
        db=db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )


# ---------------------------------------------------------------------------
# B13/A68 — MFA Policy Endpoint
# ---------------------------------------------------------------------------


class MfaPolicyRequest(BaseModel):
    enabled: bool
    grace_period_days: int | None = None


class MfaPolicyResponse(BaseModel):
    tenant_mfa_required: bool
    grace_period_starts_at: datetime | None
    grace_period_days: int


def _put_mfa_policy_impl(
    body: MfaPolicyRequest,
    db: Session,
    tenant_id: UUID,
    user_id: UUID | None = None,
) -> MfaPolicyResponse:
    """Set tenant MFA required policy (post-FIND-086: uses platform_setting + tenant.mfa_grace_period_started_at)."""

    from app.models.auth import TenantUser
    from app.models.core import Tenant
    from app.models.security import MfaGracePeriodTracking

    now = datetime.now(UTC)
    grace_days = body.grace_period_days if body.grace_period_days is not None else 7

    # Read current mfa_required from platform_setting
    current_val, _ = get_effective_setting(
        db, tenant_id, "tenant_mfa_required", fallback=False
    )
    previously_disabled = not current_val

    # Upsert platform_setting values
    _upsert_platform_setting(
        db, tenant_id, "tenant_mfa_required", body.enabled, user_id=user_id
    )
    _upsert_platform_setting(
        db, tenant_id, "tenant_mfa_grace_period_days", grace_days, user_id=user_id
    )

    # Handle grace period start timestamp on tenant table
    tenant_row = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    if tenant_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        )

    grace_period_starts_at = getattr(tenant_row, "mfa_grace_period_started_at", None)
    if body.enabled and previously_disabled:
        tenant_row.mfa_grace_period_started_at = now  # type: ignore[assignment]
        grace_period_starts_at = now
        db.add(tenant_row)
        db.commit()

        # Seed grace period tracking for all active tenant users
        users = db.exec(
            select(TenantUser).where(TenantUser.tenant_id == tenant_id)
        ).all()
        for u in users:
            existing = db.exec(
                select(MfaGracePeriodTracking)
                .where(MfaGracePeriodTracking.tenant_id == tenant_id)
                .where(MfaGracePeriodTracking.user_id == u.user_id)
            ).first()
            if not existing:
                row = MfaGracePeriodTracking(
                    tenant_id=tenant_id,
                    user_id=u.user_id,
                    grace_started_at=now,
                )
                db.add(row)
        db.commit()

    return MfaPolicyResponse(
        tenant_mfa_required=body.enabled,
        grace_period_starts_at=grace_period_starts_at,
        grace_period_days=grace_days,
    )


def _get_mfa_policy_impl(
    db: Session,
    tenant_id: UUID,
) -> MfaPolicyResponse:
    """Read current tenant MFA policy from platform_setting + tenant row.

    Data sources (post-FIND-086):
      - tenant_mfa_required      → platform_setting.value  (key='tenant_mfa_required')
      - tenant_mfa_grace_period_days → platform_setting.value  (key='tenant_mfa_grace_period_days')
      - grace_period_starts_at   → tenant.mfa_grace_period_started_at
    """
    from app.models.core import Tenant

    # Read current mfa_required setting (defaults to False if not set)
    mfa_required, _ = get_effective_setting(
        db, tenant_id, "tenant_mfa_required", fallback=False
    )

    # Read grace period days (defaults to 7 if not set)
    grace_days_val, _ = get_effective_setting(
        db, tenant_id, "tenant_mfa_grace_period_days", fallback=7
    )
    grace_days = int(grace_days_val) if grace_days_val is not None else 7

    # Read grace period start timestamp from tenant row
    tenant_row = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    grace_period_starts_at = (
        getattr(tenant_row, "mfa_grace_period_started_at", None) if tenant_row else None
    )

    return MfaPolicyResponse(
        tenant_mfa_required=bool(mfa_required),
        grace_period_starts_at=grace_period_starts_at,
        grace_period_days=grace_days,
    )


# ==================== GET /tenant/mfa-required (registered BEFORE PUT — test first) ====================


@router.get("/tenant/mfa-required/test", response_model=MfaPolicyResponse)
def get_mfa_policy_test(db: Session = Depends(get_db)):
    """Test endpoint — no auth required. Returns current tenant MFA policy."""
    from uuid import UUID as _UUID

    ctx = get_test_context()
    return _get_mfa_policy_impl(db, _UUID(str(ctx.tenant_id)))


@router.get("/tenant/mfa-required", response_model=MfaPolicyResponse)
def get_mfa_policy(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("mfa.policy.edit")),
) -> MfaPolicyResponse:
    """Return current tenant MFA required policy (owner only).

    Response shape:
        { "tenant_mfa_required": bool, "grace_period_starts_at": datetime | null,
          "grace_period_days": int }
    """
    return _get_mfa_policy_impl(db, current_user.tenant_id)


# ==================== PUT /tenant/mfa-required ====================


@router.put("/tenant/mfa-required/test", response_model=MfaPolicyResponse)
def put_mfa_policy_test(body: MfaPolicyRequest, db: Session = Depends(get_db)):
    """Test endpoint — no auth required."""
    from uuid import UUID as _UUID

    ctx = get_test_context()
    return _put_mfa_policy_impl(body, db, _UUID(str(ctx.tenant_id)))


@router.put("/tenant/mfa-required", response_model=MfaPolicyResponse)
def put_mfa_policy(
    body: MfaPolicyRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("mfa.policy.edit")),
):
    """Set tenant MFA required policy (owner only)."""
    return _put_mfa_policy_impl(body, db, current_user.tenant_id)


# ---------------------------------------------------------------------------
# MOB-B8 — Background Sync Policy Endpoint
# ---------------------------------------------------------------------------


class BackgroundSyncPolicyResponse(BaseModel):
    background_sync_enabled: bool
    background_sync_wifi_only: bool
    background_sync_battery_floor_pct: int
    background_sync_push_interval_minutes: int


def _get_background_sync_policy_impl(
    db: Session,
    tenant_id: UUID,
) -> BackgroundSyncPolicyResponse:
    """
    Read effective background sync policy for a tenant using the three-tier resolver.
    Defaults: enabled=True, wifi_only=False, battery_floor=20, interval=5.
    """

    def _get(key: str, fallback):
        val, _ = get_effective_setting(db, tenant_id, key, fallback=fallback)
        return val

    return BackgroundSyncPolicyResponse(
        background_sync_enabled=bool(_get("background_sync_enabled", True)),
        background_sync_wifi_only=bool(_get("background_sync_wifi_only", False)),
        background_sync_battery_floor_pct=int(
            _get("background_sync_battery_floor_pct", 20)
        ),
        background_sync_push_interval_minutes=int(
            _get("background_sync_push_interval_minutes", 5)
        ),
    )


@router.get(
    "/background-sync-policy/test",
    response_model=BackgroundSyncPolicyResponse,
    summary="[TEST] Get tenant background sync policy — no auth required",
)
def get_background_sync_policy_test(
    db: Session = Depends(get_db),
) -> BackgroundSyncPolicyResponse:
    """Test endpoint — no JWT required. Returns tenant-effective background sync policy."""
    ctx = get_test_context()
    return _get_background_sync_policy_impl(db, ctx.tenant_id)


@router.get(
    "/background-sync-policy",
    response_model=BackgroundSyncPolicyResponse,
    summary="Get tenant background sync policy for mobile app",
)
def get_background_sync_policy(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("jobs.view")),
) -> BackgroundSyncPolicyResponse:
    """
    Returns the effective background sync policy for the authenticated user's tenant.
    Used by the mobile app on startup to configure OS background task intervals.
    All roles with jobs.view can read this (techs need it at app launch).
    """
    return _get_background_sync_policy_impl(db, current_user.tenant_id)


# ---------------------------------------------------------------------------
# MOB-B7 — LOTO Policy Endpoint
# ---------------------------------------------------------------------------


def _get_loto_policy_impl(
    db: Session,
    tenant_id: UUID,
) -> LotoPolicyResponse:
    """
    Read the tenant-effective LOTO policy from the three-tier resolver.
    Default = False (LOTO section is optional, not required).
    """
    value, _ = get_effective_setting(
        db, tenant_id, "loto_confirmation_required", fallback=False
    )
    return LotoPolicyResponse(loto_confirmation_required=bool(value))


# ==================== GET /settings/loto-policy (test endpoint FIRST) ====================


@router.get(
    "/loto-policy/test",
    response_model=LotoPolicyResponse,
    summary="[TEST] Get tenant LOTO policy — no auth required",
)
def get_loto_policy_test(
    db: Session = Depends(get_db),
) -> LotoPolicyResponse:
    """Test endpoint — no JWT required. Returns tenant-effective LOTO policy."""
    from core.test_context import get_test_context

    ctx = get_test_context()
    return _get_loto_policy_impl(db, ctx.tenant_id)


@router.get(
    "/loto-policy",
    response_model=LotoPolicyResponse,
    summary="Get tenant LOTO confirmation-required policy",
)
def get_loto_policy(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("jobs.view")),
) -> LotoPolicyResponse:
    """
    Returns the tenant-effective LOTO policy.
    All roles with jobs.view can read this (techs need it at clock-in).
    Default = false (LOTO section is optional, not required).
    """
    return _get_loto_policy_impl(db, current_user.tenant_id)
