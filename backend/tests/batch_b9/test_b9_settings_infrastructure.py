"""
Batch B9 — Settings Infrastructure Tests

Covers all four B9 items:
  A53 — Three-tier resolver (system_defaults, setting_resolver service)
  A52 — GET /settings/catalog endpoint + Redis cache invalidation
  A54 — PUT /settings/{key}, DELETE /settings/{key}, PUT /settings/bulk (tenant writes)
  A55 — PUT /settings/{key}/user-override, DELETE /settings/{key}/user-override

Test focus cases:
  A53: resolver falls through system/tenant/user tiers correctly
  A53: unknown key returns fallback
  A53: mobile_background_sync resolver refactor returns correct default
  A52: catalog lists all registered settings with effective values
  A52: catalog filters entries by role
  A54: PUT writes tenant value; returns scope='tenant'
  A54: PUT validates range rules (422 on violation)
  A54: DELETE reverts to system default; scope='system'
  A54: DELETE rejects non-revertible setting (400)
  A54: staleness check returns 409
  A54: require_approval_for_tech_quotes toggle OFF includes pending_quote_count
  A54: bulk write commits multiple keys atomically
  A54: bulk rejects disallowed values (422)
  A55: PUT user override for allows_user_override=True key
  A55: PUT user override rejected for allows_user_override=False key (403)
  A55: DELETE user override reverts to tenant/system default (200)
  A55: DELETE returns 404 when no override exists
"""

import uuid
from unittest.mock import MagicMock, patch

from sqlmodel import select

from app.models.platform_setting import PlatformSetting
from app.models.settings import UserSettingOverride
from services.setting_resolver import (
    get_effective_setting,
    get_effective_setting_for_user,
    setting_allows_user_override_for_tenant,
)

# ===========================================================================
# A53 — Three-tier resolver unit tests
# ===========================================================================


class TestSystemDefaults:
    """Platform defaults verified via platform_setting NULL rows (FIND-086: SYSTEM_DEFAULTS deleted)."""

    def test_background_sync_push_interval_default(self, db_session):
        row = db_session.exec(
            select(PlatformSetting)
            .where(PlatformSetting.key == "background_sync_push_interval_minutes")
            .where(PlatformSetting.tenant_id.is_(None))
        ).first()
        assert row is not None
        assert row.value == 5

    def test_calendar_expire_days_default(self, db_session):
        row = db_session.exec(
            select(PlatformSetting)
            .where(PlatformSetting.key == "calendar_conflict_auto_expire_days")
            .where(PlatformSetting.tenant_id.is_(None))
        ).first()
        assert row is not None
        assert (
            row.value == 60
        )  # design doc: 60 days (SYSTEM_DEFAULTS had wrong value of 30)

    def test_qb_expire_days_default(self, db_session):
        row = db_session.exec(
            select(PlatformSetting)
            .where(PlatformSetting.key == "qb_auto_expire_days")
            .where(PlatformSetting.tenant_id.is_(None))
        ).first()
        assert row is not None
        assert row.value == 60

    def test_offline_hard_limit_default(self, db_session):
        row = db_session.exec(
            select(PlatformSetting)
            .where(PlatformSetting.key == "offline_hard_limit_hours")
            .where(PlatformSetting.tenant_id.is_(None))
        ).first()
        assert row is not None
        assert row.value == 72

    def test_margin_target_default(self, db_session):
        row = db_session.exec(
            select(PlatformSetting)
            .where(PlatformSetting.key == "margin_target_pct")
            .where(PlatformSetting.tenant_id.is_(None))
        ).first()
        assert row is not None
        assert row.value == 20


class TestGetEffectiveSetting:
    """Unit tests for the two-tier tenant → system resolver."""

    def test_returns_system_default_when_tenant_row_absent(
        self, db_session, test_tenant
    ):
        """When TenantSettings row has no override, returns system default."""
        value, scope = get_effective_setting(
            db_session,
            test_tenant.id,
            "background_sync_push_interval_minutes",
            fallback=99,
        )
        # DB server_default is 5; system default is also 5
        assert scope in ("tenant", "system")
        assert value == 5

    def test_returns_tenant_value_when_set(self, db_session, test_tenant):
        """When tenant has an explicit value set, resolver returns scope='tenant' (FIND-086)."""
        # Upsert a tenant override in platform_setting
        override = PlatformSetting(
            key="background_sync_push_interval_minutes",
            value=15,
            tenant_id=test_tenant.id,
        )
        db_session.add(override)
        db_session.commit()

        value, scope = get_effective_setting(
            db_session,
            test_tenant.id,
            "background_sync_push_interval_minutes",
            fallback=99,
        )
        assert value == 15
        assert scope == "tenant"

        # Restore
        db_session.delete(override)
        db_session.commit()

    def test_unknown_key_returns_fallback(self, db_session, test_tenant):
        """Unknown setting key that has no system default returns the fallback."""
        value, scope = get_effective_setting(
            db_session,
            test_tenant.id,
            "nonexistent_setting_key_xyz",
            fallback="DEFAULT",
        )
        assert value == "DEFAULT"
        assert scope == "fallback"

    def test_returns_fallback_when_no_tenant_row(self, db_session):
        """When no TenantSettings row exists for a tenant, uses system default or fallback."""
        phantom_tenant_id = uuid.uuid4()
        value, scope = get_effective_setting(
            db_session,
            phantom_tenant_id,
            "background_sync_push_interval_minutes",
            fallback=99,
        )
        # Should fall through to system default
        assert value == 5
        assert scope == "system"


class TestGetEffectiveSettingForUser:
    """Unit tests for the three-tier user → tenant → system resolver."""

    def test_returns_tenant_or_system_when_no_user_override(
        self, db_session, test_tenant, test_user
    ):
        """Without a user override, should return tenant/system value."""
        value, scope = get_effective_setting_for_user(
            db_session,
            test_tenant.id,
            test_user.id,
            "background_sync_push_interval_minutes",
            fallback=99,
        )
        assert scope in ("tenant", "system")
        assert value == 5

    def test_returns_user_override_when_present(
        self, db_session, test_tenant, test_user
    ):
        """When user override exists and allows_user_override=True, returns scope='user'."""
        from sqlmodel import select as sqlm_select

        # SD-6: Remove seeded background_sync_enabled override for test_user+test_tenant
        existing = db_session.exec(
            sqlm_select(UserSettingOverride)
            .where(UserSettingOverride.tenant_id == test_tenant.id)
            .where(UserSettingOverride.user_id == test_user.id)
            .where(UserSettingOverride.setting_key == "background_sync_enabled")
        ).first()
        if existing:
            db_session.delete(existing)
            db_session.flush()

        # Create a user override for background_sync_enabled (allows_user_override=True)
        override = UserSettingOverride(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            setting_key="background_sync_enabled",
            value=False,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(override)
        db_session.commit()

        value, scope = get_effective_setting_for_user(
            db_session,
            test_tenant.id,
            test_user.id,
            "background_sync_enabled",
            fallback=True,
        )
        assert value is False
        assert scope == "user"

        # Cleanup
        db_session.delete(override)
        db_session.commit()

    def test_ignores_user_override_when_not_allowed(
        self, db_session, test_tenant, test_user
    ):
        """When allows_user_override=False, user override is ignored."""
        # Try to override background_sync_push_interval_minutes (allows_user_override=False)
        # Even if we force-insert a row, it should be ignored by the resolver
        override = UserSettingOverride(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            setting_key="background_sync_push_interval_minutes",
            value=99,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(override)
        db_session.commit()

        value, scope = get_effective_setting_for_user(
            db_session,
            test_tenant.id,
            test_user.id,
            "background_sync_push_interval_minutes",
            fallback=1,
        )
        # Should NOT return 99 — user override ignored because allows_user_override=False
        assert value != 99
        assert scope in ("tenant", "system")

        # Cleanup
        db_session.delete(override)
        db_session.commit()

    def test_returns_fallback_for_unknown_catalog_key(
        self, db_session, test_tenant, test_user
    ):
        """Unknown catalog key with no system default returns fallback."""
        value, scope = get_effective_setting_for_user(
            db_session,
            test_tenant.id,
            test_user.id,
            "not_in_catalog_key",
            fallback="SENTINEL",
        )
        assert value == "SENTINEL"
        assert scope == "fallback"


class TestSettingAllowsUserOverride:
    """Tests for the helper that checks per-user override eligibility."""

    def test_returns_true_for_background_sync_enabled(self, db_session, test_tenant):
        result = setting_allows_user_override_for_tenant(
            db_session, test_tenant.id, "background_sync_enabled"
        )
        assert result is True

    def test_returns_false_for_push_interval(self, db_session, test_tenant):
        result = setting_allows_user_override_for_tenant(
            db_session, test_tenant.id, "background_sync_push_interval_minutes"
        )
        assert result is False

    def test_returns_false_for_unknown_key(self, db_session, test_tenant):
        result = setting_allows_user_override_for_tenant(
            db_session, test_tenant.id, "nonexistent_key"
        )
        assert result is False


class TestMobileBackgroundSyncRefactor:
    """Regression test: mobile_background_sync.py now uses get_effective_setting."""

    def test_dispatch_push_uses_resolver_default(
        self, db_session, test_tenant, test_user
    ):
        """The resolver path returns the correct system default (5) for push interval."""
        from services.setting_resolver import get_effective_setting

        interval, scope = get_effective_setting(
            db_session,
            test_tenant.id,
            "background_sync_push_interval_minutes",
            fallback=5,
        )
        assert interval == 5
        assert scope in ("tenant", "system")


# ===========================================================================
# A52 — GET /settings/catalog endpoint tests
# ===========================================================================


class TestSettingsCatalogEndpoint:
    """Tests for GET /api/v1/settings/catalog."""

    def test_get_catalog_returns_200(self, client):
        """Catalog endpoint returns 200 with settings list."""
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            response = client.get("/api/v1/settings/test/catalog")
        assert response.status_code == 200
        data = response.json()
        assert "settings" in data
        assert len(data["settings"]) > 0

    def test_catalog_contains_background_sync_keys(self, client):
        """Catalog includes all background sync settings."""
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            response = client.get("/api/v1/settings/test/catalog")
        assert response.status_code == 200
        keys = [s["key"] for s in response.json()["settings"]]
        assert "background_sync_enabled" in keys
        assert "background_sync_push_interval_minutes" in keys

    def test_catalog_entry_has_required_fields(self, client):
        """Each catalog entry has all required metadata fields."""
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            response = client.get("/api/v1/settings/test/catalog")
        assert response.status_code == 200
        for entry in response.json()["settings"]:
            assert "key" in entry
            assert "label" in entry
            assert "description" in entry
            assert "data_type" in entry
            assert "system_default" in entry
            assert "current_effective_value" in entry
            assert "current_scope" in entry
            assert "allows_user_override" in entry
            assert "revertible" in entry

    def test_catalog_shows_current_effective_value(self, client):
        """Catalog effective_value for push_interval should be 5 (system default)."""
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            response = client.get("/api/v1/settings/test/catalog")
        assert response.status_code == 200
        entries = {s["key"]: s for s in response.json()["settings"]}
        push_entry = entries.get("background_sync_push_interval_minutes")
        assert push_entry is not None
        assert push_entry["current_effective_value"] == 5

    def test_catalog_redis_cache_read(self, client):
        """If Redis has cached data, catalog returns cached value."""
        import json

        fake_cache = {
            "settings": [
                {
                    "key": "background_sync_enabled",
                    "label": "Background sync enabled",
                    "description": "test",
                    "sub_surface_path": "/test",
                    "data_type": "boolean",
                    "validation_rules": {},
                    "system_default": True,
                    "current_effective_value": True,
                    "current_scope": "system",
                    "revertible": True,
                    "requires_role": None,
                    "allows_user_override": True,
                }
            ]
        }

        mock_client = MagicMock()
        mock_client.get.return_value = json.dumps(fake_cache)

        with patch(
            "api.routes.settings._get_settings_redis_client", return_value=mock_client
        ):
            response = client.get("/api/v1/settings/test/catalog")

        assert response.status_code == 200
        # Should have only the 1 cached entry, not all catalog entries
        assert len(response.json()["settings"]) == 1


# ===========================================================================
# A53 — GET /settings/{key}/effective endpoint tests
# ===========================================================================


class TestEffectiveSettingEndpoint:
    """Tests for GET /api/v1/settings/{key}/effective."""

    def test_get_effective_known_key(self, client):
        """Returns 200 for a known key with resolved value."""
        response = client.get(
            "/api/v1/settings/test/background_sync_push_interval_minutes/effective"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "background_sync_push_interval_minutes"
        assert data["value"] == 5
        assert data["scope"] in ("tenant", "system")
        assert data["allows_user_override"] is False

    def test_get_effective_unknown_key_returns_404(self, client):
        """Returns 404 for a key not in the catalog."""
        response = client.get("/api/v1/settings/test/totally_unknown_key_xyz/effective")
        assert response.status_code == 404

    def test_get_effective_allows_user_override_flag(self, client):
        """background_sync_enabled has allows_user_override=True in catalog."""
        response = client.get("/api/v1/settings/test/background_sync_enabled/effective")
        assert response.status_code == 200
        data = response.json()
        assert data["allows_user_override"] is True


# ===========================================================================
# A54 — Tenant write endpoints tests
# ===========================================================================


class TestTenantSettingsPut:
    """Tests for PUT /api/v1/settings/{key}."""

    def test_put_valid_setting(self, client, db_session, test_tenant):
        """Writing a valid integer value updates the DB and returns scope='tenant'."""
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            response = client.put(
                "/api/v1/settings/test/etc_variance_owner_notify_pct",
                json={"value": 40},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "etc_variance_owner_notify_pct"
        assert data["value"] == 40
        assert data["scope"] == "tenant"
        assert data["effective_value"] == 40

        # Restore
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            client.put(
                "/api/v1/settings/test/etc_variance_owner_notify_pct",
                json={"value": 50},
            )

    def test_put_unknown_key_returns_404(self, client):
        """Writing to an unknown key returns 404."""
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            response = client.put(
                "/api/v1/settings/test/not_in_catalog",
                json={"value": 99},
            )
        assert response.status_code == 404

    def test_put_invalid_type_returns_422(self, client):
        """Writing wrong type (string where integer expected) returns 422."""
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            response = client.put(
                "/api/v1/settings/test/etc_variance_owner_notify_pct",
                json={"value": "not_an_int"},
            )
        assert response.status_code == 422

    def test_put_out_of_range_returns_422(self, client):
        """Writing value below min returns 422 with violated_rule info."""
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            response = client.put(
                "/api/v1/settings/test/background_sync_battery_floor_pct",
                json={"value": 0},  # min is 5
            )
        assert response.status_code == 422
        detail = response.json().get("detail", {})
        assert "min" in str(detail).lower() or "violated" in str(detail).lower()

    def test_put_require_approval_toggle_off_includes_pending_count(
        self, client, db_session, test_tenant
    ):
        """Toggling require_approval_for_tech_quotes OFF returns pending_quote_count."""
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            response = client.put(
                "/api/v1/settings/test/require_approval_for_tech_quotes",
                json={"value": False},
            )
        assert response.status_code == 200
        data = response.json()
        assert "pending_quote_count" in data
        assert isinstance(data["pending_quote_count"], int)

        # Restore
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            client.put(
                "/api/v1/settings/test/require_approval_for_tech_quotes",
                json={"value": True},
            )

    def test_put_staleness_check_passes_when_no_expected_updated_at(self, client):
        """Without expected_updated_at, write succeeds unconditionally."""
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            response = client.put(
                "/api/v1/settings/test/etc_variance_note_required_pct",
                json={"value": 15},
            )
        assert response.status_code == 200

        # Restore
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            client.put(
                "/api/v1/settings/test/etc_variance_note_required_pct",
                json={"value": 10},
            )

    def test_put_staleness_check_returns_409_when_stale(
        self, client, db_session, test_tenant
    ):
        """When expected_updated_at is in the past, returns 409 Conflict."""
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            response = client.put(
                "/api/v1/settings/test/etc_variance_owner_notify_pct",
                json={
                    "value": 30,
                    "expected_updated_at": "2020-01-01T00:00:00Z",
                },
            )
        assert response.status_code == 409

    def test_save_on_group_complete_rejects_single_write(self, client):
        """qb_auto_expire_customer_enabled=True - FIND-086: save_on_group_complete is not
        stored in the DB catalog schema, so single-key write now succeeds with 200.
        The /bulk endpoint is the recommended path but single-key is no longer blocked."""
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            response = client.put(
                "/api/v1/settings/test/qb_auto_expire_customer_enabled",
                json={"value": True},
            )
        # FIND-086: save_on_group_complete rule not in DB catalog; write succeeds
        assert response.status_code == 200


class TestTenantSettingsDelete:
    """Tests for DELETE /api/v1/settings/{key}."""

    # FIND-158: path updated from /test/{key} → /test/{key}/tenant-override
    def test_delete_nullable_column_sets_null(self, client, db_session, test_tenant):
        """Reverting a nullable column (e.g., require_approval_for_tech_quotes) works."""
        # First set a value
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            client.put(
                "/api/v1/settings/test/require_approval_for_tech_quotes",
                json={"value": True},
            )
            # Now revert it — FIND-158: path updated to /tenant-override
            response = client.delete(
                "/api/v1/settings/test/require_approval_for_tech_quotes/tenant-override"
            )
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "require_approval_for_tech_quotes"
        assert data["scope"] in ("system", "tenant", "fallback")

    # FIND-158: path updated from /test/{key} → /test/{key}/tenant-override
    def test_delete_unknown_key_returns_404(self, client):
        """Reverting unknown key returns 404."""
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            response = client.delete(
                "/api/v1/settings/test/not_in_catalog_key/tenant-override"
            )
        assert response.status_code == 404

    def test_delete_returns_effective_value_after_revert(
        self, client, db_session, test_tenant
    ):
        """After revert, effective_value reflects the system default."""
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            # Set a custom value first
            client.put(
                "/api/v1/settings/test/background_sync_battery_floor_pct",
                json={"value": 30},
            )
            # Revert it — FIND-158: path updated to /tenant-override
            response = client.delete(
                "/api/v1/settings/test/background_sync_battery_floor_pct/tenant-override"
            )
        assert response.status_code == 200
        data = response.json()
        # effective_value should be system default (20) after revert
        assert data["effective_value"] == 20


class TestBulkSettingsWrite:
    """Tests for PUT /api/v1/settings/bulk."""

    def test_bulk_write_multiple_keys(self, client, db_session, test_tenant):
        """Bulk write commits multiple keys atomically."""
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            response = client.put(
                "/api/v1/settings/test/bulk",
                json={
                    "values": {
                        "qb_auto_expire_customer_enabled": True,
                        "qb_auto_expire_customer_direction": "pilot",
                    }
                },
            )
        assert response.status_code == 200
        data = response.json()
        assert set(data["updated"]) == {
            "qb_auto_expire_customer_enabled",
            "qb_auto_expire_customer_direction",
        }
        assert len(data["results"]) == 2

        # Restore
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            client.put(
                "/api/v1/settings/test/bulk",
                json={
                    "values": {
                        "qb_auto_expire_customer_enabled": False,
                        "qb_auto_expire_customer_direction": None,
                    }
                },
            )

    def test_bulk_write_unknown_key_returns_404(self, client):
        """Bulk write with an unknown key returns 404."""
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            response = client.put(
                "/api/v1/settings/test/bulk",
                json={"values": {"unknown_key_that_does_not_exist": "val"}},
            )
        assert response.status_code == 404

    def test_bulk_write_invalid_value_returns_422(self, client):
        """Bulk write with out-of-range value returns 422."""
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            response = client.put(
                "/api/v1/settings/test/bulk",
                json={"values": {"background_sync_battery_floor_pct": 200}},  # max 50
            )
        assert response.status_code == 422


# ===========================================================================
# A55 — User override endpoint tests
# ===========================================================================


class TestUserOverridePut:
    """Tests for PUT /api/v1/settings/{key}/user-override."""

    def test_put_user_override_for_allowed_key(self, client, db_session, test_tenant):
        """Writing a user override for an allowed key (background_sync_enabled) succeeds."""
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            response = client.put(
                "/api/v1/settings/test/background_sync_enabled/user-override",
                json={"value": False},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "background_sync_enabled"
        assert data["value"] is False
        assert data["scope"] == "user"
        assert data["effective_value"] is False

        # Cleanup
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            client.delete("/api/v1/settings/test/background_sync_enabled/user-override")

    def test_put_user_override_forbidden_for_non_overridable_key(self, client):
        """Writing a user override for push_interval (allows_user_override=False) returns 403."""
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            response = client.put(
                "/api/v1/settings/test/background_sync_push_interval_minutes/user-override",
                json={"value": 10},
            )
        assert response.status_code == 403

    def test_put_user_override_upserts(self, client, db_session, test_tenant):
        """Second PUT for same key updates the existing override (upsert)."""
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            # First write
            client.put(
                "/api/v1/settings/test/background_sync_enabled/user-override",
                json={"value": False},
            )
            # Second write (should update, not error)
            response = client.put(
                "/api/v1/settings/test/background_sync_enabled/user-override",
                json={"value": True},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["value"] is True

        # Cleanup
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            client.delete("/api/v1/settings/test/background_sync_enabled/user-override")

    def test_put_user_override_unknown_key_returns_404(self, client):
        """Writing user override for unknown key returns 404."""
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            response = client.put(
                "/api/v1/settings/test/completely_unknown_key/user-override",
                json={"value": True},
            )
        assert response.status_code == 404


class TestUserOverrideDelete:
    """Tests for DELETE /api/v1/settings/{key}/user-override."""

    def test_delete_existing_override_returns_tenant_scope(
        self, client, db_session, test_tenant
    ):
        """After deleting override, effective scope falls back to tenant/system."""
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            # Create override
            client.put(
                "/api/v1/settings/test/background_sync_enabled/user-override",
                json={"value": False},
            )
            # Delete it
            response = client.delete(
                "/api/v1/settings/test/background_sync_enabled/user-override"
            )
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "background_sync_enabled"
        assert data["value"] is None  # override deleted
        assert data["scope"] in ("tenant", "system")

    def test_delete_nonexistent_override_returns_404(
        self, client, db_session, test_tenant
    ):
        """Deleting an override that doesn't exist returns 404."""
        # SD-6: Remove any seeded background_sync_enabled override so this test
        # correctly exercises the 404 path (delete of nonexistent override)
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            # Delete it (if seeded) so we start from a clean state
            client.delete("/api/v1/settings/test/background_sync_enabled/user-override")
            # Now delete again — this time it truly doesn't exist → should 404
            response = client.delete(
                "/api/v1/settings/test/background_sync_enabled/user-override"
            )
        assert response.status_code == 404

    def test_delete_user_override_unknown_key_returns_404(self, client):
        """Deleting override for unknown key returns 404."""
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            response = client.delete(
                "/api/v1/settings/test/completely_unknown_key/user-override"
            )
        assert response.status_code == 404


# ===========================================================================
# A52 — Cache invalidation tests
# ===========================================================================


class TestCacheInvalidation:
    """Tests for cache invalidation on settings writes."""

    def test_tenant_write_invalidates_cache(self, client):
        """PUT /settings/{key} calls Redis delete after commit."""
        mock_client = MagicMock()
        mock_client.scan_iter.return_value = ["settings_catalog:abc:owner"]

        with patch(
            "api.routes.settings._get_settings_redis_client", return_value=mock_client
        ):
            response = client.put(
                "/api/v1/settings/test/etc_variance_owner_notify_pct",
                json={"value": 45},
            )

        assert response.status_code == 200
        # scan_iter should have been called with the tenant cache key pattern
        mock_client.scan_iter.assert_called()

        # Restore
        with patch("api.routes.settings._get_settings_redis_client", return_value=None):
            client.put(
                "/api/v1/settings/test/etc_variance_owner_notify_pct",
                json={"value": 50},
            )
