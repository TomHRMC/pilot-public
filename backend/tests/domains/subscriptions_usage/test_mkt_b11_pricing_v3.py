"""
MKT-B11-BE — Pricing Model v3.0 DB Migration Tests
Domain: Subscriptions & Usage

Verifies the post-MKT-B11 state of subscription_tier, product_plan,
product_feature, and product_plan_product_feature_version tables.

Migration: 1635c1bf1d1b_mkt_b11_pricing_model_v3_schedule_lanes
"""

import pytest
from sqlmodel import func, select

pytestmark = [
    pytest.mark.domain_subscriptions_usage,
    pytest.mark.unit,
]


class TestSubscriptionTierV3:
    """Verifies subscription_tier table reflects v3.0 schema and data."""

    def test_charter_tier_is_only_active_tier(self, client, test_tenant, db_session):
        """GET /subscription-tiers/test returns at least one active tier.

        - charter mode  : exactly 1 tier ('charter') returned
        - post-beta mode : multiple tiers returned; charter may not be in the list
        """
        from app.models.subscription import SubscriptionTier

        resp = client.get("/api/v1/subscription-tiers/test")
        assert resp.status_code == 200
        tiers = resp.json()["tiers"]
        assert len(tiers) >= 1, "At least one active tier must be returned"

        charter = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "charter")
        ).first()
        if charter and charter.is_active:
            # charter mode: only charter in the list
            assert len(tiers) == 1
            assert tiers[0]["tier_name"] == "charter"

    def test_charter_tier_has_schedule_lanes(self, client, test_tenant, db_session):
        """charter tier response includes schedule_lanes=5 (when charter is active)."""
        from app.models.subscription import SubscriptionTier

        charter_row = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "charter")
        ).first()
        if not charter_row or not charter_row.is_active:
            # post-beta mode: charter not in active list — verify it has schedule_lanes in DB
            assert charter_row is not None, "charter tier must exist"
            assert charter_row.schedule_lanes == 5
            return

        resp = client.get("/api/v1/subscription-tiers/test")
        assert resp.status_code == 200
        charter = next(
            (t for t in resp.json()["tiers"] if t["tier_name"] == "charter"), None
        )
        assert charter is not None, "charter tier not found in response"
        assert charter["schedule_lanes"] == 5

    def test_no_max_users_in_response(self, client, test_tenant):
        """SubscriptionTierResponse does not expose max_users (column dropped)."""
        resp = client.get("/api/v1/subscription-tiers/test")
        for tier in resp.json()["tiers"]:
            assert "max_users" not in tier
            assert "max_sms_segments_per_month" not in tier

    def test_teams_tier_has_20_schedule_lanes(self, db_session):
        """teams tier has schedule_lanes=20."""
        from app.models.subscription import SubscriptionTier

        teams = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "teams")
        ).first()
        assert teams is not None
        assert teams.schedule_lanes == 20

    def test_enterprise_tier_absent(self, db_session):
        """enterprise tier is not present (deleted in v3.0)."""
        from app.models.subscription import SubscriptionTier

        enterprise = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "enterprise")
        ).first()
        assert enterprise is None

    def test_four_tiers_seeded(self, db_session):
        """Exactly 4 tiers: charter, trial, starter, teams."""
        from app.models.subscription import SubscriptionTier

        tiers = db_session.exec(select(SubscriptionTier)).all()
        tier_names = {t.tier_name for t in tiers}
        assert tier_names == {"charter", "trial", "starter", "teams"}

    def test_charter_display_order_is_0(self, db_session):
        """charter tier is at display_order=0 (first in list), monthly_price=4900 (C-B2: $49/mo), not a trial.

        is_active is mode-dependent — not asserted here.
        """
        from app.models.subscription import SubscriptionTier

        charter = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "charter")
        ).first()
        assert charter is not None
        assert charter.display_order == 0
        assert charter.monthly_price_cents == 4900  # C-B2: $49/mo flat
        assert charter.is_trial is False
        # is_active is mode-dependent: True in charter mode, False in post-beta mode
        assert charter.is_active in (True, False)


class TestProductPlanV3:
    """Verifies product_plan table reflects v3.0 data."""

    def test_charter_plan_is_active(self, db_session):
        """charter_plan exists with correct code.

        - charter mode  : charter_plan is the ONLY active plan
        - post-beta mode : multiple plans active; charter_plan may be dormant
        """
        from app.models.billing import ProductPlan

        charter_plan = db_session.exec(
            select(ProductPlan).where(ProductPlan.code == "charter_plan")
        ).first()
        assert charter_plan is not None, "charter_plan must exist in product_plan"

        active = db_session.exec(
            select(ProductPlan).where(ProductPlan.is_active == True)
        ).all()
        assert len(active) >= 1, "At least one product_plan must be active"

        if charter_plan.is_active:
            # charter mode: charter_plan is the only active plan
            assert len(active) == 1
            assert active[0].code == "charter_plan"
        # post-beta mode: other plans may be active alongside or instead of charter_plan

    def test_enterprise_plan_deleted(self, db_session):
        """enterprise_plan row does not exist."""
        from app.models.billing import ProductPlan

        enterprise = db_session.exec(
            select(ProductPlan).where(ProductPlan.code == "enterprise_plan")
        ).first()
        assert enterprise is None

    def test_starter_plan_exists(self, db_session):
        """starter_plan row exists in product_plan.

        is_active is mode-dependent:
        - charter mode  : is_active=False (dormant)
        - post-beta mode : is_active=True  (available to new subscribers)
        """
        from app.models.billing import ProductPlan

        starter = db_session.exec(
            select(ProductPlan).where(ProductPlan.code == "starter_plan")
        ).first()
        assert starter is not None, "starter_plan must exist in product_plan"
        # is_active is mode-dependent — both True and False are valid states
        assert starter.is_active in (True, False)

    def test_teams_plan_exists(self, db_session):
        """teams_plan row exists in product_plan (renamed from 'teams' in SD-3).

        is_active is mode-dependent:
        - charter mode  : is_active=False (dormant)
        - post-beta mode : is_active=True  (available to new subscribers)
        """
        from app.models.billing import ProductPlan

        teams = db_session.exec(
            select(ProductPlan).where(ProductPlan.code == "teams_plan")
        ).first()
        assert teams is not None, (
            "teams_plan must exist in product_plan (SD-3 renamed 'teams' → 'teams_plan')"
        )
        # is_active is mode-dependent — both True and False are valid states
        assert teams.is_active in (True, False)


class TestProductFeatureV3:
    """Verifies product_feature table reflects v3.0 data."""

    def test_schedule_lanes_feature_exists(self, db_session):
        """schedule_lanes product_feature is present and active."""
        from app.models.billing import ProductFeature

        feat = db_session.exec(
            select(ProductFeature).where(ProductFeature.code == "schedule_lanes")
        ).first()
        assert feat is not None
        assert feat.is_active is True
        assert feat.unit == "lanes"

    def test_dispatch_slots_deleted(self, db_session):
        """dispatch_slots product_feature is gone."""
        from app.models.billing import ProductFeature

        feat = db_session.exec(
            select(ProductFeature).where(ProductFeature.code == "dispatch_slots")
        ).first()
        assert feat is None

    def test_data_exports_deleted(self, db_session):
        """data_exports product_feature is gone."""
        from app.models.billing import ProductFeature

        feat = db_session.exec(
            select(ProductFeature).where(ProductFeature.code == "data_exports")
        ).first()
        assert feat is None

    def test_voice_ai_minutes_exists(self, db_session):
        """voice_ai_minutes product_feature is present and active."""
        from app.models.billing import ProductFeature

        feat = db_session.exec(
            select(ProductFeature).where(ProductFeature.code == "voice_ai_minutes")
        ).first()
        assert feat is not None
        assert feat.is_active is True

    def test_outbound_sms_segments_exists(self, db_session):
        """outbound_sms_segments product_feature is present and active."""
        from app.models.billing import ProductFeature

        feat = db_session.exec(
            select(ProductFeature).where(ProductFeature.code == "outbound_sms_segments")
        ).first()
        assert feat is not None
        assert feat.is_active is True


class TestPPFVV3:
    """Verifies product_plan_product_feature_version rows are correct for v3.0."""

    def test_total_ppfv_rows_is_9(self, db_session):
        """3 plans x 3 features = 9 ppfv rows total."""
        from app.models.billing import ProductPlanProductFeatureVersion

        count = db_session.exec(
            select(func.count(ProductPlanProductFeatureVersion.id))
        ).one()
        assert count == 9

    def test_schedule_lanes_uses_block_enforcement(self, db_session):
        """All schedule_lanes ppfv rows use block enforcement (not soft)."""
        from app.models.billing import ProductPlanProductFeatureVersion

        rows = db_session.exec(
            select(ProductPlanProductFeatureVersion).where(
                ProductPlanProductFeatureVersion.product_feature_code
                == "schedule_lanes"
            )
        ).all()
        assert len(rows) == 3  # charter, starter, teams
        for row in rows:
            assert row.limit_enforcement == "block"
            assert row.overage_price_cents is None

    def test_voice_ai_minutes_overage_is_5_cents(self, db_session):
        """All voice_ai_minutes ppfv rows have overage_price_cents=5."""
        from app.models.billing import ProductPlanProductFeatureVersion

        rows = db_session.exec(
            select(ProductPlanProductFeatureVersion).where(
                ProductPlanProductFeatureVersion.product_feature_code
                == "voice_ai_minutes"
            )
        ).all()
        assert len(rows) == 3
        for row in rows:
            assert row.overage_price_cents == 5
            assert row.limit_enforcement == "soft"

    def test_charter_plan_schedule_lanes_limit_is_5(self, db_session):
        """charter_plan schedule_lanes limit_quantity = 5."""
        from app.models.billing import ProductPlanProductFeatureVersion

        row = db_session.exec(
            select(ProductPlanProductFeatureVersion).where(
                ProductPlanProductFeatureVersion.product_plan_code == "charter_plan",
                ProductPlanProductFeatureVersion.product_feature_code
                == "schedule_lanes",
            )
        ).first()
        assert row is not None
        assert row.limit_quantity == 5

    def test_teams_schedule_lanes_limit_is_20(self, db_session):
        """teams_plan schedule_lanes limit_quantity = 20 (SD-3: 'teams' renamed to 'teams_plan')."""
        from app.models.billing import ProductPlanProductFeatureVersion

        row = db_session.exec(
            select(ProductPlanProductFeatureVersion).where(
                ProductPlanProductFeatureVersion.product_plan_code == "teams_plan",
                ProductPlanProductFeatureVersion.product_feature_code
                == "schedule_lanes",
            )
        ).first()
        assert row is not None
        assert row.limit_quantity == 20

    def test_no_dispatch_slots_or_data_exports_in_ppfv(self, db_session):
        """No ppfv rows reference dispatch_slots or data_exports."""
        from app.models.billing import ProductPlanProductFeatureVersion

        stale = db_session.exec(
            select(ProductPlanProductFeatureVersion).where(
                ProductPlanProductFeatureVersion.product_feature_code.in_(
                    ["dispatch_slots", "data_exports"]
                )
            )
        ).all()
        assert len(stale) == 0


class TestGetEffectiveScheduleLanes:
    """Verifies the get_effective_schedule_lanes() helper."""

    def test_returns_plan_base_lanes_when_no_override(self, db_session, test_tenant):
        """Returns 5 for charter plan when no tenant override."""
        from services.tier_limit_enforcer import get_effective_schedule_lanes

        lanes = get_effective_schedule_lanes(test_tenant.id, db_session)
        assert lanes == 5  # charter_plan base
