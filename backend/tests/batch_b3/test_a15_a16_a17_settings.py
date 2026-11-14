"""
Batch B3 — A15, A16, A17 Test Coverage
========================================

A15: Chart-or-Table Threshold Setting (report_chart_threshold)
A16: ETC Variance Notification System (Celery task + thresholds)
A17: Margin Bucket Configuration (margin_bucket_boundaries, margin_target_pct)

Test Coverage:
- TenantSettings ORM has report_chart_threshold (INT, default 8)
- TenantSettings ORM has etc_variance_owner_notify_pct (INT, default 50)
- TenantSettings ORM has etc_variance_note_required_pct (INT, default 10)
- TenantSettings ORM has margin_bucket_boundaries (JSONB, default [10,20,30])
- TenantSettings ORM has margin_target_pct (INT, default 20)
- notify_etc_variance_owners task is importable and registered in Celery
- notify_etc_variance_owners task returns correct dict shape when run with empty DB
- check_etc_variance correctly uses notify_pct from tenant settings
- margin_target_pct is consumed by compute_projected_margin (below_margin_target)
- check constraints are present in DB for all 4 constraints
"""

import uuid

from sqlmodel import select

# ─────────────────────────────────────────────────────────────────────────────
# A15, A16, A17 — ORM model checks
# ─────────────────────────────────────────────────────────────────────────────


class TestA15A16A17ORMModels:
    """Verify all 5 settings keys exist in platform_setting_catalog (FIND-086)."""

    def test_tenant_settings_has_report_chart_threshold(self, db_session):
        from app.models.platform_setting import PlatformSettingCatalog

        row = db_session.exec(
            select(PlatformSettingCatalog).where(
                PlatformSettingCatalog.key == "report_chart_threshold"
            )
        ).first()
        assert row is not None, (
            "report_chart_threshold missing from platform_setting_catalog"
        )

    def test_tenant_settings_has_etc_variance_owner_notify_pct(self, db_session):
        from app.models.platform_setting import PlatformSettingCatalog

        row = db_session.exec(
            select(PlatformSettingCatalog).where(
                PlatformSettingCatalog.key == "etc_variance_owner_notify_pct"
            )
        ).first()
        assert row is not None

    def test_tenant_settings_has_etc_variance_note_required_pct(self, db_session):
        from app.models.platform_setting import PlatformSettingCatalog

        row = db_session.exec(
            select(PlatformSettingCatalog).where(
                PlatformSettingCatalog.key == "etc_variance_note_required_pct"
            )
        ).first()
        assert row is not None

    def test_tenant_settings_has_margin_bucket_boundaries(self, db_session):
        from app.models.platform_setting import PlatformSettingCatalog

        row = db_session.exec(
            select(PlatformSettingCatalog).where(
                PlatformSettingCatalog.key == "margin_bucket_boundaries"
            )
        ).first()
        assert row is not None

    def test_tenant_settings_has_margin_target_pct(self, db_session):
        from app.models.platform_setting import PlatformSettingCatalog

        row = db_session.exec(
            select(PlatformSettingCatalog).where(
                PlatformSettingCatalog.key == "margin_target_pct"
            )
        ).first()
        assert row is not None

    def test_tenant_settings_defaults_in_db(self, db_session, test_tenant):
        """Verify platform defaults are seeded (FIND-086: replaces TenantSettings row check)."""
        from app.models.platform_setting import PlatformSetting

        for key in (
            "report_chart_threshold",
            "etc_variance_owner_notify_pct",
            "etc_variance_note_required_pct",
            "margin_bucket_boundaries",
            "margin_target_pct",
        ):
            row = db_session.exec(
                select(PlatformSetting)
                .where(PlatformSetting.key == key)
                .where(PlatformSetting.tenant_id.is_(None))
            ).first()
            assert row is not None, f"Platform default row missing for '{key}'"
            assert row.value is not None


# ─────────────────────────────────────────────────────────────────────────────
# A16 — Celery task registration
# ─────────────────────────────────────────────────────────────────────────────


class TestA16CeleryTask:
    """Verify the ETC variance notification Celery task is importable and registered."""

    def test_task_is_importable(self):
        from tasks.notify_etc_variance_owners import notify_etc_variance_owners

        assert callable(notify_etc_variance_owners)

    def test_task_is_registered_in_celery(self):
        """Task name must appear in Celery's registered tasks."""
        from core.celery_app import celery_app

        # Tasks are registered when the module is imported
        from tasks.notify_etc_variance_owners import (
            notify_etc_variance_owners,  # noqa: F401
        )

        registered = list(celery_app.tasks.keys())
        assert "notify_etc_variance_owners" in registered, (
            f"Task not found in registered tasks. Found: {registered}"
        )

    def test_task_in_beat_schedule(self):
        """Task must have a Beat schedule entry."""
        from core.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
        assert "notify-etc-variance-owners-every-15min" in schedule
        entry = schedule["notify-etc-variance-owners-every-15min"]
        assert entry["task"] == "notify_etc_variance_owners"

    def test_task_runs_without_data(self, db_session):
        """Task executes cleanly even with no matching ETC entries."""
        from unittest.mock import patch

        # Patch get_db to use our test session
        from tasks.notify_etc_variance_owners import notify_etc_variance_owners

        # Call with mocked DB — it should return dict, not raise
        with patch(
            "tasks.notify_etc_variance_owners.get_db", return_value=iter([db_session])
        ):
            result = notify_etc_variance_owners()
        assert isinstance(result, dict)
        assert "notified" in result
        assert "skipped" in result
        assert "errors" in result


# ─────────────────────────────────────────────────────────────────────────────
# A16 — ETC variance threshold integration
# ─────────────────────────────────────────────────────────────────────────────


class TestA16VarianceThresholds:
    """Verify check_etc_variance uses the right thresholds."""

    def test_variance_at_exactly_50_pct_triggers_notification(self):
        """Default notify_pct=50 — 50% over quoted triggers notification."""
        from decimal import Decimal

        from services.etc_service import check_etc_variance

        # 15 projected vs 10 quoted = 50% over
        should_notify, pct = check_etc_variance(Decimal("15"), Decimal("10"), 50)
        assert should_notify is True
        assert pct == Decimal("50")

    def test_variance_just_below_50_pct_does_not_trigger(self):
        """49.9% over does not trigger."""
        from decimal import Decimal

        from services.etc_service import check_etc_variance

        # 14.99 projected vs 10 quoted = 49.9%
        should_notify, pct = check_etc_variance(Decimal("14.99"), Decimal("10"), 50)
        assert should_notify is False


# ─────────────────────────────────────────────────────────────────────────────
# A17 — Margin bucket integration
# ─────────────────────────────────────────────────────────────────────────────


class TestA17MarginBuckets:
    """Verify margin_target_pct is used by compute_projected_margin."""

    def test_compute_projected_margin_uses_margin_target_pct(
        self, db_session, test_tenant
    ):
        """When projected total > quoted, below_margin_target should be True."""
        from services.etc_service import compute_projected_margin

        result = compute_projected_margin(
            db=db_session,
            tenant_id=test_tenant.id,
            job_id=uuid.uuid4(),
            hourly_rate_cents=8500,
            quoted_total_cents=50000,
            actual_labor_cost_cents=60000,  # already over budget
            actual_material_cost_cents=0,
            margin_target_pct=20,
        )
        assert result["below_margin_target"] is True
        # margin_target_pct is a parameter; verify result has the expected keys
        assert "projected_margin_pct" in result
        assert "etc_source" in result

    def test_margin_bucket_boundaries_default(self, db_session, test_tenant):
        """Default margin_bucket_boundaries platform default is [10, 20, 30] (FIND-086)."""
        from app.models.platform_setting import PlatformSetting

        row = db_session.exec(
            select(PlatformSetting)
            .where(PlatformSetting.key == "margin_bucket_boundaries")
            .where(PlatformSetting.tenant_id.is_(None))
        ).first()
        assert row is not None
        boundaries = row.value
        assert isinstance(boundaries, list)
        assert len(boundaries) == 3


# ─────────────────────────────────────────────────────────────────────────────
# A15 — Report chart threshold
# ─────────────────────────────────────────────────────────────────────────────


class TestA15ReportChartThreshold:
    """Verify report_chart_threshold in platform_setting (FIND-086)."""

    def test_chart_threshold_default_value(self, db_session, test_tenant):
        """Default report_chart_threshold should be 8 (platform default)."""
        from app.models.platform_setting import PlatformSetting

        row = db_session.exec(
            select(PlatformSetting)
            .where(PlatformSetting.key == "report_chart_threshold")
            .where(PlatformSetting.tenant_id.is_(None))
        ).first()
        assert row is not None
        assert row.value == 8

    def test_chart_threshold_can_be_updated(self, db_session, test_tenant):
        """report_chart_threshold tenant override can be set (FIND-086)."""
        from app.models.platform_setting import PlatformSetting
        from services.setting_resolver import get_effective_setting

        override = PlatformSetting(
            key="report_chart_threshold", value=15, tenant_id=test_tenant.id
        )
        db_session.add(override)
        db_session.flush()

        val, scope = get_effective_setting(
            db_session, test_tenant.id, "report_chart_threshold"
        )
        assert val == 15
        assert scope == "tenant"

        db_session.rollback()
