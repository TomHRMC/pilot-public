"""
Integration Verification: Feature Entitlement Decision Tree (Task 1-D-4)

PLP-FIX-1 (2026-08-30, Option B): rewritten from a route-level POST /api/v1/quotes
402 test to a service-level ``check_entitlement()`` decision-tree test. The quotes
route no longer carries a feature gate (quotes are unlimited on every plan per
PRD §3.11 — the ``quotes_per_month`` wiring was a phantom gate, removed in
PLP-FIX-1). Framework coverage is preserved by exercising the real entitlement
service against a self-seeded synthetic feature + plan + ppfv + usage rows.

Key scenarios (full decision tree):
  1. used_quantity == limit  → ``is_allowed is False``, ``reason == "usage_limit_exceeded"``
  2. used_quantity < limit   → ``is_allowed is True``,  ``reason == "within_plan_limit"``
  3. no active subscription  → ``is_allowed is False``, ``reason == "no_active_subscription"``
  4. feature not in plan     → ``is_allowed is False``, ``reason == "feature_not_in_plan"``
  5. unlimited plan (NULL limit) → ``is_allowed is True``, ``reason == "plan_unlimited"``
  6. tenant override enabled + custom limit, under limit → allowed
  7. tenant override disabled → blocked

Seeding approach:
  - Rows are inserted via SQLAlchemy text() within the db_session transaction.
  - The db_session rollback fixture auto-rolls-back after each test — no persistent data.
  - All assertions are scoped to the synthetic feature code inserted by the test
    (never total table counts — Rule 16).
"""

from __future__ import annotations

import uuid
from calendar import monthrange
from datetime import date

import pytest
from sqlalchemy import text

# ── Mark ──────────────────────────────────────────────────────────────────────
pytestmark = [pytest.mark.integration]


# ── Constants ─────────────────────────────────────────────────────────────────
PLAN_CODE = "mvp_entitlement_test"
FEATURE_CODE = "synthetic_metered_feature"
LIMIT = 5


# ── Helpers ───────────────────────────────────────────────────────────────────


def _period_dates() -> tuple[date, date]:
    """Return (period_start, period_end) for the current calendar month."""
    today = date.today()
    period_start = today.replace(day=1)
    _, last_day = monthrange(today.year, today.month)
    period_end = today.replace(day=last_day)
    return period_start, period_end


def _get_active_status_id(db_session) -> uuid.UUID:
    """Look up the platform 'active' SubscriptionStatus row (tenant_id IS NULL)."""
    from app.models.billing import SubscriptionStatus

    row = db_session.exec(
        # SubscriptionStatus has tenant_id; platform rows have tenant_id IS NULL
        __import__("sqlmodel")
        .select(SubscriptionStatus)
        .where(
            SubscriptionStatus.code == "active",
            SubscriptionStatus.tenant_id.is_(None),
        )
    ).first()
    assert row is not None, "Platform 'active' SubscriptionStatus not seeded"
    return row.id


def _seed_billing_rows(
    db_session,
    tenant_id: uuid.UUID,
    used_quantity: int,
    limit_quantity: int | None = LIMIT,
    feature_code: str = FEATURE_CODE,
) -> uuid.UUID:
    """
    Insert the minimum billing rows for entitlement enforcement and return
    the subscription_id.

    All inserts use ON CONFLICT DO NOTHING so repeated runs are safe.
    Returns the subscription UUID seeded.
    """
    subscription_id = uuid.uuid4()
    active_status_id = _get_active_status_id(db_session)
    period_start, period_end = _period_dates()

    # product_feature (synthetic — scoped to this test, never referenced by app code)
    db_session.execute(
        text("""
            INSERT INTO product_feature (code, name, unit, is_active, created_at, updated_at)
            VALUES (:code, 'Synthetic Metered Feature', 'count', TRUE, NOW(), NOW())
            ON CONFLICT (code) DO NOTHING
        """),
        {"code": feature_code},
    )

    # product_plan (synthetic)
    db_session.execute(
        text("""
            INSERT INTO product_plan (code, name, is_active, created_at, updated_at)
            VALUES (:code, 'Entitlement Test Plan', TRUE, NOW(), NOW())
            ON CONFLICT (code) DO NOTHING
        """),
        {"code": PLAN_CODE},
    )

    # subscription
    db_session.execute(
        text("""
            INSERT INTO subscription
                (id, tenant_id, product_plan_code, status_id,
                 quantity_seats, billing_interval, started_at,
                 is_active, created_at, updated_at)
            VALUES
                (:id, :tenant_id, :plan_code, :status_id,
                 1, 'monthly', NOW(), TRUE, NOW(), NOW())
            ON CONFLICT DO NOTHING
        """),
        {
            "id": str(subscription_id),
            "tenant_id": str(tenant_id),
            "plan_code": PLAN_CODE,
            "status_id": str(active_status_id),
        },
    )

    # product_plan_product_feature_version — infinite TSTZRANGE
    # NOTE: :limit is a reserved keyword in some SQL parsers — use :qty instead
    db_session.execute(
        text("""
            INSERT INTO product_plan_product_feature_version
                (product_plan_code, product_feature_code, limit_quantity,
                 included_quantity, valid_period, limit_enforcement, created_at)
            VALUES
                (:plan, :feature, :qty, :qty,
                 tstzrange('-infinity', 'infinity', '[]'), 'block', NOW())
            ON CONFLICT DO NOTHING
        """),
        {"plan": PLAN_CODE, "feature": feature_code, "qty": limit_quantity},
    )

    # subscription_usage (only when a limit exists — unlimited plans skip usage)
    if limit_quantity is not None:
        db_session.execute(
            text("""
                INSERT INTO subscription_usage
                    (tenant_id, subscription_id, product_feature_code,
                     period_start, period_end, used_quantity, created_at, updated_at)
                VALUES
                    (:tenant_id, :sub_id, :feature,
                     :period_start, :period_end, :used, NOW(), NOW())
                ON CONFLICT (subscription_id, product_feature_code, period_start, period_end)
                DO UPDATE SET used_quantity = :used, updated_at = NOW()
            """),
            {
                "tenant_id": str(tenant_id),
                "sub_id": str(subscription_id),
                "feature": feature_code,
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "used": used_quantity,
            },
        )

    # Flush so rows are visible in the same connection/transaction
    db_session.flush()
    return subscription_id


def _seed_override(
    db_session,
    tenant_id: uuid.UUID,
    enabled: bool = True,
    limit_quantity: int | None = None,
) -> uuid.UUID:
    """Insert a tenant_product_feature_override row and return its id."""
    override_id = uuid.uuid4()
    db_session.execute(
        text("""
            INSERT INTO tenant_product_feature_override
                (id, tenant_id, product_feature_code, enabled, limit_quantity,
                 created_at, updated_at)
            VALUES
                (:id, :tenant_id, :feature, :enabled, :limit_qty, NOW(), NOW())
            ON CONFLICT DO NOTHING
        """),
        {
            "id": str(override_id),
            "tenant_id": str(tenant_id),
            "feature": FEATURE_CODE,
            "enabled": enabled,
            "limit_qty": limit_quantity,
        },
    )
    db_session.flush()
    return override_id


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestEntitlementDecisionTree:
    """
    Service-level verification of the ``check_entitlement()`` decision tree
    against self-seeded synthetic billing rows.

    PLP-FIX-1: replaces the prior route-level POST /api/v1/quotes 402 test
    (the quotes route is now de-gated — quotes are unlimited on every plan).
    """

    @pytest.mark.skip_mock_entitlement_allowed
    def test_blocked_when_quota_exhausted(self, db_session, second_tenant):
        """used_quantity == limit → is_allowed False, reason usage_limit_exceeded."""
        from services.entitlement_service import check_entitlement

        _seed_billing_rows(db_session, second_tenant.id, used_quantity=LIMIT)

        result = check_entitlement(second_tenant.id, FEATURE_CODE, db_session)

        assert result.is_allowed is False
        assert result.reason == "usage_limit_exceeded"
        assert result.limit == LIMIT
        assert result.used == LIMIT

    @pytest.mark.skip_mock_entitlement_allowed
    def test_allowed_when_under_quota(self, db_session, second_tenant):
        """used_quantity < limit → is_allowed True, reason within_plan_limit."""
        from services.entitlement_service import check_entitlement

        _seed_billing_rows(db_session, second_tenant.id, used_quantity=LIMIT - 1)

        result = check_entitlement(second_tenant.id, FEATURE_CODE, db_session)

        assert result.is_allowed is True
        assert result.reason == "within_plan_limit"
        assert result.limit == LIMIT
        assert result.used == LIMIT - 1

    @pytest.mark.skip_mock_entitlement_allowed
    def test_blocked_when_no_active_subscription(self, db_session, second_tenant):
        """No subscription row → is_allowed False, reason no_active_subscription."""
        from services.entitlement_service import check_entitlement

        # Seed the feature + plan + ppfv but NO subscription
        db_session.execute(
            text("""
                INSERT INTO product_feature (code, name, unit, is_active, created_at, updated_at)
                VALUES (:code, 'Synthetic Metered Feature', 'count', TRUE, NOW(), NOW())
                ON CONFLICT (code) DO NOTHING
            """),
            {"code": FEATURE_CODE},
        )
        db_session.execute(
            text("""
                INSERT INTO product_plan (code, name, is_active, created_at, updated_at)
                VALUES (:code, 'Entitlement Test Plan', TRUE, NOW(), NOW())
                ON CONFLICT (code) DO NOTHING
            """),
            {"code": PLAN_CODE},
        )
        db_session.execute(
            text("""
                INSERT INTO product_plan_product_feature_version
                    (product_plan_code, product_feature_code, limit_quantity,
                     included_quantity, valid_period, limit_enforcement, created_at)
                VALUES
                    (:plan, :feature, :qty, :qty,
                     tstzrange('-infinity', 'infinity', '[]'), 'block', NOW())
                ON CONFLICT DO NOTHING
            """),
            {"plan": PLAN_CODE, "feature": FEATURE_CODE, "qty": LIMIT},
        )
        db_session.flush()

        result = check_entitlement(second_tenant.id, FEATURE_CODE, db_session)

        assert result.is_allowed is False
        assert result.reason == "no_active_subscription"

    @pytest.mark.skip_mock_entitlement_allowed
    def test_blocked_when_feature_not_in_plan(self, db_session, second_tenant):
        """Subscription exists but no ppfv row for the feature → feature_not_in_plan."""
        from services.entitlement_service import check_entitlement

        # Seed a subscription but NO ppfv row for the synthetic feature
        active_status_id = _get_active_status_id(db_session)
        subscription_id = uuid.uuid4()
        db_session.execute(
            text("""
                INSERT INTO subscription
                    (id, tenant_id, product_plan_code, status_id,
                     quantity_seats, billing_interval, started_at,
                     is_active, created_at, updated_at)
                VALUES
                    (:id, :tenant_id, :plan_code, :status_id,
                     1, 'monthly', NOW(), TRUE, NOW(), NOW())
                ON CONFLICT DO NOTHING
            """),
            {
                "id": str(subscription_id),
                "tenant_id": str(second_tenant.id),
                "plan_code": PLAN_CODE,
                "status_id": str(active_status_id),
            },
        )
        # Seed the plan but NOT the ppfv row for this feature
        db_session.execute(
            text("""
                INSERT INTO product_plan (code, name, is_active, created_at, updated_at)
                VALUES (:code, 'Entitlement Test Plan', TRUE, NOW(), NOW())
                ON CONFLICT (code) DO NOTHING
            """),
            {"code": PLAN_CODE},
        )
        db_session.flush()

        result = check_entitlement(second_tenant.id, FEATURE_CODE, db_session)

        assert result.is_allowed is False
        assert result.reason == "feature_not_in_plan"

    @pytest.mark.skip_mock_entitlement_allowed
    def test_allowed_when_plan_unlimited(self, db_session, second_tenant):
        """NULL limit_quantity → is_allowed True, reason plan_unlimited."""
        from services.entitlement_service import check_entitlement

        _seed_billing_rows(
            db_session, second_tenant.id, used_quantity=0, limit_quantity=None
        )

        result = check_entitlement(second_tenant.id, FEATURE_CODE, db_session)

        assert result.is_allowed is True
        assert result.reason == "plan_unlimited"
        assert result.limit is None

    @pytest.mark.skip_mock_entitlement_allowed
    def test_override_enabled_grants_access(self, db_session, second_tenant):
        """Override enabled with a custom limit, under limit → allowed."""
        from services.entitlement_service import check_entitlement

        # Seed base billing rows (plan limit = 5, used = 5 → would block)
        _seed_billing_rows(db_session, second_tenant.id, used_quantity=LIMIT)
        # Override with a higher limit
        _seed_override(db_session, second_tenant.id, enabled=True, limit_quantity=100)

        result = check_entitlement(second_tenant.id, FEATURE_CODE, db_session)

        assert result.is_allowed is True
        assert result.reason == "override_limit_ok"
        assert result.limit == 100

    @pytest.mark.skip_mock_entitlement_allowed
    def test_override_disabled_blocks_access(self, db_session, second_tenant):
        """Override enabled=False → blocked immediately, reason feature_disabled_by_override."""
        from services.entitlement_service import check_entitlement

        _seed_billing_rows(db_session, second_tenant.id, used_quantity=0)
        _seed_override(db_session, second_tenant.id, enabled=False)

        result = check_entitlement(second_tenant.id, FEATURE_CODE, db_session)

        assert result.is_allowed is False
        assert result.reason == "feature_disabled_by_override"
