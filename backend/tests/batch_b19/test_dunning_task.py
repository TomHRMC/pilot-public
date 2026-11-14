"""
Tests for B19/FIND-069: Dunning reminders Celery task.

Covers the dunning_reminders task which identifies overdue invoices
and enqueues notification_outbox rows for tenant owners.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session, select

from app.models.billing import Invoice, InvoiceStatus
from app.models.core import Tenant, User
from app.models.crm import Customer, Site
from app.models.system import NotificationOutbox
from tasks.dunning import _dunning_reminders_impl


@pytest.fixture
def dunning_test_tenant(db_session: Session, test_user: User):
    """
    Create a tenant with created_by set to test_user for dunning tests.
    This allows the dunning task to find a tenant owner.
    """
    from app.models.subscription import SubscriptionTier

    # Get the trial tier ID
    tier = db_session.exec(
        select(SubscriptionTier).where(SubscriptionTier.is_trial == True)
    ).first()
    if not tier:
        raise RuntimeError(
            "Trial subscription tier not seeded. Run: alembic upgrade head"
        )

    tenant = Tenant(
        name="[TEST] Dunning Test Tenant",
        is_active=True,
        current_subscription_tier_id=tier.tier_id,
        created_by=test_user.id,
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


class TestDunningRemindersTask:
    """Test the _dunning_reminders_impl function (inner impl, no Celery)."""

    def _create_customer(self, db_session: Session, tenant: Tenant, name: str):
        """Helper to create a customer for tests."""
        customer = Customer(
            tenant_id=tenant.id,
            type="person",
            display_name=name,
            first_name="Test",
            last_name="Customer",
        )
        db_session.add(customer)
        db_session.flush()
        return customer

    def _create_site(self, db_session: Session, tenant: Tenant, customer: Customer):
        """Helper to create a site for tests."""
        site = Site(
            tenant_id=tenant.id,
            customer_id=customer.id,
            name=f"Site for {customer.display_name}",
        )
        db_session.add(site)
        db_session.flush()
        return site

    def _create_invoice_status(self, db_session: Session, tenant: Tenant):
        """Helper to create invoice status if not already present."""
        status = db_session.exec(
            select(InvoiceStatus)
            .where(InvoiceStatus.tenant_id == tenant.id)
            .where(InvoiceStatus.code == "draft")
        ).first()
        if not status:
            status = InvoiceStatus(
                tenant_id=tenant.id,
                code="draft",
                name="Draft",
                is_terminal=False,
                is_default=True,
            )
            db_session.add(status)
            db_session.flush()
        return status

    def test_overdue_invoice_creates_email_notification(
        self, db_session: Session, dunning_test_tenant: Tenant, test_user: User
    ):
        """
        ARRANGE: Create an invoice that is 5 days overdue with balance > 0.
        ACT: Run _dunning_reminders_impl.
        ASSERT: One email notification created for the tenant owner.
        """
        now = datetime.now(UTC)
        due_at = now - timedelta(days=5)

        customer = self._create_customer(
            db_session, dunning_test_tenant, "Overdue Customer 1"
        )
        site = self._create_site(db_session, dunning_test_tenant, customer)
        status = self._create_invoice_status(db_session, dunning_test_tenant)

        invoice = Invoice(
            tenant_id=dunning_test_tenant.id,
            invoice_number="INV-001",
            customer_id=customer.id,
            site_id=site.id,
            status_id=status.id,
            issued_at=now - timedelta(days=10),
            due_at=due_at,
            balance_due_cents=50000,
            total_cents=50000,
            is_active=True,
        )
        db_session.add(invoice)
        db_session.commit()

        _dunning_reminders_impl(db_session)

        # Rule 16: test_tenant has overdue seed invoices — assert on tenant-scoped results only
        email_notif = db_session.exec(
            select(NotificationOutbox)
            .where(NotificationOutbox.tenant_id == dunning_test_tenant.id)
            .where(NotificationOutbox.channel == "email")
            .where(NotificationOutbox.recipient_user_id == test_user.id)
        ).first()
        assert email_notif is not None
        assert "INV-001" in email_notif.body
        assert "5 days overdue" in email_notif.body
        assert "$500" in email_notif.body
        assert email_notif.category_id == "billing"

    def test_overdue_invoice_creates_inapp_notification(
        self, db_session: Session, dunning_test_tenant: Tenant, test_user: User
    ):
        """
        ARRANGE: Create an overdue invoice.
        ACT: Run _dunning_reminders_impl.
        ASSERT: One in-app notification created for the tenant owner.
        """
        now = datetime.now(UTC)
        due_at = now - timedelta(days=3)

        customer = self._create_customer(
            db_session, dunning_test_tenant, "Overdue Customer 2"
        )
        site = self._create_site(db_session, dunning_test_tenant, customer)
        status = self._create_invoice_status(db_session, dunning_test_tenant)

        invoice = Invoice(
            tenant_id=dunning_test_tenant.id,
            invoice_number="INV-002",
            customer_id=customer.id,
            site_id=site.id,
            status_id=status.id,
            issued_at=now - timedelta(days=5),
            due_at=due_at,
            balance_due_cents=25000,
            total_cents=25000,
            is_active=True,
        )
        db_session.add(invoice)
        db_session.commit()

        result = _dunning_reminders_impl(db_session)

        inapp_notif = db_session.exec(
            select(NotificationOutbox)
            .where(NotificationOutbox.tenant_id == dunning_test_tenant.id)
            .where(NotificationOutbox.channel == "in_app")
            .where(NotificationOutbox.recipient_user_id == test_user.id)
        ).first()
        assert inapp_notif is not None
        assert "INV-002" in inapp_notif.body
        assert "3 days overdue" in inapp_notif.body
        assert "$250" in inapp_notif.body

    def test_paid_invoice_does_not_trigger_notification(
        self, db_session: Session, dunning_test_tenant: Tenant, test_user: User
    ):
        """
        ARRANGE: Create an invoice marked as paid (balance_due_cents = 0).
        ACT: Run _dunning_reminders_impl.
        ASSERT: No notifications created (invoice is paid).
        """
        now = datetime.now(UTC)
        due_at = now - timedelta(days=7)

        customer = self._create_customer(
            db_session, dunning_test_tenant, "Paid Customer"
        )
        site = self._create_site(db_session, dunning_test_tenant, customer)
        status = self._create_invoice_status(db_session, dunning_test_tenant)

        invoice = Invoice(
            tenant_id=dunning_test_tenant.id,
            invoice_number="INV-PAID",
            customer_id=customer.id,
            site_id=site.id,
            status_id=status.id,
            issued_at=now - timedelta(days=15),
            due_at=due_at,
            balance_due_cents=0,
            total_cents=50000,
            is_active=True,
        )
        db_session.add(invoice)
        db_session.commit()

        _dunning_reminders_impl(db_session)

        # Rule 16: test_tenant has overdue seed invoices so global count > 0.
        # Assert that no notifications were created for dunning_test_tenant (paid invoice)
        notifs_for_this_tenant = db_session.exec(
            select(NotificationOutbox).where(
                NotificationOutbox.tenant_id == dunning_test_tenant.id
            )
        ).all()
        assert len(notifs_for_this_tenant) == 0

    def test_multiple_overdue_invoices(
        self, db_session: Session, dunning_test_tenant: Tenant, test_user: User
    ):
        """
        ARRANGE: Create 3 overdue invoices.
        ACT: Run _dunning_reminders_impl.
        ASSERT: 3 overdue invoices detected, 6 notifications created (2 per invoice).
        """
        now = datetime.now(UTC)
        status = self._create_invoice_status(db_session, dunning_test_tenant)

        for i in range(1, 4):
            customer = self._create_customer(
                db_session, dunning_test_tenant, f"Customer {i}"
            )
            site = self._create_site(db_session, dunning_test_tenant, customer)

            invoice = Invoice(
                tenant_id=dunning_test_tenant.id,
                invoice_number=f"INV-{i}",
                customer_id=customer.id,
                site_id=site.id,
                status_id=status.id,
                issued_at=now - timedelta(days=10),
                due_at=now - timedelta(days=i),
                balance_due_cents=10000 * i,
                total_cents=10000 * i,
                is_active=True,
            )
            db_session.add(invoice)
        db_session.commit()

        _dunning_reminders_impl(db_session)

        # Check by tenant-scoped notification count (global count may include other tenants'
        # overdue seed invoices — Rule 16: test must be resilient to test_tenant seed data)
        notifs = db_session.exec(
            select(NotificationOutbox).where(
                NotificationOutbox.tenant_id == dunning_test_tenant.id
            )
        ).all()
        assert len(notifs) == 6  # 3 invoices × 2 channels = 6 for this specific tenant
        for notif in notifs:
            assert notif.category_id == "billing"
