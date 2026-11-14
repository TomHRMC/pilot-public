"""
Test Suite: Phase 4.7 Task 1 - Convert customer.type from ENUM to TEXT
Tests ENUM → TEXT + CHECK constraint migration for customer.type field

Reference: phase-4.7-db-schema-sync-3-plan.md - Phase 1, Task 1
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.crm import Customer


class TestCustomerTypeEnumToText:
    """Test customer.type uses TEXT + CHECK constraint instead of ENUM"""

    def test_customer_type_person_valid(self, db_session: Session, test_tenant):
        """Valid 'person' type should be accepted"""
        customer = Customer(
            tenant_id=test_tenant.id, type="person", display_name="John Doe"
        )
        db_session.add(customer)
        db_session.commit()

        # Use select() with exec() - NOT query()
        result = db_session.exec(
            select(Customer).where(Customer.id == customer.id)
        ).first()
        assert result is not None
        assert result.type == "person"

    def test_customer_type_company_valid(self, db_session: Session, test_tenant):
        """Valid 'company' type should be accepted"""
        customer = Customer(
            tenant_id=test_tenant.id, type="company", display_name="Acme Corp"
        )
        db_session.add(customer)
        db_session.commit()

        result = db_session.exec(
            select(Customer).where(Customer.id == customer.id)
        ).first()
        assert result is not None
        assert result.type == "company"

    def test_customer_type_invalid_rejected(self, db_session: Session, test_tenant):
        """Invalid type value should be rejected by CHECK constraint"""
        customer = Customer(
            tenant_id=test_tenant.id,
            type="business",  # Invalid value
            display_name="Test Business",
        )
        db_session.add(customer)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "customer_type_chk" in str(exc_info.value)

        # Rollback to clean up failed transaction
        db_session.rollback()

    def test_customer_type_null_rejected(self, db_session: Session, test_tenant):
        """NULL type value should be rejected at DB level (NOT NULL constraint).

        NOTE: Customer.type has ORM default='person', so passing type=None via ORM
        coerces to 'person' before the DB INSERT. Raw SQL is required to actually
        deliver NULL to the column and verify the NOT NULL constraint fires.
        """
        import uuid as _uuid

        with pytest.raises(IntegrityError):
            db_session.execute(
                text(
                    "INSERT INTO customer (id, tenant_id, type, display_name, "
                    "  preferred_contact_channel, sms_opted_out, sms_opt_in_consent, "
                    "  is_active, created_at, updated_at) "
                    "VALUES (:id, :tid, NULL, 'Raw Null Test', "
                    "  'sms', false, false, true, now(), now())"
                ).bindparams(
                    id=str(_uuid.uuid4()),
                    tid=str(test_tenant.id),
                )
            )
            db_session.flush()

        db_session.rollback()

    def test_customer_type_is_text_not_enum(self, db_session: Session):
        """Verify database column is TEXT type, not ENUM"""
        # Query system catalog to verify column type
        result = db_session.execute(
            text(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name = 'customer' AND column_name = 'type'"
            )
        ).fetchone()

        # Should be 'text' not 'USER-DEFINED' (which indicates ENUM)
        assert result is not None
        assert result[0] == "text"

    def test_customer_type_enum_type_does_not_exist(self, db_session: Session):
        """Verify PostgreSQL ENUM type 'customertype' no longer exists"""
        result = db_session.execute(
            text("SELECT typname FROM pg_type WHERE typname = 'customertype'")
        ).fetchone()

        # Should return None (ENUM type dropped)
        assert result is None

    def test_customer_type_check_constraint_exists(self, db_session: Session):
        """Verify CHECK constraint exists and enforces correct values"""
        result = db_session.execute(
            text(
                "SELECT conname, pg_get_constraintdef(oid) "
                "FROM pg_constraint "
                "WHERE conname = 'customer_type_chk' AND conrelid = 'customer'::regclass"
            )
        ).fetchone()

        assert result is not None
        constraint_name, constraint_def = result
        assert constraint_name == "customer_type_chk"
        # Constraint should reference TEXT values, not ENUM
        assert "person" in constraint_def
        assert "company" in constraint_def
        assert "::text" in constraint_def  # Should use TEXT casting, not ::customertype
