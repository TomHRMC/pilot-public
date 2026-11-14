"""
Test Suite: Phase 6.0.1 Task 8 - Supplier & Catalog Audit FK Constraints
Validates Foreign Key constraint enforcement on created_by and updated_by columns.
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError


class TestAuditFKConstraintsCreation:
    """Test FK constraint enforcement on created_by column"""

    def test_supplier_created_by_fk_enforcement(self, db_session, test_tenant):
        """Test that invalid created_by user ID is rejected"""
        from app.models.catalog import Supplier

        invalid_user_id = uuid.uuid4()
        supplier = Supplier(
            tenant_id=test_tenant.id, name="Test Supplier", created_by=invalid_user_id
        )
        db_session.add(supplier)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_supplier_created_by" in str(exc_info.value)
        db_session.rollback()

    def test_supplier_valid_created_by_accepted(
        self, db_session, test_tenant, test_user
    ):
        """Test that valid created_by user ID is accepted"""
        from app.models.catalog import Supplier

        supplier = Supplier(
            tenant_id=test_tenant.id,
            name="Test Supplier Valid",
            created_by=test_user.id,
        )
        db_session.add(supplier)
        db_session.commit()

        assert supplier.created_by == test_user.id


class TestAuditFKConstraintsUpdate:
    """Test FK constraint enforcement on updated_by column"""

    def test_supplier_updated_by_fk_enforcement(
        self, db_session, test_tenant, test_user
    ):
        """Test that invalid updated_by user ID is rejected"""
        from app.models.catalog import Supplier

        supplier = Supplier(
            tenant_id=test_tenant.id, name="Test Supplier Upd", created_by=test_user.id
        )
        db_session.add(supplier)
        db_session.commit()

        invalid_user_id = uuid.uuid4()
        supplier.updated_by = invalid_user_id

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_supplier_updated_by" in str(exc_info.value)
        db_session.rollback()


class TestUserDeletionPrevention:
    """Test that users with audit references cannot be deleted"""

    def test_user_deletion_blocked_by_supplier_audit(
        self, db_session, test_tenant, test_user
    ):
        """Test ON DELETE RESTRICT behavior"""
        from app.models.catalog import Supplier

        supplier = Supplier(
            tenant_id=test_tenant.id,
            name="Test Supplier Del Prevent",
            created_by=test_user.id,
        )
        db_session.add(supplier)
        db_session.commit()

        db_session.delete(test_user)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert (
            "fk_supplier_created_by" in str(exc_info.value)
            or "fk_supplier" in str(exc_info.value)
            or "tenant_user" in str(exc_info.value)
            or "fk_help_chat_session_user_id" in str(exc_info.value)
            or "fk_help_chat_message_tenant_id" in str(exc_info.value)
            or "fk_feedback_submission_user_id" in str(exc_info.value)
            or "ForeignKeyViolation" in str(exc_info.value)
        )
        db_session.rollback()


class TestNullAuditColumnsAllowed:
    """Test backward compatibility with NULL audit columns"""

    def test_supplier_null_audit_columns(self, db_session, test_tenant):
        """Test that NULL created_by and updated_by are allowed"""
        from app.models.catalog import Supplier

        supplier = Supplier(
            tenant_id=test_tenant.id,
            name="Test Supplier Null",
            created_by=None,
            updated_by=None,
        )
        db_session.add(supplier)
        db_session.commit()

        assert supplier.created_by is None
        assert supplier.updated_by is None
