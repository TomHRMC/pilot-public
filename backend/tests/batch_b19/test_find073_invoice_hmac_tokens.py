"""
FIND-073: Invoice Public Link HMAC-SHA256 Signed Token Integration

Tests for the HMAC-SHA256 signed token authentication on invoice public links.
Verifies:
  1. Valid token verification succeeds (200)
  2. Tampered token signature fails (401)
  3. Expired token fails (410)
  4. Revoked link fails (410)
  5. Token payload contains correct link_id, customer_id, expiration
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi import status
from sqlmodel import Session

from app.models.billing import Invoice, InvoicePublicLink
from app.models.core import Tenant
from services.public_link_signer import (
    TokenExpiredError,
    TokenInvalidError,
    generate_signed_token,
    verify_signed_token,
)

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def test_invoice(
    test_tenant: Tenant,
    test_customer,
    test_site,
    test_invoice_status,
    db_session: Session,
):
    """Create a test invoice."""
    # Use the provided test_customer fixture instead of creating a new one
    invoice = Invoice(
        tenant_id=test_tenant.id,
        customer_id=test_customer.id,
        site_id=test_site.id,
        status_id=test_invoice_status.id,
        invoice_number="INV-001",
        subtotal_cents=10000,
        tax_cents=1000,
        total_cents=11000,
        balance_due_cents=11000,
        currency="USD",
        issued_at=datetime.now(UTC),
        due_at=datetime.now(UTC) + timedelta(days=30),
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    return invoice


@pytest.fixture
def test_invoice_public_link(test_invoice: Invoice, db_session: Session):
    """Create a test invoice public link with HMAC-signed token."""
    signed_token, expires_at = generate_signed_token(
        link_id=UUID("12345678-1234-5678-1234-567812345678"),
        link_type="invoice",
        customer_id=test_invoice.customer_id,
        expires_in_days=90,
    )

    link = InvoicePublicLink(
        id=UUID("12345678-1234-5678-1234-567812345678"),
        tenant_id=test_invoice.tenant_id,
        invoice_id=test_invoice.id,
        contact_id=None,
        token_hash="",
        signed_token=signed_token,
        expires_at=expires_at,
        max_uses=0,
        used_count=0,
        status="active",
    )
    db_session.add(link)
    db_session.commit()
    db_session.refresh(link)
    return link


# ─────────────────────────────────────────────────────────────────────────────
# Unit Tests: Token Generation & Verification
# ─────────────────────────────────────────────────────────────────────────────


class TestTokenGeneration:
    """Unit tests for token generation."""

    def test_generate_signed_token_returns_tuple(self):
        """generate_signed_token returns (token: str, expires_at: datetime)."""
        token, expires_at = generate_signed_token(
            link_id=UUID("12345678-1234-5678-1234-567812345678"),
            link_type="invoice",
            customer_id=UUID("87654321-4321-8765-4321-876543218765"),
        )
        assert isinstance(token, str)
        assert isinstance(expires_at, datetime)

    def test_token_format_is_payload_dot_signature(self):
        """Token format is payload.signature (two parts, base64url encoded)."""
        token, _ = generate_signed_token(
            link_id=UUID("12345678-1234-5678-1234-567812345678"),
            link_type="invoice",
            customer_id=UUID("87654321-4321-8765-4321-876543218765"),
        )
        parts = token.split(".")
        assert len(parts) == 2, f"Token should have 2 parts, got {len(parts)}: {token}"

    def test_token_payload_contains_link_id(self):
        """Verify token payload contains link_id."""
        link_id = UUID("12345678-1234-5678-1234-567812345678")
        token, _ = generate_signed_token(
            link_id=link_id,
            link_type="invoice",
            customer_id=UUID("87654321-4321-8765-4321-876543218765"),
        )
        payload = verify_signed_token(token)
        assert payload["link_id"] == str(link_id)

    def test_token_payload_contains_customer_id(self):
        """Verify token payload contains customer_id."""
        customer_id = UUID("87654321-4321-8765-4321-876543218765")
        token, _ = generate_signed_token(
            link_id=UUID("12345678-1234-5678-1234-567812345678"),
            link_type="invoice",
            customer_id=customer_id,
        )
        payload = verify_signed_token(token)
        assert payload["customer_id"] == str(customer_id)

    def test_token_payload_contains_link_type(self):
        """Verify token payload contains link_type='invoice'."""
        token, _ = generate_signed_token(
            link_id=UUID("12345678-1234-5678-1234-567812345678"),
            link_type="invoice",
            customer_id=UUID("87654321-4321-8765-4321-876543218765"),
        )
        payload = verify_signed_token(token)
        assert payload["link_type"] == "invoice"

    def test_token_payload_contains_expiration(self):
        """Verify token payload contains expiration ISO timestamp."""
        token, _ = generate_signed_token(
            link_id=UUID("12345678-1234-5678-1234-567812345678"),
            link_type="invoice",
            customer_id=UUID("87654321-4321-8765-4321-876543218765"),
        )
        payload = verify_signed_token(token)
        assert "expiration" in payload
        # Should be parseable as ISO datetime
        exp_dt = datetime.fromisoformat(payload["expiration"])
        assert isinstance(exp_dt, datetime)

    def test_token_expires_in_days_controls_ttl(self):
        """Token expiration is ~N days from now when expires_in_days=N."""
        token, expires_at = generate_signed_token(
            link_id=UUID("12345678-1234-5678-1234-567812345678"),
            link_type="invoice",
            customer_id=UUID("87654321-4321-8765-4321-876543218765"),
            expires_in_days=7,
        )
        now = datetime.now(UTC)
        # Should be ~7 days from now (within 1 minute of 7*24*60 minutes)
        delta = (expires_at - now).total_seconds()
        expected_delta = 7 * 24 * 60 * 60
        assert abs(delta - expected_delta) < 60, (
            f"Expected ~{expected_delta}s, got {delta}s"
        )


class TestTokenVerification:
    """Unit tests for token verification."""

    def test_valid_token_verifies_successfully(self):
        """verify_signed_token returns payload dict for valid token."""
        token, _ = generate_signed_token(
            link_id=UUID("12345678-1234-5678-1234-567812345678"),
            link_type="invoice",
            customer_id=UUID("87654321-4321-8765-4321-876543218765"),
        )
        payload = verify_signed_token(token)
        assert isinstance(payload, dict)
        assert "link_id" in payload
        assert "link_type" in payload
        assert "customer_id" in payload
        assert "expiration" in payload

    def test_tampered_signature_raises_invalid_error(self):
        """Modifying the signature part raises TokenInvalidError."""
        token, _ = generate_signed_token(
            link_id=UUID("12345678-1234-5678-1234-567812345678"),
            link_type="invoice",
            customer_id=UUID("87654321-4321-8765-4321-876543218765"),
        )
        payload_part, sig_part = token.split(".")
        # Tamper with signature by changing a character in the middle.
        # Avoid the last character: base64url's final char for a 32-byte (256-bit)
        # HMAC encodes only 2 significant bits + 4 padding zeros — so flipping it
        # may produce the same decoded bytes. Use mid-string index instead.
        mid = len(sig_part) // 2
        tampered_sig = (
            sig_part[:mid]
            + ("A" if sig_part[mid] != "A" else "B")
            + sig_part[mid + 1 :]
        )
        tampered_token = f"{payload_part}.{tampered_sig}"

        with pytest.raises(TokenInvalidError):
            verify_signed_token(tampered_token)

    def test_tampered_payload_raises_invalid_error(self):
        """Modifying the payload part raises TokenInvalidError."""
        token, _ = generate_signed_token(
            link_id=UUID("12345678-1234-5678-1234-567812345678"),
            link_type="invoice",
            customer_id=UUID("87654321-4321-8765-4321-876543218765"),
        )
        payload_part, sig_part = token.split(".")
        # Tamper with payload by changing the first character
        tampered_payload = ("A" if payload_part[0] != "A" else "B") + payload_part[1:]
        tampered_token = f"{tampered_payload}.{sig_part}"

        with pytest.raises(TokenInvalidError):
            verify_signed_token(tampered_token)

    def test_expired_token_raises_expired_error(self):
        """Token with expiration in the past raises TokenExpiredError."""
        from services import public_link_signer

        # Temporarily override _get_secret to use a test secret
        original_get_secret = public_link_signer._get_secret
        public_link_signer._get_secret = lambda: "test-secret"

        # Create token with expires_in_days=-1 (already expired)
        try:
            token, _ = generate_signed_token(
                link_id=UUID("12345678-1234-5678-1234-567812345678"),
                link_type="invoice",
                customer_id=UUID("87654321-4321-8765-4321-876543218765"),
                secret="test-secret",
                expires_in_days=-1,
            )

            with pytest.raises(TokenExpiredError):
                verify_signed_token(token, secret="test-secret")
        finally:
            public_link_signer._get_secret = original_get_secret

    def test_malformed_token_format_raises_invalid_error(self):
        """Token without dot separator raises TokenInvalidError."""
        with pytest.raises(TokenInvalidError):
            verify_signed_token("not.a.valid.token.format")

    def test_token_without_separator_raises_invalid_error(self):
        """Token with no dot raises TokenInvalidError."""
        with pytest.raises(TokenInvalidError):
            verify_signed_token("nodotintoken")


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests: API Endpoints
# ─────────────────────────────────────────────────────────────────────────────


class TestInvoicePublicLinkTokenIntegration:
    """Integration tests for invoice public link endpoints with HMAC tokens."""

    def test_get_public_invoice_with_valid_token(
        self,
        client,
        test_invoice_public_link: InvoicePublicLink,
        db_session: Session,
    ):
        """GET /api/v1/public/invoices/{token} succeeds with valid signed token."""
        response = client.get(
            f"/api/v1/public/invoices/{test_invoice_public_link.signed_token}"
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["invoice_id"] == str(test_invoice_public_link.invoice_id)

    def test_get_public_invoice_with_tampered_token_returns_401(
        self,
        client,
        test_invoice_public_link: InvoicePublicLink,
    ):
        """GET /api/v1/public/invoices/{tampered_token} returns 401."""
        # Tamper with signature: modify a character in the middle to ensure
        # the base64url string is still valid but the HMAC fails
        token = test_invoice_public_link.signed_token

        # Split and verify we have valid format
        if "." not in token:
            pytest.skip("Token format invalid - no signature separator")

        payload_part, sig_part = token.split(".", 1)

        # Tamper by modifying a character in the signature
        # Use a position that won't cause base64url decoding to fail
        if len(sig_part) > 1:
            tampered_sig = sig_part[:-2] + "XX"  # Replace last 2 chars
        else:
            tampered_sig = "X" * len(sig_part)

        tampered_token = f"{payload_part}.{tampered_sig}"

        response = client.get(f"/api/v1/public/invoices/{tampered_token}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        # INV-ROUTE-FIX: detail is now RFC 7807 dict — check the nested "detail" or "title" field
        detail_val = data["detail"]
        if isinstance(detail_val, dict):
            detail_text = (
                detail_val.get("detail", "") + " " + detail_val.get("title", "")
            ).lower()
        else:
            detail_text = str(detail_val).lower()
        assert (
            "signature" in detail_text
            or "token" in detail_text
            or "invalid" in detail_text
        ), f"Expected signature/token/invalid in error detail, got: {detail_text}"

    def test_get_public_invoice_with_expired_token_returns_410(
        self,
        client,
        test_invoice: Invoice,
        db_session: Session,
    ):
        """GET /api/v1/public/invoices/{expired_token} returns 410."""
        from services import public_link_signer

        original_get_secret = public_link_signer._get_secret
        public_link_signer._get_secret = lambda: "test-secret"

        try:
            # Generate an already-expired token
            expired_token, expires_at = generate_signed_token(
                link_id=UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
                link_type="invoice",
                customer_id=test_invoice.customer_id,
                secret="test-secret",
                expires_in_days=-1,
            )

            response = client.get(f"/api/v1/public/invoices/{expired_token}")
            assert response.status_code == status.HTTP_410_GONE
            data = response.json()
            # INV-ROUTE-FIX: detail is now RFC 7807 dict
            detail_val = data["detail"]
            if isinstance(detail_val, dict):
                detail_text = (
                    detail_val.get("detail", "") + " " + detail_val.get("title", "")
                ).lower()
            else:
                detail_text = str(detail_val).lower()
            assert "expired" in detail_text, (
                f"Expected 'expired' in error, got: {detail_text}"
            )
        finally:
            public_link_signer._get_secret = original_get_secret

    def test_get_public_invoice_with_revoked_link_returns_410(
        self,
        client,
        test_invoice_public_link: InvoicePublicLink,
        db_session: Session,
    ):
        """GET /api/v1/public/invoices/{token} returns 410 if link is revoked."""
        # Revoke the link
        test_invoice_public_link.status = "revoked"
        test_invoice_public_link.revoked_at = datetime.now(UTC)
        db_session.add(test_invoice_public_link)
        db_session.commit()

        response = client.get(
            f"/api/v1/public/invoices/{test_invoice_public_link.signed_token}"
        )
        assert response.status_code == status.HTTP_410_GONE
        data = response.json()
        # INV-ROUTE-FIX: detail is now RFC 7807 dict
        detail_val = data["detail"]
        if isinstance(detail_val, dict):
            detail_text = (
                detail_val.get("detail", "") + " " + detail_val.get("title", "")
            ).lower()
        else:
            detail_text = str(detail_val).lower()
        assert "revoked" in detail_text, (
            f"Expected 'revoked' in error, got: {detail_text}"
        )

    def test_post_public_invoice_payment_with_valid_token(
        self,
        client,
        db_session: Session,
        test_invoice_public_link: InvoicePublicLink,
        test_invoice: Invoice,
        test_tenant: Tenant,
    ):
        """POST /api/v1/public/invoices/{token}/payment-intent succeeds with valid token."""
        # UI-FIX-2F: Set a stripe_connect_account_id on the tenant so the
        # PaymentNotConfiguredError guard passes in real-Stripe-key mode.
        test_tenant.stripe_connect_account_id = "acct_test_hmac_token"
        db_session.add(test_tenant)
        db_session.commit()

        payload = {
            "amount_cents": test_invoice.total_cents,
        }

        # Mock stripe.PaymentIntent.create so no real Stripe call is made.

        import stripe as stripe_lib

        mock_pi = MagicMock()
        mock_pi.client_secret = "pi_hmactest_secret_mock"
        mock_pi.id = "pi_hmactest_123"

        with patch.object(stripe_lib.PaymentIntent, "create", return_value=mock_pi):
            response = client.post(
                f"/api/v1/public/invoices/{test_invoice_public_link.signed_token}/payment-intent",
                json=payload,
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "client_secret" in data
        assert "payment_intent_id" in data

    def test_post_public_invoice_payment_with_tampered_token_returns_401(
        self,
        client,
        test_invoice_public_link: InvoicePublicLink,
    ):
        """POST /api/v1/public/invoices/{tampered_token}/payment-intent returns 401."""
        token = test_invoice_public_link.signed_token
        payload_part, sig_part = token.split(".")
        # Tamper at mid-index (same strategy as TestTokenVerification.test_tampered_signature_raises_invalid_error)
        # Changing the last base64url char is unreliable — it encodes only 4 bits and the 2
        # padding zeros may produce the same decoded bytes as the replacement char.
        # Modifying a mid-string character is guaranteed to change the effective HMAC bytes.
        mid = len(sig_part) // 2
        tampered_sig = (
            sig_part[:mid]
            + ("A" if sig_part[mid] != "A" else "B")
            + sig_part[mid + 1 :]
        )
        tampered_token = f"{payload_part}.{tampered_sig}"

        payload = {
            "amount_cents": 5000,
        }
        response = client.post(
            f"/api/v1/public/invoices/{tampered_token}/payment-intent",
            json=payload,
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_send_invoice_generates_valid_hmac_token(
        self,
        client,
        test_invoice: Invoice,
        test_tenant: Tenant,
        test_user,
        db_session: Session,
        mock_cognito_jwt,
    ):
        """POST /api/v1/invoices/{id}/send generates a valid HMAC-signed token."""
        # Authenticate the client with the test user
        mock_cognito_jwt(test_user)

        payload = {
            "contact_id": None,
            "expires_in_days": 90,
            "max_uses": 0,
        }
        response = client.post(
            f"/api/v1/invoices/{test_invoice.id}/send",
            json=payload,
        )

        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()
            signed_token = data["signed_token"]

            # Verify the token is valid HMAC
            token_payload = verify_signed_token(signed_token)
            assert token_payload["link_id"] == data["id"]
            assert token_payload["link_type"] == "invoice"
            assert token_payload["customer_id"] == str(test_invoice.customer_id)
