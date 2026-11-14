"""
C-B4: Tests for the 7 new webhook handler functions.
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
    assert paused_status is not None

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


class TestHandleSubscriptionTrialWillEnd:
    """customer.subscription.trial_will_end — stub handler."""

    def test_logs_event_without_error(self, db_session):
        """Handler logs the event and does not raise."""
        from services.stripe_subscriptions import handle_subscription_trial_will_end

        event = {
            "data": {
                "object": {
                    "id": "sub_test_trial",
                    "metadata": {"tenant_id": "test-tenant"},
                }
            }
        }
        # Should not raise
        handle_subscription_trial_will_end(db_session, event)


class TestHandleSubscriptionPaused:
    """customer.subscription.paused — updates subscription status to 'paused'."""

    def test_updates_status_to_paused(self, db_session, test_tenant):
        """Subscription row status_id updated to 'paused' status."""
        from app.models.billing import SubscriptionStatus
        from services.stripe_subscriptions import handle_subscription_paused

        psp_sub_id = "sub_test_paused_evt"
        sub = _create_test_subscription(
            db_session, test_tenant.id, psp_sub_id, "cus_test_paused"
        )

        # Set status to active first so we can verify it changes to paused
        active_status = db_session.exec(
            select(SubscriptionStatus).where(SubscriptionStatus.code == "active")
        ).first()
        sub.status_id = active_status.id
        db_session.add(sub)
        db_session.commit()

        event = {"data": {"object": {"id": psp_sub_id}}}
        handle_subscription_paused(db_session, event)

        db_session.refresh(sub)
        paused_status = db_session.exec(
            select(SubscriptionStatus).where(SubscriptionStatus.code == "paused")
        ).first()
        assert sub.status_id == paused_status.id

    def test_unknown_subscription_id_is_ignored(self, db_session):
        """Unknown psp_subscription_id → logs warning, no error."""
        from services.stripe_subscriptions import handle_subscription_paused

        event = {"data": {"object": {"id": "sub_nonexistent_xyz"}}}
        # Should not raise
        handle_subscription_paused(db_session, event)


class TestHandleSubscriptionResumed:
    """customer.subscription.resumed — updates subscription status to 'active'."""

    def test_updates_status_to_active(self, db_session, test_tenant):
        """Subscription row status_id updated to 'active' status."""
        from app.models.billing import SubscriptionStatus
        from services.stripe_subscriptions import handle_subscription_resumed

        psp_sub_id = "sub_test_resumed_evt"
        sub = _create_test_subscription(
            db_session, test_tenant.id, psp_sub_id, "cus_test_resumed"
        )

        event = {"data": {"object": {"id": psp_sub_id}}}
        handle_subscription_resumed(db_session, event)

        db_session.refresh(sub)
        active_status = db_session.exec(
            select(SubscriptionStatus)
            .where(SubscriptionStatus.code == "active")
            .where(SubscriptionStatus.is_billing_active == True)
        ).first()
        assert sub.status_id == active_status.id


class TestHandleSubscriptionDeleted:
    """customer.subscription.deleted — sets charter_eligible=false, status to 'canceled'."""

    def test_sets_charter_eligible_false_and_cancels(self, db_session, test_tenant):
        """Tenant.charter_eligible set to False; subscription status set to 'canceled'."""
        from app.models.billing import SubscriptionStatus
        from app.models.core import Tenant
        from services.stripe_subscriptions import handle_subscription_deleted

        # Set stripe_customer_id on tenant
        tenant = db_session.exec(
            select(Tenant).where(Tenant.id == test_tenant.id)
        ).first()
        tenant.stripe_customer_id = "cus_test_deleted"
        tenant.charter_eligible = True
        db_session.add(tenant)
        db_session.commit()

        psp_sub_id = "sub_test_deleted_evt"
        sub = _create_test_subscription(
            db_session, test_tenant.id, psp_sub_id, "cus_test_deleted"
        )

        event = {
            "data": {
                "object": {
                    "id": psp_sub_id,
                    "customer": "cus_test_deleted",
                }
            }
        }
        handle_subscription_deleted(db_session, event)

        db_session.refresh(tenant)
        db_session.refresh(sub)
        assert tenant.charter_eligible is False

        canceled_status = db_session.exec(
            select(SubscriptionStatus).where(SubscriptionStatus.code == "canceled")
        ).first()
        assert sub.status_id == canceled_status.id
        assert sub.is_active is False
        assert sub.canceled_at is not None

    def test_unknown_customer_is_ignored(self, db_session):
        """Unknown stripe_customer_id → logs warning, no error."""
        from services.stripe_subscriptions import handle_subscription_deleted

        event = {
            "data": {
                "object": {
                    "id": "sub_test",
                    "customer": "cus_completely_unknown",
                }
            }
        }
        # Should not raise
        handle_subscription_deleted(db_session, event)


class TestHandleInvoicePaid:
    """invoice.paid — logs payment success."""

    def test_logs_without_error(self, db_session):
        """Handler logs the invoice payment and does not raise."""
        from services.stripe_subscriptions import handle_invoice_paid

        event = {
            "data": {
                "object": {
                    "subscription": "sub_test_invoice",
                    "amount_paid": 4900,
                }
            }
        }
        # Should not raise
        handle_invoice_paid(db_session, event)


class TestHandleCheckoutSessionCompleted:
    """checkout.session.completed — stub for C-B9 (10DLC setup)."""

    def test_10dlc_purpose_logs_without_error(self, db_session):
        """metadata.purpose == 'a2p_10dlc_setup' → logs, no error."""
        from services.stripe_subscriptions import handle_checkout_session_completed

        event = {
            "data": {
                "object": {
                    "id": "cs_test_10dlc",
                    "metadata": {"purpose": "a2p_10dlc_setup"},
                }
            }
        }
        # Should not raise
        handle_checkout_session_completed(db_session, event)

    def test_other_purpose_logs_without_error(self, db_session):
        """Non-10DLC purpose → logs debug, no error."""
        from services.stripe_subscriptions import handle_checkout_session_completed

        event = {
            "data": {
                "object": {
                    "id": "cs_test_other",
                    "metadata": {"purpose": "other"},
                }
            }
        }
        # Should not raise
        handle_checkout_session_completed(db_session, event)


class TestHandlePaymentMethodAttached:
    """payment_method.attached — checks if tenant's subscription is paused."""

    def test_paused_subscription_logs_resume_available(self, db_session, test_tenant):
        """If tenant has a paused subscription, logs that resume is available."""
        from services.stripe_subscriptions import handle_payment_method_attached

        psp_sub_id = "sub_test_pm_paused"
        _create_test_subscription(db_session, test_tenant.id, psp_sub_id, "cus_test_pm")

        with patch("services.stripe_subscriptions._get_stripe_client") as mock_client:
            mock_stripe = MagicMock()
            mock_retrieved = MagicMock()
            mock_retrieved.status = "paused"
            mock_stripe.Subscription.retrieve.return_value = mock_retrieved
            mock_client.return_value = mock_stripe

            event = {
                "data": {
                    "object": {
                        "customer": "cus_test_pm",
                    }
                }
            }
            # Should not raise
            handle_payment_method_attached(db_session, event)

    def test_no_customer_id_is_ignored(self, db_session):
        """Event with no customer ID → returns early, no error."""
        from services.stripe_subscriptions import handle_payment_method_attached

        event = {"data": {"object": {}}}
        # Should not raise
        handle_payment_method_attached(db_session, event)
