"""
INV-ROUTE-FIX — Canonical public invoice route regression guard.

Verifies that GET /api/v1/public/invoices/{signed_token} returns the
canonical response shape that the frontend `normalizeInvoiceData` expects:
  - tenant_name (string)
  - customer_name (string)
  - line_items[] (list)
  - branding (object)
  - status (string: unpaid|partial|paid)
  - amount_due_cents (int)
  - amount_paid_cents (int)
  - invoice_total_cents (int)

This is the regression guard proving the pay-invoice page gets the correct data.
"""

import secrets as _secrets
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import select

from app.models.billing import (
    Currency,
    Invoice,
    InvoicePublicLink,
    InvoiceStatus,
)
from services.public_link_signer import generate_signed_token

pytestmark = [pytest.mark.domain_invoicing_billing, pytest.mark.unit]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_currency(db_session) -> None:
    if not db_session.exec(select(Currency).where(Currency.code == "USD")).first():
        db_session.add(Currency(code="USD", name="US Dollar", symbol="$"))
        db_session.flush()


def _get_or_create_invoice_status(db_session, code: str = "sent") -> InvoiceStatus:
    ist = db_session.exec(
        select(InvoiceStatus).where(
            InvoiceStatus.code == code,
            InvoiceStatus.tenant_id.is_(None),
        )
    ).first()
    if not ist:
        ist = InvoiceStatus(
            id=uuid.uuid4(),
            tenant_id=None,
            code=code,
            name=code.capitalize(),
            is_default=(code == "sent"),
            is_active=True,
        )
        db_session.add(ist)
        db_session.flush()
    return ist


def _create_invoice(db_session, tenant_id, customer_id, site_id, total_cents=50000):
    _ensure_currency(db_session)
    ist = _get_or_create_invoice_status(db_session, "sent")
    invoice = Invoice(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        invoice_number=f"INV-CANON-{uuid.uuid4().hex[:6].upper()}",
        customer_id=customer_id,
        site_id=site_id,
        status_id=ist.id,
        currency="USD",
        subtotal_cents=total_cents,
        tax_cents=0,
        total_cents=total_cents,
        balance_due_cents=total_cents,
        is_active=True,
    )
    db_session.add(invoice)
    db_session.flush()
    return invoice


def _create_link_with_signed_token(
    db_session,
    tenant_id,
    invoice_id,
    customer_id,
    expires_in_days: int = 30,
) -> tuple[InvoicePublicLink, str]:
    """Create InvoicePublicLink and return (link, signed_token)."""
    link = InvoicePublicLink(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        invoice_id=invoice_id,
        token_hash=_secrets.token_hex(32),
        status="active",
        expires_at=datetime.now(UTC) + timedelta(days=expires_in_days),
        max_uses=0,
        used_count=0,
    )
    db_session.add(link)
    db_session.flush()

    signed_token, _ = generate_signed_token(
        link_id=link.id,
        link_type="invoice",
        customer_id=customer_id,
        expires_in_days=expires_in_days,
    )
    link.signed_token = signed_token
    db_session.flush()
    return link, signed_token


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPublicInvoiceCanonicalShape:
    """
    INV-ROUTE-FIX regression guard:
    GET /public/invoices/{signed_token} returns canonical response shape.
    """

    def test_canonical_response_shape_present(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """
        The pay-invoice page requires these fields in the response.
        Verifying them here ensures the frontend normalizeInvoiceData() won't break.
        """
        invoice = _create_invoice(
            db_session,
            test_tenant.id,
            test_customer.id,
            test_site.id,
            total_cents=75000,
        )
        _, signed_token = _create_link_with_signed_token(
            db_session, test_tenant.id, invoice.id, test_customer.id
        )
        db_session.commit()

        resp = client.get(f"/api/v1/public/invoices/{signed_token}")
        assert resp.status_code == 200, f"Canonical GET failed: {resp.text}"

        body = resp.json()

        # === Canonical shape fields ===
        # Invoice identification
        assert body.get("invoice_id") == str(invoice.id), (
            f"invoice_id mismatch: {body.get('invoice_id')} != {invoice.id}"
        )

        # Party names (strings, not UUIDs — canonical vs legacy difference)
        assert "tenant_name" in body, (
            f"INV-ROUTE-FIX: canonical shape must have tenant_name. "
            f"Got keys: {sorted(body.keys())}"
        )
        assert isinstance(body["tenant_name"], str), "tenant_name must be a string"

        assert "customer_name" in body, (
            f"INV-ROUTE-FIX: canonical shape must have customer_name. "
            f"Got keys: {sorted(body.keys())}"
        )
        assert isinstance(body["customer_name"], str), "customer_name must be a string"

        # Line items
        assert "line_items" in body, (
            f"INV-ROUTE-FIX: canonical shape must have line_items. "
            f"Got keys: {sorted(body.keys())}"
        )
        assert isinstance(body["line_items"], list), "line_items must be a list"

        # Branding
        assert "branding" in body, (
            f"INV-ROUTE-FIX: canonical shape must have branding. "
            f"Got keys: {sorted(body.keys())}"
        )

        # Payment status
        assert "status" in body, "canonical shape must have status"
        assert body["status"] in ("unpaid", "partial", "paid"), (
            f"status must be unpaid|partial|paid, got: {body['status']}"
        )

        # Amount fields
        assert "amount_due_cents" in body, "canonical shape must have amount_due_cents"
        assert "amount_paid_cents" in body, (
            "canonical shape must have amount_paid_cents"
        )
        assert "invoice_total_cents" in body, (
            "canonical shape must have invoice_total_cents"
        )
        assert isinstance(body["invoice_total_cents"], int)
        assert isinstance(body["amount_due_cents"], int)
        assert isinstance(body["amount_paid_cents"], int)

        # Legacy fields must NOT be present (they belonged to the old handler)
        assert "tenant_id" not in body, (
            "INV-ROUTE-FIX: legacy tenant_id UUID must not be in canonical response. "
            "Use tenant_name instead."
        )
        assert "balance_due_cents" not in body, (
            "INV-ROUTE-FIX: legacy balance_due_cents must not be in canonical response. "
            "Use amount_due_cents instead."
        )

    def test_unpaid_invoice_status_is_unpaid(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """An invoice with no payments has status='unpaid' and amount_due == total."""
        invoice = _create_invoice(
            db_session,
            test_tenant.id,
            test_customer.id,
            test_site.id,
            total_cents=30000,
        )
        _, signed_token = _create_link_with_signed_token(
            db_session, test_tenant.id, invoice.id, test_customer.id
        )
        db_session.commit()

        resp = client.get(f"/api/v1/public/invoices/{signed_token}")
        assert resp.status_code == 200, resp.text

        body = resp.json()
        assert body["status"] == "unpaid", (
            f"No payments → status must be 'unpaid', got: {body['status']}"
        )
        assert body["amount_paid_cents"] == 0, (
            f"No payments → amount_paid_cents must be 0, got: {body['amount_paid_cents']}"
        )
        # amount_due should equal total for unpaid invoice
        assert body["amount_due_cents"] == body["invoice_total_cents"], (
            "Unpaid: amount_due_cents should equal total_cents"
        )

    def test_garbage_token_returns_401_not_404(self, client, db_session):
        """
        INV-ROUTE-FIX semantic change documented:
        An unknown/garbage token returns 401 (invalid signature), not 404.
        This prevents UUID/token enumeration attacks.
        """
        resp = client.get("/api/v1/public/invoices/totally_garbage_token_xyz")
        assert resp.status_code == 401, (
            f"INV-ROUTE-FIX: garbage token must return 401, got {resp.status_code}. "
            "The canonical handler treats unparseable tokens as unauthenticated (not not-found)."
        )

    def test_route_uniqueness_no_legacy_shadow(self):
        """
        INV-ROUTE-FIX regression: only ONE route matches the canonical path.
        The legacy invoices.public_router must not shadow the canonical handler.
        """
        from app.main import app

        canonical_matches = [
            r
            for r in app.routes
            if getattr(r, "path", "") == "/api/v1/public/invoices/{signed_token}"
        ]
        assert len(canonical_matches) == 1, (
            f"Expected exactly 1 canonical route, found {len(canonical_matches)}"
        )

        legacy_matches = [
            r
            for r in app.routes
            if getattr(r, "path", "") == "/api/v1/public/invoices/{token}"
        ]
        assert len(legacy_matches) == 0, (
            "Legacy /{token} route is still registered — it would shadow the canonical route"
        )
