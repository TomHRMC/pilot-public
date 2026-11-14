"""
Tests for: Wildcard permission matching in has_permission()
Domain: platform_infrastructure (PRD §3.8)

Root cause fixed (BETA-B1/Task 1):
  TenantUserRole.permissions was typed as dict[str, Any] but the DB stores a
  JSON array like ["*", "users.manage", ...].  Pydantic v2 coerced the list to
  {} (empty dict), causing isinstance({}, list) == False in auth.py, so all
  permissions resolved to [] → 403 for every authenticated call.
  Fix: changed model type to list[str] so Pydantic deserializes the array
  correctly and has_permission(["*"], ...) returns True as intended.
"""

import pytest

pytestmark = [
    pytest.mark.domain_platform_infrastructure,
    pytest.mark.unit,
]


class TestHasPermissionWildcard:
    def test_wildcard_matches_any_permission(self):
        from core.permissions import has_permission

        assert has_permission(["*"], "communications.view") is True

    def test_wildcard_matches_deeply_namespaced_permission(self):
        from core.permissions import has_permission

        assert has_permission(["*"], "quotes.approve") is True

    def test_wildcard_matches_all_actions(self):
        from core.permissions import has_permission

        permissions = ["*"]
        for perm in [
            "customers.create",
            "customers.view",
            "jobs.delete",
            "settings.manage",
        ]:
            assert has_permission(permissions, perm) is True

    def test_wildcard_alongside_other_permissions(self):
        """Owner role has ['*', 'users.manage', ...] — wildcard still matches."""
        from core.permissions import has_permission

        owner_permissions = ["*", "users.manage", "users.view", "integrations.manage"]
        assert has_permission(owner_permissions, "communications.view") is True
        assert has_permission(owner_permissions, "quotes.create") is True
        assert has_permission(owner_permissions, "field_issue.view") is True

    def test_specific_permission_matches_itself(self):
        from core.permissions import has_permission

        assert has_permission(["communications.view"], "communications.view") is True

    def test_specific_permission_does_not_match_other(self):
        from core.permissions import has_permission

        assert has_permission(["communications.view"], "quotes.approve") is False

    def test_resource_wildcard_matches_all_actions(self):
        from core.permissions import has_permission

        assert has_permission(["customers.*"], "customers.create") is True
        assert has_permission(["customers.*"], "customers.view") is True
        assert has_permission(["customers.*"], "customers.delete") is True
        assert has_permission(["customers.*"], "quotes.view") is False

    def test_action_wildcard_matches_resource(self):
        from core.permissions import has_permission

        assert has_permission(["*.view"], "quotes.view") is True
        assert has_permission(["*.view"], "customers.view") is True
        assert has_permission(["*.view"], "customers.create") is False

    def test_empty_permissions_matches_nothing(self):
        from core.permissions import has_permission

        assert has_permission([], "communications.view") is False

    def test_dashboard_widget_not_403_for_test_user(
        self, client, test_tenant, test_user
    ):
        """
        End-to-end: GET /api/v1/dashboard/widgets/recent-customer-messages/test
        must not return 403 (auth passed = 200 or 404 for empty data).
        """
        response = client.get("/api/v1/dashboard/widgets/recent-customer-messages/test")
        assert response.status_code != 403, (
            f"Expected 200 or 404 (auth passed), got 403. "
            f"Wildcard permission check is still failing. Body: {response.json()}"
        )
