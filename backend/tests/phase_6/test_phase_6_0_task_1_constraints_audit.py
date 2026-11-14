"""
Test Suite: Phase 6.0 Task 1 - Constraints & Audit Columns Verification
Validates multi-tenant constraints, business logic constraints, and audit columns.

Reference: phase-6.0-db-schema-sync-10-plan.md - Task 1
"""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.ai import ConversationSession
from app.models.billing import (
    InvoiceStatus,
    PaymentMethod,
    PaymentStatus,
    PaymentType,
    PspCustomer,
)
from app.models.catalog import (
    SupplierLifecycleStatus,
)
from app.models.core import User, UserPreference
from app.models.crm import CustomerLifecycleStatus
from app.models.fulfillment import JobStatus
from app.models.quoting import QuoteStatus


class TestMultiTenantUniqueConstraints:
    """Test multi-tenant unique constraints on lookup tables"""

    def test_customer_lifecycle_status_prevents_duplicate_codes(
        self, db_session: Session, test_tenant
    ):
        """Verify uq_customer_lifecycle_status_tenant_code constraint"""
        # Insert first status
        status1 = CustomerLifecycleStatus(
            tenant_id=test_tenant.id, code="ACTIVE", name="Active Customer"
        )
        db_session.add(status1)
        db_session.commit()

        # Attempt duplicate code within same tenant (should fail)
        status2 = CustomerLifecycleStatus(
            tenant_id=test_tenant.id, code="ACTIVE", name="Different Active"
        )
        db_session.add(status2)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "uq_customer_lifecycle_status_tenant_code" in str(exc_info.value)
        db_session.rollback()

    def test_customer_lifecycle_status_different_tenants_allowed(
        self, db_session: Session, test_tenant, second_tenant
    ):
        """Test that same code across different tenants is allowed"""
        status1 = CustomerLifecycleStatus(
            tenant_id=test_tenant.id, code="ACTIVE", name="Active"
        )
        status2 = CustomerLifecycleStatus(
            tenant_id=second_tenant.id, code="ACTIVE", name="Active"
        )
        db_session.add(status1)
        db_session.add(status2)
        db_session.commit()

        # Should succeed - different tenants
        assert status1.id != status2.id

    def test_job_status_tenant_code_prevents_duplicates(
        self, db_session: Session, test_tenant
    ):
        """Verify uq_job_status_tenant_code constraint"""
        status1 = JobStatus(
            tenant_id=test_tenant.id, code="PENDING", name="Pending Review"
        )
        db_session.add(status1)
        db_session.commit()

        status2 = JobStatus(
            tenant_id=test_tenant.id, code="PENDING", name="Pending Approval"
        )
        db_session.add(status2)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "uq_job_status_tenant_code" in str(exc_info.value)
        db_session.rollback()

    def test_invoice_status_tenant_code_prevents_duplicates(
        self, db_session: Session, test_tenant
    ):
        """Verify uq_invoice_status_tenant_code constraint"""
        status1 = InvoiceStatus(tenant_id=test_tenant.id, code="DRAFT", name="Draft")
        db_session.add(status1)
        db_session.commit()

        status2 = InvoiceStatus(tenant_id=test_tenant.id, code="DRAFT", name="Draft v2")
        db_session.add(status2)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "uq_invoice_status_tenant_code" in str(exc_info.value)
        db_session.rollback()

    def test_payment_status_tenant_code_prevents_duplicates(
        self, db_session: Session, test_tenant
    ):
        """Verify uq_payment_status_tenant_code constraint"""
        status1 = PaymentStatus(
            tenant_id=test_tenant.id, code="PENDING", name="Pending"
        )
        db_session.add(status1)
        db_session.commit()

        status2 = PaymentStatus(
            tenant_id=test_tenant.id, code="PENDING", name="Pending v2"
        )
        db_session.add(status2)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "uq_payment_status_tenant_code" in str(exc_info.value)
        db_session.rollback()

    def test_payment_type_tenant_code_prevents_duplicates(
        self, db_session: Session, test_tenant
    ):
        """Verify uq_payment_type_tenant_code constraint"""
        type1 = PaymentType(tenant_id=test_tenant.id, code="CARD", name="Card")
        db_session.add(type1)
        db_session.commit()

        type2 = PaymentType(tenant_id=test_tenant.id, code="CARD", name="Card v2")
        db_session.add(type2)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "uq_payment_type_tenant_code" in str(exc_info.value)
        db_session.rollback()

    def test_quote_status_tenant_code_prevents_duplicates(
        self, db_session: Session, test_tenant
    ):
        """Verify uq_quote_status_tenant_code constraint"""
        status1 = QuoteStatus(tenant_id=test_tenant.id, code="DRAFT", name="Draft")
        db_session.add(status1)
        db_session.commit()

        status2 = QuoteStatus(tenant_id=test_tenant.id, code="DRAFT", name="Draft v2")
        db_session.add(status2)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "uq_quote_status_tenant_code" in str(exc_info.value)
        db_session.rollback()

    def test_supplier_lifecycle_status_tenant_code_prevents_duplicates(
        self, db_session: Session, test_tenant
    ):
        """Verify uq_supplier_lifecycle_status_tenant_code constraint"""
        status1 = SupplierLifecycleStatus(
            tenant_id=test_tenant.id, code="ACTIVE", name="Active"
        )
        db_session.add(status1)
        db_session.commit()

        status2 = SupplierLifecycleStatus(
            tenant_id=test_tenant.id, code="ACTIVE", name="Active v2"
        )
        db_session.add(status2)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "uq_supplier_lifecycle_status_tenant_code" in str(exc_info.value)
        db_session.rollback()


class TestBusinessLogicUniqueConstraints:
    """Test business logic unique constraints"""

    def test_payment_method_psp_uniqueness(self, db_session: Session, test_tenant):
        """Verify uq_payment_method_tenant_psp constraint"""
        # Create payment type first
        payment_type = PaymentType(
            tenant_id=test_tenant.id, code="CARD", name="Credit Card"
        )
        db_session.add(payment_type)
        db_session.commit()

        # First payment method
        method1 = PaymentMethod(
            tenant_id=test_tenant.id,
            payment_type_id=payment_type.id,
            psp_provider="stripe",
            psp_payment_method_id="pm_12345",
        )
        db_session.add(method1)
        db_session.commit()

        # Attempt duplicate PSP payment method (should fail)
        method2 = PaymentMethod(
            tenant_id=test_tenant.id,
            payment_type_id=payment_type.id,
            psp_provider="stripe",
            psp_payment_method_id="pm_12345",
        )
        db_session.add(method2)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "uq_payment_method_tenant_psp" in str(exc_info.value)
        db_session.rollback()

    def test_psp_customer_uniqueness(
        self, db_session: Session, test_tenant, test_customer
    ):
        """Verify uq_psp_customer_provider_id constraint"""
        # First PSP customer
        psp_cust1 = PspCustomer(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            psp_provider="stripe",
            psp_customer_id="cus_12345",
        )
        db_session.add(psp_cust1)
        db_session.commit()

        # Attempt duplicate PSP customer (should fail)
        psp_cust2 = PspCustomer(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            psp_provider="stripe",
            psp_customer_id="cus_12345",
        )
        db_session.add(psp_cust2)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "uq_psp_customer_provider_id" in str(exc_info.value)
        db_session.rollback()

    def test_user_preference_uniqueness(
        self, db_session: Session, test_tenant, test_user
    ):
        """Verify uq_user_preference_user_tenant constraint"""
        from sqlmodel import select as sqlm_select

        # SD-6: Remove seeded user_preference for test_user+test_tenant so we can test
        # the uniqueness constraint cleanly (insert first, then fail duplicate)
        existing = db_session.exec(
            sqlm_select(UserPreference)
            .where(UserPreference.user_id == test_user.id)
            .where(UserPreference.tenant_id == test_tenant.id)
        ).first()
        if existing:
            db_session.delete(existing)
            db_session.commit()

        # First preference
        pref1 = UserPreference(
            user_id=test_user.id,
            tenant_id=test_tenant.id,
            preferences={"theme": "dark"},
        )
        db_session.add(pref1)
        db_session.commit()

        # Attempt duplicate preference for same user-tenant (should fail)
        pref2 = UserPreference(
            user_id=test_user.id,
            tenant_id=test_tenant.id,
            preferences={"theme": "light"},
        )
        db_session.add(pref2)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "uq_user_preference_user_tenant" in str(exc_info.value)
        db_session.rollback()

    def test_user_email_uniqueness(self, db_session: Session):
        """Verify uq_user_email constraint (or existing ix_user_email index)"""
        # First user
        user1 = User(email="test@example.com", first_name="Test", last_name="User")
        db_session.add(user1)
        db_session.commit()

        # Attempt duplicate email (should fail)
        user2 = User(email="test@example.com", first_name="Another", last_name="User")
        db_session.add(user2)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        # Accept either the new constraint or the existing unique index
        error_str = str(exc_info.value)
        assert "uq_user_email" in error_str or "ix_user_email" in error_str
        db_session.rollback()


class TestAuditColumns:
    """Test audit columns on conversation_session"""

    def test_conversation_session_audit_columns_nullable(
        self, db_session: Session, test_tenant, test_user
    ):
        """Verify created_by and updated_by are nullable and accessible"""
        session = ConversationSession(
            tenant_id=test_tenant.id, user_id=test_user.id, status="active"
        )
        db_session.add(session)
        db_session.commit()

        # Audit columns should be None by default
        assert session.created_by is None
        assert session.updated_by is None

    def test_conversation_session_audit_columns_writable(
        self, db_session: Session, test_tenant, test_user
    ):
        """Verify created_by and updated_by can be set"""
        # Phase 6.0.1: Must use valid user ID due to FK constraints
        session = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(session)
        db_session.commit()

        # Re-fetch to verify persisted
        fetched = db_session.exec(
            select(ConversationSession).where(ConversationSession.id == session.id)
        ).first()

        assert fetched.created_by == test_user.id
        assert fetched.updated_by == test_user.id

    def test_conversation_session_audit_columns_updatable(
        self, db_session: Session, test_tenant, test_user
    ):
        """Verify created_by and updated_by can be updated"""
        session = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
            created_by=test_user.id,
        )
        db_session.add(session)
        db_session.commit()

        # Phase 6.0.1: Update audit column with valid user ID (FK constraint enforced)
        session.updated_by = test_user.id
        db_session.commit()

        # Re-fetch to verify
        fetched = db_session.exec(
            select(ConversationSession).where(ConversationSession.id == session.id)
        ).first()

        assert fetched.created_by == test_user.id
        assert fetched.updated_by == test_user.id
