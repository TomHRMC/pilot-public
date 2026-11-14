"""
Test Suite: Phase 4.8 Task 8 - Add Payment Domain Composite Index
Tests index creation for payment transaction log query performance optimization

Reference: dev-docs/analysis/phase-4.8-db-schema-sync-4-plan.md - Phase 2, Task 8
Authority: dev-docs/db-design/aevofab-db-schema-v2.6h.json

This test suite verifies the composite index for payment transaction log queries:
- idx_psp_tx_log_tenant_time: Optimizes tenant-scoped time-ordered transaction history

Common Query Pattern:
SELECT * FROM psp_transaction_log
WHERE tenant_id = '...'
ORDER BY created_at DESC
LIMIT 100;
"""

from sqlalchemy import text
from sqlmodel import Session


class TestPaymentIndexes:
    """Verify payment domain composite index was created"""

    def test_payment_index_exists(self, db_session: Session):
        """Verify psp_transaction_log tenant+time index was created"""
        result = db_session.execute(
            text("""
            SELECT indexname FROM pg_indexes
            WHERE tablename = 'psp_transaction_log'
            AND indexname = 'idx_psp_tx_log_tenant_time'
        """)
        )
        index = result.fetchone()
        assert index is not None, "Missing index: idx_psp_tx_log_tenant_time"

    def test_payment_index_definition(self, db_session: Session):
        """Verify index has correct column order (tenant_id, created_at DESC)"""
        result = db_session.execute(
            text("""
            SELECT indexdef FROM pg_indexes
            WHERE indexname = 'idx_psp_tx_log_tenant_time'
        """)
        )
        indexdef = result.fetchone()[0]

        # Verify index includes expected columns in correct order
        assert "tenant_id" in indexdef, "Index should include tenant_id"
        assert "created_at" in indexdef, "Index should include created_at"

        # Verify DESC ordering is present
        # PostgreSQL shows DESC explicitly in the index definition
        assert "DESC" in indexdef, "Index should have DESC ordering on created_at"

        # Verify correct column order: tenant_id appears before created_at
        tenant_pos = indexdef.index("tenant_id")
        created_pos = indexdef.index("created_at")
        assert tenant_pos < created_pos, (
            "tenant_id should appear before created_at in index definition"
        )
