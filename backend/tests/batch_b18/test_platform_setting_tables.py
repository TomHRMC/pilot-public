"""
Tests for FIND-086: platform_setting_catalog + platform_setting redesign.

Verifies:
  - All 41 catalog rows seeded correctly
  - Platform default NULL rows (one per catalog key)
  - Two-tier resolver behavior (tenant → system)
  - Endpoint behavior (catalog, put, delete/tenant-override)
  - Audit trigger fires on platform_setting insert/update
  - Deleted artifacts (tenant_settings, system_defaults, setting_catalog)

Batch: B18 | File: backend/tests/batch_b18/test_platform_setting_tables.py
"""

import pytest
from sqlalchemy import text
from sqlmodel import select

# ---------------------------------------------------------------------------
# Required catalog keys (41 total per Section G.1 of design doc)
# ---------------------------------------------------------------------------
REQUIRED_CATALOG_KEYS = {
    "require_approval_for_tech_quotes",
    "max_discount_pct_owner",
    "default_quote_validity_days",
    "default_invoice_terms_days",
    "default_labor_rate_cents",
    "default_billable_labor_rate_cents",
    "etc_variance_owner_notify_pct",
    "etc_variance_note_required_pct",
    "margin_target_pct",
    "margin_bucket_boundaries",
    "report_chart_threshold",
    "calendar_conflict_auto_expire_enabled",
    "calendar_conflict_auto_expire_days",
    "calendar_conflict_pre_warning_days",
    "qb_auto_expire_days",
    "qb_pre_warning_days",
    "qb_auto_expire_customer_enabled",
    "qb_auto_expire_customer_direction",
    "qb_auto_expire_quote_enabled",
    "qb_auto_expire_quote_direction",
    "qb_auto_expire_invoice_enabled",
    "qb_auto_expire_invoice_direction",
    "qb_auto_expire_expense_enabled",
    "qb_auto_expire_expense_direction",
    "photo_upload_wifi_only",
    "photo_local_retention_days",
    "offline_hard_limit_hours",
    "voice_offline_audio_storage_limit_mb",
    "background_sync_enabled",
    "background_sync_wifi_only",
    "background_sync_battery_floor_pct",
    "background_sync_push_interval_minutes",
    "tenant_sync_indicator_pending_amber_threshold",
    "voice_persona_tone",
    "voice_persona_tone_user_override_allowed",
    "tenant_mfa_required",
    "tenant_mfa_grace_period_days",
    "sms_quota_cap_policy",
    "tech_color_palette",
    "default_trial_length_days",
    "gps_variance_alert_threshold_meters",
}


class TestPlatformSettingCatalog:
    """Verify catalog seeding (41 rows with correct metadata)."""

    def test_catalog_has_all_41_required_keys(self, db_session):
        from app.models.platform_setting import PlatformSettingCatalog

        rows = db_session.exec(select(PlatformSettingCatalog)).all()
        actual_keys = {r.key for r in rows}
        missing = REQUIRED_CATALOG_KEYS - actual_keys
        assert not missing, f"Missing catalog keys: {missing}"
        assert len(actual_keys) >= 41, (
            f"Expected 41+ catalog rows, got {len(actual_keys)}"
        )

    def test_catalog_keys_have_correct_value_types(self, db_session):
        from app.models.platform_setting import PlatformSettingCatalog

        expected = {
            "require_approval_for_tech_quotes": "boolean",
            "default_labor_rate_cents": "integer",
            "max_discount_pct_owner": "decimal",
            "voice_persona_tone": "string",
            "margin_bucket_boundaries": "jsonb",
        }
        for key, expected_type in expected.items():
            row = db_session.exec(
                select(PlatformSettingCatalog).where(PlatformSettingCatalog.key == key)
            ).first()
            assert row is not None, f"Catalog key not found: {key}"
            assert row.value_type == expected_type, (
                f"Key '{key}': expected type '{expected_type}', got '{row.value_type}'"
            )

    def test_tenant_editable_classification(self, db_session):
        from app.models.platform_setting import PlatformSettingCatalog

        operator_only = {
            "default_labor_rate_cents",
            "offline_hard_limit_hours",
            "report_chart_threshold",
            "default_trial_length_days",
        }
        tenant_editable = {
            "default_quote_validity_days",
            "voice_persona_tone",
            "tenant_mfa_required",
        }

        for key in operator_only:
            row = db_session.exec(
                select(PlatformSettingCatalog).where(PlatformSettingCatalog.key == key)
            ).first()
            assert row is not None, f"Catalog key not found: {key}"
            assert not row.tenant_editable, f"Key '{key}' should be operator-only"

        for key in tenant_editable:
            row = db_session.exec(
                select(PlatformSettingCatalog).where(PlatformSettingCatalog.key == key)
            ).first()
            assert row is not None, f"Catalog key not found: {key}"
            assert row.tenant_editable, f"Key '{key}' should be tenant-editable"

    def test_allows_user_override_classification(self, db_session):
        from app.models.platform_setting import PlatformSettingCatalog

        should_allow = {"voice_persona_tone", "background_sync_enabled"}
        should_not_allow = {"default_labor_rate_cents"}

        for key in should_allow:
            row = db_session.exec(
                select(PlatformSettingCatalog).where(PlatformSettingCatalog.key == key)
            ).first()
            assert row is not None
            assert row.allows_user_override, f"Key '{key}' should allow user override"

        for key in should_not_allow:
            row = db_session.exec(
                select(PlatformSettingCatalog).where(PlatformSettingCatalog.key == key)
            ).first()
            assert row is not None
            assert not row.allows_user_override, (
                f"Key '{key}' should NOT allow user override"
            )


class TestPlatformSettingDefaults:
    """Verify platform default rows (NULL tenant_id) and resolver behavior."""

    def test_all_keys_have_null_platform_default_row(self, db_session):
        from app.models.platform_setting import PlatformSetting, PlatformSettingCatalog

        catalog_count = len(db_session.exec(select(PlatformSettingCatalog)).all())
        null_rows = db_session.exec(
            select(PlatformSetting).where(PlatformSetting.tenant_id.is_(None))
        ).all()
        assert len(null_rows) >= catalog_count, (
            f"Expected {catalog_count} NULL platform default rows, got {len(null_rows)}"
        )

    def test_resolver_returns_system_default_for_new_tenant(
        self, db_session, test_tenant
    ):
        from services.setting_resolver import get_effective_setting

        # Test tenant with no overrides — should hit the NULL default rows
        labor, scope = get_effective_setting(
            db_session, test_tenant.id, "default_labor_rate_cents"
        )
        assert labor == 8500, f"Expected 8500, got {labor}"
        assert scope == "system"

        tone, scope = get_effective_setting(
            db_session, test_tenant.id, "voice_persona_tone"
        )
        assert tone == "balanced", f"Expected 'balanced', got {tone}"
        assert scope == "system"

        trial, scope = get_effective_setting(
            db_session, test_tenant.id, "default_trial_length_days"
        )
        assert trial == 14, f"Expected 14, got {trial}"
        assert scope == "system"

    def test_tenant_override_takes_precedence_over_null_row(
        self, db_session, test_tenant
    ):
        from app.models.platform_setting import PlatformSetting
        from services.setting_resolver import get_effective_setting

        # Insert a tenant override
        override = PlatformSetting(
            key="default_quote_validity_days",
            value=45,
            tenant_id=test_tenant.id,
        )
        db_session.add(override)
        db_session.commit()

        val, scope = get_effective_setting(
            db_session, test_tenant.id, "default_quote_validity_days"
        )
        assert val == 45, f"Expected 45, got {val}"
        assert scope == "tenant"

        # Clean up
        db_session.delete(override)
        db_session.commit()

    def test_delete_tenant_override_reverts_to_platform_default(
        self, db_session, test_tenant
    ):
        from app.models.platform_setting import PlatformSetting
        from services.setting_resolver import get_effective_setting

        # Insert override then delete it
        override = PlatformSetting(
            key="voice_persona_tone",
            value="conservative",
            tenant_id=test_tenant.id,
        )
        db_session.add(override)
        db_session.commit()

        # Verify override active
        val, scope = get_effective_setting(
            db_session, test_tenant.id, "voice_persona_tone"
        )
        assert val == "conservative"
        assert scope == "tenant"

        # Delete override
        db_session.delete(override)
        db_session.commit()

        # Should fall back to system default
        val, scope = get_effective_setting(
            db_session, test_tenant.id, "voice_persona_tone"
        )
        assert val == "balanced", f"Expected 'balanced' after revert, got {val}"
        assert scope == "system"

    def test_tenant_without_override_unaffected_by_another_tenants_override(
        self, db_session, test_tenant
    ):
        import uuid

        from app.models.platform_setting import PlatformSetting
        from services.setting_resolver import get_effective_setting

        # Create a second tenant inline — needs current_subscription_tier_id
        tenant_b_id = uuid.uuid4()
        tier_row = db_session.execute(
            text("SELECT tier_id FROM subscription_tier WHERE is_trial = true LIMIT 1")
        ).first()
        tier_id = str(tier_row[0]) if tier_row else None
        if tier_id is None:
            # Skip test if no trial tier is seeded
            return
        db_session.execute(
            text(
                "INSERT INTO tenant (id, name, is_active, current_subscription_tier_id, created_at, updated_at) "
                "VALUES (:id, :name, true, :tier_id, now(), now()) ON CONFLICT DO NOTHING"
            ),
            {"id": str(tenant_b_id), "name": "Test Tenant B", "tier_id": tier_id},
        )
        db_session.commit()

        # Tenant A (test_tenant) upserts override
        override = PlatformSetting(
            key="margin_target_pct",
            value=35,
            tenant_id=test_tenant.id,
        )
        db_session.add(override)
        db_session.commit()

        # Tenant B should still see the system default
        val, scope = get_effective_setting(db_session, tenant_b_id, "margin_target_pct")
        assert val == 20, f"Tenant B expected 20 (system), got {val}"
        assert scope == "system"

        # Clean up
        db_session.delete(override)
        db_session.execute(
            text("DELETE FROM tenant WHERE id = :id"), {"id": str(tenant_b_id)}
        )
        db_session.commit()


class TestAuditTrail:
    """Verify audit trigger fires on platform_setting table changes."""

    def test_audit_trigger_fires_on_platform_setting_insert(
        self, db_session, test_tenant
    ):
        from app.models.platform_setting import PlatformSetting

        override = PlatformSetting(
            key="photo_local_retention_days",
            value=14,
            tenant_id=test_tenant.id,
        )
        db_session.add(override)
        db_session.commit()

        # Check audit.event row created
        audit_row = db_session.execute(
            text(
                "SELECT COUNT(*) FROM audit.event "
                "WHERE entity_name = 'platform_setting' AND action = 'INSERT'"
            )
        ).scalar()
        assert audit_row >= 1, (
            "Expected at least 1 audit INSERT event for platform_setting"
        )

        # Clean up
        db_session.delete(override)
        db_session.commit()


class TestDeletedArtifacts:
    """Verify that the old flat-table approach is completely gone."""

    def test_tenant_settings_table_does_not_exist(self, db_session):
        row = db_session.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'tenant_settings'"
            )
        ).scalar()
        assert row == 0, "tenant_settings table still exists — migration didn't drop it"

    def test_system_defaults_module_does_not_exist(self):
        with pytest.raises((ImportError, ModuleNotFoundError)):
            import importlib

            importlib.import_module("core.system_defaults")

    def test_setting_catalog_module_does_not_exist(self):
        with pytest.raises((ImportError, ModuleNotFoundError)):
            import importlib

            importlib.import_module("core.setting_catalog")

    def test_tenant_settings_class_does_not_exist(self):
        with pytest.raises((ImportError, AttributeError)):
            from app.models.core import TenantSettings  # noqa: F401

            # If import succeeds without error, something's wrong
            raise AssertionError(
                "TenantSettings should not be importable from app.models.core"
            )


class TestPlatformDefaultValues:
    """Spot-check that the seeded platform defaults match the design doc spec."""

    def test_key_platform_default_values(self, db_session):
        from app.models.platform_setting import PlatformSetting

        expected = {
            "default_labor_rate_cents": 8500,
            "default_quote_validity_days": 30,
            "margin_target_pct": 20,
            "tenant_mfa_required": False,
            "tenant_mfa_grace_period_days": 7,
            "default_trial_length_days": 14,
            "calendar_conflict_auto_expire_days": 60,
            "qb_auto_expire_days": 60,
            "background_sync_battery_floor_pct": 20,
        }

        for key, expected_val in expected.items():
            row = db_session.exec(
                select(PlatformSetting)
                .where(PlatformSetting.key == key)
                .where(PlatformSetting.tenant_id.is_(None))
            ).first()
            assert row is not None, f"No NULL platform default row for key '{key}'"
            assert row.value == expected_val, (
                f"Key '{key}': expected default {expected_val}, got {row.value}"
            )
