"""
System-level configuration constants for platform-wide two-tier settings.
B6/A34 — First instantiation of mvp-arch.md §16.5 two-tier pattern.

All values are loaded from environment variables with hard-coded fallback
constants. Phase 2 will upgrade this to an admin-tier DB table.

Usage:
    from core.system_config import SystemConfig
    expire_days = SystemConfig.CALENDAR_CONFLICT_AUTO_EXPIRE_DAYS
"""

import os


class SystemConfig:
    """Platform-wide system defaults for two-tier settings (§16.5).

    These are the fallback values used when tenant_settings has NULL for
    the corresponding column, or when no tenant_settings row exists.

    All values can be overridden via environment variables for ops
    tuning without a code deploy.
    """

    # -----------------------------------------------------------------------
    # Calendar conflict auto-expiry defaults (B6/A34)
    # -----------------------------------------------------------------------

    CALENDAR_CONFLICT_AUTO_EXPIRE_DAYS: int = int(
        os.environ.get("SYSTEM_CALENDAR_CONFLICT_AUTO_EXPIRE_DAYS", "30")
    )
    """
    Default number of days before an unresolved calendar conflict is
    auto-resolved to 'accept_local'. Tenant can override via
    tenant_settings.calendar_conflict_auto_expire_days.
    """

    CALENDAR_CONFLICT_PRE_WARNING_DAYS: int = int(
        os.environ.get("SYSTEM_CALENDAR_CONFLICT_PRE_WARNING_DAYS", "7")
    )
    """
    Default number of days before auto-expiry at which a pre-warning
    notification is sent. Tenant can override via
    tenant_settings.calendar_conflict_pre_warning_days.
    Must be < CALENDAR_CONFLICT_AUTO_EXPIRE_DAYS.
    """
