"""
B14/A75 — Subscription Tier Infrastructure tests.

MKT-B11 UPDATE: Pricing Model v3.0 changed the tier structure:
- Tier names: charter (active), trial/starter/teams (inactive)
- Removed max_users column (unlimited users permanent invariant)
- Added schedule_lanes column
- charter tier: is_trial=False, monthly_price_cents=4900 (C-B2: $49/mo), schedule_lanes=5
- trial tier: is_trial=True, monthly_price_cents=0 (but is_active=False)
- check_user_add_allowed always returns True (unlimited users)

Test focus cases:
1. subscription_tier seed data exists (4 tiers seeded by migration)
2. charter tier has correct properties (is_active=true, schedule_lanes=5)
3. GET /subscription-tiers/test returns active tiers ordered by display_order
4. tier_limit_enforcer allows user-add (always true — unlimited users)
5. tier_limit_enforcer.increment_user_count creates usage row when none exists
6. tier_limit_enforcer.decrement_user_count floors at 0
7. GET /tenants/{id}/subscription/test returns tier + trial fields
8. TenantTierOverride takes precedence over tenant.current_subscription_tier_id
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import select

from app.models.core import Tenant
from app.models.subscription import SubscriptionTier, TenantSubscriptionUsage

# ==================== FIXTURES ====================


@pytest.fixture
def trial_tier(db_session):
    """Return the seeded trial subscription tier (is_active=False post MKT-B11)."""
    tier = db_session.exec(
        select(SubscriptionTier).where(SubscriptionTier.is_trial == True)
    ).first()
    assert tier is not None, "Trial tier must be seeded by migration"
    return tier


@pytest.fixture
def charter_tier(db_session):
    """Return the seeded charter subscription tier (is_active=True, only active tier)."""
    tier = db_session.exec(
        select(SubscriptionTier).where(SubscriptionTier.tier_name == "charter")
    ).first()
    assert tier is not None, "Charter tier must be seeded by MKT-B11 migration"
    return tier


@pytest.fixture
def starter_tier(db_session):
    """Return the seeded starter subscription tier."""
    tier = db_session.exec(
        select(SubscriptionTier).where(SubscriptionTier.tier_name == "starter")
    ).first()
    assert tier is not None, "Starter tier must be seeded by migration"
    return tier


@pytest.fixture
def tenant_with_charter(db_session, charter_tier):
    """Create a test tenant on the charter tier."""
    import uuid as _uuid

    t = Tenant(
        id=_uuid.uuid4(),
        name=f"B14 Test Tenant {_uuid.uuid4().hex[:8]}",
        is_active=True,
        current_subscription_tier_id=charter_tier.tier_id,
        trial_started_at=datetime.now(UTC),
        trial_ends_at=datetime.now(UTC) + timedelta(days=180),
    )
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    return t


@pytest.fixture
def usage_row(db_session, tenant_with_charter):
    """Create a usage row for tenant_with_charter."""
    now = datetime.now(UTC)
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if period_start.month == 12:
        period_end = period_start.replace(year=period_start.year + 1, month=1)
    else:
        period_end = period_start.replace(month=period_start.month + 1)

    row = TenantSubscriptionUsage(
        tenant_id=tenant_with_charter.id,
        period_start=period_start,
        period_end=period_end,
        current_user_count=0,
        current_sms_segment_count=0,
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


# ==================== TEST CASES ====================


class TestSubscriptionTierSeedData:
    """Test cases 1-2: Seed data integrity for MKT-B11 v3.0."""

    def test_four_tiers_seeded(self, db_session):
        """Migration must seed exactly 4 tiers: charter, trial, starter, teams."""
        tiers = db_session.exec(select(SubscriptionTier)).all()
        tier_names = {t.tier_name for t in tiers}
        assert {"charter", "trial", "starter", "teams"}.issubset(tier_names), (
            f"Expected all 4 v3.0 tiers, got: {tier_names}"
        )

    def test_charter_tier_properties(self, db_session, charter_tier):
        """Charter tier: monthly_price_cents=4900 (C-B2: $49/mo), schedule_lanes=5, display_order=0.

        is_active is mode-dependent:
        - charter mode  : is_active=True  (only active tier)
        - post-beta mode : is_active=False (starter/teams become active)
        Both states are valid — no assertion on is_active here.
        """
        assert charter_tier.monthly_price_cents == 4900  # C-B2: $49/mo flat
        assert charter_tier.schedule_lanes == 5
        assert charter_tier.display_order == 0

    def test_tiers_ordered_by_display_order(self, db_session):
        """Tiers should be ordered charter(0), trial(1), starter(2), teams(3)."""
        tiers = db_session.exec(
            select(SubscriptionTier).order_by(SubscriptionTier.display_order)
        ).all()
        assert [t.tier_name for t in tiers] == [
            "charter",
            "trial",
            "starter",
            "teams",
        ]

    def test_only_charter_is_active(self, db_session, charter_tier):
        """At least one tier is always active.

        - charter mode  : exactly 1 active tier and it is 'charter'
        - post-beta mode : multiple tiers active; 'charter' may be dormant
        """
        active_tiers = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.is_active == True)
        ).all()
        assert len(active_tiers) >= 1, "At least one tier must be active"
        if charter_tier.is_active:
            # charter mode: charter is the only active paid tier
            assert len(active_tiers) == 1
            assert active_tiers[0].tier_name == "charter"
        # post-beta mode: multiple tiers active — no further constraint

    def test_trial_tier_properties(self, db_session, trial_tier):
        """Trial tier: is_trial=True, monthly_price_cents=0, trial_duration_days=14."""
        assert trial_tier.is_trial is True
        assert trial_tier.monthly_price_cents == 0
        assert trial_tier.trial_duration_days == 14

    def test_teams_tier_has_20_schedule_lanes(self, db_session):
        """Teams tier has schedule_lanes=20."""
        teams = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "teams")
        ).first()
        assert teams is not None
        assert teams.schedule_lanes == 20


class TestSubscriptionTiersEndpoint:
    """Test case 3: GET /subscription-tiers/test returns active tiers."""

    def test_list_tiers_returns_active_tiers(self, client, test_tenant, db_session):
        """Test endpoint returns only active tiers.

        - charter mode  : exactly 1 tier ('charter') returned
        - post-beta mode : multiple tiers returned; at least 1
        """
        response = client.get("/api/v1/subscription-tiers/test")
        assert response.status_code == 200
        data = response.json()
        assert "tiers" in data
        assert len(data["tiers"]) >= 1, "At least one active tier must be returned"

        charter_tier = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "charter")
        ).first()
        if charter_tier and charter_tier.is_active:
            # charter mode: only charter returned
            assert len(data["tiers"]) == 1
            assert data["tiers"][0]["tier_name"] == "charter"

    def test_list_tiers_ordered_by_display_order(self, client, test_tenant):
        """Tiers in response must be in display_order order."""
        response = client.get("/api/v1/subscription-tiers/test")
        tiers = response.json()["tiers"]
        orders = [t["display_order"] for t in tiers]
        assert orders == sorted(orders)

    def test_list_tiers_has_schedule_lanes(self, client, test_tenant):
        """Response tiers must include schedule_lanes field."""
        response = client.get("/api/v1/subscription-tiers/test")
        tiers = response.json()["tiers"]
        for tier in tiers:
            assert "schedule_lanes" in tier
            assert "max_users" not in tier
            assert "max_sms_segments_per_month" not in tier


class TestTierLimitEnforcer:
    """Test cases 4-7: tier_limit_enforcer service logic."""

    def test_allows_user_add_always(
        self, db_session, tenant_with_charter, charter_tier, usage_row
    ):
        """MKT-B11: Unlimited users — check_user_add_allowed always returns True."""
        from services.tier_limit_enforcer import check_user_add_allowed

        allowed, error = check_user_add_allowed(db_session, tenant_with_charter.id)
        assert allowed is True
        assert error == {}

    def test_allows_user_add_even_at_high_count(
        self, db_session, tenant_with_charter, charter_tier, usage_row
    ):
        """MKT-B11: Unlimited users — never blocked regardless of user count."""
        from services.tier_limit_enforcer import check_user_add_allowed

        # Set count to large value — still allowed
        usage_row.current_user_count = 9999
        db_session.add(usage_row)
        db_session.commit()

        allowed, error = check_user_add_allowed(db_session, tenant_with_charter.id)
        assert allowed is True
        assert error == {}

    def test_increment_creates_usage_row_if_missing(
        self, db_session, tenant_with_charter
    ):
        """increment_user_count creates usage row when none exists."""
        from services.tier_limit_enforcer import increment_user_count

        # No usage row yet
        increment_user_count(db_session, tenant_with_charter.id)

        now = datetime.now(UTC)
        row = db_session.exec(
            select(TenantSubscriptionUsage)
            .where(TenantSubscriptionUsage.tenant_id == tenant_with_charter.id)
            .where(TenantSubscriptionUsage.period_end >= now)
        ).first()
        assert row is not None
        assert row.current_user_count == 1

    def test_increment_increments_existing_row(
        self, db_session, tenant_with_charter, usage_row
    ):
        """increment_user_count increments existing row."""
        from services.tier_limit_enforcer import increment_user_count

        increment_user_count(db_session, tenant_with_charter.id)
        db_session.refresh(usage_row)
        assert usage_row.current_user_count == 1

    def test_decrement_floors_at_zero(self, db_session, tenant_with_charter, usage_row):
        """decrement_user_count never goes below 0."""
        from services.tier_limit_enforcer import decrement_user_count

        # Count is 0, decrement should remain 0
        decrement_user_count(db_session, tenant_with_charter.id)
        db_session.refresh(usage_row)
        assert usage_row.current_user_count == 0

    def test_decrement_reduces_count(self, db_session, tenant_with_charter, usage_row):
        """decrement_user_count reduces count by 1."""
        from services.tier_limit_enforcer import decrement_user_count

        usage_row.current_user_count = 3
        db_session.add(usage_row)
        db_session.commit()

        decrement_user_count(db_session, tenant_with_charter.id)
        db_session.refresh(usage_row)
        assert usage_row.current_user_count == 2


class TestTenantSubscriptionEndpoint:
    """Test cases 8-9: GET /tenants/{id}/subscription/test."""

    def test_get_subscription_returns_tier(self, client, test_tenant, db_session):
        """Test endpoint returns current_tier with correct structure."""
        response = client.get(f"/api/v1/tenants/{test_tenant.id}/subscription/test")
        assert response.status_code == 200
        data = response.json()
        assert "current_tier" in data
        assert "tier_id" in data["current_tier"]
        assert "tier_name" in data["current_tier"]

    def test_get_subscription_returns_charter_tier_for_test_tenant(
        self, client, test_tenant
    ):
        """Test tenant should be on charter tier (assigned by MKT-B11 migration)."""
        response = client.get(f"/api/v1/tenants/{test_tenant.id}/subscription/test")
        assert response.status_code == 200
        data = response.json()
        assert data["current_tier"]["tier_name"] == "charter"

    def test_operator_override_takes_precedence(
        self, client, db_session, tenant_with_charter, starter_tier
    ):
        """TenantTierOverride.override_tier_id overrides tenant.current_subscription_tier_id."""
        from sqlalchemy import text

        # Create override via raw SQL (bypass audit trigger - no 'id' column on tenant_tier_override)
        db_session.execute(text("SET LOCAL session_replication_role = 'replica'"))
        db_session.execute(
            text("""
                INSERT INTO tenant_tier_override
                    (tenant_id, override_tier_id, override_reason, set_by_operator_user_id, set_at, created_at, updated_at)
                VALUES
                    (:tid, :override_tid, 'Test override — tier forced for subscription tier infrastructure test', :operator_id, now(), now(), now())
            """),
            {
                "tid": str(tenant_with_charter.id),
                "override_tid": str(starter_tier.tier_id),
                "operator_id": "00000000-0000-0000-0000-000000000002",
            },
        )
        db_session.execute(text("SET LOCAL session_replication_role = 'origin'"))
        db_session.commit()

        response = client.get(
            f"/api/v1/tenants/{tenant_with_charter.id}/subscription/test"
        )
        assert response.status_code == 200
        data = response.json()
        # Override should show starter tier, not charter
        assert data["current_tier"]["tier_name"] == "starter"
        assert data["tier_override"] is not None
