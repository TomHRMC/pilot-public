"""
Tests for: UI-FIX-2B — TenantUserWithRoleResponse name fields (first_name, last_name, display_color)
Domain: scheduling_dispatch (PRD §3.14)

Verifies that GET /api/v1/users returns user records that include first_name,
last_name, and display_color fields — required for the tech picker on the
Dispatch Board and Job Detail page to show human-readable names rather than
just email addresses.
"""

import pytest

pytestmark = [
    pytest.mark.domain_scheduling_dispatch,
    pytest.mark.unit,
]


class TestTechUserNameFields:
    """Verify that the tenant user list endpoint returns name fields."""

    def test_list_users_includes_first_name_key(self, client, test_tenant):
        """GET /api/v1/users/test response items contain the first_name key."""
        resp = client.get("/api/v1/users/test")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Expected at least one seeded user in test_tenant"
        # All returned users must have the first_name key (value may be None)
        for user in data:
            assert "first_name" in user, (
                f"Missing 'first_name' key in user: {user.get('user_id')}"
            )

    def test_list_users_includes_last_name_key(self, client, test_tenant):
        """GET /api/v1/users/test response items contain the last_name key."""
        resp = client.get("/api/v1/users/test")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Expected at least one seeded user in test_tenant"
        for user in data:
            assert "last_name" in user, (
                f"Missing 'last_name' key in user: {user.get('user_id')}"
            )

    def test_list_users_includes_display_color_key(self, client, test_tenant):
        """GET /api/v1/users/test response items contain the display_color key."""
        resp = client.get("/api/v1/users/test")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Expected at least one seeded user in test_tenant"
        for user in data:
            assert "display_color" in user, (
                f"Missing 'display_color' key in user: {user.get('user_id')}"
            )

    def test_list_users_name_fields_nullable(self, client, db_session, test_tenant):
        """A user with no name set returns first_name: null (not missing key) in response."""
        import uuid

        from sqlalchemy import text

        # Insert a minimal user with no first_name/last_name/display_color
        new_user_id = uuid.uuid4()
        new_email = f"noname_{new_user_id.hex[:8]}@test.local"

        db_session.execute(
            text(
                """
                INSERT INTO public."user"
                    (id, email, is_active, created_at, updated_at)
                VALUES
                    (:id, :email, true, now(), now())
                """
            ),
            {"id": str(new_user_id), "email": new_email},
        )

        # Link to test_tenant with technician role (role must exist)
        # status_id is NOT NULL — use the 'active' status from tenant_user_status
        db_session.execute(
            text(
                """
                INSERT INTO public.tenant_user
                    (tenant_id, user_id, role_code, status_id, is_active, created_at, updated_at)
                VALUES
                    (:tenant_id, :user_id, 'technician',
                     (SELECT id FROM public.tenant_user_status WHERE code = 'active' LIMIT 1),
                     true, now(), now())
                """
            ),
            {"tenant_id": str(test_tenant.id), "user_id": str(new_user_id)},
        )
        db_session.commit()

        resp = client.get("/api/v1/users/test")
        assert resp.status_code == 200
        data = resp.json()

        # Find our newly created user in the response
        our_user = next((u for u in data if u["user_id"] == str(new_user_id)), None)
        assert our_user is not None, f"User {new_user_id} not found in response"

        # Key must be present with null value (not absent)
        assert "first_name" in our_user, "first_name key missing from response"
        assert "last_name" in our_user, "last_name key missing from response"
        assert "display_color" in our_user, "display_color key missing from response"
        assert our_user["first_name"] is None, (
            f"Expected None but got: {our_user['first_name']}"
        )
        assert our_user["last_name"] is None, (
            f"Expected None but got: {our_user['last_name']}"
        )
        assert our_user["display_color"] is None, (
            f"Expected None but got: {our_user['display_color']}"
        )
