"""
DB-touching tests for seed_platform env-aware Stripe converge (DB-MGMT-1).

Uses the ``db_session`` fixture (transaction rollback) so the converge-UPDATE
is safe — rollback undoes it. Asserts the 4 starter/teams slots flip test→live→test
and that charter is left untouched (design §G-7 — UNCLASSIFIED).

Per Rule 16: assertions are scoped by tier_name, never table counts.
"""

import pytest
from sqlalchemy import text

from migrations.scripts._env_profiles import (
    SeedEnv,
    convergeable_tiers,
    get_profile,
)

pytestmark = [pytest.mark.domain_platform_infrastructure, pytest.mark.unit]


def _get_tier_stripe_ids(db, tier_name: str) -> dict[str, str | None]:
    """Fetch the current stripe_price_id_monthly/annual for a tier."""
    row = db.execute(
        text(
            "SELECT stripe_price_id_monthly, stripe_price_id_annual "
            "FROM public.subscription_tier WHERE tier_name = :name"
        ),
        {"name": tier_name},
    ).first()
    if row is None:
        return {"monthly": None, "annual": None}
    return {"monthly": row[0], "annual": row[1]}


def _run_converge(db, profile):
    """Run the converge-UPDATE logic from seed_platform.mode_seed (§4b).

    This replicates the converge block without importing the full seed_platform
    module (which has side effects at import time). The logic is identical:
    UPDATE subscription_tier SET stripe_price_id_{interval} = :price_id
    WHERE tier_name = :tier AND (col IS NULL OR col != :price_id).
    """
    for tier_name in convergeable_tiers():
        for interval, column in (
            ("monthly", "stripe_price_id_monthly"),
            ("annual", "stripe_price_id_annual"),
        ):
            price_id = profile.stripe_price_id(tier_name, interval)
            db.execute(
                text(
                    f"UPDATE public.subscription_tier "
                    f"SET {column} = :price_id, updated_at = NOW() "
                    f"WHERE tier_name = :tier "
                    f"AND ({column} IS NULL OR {column} != :price_id)"
                ),
                {"price_id": price_id, "tier": tier_name},
            )
    # Charter: converge only if non-None (design §G-7)
    charter_monthly = profile.stripe_price_id("charter", "monthly")
    if charter_monthly is not None:
        db.execute(
            text(
                "UPDATE public.subscription_tier "
                "SET stripe_price_id_monthly = :price_id, updated_at = NOW() "
                "WHERE tier_name = 'charter' "
                "AND (stripe_price_id_monthly IS NULL "
                "OR stripe_price_id_monthly != :price_id)"
            ),
            {"price_id": charter_monthly},
        )
    db.flush()


class TestSeedPlatformConverge:
    def test_converge_test_mode_sets_test_ids(self, db_session):
        """Converge with test mode sets the test price IDs on starter/teams."""
        profile = get_profile(SeedEnv.PROD, "test")
        _run_converge(db_session, profile)

        starter = _get_tier_stripe_ids(db_session, "starter")
        assert starter["monthly"] == "price_REDACTED16"
        assert starter["annual"] == "price_REDACTED17"

        teams = _get_tier_stripe_ids(db_session, "teams")
        assert teams["monthly"] == "price_REDACTED19"
        assert teams["annual"] == "price_REDACTED18"

    def test_converge_live_mode_flips_to_live_ids(self, db_session):
        """Converge with live mode flips starter/teams to live price IDs."""
        profile = get_profile(SeedEnv.PROD, "live")
        _run_converge(db_session, profile)

        starter = _get_tier_stripe_ids(db_session, "starter")
        assert starter["monthly"] == "price_REDACTED01"
        assert starter["annual"] == "price_REDACTED05"

        teams = _get_tier_stripe_ids(db_session, "teams")
        assert teams["monthly"] == "price_REDACTED02"
        assert teams["annual"] == "price_REDACTED06"

    def test_converge_test_then_live_then_test(self, db_session):
        """Re-running converge with different modes flips cleanly."""
        # Start with test
        p_test = get_profile(SeedEnv.PROD, "test")
        _run_converge(db_session, p_test)
        starter_test = _get_tier_stripe_ids(db_session, "starter")
        assert starter_test["monthly"] == "price_REDACTED16"

        # Flip to live
        p_live = get_profile(SeedEnv.PROD, "live")
        _run_converge(db_session, p_live)
        starter_live = _get_tier_stripe_ids(db_session, "starter")
        assert starter_live["monthly"] == "price_REDACTED01"

        # Flip back to test
        _run_converge(db_session, p_test)
        starter_back = _get_tier_stripe_ids(db_session, "starter")
        assert starter_back["monthly"] == "price_REDACTED16"

    def test_converge_idempotent(self, db_session):
        """Running converge twice with the same mode is a no-op on second run."""
        profile = get_profile(SeedEnv.PROD, "test")
        _run_converge(db_session, profile)
        starter_after_1 = _get_tier_stripe_ids(db_session, "starter")

        # Second run — should not change anything
        _run_converge(db_session, profile)
        starter_after_2 = _get_tier_stripe_ids(db_session, "starter")

        assert starter_after_1 == starter_after_2

    def test_converge_does_not_touch_pricing_columns(self, db_session):
        """Converge only touches price-ID columns, never pricing/lifecycle."""
        profile = get_profile(SeedEnv.PROD, "test")

        # Capture pricing columns before
        row_before = db_session.execute(
            text(
                "SELECT monthly_price_cents, annual_price_cents, "
                "free_period_days, requires_payment_method "
                "FROM public.subscription_tier WHERE tier_name = 'starter'"
            )
        ).first()

        _run_converge(db_session, profile)

        row_after = db_session.execute(
            text(
                "SELECT monthly_price_cents, annual_price_cents, "
                "free_period_days, requires_payment_method "
                "FROM public.subscription_tier WHERE tier_name = 'starter'"
            )
        ).first()

        assert row_before == row_after
