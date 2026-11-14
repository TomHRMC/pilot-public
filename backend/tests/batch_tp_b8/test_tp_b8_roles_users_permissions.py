"""
TP-B8 — Roles, Users & Permissions — Test Endpoints

Coverage:
  1. GET  /api/v1/roles/test                        → list_roles_test
  2. GET  /api/v1/users/me/permissions/test         → get_my_permissions_test
  3. POST /api/v1/users/{user_id}/role/test         → assign_role_test
  4. GET  /api/v1/users/test                        → list_tenant_users_test
  5. POST /api/v1/permissions/check/test            → check_user_permission_test

Also verifies:
  - 403 when TEST_ENDPOINT_ENABLED=false
  - All endpoints return expected schema shapes
"""

import uuid
from unittest.mock import patch

from fastapi import status

from core.config import settings

# ==================== SECURITY GUARD TESTS ====================


class TestTpB8SecurityGuards:
    def test_list_roles_blocked_when_disabled(self, client):
        """GET /roles/test returns 403 when TEST_ENDPOINT_ENABLED=false."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", False):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get("/api/v1/roles/test")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "test_endpoints_disabled" in response.json()["detail"]["error"]

    def test_permissions_blocked_in_production(self, client):
        """GET /users/me/permissions/test returns 403 in production."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "production"):
                response = client.get("/api/v1/users/me/permissions/test")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_check_permission_blocked_when_disabled(self, client):
        """POST /permissions/check/test returns 403 when disabled."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", False):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    "/api/v1/permissions/check/test",
                    json={"permission": "quotes.view"},
                )
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ==================== LIST ROLES /test ====================


class TestTpB8ListRoles:
    def test_list_roles_returns_200(self, client):
        """GET /roles/test returns list of active roles."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get("/api/v1/roles/test")
        assert response.status_code == status.HTTP_200_OK
        roles = response.json()
        assert isinstance(roles, list)
        # Roles are global (not tenant-scoped), should have at least seeded roles
        if len(roles) > 0:
            role = roles[0]
            assert "code" in role
            assert "name" in role
            assert "permissions" in role
            assert "is_active" in role

    def test_list_roles_only_returns_active(self, client):
        """All returned roles should be active."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get("/api/v1/roles/test")
        assert response.status_code == status.HTTP_200_OK
        for role in response.json():
            assert role["is_active"] is True


# ==================== GET MY PERMISSIONS /test ====================


class TestTpB8GetMyPermissions:
    def test_get_permissions_returns_test_user_context(self, client):
        """GET /users/me/permissions/test returns test user's permission info."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get("/api/v1/users/me/permissions/test")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "user_id" in data
        assert "tenant_id" in data
        assert "role_code" in data
        assert "permissions" in data
        assert isinstance(data["permissions"], list)


# ==================== LIST TENANT USERS /test ====================


class TestTpB8ListTenantUsers:
    def test_list_users_returns_200(self, client):
        """GET /users/test returns list of tenant users (may be empty for test tenant)."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get("/api/v1/users/test")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)

    def test_list_users_schema_valid(self, client, test_tenant, test_user):
        """Users in list have expected fields."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get("/api/v1/users/test")
        assert response.status_code == status.HTTP_200_OK
        for user in response.json():
            assert "user_id" in user
            assert "email" in user
            assert "role_code" in user


# ==================== ASSIGN ROLE /test ====================


class TestTpB8AssignRole:
    def test_assign_role_404_for_unknown_user(self, client):
        """POST /users/{user_id}/role/test returns 404 for unknown user."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"/api/v1/users/{uuid.uuid4()}/role/test",
                    json={"role_code": "technician"},
                )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_assign_role_endpoint_reachable(self, client):
        """POST /users/{user_id}/role/test endpoint is reachable (not 403/405)."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    f"/api/v1/users/{uuid.uuid4()}/role/test",
                    json={"role_code": "technician"},
                )
        assert response.status_code != status.HTTP_403_FORBIDDEN
        assert response.status_code != status.HTTP_405_METHOD_NOT_ALLOWED


# ==================== CHECK PERMISSION /test ====================


class TestTpB8CheckPermission:
    def test_check_permission_returns_result(self, client):
        """POST /permissions/check/test returns permission check result."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    "/api/v1/permissions/check/test",
                    json={"permission": "quotes.view"},
                )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "permission" in data
        assert "has_permission" in data
        assert data["permission"] == "quotes.view"
        # Test context has no permissions — always False
        assert data["has_permission"] is False

    def test_check_permission_endpoint_blocked_in_production(self, client):
        """POST /permissions/check/test returns 403 in production."""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "production"):
                response = client.post(
                    "/api/v1/permissions/check/test",
                    json={"permission": "quotes.view"},
                )
        assert response.status_code == status.HTTP_403_FORBIDDEN
