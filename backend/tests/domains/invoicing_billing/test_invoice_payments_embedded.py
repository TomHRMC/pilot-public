"""
UI-FIX-1A Tests: InvoiceResponse.payments embedded field (FIX-013-BE).

Tests:
1. test_get_invoice_includes_payments_field — GET invoice returns 'payments' list (empty ok)
2. test_get_invoice_includes_existing_payments — payments populated when payment exists
3. test_get_invoice_payments_tenant_scoped — tenant A's invoice returns 404 for tenant B
"""

import uuid

import pytest
from sqlalchemy import text
from sqlmodel import Session, select

from app.models.billing import (
    Invoice,
    InvoiceStatus,
    Payment,
    PaymentMethod,
    PaymentStatus,
    PaymentType,
)

pytestmark = [
    pytest.mark.domain_invoicing_billing,
    pytest.mark.unit,
]


def _get_or_skip_issued_status(db: Session) -> InvoiceStatus:
    status = db.exec(
        select(InvoiceStatus)
        .where(InvoiceStatus.tenant_id == None)
        .where(InvoiceStatus.code == "issued")
    ).first()
    if not status:
        pytest.skip("No 'issued' invoice_status seeded")
    return status


def _get_or_skip_payment_status(db: Session, code: str) -> PaymentStatus:
    status = db.exec(
        select(PaymentStatus)
        .where(PaymentStatus.tenant_id == None)
        .where(PaymentStatus.code == code)
    ).first()
    if not status:
        pytest.skip(f"No '{code}' payment_status seeded")
    return status


def _get_or_skip_payment_type(db: Session) -> PaymentType:
    pay_type = db.exec(
        select(PaymentType)
        .where(PaymentType.tenant_id == None)
        .where(PaymentType.code == "manual_check")
    ).first()
    if not pay_type:
        pay_type = db.exec(
            select(PaymentType).where(PaymentType.tenant_id == None)
        ).first()
    if not pay_type:
        pytest.skip("No payment_type seeded")
    return pay_type


def _get_or_create_customer_and_site(db: Session, tenant_id) -> tuple:
    """Return (customer_id, site_id) for the tenant, creating rows inline if needed.

    Creates its own customer/site so tests are not dependent on pre-seeded data
    (important for second_tenant which has no seed data by default).
    """
    customer_row = db.execute(
        text(
            "SELECT id FROM public.customer"
            " WHERE tenant_id = :tid AND is_active = true LIMIT 1"
        ),
        {"tid": str(tenant_id)},
    ).first()

    if customer_row:
        cust_id = customer_row.id
    else:
        lifecycle_row = db.execute(
            text(
                "SELECT id FROM public.customer_lifecycle_status"
                " WHERE code = 'active' AND tenant_id IS NULL LIMIT 1"
            )
        ).first()
        if not lifecycle_row:
            pytest.skip("No customer_lifecycle_status seeded")

        new_cust = db.execute(
            text("""
                INSERT INTO public.customer
                (id, tenant_id, type, display_name, first_name, last_name,
                 is_active, preferred_contact_channel, sms_opted_out, sms_opt_in_consent,
                 lifecycle_status_id, created_at, updated_at)
                VALUES (gen_random_uuid(), :tid, 'person', 'Test Customer FIX-013',
                        'Test', 'Customer', true, 'email', false, false, :lifecycle_id,
                        NOW(), NOW())
                RETURNING id
            """),
            {"tid": str(tenant_id), "lifecycle_id": str(lifecycle_row.id)},
        ).first()
        cust_id = new_cust.id

    site_row = db.execute(
        text("SELECT id FROM public.site WHERE tenant_id = :tid LIMIT 1"),
        {"tid": str(tenant_id)},
    ).first()

    if site_row:
        site_id = site_row.id
    else:
        site_lifecycle = db.execute(
            text(
                "SELECT id FROM public.site_lifecycle_status"
                " WHERE code = 'active' AND tenant_id IS NULL LIMIT 1"
            )
        ).first()

        new_site = db.execute(
            text("""
                INSERT INTO public.site
                (id, tenant_id, customer_id, name, is_active, lifecycle_status_id,
                 created_at, updated_at)
                VALUES (gen_random_uuid(), :tid, :cid, 'Test Site FIX-013', true, :lifecycle_id,
                        NOW(), NOW())
                RETURNING id
            """),
            {
                "tid": str(tenant_id),
                "cid": str(cust_id),
                "lifecycle_id": str(site_lifecycle.id) if site_lifecycle else None,
            },
        ).first()
        site_id = new_site.id

    return cust_id, site_id


def _create_test_invoice(db: Session, tenant_id) -> Invoice:
    """Create an invoice directly using the ORM for test isolation."""
    issued_status = _get_or_skip_issued_status(db)
    cust_id, site_id = _get_or_create_customer_and_site(db, tenant_id)

    invoice = Invoice(
        tenant_id=tenant_id,
        invoice_number=f"INV-PMT-TEST-{uuid.uuid4().hex[:6].upper()}",
        customer_id=cust_id,
        site_id=site_id,
        status_id=issued_status.id,
        total_cents=10000,
        balance_due_cents=10000,
        subtotal_cents=10000,
    )
    db.add(invoice)
    db.flush()
    return invoice


def _create_test_payment(db: Session, invoice: Invoice, amount_cents: int) -> Payment:
    """Create a payment directly using the ORM."""
    succeeded_status = _get_or_skip_payment_status(db, "succeeded")
    pay_type = _get_or_skip_payment_type(db)

    pay_method = PaymentMethod(
        tenant_id=invoice.tenant_id,
        payment_type_id=pay_type.id,
        psp_provider="seed",
        psp_payment_method_id=f"seed-{uuid.uuid4().hex[:8]}",
    )
    db.add(pay_method)
    db.flush()

    payment = Payment(
        tenant_id=invoice.tenant_id,
        invoice_id=invoice.id,
        amount_cents=amount_cents,
        payment_method_id=pay_method.id,
        status_id=succeeded_status.id,
        paid_via="check",
        is_active=True,
    )
    db.add(payment)
    db.flush()
    return payment


class TestInvoicePaymentsEmbedded:
    """FIX-013-BE: GET /api/v1/invoices/{id} includes embedded payments list."""

    def test_get_invoice_includes_payments_field(
        self, client, db_session: Session, test_tenant, mock_cognito_jwt
    ):
        """
        GET /api/v1/invoices/{invoice_id}/test returns a response dict that
        includes a 'payments' key as a list (empty is fine when no payments exist).
        """
        invoice = _create_test_invoice(db_session, test_tenant.id)
        invoice_id = invoice.id
        db_session.commit()

        resp = client.get(f"/api/v1/invoices/{invoice_id}/test")
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}: {resp.text}"
        )

        data = resp.json()
        assert data["id"] == str(invoice_id), "Response id must match inserted invoice"
        assert "payments" in data, "'payments' key missing from InvoiceResponse"
        assert isinstance(data["payments"], list), "'payments' must be a list"

    def test_get_invoice_includes_existing_payments(
        self, client, db_session: Session, test_tenant, mock_cognito_jwt
    ):
        """
        Create an invoice + one payment. GET /api/v1/invoices/{id}/test
        must return payments list containing that payment with correct amount_cents.
        Asserts by inserted payment ID — never by total list count.
        """
        invoice = _create_test_invoice(db_session, test_tenant.id)
        payment = _create_test_payment(db_session, invoice, amount_cents=5000)
        invoice_id = invoice.id
        payment_id = payment.id
        db_session.commit()

        resp = client.get(f"/api/v1/invoices/{invoice_id}/test")
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}: {resp.text}"
        )

        data = resp.json()
        assert "payments" in data, "'payments' key missing from InvoiceResponse"

        # Find the specific payment we inserted by its ID — never assert total list count
        matching = [p for p in data["payments"] if p["id"] == str(payment_id)]
        assert len(matching) == 1, (
            f"Expected to find payment {payment_id} in response payments list. "
            f"Got payments: {data['payments']}"
        )
        assert matching[0]["amount_cents"] == 5000, (
            f"Expected amount_cents=5000, got {matching[0]['amount_cents']}"
        )

    def test_get_invoice_payments_tenant_scoped(
        self, client, db_session: Session, test_tenant, second_tenant, mock_cognito_jwt
    ):
        """
        Create invoice in second_tenant using an inline-created customer/site.
        Fetch that invoice via /test endpoint (uses test_tenant context).
        Must return 404 — tenant B invoice is not visible under tenant A context.
        Does NOT depend on pre-seeded second_tenant customer/site data.
        """
        if second_tenant is None:
            pytest.skip("second_tenant fixture not available")

        issued_status = _get_or_skip_issued_status(db_session)

        # Create customer + site in second_tenant inline (no pre-seed dependency)
        second_cust_id, second_site_id = _get_or_create_customer_and_site(
            db_session, second_tenant.id
        )

        # Create invoice in second_tenant
        second_invoice = Invoice(
            tenant_id=second_tenant.id,
            invoice_number=f"INV-CROSS-TENANT-{uuid.uuid4().hex[:6].upper()}",
            customer_id=second_cust_id,
            site_id=second_site_id,
            status_id=issued_status.id,
            total_cents=20000,
            balance_due_cents=20000,
            subtotal_cents=20000,
        )
        db_session.add(second_invoice)
        db_session.flush()
        second_invoice_id = second_invoice.id
        db_session.commit()

        # Fetch second_tenant's invoice via test endpoint (uses test_tenant context)
        resp = client.get(f"/api/v1/invoices/{second_invoice_id}/test")
        assert resp.status_code == 404, (
            f"Expected 404 when fetching tenant B invoice from tenant A context, "
            f"got {resp.status_code}: {resp.text}"
        )
