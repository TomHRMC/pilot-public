"""
C-B4: Tests for create_charter_subscription() — Charter subscription creation with trial.
Domain: subscriptions_usage (PRD §3.11)
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.domain_subscriptions_usage,
    pytest.mark.unit,
]


class TestCreateCharterSubscription:
    """Tests for create_charter_subscription() with mocked Stripe."""

    def test_creates_subscription_with_trial_end_and_trial_settings(self, db_session):
        """Subscription.create is called with trial_end (absolute timestamp) and
        trial_settings.end_behavior.missing_payment_method = pause."""
        from services.stripe_subscriptions import create_charter_subscription

        tenant_id = uuid.uuid4()
        free_period_ends_at = datetime(2026, 11, 4, tzinfo=UTC)

        # PLP-STRIPE-CHARTER-ROW-1: mock the local-row write — these tests use a
        # random (non-existent) tenant_id and verify the Stripe call contract only.
        with (
            patch("services.stripe_subscriptions._get_stripe_client") as mock_client,
            patch(
                "services.stripe_subscriptions._write_local_charter_subscription_row"
            ),
        ):
            mock_stripe = MagicMock()
            mock_sub = MagicMock()
            mock_sub.id = "sub_test_charter_123"
            mock_sub.status = "trialing"
            mock_stripe.Subscription.create.return_value = mock_sub
            mock_client.return_value = mock_stripe

            result = create_charter_subscription(
                db=db_session,
                tenant_id=tenant_id,
                stripe_customer_id="cus_test_charter",
                free_period_ends_at=free_period_ends_at,
            )

        assert result == "sub_test_charter_123"
        mock_stripe.Subscription.create.assert_called_once()
        call_kwargs = mock_stripe.Subscription.create.call_args.kwargs
        assert call_kwargs["trial_end"] == int(free_period_ends_at.timestamp())
        assert call_kwargs["trial_settings"] == {
            "end_behavior": {"missing_payment_method": "pause"}
        }
        assert call_kwargs["payment_behavior"] == "allow_incomplete"

    def test_creates_subscription_with_single_flat_rate_item(self, db_session):
        """Subscription.create is called with 1 item: charter_monthly (qty=1).

        Metered overage items (voice_overage, sms_overage) are NOT included
        at creation time — Stripe does not allow metered usage items on
        subscriptions configured to pause at trial end. They are added by
        resume_subscription() after a payment method is attached.
        """
        from services.stripe_subscriptions import create_charter_subscription

        tenant_id = uuid.uuid4()
        free_period_ends_at = datetime(2026, 11, 4, tzinfo=UTC)

        with (
            patch("services.stripe_subscriptions._get_stripe_client") as mock_client,
            patch(
                "services.stripe_subscriptions._write_local_charter_subscription_row"
            ),
        ):
            mock_stripe = MagicMock()
            mock_sub = MagicMock()
            mock_sub.id = "sub_test_charter_456"
            mock_sub.status = "trialing"
            mock_stripe.Subscription.create.return_value = mock_sub
            mock_client.return_value = mock_stripe

            create_charter_subscription(
                db=db_session,
                tenant_id=tenant_id,
                stripe_customer_id="cus_test_charter",
                free_period_ends_at=free_period_ends_at,
            )

        call_kwargs = mock_stripe.Subscription.create.call_args.kwargs
        items = call_kwargs["items"]
        assert len(items) == 1
        # Only the charter monthly flat-rate item with quantity=1
        assert items[0]["quantity"] == 1

    def test_metadata_includes_tenant_id_and_charter_member_number(self, db_session):
        """Subscription metadata includes tenant_id, tier_code=charter, and
        charter_member_number when provided."""
        from services.stripe_subscriptions import create_charter_subscription

        tenant_id = uuid.uuid4()
        free_period_ends_at = datetime(2026, 11, 4, tzinfo=UTC)
        charter_member_number = 42

        with (
            patch("services.stripe_subscriptions._get_stripe_client") as mock_client,
            patch(
                "services.stripe_subscriptions._write_local_charter_subscription_row"
            ),
        ):
            mock_stripe = MagicMock()
            mock_sub = MagicMock()
            mock_sub.id = "sub_test_charter_789"
            mock_sub.status = "trialing"
            mock_stripe.Subscription.create.return_value = mock_sub
            mock_client.return_value = mock_stripe

            create_charter_subscription(
                db=db_session,
                tenant_id=tenant_id,
                stripe_customer_id="cus_test_charter",
                free_period_ends_at=free_period_ends_at,
                charter_member_number=charter_member_number,
            )

        call_kwargs = mock_stripe.Subscription.create.call_args.kwargs
        metadata = call_kwargs["metadata"]
        assert metadata["tenant_id"] == str(tenant_id)
        assert metadata["tier_code"] == "charter"
        assert metadata["charter_member_number"] == "42"
