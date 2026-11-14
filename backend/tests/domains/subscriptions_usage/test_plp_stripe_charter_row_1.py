"""
PLP-STRIPE-CHARTER-ROW-1: local `subscription` row written for Charter signups.

Covers the shared helper `_write_local_charter_subscription_row()`, the
write-at-source call in `create_charter_subscription()`, the Charter-metadata
fallback in `handle_subscription_created()`, and the paywall flip in
`is_subscription_billing_active()`.

Domain: subscriptions_usage (PRD §3.11)
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

_FREE_PERIOD_END = datetime(2026, 11, 9, tzinfo=UTC)


def _row_for_psp_sub_id(db, psp_subscription_id: str):
    """Fetch the subscription row for a given Stripe sub id (ID-scoped)."""
    from app.models.billing import Subscription

    return db.exec(
        select(Subscription).where(
            Subscription.psp_subscription_id == psp_subscription_id
        )
    ).first()


def _rows_for_psp_sub_id(db, psp_subscription_id: str) -> list:
    from app.models.billing import Subscription

    return list(
        db.exec(
            select(Subscription).where(
                Subscription.psp_subscription_id == psp_subscription_id
            )
        ).all()
    )


def _trialing_status_id(db):
    from app.models.billing import SubscriptionStatus

    status = db.exec(
        select(SubscriptionStatus).where(SubscriptionStatus.code == "trialing")
    ).first()
    assert status is not None, "subscription_status 'trialing' must be seeded"
    return status.id


def _unique_sub_id() -> str:
    return f"sub_test_plp_{uuid.uuid4().hex[:16]}"


def _make_stripe_mock(sub_id: str):
    mock_stripe = MagicMock()
    mock_sub = MagicMock()
    mock_sub.id = sub_id
    mock_sub.status = "trialing"
    mock_stripe.Subscription.create.return_value = mock_sub
    return mock_stripe


class TestWriteLocalCharterSubscriptionRow:
    """Tests 1-2: the shared helper's insert + idempotent upsert."""

    def test_helper_insert_creates_trialing_row(self, db_session, second_tenant):
        """Helper creates exactly one row: status=trialing, is_active=True,
        correct psp ids, billing_interval=monthly, trial_ends_at==free_period."""
        from services.stripe_subscriptions import (
            _write_local_charter_subscription_row,
        )

        sub_id = _unique_sub_id()
        _write_local_charter_subscription_row(
            db_session,
            tenant_id=second_tenant.id,
            stripe_customer_id="cus_test_plp_helper",
            stripe_subscription_id=sub_id,
            free_period_ends_at=_FREE_PERIOD_END,
        )

        row = _row_for_psp_sub_id(db_session, sub_id)
        assert row is not None
        assert row.tenant_id == second_tenant.id
        assert row.status_id == _trialing_status_id(db_session)
        assert row.is_active is True
        assert row.psp_provider == "stripe"
        assert row.psp_customer_id == "cus_test_plp_helper"
        assert row.billing_interval == "monthly"
        assert row.quantity_seats == 1
        assert row.trial_ends_at == _FREE_PERIOD_END
        assert row.renews_at == _FREE_PERIOD_END
        assert row.stripe_schedule_id is None
        # product_plan_code resolved from the Charter tier (never hardcoded)
        from app.models.subscription import SubscriptionTier

        charter_tier = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "charter")
        ).first()
        assert row.product_plan_code == charter_tier.product_plan_code

    def test_helper_idempotent_rerun_no_duplicate(self, db_session, second_tenant):
        """Calling the helper twice with the same psp_subscription_id yields
        one row (upsert), not a duplicate."""
        from services.stripe_subscriptions import (
            _write_local_charter_subscription_row,
        )

        sub_id = _unique_sub_id()
        for _ in range(2):
            _write_local_charter_subscription_row(
                db_session,
                tenant_id=second_tenant.id,
                stripe_customer_id="cus_test_plp_idem",
                stripe_subscription_id=sub_id,
                free_period_ends_at=_FREE_PERIOD_END,
            )

        rows = _rows_for_psp_sub_id(db_session, sub_id)
        assert len(rows) == 1
        assert rows[0].status_id == _trialing_status_id(db_session)
        assert rows[0].is_active is True


class TestCreateCharterSubscriptionLocalRow:
    """Test 3 + 6: create-path writes the row and never propagates failures."""

    def test_create_path_writes_local_row(self, db_session, second_tenant):
        """create_charter_subscription() (Stripe mocked) results in the local
        subscription row existing for the tenant."""
        from services.stripe_subscriptions import create_charter_subscription

        sub_id = _unique_sub_id()
        with patch("services.stripe_subscriptions._get_stripe_client") as mock_client:
            mock_client.return_value = _make_stripe_mock(sub_id)

            result = create_charter_subscription(
                db=db_session,
                tenant_id=second_tenant.id,
                stripe_customer_id="cus_test_plp_create",
                free_period_ends_at=_FREE_PERIOD_END,
            )

        assert result == sub_id
        row = _row_for_psp_sub_id(db_session, sub_id)
        assert row is not None
        assert row.tenant_id == second_tenant.id
        assert row.status_id == _trialing_status_id(db_session)
        assert row.is_active is True
        assert row.trial_ends_at == _FREE_PERIOD_END

    def test_create_path_swallows_helper_error(self, db_session, second_tenant):
        """A helper that raises internally does not propagate out of
        create_charter_subscription() — sub.id is still returned."""
        from services.stripe_subscriptions import create_charter_subscription

        sub_id = _unique_sub_id()
        with (
            patch("services.stripe_subscriptions._get_stripe_client") as mock_client,
            patch(
                "services.stripe_subscriptions._write_local_charter_subscription_row",
                side_effect=RuntimeError("boom"),
            ),
        ):
            mock_client.return_value = _make_stripe_mock(sub_id)

            result = create_charter_subscription(
                db=db_session,
                tenant_id=second_tenant.id,
                stripe_customer_id="cus_test_plp_swallow",
                free_period_ends_at=_FREE_PERIOD_END,
            )

        assert result == sub_id


class TestWebhookCharterMetadataFallback:
    """Test 4: handle_subscription_created() Charter-metadata fallback."""

    def test_charter_metadata_fallback_writes_row(self, db_session, second_tenant):
        """Payload whose price ID matches no tier but metadata.tier_code=charter
        writes the local row via the fallback."""
        from services.stripe_subscriptions import handle_subscription_created

        second_tenant.stripe_customer_id = "cus_test_plp_wh_charter"
        second_tenant.free_period_ends_at = _FREE_PERIOD_END
        db_session.add(second_tenant)
        db_session.commit()

        sub_id = _unique_sub_id()
        event = {
            "data": {
                "object": {
                    "id": sub_id,
                    "customer": "cus_test_plp_wh_charter",
                    "metadata": {"tier_code": "charter"},
                    "items": {
                        "data": [
                            {
                                "price": {
                                    "id": f"price_unknown_{uuid.uuid4().hex[:8]}",
                                    "recurring": {"interval": "month"},
                                }
                            }
                        ]
                    },
                }
            }
        }

        handle_subscription_created(db_session, event)

        row = _row_for_psp_sub_id(db_session, sub_id)
        assert row is not None
        assert row.tenant_id == second_tenant.id
        assert row.status_id == _trialing_status_id(db_session)
        assert row.is_active is True
        assert row.trial_ends_at == _FREE_PERIOD_END
        assert row.psp_customer_id == "cus_test_plp_wh_charter"

    def test_non_charter_unknown_price_still_returns_early(
        self, db_session, second_tenant
    ):
        """Non-Charter payload with an unknown price returns early unchanged —
        no row is written."""
        from services.stripe_subscriptions import handle_subscription_created

        second_tenant.stripe_customer_id = "cus_test_plp_wh_noncharter"
        db_session.add(second_tenant)
        db_session.commit()

        sub_id = _unique_sub_id()
        event = {
            "data": {
                "object": {
                    "id": sub_id,
                    "customer": "cus_test_plp_wh_noncharter",
                    "metadata": {"tier_code": "starter"},
                    "items": {
                        "data": [
                            {
                                "price": {
                                    "id": f"price_unknown_{uuid.uuid4().hex[:8]}",
                                    "recurring": {"interval": "month"},
                                }
                            }
                        ]
                    },
                }
            }
        }

        handle_subscription_created(db_session, event)

        assert _row_for_psp_sub_id(db_session, sub_id) is None


class TestPaywallFlip:
    """Test 5: is_subscription_billing_active() flips True after the helper."""

    def test_paywall_flips_to_true_after_helper(self, db_session, second_tenant):
        """Before the helper runs there is no subscription row → False; after
        the helper writes the trialing row → True."""
        from services.entitlement_service import is_subscription_billing_active
        from services.stripe_subscriptions import (
            _write_local_charter_subscription_row,
        )

        # second_tenant has no seeded subscription rows → paywall closed
        assert is_subscription_billing_active(db_session, second_tenant.id) is False

        _write_local_charter_subscription_row(
            db_session,
            tenant_id=second_tenant.id,
            stripe_customer_id="cus_test_plp_paywall",
            stripe_subscription_id=_unique_sub_id(),
            free_period_ends_at=_FREE_PERIOD_END,
        )

        assert is_subscription_billing_active(db_session, second_tenant.id) is True
