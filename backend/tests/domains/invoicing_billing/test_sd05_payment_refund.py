"""
SD-05/SD-2 Tests: Payment refund model.

SD-2 update: Refunds now create a negative-amount payment row
(replaces SD-05 column-based approach of refunded_amount_cents/refunded_at).

Tests:
1. test_payment_model_has_no_refund_columns — Payment model must NOT have deprecated fields
2. test_charge_refunded_webhook_creates_negative_row — charge.refunded creates new negative Payment row
3. test_partial_refund_original_row_unchanged — original payment row is unchanged after refund
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


def _create_payment_row(db: Session, tenant_id) -> Payment:
    """Create a minimal Payment row for refund tests."""
    from sqlalchemy import text

    # Get draft invoice status (null-tenant global)
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
        invoice_number=f"INV-SD05-{uuid.uuid4().hex[:6].upper()}",
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

    pay_status = db.exec(
        select(PaymentStatus)
        .where(PaymentStatus.tenant_id == None)
        .where(PaymentStatus.code == "succeeded")
    ).first()
    if not pay_status:
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
        status_id=pay_status.id,
        stripe_payment_intent_id=stripe_pi_id,
    )
    db.add(payment)
    db.flush()
    return payment


class TestPaymentRefundColumns:
    """SD-2: Payment refund model — negative-amount row, no columns on original row."""

    def test_payment_model_has_no_refund_columns(self, db_session: Session):
        """
        SD-2: Payment model must NOT have refunded_amount_cents or refunded_at fields.
        These columns were removed when we switched to the negative-row model.
        """
        payment = Payment(
            tenant_id=uuid.uuid4(),
            invoice_id=uuid.uuid4(),
            amount_cents=5000,
            payment_method_id=uuid.uuid4(),
            status_id=uuid.uuid4(),
        )
        assert not hasattr(payment, "refunded_amount_cents"), (
            "Payment.refunded_amount_cents still exists — SD-2 migration not applied"
        )
        assert not hasattr(payment, "refunded_at"), (
            "Payment.refunded_at still exists — SD-2 migration not applied"
        )

    def test_charge_refunded_webhook_creates_negative_row(
        self, client, db_session: Session, test_tenant, mock_cognito_jwt
    ):
        """
        SD-2: charge.refunded event creates a new negative-amount Payment row.
        The original payment row is NOT modified.
        """
        from api.routes.webhooks_stripe import _handle_refund_event

        payment = _create_payment_row(db_session, test_tenant.id)
        stripe_pi_id = payment.stripe_payment_intent_id
        original_payment_id = payment.id
        db_session.commit()

        # Verify 'refunded' status is seeded
        refunded_status = db_session.exec(
            select(PaymentStatus)
            .where(PaymentStatus.code == "refunded")
            .where(PaymentStatus.tenant_id == None)
        ).first()
        if not refunded_status:
            pytest.skip("'refunded' payment_status not seeded — run SD-2 migration")

        # Build synthetic charge.refunded payload
        fake_payload = {
            "id": f"evt_{uuid.uuid4().hex}",
            "type": "charge.refunded",
            "data": {
                "object": {
                    "id": f"ch_{uuid.uuid4().hex}",
                    "payment_intent": stripe_pi_id,
                    "amount_refunded": 3000,
                    "currency": "usd",
                }
            },
        }

        _handle_refund_event(db_session, fake_payload)

        # A NEW payment row with negative amount must exist
        refund_rows = db_session.exec(
            select(Payment).where(
                Payment.invoice_id == payment.invoice_id,
                Payment.amount_cents < 0,
                Payment.status_id == refunded_status.id,
            )
        ).all()
        assert len(refund_rows) == 1, (
            f"Expected 1 negative-amount refund row, found {len(refund_rows)}"
        )
        assert refund_rows[0].amount_cents == -3000
        assert refund_rows[0].paid_via == "stripe"

    def test_partial_refund_original_row_unchanged(
        self, client, db_session: Session, test_tenant, mock_cognito_jwt
    ):
        """
        SD-2: After a refund, the original payment row must be unchanged.
        Refund tracking uses a separate negative-amount row, not mutations on the original.
        """
        from api.routes.webhooks_stripe import _handle_refund_event

        payment = _create_payment_row(db_session, test_tenant.id)
        stripe_pi_id = payment.stripe_payment_intent_id
        payment_id = payment.id
        original_amount_cents = payment.amount_cents
        original_status_id = payment.status_id
        db_session.commit()

        refunded_status = db_session.exec(
            select(PaymentStatus)
            .where(PaymentStatus.code == "refunded")
            .where(PaymentStatus.tenant_id == None)
        ).first()
        if not refunded_status:
            pytest.skip("'refunded' payment_status not seeded — run SD-2 migration")

        fake_payload = {
            "id": f"evt_{uuid.uuid4().hex}",
            "type": "charge.refunded",
            "data": {
                "object": {
                    "id": f"ch_{uuid.uuid4().hex}",
                    "payment_intent": stripe_pi_id,
                    "amount_refunded": 1000,
                    "currency": "usd",
                }
            },
        }

        _handle_refund_event(db_session, fake_payload)

        # Original payment row must be unchanged
        db_session.expire(payment)
        refreshed = db_session.exec(
            select(Payment).where(Payment.id == payment_id)
        ).first()
        assert refreshed is not None
        assert refreshed.amount_cents == original_amount_cents, (
            "Original payment.amount_cents must not be modified by refund"
        )
        assert refreshed.status_id == original_status_id, (
            "Original payment.status_id must not be modified by refund"
        )
