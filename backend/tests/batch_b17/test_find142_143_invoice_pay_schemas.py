"""
FIND-142 (S2 High) — PublicInvoicePayRequest: add customer_payment_comment field +
conditional NOT NULL enforcement when amount < balance.

FIND-143 (S2 High) — InvoicePublicLinkResponse: replace token_hash with signed_token.

INV-ROUTE-FIX migration:
  - POST /pay endpoint removed; canonical payment path is POST /payment-intent.
  - FIND-142 partial-payment enforcement now tested via POST /payment-intent.
  - FIND-143 tests unchanged (verify send endpoint returns signed_token).

Test plan:
  FIND-142:
    - PublicInvoicePayRequest has customer_payment_comment field (optional) [schema test]
    - POST /payment-intent: partial payment (amount != invoice.total_cents) without comment → 422
    - POST /payment-intent: partial payment with comment → accepted
    - POST /payment-intent: full payment without comment → no 422

  FIND-143:
    - InvoicePublicLinkResponse has signed_token field (NOT token_hash)
    - POST /send returns signed_token in response (not token_hash)
    - signed_token is usable in GET /public/invoices/{signed_token}

Test subfolder: tests/batch_b17/
"""

import secrets as _secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from services.public_link_signer import generate_signed_token

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_invoice_and_link(
    db_session: Session, tenant_id, customer_id, site_id, balance=50000
):
    """Create an invoice + link with HMAC signed_token; return (invoice, signed_token)."""
    from app.models.billing import Currency, Invoice, InvoicePublicLink, InvoiceStatus

    if not db_session.exec(select(Currency).where(Currency.code == "USD")).first():
        db_session.add(Currency(code="USD", name="US Dollar", symbol="$"))
        db_session.flush()

    status = db_session.exec(
        select(InvoiceStatus).where(
            InvoiceStatus.code == "sent", InvoiceStatus.tenant_id.is_(None)
        )
    ).first()
    if not status:
        status = InvoiceStatus(
            id=uuid.uuid4(),
            tenant_id=None,
            code="sent",
            name="Sent",
            is_default=True,
            is_active=True,
        )
        db_session.add(status)
        db_session.flush()

    invoice = Invoice(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        invoice_number=f"INV-{uuid.uuid4().hex[:8].upper()}",
        customer_id=customer_id,
        site_id=site_id,
        status_id=status.id,
        currency="USD",
        subtotal_cents=balance,
        tax_cents=0,
        total_cents=balance,
        balance_due_cents=balance,
        is_active=True,
    )
    db_session.add(invoice)
    db_session.flush()

    link = InvoicePublicLink(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        invoice_id=invoice.id,
        token_hash=_secrets.token_hex(32),
        status="active",
        expires_at=datetime.now(UTC) + timedelta(days=30),
        max_uses=0,
        used_count=0,
    )
    db_session.add(link)
    db_session.flush()

    signed_token, _ = generate_signed_token(
        link_id=link.id,
        link_type="invoice",
        customer_id=customer_id,
        expires_in_days=30,
    )
    link.signed_token = signed_token
    db_session.flush()

    return invoice, signed_token


# ---------------------------------------------------------------------------
# FIND-142 schema tests
# ---------------------------------------------------------------------------


class TestPublicInvoicePayRequestSchema:
    """FIND-142: PublicInvoicePayRequest must have customer_payment_comment."""

    def test_schema_has_customer_payment_comment(self):
        from api.schemas.schemas import PublicInvoicePayRequest

        assert "customer_payment_comment" in PublicInvoicePayRequest.model_fields

    def test_customer_payment_comment_is_optional(self):
        from api.schemas.schemas import PublicInvoicePayRequest

        field = PublicInvoicePayRequest.model_fields["customer_payment_comment"]
        assert field.default is None, "customer_payment_comment must default to None"


# ---------------------------------------------------------------------------
# FIND-142 HTTP tests — migrated from /pay to /payment-intent (canonical)
# ---------------------------------------------------------------------------


class TestPartialPaymentCommentEnforcement:
    """
    FIND-142: conditional NOT NULL — partial payment (amount != total) requires comment.
    Now enforced via POST /payment-intent (canonical handler).
    """

    def test_partial_payment_without_comment_returns_422(
        self, client, db_session: Session, test_tenant, test_customer, test_site
    ):
        """
        POST /payment-intent: partial payment without comment → 422.
        The canonical handler checks: if amount_cents != invoice.total_cents AND no comment → 422.
        """
        db_session.commit()
        invoice, signed_token = _create_invoice_and_link(
            db_session, test_tenant.id, test_customer.id, test_site.id, balance=10000
        )
        db_session.commit()

        response = client.post(
            f"/api/v1/public/invoices/{signed_token}/payment-intent",
            json={
                "amount_cents": 5000,  # partial: 50% of 100.00
                # no comment
            },
        )
        assert response.status_code == 422, (
            f"FIND-142: partial payment without comment must return 422. "
            f"Got {response.status_code}: {response.text}"
        )

    def test_partial_payment_with_comment_is_accepted(
        self, client, db_session: Session, test_tenant, test_customer, test_site
    ):
        """
        POST /payment-intent: partial payment with comment → accepted.
        """
        db_session.commit()
        invoice, signed_token = _create_invoice_and_link(
            db_session, test_tenant.id, test_customer.id, test_site.id, balance=10000
        )
        db_session.commit()

        response = client.post(
            f"/api/v1/public/invoices/{signed_token}/payment-intent",
            json={
                "amount_cents": 5000,
                "comment": "Paying half now, rest on delivery",
            },
        )
        assert response.status_code not in (400, 422), (
            f"FIND-142: partial payment WITH comment must not return 400/422. "
            f"Got {response.status_code}: {response.text}"
        )

    def test_full_payment_without_comment_is_accepted(
        self, client, db_session: Session, test_tenant, test_customer, test_site
    ):
        """
        POST /payment-intent: full payment (amount == total) without comment → no 422.
        """
        db_session.commit()
        invoice, signed_token = _create_invoice_and_link(
            db_session, test_tenant.id, test_customer.id, test_site.id, balance=10000
        )
        db_session.commit()

        response = client.post(
            f"/api/v1/public/invoices/{signed_token}/payment-intent",
            json={
                "amount_cents": 10000,  # full payment
                # no comment — should be fine
            },
        )
        assert response.status_code not in (400, 422), (
            f"FIND-142: full payment without comment must not require comment. "
            f"Got {response.status_code}: {response.text}"
        )


# ---------------------------------------------------------------------------
# FIND-143 tests
# ---------------------------------------------------------------------------


class TestInvoicePublicLinkResponseSignedToken:
    """
    FIND-143: InvoicePublicLinkResponse must use signed_token, not token_hash.
    """

    def test_schema_has_signed_token_not_token_hash(self):
        from api.schemas.schemas import InvoicePublicLinkResponse

        fields = InvoicePublicLinkResponse.model_fields
        assert "signed_token" in fields, (
            "InvoicePublicLinkResponse must have 'signed_token' field (FIND-143)"
        )
        assert "token_hash" not in fields, (
            "InvoicePublicLinkResponse must NOT have 'token_hash' field — "
            "token_hash is the internal SHA-256 DB key and must not be exposed to frontend"
        )

    def test_send_endpoint_returns_signed_token(
        self, client, db_session: Session, test_tenant, test_customer, test_site
    ):
        """
        POST /invoices/{id}/send/test must return signed_token in response body.
        The signed_token must be usable in GET /public/invoices/{signed_token}.
        """
        from app.models.billing import Currency, Invoice, InvoiceStatus

        if not db_session.exec(select(Currency).where(Currency.code == "USD")).first():
            db_session.add(Currency(code="USD", name="US Dollar", symbol="$"))
            db_session.flush()

        ist = db_session.exec(
            select(InvoiceStatus).where(
                InvoiceStatus.code == "sent", InvoiceStatus.tenant_id.is_(None)
            )
        ).first()
        if not ist:
            ist = InvoiceStatus(
                id=uuid.uuid4(),
                tenant_id=None,
                code="sent",
                name="Sent",
                is_default=True,
                is_active=True,
            )
            db_session.add(ist)
            db_session.flush()

        invoice = Invoice(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            invoice_number=f"INV-FIND143-{uuid.uuid4().hex[:6].upper()}",
            customer_id=test_customer.id,
            site_id=test_site.id,
            status_id=ist.id,
            currency="USD",
            subtotal_cents=10000,
            tax_cents=0,
            total_cents=10000,
            balance_due_cents=10000,
            is_active=True,
        )
        db_session.add(invoice)
        db_session.commit()

        # Generate public link via test endpoint
        send_resp = client.post(
            f"/api/v1/invoices/{invoice.id}/send/test",
            json={"expires_in_days": 7, "max_uses": 0},
        )
        assert send_resp.status_code == 201, f"Send failed: {send_resp.text}"
        body = send_resp.json()

        # FIND-143: must return signed_token, not token_hash
        assert "signed_token" in body, (
            f"FIND-143: response must contain 'signed_token', got keys: {list(body.keys())}"
        )
        assert "token_hash" not in body, (
            "FIND-143: response must NOT expose 'token_hash' (SHA-256 internal key)"
        )

        # signed_token must be usable in the GET URL (canonical handler)
        signed_token = body["signed_token"]
        get_resp = client.get(f"/api/v1/public/invoices/{signed_token}")
        assert get_resp.status_code == 200, (
            f"GET with signed_token failed: {get_resp.status_code}: {get_resp.text}"
        )
        # Canonical shape check
        get_body = get_resp.json()
        assert "tenant_name" in get_body, (
            f"Canonical shape must include tenant_name, got: {list(get_body.keys())}"
        )
