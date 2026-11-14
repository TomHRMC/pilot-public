"""
Test Suite: Phase 4.7 Task 3 - Fix tax_rate_version_id FK Type Mismatches
Tests BIGINT FK capacity for tax rate version references - final schema alignment for production deployment

Reference: phase-4.7-db-schema-sync-3-plan.md
"""

from sqlalchemy import text
from sqlmodel import Session


class TestTaxRateVersionIdBigintCapacity:
    """Test that all tax_rate_version_id FKs can handle BIGINT values"""

    def test_verify_quote_line_tax_component_column_is_bigint(
        self, db_session: Session
    ):
        """Verify quote_line_tax_component.tax_rate_version_id is BIGINT"""
        query = text("""
            SELECT data_type, numeric_precision
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'quote_line_tax_component'
              AND column_name = 'tax_rate_version_id'
        """)

        result = db_session.exec(query).first()
        assert result is not None
        assert result[0] == "bigint", f"Expected bigint, got {result[0]}"
        assert result[1] == 64, f"Expected 64-bit precision, got {result[1]}"

    def test_verify_invoice_line_tax_component_column_is_bigint(
        self, db_session: Session
    ):
        """Verify invoice_line_tax_component.tax_rate_version_id is BIGINT"""
        query = text("""
            SELECT data_type, numeric_precision
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'invoice_line_tax_component'
              AND column_name = 'tax_rate_version_id'
        """)

        result = db_session.exec(query).first()
        assert result is not None
        assert result[0] == "bigint", f"Expected bigint, got {result[0]}"
        assert result[1] == 64, f"Expected 64-bit precision, got {result[1]}"

    def test_verify_change_order_line_tax_component_column_is_bigint(
        self, db_session: Session
    ):
        """Verify change_order_line_tax_component.tax_rate_version_id is BIGINT"""
        query = text("""
            SELECT data_type, numeric_precision
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'change_order_line_tax_component'
              AND column_name = 'tax_rate_version_id'
        """)

        result = db_session.exec(query).first()
        assert result is not None
        assert result[0] == "bigint", f"Expected bigint, got {result[0]}"
        assert result[1] == 64, f"Expected 64-bit precision, got {result[1]}"

    def test_verify_all_three_columns_are_bigint(self, db_session: Session):
        """Verify all 3 FK columns are BIGINT type with 64-bit precision"""
        query = text("""
            SELECT 
              table_name,
              column_name,
              data_type,
              numeric_precision
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND column_name = 'tax_rate_version_id'
              AND table_name IN (
                'quote_line_tax_component',
                'invoice_line_tax_component',
                'change_order_line_tax_component'
              )
            ORDER BY table_name
        """)

        result = db_session.exec(query).all()

        # Should return 3 rows, all with data_type = 'bigint' and precision = 64
        assert len(result) == 3, f"Expected 3 columns, found {len(result)}"

        for row in result:
            table_name, column_name, data_type, precision = row
            assert data_type == "bigint", (
                f"{table_name}.{column_name} should be bigint, got {data_type}"
            )
            assert precision == 64, (
                f"{table_name}.{column_name} should have 64-bit precision, got {precision}"
            )

    def test_verify_foreign_key_constraints_exist(self, db_session: Session):
        """Verify FK constraints to tax_rate_version table still exist after migration"""
        query = text("""
            SELECT 
              tc.table_name,
              kcu.column_name,
              ccu.table_name AS foreign_table_name,
              ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
              AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = 'public'
              AND kcu.column_name = 'tax_rate_version_id'
              AND tc.table_name IN (
                'quote_line_tax_component',
                'invoice_line_tax_component',
                'change_order_line_tax_component'
              )
            ORDER BY tc.table_name
        """)

        result = db_session.exec(query).all()

        # Should return 3 FK constraints
        assert len(result) == 3, f"Expected 3 FK constraints, found {len(result)}"

        for row in result:
            table_name, column_name, foreign_table, foreign_column = row
            assert foreign_table == "tax_rate_version", (
                f"{table_name}.{column_name} should reference tax_rate_version, got {foreign_table}"
            )
            assert foreign_column == "id", (
                f"{table_name}.{column_name} should reference id column, got {foreign_column}"
            )

    def test_verify_parent_table_id_is_bigint(self, db_session: Session):
        """Verify parent table tax_rate_version.id is also BIGINT"""
        query = text("""
            SELECT data_type, numeric_precision
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'tax_rate_version'
              AND column_name = 'id'
        """)

        result = db_session.exec(query).first()
        assert result is not None
        assert result[0] == "bigint", f"Parent PK should be bigint, got {result[0]}"
        assert result[1] == 64, (
            f"Parent PK should have 64-bit precision, got {result[1]}"
        )
