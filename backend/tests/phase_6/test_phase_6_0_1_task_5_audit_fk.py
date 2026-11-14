"""
Test Suite: Phase 6.0.1 Task 5 - Billing & Payments Audit FK Constraints

Validates Foreign Key constraint enforcement on created_by and updated_by columns
for 18 billing and payment-related tables.

Reference: dev-docs/analysis/phase-6.0-db-schema-sync-11-plan.md - Task 5
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.models.billing import (
    Invoice,
    InvoiceStatus,
    Payment,
    PaymentMethod,
    PaymentStatus,
    PaymentType,
    ProductFeature,
    ProductPlan,
    Subscription,
    SubscriptionStatus,
    UsageLedger,
)
from app.models.core import Tenant, User
from app.models.crm import Customer, Site


class TestAuditFKConstraintsCreatedBy:
    """Test FK constraint enforcement on created_by column"""

    def test_invoice_created_by_fk_enforcement(
        self,
        db_session: Session,
        test_tenant: Tenant,
        test_customer: Customer,
        test_site: Site,
    ):
        """Test that invalid created_by user ID is rejected for invoice"""
        invoice_status = InvoiceStatus(
            tenant_id=test_tenant.id,
            code="DRAFT",
            name="Draft",
        )
        db_session.add(invoice_status)
        db_session.commit()

        invalid_user_id = uuid.uuid4()
        invoice = Invoice(
            tenant_id=test_tenant.id,
            invoice_number="INV-001",
            customer_id=test_customer.id,
            site_id=test_site.id,
            status_id=invoice_status.id,
            created_by=invalid_user_id,
        )
        db_session.add(invoice)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_invoice_created_by" in str(exc_info.value).lower()
        db_session.rollback()

    def test_payment_created_by_fk_enforcement(
        self,
        db_session: Session,
        test_tenant: Tenant,
        test_customer: Customer,
        test_site: Site,
    ):
        """Test that invalid created_by user ID is rejected for payment"""
        # Create required objects
        invoice_status = InvoiceStatus(
            tenant_id=test_tenant.id, code="SENT", name="Sent"
        )
        db_session.add(invoice_status)
        db_session.flush()

        invoice = Invoice(
            tenant_id=test_tenant.id,
            invoice_number="INV-002",
            customer_id=test_customer.id,
            site_id=test_site.id,
            status_id=invoice_status.id,
        )
        db_session.add(invoice)
        db_session.flush()

        payment_type = PaymentType(
            tenant_id=test_tenant.id, code="CC", name="Credit Card"
        )
        db_session.add(payment_type)
        db_session.flush()

        payment_method = PaymentMethod(
            tenant_id=test_tenant.id,
            payment_type_id=payment_type.id,
            psp_provider="stripe",
            psp_payment_method_id="pm_test",
        )
        db_session.add(payment_method)
        db_session.flush()

        payment_status = PaymentStatus(
            tenant_id=test_tenant.id, code="PENDING", name="Pending"
        )
        db_session.add(payment_status)
        db_session.flush()

        invalid_user_id = uuid.uuid4()
        payment = Payment(
            tenant_id=test_tenant.id,
            invoice_id=invoice.id,
            amount_cents=10000,
            payment_method_id=payment_method.id,
            status_id=payment_status.id,
            created_by=invalid_user_id,
        )
        db_session.add(payment)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_payment_created_by" in str(exc_info.value).lower()
        db_session.rollback()

    def test_subscription_created_by_fk_enforcement(
        self, db_session: Session, test_tenant: Tenant
    ):
        """Test that invalid created_by user ID is rejected for subscription"""
        # Create required objects
        product_plan = ProductPlan(code="BASIC", name="Basic Plan")
        db_session.add(product_plan)
        db_session.flush()

        subscription_status = SubscriptionStatus(
            tenant_id=test_tenant.id, code="ACTIVE", name="Active"
        )
        db_session.add(subscription_status)
        db_session.flush()

        invalid_user_id = uuid.uuid4()
        subscription = Subscription(
            tenant_id=test_tenant.id,
            product_plan_code=product_plan.code,
            status_id=subscription_status.id,
            created_by=invalid_user_id,
        )
        db_session.add(subscription)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_subscription_created_by" in str(exc_info.value).lower()
        db_session.rollback()


class TestAuditFKConstraintsUpdatedBy:
    """Test FK constraint enforcement on updated_by column"""

    def test_invoice_updated_by_fk_enforcement(
        self,
        db_session: Session,
        test_tenant: Tenant,
        test_user: User,
        test_customer: Customer,
        test_site: Site,
    ):
        """Test that invalid updated_by user ID is rejected for invoice"""
        invoice_status = InvoiceStatus(
            tenant_id=test_tenant.id,
            code="DRAFT",
            name="Draft",
        )
        db_session.add(invoice_status)
        db_session.commit()

        invoice = Invoice(
            tenant_id=test_tenant.id,
            invoice_number="INV-003",
            customer_id=test_customer.id,
            site_id=test_site.id,
            status_id=invoice_status.id,
            created_by=test_user.id,
        )
        db_session.add(invoice)
        db_session.commit()

        # Try to update with invalid user ID
        invalid_user_id = uuid.uuid4()
        invoice.updated_by = invalid_user_id

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_invoice_updated_by" in str(exc_info.value).lower()
        db_session.rollback()

    def test_payment_method_updated_by_fk_enforcement(
        self, db_session: Session, test_tenant: Tenant, test_user: User
    ):
        """Test that invalid updated_by user ID is rejected for payment_method"""
        payment_type = PaymentType(
            tenant_id=test_tenant.id, code="CC", name="Credit Card"
        )
        db_session.add(payment_type)
        db_session.flush()

        payment_method = PaymentMethod(
            tenant_id=test_tenant.id,
            payment_type_id=payment_type.id,
            psp_provider="stripe",
            psp_payment_method_id="pm_test2",
            created_by=test_user.id,
        )
        db_session.add(payment_method)
        db_session.commit()

        # Try to update with invalid user ID
        invalid_user_id = uuid.uuid4()
        payment_method.updated_by = invalid_user_id

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        assert "fk_payment_method_updated_by" in str(exc_info.value).lower()
        db_session.rollback()


class TestUserDeletionPrevention:
    """Test that users with audit references cannot be deleted (ON DELETE RESTRICT)"""

    def test_user_deletion_blocked_by_invoice_audit(
        self,
        db_session: Session,
        test_tenant: Tenant,
        test_user: User,
        test_customer: Customer,
        test_site: Site,
    ):
        """Test that user cannot be deleted if invoice references exist"""
        invoice_status = InvoiceStatus(
            tenant_id=test_tenant.id, code="SENT", name="Sent"
        )
        db_session.add(invoice_status)
        db_session.flush()

        invoice = Invoice(
            tenant_id=test_tenant.id,
            invoice_number="INV-004",
            customer_id=test_customer.id,
            site_id=test_site.id,
            status_id=invoice_status.id,
            created_by=test_user.id,
        )
        db_session.add(invoice)
        db_session.commit()

        # Attempt to delete user (should fail due to RESTRICT)
        db_session.delete(test_user)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        # User deletion is blocked by FK constraints (validates ON DELETE RESTRICT works)
        assert "foreignkeyviolation" in str(exc_info.value).lower()
        assert "user" in str(exc_info.value).lower()
        db_session.rollback()

    def test_user_deletion_blocked_by_subscription_audit(
        self, db_session: Session, test_tenant: Tenant, test_user: User
    ):
        """Test that user cannot be deleted if subscription references exist"""
        product_plan = ProductPlan(code="PRO", name="Pro Plan")
        db_session.add(product_plan)
        db_session.flush()

        subscription_status = SubscriptionStatus(
            tenant_id=test_tenant.id, code="ACTIVE", name="Active"
        )
        db_session.add(subscription_status)
        db_session.flush()

        subscription = Subscription(
            tenant_id=test_tenant.id,
            product_plan_code=product_plan.code,
            status_id=subscription_status.id,
            created_by=test_user.id,
        )
        db_session.add(subscription)
        db_session.commit()

        # Attempt to delete user (should fail due to RESTRICT)
        db_session.delete(test_user)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        # User deletion is blocked by FK constraints (validates ON DELETE RESTRICT works)
        assert "foreignkeyviolation" in str(exc_info.value).lower()
        assert "user" in str(exc_info.value).lower()
        db_session.rollback()


class TestNullAuditColumnsAllowed:
    """Test backward compatibility with NULL audit columns"""

    def test_invoice_null_audit_columns(
        self,
        db_session: Session,
        test_tenant: Tenant,
        test_customer: Customer,
        test_site: Site,
    ):
        """Test that NULL created_by and updated_by are allowed for invoice"""
        invoice_status = InvoiceStatus(
            tenant_id=test_tenant.id, code="DRAFT", name="Draft"
        )
        db_session.add(invoice_status)
        db_session.flush()

        invoice = Invoice(
            tenant_id=test_tenant.id,
            invoice_number="INV-005",
            customer_id=test_customer.id,
            site_id=test_site.id,
            status_id=invoice_status.id,
            created_by=None,
            updated_by=None,
        )
        db_session.add(invoice)
        db_session.commit()

        assert invoice.created_by is None
        assert invoice.updated_by is None

    def test_payment_null_audit_columns(
        self,
        db_session: Session,
        test_tenant: Tenant,
        test_customer: Customer,
        test_site: Site,
    ):
        """Test that NULL created_by and updated_by are allowed for payment"""
        invoice_status = InvoiceStatus(
            tenant_id=test_tenant.id, code="SENT", name="Sent"
        )
        db_session.add(invoice_status)
        db_session.flush()

        invoice = Invoice(
            tenant_id=test_tenant.id,
            invoice_number="INV-006",
            customer_id=test_customer.id,
            site_id=test_site.id,
            status_id=invoice_status.id,
        )
        db_session.add(invoice)
        db_session.flush()

        payment_type = PaymentType(tenant_id=test_tenant.id, code="CASH", name="Cash")
        db_session.add(payment_type)
        db_session.flush()

        payment_method = PaymentMethod(
            tenant_id=test_tenant.id,
            payment_type_id=payment_type.id,
            psp_provider="manual",
            psp_payment_method_id="pm_cash",
        )
        db_session.add(payment_method)
        db_session.flush()

        payment_status = PaymentStatus(
            tenant_id=test_tenant.id, code="COMPLETED", name="Completed"
        )
        db_session.add(payment_status)
        db_session.flush()

        payment = Payment(
            tenant_id=test_tenant.id,
            invoice_id=invoice.id,
            amount_cents=5000,
            payment_method_id=payment_method.id,
            status_id=payment_status.id,
            created_by=None,
            updated_by=None,
        )
        db_session.add(payment)
        db_session.commit()

        assert payment.created_by is None
        assert payment.updated_by is None

    def test_subscription_null_audit_columns(
        self, db_session: Session, test_tenant: Tenant
    ):
        """Test that NULL created_by and updated_by are allowed for subscription"""
        product_plan = ProductPlan(code="ENTERPRISE", name="Enterprise Plan")
        db_session.add(product_plan)
        db_session.flush()

        subscription_status = SubscriptionStatus(
            tenant_id=test_tenant.id, code="TRIAL", name="Trial"
        )
        db_session.add(subscription_status)
        db_session.flush()

        subscription = Subscription(
            tenant_id=test_tenant.id,
            product_plan_code=product_plan.code,
            status_id=subscription_status.id,
            created_by=None,
            updated_by=None,
        )
        db_session.add(subscription)
        db_session.commit()

        assert subscription.created_by is None
        assert subscription.updated_by is None

    def test_usage_ledger_null_created_by(
        self, db_session: Session, test_tenant: Tenant
    ):
        """Test that NULL created_by is allowed for append-only usage_ledger"""
        product_feature = ProductFeature(code="QUOTES", name="Quotes", unit="count")
        db_session.add(product_feature)
        db_session.flush()

        usage_ledger = UsageLedger(
            tenant_id=test_tenant.id,
            product_feature_code=product_feature.code,
            idempotency_key=f"test-{uuid.uuid4()}",
            created_by=None,
        )
        db_session.add(usage_ledger)
        db_session.commit()

        assert usage_ledger.created_by is None


class TestValidAuditReferences:
    """Test that valid user references work correctly"""

    def test_invoice_with_valid_created_by(
        self,
        db_session: Session,
        test_tenant: Tenant,
        test_user: User,
        test_customer: Customer,
        test_site: Site,
    ):
        """Test that valid created_by user ID is accepted for invoice"""
        invoice_status = InvoiceStatus(
            tenant_id=test_tenant.id, code="DRAFT", name="Draft"
        )
        db_session.add(invoice_status)
        db_session.flush()

        invoice = Invoice(
            tenant_id=test_tenant.id,
            invoice_number="INV-008",
            customer_id=test_customer.id,
            site_id=test_site.id,
            status_id=invoice_status.id,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(invoice)
        db_session.commit()

        # Verify the audit fields
        assert invoice.created_by == test_user.id
        assert invoice.updated_by == test_user.id

    def test_subscription_with_valid_audit_fields(
        self, db_session: Session, test_tenant: Tenant, test_user: User
    ):
        """Test that valid audit user IDs are accepted for subscription"""
        product_plan = ProductPlan(code="STARTER", name="Starter Plan")
        db_session.add(product_plan)
        db_session.flush()

        subscription_status = SubscriptionStatus(
            tenant_id=test_tenant.id, code="ACTIVE", name="Active"
        )
        db_session.add(subscription_status)
        db_session.flush()

        subscription = Subscription(
            tenant_id=test_tenant.id,
            product_plan_code=product_plan.code,
            status_id=subscription_status.id,
            created_by=test_user.id,
            updated_by=test_user.id,
        )
        db_session.add(subscription)
        db_session.commit()

        # Verify the audit fields
        assert subscription.created_by == test_user.id
        assert subscription.updated_by == test_user.id
