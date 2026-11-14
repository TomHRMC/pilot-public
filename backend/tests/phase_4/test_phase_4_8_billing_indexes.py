"""
Test Suite: Phase 4.8 Task 4 - Add Billing Domain Composite Indexes
Tests index creation for billing query performance optimization

Reference: phase-4.8-db-schema-sync-4-plan.md
"""

from sqlalchemy import text
from sqlmodel import Session


class TestBillingIndexes:
    """Verify billing domain composite indexes were created"""

    def test_billing_indexes_exist(self, db_session: Session):
        """Verify all 5 billing indexes were created"""
        result = db_session.execute(
            text("""
            SELECT indexname FROM pg_indexes
            WHERE indexname IN (
                'idx_invoice_status_due_at',
                'idx_invoice_created_at',
                'idx_su_tenant_product_feature_period',
                'idx_ul_subscription_product_feature_time',
                'idx_usage_ledger_unreported'
            )
            ORDER BY indexname
        """)
        )
        indexes = [row[0] for row in result]
        expected_count = 5
        assert len(indexes) == expected_count, (
            f"Expected {expected_count} indexes, found {len(indexes)}: {indexes}"
        )

    def test_usage_ledger_unreported_partial_index(self, db_session: Session):
        """Verify unreported usage partial index has WHERE clause"""
        result = db_session.execute(
            text("""
            SELECT indexdef FROM pg_indexes
            WHERE indexname = 'idx_usage_ledger_unreported'
        """)
        )
        indexdef = result.fetchone()[0]

        # Verify partial index includes WHERE clause
        assert "WHERE" in indexdef
        assert "is_reported = false" in indexdef or "is_reported = 'false'" in indexdef

        # Verify index includes expected columns
        assert "tenant_id" in indexdef
        assert "product_feature_code" in indexdef
