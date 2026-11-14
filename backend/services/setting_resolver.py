"""
Two-tier settings resolver for Pilot for Trades (post-FIND-086 platform_setting redesign).

Resolution chain:
  User override (if tenant allows) → Tenant override (platform_setting WHERE tenant_id=X)
  → Platform default (platform_setting WHERE tenant_id IS NULL)
  → FAIL FAST (missing default row is a data integrity error, not a code fallback)

The `fallback` parameter is kept for backward compatibility with callers that pass it,
but after migration there should always be a NULL row for every catalog key.
If neither a tenant row nor a NULL row is found, the fallback is returned WITH A WARNING log.

Replaces the flat TenantSettings + SYSTEM_DEFAULTS + SETTING_CATALOG approach (FIND-086).
"""

import logging
from typing import Any
from uuid import UUID

from sqlmodel import Session, or_, select

from app.models.platform_setting import PlatformSetting, PlatformSettingCatalog
from app.models.settings import UserSettingOverride

logger = logging.getLogger(__name__)


def get_effective_setting(
    db: Session,
    tenant_id: UUID,
    setting_key: str,
    fallback: Any = None,
) -> tuple[Any, str]:
    """
    Two-tier resolver: tenant override → platform default → fallback.

    Single SQL:
        SELECT value FROM platform_setting
        WHERE key=:key AND (tenant_id=:tid OR tenant_id IS NULL)
        ORDER BY tenant_id NULLS LAST LIMIT 1

    Returns:
        (value, scope) where scope is 'tenant' | 'system' | 'fallback'
    """
    row = db.exec(
        select(PlatformSetting)
        .where(PlatformSetting.key == setting_key)
        .where(
            or_(
                PlatformSetting.tenant_id == tenant_id,
                PlatformSetting.tenant_id.is_(None),
            )
        )
        .order_by(PlatformSetting.tenant_id.nulls_last())
        .limit(1)
    ).first()

    if row is None:
        logger.warning(
            "get_effective_setting: no platform_setting row for key=%s "
            "(missing seed data?); returning fallback=%s",
            setting_key,
            fallback,
        )
        return fallback, "fallback"

    scope = "tenant" if row.tenant_id is not None else "system"
    return row.value, scope


def get_effective_setting_for_user(
    db: Session,
    tenant_id: UUID,
    user_id: UUID,
    setting_key: str,
    fallback: Any = None,
) -> tuple[Any, str]:
    """
    Three-tier resolver: user override → tenant override → platform default → fallback.

    Only applies the user tier when the catalog + meta-toggle allow it.

    Returns:
        (value, scope) where scope is 'user' | 'tenant' | 'system' | 'fallback'
    """
    if setting_allows_user_override_for_tenant(db, tenant_id, setting_key):
        user_override = db.exec(
            select(UserSettingOverride)
            .where(UserSettingOverride.tenant_id == tenant_id)
            .where(UserSettingOverride.user_id == user_id)
            .where(UserSettingOverride.setting_key == setting_key)
        ).first()

        if user_override is not None:
            return user_override.value, "user"

    return get_effective_setting(db, tenant_id, setting_key, fallback)


def setting_allows_user_override_for_tenant(
    db: Session,
    tenant_id: UUID,
    setting_key: str,
) -> bool:
    """
    Returns True if the tenant allows per-user overrides for this setting.

    Checks:
    1. catalog row has allows_user_override=True
    2. Tenant's platform_setting value for '{setting_key}_user_override_allowed' is True
       (only if such a catalog row exists)
    """
    catalog_row = db.exec(
        select(PlatformSettingCatalog).where(PlatformSettingCatalog.key == setting_key)
    ).first()

    if catalog_row is None:
        return False

    if not catalog_row.allows_user_override:
        return False

    # Per-setting meta-toggle: check the '_user_override_allowed' companion key
    meta_toggle_key = f"{setting_key}_user_override_allowed"
    meta_value, _ = get_effective_setting(db, tenant_id, meta_toggle_key, fallback=True)
    if meta_value is False:
        return False

    return True
