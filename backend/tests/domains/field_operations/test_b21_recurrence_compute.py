"""
B21: Pure function tests for _compute_next_job_at.

No DB, no client — pure date arithmetic.

Covers:
- daily interval=1 → +1 day
- weekly interval=2 → +14 days
- monthly interval=1 → same day next month
- monthly with end-of-month edge case (Jan 31 → Feb 28)
- annually interval=1 → same day next year
- interval_count respected (weekly interval=3 → +21 days)
"""

from datetime import date

import pytest

from tasks.recurring_jobs import _compute_next_job_at

pytestmark = [
    pytest.mark.domain_field_operations,
    pytest.mark.unit,
]


class TestComputeNextJobAt:
    def test_daily_next_date(self):
        """daily, interval=1 → next day."""
        d = date(2026, 7, 1)
        result = _compute_next_job_at("daily", 1, d)
        assert result == date(2026, 7, 2)

    def test_weekly_next_date(self):
        """weekly, interval=2 → 14 days later."""
        d = date(2026, 7, 1)
        result = _compute_next_job_at("weekly", 2, d)
        assert result == date(2026, 7, 15)

    def test_monthly_next_date(self):
        """monthly, interval=1 → same day next month."""
        d = date(2026, 7, 15)
        result = _compute_next_job_at("monthly", 1, d)
        assert result == date(2026, 8, 15)

    def test_monthly_next_date_end_of_month(self):
        """monthly, Jan 31 + 1 month → Feb 28 (dateutil clamps to last valid day)."""
        d = date(2026, 1, 31)
        result = _compute_next_job_at("monthly", 1, d)
        assert result == date(2026, 2, 28)

    def test_annually_next_date(self):
        """annually, interval=1 → same day next year."""
        d = date(2026, 7, 12)
        result = _compute_next_job_at("annually", 1, d)
        assert result == date(2027, 7, 12)

    def test_interval_count_respected(self):
        """weekly, interval=3 → 21 days later."""
        d = date(2026, 7, 1)
        result = _compute_next_job_at("weekly", 3, d)
        assert result == date(2026, 7, 22)
