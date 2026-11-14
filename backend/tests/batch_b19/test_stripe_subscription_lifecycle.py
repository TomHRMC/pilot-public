"""
B19 — FIND-102: Stripe Subscription Lifecycle Tests
Tests for convert-from-trial and change-tier endpoints + webhook handler.
"""

import uuid

import pytest
from sqlmodel import Session, select

from app.models.billing import (
    ProductFeature,
    ProductPlan,
    Subscription,
    SubscriptionStatus,
)
from app.models.subscription import SubscriptionTier


@pytest.fixture
def product_plans_seeded(db_session: Session):
    """Seed product_plan and product_feature lookups required for subscription tests."""
    starter = ProductPlan(code="starter_monthly", name="Starter Monthly")
    professional = ProductPlan(code="professional_monthly", name="Professional Monthly")
    sms_feature = ProductFeature(code="sms_messages", name="SMS Messages", unit="count")
    db_session.add(starter)
    db_session.add(professional)
    db_session.add(sms_feature)
    db_session.commit()
    return {
        "starter_monthly": starter,
        "professional_monthly": professional,
        "sms_messages": sms_feature,
    }


@pytest.fixture
def subscription_tier_trial(db_session: Session, product_plans_seeded):
    """Seed a trial tier."""
    tier = SubscriptionTier(
        tier_id=uuid.uuid4(),
        tier_name="trial_b19_test",
        display_label="30-Day Trial",
        annual_price_cents=0,  # SD-3: renamed from monthly_price_cents
        monthly_price_cents=0,  # SD-3: new M2M premium column
        is_trial=True,
        trial_duration_days=30,
        display_order=91,
        is_active=True,
        schedule_lanes=0,
    )
    db_session.add(tier)
    db_session.commit()
    db_session.refresh(tier)
    return tier


@pytest.fixture
def subscription_tier_starter(db_session: Session, product_plans_seeded):
    """Seed a paid starter tier."""
    tier = SubscriptionTier(
        tier_id=uuid.uuid4(),
        tier_name="starter_b19_test",
        display_label="Starter - $99/mo",
        annual_price_cents=9900,  # SD-3: renamed from monthly_price_cents
        monthly_price_cents=9900,  # SD-3: new M2M premium column
        is_trial=False,
        display_order=92,
        stripe_price_id_monthly="price_starter_test",  # SD-3: renamed from stripe_price_id
        product_plan_code="starter_monthly",
        is_active=True,
        schedule_lanes=0,
    )
    db_session.add(tier)
    db_session.commit()
    db_session.refresh(tier)
    return tier


@pytest.fixture
def subscription_tier_professional(db_session: Session, product_plans_seeded):
    """Seed a paid professional tier."""
    tier = SubscriptionTier(
        tier_id=uuid.uuid4(),
        tier_name="professional_b19_test",
        display_label="Professional - $299/mo",
        annual_price_cents=29900,  # SD-3: renamed from monthly_price_cents
        monthly_price_cents=29900,  # SD-3: new M2M premium column
        is_trial=False,
        display_order=93,
        stripe_price_id_monthly="price_professional_test",  # SD-3: renamed from stripe_price_id
        product_plan_code="professional_monthly",
        is_active=True,
        schedule_lanes=0,
    )
    db_session.add(tier)
    db_session.commit()
    db_session.refresh(tier)
    return tier


@pytest.fixture
def subscription_status_active(db_session: Session, test_tenant):
    """Look up the seeded 'active' subscription_status row.

    IMPORTANT: This row is seeded by seed_platform.py, NOT by this fixture.
    If this assertion fails, run: python migrations/scripts/seed_platform.py
    """
    from sqlalchemy import text

    row = db_session.execute(
        text("""
            SELECT id, code, name, is_billing_active
            FROM public.subscription_status
            WHERE code = :code AND tenant_id IS NULL
            LIMIT 1
        """),
        {"code": "active"},
    ).first()
    assert row is not None, (
        "subscription_status 'active' not found in DB. "
        "Run: cd backend && python migrations/scripts/seed_platform.py"
    )
    return db_session.exec(
        select(SubscriptionStatus).where(SubscriptionStatus.id == row.id)
    ).first()


class TestWebhookSubscriptionCreated:
    """Tests for handle_subscription_created webhook handler — core functionality."""

    def test_webhook_creates_subscription_row(
        self,
        db_session: Session,
        test_tenant,
        subscription_tier_starter,
        subscription_status_active,
    ):
        """Webhook: subscription row created with correct fields."""
        from services.stripe_subscriptions import handle_subscription_created

        test_tenant.stripe_customer_id = "cus_webhook_test"
        db_session.add(test_tenant)
        db_session.commit()

        stripe_event = {
            "data": {
                "object": {
                    "customer": "cus_webhook_test",
                    "id": "sub_webhook123",
                    "billing_cycle_anchor": 1700000000,
                    "current_period_end": 1702678000,
                    "items": {
                        "data": [
                            {
                                "price": {
                                    "id": "price_starter_test",
                                }
                            }
                        ]
                    },
                }
            }
        }

        handle_subscription_created(db_session, stripe_event)

        # Verify subscription row created
        sub_row = db_session.exec(
            select(Subscription).where(
                Subscription.psp_subscription_id == "sub_webhook123"
            )
        ).first()

        assert sub_row is not None
        assert sub_row.tenant_id == test_tenant.id
        assert sub_row.product_plan_code == "starter_monthly"
        assert sub_row.status_id == subscription_status_active.id
        assert sub_row.psp_customer_id == "cus_webhook_test"
        assert sub_row.is_active is True

    def test_webhook_tenant_tier_updated(
        self,
        db_session: Session,
        test_tenant,
        subscription_tier_starter,
        subscription_status_active,
    ):
        """Webhook: tenant.current_subscription_tier_id updated on conversion."""
        from services.stripe_subscriptions import handle_subscription_created

        test_tenant.stripe_customer_id = "cus_tier_test"
        db_session.add(test_tenant)
        db_session.commit()

        stripe_event = {
            "data": {
                "object": {
                    "customer": "cus_tier_test",
                    "id": "sub_tier123",
                    "billing_cycle_anchor": 1700000000,
                    "current_period_end": 1702678000,
                    "items": {
                        "data": [
                            {
                                "price": {
                                    "id": "price_starter_test",
                                }
                            }
                        ]
                    },
                }
            }
        }

        handle_subscription_created(db_session, stripe_event)

        # Verify tenant tier updated
        db_session.refresh(test_tenant)
        assert (
            test_tenant.current_subscription_tier_id
            == subscription_tier_starter.tier_id
        )
        assert test_tenant.trial_ends_at is None

    def test_webhook_idempotency_upserts_not_duplicates(
        self,
        db_session: Session,
        test_tenant,
        subscription_tier_starter,
        subscription_status_active,
    ):
        """Webhook: duplicate event → upsert, not duplicate row."""
        from services.stripe_subscriptions import handle_subscription_created

        test_tenant.stripe_customer_id = "cus_idem_test"
        db_session.add(test_tenant)
        db_session.commit()

        stripe_event = {
            "data": {
                "object": {
                    "customer": "cus_idem_test",
                    "id": "sub_idem123",
                    "billing_cycle_anchor": 1700000000,
                    "current_period_end": 1702678000,
                    "items": {
                        "data": [
                            {
                                "price": {
                                    "id": "price_starter_test",
                                }
                            }
                        ]
                    },
                }
            }
        }

        # First webhook call
        handle_subscription_created(db_session, stripe_event)

        # Count rows
        count_1 = db_session.exec(
            select(Subscription).where(
                Subscription.psp_subscription_id == "sub_idem123"
            )
        ).first()
        assert count_1 is not None

        # Duplicate webhook call
        handle_subscription_created(db_session, stripe_event)

        # Should still be exactly 1 row (upserted)
        count_2 = db_session.exec(
            select(Subscription).where(
                Subscription.psp_subscription_id == "sub_idem123"
            )
        ).all()
        assert len(count_2) == 1

    def test_webhook_requires_product_plan_code(
        self,
        db_session: Session,
        test_tenant,
        subscription_status_active,
    ):
        """Webhook: logs warning if tier lacks product_plan_code."""
        from services.stripe_subscriptions import handle_subscription_created

        # Create tier without product_plan_code
        tier_no_code = SubscriptionTier(
            tier_id=uuid.uuid4(),
            tier_name="incomplete_b19_test",
            display_label="Incomplete",
            annual_price_cents=9900,  # SD-3: renamed from monthly_price_cents
            monthly_price_cents=9900,  # SD-3: new M2M premium column
            is_trial=False,
            display_order=99,
            stripe_price_id_monthly="price_incomplete_test",  # SD-3: renamed from stripe_price_id
            product_plan_code=None,  # Missing!
            is_active=True,
            schedule_lanes=0,
        )
        db_session.add(tier_no_code)
        db_session.commit()

        test_tenant.stripe_customer_id = "cus_incomplete"
        db_session.add(test_tenant)
        db_session.commit()

        stripe_event = {
            "data": {
                "object": {
                    "customer": "cus_incomplete",
                    "id": "sub_incomplete123",
                    "billing_cycle_anchor": 1700000000,
                    "current_period_end": 1702678000,
                    "items": {
                        "data": [
                            {
                                "price": {
                                    "id": "price_incomplete_test",
                                }
                            }
                        ]
                    },
                }
            }
        }

        # Should log warning but not crash
        handle_subscription_created(db_session, stripe_event)

        # No subscription row created
        sub = db_session.exec(
            select(Subscription).where(
                Subscription.psp_subscription_id == "sub_incomplete123"
            )
        ).first()
        assert sub is None


class TestUsageLedgerFK:
    """Tests for UsageLedger.subscription_id FK to Subscription.id"""

    def test_usage_ledger_can_reference_subscription(
        self,
        db_session: Session,
        test_tenant,
        subscription_status_active,
        product_plans_seeded,
    ):
        """Integration: UsageLedger.subscription_id → Subscription.id (FIND-101 dependency)."""
        from app.models.billing import UsageLedger

        # Create subscription row
        sub = Subscription(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            product_plan_code="starter_monthly",
            status_id=subscription_status_active.id,
            psp_subscription_id="sub_fk_test",
            psp_customer_id="cus_fk_test",
            psp_provider="stripe",
            billing_interval="monthly",
            is_active=True,
        )
        db_session.add(sub)
        db_session.commit()

        # Create usage ledger row referencing subscription
        usage = UsageLedger(
            tenant_id=test_tenant.id,
            subscription_id=sub.id,  # FK to subscription.id
            product_feature_code="sms_messages",
            quantity=100.0,
            idempotency_key=f"usage_fk_test_{uuid.uuid4()}",
        )
        db_session.add(usage)
        db_session.commit()
        db_session.refresh(usage)

        assert usage.subscription_id == sub.id
