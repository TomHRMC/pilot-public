"""
Test suite for Phase 5.3 - Comprehensive Schema Sync (DB Sync v#9)

This test file validates all database-level changes from Phase 5.3:
1. notification_delivery_attempt schema updates (new columns, renamed column, indexes)
2. Idempotency unique constraints (invoice, quote, payment)
3. Index standardization (conversation_session, job_time_entry, voice_command_log)
4. discount_version triggers (audit logging, immutability)

Reference: dev-docs/analysis/phase-5.3-db-schema-sync-9-plan.md
Migration: backend/migrations/versions/2026_04_11_2130-01bf58eed1b3_phase_5_3_comprehensive_schema_sync.py
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

# ==================== PHASE 1: notification_delivery_attempt Tests ====================


class TestNotificationDeliveryAttemptSchema:
    """Test Phase 5.3 Phase 1: notification_delivery_attempt schema updates."""

    def test_notification_delivery_attempt_columns_exist(self, db_session: Session):
        """Verify new columns exist in database: provider_code, duration_ms, created_by, details."""
        result = db_session.exec(
            text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'notification_delivery_attempt'
                  AND column_name IN ('details', 'provider_code', 'duration_ms', 'created_by')
                ORDER BY column_name
            """)
        ).all()

        assert len(result) == 4, "All 4 new/renamed columns should exist"

        column_names = {row[0] for row in result}
        assert "details" in column_names, (
            "Column 'details' should exist (renamed from provider_response)"
        )
        assert "provider_code" in column_names, "Column 'provider_code' should exist"
        assert "duration_ms" in column_names, "Column 'duration_ms' should exist"
        assert "created_by" in column_names, "Column 'created_by' should exist"

    def test_notification_delivery_attempt_created_by_foreign_key_exists(
        self, db_session: Session
    ):
        """Verify created_by foreign key to user.id exists."""
        result = db_session.exec(
            text("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name = 'notification_delivery_attempt'
                  AND constraint_type = 'FOREIGN KEY'
                  AND constraint_name = 'notification_delivery_attempt_created_by_fkey'
            """)
        ).first()

        assert result is not None, (
            "Foreign key notification_delivery_attempt_created_by_fkey should exist"
        )

    def test_notification_delivery_attempt_composite_index_exists(
        self, db_session: Session
    ):
        """Verify composite index idx_notif_attempt_outbox_time exists."""
        result = db_session.exec(
            text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'notification_delivery_attempt'
                  AND indexname = 'idx_notif_attempt_outbox_time'
            """)
        ).first()

        assert result is not None, (
            "Composite index idx_notif_attempt_outbox_time should exist"
        )

    def test_notification_delivery_attempt_old_indexes_removed(
        self, db_session: Session
    ):
        """Verify old ix_* indexes were removed.

        Note: ix_notification_delivery_attempt_tenant_id was legitimately
        re-created in Phase 8.0 Batch 6 as a proper FK structural index.
        Only ix_notification_delivery_attempt_notification_outbox_id (the
        old Phase 5.3 auto-generated index) must remain absent.
        """
        result = db_session.exec(
            text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'notification_delivery_attempt'
                  AND indexname = 'ix_notification_delivery_attempt_notification_outbox_id'
            """)
        ).all()

        assert len(result) == 0, "Old ix_* indexes should have been dropped"


# ==================== PHASE 2: Idempotency Unique Constraints Tests ====================


class TestIdempotencyUniqueConstraints:
    """Test Phase 5.3 Phase 2: Idempotency unique constraints enforcement."""

    def test_invoice_tenant_number_uniqueness_constraint_exists(
        self, db_session: Session
    ):
        """Verify uq_invoice_tenant_number constraint exists."""
        result = db_session.exec(
            text("""
                SELECT constraint_name, constraint_type
                FROM information_schema.table_constraints
                WHERE table_name = 'invoice'
                  AND constraint_name = 'uq_invoice_tenant_number'
            """)
        ).first()

        assert result is not None, (
            "Unique constraint uq_invoice_tenant_number should exist"
        )
        assert result[1] == "UNIQUE", "Constraint should be UNIQUE type"

    def test_invoice_tenant_idempotency_constraint_exists(self, db_session: Session):
        """Verify uq_invoice_tenant_idempotency constraint exists."""
        result = db_session.exec(
            text("""
                SELECT constraint_name, constraint_type
                FROM information_schema.table_constraints
                WHERE table_name = 'invoice'
                  AND constraint_name = 'uq_invoice_tenant_idempotency'
            """)
        ).first()

        assert result is not None, (
            "Unique constraint uq_invoice_tenant_idempotency should exist"
        )
        assert result[1] == "UNIQUE", "Constraint should be UNIQUE type"

    def test_quote_tenant_idempotency_constraint_exists(self, db_session: Session):
        """Verify uq_quote_tenant_idempotency constraint exists."""
        result = db_session.exec(
            text("""
                SELECT constraint_name, constraint_type
                FROM information_schema.table_constraints
                WHERE table_name = 'quote'
                  AND constraint_name = 'uq_quote_tenant_idempotency'
            """)
        ).first()

        assert result is not None, (
            "Unique constraint uq_quote_tenant_idempotency should exist"
        )
        assert result[1] == "UNIQUE", "Constraint should be UNIQUE type"

    def test_payment_tenant_idempotency_constraint_exists(self, db_session: Session):
        """Verify uq_payment_tenant_idempotency constraint exists."""
        result = db_session.exec(
            text("""
                SELECT constraint_name, constraint_type
                FROM information_schema.table_constraints
                WHERE table_name = 'payment'
                  AND constraint_name = 'uq_payment_tenant_idempotency'
            """)
        ).first()

        assert result is not None, (
            "Unique constraint uq_payment_tenant_idempotency should exist"
        )
        assert result[1] == "UNIQUE", "Constraint should be UNIQUE type"


# ==================== PHASE 3: Index Standardization Tests ====================


class TestIndexStandardization:
    """Test Phase 5.3 Phase 3: Index naming standardization and new indexes."""

    def test_conversation_session_composite_index_exists(self, db_session: Session):
        """Verify idx_conv_session_tenant_user composite index exists."""
        result = db_session.exec(
            text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'conversation_session'
                  AND indexname = 'idx_conv_session_tenant_user'
            """)
        ).first()

        assert result is not None, (
            "Composite index idx_conv_session_tenant_user should exist"
        )

    def test_job_time_entry_indexes_standardized(self, db_session: Session):
        """Verify job_time_entry indexes use idx_jte_* naming and idx_jte_started_at exists."""
        # Check new idx_jte_* indexes exist
        expected_indexes = ["idx_jte_job", "idx_jte_user", "idx_jte_started_at"]

        for index_name in expected_indexes:
            result = db_session.exec(
                text(f"""
                    SELECT indexname
                    FROM pg_indexes
                    WHERE tablename = 'job_time_entry'
                      AND indexname = '{index_name}'
                """)
            ).first()
            assert result is not None, f"Index {index_name} should exist"

        # Check old ix_* indexes are removed
        old_indexes = db_session.exec(
            text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'job_time_entry'
                  AND (indexname = 'ix_job_time_entry_job_id'
                    OR indexname = 'ix_job_time_entry_user_id')
            """)
        ).all()

        assert len(old_indexes) == 0, (
            "Old ix_job_time_entry_* indexes should be removed"
        )

    def test_voice_command_log_indexes_standardized(self, db_session: Session):
        """Verify voice_command_log indexes use idx_voice_log_* naming."""
        # Check new idx_voice_log_* indexes exist
        expected_indexes = [
            "idx_voice_log_tenant_time",
            "idx_voice_log_intent",
            "idx_voice_log_latency",
        ]

        for index_name in expected_indexes:
            result = db_session.exec(
                text(f"""
                    SELECT indexname
                    FROM pg_indexes
                    WHERE tablename = 'voice_command_log'
                      AND indexname = '{index_name}'
                """)
            ).first()
            assert result is not None, f"Index {index_name} should exist"

        # Check old ix_* index is removed
        old_index = db_session.exec(
            text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'voice_command_log'
                  AND indexname = 'ix_voice_command_log_total_latency_ms'
            """)
        ).first()

        assert old_index is None, (
            "Old ix_voice_command_log_total_latency_ms index should be removed"
        )


# ==================== PHASE 4: discount_version Triggers Tests ====================


class TestDiscountVersionTriggers:
    """Test Phase 5.3 Phase 4: discount_version audit and immutability triggers."""

    def test_discount_version_audit_trigger_exists(self, db_session: Session):
        """Verify audit_discount_version_changes trigger exists."""
        result = db_session.exec(
            text("""
                SELECT t.tgname
                FROM pg_trigger t
                JOIN pg_class c ON t.tgrelid = c.oid
                WHERE c.relname = 'discount_version'
                  AND t.tgname = 'audit_discount_version_changes'
                  AND NOT t.tgisinternal
            """)
        ).first()

        assert result is not None, (
            "Audit trigger audit_discount_version_changes should exist"
        )

    def test_discount_version_immutability_trigger_exists(self, db_session: Session):
        """Verify trg_discount_version_guard_created_immutable trigger exists."""
        result = db_session.exec(
            text("""
                SELECT t.tgname
                FROM pg_trigger t
                JOIN pg_class c ON t.tgrelid = c.oid
                WHERE c.relname = 'discount_version'
                  AND t.tgname = 'trg_discount_version_guard_created_immutable'
                  AND NOT t.tgisinternal
            """)
        ).first()

        assert result is not None, (
            "Immutability trigger trg_discount_version_guard_created_immutable should exist"
        )

    def test_discount_version_audit_logging_works(
        self, db_session: Session, test_tenant, test_user
    ):
        """Verify discount_version changes are logged to audit.event table."""
        # Clear audit log for clean test
        db_session.exec(text("TRUNCATE TABLE audit.event CASCADE"))
        db_session.commit()

        # Create a discount version using f-string to avoid bind parameter issues
        tenant_id = str(test_tenant.id)
        user_id = str(test_user.id)

        db_session.execute(
            text(f"""
                INSERT INTO discount_version (tenant_id, code, pct_off, valid_period, created_by, created_at)
                VALUES ('{tenant_id}'::uuid, 'TEST_DISCOUNT', 10.000, tstzrange(now(), 'infinity'), '{user_id}'::uuid, now())
            """)
        )
        db_session.commit()

        # Check audit log for INSERT event (column is 'action' not 'operation')
        audit_events = db_session.exec(
            text("""
                SELECT action, entity_name
                FROM audit.event
                WHERE entity_name = 'discount_version'
                  AND action = 'INSERT'
            """)
        ).all()

        assert len(audit_events) > 0, (
            "Audit log should contain INSERT event for discount_version"
        )

    def test_discount_version_immutability_guard_works(
        self, db_session: Session, test_tenant, test_user
    ):
        """Verify created_at and created_by cannot be updated on discount_version."""
        # Create discount version using f-string
        tenant_id = str(test_tenant.id)
        user_id = str(test_user.id)

        result = db_session.execute(
            text(f"""
                INSERT INTO discount_version (tenant_id, code, amount_off_cents, valid_period, created_by, created_at)
                VALUES ('{tenant_id}'::uuid, 'IMMUTABLE_TEST', 5000, tstzrange(now(), 'infinity'), '{user_id}'::uuid, now())
                RETURNING id
            """)
        )
        version_id = result.first()[0]
        db_session.commit()

        # Attempt to update created_by - should fail due to immutability guard
        new_user_id = str(uuid.uuid4())
        with pytest.raises(IntegrityError) as exc_info:
            db_session.execute(
                text(f"""
                    UPDATE discount_version
                    SET created_by = '{new_user_id}'::uuid
                    WHERE id = {version_id}
                """)
            )
            db_session.commit()

        assert (
            "immutable" in str(exc_info.value).lower()
            or "guard" in str(exc_info.value).lower()
            or "created" in str(exc_info.value).lower()
        ), "Update should fail with immutability error"
