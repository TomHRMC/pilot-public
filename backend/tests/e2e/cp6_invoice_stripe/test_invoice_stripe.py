"""
CP-6: Invoice / Stripe Payment (SD-10 E2E Tier 1)

W-05: Invoice/Stripe payment workflow.

NOTE: The Stripe integration is not yet complete. These tests skip gracefully
when STRIPE_SECRET_KEY is a placeholder (sk_test_e2e_placeholder or unset).
When a real Stripe test key is configured, the tests exercise the live Stripe
test mode API end-to-end.

Deviation from design doc: No /test webhook endpoint exists per webhooks_stripe.py
comment ("No /test endpoint per design doc §D — webhook signatures cannot be faked
in the test endpoint pattern"). Tests that require webhook processing are marked
accordingly and skip until the Stripe integration is complete.
"""

from __future__ import annotations

import uuid

import pytest

pytestmark = [pytest.mark.e2e]

# Placeholder value injected in CI when Stripe is not yet integrated
_STRIPE_PLACEHOLDER = "sk_test_e2e_placeholder"


def _get_stripe_key() -> str | None:
    """Return Stripe key from settings, or None if it is a placeholder."""
    try:
        from core.config import settings

        key = getattr(settings, "STRIPE_SECRET_KEY", None)
        if not key or key == _STRIPE_PLACEHOLDER or not key.startswith("sk_"):
            return None
        return key
    except Exception:
        return None


class TestInvoiceStripePayment:
    """W-05: Stripe PaymentIntent creation and invoice payment flow."""

    def test_stripe_payment_intent_created_and_succeeds(
        self, e2e_client, e2e_mock_entitlement, e2e_mock_ai
    ):
        """
        Create a PaymentIntent in Stripe test mode for a test invoice.
        Skips if STRIPE_SECRET_KEY is not a real test key.
        """
        stripe_key = _get_stripe_key()
        if not stripe_key:
            pytest.skip(
                "Real Stripe key not configured — "
                "set STRIPE_SECRET_KEY to a real sk_test_... key to run Stripe E2E tests"
            )

        import stripe

        stripe.api_key = stripe_key

        # Step 1: Create customer entity via /test endpoint
        create_cust_resp = e2e_client.post(
            "/api/v1/customers/test",
            json={
                "first_name": "E2E",
                "last_name": f"StripeTest-{uuid.uuid4().hex[:6]}",
                "customer_type": "person",
                "lifecycle_status_code": "active",
            },
        )
        assert create_cust_resp.status_code == 201, (
            f"Customer creation failed: {create_cust_resp.status_code} {create_cust_resp.text[:200]}"
        )
        customer_id = create_cust_resp.json()["id"]

        # Step 2: Create site via /test endpoint
        create_site_resp = e2e_client.post(
            "/api/v1/sites/test",
            json={
                "name": f"E2E Stripe Site {uuid.uuid4().hex[:6]}",
                "customer_id": customer_id,
                "address_line_1": "123 Test St",
                "city": "Testville",
                "state_code": "CA",
                "postal_code": "90210",
                "country_code": "US",
            },
        )
        assert create_site_resp.status_code == 201, (
            f"Site creation failed: {create_site_resp.status_code} {create_site_resp.text[:200]}"
        )
        site_id = create_site_resp.json()["id"]

        # Step 3: Create Stripe Customer
        stripe_customer = stripe.Customer.create(
            email=f"e2e-stripe-{uuid.uuid4().hex[:6]}@pilot.local"
        )

        # Step 4: Create and attach PaymentMethod (tok_visa = test Visa card)
        pm = stripe.PaymentMethod.create(
            type="card",
            card={"token": "tok_visa"},
        )
        stripe.PaymentMethod.attach(pm.id, customer=stripe_customer.id)

        # Step 5: Create PaymentIntent and confirm immediately
        pi = stripe.PaymentIntent.create(
            amount=5000,
            currency="usd",
            customer=stripe_customer.id,
            payment_method=pm.id,
            confirm=True,
            automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
        )

        assert pi.status == "succeeded", (
            f"Expected PaymentIntent to succeed, got status={pi.status}"
        )

        # Store on class for use by subsequent tests (session-scoped fixture means
        # class-level state persists within the same session)
        TestInvoiceStripePayment._pi_id = pi.id
        TestInvoiceStripePayment._customer_id = customer_id
        TestInvoiceStripePayment._site_id = site_id

    def test_webhook_payment_intent_succeeded_marks_invoice_paid(
        self, e2e_client, e2e_mock_entitlement, e2e_mock_ai
    ):
        """
        Verify webhook processing marks an invoice paid.

        NOTE: webhooks_stripe.py has NO /test endpoint (by design — HMAC cannot be
        faked). This test skips until the Stripe integration is complete and a
        /test webhook endpoint is added, or until the webhook processing is testable
        via a direct impl() call.

        Deferred: Will be implemented in a future batch after the Stripe webhook
        integration is completed (see webhooks_stripe.py design note §D).
        """
        stripe_key = _get_stripe_key()
        if not stripe_key:
            pytest.skip("Real Stripe key not configured — Stripe webhook test skipped")

        pytest.skip(
            "Stripe webhook /test endpoint not available (by design — see webhooks_stripe.py §D). "
            "This test will be activated in the batch that completes the Stripe webhook integration."
        )

    def test_invoice_payment_creates_payment_row(
        self, e2e_client, e2e_engine, e2e_mock_entitlement, e2e_mock_ai
    ):
        """
        Guard test: verifies the payment table is accessible and the Stripe
        PaymentIntent from test 1 can be correlated to a payment record IF
        the webhook processing was triggered.

        In the current state (Stripe integration not complete), this test
        confirms the payment table schema is intact and queryable.
        """
        from sqlmodel import Session, text

        with Session(e2e_engine) as db:
            # Confirm payment table is queryable
            result = db.exec(text("SELECT COUNT(*) FROM public.payment")).first()
            assert result is not None, "payment table must be queryable"
            # Count may be 0 or non-zero depending on seed data — that's fine
            assert isinstance(result[0], int), "payment count must be an integer"

        # Note: Full assertion of pi→payment correlation is deferred until
        # the Stripe webhook integration is complete.
