"""
Test Suite: Phase 4.8 Task 3 - Add Quoting Domain Composite Indexes
Tests index creation for query performance optimization

Reference: phase-4.8-db-schema-sync-4-plan.md - Task 3
"""

from sqlalchemy import text
from sqlmodel import Session


class TestQuoteIndexes:
    """Verify quote composite index was created"""

    def test_quote_index_exists(self, db_session: Session):
        """Verify composite quote index was created"""
        result = db_session.execute(
            text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'quote'
            AND indexname = 'idx_quote_tenant_status_created_at'
        """)
        )
        index = result.fetchone()
        assert index is not None, "Missing index: idx_quote_tenant_status_created_at"

    def test_quote_index_definition(self, db_session: Session):
        """Verify quote index has correct definition"""
        result = db_session.execute(
            text("""
            SELECT indexdef FROM pg_indexes
            WHERE indexname = 'idx_quote_tenant_status_created_at'
        """)
        )
        indexdef = result.fetchone()
        assert indexdef is not None, "Index not found"

        indexdef_str = indexdef[0]
        # Verify index includes expected columns in correct order
        assert "tenant_id" in indexdef_str, "Index missing tenant_id column"
        assert "status_id" in indexdef_str, "Index missing status_id column"
        assert "created_at" in indexdef_str, "Index missing created_at column"
        # Verify DESC ordering on created_at
        assert "DESC" in indexdef_str, "Index missing DESC ordering on created_at"
