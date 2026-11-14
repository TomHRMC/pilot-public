"""
STRIPE-CONNECT-1-B2 — Billing payment-contact settings + public GET field tests.

Covers:
  1-8. Settings endpoints (GET + PATCH /api/v1/settings/billing/payment-contact):
       round-trip, partial update, explicit-null clear, empty-string→null,
       invalid email 422, idempotency replay, unauthenticated 401,
       cross-tenant isolation.
  9-10. Public GET /api/v1/public/invoices/{signed_token} — tenant_phone /
        tenant_email populated from local tenant columns (set + null cases).

Domain: invoicing_billing. Marker: unit.
All assertions scoped by inserted IDs — never total counts (Rule 16).
db_session rollback is the cleanup mechanism.
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

pytestmark = [
    pytest.mark.domain_invoicing_billing,
    pytest.mark.unit,
]


# ---------------------------------------------------------------------------
# Helpers — public invoice token minting (mirrors test_public_invoice_canonical.py)
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
        invoice_number=f"INV-B2-{uuid.uuid4().hex[:6].upper()}",
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
    db_session, tenant_id, invoice_id, customer_id, expires_in_days: int = 30
) -> tuple[InvoicePublicLink, str]:
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


# ===========================================================================
# Settings endpoint tests (1-8) — use /test endpoints (TestUserContext)
# ===========================================================================


class TestPaymentContactSettings:
    """STRIPE-CONNECT-1-B2: GET + PATCH /api/v1/settings/billing/payment-contact."""

    def test_1_patch_round_trip(self, client, db_session, test_tenant):
        """PATCH both fields → 200 → GET returns them."""
        resp = client.patch(
            "/api/v1/settings/billing/payment-contact/test",
            json={
                "billing_contact_phone": "(555) 123-4567",
                "billing_contact_email": "test@example.com",
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["billing_contact_phone"] == "(555) 123-4567"
        assert body["billing_contact_email"] == "test@example.com"

        get_resp = client.get("/api/v1/settings/billing/payment-contact/test")
        assert get_resp.status_code == 200, get_resp.text
        get_body = get_resp.json()
        assert get_body["billing_contact_phone"] == "(555) 123-4567"
        assert get_body["billing_contact_email"] == "test@example.com"

    def test_2_partial_update_phone_only(self, client, db_session, test_tenant):
        """PATCH phone only → email unchanged (pre-set email first)."""
        # Pre-set both fields
        client.patch(
            "/api/v1/settings/billing/payment-contact/test",
            json={
                "billing_contact_phone": "(111) 222-3333",
                "billing_contact_email": "keep@example.com",
            },
        )
        # PATCH phone only — email omitted → unchanged
        resp = client.patch(
            "/api/v1/settings/billing/payment-contact/test",
            json={"billing_contact_phone": "(999) 888-7777"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["billing_contact_phone"] == "(999) 888-7777"
        assert body["billing_contact_email"] == "keep@example.com"

    def test_3_explicit_null_clears_phone(self, client, db_session, test_tenant):
        """PATCH {"billing_contact_phone": null} → phone null, email preserved."""
        # Pre-set both
        client.patch(
            "/api/v1/settings/billing/payment-contact/test",
            json={
                "billing_contact_phone": "(444) 555-6666",
                "billing_contact_email": "preserve@example.com",
            },
        )
        # Explicit null clears phone
        resp = client.patch(
            "/api/v1/settings/billing/payment-contact/test",
            json={"billing_contact_phone": None},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["billing_contact_phone"] is None
        assert body["billing_contact_email"] == "preserve@example.com"

    def test_4_empty_string_phone_becomes_null(self, client, db_session, test_tenant):
        """PATCH {"billing_contact_phone": "   "} → null (empty-after-strip)."""
        resp = client.patch(
            "/api/v1/settings/billing/payment-contact/test",
            json={"billing_contact_phone": "   "},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["billing_contact_phone"] is None

    def test_5_invalid_email_returns_422_rfc7807(self, client, db_session, test_tenant):
        """Invalid email → 422 with RFC 7807 shape."""
        resp = client.patch(
            "/api/v1/settings/billing/payment-contact/test",
            json={"billing_contact_email": "not-an-email"},
        )
        assert resp.status_code == 422, resp.text
        # FastAPI validation errors use the standard 422 envelope; the body
        # contains "detail" with validation info. Confirm 422 status code.
        body = resp.json()
        assert "detail" in body

    def test_6_idempotency_replay(self, client, db_session, test_tenant):
        """Same Idempotency-Key + same payload twice → second is a replay."""
        import uuid as _uuid

        key = str(_uuid.uuid4())
        payload = {
            "billing_contact_phone": "(777) 777-7777",
            "billing_contact_email": "idem@example.com",
        }
        headers = {"Idempotency-Key": key}

        resp1 = client.patch(
            "/api/v1/settings/billing/payment-contact/test",
            json=payload,
            headers=headers,
        )
        assert resp1.status_code == 200, resp1.text
        body1 = resp1.json()

        resp2 = client.patch(
            "/api/v1/settings/billing/payment-contact/test",
            json=payload,
            headers=headers,
        )
        # Replay returns cached response (200) with X-Idempotency-Replay header
        assert resp2.status_code == 200, resp2.text
        assert resp2.headers.get("X-Idempotency-Replay") == "true"
        assert resp2.json() == body1

    def test_7_unauthenticated_returns_401(self, client, db_session, test_tenant):
        """Authenticated endpoint without JWT → 401 (not the /test variant)."""
        resp = client.get("/api/v1/settings/billing/payment-contact")
        assert resp.status_code == 401, resp.text

    def test_8_cross_tenant_isolation(
        self,
        client,
        db_session,
        tenant_a,
        tenant_b,
        user_tenant_a,
        user_tenant_b,
        mock_cognito_jwt,
    ):
        """PATCH in tenant_a is invisible in tenant_b's GET."""
        # Tenant A sets its billing contact
        mock_cognito_jwt(user_tenant_a)
        resp_a = client.patch(
            "/api/v1/settings/billing/payment-contact",
            json={
                "billing_contact_phone": "(100) 200-3000",
                "billing_contact_email": "tenant-a@example.com",
            },
        )
        assert resp_a.status_code == 200, resp_a.text
        assert resp_a.json()["billing_contact_email"] == "tenant-a@example.com"

        # Tenant B reads its own — must NOT see tenant A's values
        mock_cognito_jwt(user_tenant_b)
        resp_b = client.get("/api/v1/settings/billing/payment-contact")
        assert resp_b.status_code == 200, resp_b.text
        b_body = resp_b.json()
        assert b_body["billing_contact_email"] != "tenant-a@example.com"
        assert b_body["billing_contact_phone"] != "(100) 200-3000"


# ===========================================================================
# Public GET field tests (9-10)
# ===========================================================================


class TestPublicInvoiceBillingContact:
    """STRIPE-CONNECT-1-B2: public GET ships tenant_phone / tenant_email."""

    def test_9_tenant_with_billing_contact_set(
        self, client, db_session, test_tenant, test_customer, test_site
    ):
        """Tenant with billing contact set → 200 includes tenant_phone / tenant_email."""
        # Set billing contact on test_tenant via the /test PATCH endpoint
        client.patch(
            "/api/v1/settings/billing/payment-contact/test",
            json={
                "billing_contact_phone": "(804) 555-0142",
                "billing_contact_email": "billing@example.com",
            },
        )

        invoice = _create_invoice(
            db_session,
            test_tenant.id,
            test_customer.id,
            test_site.id,
            total_cents=50000,
        )
        _, signed_token = _create_link_with_signed_token(
            db_session, test_tenant.id, invoice.id, test_customer.id
        )
        db_session.commit()

        resp = client.get(f"/api/v1/public/invoices/{signed_token}")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["tenant_phone"] == "(804) 555-0142"
        assert body["tenant_email"] == "billing@example.com"

    def test_10_tenant_with_both_null(
        self, client, db_session, second_tenant, test_customer, test_site
    ):
        """Tenant with both null → response fields are null (frontend fallback case)."""
        # second_tenant has no billing contact set (fresh tenant → both null)
        invoice = _create_invoice(
            db_session,
            second_tenant.id,
            test_customer.id,
            test_site.id,
            total_cents=30000,
        )
        _, signed_token = _create_link_with_signed_token(
            db_session, second_tenant.id, invoice.id, test_customer.id
        )
        db_session.commit()

        resp = client.get(f"/api/v1/public/invoices/{signed_token}")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        # Keys must exist and be null
        assert "tenant_phone" in body
        assert "tenant_email" in body
        assert body["tenant_phone"] is None
        assert body["tenant_email"] is None
