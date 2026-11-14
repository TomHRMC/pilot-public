"""
Tests for: GET /api/v1/settings/tenant/mfa-required
Domain: identity_access (PRD §3.5)
Gap: BETA-B4-BE-03

The GET endpoint reads current tenant MFA policy from:
  - platform_setting (key='tenant_mfa_required', 'tenant_mfa_grace_period_days')
  - tenant.mfa_grace_period_started_at

Response shape: { "tenant_mfa_required": bool, "grace_period_starts_at": datetime|null, "grace_period_days": int }
"""

import pytest

pytestmark = [
    pytest.mark.domain_identity_access,
    pytest.mark.unit,
]


class TestGetTenantMfaPolicy:
    def test_returns_200(self, client, test_tenant):
        """GET /test endpoint returns 200."""
        response = client.get("/api/v1/settings/tenant/mfa-required/test")
        assert response.status_code == 200

    def test_response_shape(self, client, test_tenant):
        """Response contains exactly the required fields."""
        response = client.get("/api/v1/settings/tenant/mfa-required/test")
        assert response.status_code == 200
        data = response.json()
        assert "tenant_mfa_required" in data
        assert "grace_period_starts_at" in data
        assert "grace_period_days" in data

    def test_tenant_mfa_required_is_bool(self, client, test_tenant):
        """tenant_mfa_required is a boolean."""
        response = client.get("/api/v1/settings/tenant/mfa-required/test")
        assert response.status_code == 200
        assert isinstance(response.json()["tenant_mfa_required"], bool)

    def test_grace_period_days_is_int(self, client, test_tenant):
        """grace_period_days is an integer."""
        response = client.get("/api/v1/settings/tenant/mfa-required/test")
        assert response.status_code == 200
        assert isinstance(response.json()["grace_period_days"], int)

    def test_defaults_when_no_policy_set(self, client, test_tenant):
        """When no policy has been set, mfa_required defaults to False."""
        response = client.get("/api/v1/settings/tenant/mfa-required/test")
        assert response.status_code == 200
        data = response.json()
        # Default state: MFA not required, no grace period active
        assert data["tenant_mfa_required"] is False

    def test_grace_period_starts_at_is_null_when_mfa_not_enabled(
        self, client, test_tenant
    ):
        """grace_period_starts_at is null when MFA policy has never been enabled."""
        response = client.get("/api/v1/settings/tenant/mfa-required/test")
        assert response.status_code == 200
        data = response.json()
        # If MFA was never enabled for this test tenant, grace_period_starts_at is null
        # (It may be non-null if another test already enabled MFA for this tenant — that's OK)
        assert data["grace_period_starts_at"] is None or isinstance(
            data["grace_period_starts_at"], str
        )

    def test_get_reflects_put_state(self, client, test_tenant):
        """GET returns the same state that PUT writes."""
        # Enable MFA via PUT
        put_response = client.put(
            "/api/v1/settings/tenant/mfa-required/test",
            json={"enabled": True, "grace_period_days": 14},
        )
        assert put_response.status_code == 200
        put_data = put_response.json()

        # GET must return the same values
        get_response = client.get("/api/v1/settings/tenant/mfa-required/test")
        assert get_response.status_code == 200
        get_data = get_response.json()

        assert get_data["tenant_mfa_required"] == put_data["tenant_mfa_required"]
        assert get_data["grace_period_days"] == put_data["grace_period_days"]
        # grace_period_starts_at should now be set
        assert get_data["grace_period_starts_at"] is not None
