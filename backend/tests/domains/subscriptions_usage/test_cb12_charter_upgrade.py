"""
C-B12: Tests for upgrade_charter_to_teams() — Charter → Teams upgrade flow.
Domain: subscriptions_usage (PRD §3.11)

Covers the service function (upgrade_charter_to_teams) and the API endpoints
(POST /upgrade-from-charter + /test twin).
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import select

pytestmark = [
    pytest.mark.domain_subscriptions_usage,
    pytest.mark.unit,
]


# ==================== HELPERS ====================


def _create_charter_subscription_row(
    db_session, tenant_id, psp_sub_id, psp_customer_id
):
    """Insert an active subscription row scoped to this test (rolled back after test)."""
    from app.models.billing import Subscription, SubscriptionStatus

    active_status = db_session.exec(
        select(SubscriptionStatus).where(SubscriptionStatus.code == "active")
    ).first()
    assert active_status is not None, "active subscription_status not seeded"

    sub = Subscription(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        product_plan_code="charter_plan",
        status_id=active_status.id,
        quantity_seats=1,
        psp_provider="stripe",
        psp_subscription_id=psp_sub_id,
        psp_customer_id=psp_customer_id,
        billing_interval="monthly",
        is_active=True,
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)
    return sub


def _setup_charter_tenant(db_session, tenant, *, stripe_customer_id="cus_test_upgrade"):
    """Configure a tenant as a Charter member with stripe_customer_id."""
    from app.models.core import Tenant
    from app.models.subscription import SubscriptionTier

    charter_tier = db_session.exec(
        select(SubscriptionTier).where(SubscriptionTier.tier_name == "charter")
    ).first()
    assert charter_tier is not None, "charter tier not seeded"

    tenant_row = db_session.exec(select(Tenant).where(Tenant.id == tenant.id)).first()
    tenant_row.charter_eligible = True
    tenant_row.current_subscription_tier_id = charter_tier.tier_id
    tenant_row.stripe_customer_id = stripe_customer_id
    tenant_row.free_period_ends_at = datetime(2026, 12, 31, tzinfo=UTC)
    db_session.add(tenant_row)
    db_session.commit()
    return tenant_row


def _make_mock_stripe_sub(
    *,
    charter_price_id,
    voice_price_id,
    sms_price_id,
    status="active",
    include_metered=True,
):
    """Build a fake Stripe subscription object.

    With include_metered=True (default): 3 items (charter + 2 metered).
    With include_metered=False: 1 item (charter only — simulates Charter
    subscription created without metered items due to Stripe trial-pause
    constraint).
    """
    mock_sub = MagicMock()
    mock_sub.status = status
    mock_sub.id = "sub_test_upgrade_456"

    charter_item = {"id": "si_charter_123", "price": {"id": charter_price_id}}
    items_data = [charter_item]
    if include_metered:
        voice_item = {"id": "si_voice_456", "price": {"id": voice_price_id}}
        sms_item = {"id": "si_sms_789", "price": {"id": sms_price_id}}
        items_data = [charter_item, voice_item, sms_item]

    mock_sub.__getitem__ = MagicMock(
        side_effect=lambda key: {
            "items": {"data": items_data},
        }[key]
    )
    return mock_sub


def _make_mock_customer(*, has_payment_method=True):
    """Build a fake Stripe customer object.

    Uses attribute access (getattr) to match the production code pattern
    for StripeObject — Stripe objects don't support .get() dict access.
    """
    mock_customer = MagicMock()
    pm = "pm_test_123" if has_payment_method else None
    mock_customer.invoice_settings.default_payment_method = pm
    return mock_customer


# ==================== SERVICE FUNCTION TESTS ====================


class TestUpgradeCharterToTeams:
    """Tests for upgrade_charter_to_teams() with mocked Stripe."""

    def test_upgrade_charter_to_teams_monthly(self, db_session, second_tenant):
        """Valid Charter tenant, monthly interval → Charter item deleted, Teams item added,
        charter_eligible=False, tier updated, free_period_ends_at=None."""
        from app.models.core import Tenant
        from app.models.subscription import SubscriptionTier
        from core.stripe_config import get_stripe_ids
        from services.stripe_subscriptions import upgrade_charter_to_teams

        ids = get_stripe_ids()
        charter_price_id = ids["prices"]["price_charter_monthly"]
        teams_monthly_id = ids["prices"]["price_teams_monthly"]
        voice_price_id = ids["prices"]["price_voice_overage"]
        sms_price_id = ids["prices"]["price_sms_overage"]

        _setup_charter_tenant(db_session, second_tenant)
        _create_charter_subscription_row(
            db_session, second_tenant.id, "sub_test_upgrade_monthly", "cus_test_upgrade"
        )

        with (
            patch("services.stripe_subscriptions._get_stripe_client") as mock_client,
            patch("core.stripe_config.get_stripe_ids", return_value=ids),
        ):
            mock_stripe = MagicMock()
            mock_stripe.Customer.retrieve.return_value = _make_mock_customer(
                has_payment_method=True
            )
            mock_stripe.Subscription.retrieve.return_value = _make_mock_stripe_sub(
                charter_price_id=charter_price_id,
                voice_price_id=voice_price_id,
                sms_price_id=sms_price_id,
                status="active",
            )
            mock_updated = MagicMock()
            mock_updated.id = "sub_test_upgrade_monthly"
            mock_stripe.Subscription.modify.return_value = mock_updated
            mock_client.return_value = mock_stripe

            result = upgrade_charter_to_teams(
                db=db_session,
                tenant_id=second_tenant.id,
                billing_interval="monthly",
            )

        assert result["new_tier_name"] == "teams"
        assert result["billing_interval"] == "monthly"
        assert result["charter_eligible_forfeited"] is True

        # Verify tenant updated
        tenant = db_session.exec(
            select(Tenant).where(Tenant.id == second_tenant.id)
        ).first()
        assert tenant.charter_eligible is False
        assert tenant.free_period_ends_at is None

        teams_tier = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "teams")
        ).first()
        assert tenant.current_subscription_tier_id == teams_tier.tier_id

        # Verify Stripe modify called with delete + add
        modify_call = mock_stripe.Subscription.modify.call_args
        items = modify_call.kwargs["items"]
        assert items[0] == {"id": "si_charter_123", "deleted": True}
        assert items[1] == {"price": teams_monthly_id, "quantity": 1}
        assert modify_call.kwargs["proration_behavior"] == "create_prorations"

    def test_upgrade_charter_to_teams_annual(self, db_session, second_tenant):
        """Valid Charter tenant, annual interval → uses price_teams_annual."""
        from core.stripe_config import get_stripe_ids
        from services.stripe_subscriptions import upgrade_charter_to_teams

        ids = get_stripe_ids()
        teams_annual_id = ids["prices"]["price_teams_annual"]

        _setup_charter_tenant(db_session, second_tenant)
        _create_charter_subscription_row(
            db_session, second_tenant.id, "sub_test_upgrade_annual", "cus_test_upgrade"
        )

        with (
            patch("services.stripe_subscriptions._get_stripe_client") as mock_client,
            patch("core.stripe_config.get_stripe_ids", return_value=ids),
        ):
            mock_stripe = MagicMock()
            mock_stripe.Customer.retrieve.return_value = _make_mock_customer(
                has_payment_method=True
            )
            mock_stripe.Subscription.retrieve.return_value = _make_mock_stripe_sub(
                charter_price_id=ids["prices"]["price_charter_monthly"],
                voice_price_id=ids["prices"]["price_voice_overage"],
                sms_price_id=ids["prices"]["price_sms_overage"],
            )
            mock_updated = MagicMock()
            mock_updated.id = "sub_test_upgrade_annual"
            mock_stripe.Subscription.modify.return_value = mock_updated
            mock_client.return_value = mock_stripe

            result = upgrade_charter_to_teams(
                db=db_session,
                tenant_id=second_tenant.id,
                billing_interval="annual",
            )

        assert result["billing_interval"] == "annual"

        modify_call = mock_stripe.Subscription.modify.call_args
        items = modify_call.kwargs["items"]
        assert items[1] == {"price": teams_annual_id, "quantity": 1}

    def test_upgrade_ends_trial_immediately(self, db_session, second_tenant):
        """Charter tenant in trialing status → trial_end='now' passed to modify()."""
        from core.stripe_config import get_stripe_ids
        from services.stripe_subscriptions import upgrade_charter_to_teams

        ids = get_stripe_ids()

        _setup_charter_tenant(db_session, second_tenant)
        _create_charter_subscription_row(
            db_session, second_tenant.id, "sub_test_trial_end", "cus_test_upgrade"
        )

        with (
            patch("services.stripe_subscriptions._get_stripe_client") as mock_client,
            patch("core.stripe_config.get_stripe_ids", return_value=ids),
        ):
            mock_stripe = MagicMock()
            mock_stripe.Customer.retrieve.return_value = _make_mock_customer(
                has_payment_method=True
            )
            mock_stripe.Subscription.retrieve.return_value = _make_mock_stripe_sub(
                charter_price_id=ids["prices"]["price_charter_monthly"],
                voice_price_id=ids["prices"]["price_voice_overage"],
                sms_price_id=ids["prices"]["price_sms_overage"],
                status="trialing",
            )
            mock_updated = MagicMock()
            mock_updated.id = "sub_test_trial_end"
            mock_stripe.Subscription.modify.return_value = mock_updated
            mock_client.return_value = mock_stripe

            upgrade_charter_to_teams(
                db=db_session,
                tenant_id=second_tenant.id,
                billing_interval="monthly",
            )

        modify_call = mock_stripe.Subscription.modify.call_args
        assert modify_call.kwargs.get("trial_end") == "now"

    def test_upgrade_preserves_metered_items(self, db_session, second_tenant):
        """When metered items already exist, upgrade does NOT re-add them.

        The subscription has 3 items (charter + voice + sms). After upgrade,
        the modify call has only 2 items: deleted charter + new teams.
        The metered items are preserved automatically by Stripe.
        """
        from core.stripe_config import get_stripe_ids
        from services.stripe_subscriptions import upgrade_charter_to_teams

        ids = get_stripe_ids()

        _setup_charter_tenant(db_session, second_tenant)
        _create_charter_subscription_row(
            db_session, second_tenant.id, "sub_test_preserve", "cus_test_upgrade"
        )

        with (
            patch("services.stripe_subscriptions._get_stripe_client") as mock_client,
            patch("core.stripe_config.get_stripe_ids", return_value=ids),
        ):
            mock_stripe = MagicMock()
            mock_stripe.Customer.retrieve.return_value = _make_mock_customer(
                has_payment_method=True
            )
            mock_stripe.Subscription.retrieve.return_value = _make_mock_stripe_sub(
                charter_price_id=ids["prices"]["price_charter_monthly"],
                voice_price_id=ids["prices"]["price_voice_overage"],
                sms_price_id=ids["prices"]["price_sms_overage"],
                include_metered=True,
            )
            mock_updated = MagicMock()
            mock_updated.id = "sub_test_preserve"
            mock_stripe.Subscription.modify.return_value = mock_updated
            mock_client.return_value = mock_stripe

            upgrade_charter_to_teams(
                db=db_session,
                tenant_id=second_tenant.id,
                billing_interval="monthly",
            )

        modify_call = mock_stripe.Subscription.modify.call_args
        items = modify_call.kwargs["items"]
        # Only 2 items: the deleted charter item + the new teams item.
        # The metered items are NOT included → preserved by Stripe.
        assert len(items) == 2
        voice_price_id = ids["prices"]["price_voice_overage"]
        sms_price_id = ids["prices"]["price_sms_overage"]
        for item in items:
            price = item.get("price")
            if price:
                assert price != voice_price_id
                assert price != sms_price_id

    def test_upgrade_adds_metered_items_if_missing(self, db_session, second_tenant):
        """When metered items are NOT on the subscription, upgrade adds them.

        Charter subscriptions created without metered items (Stripe
        trial-pause constraint) get voice_overage + sms_overage added
        during the upgrade modify call.
        """
        from core.stripe_config import get_stripe_ids
        from services.stripe_subscriptions import upgrade_charter_to_teams

        ids = get_stripe_ids()
        voice_price_id = ids["prices"]["price_voice_overage"]
        sms_price_id = ids["prices"]["price_sms_overage"]
        teams_monthly_id = ids["prices"]["price_teams_monthly"]

        _setup_charter_tenant(db_session, second_tenant)
        _create_charter_subscription_row(
            db_session, second_tenant.id, "sub_test_add_metered", "cus_test_upgrade"
        )

        with (
            patch("services.stripe_subscriptions._get_stripe_client") as mock_client,
            patch("core.stripe_config.get_stripe_ids", return_value=ids),
        ):
            mock_stripe = MagicMock()
            mock_stripe.Customer.retrieve.return_value = _make_mock_customer(
                has_payment_method=True
            )
            mock_stripe.Subscription.retrieve.return_value = _make_mock_stripe_sub(
                charter_price_id=ids["prices"]["price_charter_monthly"],
                voice_price_id=voice_price_id,
                sms_price_id=sms_price_id,
                include_metered=False,
            )
            mock_updated = MagicMock()
            mock_updated.id = "sub_test_add_metered"
            mock_stripe.Subscription.modify.return_value = mock_updated
            mock_client.return_value = mock_stripe

            upgrade_charter_to_teams(
                db=db_session,
                tenant_id=second_tenant.id,
                billing_interval="monthly",
            )

        modify_call = mock_stripe.Subscription.modify.call_args
        items = modify_call.kwargs["items"]
        # 4 items: deleted charter + new teams + voice_overage + sms_overage
        assert len(items) == 4
        assert items[0] == {"id": "si_charter_123", "deleted": True}
        assert items[1] == {"price": teams_monthly_id, "quantity": 1}
        added_prices = [item.get("price") for item in items[2:]]
        assert voice_price_id in added_prices
        assert sms_price_id in added_prices

    def test_upgrade_not_charter_tenant(self, db_session, second_tenant):
        """Tenant with charter_eligible=False → ValueError."""
        from app.models.core import Tenant
        from services.stripe_subscriptions import upgrade_charter_to_teams

        tenant = db_session.exec(
            select(Tenant).where(Tenant.id == second_tenant.id)
        ).first()
        tenant.charter_eligible = False
        db_session.add(tenant)
        db_session.commit()

        with pytest.raises(ValueError, match="not a Charter member"):
            upgrade_charter_to_teams(
                db=db_session,
                tenant_id=second_tenant.id,
                billing_interval="monthly",
            )

    def test_upgrade_not_charter_tier(self, db_session, second_tenant):
        """Tenant on Starter tier (not Charter) → ValueError."""
        from app.models.core import Tenant
        from app.models.subscription import SubscriptionTier
        from services.stripe_subscriptions import upgrade_charter_to_teams

        starter_tier = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "starter")
        ).first()

        tenant = db_session.exec(
            select(Tenant).where(Tenant.id == second_tenant.id)
        ).first()
        tenant.charter_eligible = True
        tenant.current_subscription_tier_id = starter_tier.tier_id
        db_session.add(tenant)
        db_session.commit()

        with pytest.raises(ValueError, match="not on the Charter tier"):
            upgrade_charter_to_teams(
                db=db_session,
                tenant_id=second_tenant.id,
                billing_interval="monthly",
            )

    def test_upgrade_no_subscription(self, db_session, second_tenant):
        """No active subscription row → ValueError."""
        from services.stripe_subscriptions import upgrade_charter_to_teams

        _setup_charter_tenant(db_session, second_tenant)
        # No subscription row created

        with pytest.raises(ValueError, match="No active subscription"):
            upgrade_charter_to_teams(
                db=db_session,
                tenant_id=second_tenant.id,
                billing_interval="monthly",
            )

    def test_upgrade_no_payment_method(self, db_session, second_tenant):
        """Stripe customer has no default_payment_method → ValueError."""
        from core.stripe_config import get_stripe_ids
        from services.stripe_subscriptions import upgrade_charter_to_teams

        ids = get_stripe_ids()

        _setup_charter_tenant(db_session, second_tenant)
        _create_charter_subscription_row(
            db_session, second_tenant.id, "sub_test_no_pm", "cus_test_upgrade"
        )

        with (
            patch("services.stripe_subscriptions._get_stripe_client") as mock_client,
            patch("core.stripe_config.get_stripe_ids", return_value=ids),
        ):
            mock_stripe = MagicMock()
            mock_stripe.Customer.retrieve.return_value = _make_mock_customer(
                has_payment_method=False
            )
            mock_client.return_value = mock_stripe

            with pytest.raises(ValueError, match="No payment method"):
                upgrade_charter_to_teams(
                    db=db_session,
                    tenant_id=second_tenant.id,
                    billing_interval="monthly",
                )

    def test_upgrade_invalid_billing_interval(self, db_session, second_tenant):
        """billing_interval='weekly' → ValueError."""
        from services.stripe_subscriptions import upgrade_charter_to_teams

        with pytest.raises(ValueError, match="billing_interval must be"):
            upgrade_charter_to_teams(
                db=db_session,
                tenant_id=second_tenant.id,
                billing_interval="weekly",
            )

    def test_upgrade_stripe_error(self, db_session, second_tenant):
        """Stripe API raises → error propagates, charter_eligible NOT flipped (DB unchanged)."""
        from app.models.core import Tenant
        from core.stripe_config import get_stripe_ids
        from services.stripe_subscriptions import upgrade_charter_to_teams

        ids = get_stripe_ids()

        _setup_charter_tenant(db_session, second_tenant)
        _create_charter_subscription_row(
            db_session, second_tenant.id, "sub_test_stripe_err", "cus_test_upgrade"
        )

        with (
            patch("services.stripe_subscriptions._get_stripe_client") as mock_client,
            patch("core.stripe_config.get_stripe_ids", return_value=ids),
        ):
            mock_stripe = MagicMock()
            mock_stripe.Customer.retrieve.return_value = _make_mock_customer(
                has_payment_method=True
            )
            mock_stripe.Subscription.retrieve.return_value = _make_mock_stripe_sub(
                charter_price_id=ids["prices"]["price_charter_monthly"],
                voice_price_id=ids["prices"]["price_voice_overage"],
                sms_price_id=ids["prices"]["price_sms_overage"],
            )
            mock_stripe.Subscription.modify.side_effect = Exception("Stripe API error")
            mock_client.return_value = mock_stripe

            with pytest.raises(Exception, match="Stripe API error"):
                upgrade_charter_to_teams(
                    db=db_session,
                    tenant_id=second_tenant.id,
                    billing_interval="monthly",
                )

        # Verify charter_eligible was NOT flipped (DB unchanged)
        tenant = db_session.exec(
            select(Tenant).where(Tenant.id == second_tenant.id)
        ).first()
        assert tenant.charter_eligible is True


# ==================== ENDPOINT TESTS ====================


class TestUpgradeFromCharterEndpoint:
    """Tests for POST /upgrade-from-charter + /test twin."""

    def test_endpoint_test_twin(self, client, test_tenant):
        """Test endpoint bypasses Stripe, returns mock."""
        resp = client.post(
            f"/api/v1/tenants/{test_tenant.id}/subscription/upgrade-from-charter/test",
            json={"billing_interval": "monthly"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["new_tier_name"] == "teams"
        assert body["billing_interval"] == "monthly"
        assert body["charter_eligible_forfeited"] is True
        assert body["psp_subscription_id"] == "test_sub_mock_id"

    def test_endpoint_test_twin_annual(self, client, test_tenant):
        """Test endpoint with annual interval returns annual in response."""
        resp = client.post(
            f"/api/v1/tenants/{test_tenant.id}/subscription/upgrade-from-charter/test",
            json={"billing_interval": "annual"},
        )
        assert resp.status_code == 200
        assert resp.json()["billing_interval"] == "annual"

    def test_endpoint_test_twin_invalid_interval(self, client, test_tenant):
        """Test endpoint with invalid billing_interval → 422."""
        resp = client.post(
            f"/api/v1/tenants/{test_tenant.id}/subscription/upgrade-from-charter/test",
            json={"billing_interval": "weekly"},
        )
        assert resp.status_code == 422

    def test_endpoint_tenant_isolation(self, client, test_tenant):
        """tenant_id != test_context.tenant_id → 404 (tenant isolation)."""
        other_tenant_id = uuid.uuid4()
        resp = client.post(
            f"/api/v1/tenants/{other_tenant_id}/subscription/upgrade-from-charter/test",
            json={"billing_interval": "monthly"},
        )
        assert resp.status_code == 404
        detail = resp.json()["detail"]
        assert detail["status"] == 404
        assert "another tenant" in detail["detail"].lower()
