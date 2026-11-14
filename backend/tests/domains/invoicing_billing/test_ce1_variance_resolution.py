"""
Tests for: CE-1 Overpayment Variance Resolution
Domain: invoicing_billing (PRD §3.6)

Covers D.4 — POST /api/v1/invoices/{payment_id}/resolve-variance.
(Payments routes live in invoices.py — see _record_payment_impl; the
invoices router prefix is /api/v1/invoices.)
Record-keeping only — no Stripe refund execution (§G-R6).
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlmodel import select

from app.models.billing import Invoice, InvoiceStatus, Payment, PaymentStatus

pytestmark = [
    pytest.mark.domain_invoicing_billing,
    pytest.mark.unit,
]


def _create_overpaid_payment(
    client, db_session, test_tenant, amount_cents=11500, variance_cents=1500
):
    """Create a customer, site, job, issued invoice, and an overpaid payment row."""
    # Create customer
    cust = client.post(
        "/api/v1/customers/test",
        json={"display_name": "Variance Test Co", "type": "person"},
    )
    assert cust.status_code == 201
    customer_id = cust.json()["id"]

    # Create site
    site = client.post(
        "/api/v1/sites/test",
        json={"customer_id": customer_id, "name": "Test Site"},
    )
    assert site.status_code == 201
    site_id = site.json()["id"]

    # Create job
    job = client.post(
        "/api/v1/jobs/test",
        json={"customer_id": customer_id, "site_id": site_id},
    )
    assert job.status_code == 201
    job_id = job.json()["id"]

    # Resolve invoice status by code
    inv_status = db_session.exec(
        select(InvoiceStatus).where(InvoiceStatus.code == "issued")
    ).first()

    # Create payment status (succeeded)
    pay_status = db_session.exec(
        select(PaymentStatus).where(PaymentStatus.code == "succeeded")
    ).first()

    # Create payment method — use a seed/test pattern
    from app.models.billing import PaymentMethod, PaymentType

    pay_type = db_session.exec(
        select(PaymentType).where(PaymentType.code == "card")
    ).first()

    pm = PaymentMethod(
        tenant_id=test_tenant.id,
        customer_id=uuid.UUID(customer_id),
        payment_type_id=pay_type.id,
        psp_provider="seed",
        psp_payment_method_id=f"seed-pm-{uuid.uuid4().hex[:8]}",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(pm)
    db_session.commit()
    db_session.refresh(pm)

    # Create invoice with balance_due = amount - variance
    invoice = Invoice(
        tenant_id=test_tenant.id,
        invoice_number=f"INV-VAR-{uuid.uuid4().hex[:8]}",
        customer_id=uuid.UUID(customer_id),
        site_id=uuid.UUID(site_id),
        job_id=uuid.UUID(job_id),
        status_id=inv_status.id,
        subtotal_cents=10000,
        tax_cents=0,
        total_cents=10000,
        balance_due_cents=0,  # fully paid
        currency="USD",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)

    # Create overpaid payment
    payment = Payment(
        tenant_id=test_tenant.id,
        invoice_id=invoice.id,
        amount_cents=amount_cents,
        payment_method_id=pm.id,
        status_id=pay_status.id,
        paid_at=datetime.now(UTC),
        amount_variance_cents=variance_cents,
        paid_via="check",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)

    return {
        "payment_id": str(payment.id),
        "invoice_id": str(invoice.id),
        "job_id": job_id,
    }


class TestResolveVariance:
    """D.4 — POST /api/v1/invoices/{payment_id}/resolve-variance"""

    def test_resolve_happy_path(self, client, db_session, test_tenant, test_user):
        """Overpaid payment → 200, fields set, resolved_by = calling user."""
        ctx = _create_overpaid_payment(client, db_session, test_tenant)

        resp = client.post(
            f"/api/v1/invoices/{ctx['payment_id']}/resolve-variance/test",
            json={"resolution": "credit", "note": "Credited forward to next invoice"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["variance_resolution"] == "credit"
        assert data["variance_resolution_note"] == "Credited forward to next invoice"
        assert data["variance_resolved_at"] is not None
        assert data["variance_resolved_by_user_id"] is not None

    def test_already_resolved_409(self, client, db_session, test_tenant):
        """Already resolved → 409 with current resolution in detail."""
        ctx = _create_overpaid_payment(client, db_session, test_tenant)

        # First resolution
        client.post(
            f"/api/v1/invoices/{ctx['payment_id']}/resolve-variance/test",
            json={"resolution": "credit"},
        )

        # Second attempt → 409
        resp = client.post(
            f"/api/v1/invoices/{ctx['payment_id']}/resolve-variance/test",
            json={"resolution": "writeoff"},
        )
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert "credit" in detail["detail"]

    def test_no_variance_422(self, client, db_session, test_tenant):
        """amount_variance_cents NULL → 422."""
        ctx = _create_overpaid_payment(
            client, db_session, test_tenant, variance_cents=0
        )

        # Set variance to NULL
        payment = db_session.exec(
            select(Payment).where(Payment.id == uuid.UUID(ctx["payment_id"]))
        ).first()
        payment.amount_variance_cents = None
        db_session.add(payment)
        db_session.commit()

        resp = client.post(
            f"/api/v1/invoices/{ctx['payment_id']}/resolve-variance/test",
            json={"resolution": "credit"},
        )
        assert resp.status_code == 422

    def test_negative_variance_422(self, client, db_session, test_tenant):
        """amount_variance_cents ≤ 0 → 422."""
        ctx = _create_overpaid_payment(
            client, db_session, test_tenant, variance_cents=-500
        )

        resp = client.post(
            f"/api/v1/invoices/{ctx['payment_id']}/resolve-variance/test",
            json={"resolution": "credit"},
        )
        assert resp.status_code == 422

    def test_refund_payment_422(self, client, db_session, test_tenant):
        """Negative-amount (refund) payment row → 422."""
        ctx = _create_overpaid_payment(
            client, db_session, test_tenant, amount_cents=-3200, variance_cents=0
        )

        # Set a positive variance on a negative-amount payment (edge case)
        payment = db_session.exec(
            select(Payment).where(Payment.id == uuid.UUID(ctx["payment_id"]))
        ).first()
        payment.amount_variance_cents = 500
        db_session.add(payment)
        db_session.commit()

        resp = client.post(
            f"/api/v1/invoices/{ctx['payment_id']}/resolve-variance/test",
            json={"resolution": "credit"},
        )
        assert resp.status_code == 422

    def test_invalid_resolution_value_422(self, client, db_session, test_tenant):
        """Invalid resolution value → 422 (schema validation)."""
        ctx = _create_overpaid_payment(client, db_session, test_tenant)

        resp = client.post(
            f"/api/v1/invoices/{ctx['payment_id']}/resolve-variance/test",
            json={"resolution": "invalid_option"},
        )
        assert resp.status_code == 422

    def test_cross_tenant_payment_404(self, client, db_session, test_tenant, tenant_b):
        """Cross-tenant payment → 404."""
        ctx = _create_overpaid_payment(client, db_session, tenant_b)

        # /test endpoint uses test_tenant context, so tenant_b payment → 404
        resp = client.post(
            f"/api/v1/invoices/{ctx['payment_id']}/resolve-variance/test",
            json={"resolution": "credit"},
        )
        assert resp.status_code == 404

    def test_extended_payment_response_fields(self, client, db_session, test_tenant):
        """Extended PaymentResponse serialization includes the four new fields."""
        ctx = _create_overpaid_payment(client, db_session, test_tenant)

        resp = client.post(
            f"/api/v1/invoices/{ctx['payment_id']}/resolve-variance/test",
            json={
                "resolution": "refund_offline",
                "note": "Refunded via Stripe manually",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "variance_resolution" in data
        assert "variance_resolution_note" in data
        assert "variance_resolved_at" in data
        assert "variance_resolved_by_user_id" in data
        assert data["variance_resolution"] == "refund_offline"
