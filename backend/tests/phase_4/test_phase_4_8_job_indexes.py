"""
Test Suite: Phase 4.8 Task 5 - Add Job/Fulfillment Domain Composite Indexes
Tests index creation for job domain query performance optimization

Reference: phase-4.8-db-schema-sync-4-plan.md - Task 5
"""

from sqlalchemy import text
from sqlmodel import Session


class TestJobIndexes:
    """Verify job domain composite indexes were created"""

    def test_job_indexes_exist(self, db_session: Session):
        """Verify both job domain indexes were created"""
        result = db_session.execute(
            text("""
            SELECT indexname FROM pg_indexes
            WHERE indexname IN (
                'idx_job_tenant_status_created_at',
                'idx_job_expense_tenant'
            )
            ORDER BY indexname
        """)
        )
        indexes = [row[0] for row in result]
        expected_count = 2
        assert len(indexes) == expected_count, (
            f"Expected {expected_count} indexes, found {len(indexes)}: {indexes}"
        )

    def test_job_tenant_status_index_definition(self, db_session: Session):
        """Verify job index has correct column order and DESC sorting"""
        result = db_session.execute(
            text("""
            SELECT indexdef FROM pg_indexes
            WHERE indexname = 'idx_job_tenant_status_created_at'
        """)
        )
        row = result.fetchone()
        assert row is not None, "idx_job_tenant_status_created_at index not found"

        indexdef = row[0]
        # Verify index includes expected columns in correct order
        assert "tenant_id" in indexdef
        assert "status_id" in indexdef
        assert "created_at" in indexdef
        # Verify DESC ordering on created_at
        assert "DESC" in indexdef

    def test_job_expense_index_definition(self, db_session: Session):
        """Verify job_expense index has correct column order and DESC sorting"""
        result = db_session.execute(
            text("""
            SELECT indexdef FROM pg_indexes
            WHERE indexname = 'idx_job_expense_tenant'
        """)
        )
        row = result.fetchone()
        assert row is not None, "idx_job_expense_tenant index not found"

        indexdef = row[0]
        # Verify index includes expected columns
        assert "tenant_id" in indexdef
        assert "incurred_at" in indexdef
        # Verify DESC ordering on incurred_at
        assert "DESC" in indexdef
