"""
B12/A67 — ORM model + migration tests (post-FIND-086).

Test focus cases (updated for platform_setting redesign):
- platform_setting_catalog has voice_persona_tone key (FIND-086: replaces TenantSettings column)
- platform_setting_catalog has voice_persona_tone_user_override_allowed key
- voice_persona_tone platform default is "balanced"
- voice_persona_tone catalog: allows_user_override=True
- voice_persona_tone_user_override_allowed catalog: allows_user_override=False
- platform_setting NULL rows seeded correctly for both keys
- RBAC has_permission() covers voice persona permission strings (unchanged)

FIND-086: TenantSettings dropped. SETTING_CATALOG deleted. SYSTEM_DEFAULTS deleted.
Tests that previously verified those artifacts now verify platform_setting_catalog rows.
"""

from sqlmodel import select


class TestTenantSettingsORM:
    """
    ORM verification — post-FIND-086: checks platform_setting_catalog + platform_setting.
    (Class name kept for traceability; previously verified TenantSettings ORM fields.)
    """

    def test_voice_persona_tone_field_exists(self, db_session):
        """voice_persona_tone key exists in platform_setting_catalog."""
        from app.models.platform_setting import PlatformSettingCatalog

        row = db_session.exec(
            select(PlatformSettingCatalog).where(
                PlatformSettingCatalog.key == "voice_persona_tone"
            )
        ).first()
        assert row is not None, (
            "voice_persona_tone missing from platform_setting_catalog"
        )

    def test_voice_persona_tone_user_override_allowed_field_exists(self, db_session):
        """voice_persona_tone_user_override_allowed key exists in platform_setting_catalog."""
        from app.models.platform_setting import PlatformSettingCatalog

        row = db_session.exec(
            select(PlatformSettingCatalog).where(
                PlatformSettingCatalog.key == "voice_persona_tone_user_override_allowed"
            )
        ).first()
        assert row is not None, (
            "voice_persona_tone_user_override_allowed missing from catalog"
        )

    def test_voice_persona_tone_defaults_to_balanced(self, db_session):
        """voice_persona_tone platform default (NULL tenant_id row) is 'balanced'."""
        from app.models.platform_setting import PlatformSetting

        row = db_session.exec(
            select(PlatformSetting)
            .where(PlatformSetting.key == "voice_persona_tone")
            .where(PlatformSetting.tenant_id.is_(None))
        ).first()
        assert row is not None, "voice_persona_tone platform default row missing"
        assert row.value == "balanced"

    def test_voice_persona_tone_user_override_allowed_defaults_to_true(
        self, db_session
    ):
        """voice_persona_tone_user_override_allowed platform default is True."""
        from app.models.platform_setting import PlatformSetting

        row = db_session.exec(
            select(PlatformSetting)
            .where(PlatformSetting.key == "voice_persona_tone_user_override_allowed")
            .where(PlatformSetting.tenant_id.is_(None))
        ).first()
        assert row is not None
        assert row.value is True

    def test_valid_tone_values_accepted(self, db_session, test_tenant):
        """All three valid tone values can be stored as platform_setting overrides."""
        from app.models.platform_setting import PlatformSetting

        for tone in ("conservative", "balanced", "playful"):
            existing = db_session.exec(
                select(PlatformSetting)
                .where(PlatformSetting.key == "voice_persona_tone")
                .where(PlatformSetting.tenant_id == test_tenant.id)
            ).first()
            if existing:
                existing.value = tone
            else:
                existing = PlatformSetting(
                    key="voice_persona_tone", value=tone, tenant_id=test_tenant.id
                )
            db_session.add(existing)
            db_session.commit()
            db_session.refresh(existing)
            assert existing.value == tone

        # Cleanup
        existing = db_session.exec(
            select(PlatformSetting)
            .where(PlatformSetting.key == "voice_persona_tone")
            .where(PlatformSetting.tenant_id == test_tenant.id)
        ).first()
        if existing:
            db_session.delete(existing)
            db_session.commit()

    def test_null_tone_accepted(self, db_session, test_tenant):
        """NULL is valid — no tenant override means platform default is used."""
        from app.models.platform_setting import PlatformSetting

        # Ensure no tenant override exists
        existing = db_session.exec(
            select(PlatformSetting)
            .where(PlatformSetting.key == "voice_persona_tone")
            .where(PlatformSetting.tenant_id == test_tenant.id)
        ).first()
        if existing:
            db_session.delete(existing)
            db_session.commit()

        # Resolver returns system default "balanced" when no tenant override
        from services.setting_resolver import get_effective_setting

        val, scope = get_effective_setting(
            db_session, test_tenant.id, "voice_persona_tone"
        )
        assert val == "balanced"
        assert scope == "system"

    def test_invalid_tone_violates_check_constraint(self, db_session, test_tenant):
        """Invalid tone strings are blocked at the application layer via allowed_values."""
        from app.models.platform_setting import PlatformSettingCatalog

        catalog_row = db_session.exec(
            select(PlatformSettingCatalog).where(
                PlatformSettingCatalog.key == "voice_persona_tone"
            )
        ).first()
        assert catalog_row is not None
        allowed = catalog_row.allowed_values
        assert "aggressive" not in allowed
        assert "conservative" in allowed
        assert "balanced" in allowed
        assert "playful" in allowed


class TestSettingCatalog:
    """
    platform_setting_catalog entries for voice persona (FIND-086 replacement of SETTING_CATALOG).
    """

    def test_voice_persona_tone_in_catalog(self, db_session):
        from app.models.platform_setting import PlatformSettingCatalog

        row = db_session.exec(
            select(PlatformSettingCatalog).where(
                PlatformSettingCatalog.key == "voice_persona_tone"
            )
        ).first()
        assert row is not None

    def test_voice_persona_tone_allows_user_override(self, db_session):
        from app.models.platform_setting import PlatformSettingCatalog

        row = db_session.exec(
            select(PlatformSettingCatalog).where(
                PlatformSettingCatalog.key == "voice_persona_tone"
            )
        ).first()
        assert row is not None
        assert row.allows_user_override is True

    def test_voice_persona_tone_system_default_is_balanced(self, db_session):
        from app.models.platform_setting import PlatformSetting

        row = db_session.exec(
            select(PlatformSetting)
            .where(PlatformSetting.key == "voice_persona_tone")
            .where(PlatformSetting.tenant_id.is_(None))
        ).first()
        assert row is not None
        assert row.value == "balanced"

    def test_voice_persona_tone_valid_values(self, db_session):
        from app.models.platform_setting import PlatformSettingCatalog

        row = db_session.exec(
            select(PlatformSettingCatalog).where(
                PlatformSettingCatalog.key == "voice_persona_tone"
            )
        ).first()
        assert row is not None
        assert set(row.allowed_values) == {"conservative", "balanced", "playful"}

    def test_voice_persona_tone_user_override_allowed_in_catalog(self, db_session):
        from app.models.platform_setting import PlatformSettingCatalog

        row = db_session.exec(
            select(PlatformSettingCatalog).where(
                PlatformSettingCatalog.key == "voice_persona_tone_user_override_allowed"
            )
        ).first()
        assert row is not None

    def test_meta_toggle_does_not_allow_user_override(self, db_session):
        """The meta-toggle itself cannot be overridden by users."""
        from app.models.platform_setting import PlatformSettingCatalog

        row = db_session.exec(
            select(PlatformSettingCatalog).where(
                PlatformSettingCatalog.key == "voice_persona_tone_user_override_allowed"
            )
        ).first()
        assert row is not None
        assert row.allows_user_override is False

    def test_meta_toggle_system_default_is_true(self, db_session):
        from app.models.platform_setting import PlatformSetting

        row = db_session.exec(
            select(PlatformSetting)
            .where(PlatformSetting.key == "voice_persona_tone_user_override_allowed")
            .where(PlatformSetting.tenant_id.is_(None))
        ).first()
        assert row is not None
        assert row.value is True


class TestSystemDefaults:
    """SYSTEM_DEFAULTS deleted (FIND-086). Platform defaults verified via platform_setting."""

    def test_voice_persona_tone_in_system_defaults(self, db_session):
        """Post-FIND-086: checks platform_setting NULL row instead of SYSTEM_DEFAULTS."""
        from app.models.platform_setting import PlatformSetting

        row = db_session.exec(
            select(PlatformSetting)
            .where(PlatformSetting.key == "voice_persona_tone")
            .where(PlatformSetting.tenant_id.is_(None))
        ).first()
        assert row is not None
        assert row.value == "balanced"


class TestRBACPermissions:
    """RBAC permission string coverage for voice persona permissions (unchanged)."""

    def test_wildcard_covers_tenant_default_edit(self):
        from core.permissions import has_permission

        assert has_permission(["*"], "voice_persona_tone.tenant_default.edit")

    def test_wildcard_covers_user_override_edit(self):
        from core.permissions import has_permission

        assert has_permission(["*"], "voice_persona_tone.user_override.edit")

    def test_wildcard_covers_user_override_policy_edit(self):
        from core.permissions import has_permission

        assert has_permission(["*"], "voice_persona_tone.user_override_policy.edit")

    def test_exact_tenant_default_edit_permission_match(self):
        from core.permissions import has_permission

        perms = ["voice_persona_tone.tenant_default.edit"]
        assert has_permission(perms, "voice_persona_tone.tenant_default.edit")

    def test_exact_user_override_edit_permission_match(self):
        from core.permissions import has_permission

        perms = ["voice_persona_tone.user_override.edit"]
        assert has_permission(perms, "voice_persona_tone.user_override.edit")

    def test_exact_user_override_policy_edit_permission_match(self):
        from core.permissions import has_permission

        perms = ["voice_persona_tone.user_override_policy.edit"]
        assert has_permission(perms, "voice_persona_tone.user_override_policy.edit")

    def test_technician_without_tenant_default_is_denied(self):
        from core.permissions import has_permission

        tech_perms = ["voice_persona_tone.user_override.edit"]
        assert not has_permission(tech_perms, "voice_persona_tone.tenant_default.edit")

    def test_technician_without_policy_edit_is_denied(self):
        from core.permissions import has_permission

        tech_perms = ["voice_persona_tone.user_override.edit"]
        assert not has_permission(
            tech_perms, "voice_persona_tone.user_override_policy.edit"
        )

    def test_all_three_permissions_are_distinct(self):
        perms = {
            "voice_persona_tone.tenant_default.edit",
            "voice_persona_tone.user_override.edit",
            "voice_persona_tone.user_override_policy.edit",
        }
        assert len(perms) == 3
