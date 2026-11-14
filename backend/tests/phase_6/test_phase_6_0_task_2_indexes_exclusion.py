"""
Test Suite: Phase 6.0 Task 2 - Partial Indexes & Exclusion Constraint Verification
Validates partial indexes, GiST exclusion constraint, and redundant index removal.

Reference: phase-6.0-db-schema-sync-10-plan.md - Task 2
"""

import uuid
from datetime import UTC, datetime

import pytest
from psycopg2.extras import DateTimeTZRange
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.catalog import SupplierItem, SupplierItemPrice, SupplierItemUom


@pytest.fixture
def supplier_item(db_session: Session, test_supplier, test_tenant):
    """Create a test supplier item for price testing"""
    # Create UOM first
    uom = SupplierItemUom(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        code="EA",
        name="Each",
        is_default=True,
        is_active=True,
    )
    db_session.add(uom)
    db_session.commit()
    db_session.refresh(uom)

    # Create supplier item
    item = SupplierItem(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        supplier_id=test_supplier.id,
        sku="TEST-SKU-001",
        name="Test Item",
        uom_id=uom.id,
        is_active=True,
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


class TestPartialIndexes:
    """Test partial index query performance and functionality"""

    def test_invoice_balance_partial_index_exists(self, db_session: Session):
        """Verify idx_invoice_balance index exists with correct WHERE clause"""
        result = db_session.execute(
            text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'invoice'
                AND indexname = 'idx_invoice_balance'
        """)
        )
        row = result.fetchone()
        assert row is not None, "idx_invoice_balance index should exist"
        assert "balance_due_cents > 0" in row[1], "Index should have WHERE clause"

    def test_job_expense_unbilled_partial_index_exists(self, db_session: Session):
        """Verify idx_job_expense_unbilled index exists with correct WHERE clause"""
        result = db_session.execute(
            text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'job_expense'
                AND indexname = 'idx_job_expense_unbilled'
        """)
        )
        row = result.fetchone()
        assert row is not None, "idx_job_expense_unbilled index should exist"
        assert "is_billable = true" in row[1], "Index should filter billable expenses"
        assert "invoice_line_id IS NULL" in row[1], (
            "Index should filter unbilled expenses"
        )

    def test_user_endpoint_primary_email_partial_index_exists(
        self, db_session: Session
    ):
        """Verify ux_user_email_primary unique partial index exists.

        NOTE (FIND-067): idx_user_endpoint_primary_email was dropped — it was an
        exact duplicate of ux_user_email_primary. This test now validates the
        canonical index that replaced it.
        """
        result = db_session.execute(
            text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'user_endpoint'
                AND indexname = 'ux_user_email_primary'
        """)
        )
        row = result.fetchone()
        assert row is not None, (
            "ux_user_email_primary index should exist (canonical replacement for dropped idx_user_endpoint_primary_email)"
        )
        assert "UNIQUE" in row[1], "Index should be unique"
        assert "channel" in row[1] and "email" in row[1], (
            "Index should filter email channel"
        )
        assert "is_primary = true" in row[1], "Index should filter primary endpoints"

    def test_user_endpoint_email_value_lower_partial_index_exists(
        self, db_session: Session
    ):
        """Verify ux_global_primary_email unique partial index exists.

        NOTE (FIND-067): idx_user_endpoint_email_value_lower was dropped — it was an
        exact duplicate of ux_global_primary_email. This test now validates the
        canonical index that replaced it.
        """
        result = db_session.execute(
            text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'user_endpoint'
                AND indexname = 'ux_global_primary_email'
        """)
        )
        row = result.fetchone()
        assert row is not None, (
            "ux_global_primary_email index should exist (canonical replacement for dropped idx_user_endpoint_email_value_lower)"
        )
        assert "UNIQUE" in row[1], "Index should be unique"
        assert "lower" in row[1], "Index should use lower() function"

    def test_integration_cred_expires_partial_index_exists(self, db_session: Session):
        """Verify idx_integration_cred_expires partial index exists"""
        result = db_session.execute(
            text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'integration_credential'
                AND indexname = 'idx_integration_cred_expires'
        """)
        )
        row = result.fetchone()
        assert row is not None, "idx_integration_cred_expires index should exist"
        assert "expires_at IS NOT NULL" in row[1], (
            "Index should filter non-null expiration"
        )


class TestGiSTExclusionConstraint:
    """Test temporal overlap prevention on supplier_item_price"""

    def test_supplier_item_price_exclusion_constraint_exists(self, db_session: Session):
        """Verify exclude_supplier_item_price_period_overlap constraint exists"""
        result = db_session.execute(
            text("""
            SELECT conname, pg_get_constraintdef(c.oid) as definition
            FROM pg_constraint c
            JOIN pg_class t ON c.conrelid = t.oid
            WHERE t.relname = 'supplier_item_price'
                AND c.contype = 'x'
                AND conname = 'exclude_supplier_item_price_period_overlap'
        """)
        )
        row = result.fetchone()
        assert row is not None, "Exclusion constraint should exist"
        assert "supplier_item_id" in row[1], "Constraint should check supplier_item_id"
        assert "valid_period" in row[1], "Constraint should check valid_period"
        assert "&&" in row[1], "Constraint should use overlap operator"

    def test_supplier_item_price_no_overlap_same_item(
        self, db_session: Session, supplier_item
    ):
        """Test that overlapping price periods for same item are rejected"""
        # Create first price period
        price1 = SupplierItemPrice(
            supplier_item_id=supplier_item.id,
            unit_price=100.00,
            valid_period=DateTimeTZRange(
                datetime(2026, 1, 1, tzinfo=UTC),
                datetime(2026, 6, 30, tzinfo=UTC),
            ),
        )
        db_session.add(price1)
        db_session.commit()

        # Attempt overlapping price period (should fail)
        price2 = SupplierItemPrice(
            supplier_item_id=supplier_item.id,
            unit_price=120.00,
            valid_period=DateTimeTZRange(
                datetime(2026, 3, 1, tzinfo=UTC),  # OVERLAPS with price1
                datetime(2026, 9, 30, tzinfo=UTC),
            ),
        )
        db_session.add(price2)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "exclude_supplier_item_price_period_overlap" in str(exc_info.value)
        db_session.rollback()

    def test_supplier_item_price_adjacent_periods_allowed(
        self, db_session: Session, supplier_item
    ):
        """Test that adjacent (non-overlapping) periods are allowed"""
        # Create first price period
        price1 = SupplierItemPrice(
            supplier_item_id=supplier_item.id,
            unit_price=100.00,
            valid_period=DateTimeTZRange(
                datetime(2026, 1, 1, tzinfo=UTC),
                datetime(2026, 6, 30, tzinfo=UTC),
                bounds="[)",  # Excludes upper bound
            ),
        )
        db_session.add(price1)
        db_session.commit()

        # Create adjacent price period (should succeed)
        price2 = SupplierItemPrice(
            supplier_item_id=supplier_item.id,
            unit_price=120.00,
            valid_period=DateTimeTZRange(
                datetime(2026, 6, 30, tzinfo=UTC),  # Starts where price1 ends
                datetime(2026, 12, 31, tzinfo=UTC),
                bounds="[)",
            ),
        )
        db_session.add(price2)
        db_session.commit()  # Should succeed

        # Verify both prices exist
        prices = db_session.exec(
            select(SupplierItemPrice).where(
                SupplierItemPrice.supplier_item_id == supplier_item.id
            )
        ).all()
        assert len(prices) == 2


class TestIndexRemoval:
    """Test redundant index removal"""

    def test_redundant_index_removed(self, db_session: Session):
        """Verify ix_conversation_message_session_id no longer exists"""
        result = db_session.execute(
            text("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'conversation_message'
                AND indexname = 'ix_conversation_message_session_id'
        """)
        )
        assert result.fetchone() is None, "Redundant index should be removed"

    def test_composite_index_still_exists(self, db_session: Session):
        """Verify composite index idx_conv_msg_session_time still exists"""
        result = db_session.execute(
            text("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'conversation_message'
                AND indexname = 'idx_conv_msg_session_time'
        """)
        )
        row = result.fetchone()
        assert row is not None, "Composite index should still exist"


class TestConstraintRename:
    """Test that exclusion constraint was renamed with standardized name"""

    def test_old_exclusion_constraint_removed(self, db_session: Session):
        """Verify sip_no_overlap constraint no longer exists"""
        result = db_session.execute(
            text("""
            SELECT conname
            FROM pg_constraint c
            JOIN pg_class t ON c.conrelid = t.oid
            WHERE t.relname = 'supplier_item_price'
                AND conname = 'sip_no_overlap'
        """)
        )
        assert result.fetchone() is None, "Old constraint should be removed"

    def test_new_exclusion_constraint_keeps_null_safety(self, db_session: Session):
        """Verify new constraint maintains NULL-safe COALESCE logic for tenant_id"""
        result = db_session.execute(
            text("""
            SELECT pg_get_constraintdef(c.oid) as definition
            FROM pg_constraint c
            JOIN pg_class t ON c.conrelid = t.oid
            WHERE t.relname = 'supplier_item_price'
                AND conname = 'exclude_supplier_item_price_period_overlap'
        """)
        )
        row = result.fetchone()
        assert row is not None
        # Constraint should maintain COALESCE and tenant_id for multi-tenancy
        assert "COALESCE" in row[0], (
            "Constraint should use COALESCE for NULL-safe comparison"
        )
        assert "tenant_id" in row[0], (
            "Constraint should check tenant_id for proper isolation"
        )
