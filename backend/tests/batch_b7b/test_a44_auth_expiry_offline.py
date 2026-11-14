"""
tests/batch_b7b/test_a44_auth_expiry_offline.py

Tests for B7b/A44 — Auth Expiry Offline Handling (post-FIND-086 update).

FIND-086: tenant_settings table dropped. offline/photo policy settings now live in
platform_setting_catalog + platform_setting tables.

Tests updated to:
  - Check platform_setting_catalog for key presence and value_type
  - Check platform_setting NULL rows for default values
  - Use platform_setting upsert instead of raw SQL UPDATE on tenant_settings
"""

from __future__ import annotations

from sqlmodel import select


class TestA44AuthExpiryOfflineColumn:
    def test_offline_hard_limit_hours_column_exists(self, db_session):
        """Key exists in platform_setting_catalog with integer type, nullable (FIND-086)."""
        from app.models.platform_setting import PlatformSettingCatalog

        row = db_session.exec(
            select(PlatformSettingCatalog).where(
                PlatformSettingCatalog.key == "offline_hard_limit_hours"
            )
        ).first()
        assert row is not None, (
            "offline_hard_limit_hours missing from platform_setting_catalog"
        )
        assert row.value_type == "integer"
        # Not tenant_editable (operator-only)
        assert row.tenant_editable is False

    def test_photo_upload_wifi_only_column_exists(self, db_session):
        """photo_upload_wifi_only exists in catalog, boolean type."""
        from app.models.platform_setting import PlatformSettingCatalog

        row = db_session.exec(
            select(PlatformSettingCatalog).where(
                PlatformSettingCatalog.key == "photo_upload_wifi_only"
            )
        ).first()
        assert row is not None, (
            "photo_upload_wifi_only missing from platform_setting_catalog"
        )
        assert row.value_type == "boolean"

    def test_photo_local_retention_days_column_exists(self, db_session):
        """photo_local_retention_days exists in catalog with integer type."""
        from app.models.platform_setting import PlatformSettingCatalog

        row = db_session.exec(
            select(PlatformSettingCatalog).where(
                PlatformSettingCatalog.key == "photo_local_retention_days"
            )
        ).first()
        assert row is not None, (
            "photo_local_retention_days missing from platform_setting_catalog"
        )
        assert row.value_type == "integer"

    def test_voice_offline_audio_storage_limit_mb_column_exists(self, db_session):
        """voice_offline_audio_storage_limit_mb exists in catalog with integer type."""
        from app.models.platform_setting import PlatformSettingCatalog

        row = db_session.exec(
            select(PlatformSettingCatalog).where(
                PlatformSettingCatalog.key == "voice_offline_audio_storage_limit_mb"
            )
        ).first()
        assert row is not None, (
            "voice_offline_audio_storage_limit_mb missing from catalog"
        )
        assert row.value_type == "integer"

    def test_offline_hard_limit_hours_can_be_set_to_integer(
        self, db_session, test_tenant
    ):
        """Setting offline_hard_limit_hours to an integer persists via platform_setting (FIND-086)."""
        from app.models.platform_setting import PlatformSetting
        from services.setting_resolver import get_effective_setting

        override = PlatformSetting(
            key="offline_hard_limit_hours",
            value=72,
            tenant_id=test_tenant.id,
        )
        db_session.add(override)
        db_session.commit()

        val, scope = get_effective_setting(
            db_session, test_tenant.id, "offline_hard_limit_hours"
        )
        assert val == 72
        assert scope == "tenant"

        # Cleanup
        db_session.delete(override)
        db_session.commit()

    def test_offline_hard_limit_hours_can_be_set_to_null(self, db_session, test_tenant):
        """Without a tenant override, resolver returns platform default (72) not None."""
        from app.models.platform_setting import PlatformSetting
        from services.setting_resolver import get_effective_setting

        # Ensure no tenant override
        existing = db_session.exec(
            select(PlatformSetting)
            .where(PlatformSetting.key == "offline_hard_limit_hours")
            .where(PlatformSetting.tenant_id == test_tenant.id)
        ).first()
        if existing:
            db_session.delete(existing)
            db_session.commit()

        val, scope = get_effective_setting(
            db_session, test_tenant.id, "offline_hard_limit_hours", fallback=None
        )
        assert val == 72  # platform default
        assert scope == "system"
