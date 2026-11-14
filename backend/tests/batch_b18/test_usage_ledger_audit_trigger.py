"""
FIND-130 (S2 High) — Add audit.log_changes() trigger to usage_ledger table.

usage_ledger is the revenue backbone (voice AI minutes, QB sync calls, SMS
segments). Without an audit trigger, billing disputes have no forensic trail.
PRD-§3.1-F1 requires audit.log_changes() on all core tables.

Migration: phase_fe_1_batch_b18_usage_ledger_audit_trigger (109af03f0a5f)

Test coverage:
  1. DB: trigger audit_usage_ledger_changes exists on usage_ledger
  2. Functional: INSERT into usage_ledger → audit.event row captured with
     entity_name='usage_ledger' and action='INSERT'

Test subfolder: tests/batch_b18/
"""

import uuid
from datetime import UTC, datetime


class TestFind130AuditTriggerExists:
    """audit_usage_ledger_changes trigger must exist on usage_ledger."""

    def test_audit_trigger_exists(self, db_session):
        """audit_usage_ledger_changes trigger must be present in pg_trigger."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT t.tgname "
                "FROM pg_trigger t "
                "JOIN pg_class c ON t.tgrelid = c.oid "
                "WHERE c.relname = 'usage_ledger' "
                "  AND t.tgname = 'audit_usage_ledger_changes' "
                "  AND NOT t.tgisinternal"
            )
        ).first()

        assert result is not None, (
            "Trigger 'audit_usage_ledger_changes' missing from usage_ledger — "
            "FIND-130 migration not applied"
        )


class TestFind130AuditTriggerFires:
    """INSERT into usage_ledger must produce an audit.event row (§16.6 DB persistence test)."""

    def test_insert_usage_ledger_creates_audit_event(
        self, db_session, test_tenant, test_user
    ):
        """Write a UsageLedger row → assert audit.event row captured with entity_name='usage_ledger'."""
        from sqlalchemy import text

        # Seed a ProductFeature for the FK if not already present
        feature_code = f"test_feat_{uuid.uuid4().hex[:8]}"
        now = datetime.now(UTC)
        db_session.execute(
            text(
                f"INSERT INTO product_feature (code, name, unit, is_active, created_at, updated_at) "
                f"VALUES ('{feature_code}', 'Test Feature', 'count', true, now(), now()) "
                f"ON CONFLICT (code) DO NOTHING"
            )
        )
        db_session.commit()

        # Clear audit log for this entity to isolate assertion
        db_session.execute(
            text("DELETE FROM audit.event WHERE entity_name = 'usage_ledger'")
        )
        db_session.commit()

        # Insert a UsageLedger row via ORM
        idempotency_key = f"test-idem-{uuid.uuid4().hex}"
        tenant_id = str(test_tenant.id)
        db_session.execute(
            text(
                f"INSERT INTO usage_ledger "
                f"(tenant_id, product_feature_code, occurred_at, quantity, idempotency_key, is_reported, created_at) "
                f"VALUES ('{tenant_id}'::uuid, '{feature_code}', now(), 1.0, '{idempotency_key}', false, now())"
            )
        )
        db_session.commit()

        # Assert audit.event row was captured
        result = db_session.execute(
            text(
                "SELECT action, entity_name FROM audit.event "
                "WHERE entity_name = 'usage_ledger' AND action = 'INSERT' "
                "ORDER BY occurred_at DESC LIMIT 1"
            )
        ).first()

        assert result is not None, (
            "audit.event should contain INSERT event for usage_ledger after FIND-130 migration — "
            "trigger is not firing"
        )
        assert result[0] == "INSERT", f"Expected action='INSERT', got '{result[0]}'"
        assert result[1] == "usage_ledger", (
            f"Expected entity_name='usage_ledger', got '{result[1]}'"
        )
