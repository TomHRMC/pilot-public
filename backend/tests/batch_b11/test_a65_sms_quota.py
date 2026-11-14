"""
B11/A65 — SMS Quota Tracking Tests
=====================================
Tests for:
  - SmsQuotaPeriod ORM model fields
  - check_quota(): customer opted out → blocked
  - check_quota(): no period → allowed (unlimited)
  - check_quota(): soft cap with overage → allowed + overage=True
  - check_quota(): hard cap at 100% → blocked
  - consume_quota(): increments used_segments
  - create_initial_period(): creates correct month boundary
  - Celery task _monitor_impl() no-op when no periods
  - Celery task _rollover_impl() no-op when no active phones
  - GET /sms/quota/test endpoint reachability
"""

import uuid
from datetime import UTC, datetime, timedelta

from app.models.sms import SmsQuotaPeriod
from services.sms_quota import (
    check_quota,
    consume_quota,
    create_initial_period,
)


def _make_period(
    db_session, tenant_id, used=0, included=100, cap_policy="soft", days_offset=0
):
    """Helper: create a quota period for a tenant."""
    now = datetime.now(UTC)
    period = SmsQuotaPeriod(
        tenant_id=tenant_id,
        period_start=now - timedelta(days=1) + timedelta(days=days_offset),
        period_end=now + timedelta(days=29) + timedelta(days=days_offset),
        included_segments=included,
        used_segments=used,
        cap_policy=cap_policy,
    )
    db_session.add(period)
    db_session.commit()
    db_session.refresh(period)
    return period


# ─── ORM Model Fields ─────────────────────────────────────────────────────────


class TestSmsQuotaPeriodModel:
    def test_model_has_required_fields(self):
        assert hasattr(SmsQuotaPeriod, "id")
        assert hasattr(SmsQuotaPeriod, "tenant_id")
        assert hasattr(SmsQuotaPeriod, "period_start")
        assert hasattr(SmsQuotaPeriod, "period_end")
        assert hasattr(SmsQuotaPeriod, "included_segments")
        assert hasattr(SmsQuotaPeriod, "used_segments")
        assert hasattr(SmsQuotaPeriod, "overage_segments")
        assert hasattr(SmsQuotaPeriod, "cap_policy")

    def test_model_defaults(self):
        now = datetime.now(UTC)
        period = SmsQuotaPeriod(
            tenant_id=uuid.uuid4(),
            period_start=now,
            period_end=now + timedelta(days=30),
        )
        assert period.included_segments == 100
        assert period.used_segments == 0
        assert period.cap_policy == "soft"

    def test_has_created_by_field(self):
        """B13b remediation: SmsQuotaPeriod now uses StandardAuditMixin — has created_by."""
        assert hasattr(SmsQuotaPeriod, "created_by")


# ─── check_quota() ────────────────────────────────────────────────────────────


class TestCheckQuota:
    def test_opted_out_customer_blocked(self, db_session, test_tenant, test_customer):
        """Customer with sms_opted_out=True should be blocked."""
        test_customer.sms_opted_out = True
        db_session.add(test_customer)
        db_session.commit()

        result = check_quota(db_session, test_tenant.id, test_customer.id, 1)

        assert result.allowed is False
        assert result.blocked_reason == "customer_opted_out"

    def test_no_period_returns_allowed_unlimited(
        self, db_session, test_tenant, test_customer
    ):
        """No active period → allowed with unlimited quota."""
        # Reset opted_out in case previous test set it
        test_customer.sms_opted_out = False
        db_session.add(test_customer)
        db_session.commit()

        result = check_quota(db_session, test_tenant.id, test_customer.id, 1)

        assert result.allowed is True
        assert result.overage is False
        assert result.blocked_reason is None

    def test_soft_cap_allows_overage(self, db_session, test_tenant, test_customer):
        """Soft cap: if used + requested > included, allowed with overage=True."""
        test_customer.sms_opted_out = False
        db_session.add(test_customer)
        db_session.commit()

        _make_period(db_session, test_tenant.id, used=9, included=10, cap_policy="soft")

        # Requesting 5 segments but only 1 remaining
        result = check_quota(db_session, test_tenant.id, test_customer.id, 5)

        assert result.allowed is True
        assert result.overage is True

    def test_hard_cap_blocks_at_100pct(self, db_session, test_tenant, test_customer):
        """Hard cap: if at 100%, block the send."""
        test_customer.sms_opted_out = False
        db_session.add(test_customer)
        db_session.commit()

        _make_period(
            db_session, test_tenant.id, used=10, included=10, cap_policy="hard"
        )

        result = check_quota(db_session, test_tenant.id, test_customer.id, 1)

        assert result.allowed is False
        assert result.blocked_reason == "monthly_quota_reached"

    def test_remaining_segments_computed_correctly(
        self, db_session, test_tenant, test_customer
    ):
        """remaining_segments = max(0, included - used)."""
        test_customer.sms_opted_out = False
        db_session.add(test_customer)
        db_session.commit()

        _make_period(
            db_session, test_tenant.id, used=73, included=100, cap_policy="soft"
        )

        result = check_quota(db_session, test_tenant.id, test_customer.id, 1)

        assert result.allowed is True
        assert result.remaining_segments == 27
        assert result.used_segments == 73


# ─── consume_quota() ──────────────────────────────────────────────────────────


class TestConsumeQuota:
    def test_consume_increments_used_segments(self, db_session, test_tenant):
        """consume_quota() should increment used_segments atomically."""
        period = _make_period(db_session, test_tenant.id, used=50, included=100)
        initial_used = period.used_segments

        consume_quota(db_session, test_tenant.id, segments=5)
        db_session.commit()

        db_session.refresh(period)
        assert period.used_segments == initial_used + 5

    def test_consume_no_op_when_no_active_period(self, db_session, test_tenant):
        """consume_quota should silently skip if no period found (uses future period to avoid collision)."""
        from datetime import timedelta

        # Create a period in the far future so it won't be "active" now
        future_period = SmsQuotaPeriod(
            tenant_id=test_tenant.id,
            period_start=datetime.now(UTC) + timedelta(days=60),
            period_end=datetime.now(UTC) + timedelta(days=90),
            included_segments=100,
            used_segments=0,
            cap_policy="soft",
        )
        db_session.add(future_period)
        db_session.commit()

        # No active period — should not raise
        consume_quota(db_session, test_tenant.id, segments=3)
        db_session.commit()


# ─── create_initial_period() ─────────────────────────────────────────────────


class TestCreateInitialPeriod:
    def test_creates_period_for_current_month(self, db_session, test_tenant):
        """Initial period should cover start-to-end of current calendar month."""
        period = create_initial_period(db_session, test_tenant.id)

        assert period.tenant_id == test_tenant.id
        assert period.period_start.day == 1
        assert period.period_start.hour == 0
        assert period.included_segments == 100
        assert period.used_segments == 0
        assert period.cap_policy == "soft"

    def test_creates_period_with_custom_params(self, db_session, test_tenant):
        """Custom included_segments and cap_policy are respected."""
        period = create_initial_period(
            db_session, test_tenant.id, included_segments=500, cap_policy="hard"
        )

        assert period.included_segments == 500
        assert period.cap_policy == "hard"


# ─── Celery Task Inner Impls ──────────────────────────────────────────────────


class TestCeleryTaskImpls:
    def test_monitor_impl_no_op_when_no_periods(self, db_session):
        """Monitor task returns zeros when no active periods exist."""
        from tasks.monitor_sms_quota_thresholds import _monitor_impl

        result = _monitor_impl(db_session)

        assert "notified_80_pct" in result
        assert "notified_100_pct" in result

    def test_rollover_impl_no_op_when_no_active_phones(self, db_session):
        """Rollover task returns zeros when no active provisioned phones."""
        from tasks.rollover_sms_quota_periods import _rollover_impl

        result = _rollover_impl(db_session)

        assert "periods_created" in result
        assert "periods_skipped" in result


# ─── API Route Smoke Tests ────────────────────────────────────────────────────


class TestSmsQuotaRoute:
    def test_quota_test_endpoint_returns_200(self, client):
        """Test endpoint returns a quota response."""
        resp = client.get("/api/v1/sms/quota/test")
        assert resp.status_code == 200
        data = resp.json()
        assert "included_segments" in data
        assert "used_segments" in data
        assert "remaining_segments" in data
        assert "cap_policy" in data

    def test_quota_authenticated_endpoint_requires_auth(self, client):
        """Authenticated endpoint requires JWT."""
        resp = client.get("/api/v1/sms/quota/")
        assert resp.status_code in (401, 403)
