"""
C-B4: Tests for resume_subscription() — C-SPIKE-1 resume flow with status check.
Domain: subscriptions_usage (PRD §3.11)
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import select

pytestmark = [
    pytest.mark.domain_subscriptions_usage,
    pytest.mark.unit,
]


def _create_test_subscription(db_session, tenant_id, psp_sub_id, psp_customer_id):
    """Insert a subscription row scoped to this test (rolled back after test)."""
    from app.models.billing import Subscription, SubscriptionStatus

    paused_status = db_session.exec(
        select(SubscriptionStatus).where(SubscriptionStatus.code == "paused")
    ).first()
    assert paused_status is not None, "paused subscription_status not seeded"

    sub = Subscription(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        product_plan_code="starter_plan",
        status_id=paused_status.id,
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


class TestResumeSubscription:
    """Tests for resume_subscription() with mocked Stripe."""

    def test_resume_success_updates_status_to_active(self, db_session, second_tenant):
        """Successful resume: status updated to 'active' in DB, returns sub id + status.

        Also verifies that metered overage items are added after resume
        (Stripe trial-pause constraint prevents metered items at creation).

        Uses second_tenant to avoid the seeded subscription (which has
        psp_subscription_id=NULL) on test_tenant.
        """
        from app.models.billing import SubscriptionStatus
        from app.models.core import Tenant
        from services.stripe_subscriptions import resume_subscription

        # Set stripe_customer_id on the test tenant
        tenant = db_session.exec(
            select(Tenant).where(Tenant.id == second_tenant.id)
        ).first()
        tenant.stripe_customer_id = "cus_test_resume_ok"
        db_session.add(tenant)
        db_session.commit()

        psp_sub_id = "sub_test_resume_ok"
        sub = _create_test_subscription(
            db_session, second_tenant.id, psp_sub_id, "cus_test_resume_ok"
        )

        with (
            patch("services.stripe_subscriptions._get_stripe_client") as mock_client,
            patch("core.stripe_config.get_stripe_ids") as mock_ids,
        ):
            mock_stripe = MagicMock()

            # First retrieve: returns paused (for the initial status check)
            # Second retrieve: returns sub with items (for _add_metered_overage_items)
            mock_paused = MagicMock()
            mock_paused.status = "paused"

            mock_for_items = MagicMock()
            mock_for_items.__getitem__ = MagicMock(
                side_effect=lambda key: {"items": {"data": []}}[key]
            )

            mock_stripe.Subscription.retrieve.side_effect = [
                mock_paused,  # initial retrieve (check paused)
                mock_for_items,  # retrieve inside _add_metered_overage_items
            ]

            # resume returns active
            mock_resumed = MagicMock()
            mock_resumed.id = psp_sub_id
            mock_resumed.status = "active"
            mock_resumed.billing_cycle_anchor = 1700000000
            mock_stripe.Subscription.resume.return_value = mock_resumed

            # Mock stripe IDs for _add_metered_overage_items
            mock_ids.return_value = {
                "prices": {
                    "price_voice_overage": "price_voice_test",
                    "price_sms_overage": "price_sms_test",
                }
            }

            mock_client.return_value = mock_stripe

            result = resume_subscription(
                db=db_session,
                tenant_id=second_tenant.id,
                stripe_payment_method_id="pm_test_ok",
            )

        assert result["psp_subscription_id"] == psp_sub_id
        assert result["status"] == "active"
        assert result["billing_cycle_anchor"] == 1700000000

        # Verify PM attached + set as default
        mock_stripe.PaymentMethod.attach.assert_called_once_with(
            "pm_test_ok", customer="cus_test_resume_ok"
        )
        mock_stripe.Customer.modify.assert_called_once_with(
            "cus_test_resume_ok",
            invoice_settings={"default_payment_method": "pm_test_ok"},
        )

        # Verify metered overage items were added after resume
        mock_stripe.Subscription.modify.assert_called_once()
        modify_items = mock_stripe.Subscription.modify.call_args.kwargs["items"]
        added_prices = [item["price"] for item in modify_items]
        assert "price_voice_test" in added_prices
        assert "price_sms_test" in added_prices

        # Verify DB status updated to active
        db_session.refresh(sub)
        active_status = db_session.exec(
            select(SubscriptionStatus).where(SubscriptionStatus.code == "active")
        ).first()
        assert sub.status_id == active_status.id

    def test_resume_silent_fail_raises_resume_failed_error(
        self, db_session, second_tenant
    ):
        """C-SPIKE-1 critical: resume returns 200 but status stays 'paused' → ResumeFailedError.

        Uses second_tenant to avoid the seeded subscription (which has
        psp_subscription_id=NULL) on test_tenant.
        """
        from app.models.core import Tenant
        from services.stripe_subscriptions import ResumeFailedError, resume_subscription

        tenant = db_session.exec(
            select(Tenant).where(Tenant.id == second_tenant.id)
        ).first()
        tenant.stripe_customer_id = "cus_test_resume_fail"
        db_session.add(tenant)
        db_session.commit()

        _create_test_subscription(
            db_session, second_tenant.id, "sub_test_resume_fail", "cus_test_resume_fail"
        )

        with patch("services.stripe_subscriptions._get_stripe_client") as mock_client:
            mock_stripe = MagicMock()

            mock_retrieved = MagicMock()
            mock_retrieved.status = "paused"
            mock_stripe.Subscription.retrieve.return_value = mock_retrieved

            # resume returns paused (silent fail!)
            mock_resumed = MagicMock()
            mock_resumed.status = "paused"
            mock_resumed.id = "sub_test_resume_fail"
            mock_stripe.Subscription.resume.return_value = mock_resumed

            mock_client.return_value = mock_stripe

            with pytest.raises(ResumeFailedError):
                resume_subscription(
                    db=db_session,
                    tenant_id=second_tenant.id,
                    stripe_payment_method_id="pm_test_fail",
                )

    def test_resume_non_paused_raises_value_error(self, db_session, second_tenant):
        """Resume on a subscription that is not paused → ValueError.

        Uses second_tenant to avoid the seeded subscription (which has
        psp_subscription_id=NULL) on test_tenant.
        """
        from app.models.core import Tenant
        from services.stripe_subscriptions import resume_subscription

        tenant = db_session.exec(
            select(Tenant).where(Tenant.id == second_tenant.id)
        ).first()
        tenant.stripe_customer_id = "cus_test_resume_notpaused"
        db_session.add(tenant)
        db_session.commit()

        _create_test_subscription(
            db_session,
            second_tenant.id,
            "sub_test_resume_notpaused",
            "cus_test_resume_notpaused",
        )

        with patch("services.stripe_subscriptions._get_stripe_client") as mock_client:
            mock_stripe = MagicMock()

            # retrieve returns active (not paused)
            mock_retrieved = MagicMock()
            mock_retrieved.status = "active"
            mock_stripe.Subscription.retrieve.return_value = mock_retrieved

            mock_client.return_value = mock_stripe

            with pytest.raises(ValueError, match="not paused"):
                resume_subscription(
                    db=db_session,
                    tenant_id=second_tenant.id,
                    stripe_payment_method_id="pm_test",
                )

    def test_resume_no_stripe_customer_id_raises_value_error(
        self, db_session, test_tenant
    ):
        """Tenant with no stripe_customer_id → ValueError."""
        from app.models.core import Tenant
        from services.stripe_subscriptions import resume_subscription

        # Ensure tenant has no stripe_customer_id
        tenant = db_session.exec(
            select(Tenant).where(Tenant.id == test_tenant.id)
        ).first()
        tenant.stripe_customer_id = None
        db_session.add(tenant)
        db_session.commit()

        with pytest.raises(ValueError, match="no Stripe customer ID"):
            resume_subscription(
                db=db_session,
                tenant_id=test_tenant.id,
                stripe_payment_method_id="pm_test",
            )
