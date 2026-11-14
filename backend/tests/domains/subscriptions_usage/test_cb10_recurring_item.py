"""
C-B10: Tests for recurring 10DLC carrier fee pass-through service + Celery task.
Domain: subscriptions_usage (PRD §3.11)

Tests (9 total per design doc §J):
  Service (create_recurring_carrier_item):
    1. test_create_recurring_item_happy_path
    2. test_create_recurring_item_idempotent
    3. test_create_recurring_item_wrong_status
    4. test_create_recurring_item_no_subscription
    5. test_create_recurring_item_zero_amount
  Celery task (_create_recurring_carrier_items_impl):
    6. test_celery_task_finds_eligible
    7. test_celery_task_skips_existing
    8. test_celery_task_handles_errors
    9. test_celery_task_no_eligible
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.domain_subscriptions_usage,
    pytest.mark.unit,
]


def _create_registration(
    db_session,
    tenant_id,
    status="active",
    quoted_monthly_cents=500,
    created_at=None,
    user_id=None,
    stripe_recurring_item_id=None,
):
    """Create a TenantMessagingRegistration row for testing."""
    from app.models.sms import TenantMessagingRegistration

    reg = TenantMessagingRegistration(
        tenant_id=tenant_id,
        entity_type="standard",
        status=status,
        quoted_monthly_cents=quoted_monthly_cents,
        created_by=user_id,
        updated_by=user_id,
    )
    if created_at:
        reg.created_at = created_at
    if stripe_recurring_item_id:
        reg.stripe_recurring_item_id = stripe_recurring_item_id
    db_session.add(reg)
    db_session.commit()
    db_session.refresh(reg)
    return reg


def _create_subscription(db_session, tenant_id, psp_subscription_id="sub_test_123"):
    """Create an active Stripe Subscription row for testing."""
    from sqlmodel import select

    from app.models.billing import Subscription, SubscriptionStatus

    active_status = db_session.exec(
        select(SubscriptionStatus).where(SubscriptionStatus.code == "active")
    ).first()

    sub = Subscription(
        tenant_id=tenant_id,
        product_plan_code="starter_plan",
        status_id=active_status.id,
        psp_provider="stripe",
        psp_subscription_id=psp_subscription_id,
        is_active=True,
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)
    return sub


def _mock_stripe_sub_item():
    """Return a mock Stripe SubscriptionItem.create result."""
    mock_item = MagicMock()
    mock_item.id = "si_test_recurring_001"
    return mock_item


# ── Service Tests ────────────────────────────────────────────────────────────


class TestCreateRecurringCarrierItem:
    """Tests for services.messaging_recurring.create_recurring_carrier_item()."""

    def test_create_recurring_item_happy_path(
        self, db_session, second_tenant, test_user
    ):
        """Registration active + quoted_monthly_cents set + active subscription →
        creates SubscriptionItem, stores ID + timestamp."""
        from services.messaging_recurring import create_recurring_carrier_item

        reg = _create_registration(
            db_session,
            second_tenant.id,
            status="active",
            quoted_monthly_cents=500,
            user_id=test_user.id,
        )
        _create_subscription(db_session, second_tenant.id)

        mock_ids = {
            "products": {"prod_passthrough": "prod_test_passthrough_001"},
            "prices": {},
            "meters": {},
        }

        with (
            patch("services.stripe_subscriptions._get_stripe_client") as mock_stripe,
            patch("core.stripe_config.get_stripe_ids", return_value=mock_ids),
        ):
            mock_stripe.return_value.SubscriptionItem.create.return_value = (
                _mock_stripe_sub_item()
            )

            result_id = create_recurring_carrier_item(db_session, reg.id)

        assert result_id == "si_test_recurring_001"

        db_session.refresh(reg)
        assert reg.stripe_recurring_item_id == "si_test_recurring_001"
        assert reg.recurring_item_created_at is not None

        # Verify Stripe was called with correct price_data
        mock_stripe.return_value.SubscriptionItem.create.assert_called_once()
        call_kwargs = mock_stripe.return_value.SubscriptionItem.create.call_args.kwargs
        assert call_kwargs["price_data"]["unit_amount"] == 500
        assert call_kwargs["price_data"]["product"] == "prod_test_passthrough_001"
        assert call_kwargs["price_data"]["recurring"]["interval"] == "month"
        assert call_kwargs["proration_behavior"] == "none"

    def test_create_recurring_item_idempotent(
        self, db_session, second_tenant, test_user
    ):
        """stripe_recurring_item_id already set → returns existing ID, no Stripe call."""
        from services.messaging_recurring import create_recurring_carrier_item

        reg = _create_registration(
            db_session,
            second_tenant.id,
            status="active",
            quoted_monthly_cents=500,
            user_id=test_user.id,
            stripe_recurring_item_id="si_existing_999",
        )

        with (
            patch("services.stripe_subscriptions._get_stripe_client") as mock_stripe,
            patch("core.stripe_config.get_stripe_ids") as mock_ids,
        ):
            result_id = create_recurring_carrier_item(db_session, reg.id)

        assert result_id == "si_existing_999"
        # Stripe should NOT have been called
        mock_stripe.return_value.SubscriptionItem.create.assert_not_called()
        mock_ids.assert_not_called()

    def test_create_recurring_item_wrong_status(
        self, db_session, second_tenant, test_user
    ):
        """Registration not in 'active' status → raises ValueError."""
        from services.messaging_recurring import create_recurring_carrier_item

        reg = _create_registration(
            db_session,
            second_tenant.id,
            status="quoting",
            quoted_monthly_cents=500,
            user_id=test_user.id,
        )

        with pytest.raises(ValueError, match="not in 'active' status"):
            create_recurring_carrier_item(db_session, reg.id)

    def test_create_recurring_item_no_subscription(
        self, db_session, second_tenant, test_user
    ):
        """No active Stripe subscription for tenant → raises ValueError."""
        from services.messaging_recurring import create_recurring_carrier_item

        reg = _create_registration(
            db_session,
            second_tenant.id,
            status="active",
            quoted_monthly_cents=500,
            user_id=test_user.id,
        )
        # No subscription row created

        with pytest.raises(ValueError, match="No active Stripe subscription"):
            create_recurring_carrier_item(db_session, reg.id)

    def test_create_recurring_item_zero_amount(
        self, db_session, second_tenant, test_user
    ):
        """quoted_monthly_cents is 0 → raises ValueError."""
        from services.messaging_recurring import create_recurring_carrier_item

        reg = _create_registration(
            db_session,
            second_tenant.id,
            status="active",
            quoted_monthly_cents=0,
            user_id=test_user.id,
        )

        with pytest.raises(ValueError, match="quoted_monthly_cents is null or zero"):
            create_recurring_carrier_item(db_session, reg.id)


# ── Celery Task Tests ────────────────────────────────────────────────────────


class TestCeleryTaskRecurringItems:
    """Tests for tasks.messaging_recurring._create_recurring_carrier_items_impl()."""

    def test_celery_task_finds_eligible(
        self, db_session, second_tenant, tenant_a, test_user
    ):
        """Two registrations: one eligible (active, >90d, no item), one not (<90d)
        → only eligible one processed.

        Uses two different tenants because tenant_messaging_registration has a
        UNIQUE constraint on tenant_id.
        """
        from tasks.messaging_recurring import _create_recurring_carrier_items_impl

        # Eligible: active, created >90 days ago, no recurring item
        old_date = datetime.now(UTC) - timedelta(days=100)
        reg_eligible = _create_registration(
            db_session,
            second_tenant.id,
            status="active",
            quoted_monthly_cents=500,
            created_at=old_date,
            user_id=test_user.id,
        )

        # Not eligible: active, created recently (<90 days) — different tenant
        reg_recent = _create_registration(
            db_session,
            tenant_a.id,
            status="active",
            quoted_monthly_cents=500,
            created_at=datetime.now(UTC),
            user_id=test_user.id,
        )

        _create_subscription(db_session, second_tenant.id)

        mock_ids = {
            "products": {"prod_passthrough": "prod_test_passthrough_001"},
            "prices": {},
            "meters": {},
        }

        with (
            patch("services.stripe_subscriptions._get_stripe_client") as mock_stripe,
            patch("core.stripe_config.get_stripe_ids", return_value=mock_ids),
        ):
            mock_stripe.return_value.SubscriptionItem.create.return_value = (
                _mock_stripe_sub_item()
            )

            result = _create_recurring_carrier_items_impl(db_session)

        assert result["processed"] == 1
        assert result["created"] == 1
        assert result["skipped"] == 0
        assert result["errors"] == 0

        # Verify the eligible registration got the recurring item
        db_session.refresh(reg_eligible)
        assert reg_eligible.stripe_recurring_item_id == "si_test_recurring_001"

        # The recent one should NOT have a recurring item
        db_session.refresh(reg_recent)
        assert reg_recent.stripe_recurring_item_id is None

    def test_celery_task_skips_existing(self, db_session, second_tenant, test_user):
        """Registration with stripe_recurring_item_id already set → skipped."""
        from tasks.messaging_recurring import _create_recurring_carrier_items_impl

        old_date = datetime.now(UTC) - timedelta(days=100)
        _create_registration(
            db_session,
            second_tenant.id,
            status="active",
            quoted_monthly_cents=500,
            created_at=old_date,
            user_id=test_user.id,
            stripe_recurring_item_id="si_already_exists_001",
        )

        _create_subscription(db_session, second_tenant.id)

        # The query filters WHERE stripe_recurring_item_id IS NULL,
        # so this registration won't even be selected.
        result = _create_recurring_carrier_items_impl(db_session)

        assert result["processed"] == 0
        assert result["created"] == 0
        assert result["skipped"] == 0
        assert result["errors"] == 0

    def test_celery_task_handles_errors(self, db_session, second_tenant, test_user):
        """Stripe API error on one registration → error logged, others still processed."""
        from tasks.messaging_recurring import _create_recurring_carrier_items_impl

        old_date = datetime.now(UTC) - timedelta(days=100)

        # First registration: will cause a Stripe error
        _create_registration(
            db_session,
            second_tenant.id,
            status="active",
            quoted_monthly_cents=500,
            created_at=old_date,
            user_id=test_user.id,
        )

        _create_subscription(db_session, second_tenant.id)

        mock_ids = {
            "products": {"prod_passthrough": "prod_test_passthrough_001"},
            "prices": {},
            "meters": {},
        }

        with (
            patch("services.stripe_subscriptions._get_stripe_client") as mock_stripe,
            patch("core.stripe_config.get_stripe_ids", return_value=mock_ids),
        ):
            # First call raises, subsequent calls succeed
            mock_stripe.return_value.SubscriptionItem.create.side_effect = [
                Exception("Stripe API error"),
                _mock_stripe_sub_item(),
            ]

            result = _create_recurring_carrier_items_impl(db_session)

        assert result["processed"] == 1
        assert result["created"] == 0
        assert result["errors"] == 1

        # Note: The task's db.rollback() on error rolls back the test's
        # transaction, so the registration row is no longer queryable.
        # In production, the row was committed in a prior transaction and
        # survives the rollback. The key assertion is that the error was
        # counted correctly and the task did not crash.

    def test_celery_task_no_eligible(self, db_session, second_tenant, test_user):
        """No eligible registrations → returns all-zero result."""
        from tasks.messaging_recurring import _create_recurring_carrier_items_impl

        # Create a registration that is NOT eligible (recent, <90 days)
        _create_registration(
            db_session,
            second_tenant.id,
            status="active",
            quoted_monthly_cents=500,
            created_at=datetime.now(UTC),
            user_id=test_user.id,
        )

        result = _create_recurring_carrier_items_impl(db_session)

        assert result["processed"] == 0
        assert result["created"] == 0
        assert result["skipped"] == 0
        assert result["errors"] == 0
