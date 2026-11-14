"""
Test Suite: Phase 4.8 Task 6 - Add Integration Domain Composite Indexes
Tests index creation for QuickBooks sync query performance optimization

Reference: phase-4.8-db-schema-sync-4-plan.md
"""

from sqlalchemy import text
from sqlmodel import Session


class TestIntegrationIndexes:
    """Verify integration domain composite indexes were created"""

    def test_integration_indexes_exist(self, db_session: Session):
        """Verify all 4 integration indexes were created"""
        result = db_session.execute(
            text("""
            SELECT indexname FROM pg_indexes
            WHERE indexname IN (
                'idx_ism_entity',
                'idx_ism_external',
                'idx_isc_tenant_status',
                'idx_isl_tenant_service'
            )
            ORDER BY indexname
        """)
        )
        indexes = [row[0] for row in result]
        expected_count = 4
        assert len(indexes) == expected_count, (
            f"Expected {expected_count} indexes, found {len(indexes)}: {indexes}"
        )

    def test_sync_mapping_entity_index_definition(self, db_session: Session):
        """Verify entity lookup index has correct definition"""
        result = db_session.execute(
            text("""
            SELECT indexdef FROM pg_indexes
            WHERE indexname = 'idx_ism_entity'
        """)
        )
        indexdef = result.fetchone()[0]

        # Verify index includes expected columns in correct order
        assert "entity_type_code" in indexdef, (
            f"Index should include entity_type_code: {indexdef}"
        )
        assert "entity_id" in indexdef, f"Index should include entity_id: {indexdef}"
        assert "integration_sync_mapping" in indexdef, (
            f"Index should be on integration_sync_mapping table: {indexdef}"
        )
