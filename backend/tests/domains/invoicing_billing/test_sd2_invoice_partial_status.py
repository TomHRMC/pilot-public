"""
SD-2 Tests: Invoice transitions to 'partial' on under-payment.

Tests:
1. test_invoice_transitions_to_partial_on_underpayment — partial payment sets status='partial'
2. test_invoice_transitions_to_paid_on_full_payment — full payment sets status='paid'
"""

import uuid

import pytest
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


def _seed_invoice(db: Session, tenant_id, total_cents: int) -> Invoice:
    """Create an invoice with issued status and total_cents."""
    from sqlalchemy import text

    issued_status = db.exec(
        select(InvoiceStatus)
        .where(InvoiceStatus.tenant_id == None)
        .where(InvoiceStatus.code == "issued")
    ).first()
    if not issued_status:
        pytest.skip("No 'issued' invoice_status seeded")

    customer_row = db.execute(
        text("SELECT id FROM public.customer WHERE tenant_id = :tid LIMIT 1"),
        {"tid": str(tenant_id)},
    ).first()
    if not customer_row:
        pytest.skip("No customer for test tenant — run seed_test_tenant.py")

    site_row = db.execute(
        text("SELECT id FROM public.site WHERE tenant_id = :tid LIMIT 1"),
        {"tid": str(tenant_id)},
    ).first()
    if not site_row:
        pytest.skip("No site for test tenant — run seed_test_tenant.py")

    invoice = Invoice(
        tenant_id=tenant_id,
        invoice_number=f"INV-PARTIAL-{uuid.uuid4().hex[:6].upper()}",
        customer_id=customer_row.id,
        site_id=site_row.id,
        status_id=issued_status.id,
        total_cents=total_cents,
        balance_due_cents=total_cents,
        subtotal_cents=total_cents,
    )
    db.add(invoice)
    db.flush()
    return invoice


def _apply_payment(db: Session, invoice: Invoice, amount_cents: int) -> None:
    """Apply a payment to the invoice and call status update logic."""
    from services.stripe_payment_intents import _update_invoice_status_after_payment

    pay_type = db.exec(
        select(PaymentType)
        .where(PaymentType.tenant_id == None)
        .where(PaymentType.code == "card")
    ).first()
    if not pay_type:
        pytest.skip("No 'card' payment type seeded")

    succeeded_status = db.exec(
        select(PaymentStatus)
        .where(PaymentStatus.tenant_id == None)
        .where(PaymentStatus.code == "succeeded")
    ).first()
    if not succeeded_status:
        pytest.skip("No 'succeeded' payment status seeded")

    pay_method = PaymentMethod(
        tenant_id=invoice.tenant_id,
        payment_type_id=pay_type.id,
        psp_provider="stripe",
        psp_payment_method_id=f"pm_{uuid.uuid4().hex}",
    )
    db.add(pay_method)
    db.flush()

    payment = Payment(
        tenant_id=invoice.tenant_id,
        invoice_id=invoice.id,
        amount_cents=amount_cents,
        payment_method_id=pay_method.id,
        status_id=succeeded_status.id,
        paid_via="stripe",
        is_active=True,
    )
    db.add(payment)
    db.flush()

    # Call SD-2 status update logic
    _update_invoice_status_after_payment(db, invoice)
    db.flush()


class TestInvoicePartialStatus:
    """SD-2: Invoice status transitions to partial/paid based on remaining balance."""

    def test_invoice_transitions_to_partial_on_underpayment(
        self, client, db_session: Session, test_tenant, mock_cognito_jwt
    ):
        """
        Create invoice with total=10000 cents.
        Apply payment of 5000 cents → assert invoice.status_code == 'partial'.
        """
        partial_status = db_session.exec(
            select(InvoiceStatus)
            .where(InvoiceStatus.tenant_id == None)
            .where(InvoiceStatus.code == "partial")
        ).first()
        if not partial_status:
            pytest.skip("'partial' invoice_status not seeded — run SD-2 migration")

        invoice = _seed_invoice(db_session, test_tenant.id, total_cents=10000)
        invoice_id = invoice.id
        db_session.commit()

        # Apply partial payment (5000 of 10000)
        _apply_payment(db_session, invoice, amount_cents=5000)
        db_session.commit()

        refreshed = db_session.exec(
            select(Invoice).where(Invoice.id == invoice_id)
        ).first()
        assert refreshed is not None
        assert refreshed.status_id == partial_status.id, (
            f"Expected invoice status 'partial' after 5000/10000 payment, "
            f"got status_id={refreshed.status_id}"
        )

    def test_invoice_transitions_to_paid_on_full_payment(
        self, client, db_session: Session, test_tenant, mock_cognito_jwt
    ):
        """
        Create invoice with total=10000 cents.
        Apply first payment of 5000 (→ partial), then another 5000 (→ paid).
        """
        partial_status = db_session.exec(
            select(InvoiceStatus)
            .where(InvoiceStatus.tenant_id == None)
            .where(InvoiceStatus.code == "partial")
        ).first()
        if not partial_status:
            pytest.skip("'partial' invoice_status not seeded — run SD-2 migration")

        paid_status = db_session.exec(
            select(InvoiceStatus)
            .where(InvoiceStatus.tenant_id == None)
            .where(InvoiceStatus.code == "paid")
        ).first()
        if not paid_status:
            pytest.skip("'paid' invoice_status not seeded")

        invoice = _seed_invoice(db_session, test_tenant.id, total_cents=10000)
        invoice_id = invoice.id
        db_session.commit()

        # First partial payment
        _apply_payment(db_session, invoice, amount_cents=5000)
        db_session.commit()

        refreshed = db_session.exec(
            select(Invoice).where(Invoice.id == invoice_id)
        ).first()
        assert refreshed.status_id == partial_status.id, (
            "Expected 'partial' after first payment"
        )

        # Second payment — brings total to 10000 = full payment
        _apply_payment(db_session, refreshed, amount_cents=5000)
        db_session.commit()

        final = db_session.exec(select(Invoice).where(Invoice.id == invoice_id)).first()
        assert final is not None
        assert final.status_id == paid_status.id, (
            "Expected invoice status 'paid' after full 10000/10000 payment"
        )
