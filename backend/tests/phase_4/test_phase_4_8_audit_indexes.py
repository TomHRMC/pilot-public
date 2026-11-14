"""
Test Suite: Phase 4.8 Task 2 - Add Audit Domain Composite Indexes
Tests index creation for audit log query performance optimization

Reference: phase-4.8-db-schema-sync-4-plan.md - Task 2
"""

from sqlalchemy import text
from sqlmodel import Session


class TestAuditIndexes:
    """Verify audit.event composite indexes were created"""

    def test_audit_indexes_exist(self, db_session: Session):
        """Verify all 3 audit indexes were created"""
        result = db_session.execute(
            text("""
            SELECT indexname FROM pg_indexes
            WHERE schemaname = 'audit' 
              AND tablename = 'event'
              AND indexname IN (
                'idx_audit_event_tenant_time',
                'idx_audit_event_entity_search',
                'idx_audit_event_user_action_time'
            )
            ORDER BY indexname
        """)
        )
        indexes = [row[0] for row in result]
        expected_count = 3
        assert len(indexes) == expected_count, (
            f"Expected {expected_count} indexes, found {len(indexes)}: {indexes}"
        )

    def test_audit_tenant_time_index_definition(self, db_session: Session):
        """Verify tenant time index has correct definition"""
        result = db_session.execute(
            text("""
            SELECT indexdef FROM pg_indexes
            WHERE schemaname = 'audit'
              AND tablename = 'event'
              AND indexname = 'idx_audit_event_tenant_time'
        """)
        )
        row = result.fetchone()
        assert row is not None, "Index idx_audit_event_tenant_time not found"

        indexdef = row[0]
        # Verify index includes expected columns
        assert "tenant_id" in indexdef
        assert "occurred_at" in indexdef
        # Verify DESC ordering on occurred_at
        assert "occurred_at DESC" in indexdef

    def test_audit_entity_search_index_definition(self, db_session: Session):
        """Verify entity search index has correct definition"""
        result = db_session.execute(
            text("""
            SELECT indexdef FROM pg_indexes
            WHERE schemaname = 'audit'
              AND tablename = 'event'
              AND indexname = 'idx_audit_event_entity_search'
        """)
        )
        row = result.fetchone()
        assert row is not None, "Index idx_audit_event_entity_search not found"

        indexdef = row[0]
        # Verify index includes expected columns
        assert "entity_name" in indexdef
        assert "entity_id" in indexdef
        assert "occurred_at" in indexdef
        # Verify DESC ordering on occurred_at
        assert "occurred_at DESC" in indexdef

    def test_audit_user_action_time_index_definition(self, db_session: Session):
        """Verify user action time index has correct definition"""
        result = db_session.execute(
            text("""
            SELECT indexdef FROM pg_indexes
            WHERE schemaname = 'audit'
              AND tablename = 'event'
              AND indexname = 'idx_audit_event_user_action_time'
        """)
        )
        row = result.fetchone()
        assert row is not None, "Index idx_audit_event_user_action_time not found"

        indexdef = row[0]
        # Verify index includes expected columns
        assert "user_id" in indexdef
        assert "action" in indexdef
        assert "occurred_at" in indexdef
        # Verify DESC ordering on occurred_at
        assert "occurred_at DESC" in indexdef
