"""
SD-3: Verify subscription_tier billing schema changes.
- annual_price_cents column renamed from monthly_price_cents
- monthly_price_cents new column with correct values
- stripe_price_id_monthly renamed from stripe_price_id
- stripe_price_id_annual new column (nullable)
- teams_plan rename complete
- charter_plan product_plan_version price_cents = 0
"""

import pytest
from sqlmodel import select

pytestmark = [
    pytest.mark.domain_subscriptions_usage,
    pytest.mark.unit,
]


class TestSubscriptionTierBillingSchema:
    def test_annual_price_cents_column_exists_on_all_tiers(self, db_session):
        """annual_price_cents must exist and have correct values for all 4 tiers.

        C-B2: Charter annual_price_cents updated from 0 to 58800 ($49/mo x 12).
        """
        from app.models.subscription import SubscriptionTier

        tiers = db_session.exec(select(SubscriptionTier)).all()
        tier_map = {t.tier_name: t for t in tiers}

        assert tier_map["charter"].annual_price_cents == 58800  # C-B2: $588/yr
        assert tier_map["trial"].annual_price_cents == 0
        assert (
            tier_map["starter"].annual_price_cents == 58800
        )  # $588/year ($49/mo x 12)
        assert (
            tier_map["teams"].annual_price_cents == 178800
        )  # $1,788/year ($149/mo x 12)

    def test_monthly_price_cents_new_column_correct_values(self, db_session):
        """monthly_price_cents (month-to-month premium) must have correct values.

        C-B2: Charter monthly_price_cents updated from 0 to 4900 ($49/mo flat).
        """
        from app.models.subscription import SubscriptionTier

        tiers = db_session.exec(select(SubscriptionTier)).all()
        tier_map = {t.tier_name: t for t in tiers}

        assert tier_map["charter"].monthly_price_cents == 4900  # C-B2: $49/mo flat
        assert tier_map["trial"].monthly_price_cents == 0
        assert tier_map["starter"].monthly_price_cents == 5900
        assert tier_map["teams"].monthly_price_cents == 17900

    def test_stripe_price_id_monthly_field_exists(self, db_session):
        """stripe_price_id_monthly column must exist; test-mode IDs must be set."""
        from app.models.subscription import SubscriptionTier

        starter = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "starter")
        ).first()
        assert starter is not None
        assert starter.stripe_price_id_monthly is not None
        assert starter.stripe_price_id_monthly.startswith("price_")

    def test_stripe_price_id_annual_field_exists_nullable(self, db_session):
        """stripe_price_id_annual must exist as nullable (Tom populates later)."""
        from app.models.subscription import SubscriptionTier

        starter = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "starter")
        ).first()
        assert starter is not None
        # Column must exist on the model (even if NULL)
        assert hasattr(starter, "stripe_price_id_annual")
        # Annual price IDs are NULL until Tom creates them in Stripe Dashboard
        # (acceptable pre-GA)


class TestTeamsPlanRename:
    def test_teams_plan_code_exists(self, db_session):
        """product_plan must have code='teams_plan' (not 'teams')."""
        from sqlalchemy import text as sa_text

        result = db_session.exec(
            sa_text("SELECT code FROM public.product_plan WHERE code = 'teams_plan'")
        ).first()
        assert result is not None, "teams_plan not found — Migration 1 may not have run"

    def test_teams_code_does_not_exist(self, db_session):
        """Old product_plan code 'teams' must not exist after rename."""
        from sqlalchemy import text as sa_text

        result = db_session.exec(
            sa_text("SELECT code FROM public.product_plan WHERE code = 'teams'")
        ).first()
        assert result is None, (
            "Old 'teams' code still exists — rename migration may have failed"
        )

    def test_teams_plan_subscription_tier_linked(self, db_session):
        """subscription_tier 'teams' tier must reference product_plan_code='teams_plan'."""
        from app.models.subscription import SubscriptionTier

        teams_tier = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "teams")
        ).first()
        assert teams_tier is not None
        assert teams_tier.product_plan_code == "teams_plan"


class TestCharterPlanPriceFix:
    def test_charter_plan_version_price_cents_is_zero(self, db_session):
        """charter_plan product_plan_version.price_cents must be 0.

        The MKT-B11 migration incorrectly set this to 4900. Charter plan
        list price is $0 during the free cohort period. The $49/mo billing
        that activates at month 7 is a Stripe Subscription Schedule event
        (STRIPE-B1) — not a plan-price change.
        """
        from sqlalchemy import text as sa_text

        result = db_session.exec(
            sa_text("""
                SELECT price_cents FROM public.product_plan_version
                WHERE product_plan_code = 'charter_plan'
                LIMIT 1
            """)
        ).first()
        assert result is not None, "charter_plan product_plan_version row not found"
        assert result.price_cents == 0, (
            f"charter_plan price_cents should be 0, got {result.price_cents}. "
            "SD-3 Migration 2 may not have run or downgrade was applied."
        )

    def test_starter_plan_version_price_cents_correct(self, db_session):
        """starter_plan product_plan_version.price_cents must be 4900."""
        from sqlalchemy import text as sa_text

        result = db_session.exec(
            sa_text("""
                SELECT price_cents FROM public.product_plan_version
                WHERE product_plan_code = 'starter_plan'
                LIMIT 1
            """)
        ).first()
        assert result is not None
        assert result.price_cents == 4900
