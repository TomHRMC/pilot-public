"""
Batch B2 — A7 Test Coverage
============================

A7: Field Mode Backend Support

Test Coverage:
- PATCH /api/v1/users/me/preferences/test sets field_mode_enabled=true
- PATCH /api/v1/users/me/preferences/test sets field_mode_enabled=false
- GET /api/v1/users/me/preferences/test returns current preferences
- field_mode_enabled is stored in user_preference.preferences JSONB (not a separate column)
- Updating preferences merges with existing JSONB (does not overwrite other keys)
- No new migration required (user_preference.preferences already exists)
- UserPreference ORM model has preferences JSONB field
"""

import pytest
from sqlmodel import select

# ─────────────────────────────────────────────────────────────────────────────
# A7 — ORM model check
# ─────────────────────────────────────────────────────────────────────────────


class TestA7ORMModel:
    """Verify UserPreference.preferences JSONB exists for field_mode storage."""

    def test_user_preference_has_preferences_field(self):
        from app.models.core import UserPreference

        assert hasattr(UserPreference, "preferences")

    def test_user_preference_can_store_field_mode(
        self, db_session, test_tenant, test_user
    ):
        """field_mode_enabled can be stored in preferences JSONB."""
        from sqlmodel import select

        from app.models.core import UserPreference

        # SD-6: Delete any seeded user_preference for this user+tenant before testing
        existing = db_session.exec(
            select(UserPreference)
            .where(UserPreference.user_id == test_user.id)
            .where(UserPreference.tenant_id == test_tenant.id)
        ).first()
        if existing:
            db_session.delete(existing)
            db_session.flush()

        pref = UserPreference(
            user_id=test_user.id,
            tenant_id=test_tenant.id,
            preferences={"field_mode_enabled": True},
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(pref)
        db_session.flush()
        db_session.refresh(pref)

        assert pref.preferences["field_mode_enabled"] is True


# ─────────────────────────────────────────────────────────────────────────────
# A7 — HTTP endpoint tests
# ─────────────────────────────────────────────────────────────────────────────


class TestA7FieldModeEndpoint:
    """HTTP tests for PATCH/GET /api/v1/users/me/preferences/test"""

    def test_patch_preferences_enables_field_mode(self, client, test_tenant, test_user):
        """PATCH /api/v1/users/me/preferences/test with field_mode_enabled=true returns 200."""
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("TEST_ENDPOINT_ENABLED", "true")
            mp.setenv("ENVIRONMENT", "dev")
            resp = client.patch(
                "/api/v1/users/me/preferences/test", json={"field_mode_enabled": True}
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["preferences"]["field_mode_enabled"] is True

    def test_patch_preferences_disables_field_mode(
        self, client, test_tenant, test_user
    ):
        """PATCH /api/v1/users/me/preferences/test with field_mode_enabled=false returns 200."""
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("TEST_ENDPOINT_ENABLED", "true")
            mp.setenv("ENVIRONMENT", "dev")
            # First enable
            client.patch(
                "/api/v1/users/me/preferences/test", json={"field_mode_enabled": True}
            )
            # Then disable
            resp = client.patch(
                "/api/v1/users/me/preferences/test", json={"field_mode_enabled": False}
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["preferences"]["field_mode_enabled"] is False

    def test_patch_preferences_response_has_correct_shape(
        self, client, test_tenant, test_user
    ):
        """Response has user_id, tenant_id, preferences, updated_at."""
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("TEST_ENDPOINT_ENABLED", "true")
            mp.setenv("ENVIRONMENT", "dev")
            resp = client.patch(
                "/api/v1/users/me/preferences/test", json={"field_mode_enabled": True}
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "user_id" in data
        assert "tenant_id" in data
        assert "preferences" in data
        assert "updated_at" in data

    def test_get_preferences_returns_200(self, client, test_tenant, test_user):
        """GET /api/v1/users/me/preferences/test returns 200."""
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("TEST_ENDPOINT_ENABLED", "true")
            mp.setenv("ENVIRONMENT", "dev")
            resp = client.get("/api/v1/users/me/preferences/test")

        assert resp.status_code == 200
        data = resp.json()
        assert "preferences" in data

    def test_preferences_persist_across_requests(self, client, test_tenant, test_user):
        """Preferences set via PATCH are visible in subsequent GET."""
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("TEST_ENDPOINT_ENABLED", "true")
            mp.setenv("ENVIRONMENT", "dev")
            # Set field_mode_enabled=True
            client.patch(
                "/api/v1/users/me/preferences/test", json={"field_mode_enabled": True}
            )
            # Read it back
            resp = client.get("/api/v1/users/me/preferences/test")

        assert resp.status_code == 200
        data = resp.json()
        assert data["preferences"].get("field_mode_enabled") is True

    def test_field_mode_stored_in_jsonb_not_separate_column(self):
        """field_mode_enabled is in preferences JSONB, not a separate DB column."""
        from app.models.core import UserPreference

        # Verify there is no field_mode_enabled column on the model
        assert not hasattr(UserPreference, "field_mode_enabled"), (
            "field_mode_enabled must be stored in JSONB preferences, not a separate column"
        )


# ─────────────────────────────────────────────────────────────────────────────
# A7 — Service layer tests
# ─────────────────────────────────────────────────────────────────────────────


class TestA7PreferenceServiceLayer:
    """Test the _update_preferences_impl shared logic directly."""

    def test_update_creates_new_preference_record(
        self, db_session, test_tenant, test_user
    ):
        """_update_preferences_impl creates a UserPreference row if none exists."""
        from api.routes.user_preferences import (
            UserPreferencePatch,
            _update_preferences_impl,
        )
        from app.models.core import UserPreference

        # Ensure no preference exists
        existing = db_session.exec(
            select(UserPreference)
            .where(UserPreference.user_id == test_user.id)
            .where(UserPreference.tenant_id == test_tenant.id)
        ).first()
        if existing:
            db_session.delete(existing)
            db_session.flush()

        from unittest.mock import MagicMock

        mock_user = MagicMock()
        mock_user.id = test_user.id
        mock_user.tenant_id = test_tenant.id

        patch = UserPreferencePatch(field_mode_enabled=True)
        result = _update_preferences_impl(patch, mock_user, db_session)

        assert result.preferences["field_mode_enabled"] is True

    def test_update_merges_with_existing_preferences(
        self, db_session, test_tenant, test_user
    ):
        """_update_preferences_impl merges new fields without overwriting existing ones."""
        from api.routes.user_preferences import (
            UserPreferencePatch,
            _update_preferences_impl,
        )
        from app.models.core import UserPreference

        # Create a preference record with an existing key
        existing = db_session.exec(
            select(UserPreference)
            .where(UserPreference.user_id == test_user.id)
            .where(UserPreference.tenant_id == test_tenant.id)
        ).first()

        if existing:
            existing.preferences = {"some_other_key": "preserved_value"}
            db_session.add(existing)
            db_session.flush()
        else:
            pref = UserPreference(
                user_id=test_user.id,
                tenant_id=test_tenant.id,
                preferences={"some_other_key": "preserved_value"},
                created_by=test_user.id,
                updated_by=test_user.id,
            )
            db_session.add(pref)
            db_session.flush()

        from unittest.mock import MagicMock

        mock_user = MagicMock()
        mock_user.id = test_user.id
        mock_user.tenant_id = test_tenant.id

        patch = UserPreferencePatch(field_mode_enabled=True)
        result = _update_preferences_impl(patch, mock_user, db_session)

        # Both keys should be present
        assert result.preferences.get("field_mode_enabled") is True
        assert result.preferences.get("some_other_key") == "preserved_value"
