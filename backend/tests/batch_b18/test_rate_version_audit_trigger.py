"""
FIND-131 (S2 High) — Add audit.log_changes() triggers to labor_rate_version
and pricing_cache tables.

Labor rate changes feed directly into labor cost calculations on quotes, time
entries, and job profitability. Supplier price changes feed quote estimates.
Without audit triggers, rate/price changes produce unexplained billing
differences with no forensic trail.

Migration: phase_fe_1_batch_b18_audit_triggers_rate_version_pricing_cache (00b2f1d3e1ce)

Test coverage:
  1. DB: audit_labor_rate_version_changes trigger exists on labor_rate_version
  2. DB: audit_pricing_cache_changes trigger exists on pricing_cache
  3. Functional: INSERT into labor_rate_version → audit.event row captured

Test subfolder: tests/batch_b18/
"""


class TestFind131LaborRateVersionTriggerExists:
    """audit_labor_rate_version_changes trigger must exist."""

    def test_audit_labor_rate_version_trigger_exists(self, db_session):
        """audit_labor_rate_version_changes trigger must be present in pg_trigger."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT t.tgname "
                "FROM pg_trigger t "
                "JOIN pg_class c ON t.tgrelid = c.oid "
                "WHERE c.relname = 'labor_rate_version' "
                "  AND t.tgname = 'audit_labor_rate_version_changes' "
                "  AND NOT t.tgisinternal"
            )
        ).first()

        assert result is not None, (
            "Trigger 'audit_labor_rate_version_changes' missing from labor_rate_version — "
            "FIND-131 migration not applied"
        )


class TestFind131PricingCacheTriggerExists:
    """audit_pricing_cache_changes trigger must exist."""

    def test_audit_pricing_cache_trigger_exists(self, db_session):
        """audit_pricing_cache_changes trigger must be present in pg_trigger."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT t.tgname "
                "FROM pg_trigger t "
                "JOIN pg_class c ON t.tgrelid = c.oid "
                "WHERE c.relname = 'pricing_cache' "
                "  AND t.tgname = 'audit_pricing_cache_changes' "
                "  AND NOT t.tgisinternal"
            )
        ).first()

        assert result is not None, (
            "Trigger 'audit_pricing_cache_changes' missing from pricing_cache — "
            "FIND-131 migration not applied"
        )


class TestFind131LaborRateVersionAuditFires:
    """INSERT into labor_rate_version → audit.event row captured (§16.6 persistence test)."""

    def test_insert_labor_rate_version_creates_audit_event(
        self, db_session, test_tenant
    ):
        """Write a LaborRateVersion row → assert audit.event row captured with entity_name='labor_rate_version'."""
        from sqlalchemy import text

        tenant_id = str(test_tenant.id)

        # Clear audit log for this entity to isolate assertion
        db_session.execute(
            text("DELETE FROM audit.event WHERE entity_name = 'labor_rate_version'")
        )
        db_session.commit()

        # Insert a LaborRateVersion row via raw SQL (valid_period requires tstzrange).
        # Use a past CLOSED range to avoid GiST conflict with the seeded open-ended
        # journeyman row from seed_test_tenant.py [2026-06-01, NULL).
        db_session.execute(
            text(
                f"INSERT INTO labor_rate_version "
                f"(tenant_id, skill_level_code, hourly_rate_cents, burden_pct, valid_period, created_at) "
                f"VALUES ('{tenant_id}'::uuid, 'journeyman', 8500, 0.20, "
                f"tstzrange('2019-01-01', '2019-12-31'), now())"
            )
        )
        db_session.commit()

        # Assert audit.event row was captured
        result = db_session.execute(
            text(
                "SELECT action, entity_name FROM audit.event "
                "WHERE entity_name = 'labor_rate_version' AND action = 'INSERT' "
                "ORDER BY occurred_at DESC LIMIT 1"
            )
        ).first()

        assert result is not None, (
            "audit.event should contain INSERT event for labor_rate_version after FIND-131 migration — "
            "trigger is not firing"
        )
        assert result[0] == "INSERT", f"Expected action='INSERT', got '{result[0]}'"
        assert result[1] == "labor_rate_version", (
            f"Expected entity_name='labor_rate_version', got '{result[1]}'"
        )
