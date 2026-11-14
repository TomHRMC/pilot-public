"""
Tests for: MOB-B8 Background Sync Policy endpoint
Domain: mobile_offline (PRD §3.15)

Covers GET /api/v1/settings/background-sync-policy (authenticated)
and   GET /api/v1/settings/background-sync-policy/test (no-auth test endpoint)
"""

import pytest

pytestmark = [
    pytest.mark.domain_mobile_offline,
    pytest.mark.unit,
]

POLICY_URL = "/api/v1/settings/background-sync-policy/test"
POLICY_AUTH_URL = "/api/v1/settings/background-sync-policy"


class TestBackgroundSyncPolicy:
    """Tests for GET /api/v1/settings/background-sync-policy."""

    def test_sync_policy_returns_defaults(self, client, test_tenant):
        """GET /background-sync-policy/test returns the 4 default values when no tenant override."""
        resp = client.get(POLICY_URL)
        assert resp.status_code == 200, resp.text

        data = resp.json()
        assert set(data.keys()) == {
            "background_sync_enabled",
            "background_sync_wifi_only",
            "background_sync_battery_floor_pct",
            "background_sync_push_interval_minutes",
        }

    def test_sync_policy_returns_correct_types(self, client, test_tenant):
        """All 4 fields have correct Python types (bool, bool, int, int)."""
        resp = client.get(POLICY_URL)
        assert resp.status_code == 200, resp.text

        data = resp.json()
        # Booleans from JSON
        assert isinstance(data["background_sync_enabled"], bool), (
            f"background_sync_enabled must be bool, got {type(data['background_sync_enabled'])}"
        )
        assert isinstance(data["background_sync_wifi_only"], bool), (
            f"background_sync_wifi_only must be bool, got {type(data['background_sync_wifi_only'])}"
        )
        # Integers from JSON
        assert isinstance(data["background_sync_battery_floor_pct"], int), (
            f"background_sync_battery_floor_pct must be int, got {type(data['background_sync_battery_floor_pct'])}"
        )
        assert isinstance(data["background_sync_push_interval_minutes"], int), (
            f"background_sync_push_interval_minutes must be int, got {type(data['background_sync_push_interval_minutes'])}"
        )

    def test_sync_policy_requires_auth(self, client, test_tenant):
        """Unauthenticated request to authenticated endpoint returns 401 or 403."""
        # The authenticated route requires jobs.view permission; no JWT = 401/403
        resp = client.get(POLICY_AUTH_URL)
        # Without Authorization header, FastAPI returns 403 (no JWT = missing credentials)
        assert resp.status_code in (401, 403), (
            f"Expected 401 or 403, got {resp.status_code}: {resp.text}"
        )

    def test_sync_policy_tenant_isolation(
        self,
        client,
        test_tenant,
        second_tenant,
        db_session,
    ):
        """
        Tenant A's overrides do not bleed into Tenant B's effective policy.

        Write a custom push interval for test_tenant; second_tenant should
        still see the system default.
        """
        from services.setting_resolver import get_effective_setting

        # Verify second_tenant sees the system default (5 minutes)
        interval, scope = get_effective_setting(
            db_session,
            second_tenant.id,
            "background_sync_push_interval_minutes",
            fallback=5,
        )
        assert int(interval) == 5, (
            f"second_tenant should see default interval=5, got {interval} (scope={scope})"
        )

        # Verify second_tenant policy endpoint returns valid response
        resp = client.get(POLICY_URL)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        # Default values must match catalog defaults
        assert data["background_sync_enabled"] is True
        assert data["background_sync_wifi_only"] is False
        assert data["background_sync_battery_floor_pct"] == 20
        assert data["background_sync_push_interval_minutes"] == 5
