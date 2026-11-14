"""
C-B4: Tests for POST /subscription/resume endpoint + /test twin.
Domain: subscriptions_usage (PRD §3.11)
"""

import pytest

pytestmark = [
    pytest.mark.domain_subscriptions_usage,
    pytest.mark.unit,
]


class TestResumeSubscriptionTestEndpoint:
    """Tests for POST /{tenant_id}/subscription/resume/test (no auth, Stripe bypassed)."""

    def test_test_endpoint_returns_mock_response(self, client, test_tenant):
        """Test endpoint bypasses Stripe and returns mock active response."""
        resp = client.post(
            f"/api/v1/tenants/{test_tenant.id}/subscription/resume/test",
            json={"stripe_payment_method_id": "pm_test_mock"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["psp_subscription_id"] == "test_sub_mock_id"
        assert data["status"] == "active"
        assert data["billing_cycle_anchor"] is None


class TestResumeSubscriptionCrossTenant:
    """Cross-tenant access returns 404 (not 403) per Rule 13."""

    def test_test_endpoint_cross_tenant_returns_404(self, client, test_tenant):
        """Resuming subscription for a different tenant_id returns 404."""
        import uuid

        other_tenant_id = uuid.uuid4()
        resp = client.post(
            f"/api/v1/tenants/{other_tenant_id}/subscription/resume/test",
            json={"stripe_payment_method_id": "pm_test_mock"},
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["detail"]["status"] == 404
        assert "type" in body["detail"]  # RFC 7807
