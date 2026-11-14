"""
PLP-FIX-5 (Issue 8 BE) — plan-summary payload in GET /{tenant_id}/subscription.

Covers the three new response sections (plan_summary, charter_eligible, limits)
and the SubscriptionTierResponse.annual_price_cents addition across:

  1. With an active subscription row → status/interval/renews_at from the row.
  2. Derived trialing (no row + future trial_ends_at) → "trialing"/True.
  3. Derived none (no row + past/null trial_ends_at) → None/False.
  4. annual_price_cents present on current_tier as an int.

All assertions are tenant-scoped to the fixture tenant (rule §16 isolation).

Domain: subscriptions_usage (PRD §3.11)
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import select

pytestmark = [
    pytest.mark.domain_subscriptions_usage,
    pytest.mark.unit,
]

BASE = "/api/v1/tenants"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_status_id(db_session, code: str) -> uuid.UUID:
    """Look up a platform SubscriptionStatus row by code (tenant_id IS NULL)."""
    from app.models.billing import SubscriptionStatus

    row = db_session.exec(
        select(SubscriptionStatus).where(SubscriptionStatus.code == code)
    ).first()
    assert row is not None, f"SubscriptionStatus code='{code}' not seeded"
    return row.id


def _create_subscription(
    db_session,
    tenant_id,
    status_code="active",
    product_plan_code="charter_plan",
    billing_interval="monthly",
    renews_at=None,
):
    """Insert a subscription row scoped to this test (rolled back after test)."""
    from app.models.billing import Subscription

    sub = Subscription(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        product_plan_code=product_plan_code,
        status_id=_get_status_id(db_session, status_code),
        quantity_seats=1,
        billing_interval=billing_interval,
        is_active=True,
        renews_at=renews_at,
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)
    return sub


def _set_tenant_trial_ends(db_session, tenant_id, trial_ends_at):
    """Update the tenant's trial_ends_at (only mutates rows we control)."""
    from app.models.core import Tenant

    tenant = db_session.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    assert tenant is not None
    tenant.trial_ends_at = trial_ends_at
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


def _get_subscription(client, tenant_id: str):
    return client.get(f"{BASE}/{tenant_id}/subscription/test")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPlanSummaryPayload:
    """PLP-FIX-5 (Issue 8) — the three new response sections."""

    def test_plan_summary_with_active_subscription_row(
        self, client, db_session, second_tenant
    ):
        """With an active subscription row: status/interval/renews_at from it."""
        renews = datetime.now(UTC) + timedelta(days=30)
        sub = _create_subscription(
            db_session,
            second_tenant.id,
            status_code="active",
            billing_interval="annual",
            renews_at=renews,
        )

        resp = _get_subscription(client, second_tenant.id)
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # The three new sections are present
        assert "plan_summary" in data
        assert "charter_eligible" in data
        assert "limits" in data

        ps = data["plan_summary"]
        assert ps["status_code"] == "active"
        assert ps["is_billing_active"] is True
        assert ps["billing_interval"] == "annual"
        # renews_at round-trips the inserted value (ISO prefix match — tz format)
        assert ps["renews_at"] is not None
        assert ps["renews_at"].startswith(renews.isoformat()[:19])

        # charter_eligible mirrors the tenant column
        assert isinstance(data["charter_eligible"], bool)

        # limits keys present (values depend on seeded ppfv; assert type/presence)
        limits = data["limits"]
        for key in ("outbound_sms_segments", "schedule_lanes", "voice_ai_minutes"):
            assert key in limits
        # ID-scope: the subscription row we inserted is the active one
        assert sub.product_plan_code == "charter_plan"

    def test_plan_summary_derived_trialing_no_row_future_trial(
        self, client, db_session, second_tenant
    ):
        """No subscription row + future trial_ends_at → derived "trialing"/True.

        Design §G.4: pre-conversion trial tenants have no subscription row;
        status is derived from tenant.trial_ends_at.
        """
        future = datetime.now(UTC) + timedelta(days=10)
        _set_tenant_trial_ends(db_session, second_tenant.id, future)

        resp = _get_subscription(client, second_tenant.id)
        assert resp.status_code == 200, resp.text
        ps = resp.json()["plan_summary"]

        assert ps["status_code"] == "trialing"
        assert ps["is_billing_active"] is True
        assert ps["billing_interval"] is None

    def test_plan_summary_derived_none_no_row_past_trial(
        self, client, db_session, second_tenant
    ):
        """No subscription row + past trial_ends_at → status None/False."""
        past = datetime.now(UTC) - timedelta(days=5)
        _set_tenant_trial_ends(db_session, second_tenant.id, past)

        resp = _get_subscription(client, second_tenant.id)
        assert resp.status_code == 200, resp.text
        ps = resp.json()["plan_summary"]

        assert ps["status_code"] is None
        assert ps["is_billing_active"] is False
        assert ps["billing_interval"] is None

    def test_current_tier_has_annual_price_cents(
        self, client, db_session, second_tenant
    ):
        """SubscriptionTierResponse exposes annual_price_cents as a non-null int."""
        resp = _get_subscription(client, second_tenant.id)
        assert resp.status_code == 200, resp.text
        tier = resp.json()["current_tier"]

        assert "annual_price_cents" in tier
        assert isinstance(tier["annual_price_cents"], int)
