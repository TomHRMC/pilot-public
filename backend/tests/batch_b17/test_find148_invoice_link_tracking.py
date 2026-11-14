"""
FIND-148 (S1 Critical) — GET /public/invoices/{signed_token} must be read-only.

INV-ROUTE-FIX migration: updated to use HMAC signed tokens (canonical handler only).
The legacy token_hash lookup path via invoices.public_router is gone.

Before the fix: `_get_public_invoice_impl` wrote `last_used_at`, `used_count`,
`db.add(link)`, `db.commit()` on every GET — violating RFC 7231 §4.3.1.

After the fix: GET is fully read-only. The canonical handler (public_invoices.py)
never touches used_count or last_used_at on GET.

Test plan:
  - GET invoice → used_count unchanged after call (read-only confirmed)
  - Multiple GET calls → used_count remains 0 (no caching proxy inflation)
  - The canonical GET returns correct invoice data

Test subfolder: tests/batch_b17/
"""

import secrets as _secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from app.models.billing import (
    Currency,
    Invoice,
    InvoicePublicLink,
    InvoiceStatus,
)
from services.public_link_signer import generate_signed_token

# ---------------------------------------------------------------------------
# Helpers — updated to create HMAC signed_token links
# ---------------------------------------------------------------------------


def _ensure_currency(db_session: Session) -> None:
    if not db_session.exec(select(Currency).where(Currency.code == "USD")).first():
        db_session.add(Currency(code="USD", name="US Dollar", symbol="$"))
        db_session.flush()


def _get_or_create_invoice_status(
    db_session: Session, code: str = "sent"
) -> InvoiceStatus:
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


def _create_invoice(
    db_session: Session,
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
        subtotal_cents=50000,
        tax_cents=0,
        total_cents=balance_due_cents,
        balance_due_cents=balance_due_cents,
        is_active=True,
    )
    db_session.add(invoice)
    db_session.flush()
    return invoice


def _create_link(
    db_session: Session,
    tenant_id: uuid.UUID,
    invoice_id: uuid.UUID,
    customer_id: uuid.UUID,
    used_count: int = 0,
    last_used_at=None,
    expires_in_days: int = 30,
) -> tuple[InvoicePublicLink, str]:
    """Create an InvoicePublicLink with HMAC signed_token. Returns (link, signed_token)."""
    link = InvoicePublicLink(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        invoice_id=invoice_id,
        token_hash=_secrets.token_hex(32),  # NOT NULL column
        status="active",
        expires_at=datetime.now(UTC) + timedelta(days=expires_in_days),
        max_uses=0,
        used_count=used_count,
        last_used_at=last_used_at,
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


class TestGetPublicInvoiceReadOnly:
    """
    FIND-148: GET /api/v1/public/invoices/{signed_token} must not modify DB state.
    The canonical handler (public_invoices.py) is fully read-only.
    """

    def test_get_does_not_increment_used_count(
        self, client, db_session: Session, test_tenant, test_customer, test_site
    ):
        """
        GET invoice link → used_count must remain 0 after the call.
        """
        invoice = _create_invoice(
            db_session, test_tenant.id, test_customer.id, test_site.id
        )
        link, signed_token = _create_link(
            db_session, test_tenant.id, invoice.id, test_customer.id, used_count=0
        )
        db_session.commit()

        response = client.get(f"/api/v1/public/invoices/{signed_token}")
        assert response.status_code == 200, f"GET failed: {response.text}"

        # Re-fetch the link to check DB state
        db_session.expire(link)
        db_session.refresh(link)
        assert link.used_count == 0, (
            f"FIND-148 regression: GET incremented used_count to {link.used_count}. "
            "Canonical GET /public/invoices must be read-only."
        )

    def test_get_does_not_set_last_used_at(
        self, client, db_session: Session, test_tenant, test_customer, test_site
    ):
        """
        GET invoice link → last_used_at must remain NULL after the call.
        """
        invoice = _create_invoice(
            db_session, test_tenant.id, test_customer.id, test_site.id
        )
        link, signed_token = _create_link(
            db_session,
            test_tenant.id,
            invoice.id,
            test_customer.id,
            used_count=0,
            last_used_at=None,
        )
        db_session.commit()

        response = client.get(f"/api/v1/public/invoices/{signed_token}")
        assert response.status_code == 200, f"GET failed: {response.text}"

        db_session.expire(link)
        db_session.refresh(link)
        assert link.last_used_at is None, (
            f"FIND-148 regression: GET set last_used_at to {link.last_used_at}. "
            "Canonical GET /public/invoices must not write last_used_at."
        )

    def test_multiple_get_calls_do_not_inflate_used_count(
        self, client, db_session: Session, test_tenant, test_customer, test_site
    ):
        """
        Multiple GET calls (simulating caching proxy replay) must not increment used_count.
        """
        invoice = _create_invoice(
            db_session, test_tenant.id, test_customer.id, test_site.id
        )
        link, signed_token = _create_link(
            db_session, test_tenant.id, invoice.id, test_customer.id, used_count=0
        )
        db_session.commit()

        # Three successive GETs (simulating proxy replay)
        for i in range(3):
            resp = client.get(f"/api/v1/public/invoices/{signed_token}")
            assert resp.status_code == 200, f"GET #{i + 1} failed: {resp.text}"

        db_session.expire(link)
        db_session.refresh(link)
        assert link.used_count == 0, (
            f"FIND-148 regression: 3 GET calls inflated used_count to {link.used_count}. "
            "Caching proxy replays must not cause silent used_count increments."
        )

    def test_get_returns_invoice_data_correctly(
        self, client, db_session: Session, test_tenant, test_customer, test_site
    ):
        """
        Regression guard: GET returns correct invoice_id and canonical shape fields.
        """
        invoice = _create_invoice(
            db_session,
            test_tenant.id,
            test_customer.id,
            test_site.id,
            balance_due_cents=12500,
        )
        _, signed_token = _create_link(
            db_session, test_tenant.id, invoice.id, test_customer.id
        )
        db_session.commit()

        response = client.get(f"/api/v1/public/invoices/{signed_token}")
        assert response.status_code == 200, f"GET failed: {response.text}"

        body = response.json()
        assert str(invoice.id) == body.get("invoice_id"), (
            f"Expected invoice_id={invoice.id}, got {body.get('invoice_id')}"
        )
        # Canonical shape: amount_due_cents (not legacy balance_due_cents)
        assert "amount_due_cents" in body, (
            f"Canonical shape must include amount_due_cents, got keys: {list(body.keys())}"
        )
        assert body.get("amount_due_cents") == 12500, (
            f"Expected amount_due_cents=12500, got {body.get('amount_due_cents')}"
        )
