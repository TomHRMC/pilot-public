"""
STRIPE-B1: Test billing interval price ID routing logic.
"""

import pytest
from sqlmodel import select

pytestmark = [
    pytest.mark.domain_subscriptions_usage,
    pytest.mark.unit,
]


class TestSelectStripePriceId:
    """Unit tests for _select_stripe_price_id() helper."""

    def test_monthly_returns_stripe_price_id_monthly(self, db_session):
        """billing_interval='monthly' returns stripe_price_id_monthly."""
        from api.routes.tenant_subscription import _select_stripe_price_id
        from app.models.subscription import SubscriptionTier

        starter = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "starter")
        ).first()
        assert starter is not None

        result = _select_stripe_price_id(starter, "monthly")
        assert result == starter.stripe_price_id_monthly

    def test_annual_returns_stripe_price_id_annual(self, db_session):
        """billing_interval='annual' returns stripe_price_id_annual (may be None)."""
        from api.routes.tenant_subscription import _select_stripe_price_id
        from app.models.subscription import SubscriptionTier

        starter = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "starter")
        ).first()
        assert starter is not None

        result = _select_stripe_price_id(starter, "annual")
        # annual price is NULL until Tom creates it — test just verifies the routing
        assert result == starter.stripe_price_id_annual

    def test_charter_monthly_returns_price_id(self, db_session):
        """Charter tier has stripe_price_id_monthly populated (C-B3 bootstrap).

        Previously charter had NULL; now the bootstrap script populates it.
        Test verifies the routing returns the actual price ID.
        """
        from api.routes.tenant_subscription import _select_stripe_price_id
        from app.models.subscription import SubscriptionTier

        charter = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "charter")
        ).first()
        assert charter is not None

        result = _select_stripe_price_id(charter, "monthly")
        assert result == charter.stripe_price_id_monthly
        assert result is not None  # C-B3 bootstrap populated this


class TestConvertFromTrialBillingInterval:
    """Test that convert-from-trial route accepts billing_interval field."""

    def test_convert_from_trial_accepts_billing_interval_monthly(
        self, client, test_tenant
    ):
        """POST convert-from-trial with billing_interval='monthly' returns 202 or 400/404 (not 422)."""
        import uuid

        # Use test endpoint — Stripe is bypassed but we need a real paid tier
        # This verifies schema accepts the new field without 422
        resp = client.post(
            f"/api/v1/tenants/{test_tenant.id}/subscription/convert-from-trial/test",
            json={
                "target_tier_id": str(uuid.uuid4()),  # non-existent tier
                "payment_method_id": "pm_test_mock",
                "billing_email": "test@example.com",
                "billing_interval": "monthly",
            },
        )
        # 400 or 404 (tier not found or not configured) is fine — we're testing schema accepts the field
        assert resp.status_code in (400, 404), (
            f"Expected 400 or 404, got {resp.status_code}. "
            "If 422: billing_interval field was rejected — check schema definition."
        )

    def test_convert_from_trial_default_billing_interval_is_monthly(
        self, client, test_tenant
    ):
        """POST convert-from-trial without billing_interval defaults to monthly (no 422)."""
        import uuid

        resp = client.post(
            f"/api/v1/tenants/{test_tenant.id}/subscription/convert-from-trial/test",
            json={
                "target_tier_id": str(uuid.uuid4()),
                "payment_method_id": "pm_test_mock",
                "billing_email": "test@example.com",
                # billing_interval omitted — should default to "monthly"
            },
        )
        assert resp.status_code in (400, 404)

    def test_convert_from_trial_rejects_invalid_billing_interval(
        self, client, test_tenant
    ):
        """POST convert-from-trial with invalid billing_interval returns 422."""
        import uuid

        resp = client.post(
            f"/api/v1/tenants/{test_tenant.id}/subscription/convert-from-trial/test",
            json={
                "target_tier_id": str(uuid.uuid4()),
                "payment_method_id": "pm_test_mock",
                "billing_email": "test@example.com",
                "billing_interval": "quarterly",  # invalid value
            },
        )
        assert resp.status_code == 422


class TestChangeTierBillingInterval:
    """Test that change-tier route accepts billing_interval field."""

    def test_change_tier_accepts_billing_interval_annual(self, client, test_tenant):
        """POST change-tier with billing_interval='annual' returns 400/404 (not 422)."""
        import uuid

        resp = client.post(
            f"/api/v1/tenants/{test_tenant.id}/subscription/change-tier/test",
            json={
                "target_tier_id": str(uuid.uuid4()),
                "billing_interval": "annual",
            },
        )
        assert resp.status_code in (400, 404)

    def test_change_tier_default_billing_interval_is_monthly(self, client, test_tenant):
        """POST change-tier without billing_interval defaults to monthly (no 422)."""
        import uuid

        resp = client.post(
            f"/api/v1/tenants/{test_tenant.id}/subscription/change-tier/test",
            json={
                "target_tier_id": str(uuid.uuid4()),
                # billing_interval omitted — defaults to monthly
            },
        )
        assert resp.status_code in (400, 404)
