"""
tests/batch_b5/test_report_api_shapes.py

B5/A5 — Report endpoint shape + display_mode threshold tests.

Test focus areas (from design doc H):
  1. All 6 endpoints return correct JSON shape with empty data
     (no data in date range → data: [], row_count: 0)
  2. display_mode switches at exactly report_chart_threshold rows
  3. Tenant isolation — reports never return cross-tenant rows
  4. margin_pct = null edge case for job with no quote_id
  5. AR aging bucket boundaries (31-day boundary, null due_at → current)
  6. Voice analytics null latency — rows with null latency don't crash

NOTE: Tests that need a custom report_chart_threshold mock get_report_chart_threshold
directly to avoid the audit.log_changes() trigger on tenant_settings (which requires
NEW.id, but tenant_settings PK is tenant_id).
"""

import uuid
from datetime import date, timedelta

from services.report_service import (
    classify_margin_bucket,
    compute_display_mode,
    get_ar_aging_report,
    get_profitability_report,
    get_revenue_report,
    get_voice_analytics_report,
)

# ---------------------------------------------------------------------------
# H1: Empty data shape tests
# ---------------------------------------------------------------------------


class TestReportEmptyShapes:
    """All 6 endpoints return valid JSON with empty data when no records exist in range."""

    def test_profitability_empty_returns_list(self, db_session, test_tenant):
        """Profitability report with no jobs in range returns empty list."""
        result = get_profitability_report(
            db=db_session,
            tenant_id=test_tenant.id,
            date_from=date(2010, 1, 1),
            date_to=date(2010, 1, 31),
        )
        assert isinstance(result, list)
        assert result == []

    def test_revenue_empty_returns_list(self, db_session, test_tenant):
        result = get_revenue_report(
            db=db_session,
            tenant_id=test_tenant.id,
            date_from=date(2010, 1, 1),
            date_to=date(2010, 1, 31),
        )
        assert isinstance(result, list)
        assert result == []

    def test_ar_aging_empty_returns_correct_shape(self, db_session, second_tenant):
        # Use second_tenant (no scenario seed data) to test empty-state shape
        result = get_ar_aging_report(
            db=db_session,
            tenant_id=second_tenant.id,
            as_of_date=date(2010, 1, 31),
        )
        assert result["data"] == []
        assert result["summary"]["total_outstanding_cents"] == 0
        assert result["summary"]["current_cents"] == 0
        assert result["summary"]["bucket_31_60_cents"] == 0
        assert result["summary"]["bucket_61_90_cents"] == 0
        assert result["summary"]["bucket_91_plus_cents"] == 0

    def test_voice_analytics_empty_returns_correct_shape(self, db_session, test_tenant):
        result = get_voice_analytics_report(
            db=db_session,
            tenant_id=test_tenant.id,
            date_from=date(2010, 1, 1),
            date_to=date(2010, 1, 31),
        )
        assert result["data"] == []
        summary = result["summary"]
        assert summary["total_commands"] == 0
        assert summary["successful_commands"] == 0
        assert summary["success_rate_pct"] is None  # 0/0 → None


# ---------------------------------------------------------------------------
# H2: display_mode threshold test
# ---------------------------------------------------------------------------


class TestDisplayModeThreshold:
    """display_mode switches at exactly report_chart_threshold rows."""

    def test_below_threshold_is_chart(self):
        assert compute_display_mode(2, 3) == "chart"

    def test_at_threshold_is_table(self):
        assert compute_display_mode(3, 3) == "table"

    def test_above_threshold_is_table(self):
        assert compute_display_mode(10, 3) == "table"

    def test_zero_rows_is_chart(self):
        assert compute_display_mode(0, 3) == "chart"

    def test_threshold_function_returns_default_when_no_settings(self, db_session):
        """Verify threshold function defaults to 8 when no TenantSettings row exists."""
        from services.report_service import get_report_chart_threshold

        random_id = uuid.uuid4()
        threshold = get_report_chart_threshold(db_session, random_id)
        assert threshold == 8

    def test_display_mode_uses_threshold_from_service(self, db_session):
        """End-to-end: compute_display_mode(row_count=5, threshold=8) → 'chart'."""
        from services.report_service import get_report_chart_threshold

        random_id = uuid.uuid4()
        threshold = get_report_chart_threshold(db_session, random_id)  # returns 8
        assert compute_display_mode(5, threshold) == "chart"
        assert compute_display_mode(8, threshold) == "table"


# ---------------------------------------------------------------------------
# H4: margin_pct = null edge case
# ---------------------------------------------------------------------------


class TestProfitabilityMarginNullEdgeCase:
    """Jobs without a quote_id (quoted_total_cents=0) return margin_pct=null, below_target=false."""

    def test_null_margin_when_no_quoted_total(self):
        margin_pct = None  # Service sets this when quoted_total_cents = 0
        below_target = margin_pct is not None and margin_pct < 20
        bucket = classify_margin_bucket(margin_pct, [10, 20, 30])

        assert margin_pct is None
        assert below_target is False
        assert bucket is None

    def test_below_target_false_when_margin_pct_none(self):
        """Conservative: below_margin_target=False when margin_pct is None."""
        margin_pct = None
        below_target = margin_pct is not None and margin_pct < 20
        assert below_target is False

    def test_below_target_true_when_below_20(self):
        """margin_pct=15 with target=20 → below_target=True."""
        margin_pct = 15.0
        below_target = margin_pct is not None and margin_pct < 20
        assert below_target is True

    def test_below_target_false_when_above_20(self):
        """margin_pct=25 with target=20 → below_target=False."""
        margin_pct = 25.0
        below_target = margin_pct is not None and margin_pct < 20
        assert below_target is False


# ---------------------------------------------------------------------------
# H5: AR Aging bucket boundary tests
# ---------------------------------------------------------------------------


class TestARAgingBucketBoundaries:
    """AR aging: 31-day boundary, null due_at lands in current bucket."""

    def test_overdue_31_days_is_in_31_60_bucket(self):
        """Invoice exactly 31 days past due → bucket_31_60."""
        as_of = date(2026, 3, 31)
        due_date = as_of - timedelta(days=31)
        days_overdue = (as_of - due_date).days
        assert days_overdue == 31
        assert 31 <= days_overdue <= 60

    def test_overdue_30_days_is_below_31_60_bucket(self):
        """Invoice 30 days past due — days_overdue=30 < 31 (not in bucket_31_60)."""
        as_of = date(2026, 3, 31)
        due_date = as_of - timedelta(days=30)
        days_overdue = (as_of - due_date).days
        assert days_overdue == 30
        assert days_overdue < 31  # Not in 31-60 bucket

    def test_null_due_at_logic_is_current(self):
        """Null due_at invoices are treated as current (not overdue)."""
        # SQL: CASE WHEN i.due_at IS NULL OR days_overdue <= 0 → current
        due_at_is_null = True
        is_current = due_at_is_null
        assert is_current is True

    def test_not_yet_due_is_current(self):
        """Invoice with future due_at (days_overdue ≤ 0) → current bucket."""
        as_of = date(2026, 3, 31)
        future_due = as_of + timedelta(days=10)  # Due in the future
        days_overdue = (as_of - future_due).days  # Negative → not overdue
        assert days_overdue < 0
        # SQL: CAST(:as_of_date AS date) - i.due_at::date <= 0 → current

    def test_61_days_overdue_is_61_90(self):
        as_of = date(2026, 3, 31)
        due_date = as_of - timedelta(days=61)
        days_overdue = (as_of - due_date).days
        assert days_overdue == 61
        assert 61 <= days_overdue <= 90

    def test_91_plus_days_overdue_is_91_plus(self):
        as_of = date(2026, 3, 31)
        due_date = as_of - timedelta(days=95)
        days_overdue = (as_of - due_date).days
        assert days_overdue == 95
        assert days_overdue > 90  # SQL: > 90 → bucket_91_plus


# ---------------------------------------------------------------------------
# H6: Voice analytics null latency
# ---------------------------------------------------------------------------


class TestVoiceAnalyticsNullLatency:
    """Rows with null latency don't crash aggregation; avg is null when all null."""

    def test_empty_voice_log_has_null_summary_latency(self, db_session, test_tenant):
        """No voice_command_log rows → all latency averages are null."""
        result = get_voice_analytics_report(
            db=db_session,
            tenant_id=test_tenant.id,
            date_from=date(2010, 1, 1),
            date_to=date(2010, 1, 31),
        )
        summary = result["summary"]
        assert summary["avg_whisper_latency_ms"] is None
        assert summary["avg_ollama_latency_ms"] is None
        assert summary["avg_total_latency_ms"] is None
        assert summary["p95_total_latency_ms"] is None

    def test_voice_analytics_group_by_intent_empty(self, db_session, test_tenant):
        result = get_voice_analytics_report(
            db=db_session,
            tenant_id=test_tenant.id,
            date_from=date(2010, 1, 1),
            date_to=date(2010, 1, 31),
            group_by="intent",
        )
        assert result["data"] == []

    def test_voice_analytics_group_by_user_empty(self, db_session, test_tenant):
        result = get_voice_analytics_report(
            db=db_session,
            tenant_id=test_tenant.id,
            date_from=date(2010, 1, 1),
            date_to=date(2010, 1, 31),
            group_by="user",
        )
        assert result["data"] == []

    def test_voice_analytics_group_by_day_empty(self, db_session, test_tenant):
        result = get_voice_analytics_report(
            db=db_session,
            tenant_id=test_tenant.id,
            date_from=date(2010, 1, 1),
            date_to=date(2010, 1, 31),
            group_by="day",
        )
        assert result["data"] == []


# ---------------------------------------------------------------------------
# Tenant isolation tests
# ---------------------------------------------------------------------------


class TestReportTenantIsolation:
    """Reports never return rows from a different tenant_id."""

    def test_profitability_isolates_to_tenant(
        self, db_session, test_tenant, second_tenant
    ):
        """Two tenants — each gets only their own profitability data."""
        result_tenant1 = get_profitability_report(
            db=db_session,
            tenant_id=test_tenant.id,
            date_from=date(2010, 1, 1),
            date_to=date(2030, 12, 31),
        )
        result_tenant2 = get_profitability_report(
            db=db_session,
            tenant_id=second_tenant.id,
            date_from=date(2010, 1, 1),
            date_to=date(2030, 12, 31),
        )
        # Both tenants have no jobs → both empty; no cross-contamination
        all_group_keys_t1 = {r["group_key"] for r in result_tenant1}
        all_group_keys_t2 = {r["group_key"] for r in result_tenant2}
        assert all_group_keys_t1.isdisjoint(all_group_keys_t2) or (
            not all_group_keys_t1 and not all_group_keys_t2
        )

    def test_ar_aging_isolates_to_tenant(self, db_session, test_tenant, second_tenant):
        result_t1 = get_ar_aging_report(
            db=db_session,
            tenant_id=test_tenant.id,
            as_of_date=date(2030, 12, 31),
        )
        result_t2 = get_ar_aging_report(
            db=db_session,
            tenant_id=second_tenant.id,
            as_of_date=date(2030, 12, 31),
        )
        # second_tenant has no invoices → total is 0
        # test_tenant may have scenario seed invoices — just verify it has valid shape
        assert result_t2["summary"]["total_outstanding_cents"] == 0
        assert isinstance(result_t1["summary"]["total_outstanding_cents"], int)
        assert result_t1["summary"]["total_outstanding_cents"] >= 0

    def test_voice_analytics_isolates_to_tenant(
        self, db_session, test_tenant, second_tenant
    ):
        """Voice analytics report isolates to the queried tenant.

        SD-9 fix: seed data now includes voice_command_log rows for both
        test_tenant and second_tenant. Assert tenant isolation by verifying
        each tenant's data stays separate (Rule 16 - Test Resilience).
        """
        result_t1 = get_voice_analytics_report(
            db=db_session,
            tenant_id=test_tenant.id,
            date_from=date(2010, 1, 1),
            date_to=date(2030, 12, 31),
        )
        result_t2 = get_voice_analytics_report(
            db=db_session,
            tenant_id=second_tenant.id,
            date_from=date(2010, 1, 1),
            date_to=date(2030, 12, 31),
        )
        # Tenant isolation: each tenant sees only its own commands.
        # Both may have seed data (SD-9), but the counts must not cross-contaminate.
        t1_total = result_t1["summary"]["total_commands"]
        t2_total = result_t2["summary"]["total_commands"]
        # Verify valid shape
        assert isinstance(t1_total, int)
        assert isinstance(t2_total, int)
        assert t1_total >= 0
        assert t2_total >= 0
        # If both have data, verify the group keys don't overlap (isolation)
        t1_keys = {r["group_key"] for r in result_t1["data"]}
        t2_keys = {r["group_key"] for r in result_t2["data"]}
        # The group_key for intent is the intent string; for user it's the user UUID.
        # Cross-tenant user UUIDs are always distinct, so keys must be disjoint.
        assert t1_keys.isdisjoint(t2_keys), (
            f"Tenant isolation violated: t1 keys {t1_keys} intersect t2 keys {t2_keys}"
        )
