"""
SD-3: Verify notification template coverage for all 9 active notification_type codes.
All 9 types must have email, in_app, and push templates with tenant_id=NULL.
"""

import pytest
from sqlmodel import text

pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]

EXPECTED_NOTIFICATION_TYPES = {
    "customer_communication_sent",
    "dunning_reminder",
    "quote_accepted",
    "job_assigned",
    "schedule_changed",
    "qb_sync_conflict",
    "qb_conflict_pre_warning",
    "gps_variance_alert",
    "system_template_updated",
}

EXPECTED_CHANNELS = {"email", "in_app", "push"}


class TestNotificationTemplateCoverage:
    def test_all_notification_types_have_templates(self, db_session):
        """Every active notification_type must have a platform-level template for each channel."""
        rows = db_session.exec(
            text("""
                SELECT notification_type_code, channel
                FROM public.notification_template
                WHERE tenant_id IS NULL AND is_active = true
                ORDER BY notification_type_code, channel
            """)
        ).fetchall()

        covered = {}
        for row in rows:
            covered.setdefault(row.notification_type_code, set()).add(row.channel)

        for nt_code in EXPECTED_NOTIFICATION_TYPES:
            assert nt_code in covered, (
                f"notification_type '{nt_code}' has no platform templates (tenant_id=NULL). "
                "Run seed_platform.py to fix."
            )
            missing = EXPECTED_CHANNELS - covered[nt_code]
            assert not missing, (
                f"notification_type '{nt_code}' missing channels: {missing}. "
                "Run seed_platform.py to fix."
            )

    def test_total_platform_template_count_is_27(self, db_session):
        """Platform-level notification_template rows: 9 types × 3 channels = 27 rows.

        Uses scoped count (only platform rows, not tenant overrides).
        """
        result = db_session.exec(
            text("""
                SELECT COUNT(*) AS cnt
                FROM public.notification_template
                WHERE tenant_id IS NULL AND is_active = true
            """)
        ).first()
        # Note: may be > 27 if future types/channels are added; use >= for resilience
        assert result.cnt >= 27, (
            f"Expected at least 27 platform notification_template rows (9 types × 3 channels), "
            f"got {result.cnt}. Run seed_platform.py to add missing rows."
        )

    def test_sd2_notification_types_have_non_placeholder_bodies(self, db_session):
        """SD-2 types must have non-empty, non-generic body text in templates."""
        result = db_session.exec(
            text("""
                SELECT notification_type_code, channel, body
                FROM public.notification_template
                WHERE tenant_id IS NULL
                  AND notification_type_code IN (
                    'job_assigned', 'schedule_changed', 'qb_sync_conflict',
                    'qb_conflict_pre_warning', 'gps_variance_alert', 'system_template_updated'
                  )
                  AND is_active = true
            """)
        ).fetchall()

        assert len(result) == 18, (
            f"Expected 18 SD-2 notification_template rows, got {len(result)}. "
            "Run seed_platform.py to add missing rows."
        )
        for row in result:
            assert row.body and len(row.body) > 10, (
                f"Template body for {row.notification_type_code}/{row.channel} "
                "appears empty or too short"
            )
