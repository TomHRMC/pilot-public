"""
SD-06B Tests: Invoice dunning enhancements.

Tests:
1. test_overdue_invoice_filter_param — GET /invoices?overdue=true
2. test_dunning_skips_recently_reminded_invoice — throttle check
3. test_dunning_updates_reminder_count — reminder_count increments
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session, select

from app.models.billing import Invoice, InvoiceStatus
from tasks.dunning import _dunning_reminders_impl

pytestmark = [
    pytest.mark.domain_invoicing_billing,
    pytest.mark.unit,
]


@pytest.fixture
def dunning_tenant(db_session: Session, test_user):
    """
    Create a test tenant with created_by=test_user — required for dunning
    task to find the tenant owner.
    """
    from app.models.subscription import SubscriptionTier

    tier = db_session.exec(
        select(SubscriptionTier).where(SubscriptionTier.is_trial == True)
    ).first()
    if not tier:
        pytest.skip("Trial subscription tier not seeded — run alembic upgrade head")

    from app.models.core import Tenant

    tenant = Tenant(
        name=f"[TEST] Dunning SD-06 Tenant {uuid.uuid4().hex[:8]}",
        is_active=True,
        current_subscription_tier_id=tier.tier_id,
        created_by=test_user.id,
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


def _create_invoice_for_dunning(
    db: Session,
    tenant_id,
    due_offset_days: int,
    balance_due_cents: int = 50000,
    last_reminder_sent_at=None,
    reminder_count: int = 0,
) -> Invoice:
    """Create an overdue invoice with a globally-scoped status (null tenant)."""
    inv_status = db.exec(
        select(InvoiceStatus)
        .where(InvoiceStatus.tenant_id == None)
        .where(InvoiceStatus.code == "draft")
    ).first()
    if not inv_status:
        # Try tenant-scoped draft
        inv_status = db.exec(
            select(InvoiceStatus)
            .where(InvoiceStatus.tenant_id == tenant_id)
            .where(InvoiceStatus.code == "draft")
        ).first()
    if not inv_status:
        pytest.skip("No 'draft' invoice status seeded")

    from sqlalchemy import text

    customer_row = db.execute(
        text("SELECT id FROM public.customer WHERE tenant_id = :tid LIMIT 1"),
        {"tid": str(tenant_id)},
    ).first()

    site_row = None
    if customer_row:
        site_row = db.execute(
            text("SELECT id FROM public.site WHERE tenant_id = :tid LIMIT 1"),
            {"tid": str(tenant_id)},
        ).first()

    if not customer_row or not site_row:
        # If no customer/site, create minimal placeholder UUIDs — invoice just needs
        # valid FK refs but we're testing dunning logic, not invoice CRUD
        # We'll rely on existing test_tenant seed data
        pytest.skip("No customer/site seeded for dunning tenant — use test_tenant seed")

    now = datetime.now(UTC)
    invoice = Invoice(
        tenant_id=tenant_id,
        invoice_number=f"INV-D06-{uuid.uuid4().hex[:8].upper()}",
        customer_id=customer_row.id,
        site_id=site_row.id,
        status_id=inv_status.id,
        issued_at=now - timedelta(days=10),
        due_at=now + timedelta(days=due_offset_days),
        total_cents=balance_due_cents,
        balance_due_cents=balance_due_cents,
        subtotal_cents=balance_due_cents,
        last_reminder_sent_at=last_reminder_sent_at,
        reminder_count=reminder_count,
        is_active=True,
    )
    db.add(invoice)
    db.flush()
    return invoice


class TestOverdueInvoiceFilter:
    """SD-06B: GET /invoices?overdue=true filter param."""

    def test_overdue_invoice_filter_param(
        self, client, db_session: Session, second_tenant, mock_cognito_jwt
    ):
        """
        GET /invoices?overdue=true should return only invoices where
        due_at < now AND status NOT IN (paid, void, writeoff).
        Uses second_tenant to avoid interference from test_tenant seed data.
        """
        tenant_id = second_tenant.id

        # Get invoice status for second tenant
        inv_status = db_session.exec(
            select(InvoiceStatus)
            .where(InvoiceStatus.tenant_id == None)
            .where(InvoiceStatus.code == "issued")
        ).first()
        if not inv_status:
            inv_status = db_session.exec(
                select(InvoiceStatus)
                .where(InvoiceStatus.tenant_id == None)
                .where(InvoiceStatus.code == "draft")
            ).first()
        if not inv_status:
            pytest.skip("No invoice status seeded")

        from sqlalchemy import text

        customer_row = db_session.execute(
            text("SELECT id FROM public.customer WHERE tenant_id = :tid LIMIT 1"),
            {"tid": str(tenant_id)},
        ).first()
        site_row = None
        if customer_row:
            site_row = db_session.execute(
                text("SELECT id FROM public.site WHERE tenant_id = :tid LIMIT 1"),
                {"tid": str(tenant_id)},
            ).first()

        if not customer_row or not site_row:
            pytest.skip("second_tenant has no customer/site — seed it first")

        now = datetime.now(UTC)

        # Overdue invoice: due 5 days ago
        overdue = Invoice(
            tenant_id=tenant_id,
            invoice_number=f"INV-OVR-{uuid.uuid4().hex[:6].upper()}",
            customer_id=customer_row.id,
            site_id=site_row.id,
            status_id=inv_status.id,
            due_at=now - timedelta(days=5),
            issued_at=now - timedelta(days=10),
            total_cents=10000,
            balance_due_cents=10000,
            subtotal_cents=10000,
        )
        # Not-overdue invoice: due tomorrow
        not_overdue = Invoice(
            tenant_id=tenant_id,
            invoice_number=f"INV-NOOVR-{uuid.uuid4().hex[:6].upper()}",
            customer_id=customer_row.id,
            site_id=site_row.id,
            status_id=inv_status.id,
            due_at=now + timedelta(days=1),
            issued_at=now - timedelta(days=1),
            total_cents=10000,
            balance_due_cents=10000,
            subtotal_cents=10000,
        )
        db_session.add_all([overdue, not_overdue])
        db_session.commit()

        resp = client.get("/api/v1/invoices/?overdue=true")
        assert resp.status_code == 200
        data = resp.json()
        ids = [item["id"] for item in data["items"]]

        assert str(overdue.id) in ids, (
            "Overdue invoice must appear in ?overdue=true results"
        )
        assert str(not_overdue.id) not in ids, "Future-due invoice must NOT appear"


class TestDunningThrottleAndTracking:
    """SD-06B: Dunning throttle and reminder_count tracking."""

    def test_dunning_skips_recently_reminded_invoice(
        self, db_session: Session, dunning_tenant, test_user
    ):
        """
        Invoice reminded 1 hour ago should be skipped (throttle < 23h).
        """
        from sqlalchemy import text

        tenant_id = dunning_tenant.id

        inv_status = db_session.exec(
            select(InvoiceStatus)
            .where(InvoiceStatus.tenant_id == None)
            .where(InvoiceStatus.code == "draft")
        ).first()
        if not inv_status:
            pytest.skip("No 'draft' status seeded")

        # Insert a minimal customer/site for dunning_tenant
        db_session.execute(
            text("""
            INSERT INTO public.customer (id, tenant_id, type, display_name, created_at, updated_at)
            VALUES (gen_random_uuid(), :tid, 'company', 'SD06 Dunning Customer', NOW(), NOW())
        """),
            {"tid": str(tenant_id)},
        )
        customer_row = db_session.execute(
            text("SELECT id FROM public.customer WHERE tenant_id = :tid LIMIT 1"),
            {"tid": str(tenant_id)},
        ).first()

        # Get or insert lifecycle status for site
        site_lifecycle_row = db_session.execute(
            text(
                "SELECT id FROM public.site_lifecycle_status WHERE code = 'active' AND tenant_id IS NULL LIMIT 1"
            )
        ).first()
        if not site_lifecycle_row:
            pytest.skip("site_lifecycle_status 'active' not seeded")

        db_session.execute(
            text("""
            INSERT INTO public.site (id, tenant_id, customer_id, name, lifecycle_status_id, created_at, updated_at)
            VALUES (gen_random_uuid(), :tid, :cid, 'SD06 Dunning Site', :ls_id, NOW(), NOW())
        """),
            {
                "tid": str(tenant_id),
                "cid": str(customer_row.id),
                "ls_id": str(site_lifecycle_row.id),
            },
        )
        site_row = db_session.execute(
            text("SELECT id FROM public.site WHERE tenant_id = :tid LIMIT 1"),
            {"tid": str(tenant_id)},
        ).first()

        now = datetime.now(UTC)
        invoice = Invoice(
            tenant_id=tenant_id,
            invoice_number=f"INV-THROT-{uuid.uuid4().hex[:6].upper()}",
            customer_id=customer_row.id,
            site_id=site_row.id,
            status_id=inv_status.id,
            due_at=now - timedelta(days=2),
            issued_at=now - timedelta(days=10),
            total_cents=50000,
            balance_due_cents=50000,
            subtotal_cents=50000,
            last_reminder_sent_at=now - timedelta(hours=1),  # recently reminded
            reminder_count=1,
            is_active=True,
        )
        db_session.add(invoice)
        db_session.commit()
        invoice_id = invoice.id

        _dunning_reminders_impl(db_session)

        db_session.expire(invoice)
        refreshed = db_session.exec(
            select(Invoice).where(Invoice.id == invoice_id)
        ).first()
        assert refreshed.reminder_count == 1, (
            "reminder_count must NOT increase for a recently-reminded invoice"
        )

    def test_dunning_updates_reminder_count(
        self, db_session: Session, dunning_tenant, test_user
    ):
        """
        Overdue invoice with reminder_count=0 gets reminder_count=1
        and last_reminder_sent_at set after dunning run.
        """
        from sqlalchemy import text

        tenant_id = dunning_tenant.id

        inv_status = db_session.exec(
            select(InvoiceStatus)
            .where(InvoiceStatus.tenant_id == None)
            .where(InvoiceStatus.code == "draft")
        ).first()
        if not inv_status:
            pytest.skip("No 'draft' status seeded")

        # Insert customer + site for this dunning_tenant
        db_session.execute(
            text("""
            INSERT INTO public.customer (id, tenant_id, type, display_name, created_at, updated_at)
            VALUES (gen_random_uuid(), :tid, 'company', 'SD06 Reminder Customer', NOW(), NOW())
        """),
            {"tid": str(tenant_id)},
        )
        customer_row = db_session.execute(
            text("SELECT id FROM public.customer WHERE tenant_id = :tid LIMIT 1"),
            {"tid": str(tenant_id)},
        ).first()

        site_lifecycle_row = db_session.execute(
            text(
                "SELECT id FROM public.site_lifecycle_status WHERE code = 'active' AND tenant_id IS NULL LIMIT 1"
            )
        ).first()
        if not site_lifecycle_row:
            pytest.skip("site_lifecycle_status 'active' not seeded")

        db_session.execute(
            text("""
            INSERT INTO public.site (id, tenant_id, customer_id, name, lifecycle_status_id, created_at, updated_at)
            VALUES (gen_random_uuid(), :tid, :cid, 'SD06 Reminder Site', :ls_id, NOW(), NOW())
        """),
            {
                "tid": str(tenant_id),
                "cid": str(customer_row.id),
                "ls_id": str(site_lifecycle_row.id),
            },
        )
        site_row = db_session.execute(
            text("SELECT id FROM public.site WHERE tenant_id = :tid LIMIT 1"),
            {"tid": str(tenant_id)},
        ).first()

        now = datetime.now(UTC)
        invoice = Invoice(
            tenant_id=tenant_id,
            invoice_number=f"INV-COUNT-{uuid.uuid4().hex[:6].upper()}",
            customer_id=customer_row.id,
            site_id=site_row.id,
            status_id=inv_status.id,
            due_at=now - timedelta(days=2),  # 2 days overdue → exceeds threshold[0]=1
            issued_at=now - timedelta(days=10),
            total_cents=50000,
            balance_due_cents=50000,
            subtotal_cents=50000,
            last_reminder_sent_at=None,
            reminder_count=0,
            is_active=True,
        )
        db_session.add(invoice)
        db_session.commit()
        invoice_id = invoice.id

        _dunning_reminders_impl(db_session)

        db_session.expire(invoice)
        refreshed = db_session.exec(
            select(Invoice).where(Invoice.id == invoice_id)
        ).first()
        assert refreshed.reminder_count == 1, (
            f"reminder_count must be 1 after first dunning run, got {refreshed.reminder_count}"
        )
        assert refreshed.last_reminder_sent_at is not None, (
            "last_reminder_sent_at must be set after dunning run"
        )
