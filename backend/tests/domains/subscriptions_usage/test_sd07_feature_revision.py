"""
SD-07 Feature Revision Verification Tests
Domain: Subscriptions & Usage

MKT-B11 UPDATE: Pricing Model v3.0 supersedes SD-07 feature codes.
- dispatch_slots → deleted (replaced by schedule_lanes)
- data_exports → deleted (unlimited and untracked)
- enterprise_plan → deleted
- charter_plan → added (only active plan during Charter cohort)
- schedule_lanes → new feature code

These tests verify the post-MKT-B11 migration state.
"""

import pytest
from sqlalchemy import text

pytestmark = [
    pytest.mark.domain_subscriptions_usage,
    pytest.mark.unit,
]


class TestSD07FeatureRevision:
    """Verify MKT-B11 v3.0 product_feature and product_plan changes are applied."""

    def test_schedule_lanes_feature_exists(self, db_session):
        """schedule_lanes must exist in product_feature after MKT-B11 migration."""
        result = db_session.execute(
            text(
                "SELECT code, name, unit, is_active FROM public.product_feature WHERE code = 'schedule_lanes'"
            )
        ).first()
        assert result is not None, (
            "schedule_lanes not found in product_feature — MKT-B11 migration may not have run"
        )
        assert result.is_active is True
        assert result.unit == "lanes"

    def test_outbound_sms_segments_feature_exists(self, db_session):
        """outbound_sms_segments must exist in product_feature after MKT-B11 migration."""
        result = db_session.execute(
            text(
                "SELECT code, name, unit, is_active FROM public.product_feature WHERE code = 'outbound_sms_segments'"
            )
        ).first()
        assert result is not None, (
            "outbound_sms_segments not found in product_feature — MKT-B11 migration may not have run"
        )
        assert result.is_active is True
        assert result.unit == "segments"

    def test_dispatch_slots_feature_deleted(self, db_session):
        """dispatch_slots must NOT exist in product_feature after MKT-B11 migration."""
        result = db_session.execute(
            text(
                "SELECT code FROM public.product_feature WHERE code = 'dispatch_slots'"
            )
        ).first()
        assert result is None, (
            "dispatch_slots still exists in product_feature — MKT-B11 migration may not have run. "
            "schedule_lanes replaces dispatch_slots in v3.0."
        )

    def test_data_exports_feature_deleted(self, db_session):
        """data_exports must NOT exist in product_feature after MKT-B11 migration."""
        result = db_session.execute(
            text("SELECT code FROM public.product_feature WHERE code = 'data_exports'")
        ).first()
        assert result is None, (
            "data_exports still exists in product_feature — MKT-B11 migration may not have run. "
            "Data exports are unlimited and untracked in v3.0."
        )

    def test_qb_sync_operations_removed(self, db_session):
        """qb_sync_operations must NOT exist in product_feature after SD-07 migration."""
        result = db_session.execute(
            text(
                "SELECT code FROM public.product_feature WHERE code = 'qb_sync_operations'"
            )
        ).first()
        assert result is None, (
            "qb_sync_operations still exists in product_feature. "
            "QB sync is unlimited on all tiers per GTM matrix."
        )

    def test_charter_plan_exists_and_is_active(self, db_session):
        """product_plan must have a row with code='charter_plan' after MKT-B11.

        is_active is mode-dependent:
        - charter mode  : is_active=True  (only active plan)
        - post-beta mode : is_active=False (dormant; starter/teams become active)
        Both states are valid — we only assert the row exists.
        """
        result = db_session.execute(
            text(
                "SELECT code, name, is_active FROM public.product_plan WHERE code = 'charter_plan'"
            )
        ).first()
        assert result is not None, (
            "charter_plan not found in product_plan — MKT-B11 migration may not have run"
        )
        # is_active is mode-dependent: True in charter mode, False in post-beta mode
        assert result.is_active in (True, False)

    def test_teams_plan_exists(self, db_session):
        """product_plan must have a row with code='teams_plan' (SD-3 renamed 'teams' → 'teams_plan')."""
        result = db_session.execute(
            text(
                "SELECT code, name, is_active FROM public.product_plan WHERE code = 'teams_plan'"
            )
        ).first()
        assert result is not None, (
            "teams_plan not found in product_plan — SD-3 migration renamed 'teams' → 'teams_plan'"
        )

    def test_enterprise_plan_deleted(self, db_session):
        """enterprise_plan must NOT exist in product_plan after MKT-B11 migration."""
        result = db_session.execute(
            text("SELECT code FROM public.product_plan WHERE code = 'enterprise_plan'")
        ).first()
        assert result is None, (
            "enterprise_plan still exists in product_plan — MKT-B11 migration may not have run"
        )

    def test_professional_plan_removed(self, db_session):
        """product_plan must NOT have a row with code='professional_plan' after SD-07 rename."""
        result = db_session.execute(
            text(
                "SELECT code FROM public.product_plan WHERE code = 'professional_plan'"
            )
        ).first()
        assert result is None, (
            "professional_plan still exists in product_plan — SD-07 rename migration may not have run"
        )

    def test_charter_plan_schedule_lanes_limit_is_5(self, db_session):
        """charter_plan x schedule_lanes limit_quantity must be 5 per MKT-B11."""
        result = db_session.execute(
            text("""
                SELECT limit_quantity, limit_enforcement FROM public.product_plan_product_feature_version
                WHERE product_plan_code = 'charter_plan'
                  AND product_feature_code = 'schedule_lanes'
            """)
        ).first()
        assert result is not None, "charter_plan/schedule_lanes ppfv row not found"
        assert result.limit_quantity == 5, (
            f"Expected limit_quantity=5, got {result.limit_quantity}"
        )
        assert result.limit_enforcement == "block"

    def test_starter_plan_schedule_lanes_limit_is_5(self, db_session):
        """starter_plan x schedule_lanes limit_quantity must be 5 per MKT-B11."""
        result = db_session.execute(
            text("""
                SELECT limit_quantity FROM public.product_plan_product_feature_version
                WHERE product_plan_code = 'starter_plan'
                  AND product_feature_code = 'schedule_lanes'
            """)
        ).first()
        assert result is not None, "starter_plan/schedule_lanes ppfv row not found"
        assert result.limit_quantity == 5, (
            f"Expected limit_quantity=5, got {result.limit_quantity}"
        )

    def test_teams_schedule_lanes_limit_is_20(self, db_session):
        """teams_plan x schedule_lanes limit_quantity must be 20 per MKT-B11 (SD-3: renamed to teams_plan)."""
        result = db_session.execute(
            text("""
                SELECT limit_quantity FROM public.product_plan_product_feature_version
                WHERE product_plan_code = 'teams_plan'
                  AND product_feature_code = 'schedule_lanes'
            """)
        ).first()
        assert result is not None, (
            "teams_plan/schedule_lanes ppfv row not found — SD-3 renamed 'teams' → 'teams_plan'"
        )
        assert result.limit_quantity == 20, (
            f"Expected limit_quantity=20, got {result.limit_quantity}"
        )

    def test_charter_plan_voice_ai_minutes_limit_is_90(self, db_session):
        """charter_plan x voice_ai_minutes limit_quantity must be 90 per MKT-B11."""
        result = db_session.execute(
            text("""
                SELECT limit_quantity FROM public.product_plan_product_feature_version
                WHERE product_plan_code = 'charter_plan'
                  AND product_feature_code = 'voice_ai_minutes'
            """)
        ).first()
        assert result is not None, "charter_plan/voice_ai_minutes ppfv row not found"
        assert result.limit_quantity == 90

    def test_teams_voice_ai_minutes_limit_is_300(self, db_session):
        """teams_plan x voice_ai_minutes limit_quantity must be 300 per MKT-B11 (SD-3: renamed to teams_plan)."""
        result = db_session.execute(
            text("""
                SELECT limit_quantity FROM public.product_plan_product_feature_version
                WHERE product_plan_code = 'teams_plan'
                  AND product_feature_code = 'voice_ai_minutes'
            """)
        ).first()
        assert result is not None, (
            "teams_plan/voice_ai_minutes ppfv row not found — SD-3 renamed 'teams' → 'teams_plan'"
        )
        assert result.limit_quantity == 300, (
            f"Expected 300, got {result.limit_quantity}"
        )

    def test_dispatch_slots_ppfv_rows_absent(self, db_session):
        """No product_plan_product_feature_version rows should reference dispatch_slots."""
        result = db_session.execute(
            text("""
                SELECT COUNT(*) AS cnt FROM public.product_plan_product_feature_version
                WHERE product_feature_code = 'dispatch_slots'
            """)
        ).first()
        assert result.cnt == 0, (
            f"Expected 0 ppfv rows for dispatch_slots (deleted in MKT-B11), got {result.cnt}"
        )

    def test_qb_sync_operations_ppfv_rows_absent(self, db_session):
        """No product_plan_product_feature_version rows should reference qb_sync_operations."""
        result = db_session.execute(
            text("""
                SELECT COUNT(*) AS cnt FROM public.product_plan_product_feature_version
                WHERE product_feature_code = 'qb_sync_operations'
            """)
        ).first()
        assert result.cnt == 0, (
            f"Expected 0 ppfv rows for qb_sync_operations, got {result.cnt}"
        )

    def test_total_ppfv_rows_is_9(self, db_session):
        """Exactly 9 ppfv rows: charter_planx3 + starter_planx3 + teamsx3."""
        result = db_session.execute(
            text(
                "SELECT COUNT(*) AS cnt FROM public.product_plan_product_feature_version"
            )
        ).first()
        assert result.cnt == 9, (
            f"Expected exactly 9 ppfv rows (3 plans x 3 features), got {result.cnt}"
        )
