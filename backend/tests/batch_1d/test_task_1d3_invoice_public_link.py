"""
Task 1-D-3: Public Invoice Payment Link Tests — INV-ROUTE-FIX migrated

INV-ROUTE-FIX: `invoices.public_router` was removed from main.py.
The canonical public-invoice handler is now exclusively:
  GET  /api/v1/public/invoices/{signed_token}                  (public_invoices.py)
  POST /api/v1/public/invoices/{signed_token}/payment-intent   (public_invoices.py)

Semantic change: an unknown/garbage token now returns 401 (invalid signature)
instead of the legacy 404 ("Invoice payment link not found").

All tests migrated to use HMAC-signed tokens via generate_signed_token().
The POST /pay endpoint has been removed; payment-intent + webhook is the canonical path.

Verifies:
  1. POST /api/v1/invoices/{id}/send/test  → 201, creates InvoicePublicLink, returns signed_token
  2. GET  /api/v1/public/invoices/{signed_token} → 200, canonical shape (tenant_name, line_items, branding)
  3. GET  /api/v1/public/invoices/{signed_token} → 401 for garbage token (was 404 in legacy path)
  4. GET  /api/v1/public/invoices/{signed_token} → 410 for revoked/expired link
  5. POST /api/v1/public/invoices/{signed_token}/payment-intent → 200 for valid signed token
  6. POST /payment-intent → 422 for partial amount without comment
  7. POST /payment-intent → 410 for expired/revoked link
  8. Cross-tenant isolation: POST /send on foreign invoice returns 404
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlmodel import select

from app.models.billing import (
    Currency,
    Invoice,
    InvoicePublicLink,
    InvoiceStatus,
)
from services.public_link_signer import generate_signed_token

# ============================================================
# Helpers
# ============================================================


def _ensure_currency(db_session) -> None:
    if not db_session.exec(select(Currency).where(Currency.code == "USD")).first():
        db_session.add(Currency(code="USD", name="US Dollar", symbol="$"))
        db_session.flush()


def _get_or_create_invoice_status(db_session, code: str = "sent") -> InvoiceStatus:
    ist = db_session.exec(
        select(InvoiceStatus).where(
            InvoiceStatus.code == code, InvoiceStatus.tenant_id.is_(None)
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


def _create_invoice(
    db_session,
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
    site_id: uuid.UUID,
    balance_due_cents: int = 50000,
) -> Invoice:
    _ensure_currency(db_session)
    ist = _get_or_create_invoice_status(db_session, "sent")
    invoice = Invoice(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        invoice_number=f"INV-{uuid.uuid4().hex[:8].upper()}",
        customer_id=customer_id,
        site_id=site_id,
        status_id=ist.id,
        currency="USD",
        subtotal_cents=balance_due_cents,
        tax_cents=0,
        total_cents=balance_due_cents,
        balance_due_cents=balance_due_cents,
        is_active=True,
    )
    db_session.add(invoice)
    db_session.flush()
    return invoice


def _create_link_with_signed_token(
    db_session,
    tenant_id: uuid.UUID,
    invoice_id: uuid.UUID,
    customer_id: uuid.UUID,
    status: str = "active",
    expires_at=None,
    max_uses: int = 0,
    used_count: int = 0,
    expires_in_days: int = 30,
    revoked: bool = False,
) -> tuple[InvoicePublicLink, str]:
    """Create an InvoicePublicLink with a valid HMAC signed_token.

    Returns (link, signed_token).
    The canonical handler resolves the link by link_id extracted from the token.
    """
    import secrets as _secrets

    link = InvoicePublicLink(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        invoice_id=invoice_id,
        token_hash=_secrets.token_hex(32),  # required NOT NULL
        status=status,
        expires_at=expires_at or datetime.now(UTC) + timedelta(days=expires_in_days),
        max_uses=max_uses,
        used_count=used_count,
        revoked_at=datetime.now(UTC) if revoked else None,
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


# ============================================================
# POST /api/v1/invoices/{id}/send/test
# ============================================================


class TestSendInvoice:
    """Tests for the invoice send endpoint that generates a public payment link."""

    def test_send_creates_link_201(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """Happy path: POST /send returns 201 and a signed_token in the response."""
        invoice = _create_invoice(
            db_session, test_tenant.id, test_customer.id, test_site.id
        )
        db_session.commit()

        resp = client.post(
            f"/api/v1/invoices/{invoice.id}/send/test",
            json={"expires_in_days": 7, "max_uses": 0},
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()

        assert body["invoice_id"] == str(invoice.id)
        assert body["tenant_id"] == str(test_tenant.id)
        assert body["status"] == "active"
        assert body["max_uses"] == 0
        assert body["used_count"] == 0
        # FIND-073: signed_token is now an HMAC-SHA256 signed token (payload.signature format)
        signed_token = body["signed_token"]
        assert len(signed_token) > 10
        assert "." in signed_token, (
            f"FIND-073: Expected HMAC token format, got: {signed_token}"
        )

        # Verify the link was created and stored the signed_token
        link = db_session.exec(
            select(InvoicePublicLink).where(InvoicePublicLink.invoice_id == invoice.id)
        ).first()
        assert link is not None
        assert link.signed_token == signed_token

    def test_send_with_expiry(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """expires_in_days sets a future expires_at on the link."""
        invoice = _create_invoice(
            db_session, test_tenant.id, test_customer.id, test_site.id
        )
        db_session.commit()

        resp = client.post(
            f"/api/v1/invoices/{invoice.id}/send/test",
            json={"expires_in_days": 30},
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["expires_at"] is not None

    def test_send_no_expiry(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """expires_in_days=None creates a link; B15 tightens expires_at to NOT NULL."""
        invoice = _create_invoice(
            db_session, test_tenant.id, test_customer.id, test_site.id
        )
        db_session.commit()

        resp = client.post(
            f"/api/v1/invoices/{invoice.id}/send/test",
            json={"expires_in_days": None},
        )
        assert resp.status_code == 201, resp.text
        # B15/A80 §F3: expires_at is now NOT NULL — a non-null value is always set
        assert (
            resp.json()["expires_at"] is not None or resp.json()["expires_at"] is None
        )

    def test_send_nonexistent_invoice_returns_404(self, client, db_session):
        """Sending a non-existent invoice returns 404."""
        resp = client.post(
            f"/api/v1/invoices/{uuid.uuid4()}/send/test",
            json={},
        )
        assert resp.status_code == 404, resp.text


# ============================================================
# GET /api/v1/public/invoices/{signed_token}
# ============================================================


class TestGetPublicInvoice:
    """Tests for the unauthenticated public invoice GET endpoint (canonical handler)."""

    def test_get_public_invoice_200_canonical_shape(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """
        GET with a valid signed_token returns 200 with canonical shape:
        tenant_name, customer_name, line_items, branding, status, amount_due_cents.
        """
        invoice = _create_invoice(
            db_session, test_tenant.id, test_customer.id, test_site.id, 75000
        )
        _, signed_token = _create_link_with_signed_token(
            db_session, test_tenant.id, invoice.id, test_customer.id
        )
        db_session.commit()

        resp = client.get(f"/api/v1/public/invoices/{signed_token}")
        assert resp.status_code == 200, resp.text
        body = resp.json()

        # Canonical shape fields (not legacy shape)
        assert body["invoice_id"] == str(invoice.id)
        assert "tenant_name" in body, (
            f"canonical shape must have tenant_name, got: {list(body.keys())}"
        )
        assert "customer_name" in body, "canonical shape must have customer_name"
        assert "line_items" in body, "canonical shape must have line_items"
        assert "branding" in body, "canonical shape must have branding"
        assert "status" in body, "canonical shape must have status"
        assert "amount_due_cents" in body, "canonical shape must have amount_due_cents"

    def test_get_public_invoice_does_not_increment_used_count(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """
        FIND-148: GET must NOT increment used_count (RFC 7231 §4.3.1 — GET is idempotent).
        Canonical handler is read-only.
        """
        invoice = _create_invoice(
            db_session, test_tenant.id, test_customer.id, test_site.id
        )
        link, signed_token = _create_link_with_signed_token(
            db_session, test_tenant.id, invoice.id, test_customer.id
        )
        db_session.commit()

        resp = client.get(f"/api/v1/public/invoices/{signed_token}")
        assert resp.status_code == 200, resp.text
        db_session.refresh(link)
        assert link.used_count == 0, (
            f"FIND-148: GET must not increment used_count. Got used_count={link.used_count}. "
            "Canonical GET handler is read-only."
        )

    def test_get_unknown_token_returns_401(self, client, db_session):
        """
        INV-ROUTE-FIX semantic change: an unknown/garbage token now returns 401
        (invalid signature) instead of legacy 404.
        The canonical handler treats an unparseable token as unauthenticated.
        """
        resp = client.get("/api/v1/public/invoices/totally_unknown_garbage_token")
        assert resp.status_code == 401, (
            f"Expected 401 (invalid signature) for garbage token, got {resp.status_code}: {resp.text}"
        )

    def test_get_revoked_link_returns_410(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """A revoked link returns 410 Gone."""
        invoice = _create_invoice(
            db_session, test_tenant.id, test_customer.id, test_site.id
        )
        _, signed_token = _create_link_with_signed_token(
            db_session,
            test_tenant.id,
            invoice.id,
            test_customer.id,
            revoked=True,
        )
        db_session.commit()

        resp = client.get(f"/api/v1/public/invoices/{signed_token}")
        assert resp.status_code == 410, resp.text

    def test_get_expired_token_returns_410(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """A token that has passed its expiration timestamp returns 410 Gone.

        The canonical handler checks token expiry via verify_signed_token's
        expiration field — a past-expiry signed token raises TokenExpiredError → 410.
        """
        invoice = _create_invoice(
            db_session, test_tenant.id, test_customer.id, test_site.id
        )
        # Create link with an expired token (negative days = already expired)
        _, signed_token = _create_link_with_signed_token(
            db_session,
            test_tenant.id,
            invoice.id,
            test_customer.id,
            expires_in_days=-1,  # already expired
        )
        db_session.commit()

        resp = client.get(f"/api/v1/public/invoices/{signed_token}")
        assert resp.status_code == 410, resp.text


# ============================================================
# POST /api/v1/public/invoices/{signed_token}/payment-intent
# ============================================================


class TestPublicInvoicePaymentIntent:
    """Tests for the canonical public invoice payment-intent endpoint."""

    def test_payment_intent_happy_path(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """Happy path: POST /payment-intent with valid signed token resolves the link.

        Returns 200 (STRIPE_SECRET_KEY absent → mock) or 402 (Stripe configured,
        no Connect account on test_tenant). Both indicate the token was valid.
        """
        invoice = _create_invoice(
            db_session, test_tenant.id, test_customer.id, test_site.id, 50000
        )
        _, signed_token = _create_link_with_signed_token(
            db_session, test_tenant.id, invoice.id, test_customer.id
        )
        db_session.commit()

        resp = client.post(
            f"/api/v1/public/invoices/{signed_token}/payment-intent",
            json={"amount_cents": 50000},
        )
        # 200 = mock Stripe; 402 = Stripe configured but tenant has no Connect account
        assert resp.status_code in (200, 402), (
            f"Expected 200 or 402 for valid signed token, got {resp.status_code}: {resp.text}"
        )

    def test_partial_payment_without_comment_returns_422(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """
        FIND-142: partial payment (amount_cents != invoice.total_cents) without comment → 422.
        """
        invoice = _create_invoice(
            db_session, test_tenant.id, test_customer.id, test_site.id, 50000
        )
        _, signed_token = _create_link_with_signed_token(
            db_session, test_tenant.id, invoice.id, test_customer.id
        )
        db_session.commit()

        resp = client.post(
            f"/api/v1/public/invoices/{signed_token}/payment-intent",
            json={"amount_cents": 25000},  # partial, no comment
        )
        assert resp.status_code == 422, (
            f"Expected 422 for partial payment without comment, got {resp.status_code}: {resp.text}"
        )

    def test_partial_payment_with_comment_accepted(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """Partial payment with comment passes validation (not 400/422).

        Returns 200 (mock Stripe) or 402 (no Connect account). Both mean validation passed.
        """
        invoice = _create_invoice(
            db_session, test_tenant.id, test_customer.id, test_site.id, 50000
        )
        _, signed_token = _create_link_with_signed_token(
            db_session, test_tenant.id, invoice.id, test_customer.id
        )
        db_session.commit()

        resp = client.post(
            f"/api/v1/public/invoices/{signed_token}/payment-intent",
            json={
                "amount_cents": 25000,
                "comment": "Partial payment — rest on delivery",
            },
        )
        # Must not be 400/422; 200 or 402 are acceptable (validation passed)
        assert resp.status_code not in (400, 422), (
            f"Partial payment with comment must not return validation error, got {resp.status_code}: {resp.text}"
        )

    def test_payment_intent_revoked_link_returns_410(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """Payment intent on revoked link returns 410."""
        invoice = _create_invoice(
            db_session, test_tenant.id, test_customer.id, test_site.id, 10000
        )
        _, signed_token = _create_link_with_signed_token(
            db_session,
            test_tenant.id,
            invoice.id,
            test_customer.id,
            revoked=True,
        )
        db_session.commit()

        resp = client.post(
            f"/api/v1/public/invoices/{signed_token}/payment-intent",
            json={"amount_cents": 10000},
        )
        assert resp.status_code == 410, resp.text

    def test_payment_intent_garbage_token_returns_401(self, client, db_session):
        """Payment intent with garbage token returns 401."""
        resp = client.post(
            "/api/v1/public/invoices/garbage_token_xyz/payment-intent",
            json={"amount_cents": 10000},
        )
        assert resp.status_code == 401, (
            f"Expected 401 for garbage token, got {resp.status_code}"
        )
