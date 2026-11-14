"""
Test Suite: Phase 6.0.1 Task 4 - Quoting System Audit FK Constraints

Validates Foreign Key constraint enforcement on created_by and updated_by columns
for all quoting-related tables.

Reference: dev-docs/analysis/phase-6.0-db-schema-sync-11-plan.md - Task 4
Migration: 2026_04_13_2056-d25bd8d5f87e_phase_6_0_1_task_4_fk_audit_quoting.py

Scope: 12 tables in quoting.py
- 7 tables with BOTH created_by AND updated_by FKs (14 constraints)
- 5 tables with ONLY created_by FK (5 constraints)
- Total: 19 Foreign Key constraints
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.models.core import User
from app.models.quoting import (
    PricebookItem,
    PricebookItemVersion,
    QuoteLinkStatus,
    QuoteStatus,
)


class TestQuotingAuditFKConstraintsCreatedBy:
    """Test FK constraint enforcement on created_by column"""

    def test_quote_status_created_by_fk_enforcement(
        self, db_session: Session, test_tenant
    ):
        """Test that invalid created_by user ID is rejected for QuoteStatus"""
        invalid_user_id = uuid.uuid4()
        status = QuoteStatus(
            tenant_id=test_tenant.id,
            code="TEST_INVALID",
            name="Test Invalid",
            created_by=invalid_user_id,
        )
        db_session.add(status)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_quote_status_created_by" in str(exc_info.value)
        db_session.rollback()

    def test_pricebook_item_created_by_fk_enforcement(
        self, db_session: Session, test_tenant
    ):
        """Test that invalid created_by user ID is rejected for PricebookItem"""
        invalid_user_id = uuid.uuid4()
        item = PricebookItem(
            tenant_id=test_tenant.id,
            sku="TEST-INVALID",
            name="Test Invalid",
            created_by=invalid_user_id,
        )
        db_session.add(item)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_pricebook_item_created_by" in str(exc_info.value)
        db_session.rollback()

    def test_quote_link_status_created_by_fk_enforcement(
        self, db_session: Session, test_tenant
    ):
        """Test that invalid created_by user ID is rejected for QuoteLinkStatus"""
        invalid_user_id = uuid.uuid4()
        status = QuoteLinkStatus(
            tenant_id=test_tenant.id,
            code="TEST_INVALID",
            name="Test Invalid",
            created_by=invalid_user_id,
        )
        db_session.add(status)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_quote_link_status_created_by" in str(exc_info.value)
        db_session.rollback()


class TestQuotingAuditFKConstraintsUpdatedBy:
    """Test FK constraint enforcement on updated_by column"""

    def test_quote_status_updated_by_fk_enforcement(
        self, db_session: Session, test_tenant, test_user
    ):
        """Test that invalid updated_by user ID is rejected for QuoteStatus"""
        # Create valid quote status
        status = QuoteStatus(
            tenant_id=test_tenant.id,
            code="TEST_VALID",
            name="Test Valid",
            created_by=test_user.id,
        )
        db_session.add(status)
        db_session.commit()

        # Attempt update with invalid user ID
        invalid_user_id = uuid.uuid4()
        status.updated_by = invalid_user_id

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_quote_status_updated_by" in str(exc_info.value)
        db_session.rollback()

    def test_pricebook_item_updated_by_fk_enforcement(
        self, db_session: Session, test_tenant, test_user
    ):
        """Test that invalid updated_by user ID is rejected for PricebookItem"""
        # Create valid pricebook item
        item = PricebookItem(
            tenant_id=test_tenant.id,
            sku="TEST-VALID",
            name="Test Valid",
            created_by=test_user.id,
        )
        db_session.add(item)
        db_session.commit()

        # Attempt update with invalid user ID
        invalid_user_id = uuid.uuid4()
        item.updated_by = invalid_user_id

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_pricebook_item_updated_by" in str(exc_info.value)
        db_session.rollback()


class TestUserDeletionPrevention:
    """Test that users with audit references cannot be deleted (ON DELETE RESTRICT)"""

    def test_user_deletion_blocked_by_pricebook_item_audit(
        self, db_session: Session, test_tenant
    ):
        """Test ON DELETE RESTRICT behavior for PricebookItem"""
        # Create a dedicated user for this test
        test_user_local = User(
            email=f"pricebook_test_{uuid.uuid4()}@example.com",
            hashed_password="hashed",
        )
        db_session.add(test_user_local)
        db_session.commit()

        # Create pricebook item with user audit reference
        item = PricebookItem(
            tenant_id=test_tenant.id,
            sku=f"TEST-RESTRICT-{uuid.uuid4()}",
            name="Test Restrict",
            created_by=test_user_local.id,
        )
        db_session.add(item)
        db_session.commit()

        # Attempt to delete user
        db_session.delete(test_user_local)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_pricebook_item_created_by" in str(exc_info.value)
        db_session.rollback()

    def test_user_deletion_blocked_by_quote_status_audit(
        self, db_session: Session, test_tenant
    ):
        """Test ON DELETE RESTRICT behavior for QuoteStatus"""
        # Create a dedicated user for this test
        test_user_local = User(
            email=f"quote_status_test_{uuid.uuid4()}@example.com",
            hashed_password="hashed",
        )
        db_session.add(test_user_local)
        db_session.commit()

        # Create quote status with user audit reference
        status = QuoteStatus(
            tenant_id=test_tenant.id,
            code=f"TEST-{uuid.uuid4()}",
            name="Test Restrict",
            created_by=test_user_local.id,
        )
        db_session.add(status)
        db_session.commit()

        # Attempt to delete user
        db_session.delete(test_user_local)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_quote_status_created_by" in str(exc_info.value)
        db_session.rollback()


class TestNullAuditColumnsAllowed:
    """Test backward compatibility with NULL audit columns"""

    def test_pricebook_item_null_audit_columns(self, db_session: Session, test_tenant):
        """Test that NULL created_by and updated_by are allowed for PricebookItem"""
        item = PricebookItem(
            tenant_id=test_tenant.id,
            sku="TEST-NULL",
            name="Test NULL",
            created_by=None,
            updated_by=None,
        )
        db_session.add(item)
        db_session.commit()

        assert item.created_by is None
        assert item.updated_by is None

    def test_quote_status_null_audit_columns(self, db_session: Session, test_tenant):
        """Test that NULL created_by and updated_by are allowed for QuoteStatus"""
        status = QuoteStatus(
            tenant_id=test_tenant.id,
            code="TEST-NULL",
            name="Test NULL",
            created_by=None,
            updated_by=None,
        )
        db_session.add(status)
        db_session.commit()

        assert status.created_by is None
        assert status.updated_by is None


class TestAppendOnlyTables:
    """Test created_by-only FK enforcement for versioned/append-only tables"""

    def test_pricebook_item_version_created_by_fk(
        self, db_session: Session, test_tenant, test_user
    ):
        """Test that PricebookItemVersion has created_by FK but no updated_by"""
        # First create a pricebook item
        item = PricebookItem(
            tenant_id=test_tenant.id,
            sku="TEST-VERSION",
            name="Test Version",
            created_by=test_user.id,
        )
        db_session.add(item)
        db_session.commit()

        # Valid creation with created_by
        version = PricebookItemVersion(
            tenant_id=test_tenant.id,
            pricebook_item_id=item.id,
            default_unit_price_cents=1000,
            valid_period="[2024-01-01,)",
            created_by=test_user.id,
        )
        db_session.add(version)
        db_session.commit()

        # Verify created_by is set
        assert hasattr(version, "created_by")
        assert version.created_by == test_user.id
        # PricebookItemVersion should not have updated_by (append-only)
        assert not hasattr(version, "updated_by")

    def test_pricebook_item_version_invalid_created_by_rejected(
        self, db_session: Session, test_tenant, test_user
    ):
        """Test that invalid created_by user ID is rejected for PricebookItemVersion"""
        # First create a pricebook item
        item = PricebookItem(
            tenant_id=test_tenant.id,
            sku="TEST-VERSION-2",
            name="Test Version 2",
            created_by=test_user.id,
        )
        db_session.add(item)
        db_session.commit()

        # Attempt with invalid user ID
        invalid_user_id = uuid.uuid4()
        version = PricebookItemVersion(
            tenant_id=test_tenant.id,
            pricebook_item_id=item.id,
            default_unit_price_cents=1000,
            valid_period="[2024-01-01,)",
            created_by=invalid_user_id,
        )
        db_session.add(version)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_pricebook_item_version_created_by" in str(exc_info.value)
        db_session.rollback()


class TestValidReferences:
    """Test that valid user references work correctly"""

    def test_pricebook_item_with_valid_audit_columns(
        self, db_session: Session, test_tenant, test_user
    ):
        """Test that PricebookItem with valid audit columns succeeds"""
        item = PricebookItem(
            tenant_id=test_tenant.id,
            sku="TEST-VALID-AUDIT",
            name="Test Valid Audit",
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(item)
        db_session.commit()

        assert item.created_by == test_user.id
        assert item.updated_by == test_user.id

    def test_quote_status_with_valid_audit_columns(
        self, db_session: Session, test_tenant, test_user
    ):
        """Test that QuoteStatus with valid audit columns succeeds"""
        status = QuoteStatus(
            tenant_id=test_tenant.id,
            code="TEST-VALID-2",
            name="Test Valid 2",
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(status)
        db_session.commit()

        assert status.created_by == test_user.id
        assert status.updated_by == test_user.id
