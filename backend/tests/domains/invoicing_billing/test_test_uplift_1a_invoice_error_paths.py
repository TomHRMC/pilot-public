"""TEST-UPLIFT-1A — Invoice error-path coverage (§C.1 priority burn-down #2, #4).

Covers:
  - POST /api/v1/invoices/{invoice_id}/send → 404 unknown invoice (RFC 7807)
  - POST /api/v1/public/invoices/{signed_token}/confirm-payment → 401 garbage
    token (RFC 7807)

These are money-path endpoints whose error responses must follow RFC 7807
Problem Details (Rule 8). The send-invoice 404 was found returning a plain
string detail — fixed in this batch to the RFC 7807 dict shape.
"""

import uuid

import pytest

pytestmark = [
    pytest.mark.domain_invoicing_billing,
    pytest.mark.unit,
]


class TestInvoiceSendErrorPaths:
    """POST /api/v1/invoices/{invoice_id}/send — error paths."""

    def test_send_invoice_404_unknown_invoice_rfc7807(
        self, client, test_tenant, test_user, mock_cognito_jwt
    ):
        """404 for an invoice UUID that does not exist in this tenant — RFC 7807 body."""
        mock_cognito_jwt(test_user)
        fake_invoice_id = uuid.uuid4()

        resp = client.post(
            f"/api/v1/invoices/{fake_invoice_id}/send",
            json={},
        )

        assert resp.status_code == 404
        problem = resp.json()["detail"]
        assert problem["type"] == "https://errors.pilotfortrades.com/not-found"
        assert problem["title"] == "Invoice not found"
        assert problem["status"] == 404
        assert "does not exist" in problem["detail"]


class TestPublicInvoiceConfirmPaymentErrorPaths:
    """POST /api/v1/public/invoices/{signed_token}/confirm-payment — error paths."""

    def test_confirm_payment_401_garbage_token_rfc7807(self, client, test_tenant):
        """401 for a garbage signed_token — RFC 7807 body (no auth required).

        The body must include the required ``payment_intent_id`` field so
        FastAPI body validation passes and the handler reaches the token
        verification path (which raises 401).
        """
        garbage_token = "garbage-token-that-will-fail-verification"

        resp = client.post(
            f"/api/v1/public/invoices/{garbage_token}/confirm-payment",
            json={"payment_intent_id": "pi_garbage_test_001"},
        )

        assert resp.status_code == 401
        problem = resp.json()["detail"]
        assert problem["type"] == "https://errors.pilotfortrades.com/invalid-link"
        assert problem["title"] == "Invalid link"
        assert problem["status"] == 401
        assert "invalid" in problem["detail"].lower()
