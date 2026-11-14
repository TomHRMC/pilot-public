"""
PLP-FIX-1 — SMS Rollover Overage-Write Code Regression Test
=============================================================
Domain: notifications_comms (PRD §3.7)

Verifies that the SMS quota rollover task's overage-write path uses the
correct live feature code ``outbound_sms_segments`` (not the stale pre-SD-07
``sms_segments``). The stale code would FK-violate against
``product_feature.code`` (which holds ``outbound_sms_segments``) — the path
never succeeded before this fix (zero ``sms_segments`` rows in ``usage_ledger``,
MCP-verified 2026-08-30).

Test:
  1. Overage write uses ``outbound_sms_segments`` — sets up a tenant with an
     active phone, a closing quota period with overage, and an active
     subscription; runs ``_rollover_impl``; asserts the inserted
     ``UsageLedger`` row has ``product_feature_code == "outbound_sms_segments"``
     and the insert did not raise.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import select

from app.models.billing import Subscription, UsageLedger
from app.models.sms import SmsQuotaPeriod, TenantPhoneNumber

pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]


def _get_active_status_id(db_session) -> uuid.UUID:
    """Look up the platform 'active' SubscriptionStatus row (tenant_id IS NULL)."""
    from app.models.billing import SubscriptionStatus

    row = db_session.exec(
        select(SubscriptionStatus).where(
            SubscriptionStatus.code == "active",
            SubscriptionStatus.tenant_id.is_(None),
        )
    ).first()
    assert row is not None, "Platform 'active' SubscriptionStatus not seeded"
    return row.id


@pytest.mark.skip_mock_entitlement_allowed
class TestRolloverOverageCode:
    """PLP-FIX-1: rollover overage-write must use ``outbound_sms_segments``."""

    def test_overage_write_uses_live_feature_code(self, db_session, second_tenant):
        """The usage_ledger row inserted by _rollover_impl uses outbound_sms_segments.

        Before PLP-FIX-1 the rollover task wrote ``product_feature_code='sms_segments'``
        which FK-violated (no such row in product_feature). The fix changed it to
        ``outbound_sms_segments`` (the SD-07 rename target, seeded + ppfv-backed).
        """
        from tasks.rollover_sms_quota_periods import _rollover_impl

        tenant_id = second_tenant.id

        # 1. Active subscription (charter_plan has outbound_sms_segments ppfv with
        #    overage_price_cents=5, enforcement=soft — seeded by seed_platform.py)
        active_status_id = _get_active_status_id(db_session)
        subscription = Subscription(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            product_plan_code="charter_plan",
            status_id=active_status_id,
            quantity_seats=1,
            billing_interval="monthly",
            is_active=True,
        )
        db_session.add(subscription)

        # 1b. Tenant override for outbound_sms_segments overage rate — the rollover
        #     task calls resolve_overage_rate(db, tenant_id, feature) without
        #     plan_code, so Tier 1 (override) must succeed. This is a pre-existing
        #     plumbing gap (the stale code masked it via FK violation first).
        from app.models.billing import TenantProductFeatureOverride

        override = TenantProductFeatureOverride(
            tenant_id=tenant_id,
            product_feature_code="outbound_sms_segments",
            enabled=True,
            overage_price_cents=5,
            overage_cap_per_period=None,
        )
        db_session.add(override)

        # 2. Active phone number (triggers the rollover loop for this tenant)
        phone = TenantPhoneNumber(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            phone_number=f"+1512555{uuid.uuid4().hex[:4]}",
            area_code="512",
            carrier="telnyx",
            status="active",
            provisioned_at=datetime.now(UTC),
        )
        db_session.add(phone)

        # 3. Quota period ending within 24 hours, with overage > 0, soft cap
        #    overage_segments is a GENERATED column (GREATEST(0, used - included))
        #    so we set used > included and let the DB compute it.
        now = datetime.now(UTC)
        period = SmsQuotaPeriod(
            tenant_id=tenant_id,
            period_start=now - timedelta(days=29),
            period_end=now + timedelta(hours=12),  # within 24h → triggers rollover
            included_segments=100,
            used_segments=150,  # → overage_segments = GREATEST(0, 150-100) = 50
            cap_policy="soft",
        )
        db_session.add(period)
        db_session.commit()
        db_session.refresh(subscription)
        db_session.refresh(phone)
        db_session.refresh(period)

        # 4. Run the rollover impl
        result = _rollover_impl(db_session)

        # 5. Assert the usage_ledger row was inserted with the correct feature code
        #    (scoped to this tenant + subscription — never total table counts)
        ledger_row = db_session.exec(
            select(UsageLedger).where(
                UsageLedger.tenant_id == tenant_id,
                UsageLedger.subscription_id == subscription.id,
            )
        ).first()

        assert ledger_row is not None, (
            "No usage_ledger row inserted — overage-write path did not fire. "
            f"Rollover result: {result}"
        )
        assert ledger_row.product_feature_code == "outbound_sms_segments", (
            f"Expected 'outbound_sms_segments', got "
            f"'{ledger_row.product_feature_code}' — stale code not fixed!"
        )
        assert ledger_row.quantity == 50, (
            f"Expected quantity=50 (overage_segments), got {ledger_row.quantity}"
        )
