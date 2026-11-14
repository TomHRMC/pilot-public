"""
SD-2 Tests: Payment refund creates a negative-amount Payment row.

Tests:
1. test_refund_creates_negative_payment_row — _handle_refund_event creates negative row
2. test_refund_original_payment_unchanged — original succeeded payment is unmodified
3. test_refund_missing_pi_id_skipped — event without payment_intent is gracefully skipped
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


def _create_test_invoice_and_payment(db: Session, tenant_id) -> tuple[Invoice, Payment]:
    """Create a minimal invoice + succeeded payment for refund tests."""
    from sqlalchemy import text

    inv_status = db.exec(
        select(InvoiceStatus)
        .where(InvoiceStatus.tenant_id == None)
        .where(InvoiceStatus.code == "draft")
    ).first()
    if not inv_status:
        pytest.skip("No 'draft' invoice status seeded")

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
        invoice_number=f"INV-SD2-{uuid.uuid4().hex[:6].upper()}",
        customer_id=customer_row.id,
        site_id=site_row.id,
        status_id=inv_status.id,
        total_cents=10000,
        balance_due_cents=10000,
        subtotal_cents=10000,
    )
    db.add(invoice)
    db.flush()

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
        tenant_id=tenant_id,
        payment_type_id=pay_type.id,
        psp_provider="stripe",
        psp_payment_method_id=f"pm_{uuid.uuid4().hex}",
    )
    db.add(pay_method)
    db.flush()

    stripe_pi_id = f"pi_{uuid.uuid4().hex}"
    payment = Payment(
        tenant_id=tenant_id,
        invoice_id=invoice.id,
        amount_cents=10000,
        payment_method_id=pay_method.id,
        status_id=succeeded_status.id,
        stripe_payment_intent_id=stripe_pi_id,
        paid_via="stripe",
        psp_provider="stripe",
    )
    db.add(payment)
    db.flush()
    return invoice, payment


class TestPaymentRefundNegativeRow:
    """SD-2: Refund creates a negative-amount payment row."""

    def test_refund_creates_negative_payment_row(
        self, client, db_session: Session, test_tenant, mock_cognito_jwt
    ):
        """
        Mock Stripe charge.refunded event → assert new Payment row with
        negative amount_cents and status_code='refunded' is created.
        """
        from services.stripe_subscriptions import _handle_refund_event

        refunded_status = db_session.exec(
            select(PaymentStatus)
            .where(PaymentStatus.code == "refunded")
            .where(PaymentStatus.tenant_id == None)
        ).first()
        if not refunded_status:
            pytest.skip("'refunded' payment_status not seeded — run SD-2 migration")

        invoice, payment = _create_test_invoice_and_payment(db_session, test_tenant.id)
        stripe_pi_id = payment.stripe_payment_intent_id
        invoice_id = invoice.id
        db_session.commit()

        # Simulate charge.refunded event_data (the "data" dict from the Stripe event)
        event_data = {
            "object": {
                "id": f"ch_{uuid.uuid4().hex}",
                "payment_intent": stripe_pi_id,
                "amount_refunded": 5000,
                "currency": "usd",
            }
        }

        _handle_refund_event(db_session, event_data)

        # Assert a new negative-amount payment row was created
        refund_rows = db_session.exec(
            select(Payment).where(
                Payment.invoice_id == invoice_id,
                Payment.amount_cents == -5000,
                Payment.status_id == refunded_status.id,
            )
        ).all()
        assert len(refund_rows) == 1, (
            f"Expected 1 negative refund row, found {len(refund_rows)}"
        )
        refund_row = refund_rows[0]
        assert refund_row.amount_cents == -5000
        assert refund_row.paid_via == "stripe"
        assert refund_row.is_active is True

    def test_refund_original_payment_unchanged(
        self, client, db_session: Session, test_tenant, mock_cognito_jwt
    ):
        """
        After _handle_refund_event, the original payment row must be unchanged.
        """
        from services.stripe_subscriptions import _handle_refund_event

        refunded_status = db_session.exec(
            select(PaymentStatus)
            .where(PaymentStatus.code == "refunded")
            .where(PaymentStatus.tenant_id == None)
        ).first()
        if not refunded_status:
            pytest.skip("'refunded' payment_status not seeded — run SD-2 migration")

        invoice, payment = _create_test_invoice_and_payment(db_session, test_tenant.id)
        stripe_pi_id = payment.stripe_payment_intent_id
        original_payment_id = payment.id
        original_amount = payment.amount_cents
        original_status_id = payment.status_id
        db_session.commit()

        event_data = {
            "object": {
                "id": f"ch_{uuid.uuid4().hex}",
                "payment_intent": stripe_pi_id,
                "amount_refunded": 3000,
                "currency": "usd",
            }
        }

        _handle_refund_event(db_session, event_data)

        # Original row must be unchanged
        db_session.expire_all()
        original = db_session.exec(
            select(Payment).where(Payment.id == original_payment_id)
        ).first()
        assert original is not None
        assert original.amount_cents == original_amount, (
            "Original payment.amount_cents must not be modified"
        )
        assert original.status_id == original_status_id, (
            "Original payment.status_id must not be modified"
        )

    def test_refund_missing_pi_id_skipped(
        self, client, db_session: Session, test_tenant, mock_cognito_jwt
    ):
        """
        _handle_refund_event with no payment_intent in the payload returns None gracefully.
        No new rows created.
        """
        from services.stripe_subscriptions import _handle_refund_event

        # Count all payments before
        all_before = db_session.exec(
            select(Payment).where(Payment.tenant_id == test_tenant.id)
        ).all()
        count_before = len(all_before)

        event_data = {
            "object": {
                "id": f"ch_{uuid.uuid4().hex}",
                # no payment_intent field
                "amount_refunded": 1000,
            }
        }

        # Should not raise
        _handle_refund_event(db_session, event_data)

        all_after = db_session.exec(
            select(Payment).where(Payment.tenant_id == test_tenant.id)
        ).all()
        assert len(all_after) == count_before, (
            "No payment rows should be created when payment_intent is missing"
        )
