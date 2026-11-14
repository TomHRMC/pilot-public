"""
STRIPE-B1: Test subscription stripe_schedule_id column + charter schedule service.
"""

import pytest
from sqlmodel import select

pytestmark = [
    pytest.mark.domain_subscriptions_usage,
    pytest.mark.unit,
]


class TestStripeScheduleIdColumn:
    """Verify stripe_schedule_id column exists and is functional."""

    def test_subscription_model_has_stripe_schedule_id(self, db_session, test_tenant):
        """Subscription model accepts stripe_schedule_id field without error."""
        from app.models.billing import Subscription

        # Fetch test tenant's subscription
        sub = db_session.exec(
            select(Subscription).where(Subscription.tenant_id == test_tenant.id)
        ).first()

        # Column must exist on the model (may be None)
        assert hasattr(sub, "stripe_schedule_id"), (
            "stripe_schedule_id field missing from Subscription model — "
            "STRIPE-B1 migration may not have run"
        )

    def test_stripe_schedule_id_is_nullable(self, db_session, test_tenant):
        """stripe_schedule_id is NULL for existing subscriptions (expected pre-charter)."""
        from app.models.billing import Subscription

        sub = db_session.exec(
            select(Subscription).where(Subscription.tenant_id == test_tenant.id)
        ).first()
        assert sub is not None
        # Existing subscriptions have no schedule — NULL is correct
        assert sub.stripe_schedule_id is None


class TestCreateCharterScheduleService:
    """Test create_charter_subscription_schedule() with mocked Stripe."""

    def test_returns_none_when_starter_price_not_configured(self, db_session):
        """Returns None gracefully when starter tier has no stripe_price_id_monthly."""
        import uuid

        from app.models.subscription import SubscriptionTier
        from services.stripe_subscriptions import create_charter_subscription_schedule

        # Temporarily unset starter price for this test
        starter = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "starter")
        ).first()
        assert starter is not None

        original_price = starter.stripe_price_id_monthly
        starter.stripe_price_id_monthly = None
        db_session.add(starter)
        db_session.flush()

        try:
            result = create_charter_subscription_schedule(
                db_session,
                uuid.uuid4(),
                "cus_test_mock",
            )
            assert result is None, "Should return None when price not configured"
        finally:
            # Restore
            starter.stripe_price_id_monthly = original_price
            db_session.add(starter)
            db_session.flush()

    def test_returns_none_on_stripe_api_error(self, db_session):
        """Returns None (does not raise) when Stripe API raises an exception."""
        import uuid
        from unittest.mock import MagicMock, patch

        from services.stripe_subscriptions import create_charter_subscription_schedule

        with patch("services.stripe_subscriptions._get_stripe_client") as mock_client:
            mock_stripe = MagicMock()
            mock_stripe.SubscriptionSchedule.create.side_effect = Exception(
                "Stripe unavailable"
            )
            mock_client.return_value = mock_stripe

            result = create_charter_subscription_schedule(
                db_session,
                uuid.uuid4(),
                "cus_test_mock",
            )
            # Non-blocking: error logged, None returned, no exception raised
            assert result is None


class TestHandleSubscriptionScheduleUpdated:
    """Test handle_subscription_schedule_updated() webhook handler."""

    def test_ignores_non_charter_schedules(self, db_session):
        """Silently ignores schedules without schedule_type=charter_cohort."""
        from services.stripe_subscriptions import handle_subscription_schedule_updated

        non_charter_event = {
            "data": {
                "object": {
                    "id": "sub_sched_test",
                    "customer": "cus_test",
                    "metadata": {"schedule_type": "other"},
                    "current_phase": {},
                    "phases": [],
                }
            }
        }
        # Should not raise and should not modify any DB state
        handle_subscription_schedule_updated(db_session, non_charter_event)

    def test_ignores_phase_1_events(self, db_session):
        """Phase 1 (index 0) events do not trigger tier change."""
        from services.stripe_subscriptions import handle_subscription_schedule_updated

        phase_1_event = {
            "data": {
                "object": {
                    "id": "sub_sched_test",
                    "customer": "cus_nonexistent",
                    "metadata": {"schedule_type": "charter_cohort"},
                    "current_phase": {"start_date": 1000000},
                    "phases": [
                        {"start_date": 1000000, "items": []},  # Phase 1 — current
                        {
                            "start_date": 2000000,
                            "items": [{"price": {"id": "price_x"}}],
                        },
                    ],
                }
            }
        }
        # Phase 1 → no tier change (tenant not found anyway since customer is nonexistent)
        handle_subscription_schedule_updated(db_session, phase_1_event)

    def test_ignores_unknown_customer(self, db_session):
        """Charter schedule for unknown stripe_customer_id is safely ignored."""
        from services.stripe_subscriptions import handle_subscription_schedule_updated

        unknown_customer_event = {
            "data": {
                "object": {
                    "id": "sub_sched_test",
                    "customer": "cus_completely_unknown_xyz",
                    "metadata": {"schedule_type": "charter_cohort"},
                    "current_phase": {"start_date": 2000000},
                    "phases": [
                        {"start_date": 1000000, "items": []},
                        {
                            "start_date": 2000000,
                            "items": [{"price": {"id": "price_x"}}],
                        },
                    ],
                }
            }
        }
        # Should not raise — just logs a warning
        handle_subscription_schedule_updated(db_session, unknown_customer_event)
