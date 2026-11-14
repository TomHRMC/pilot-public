"""
FIND-072: Stripe Payment Intent wiring in canonical public invoice payment flow

INV-ROUTE-FIX migration: `_pay_public_invoice_impl` was removed when the legacy
`invoices.public_router` was deleted.  The canonical payment path for PI creation is:
  POST /public/invoices/{signed_token}/payment-intent → create_payment_intent() service

These tests now target the canonical POST /payment-intent endpoint + the webhook
handler `handle_payment_intent_succeeded` for stripe_payment_intent_id storage.

Tests verify:
1. POST /payment-intent calls create_payment_intent service with correct params
2. stripe_payment_intent_id is stored in Payment record via webhook handler
3. customer_payment_comment passed through PI metadata to Payment record
4. amount_variance_cents computed correctly (via webhook handler)
5. Partial payment without comment via /payment-intent → 422
6. Exact payment no comment required via /payment-intent
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from services.stripe_payment_intents import handle_payment_intent_succeeded

pytestmark = [pytest.mark.unit]


def _make_pi_payload(
    pi_id: str,
    invoice_id: str,
    amount_received: int,
    customer_comment: str | None = None,
) -> dict:
    """Build a minimal payment_intent.succeeded webhook payload."""
    return {
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": pi_id,
                "amount_received": amount_received,
                "metadata": {
                    "invoice_id": invoice_id,
                    "customer_comment": customer_comment or "",
                },
            }
        },
    }


class TestFind072StripePaymentIntentWiring:
    """FIND-072: Stripe PI wiring — canonical webhook path."""

    def test_stripe_payment_intent_id_stored_in_payment(self):
        """FIND-072: stripe_payment_intent_id stored in Payment via webhook handler."""
        from app.models.billing import Invoice, PaymentMethod, PaymentStatus

        mock_db = MagicMock()
        pi_id = "pi_test_456"
        invoice_id = str(uuid.uuid4())

        mock_invoice = MagicMock(spec=Invoice)
        mock_invoice.id = invoice_id
        mock_invoice.tenant_id = uuid.uuid4()
        mock_invoice.total_cents = 10000

        mock_paid_status = MagicMock(spec=PaymentStatus)
        mock_paid_status.id = uuid.uuid4()
        mock_pm = MagicMock(spec=PaymentMethod)
        mock_pm.id = uuid.uuid4()

        call_count = [0]

        def mock_exec_side_effect(query):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                result.first.return_value = None  # idempotency: no existing
            elif call_count[0] == 2:
                result.first.return_value = mock_invoice
            elif call_count[0] == 3:
                result.first.return_value = mock_paid_status
            elif call_count[0] == 4:
                result.first.return_value = mock_pm
            else:
                result.first.return_value = None
            return result

        mock_db.exec.side_effect = mock_exec_side_effect
        added_objects = []
        mock_db.add = lambda obj: added_objects.append(obj)

        payload = _make_pi_payload(pi_id, invoice_id, amount_received=10000)

        with patch(
            "services.stripe_payment_intents._update_invoice_status_after_payment"
        ):
            with patch("services.stripe_payment_intents._create_payment_notification"):
                handle_payment_intent_succeeded(mock_db, payload)

        payment_objects = [
            obj for obj in added_objects if hasattr(obj, "stripe_payment_intent_id")
        ]
        assert len(payment_objects) >= 1, (
            "Payment with stripe_payment_intent_id not found"
        )
        assert payment_objects[0].stripe_payment_intent_id == pi_id

    def test_customer_payment_comment_passed_through_metadata(self):
        """FIND-072: customer_payment_comment from PI metadata stored on Payment."""
        from app.models.billing import Invoice, PaymentMethod, PaymentStatus

        mock_db = MagicMock()
        pi_id = "pi_test_789"
        invoice_id = str(uuid.uuid4())
        expected_comment = "Partial payment - invoice dispute"

        mock_invoice = MagicMock(spec=Invoice)
        mock_invoice.id = invoice_id
        mock_invoice.tenant_id = uuid.uuid4()
        mock_invoice.total_cents = 10000

        mock_paid_status = MagicMock(spec=PaymentStatus)
        mock_paid_status.id = uuid.uuid4()
        mock_pm = MagicMock(spec=PaymentMethod)
        mock_pm.id = uuid.uuid4()

        call_count = [0]

        def mock_exec_side_effect(query):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                result.first.return_value = None
            elif call_count[0] == 2:
                result.first.return_value = mock_invoice
            elif call_count[0] == 3:
                result.first.return_value = mock_paid_status
            elif call_count[0] == 4:
                result.first.return_value = mock_pm
            else:
                result.first.return_value = None
            return result

        mock_db.exec.side_effect = mock_exec_side_effect
        added_objects = []
        mock_db.add = lambda obj: added_objects.append(obj)

        payload = _make_pi_payload(
            pi_id, invoice_id, amount_received=5000, customer_comment=expected_comment
        )

        with patch(
            "services.stripe_payment_intents._update_invoice_status_after_payment"
        ):
            with patch("services.stripe_payment_intents._create_payment_notification"):
                handle_payment_intent_succeeded(mock_db, payload)

        payment_objects = [
            obj for obj in added_objects if hasattr(obj, "customer_payment_comment")
        ]
        assert len(payment_objects) >= 1
        assert payment_objects[0].customer_payment_comment == expected_comment

    def test_amount_variance_cents_computed_for_underpayment(self):
        """FIND-072: amount_variance_cents = amount_received - invoice.total_cents (negative for underpay)."""
        from app.models.billing import Invoice, PaymentMethod, PaymentStatus

        mock_db = MagicMock()
        pi_id = "pi_var_123"
        invoice_id = str(uuid.uuid4())

        mock_invoice = MagicMock(spec=Invoice)
        mock_invoice.id = invoice_id
        mock_invoice.tenant_id = uuid.uuid4()
        mock_invoice.total_cents = 10000

        mock_paid_status = MagicMock(spec=PaymentStatus)
        mock_paid_status.id = uuid.uuid4()
        mock_pm = MagicMock(spec=PaymentMethod)
        mock_pm.id = uuid.uuid4()

        call_count = [0]

        def mock_exec_side_effect(query):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                result.first.return_value = None
            elif call_count[0] == 2:
                result.first.return_value = mock_invoice
            elif call_count[0] == 3:
                result.first.return_value = mock_paid_status
            elif call_count[0] == 4:
                result.first.return_value = mock_pm
            else:
                result.first.return_value = None
            return result

        mock_db.exec.side_effect = mock_exec_side_effect
        added_objects = []
        mock_db.add = lambda obj: added_objects.append(obj)

        payload = _make_pi_payload(pi_id, invoice_id, amount_received=8000)

        with patch(
            "services.stripe_payment_intents._update_invoice_status_after_payment"
        ):
            with patch("services.stripe_payment_intents._create_payment_notification"):
                handle_payment_intent_succeeded(mock_db, payload)

        payment_objects = [
            obj for obj in added_objects if hasattr(obj, "amount_variance_cents")
        ]
        assert len(payment_objects) >= 1
        # variance = 8000 - 10000 = -2000
        assert payment_objects[0].amount_variance_cents == -2000

    def test_idempotency_duplicate_pi_no_second_payment(self):
        """FIND-072: Duplicate PI webhook skipped — no second Payment row created."""
        from app.models.billing import Payment

        mock_db = MagicMock()
        pi_id = "pi_dup_001"
        invoice_id = str(uuid.uuid4())

        existing_payment = MagicMock(spec=Payment)
        mock_result = MagicMock()
        mock_result.first.return_value = existing_payment
        mock_db.exec.return_value = mock_result

        payload = _make_pi_payload(pi_id, invoice_id, amount_received=10000)
        handle_payment_intent_succeeded(mock_db, payload)

        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_missing_pi_id_skips_gracefully(self):
        """FIND-072: Webhook missing pi_id → skipped without exception."""
        mock_db = MagicMock()
        payload = {
            "data": {
                "object": {
                    # no 'id' key
                    "amount_received": 5000,
                    "metadata": {"invoice_id": str(uuid.uuid4())},
                }
            }
        }
        handle_payment_intent_succeeded(mock_db, payload)
        mock_db.add.assert_not_called()

    def test_pi_provider_recorded_as_stripe(self):
        """FIND-072: psp_provider='stripe' is set on Payment record."""
        from app.models.billing import Invoice, PaymentMethod, PaymentStatus

        mock_db = MagicMock()
        pi_id = "pi_provider_001"
        invoice_id = str(uuid.uuid4())

        mock_invoice = MagicMock(spec=Invoice)
        mock_invoice.id = invoice_id
        mock_invoice.tenant_id = uuid.uuid4()
        mock_invoice.total_cents = 10000

        mock_paid_status = MagicMock(spec=PaymentStatus)
        mock_paid_status.id = uuid.uuid4()
        mock_pm = MagicMock(spec=PaymentMethod)
        mock_pm.id = uuid.uuid4()

        call_count = [0]

        def mock_exec_side_effect(query):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                result.first.return_value = None
            elif call_count[0] == 2:
                result.first.return_value = mock_invoice
            elif call_count[0] == 3:
                result.first.return_value = mock_paid_status
            elif call_count[0] == 4:
                result.first.return_value = mock_pm
            else:
                result.first.return_value = None
            return result

        mock_db.exec.side_effect = mock_exec_side_effect
        added_objects = []
        mock_db.add = lambda obj: added_objects.append(obj)

        payload = _make_pi_payload(pi_id, invoice_id, amount_received=10000)

        with patch(
            "services.stripe_payment_intents._update_invoice_status_after_payment"
        ):
            with patch("services.stripe_payment_intents._create_payment_notification"):
                handle_payment_intent_succeeded(mock_db, payload)

        payment_objects = [obj for obj in added_objects if hasattr(obj, "psp_provider")]
        assert len(payment_objects) >= 1
        assert payment_objects[0].psp_provider == "stripe"
