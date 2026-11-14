"""
MOB-B7 Part A — LOTO Policy Endpoint Unit Tests

Verifies:
  1. Default LOTO policy returns loto_confirmation_required = false (test endpoint)
  2. Authenticated endpoint returns loto_confirmation_required = false by default
  3. Tenant override is respected (test write endpoint → loto-policy/test read)

Test resilience rules:
  - Uses /test endpoints for unauthenticated reads; cleans up overrides after each test.
  - Never asserts on total row counts; scoped to the setting key.
"""

import pytest

pytestmark = [pytest.mark.domain_platform_infrastructure, pytest.mark.unit]


class TestLotoPolicyMobB7:
    def test_loto_policy_returns_false_by_default(
        self, client, test_tenant, mock_cognito_jwt
    ):
        """Default: loto_confirmation_required = false (system default in platform_setting)."""
        resp = client.get("/api/v1/settings/loto-policy/test")
        assert resp.status_code == 200
        data = resp.json()
        assert "loto_confirmation_required" in data
        assert data["loto_confirmation_required"] is False

    def test_loto_policy_authenticated_returns_false_by_default(
        self, client, test_tenant, test_user, mock_cognito_jwt
    ):
        """Authenticated endpoint: loto_confirmation_required = false by default."""
        mock_cognito_jwt(test_user)
        resp = client.get("/api/v1/settings/loto-policy")
        assert resp.status_code == 200
        data = resp.json()
        assert data["loto_confirmation_required"] is False

    def test_loto_policy_respects_tenant_override(
        self, client, test_tenant, mock_cognito_jwt
    ):
        """When tenant overrides loto_confirmation_required=true, endpoint returns true."""
        # Write tenant override via test endpoint
        put_resp = client.put(
            "/api/v1/settings/test/loto_confirmation_required",
            json={"value": True},
        )
        assert put_resp.status_code == 200

        # Verify loto-policy now returns true
        resp = client.get("/api/v1/settings/loto-policy/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["loto_confirmation_required"] is True

        # Clean up — revert to system default
        revert_resp = client.delete(
            "/api/v1/settings/test/loto_confirmation_required/tenant-override"
        )
        assert revert_resp.status_code == 200
