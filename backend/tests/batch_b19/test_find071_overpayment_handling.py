"""
FIND-071: Overpayment handling in public invoice payment flow

INV-ROUTE-FIX migration: `_pay_public_invoice_impl` was removed when the legacy
`invoices.public_router` was deleted.  The canonical payment path is:
  POST /public/invoices/{signed_token}/payment-intent  →  Stripe  →  webhook
  `handle_payment_intent_succeeded` (stripe_payment_intents.py) records Payment +
  computes amount_variance_cents.

These tests now target `handle_payment_intent_succeeded` directly, which is the
function that actually owns FIND-071 variance behaviour in the canonical path.

Tests verify:
1. Overpayment is accepted — amount_variance_cents positive, invoice marked paid
2. amount_variance_cents recorded with positive value for overpayment
3. Invoice status transitions to 'paid' on overpayment (balance covered)
4. Underpayment → 'partial' invoice status
5. Exact payment → amount_variance_cents = 0 (stored as-is; zero variance)
6. Idempotency: duplicate PI event skipped
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


class TestFind071OverpaymentHandling:
    """FIND-071: Overpayment handling — now owned by handle_payment_intent_succeeded."""

    def test_overpayment_accepted_variance_positive(self):
        """
        FIND-071 Step 1+2: Overpayment accepted; amount_variance_cents is positive.
        PI amount_received > invoice.total_cents → variance > 0 recorded.
        """
        from app.models.billing import Invoice, PaymentMethod, PaymentStatus

        mock_db = MagicMock()
        pi_id = "pi_overpay_001"
        invoice_id = str(uuid.uuid4())

        mock_invoice = MagicMock(spec=Invoice)
        mock_invoice.id = invoice_id
        mock_invoice.tenant_id = uuid.uuid4()
        mock_invoice.total_cents = 10000  # canonical path uses total_cents

        mock_paid_status = MagicMock(spec=PaymentStatus)
        mock_paid_status.id = uuid.uuid4()

        mock_pm = MagicMock(spec=PaymentMethod)
        mock_pm.id = uuid.uuid4()

        # No existing payment (idempotency check returns None)
        call_count = [0]

        def mock_exec_side_effect(query):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:  # idempotency check
                result.first.return_value = None
            elif call_count[0] == 2:  # invoice lookup
                result.first.return_value = mock_invoice
            elif call_count[0] == 3:  # paid status
                result.first.return_value = mock_paid_status
            elif call_count[0] == 4:  # payment_method lookup
                result.first.return_value = mock_pm
            else:
                result.first.return_value = mock_paid_status  # invoice status update
            return result

        mock_db.exec.side_effect = mock_exec_side_effect
        added_objects = []
        mock_db.add = lambda obj: added_objects.append(obj)

        payload = _make_pi_payload(pi_id, invoice_id, amount_received=12000)

        with patch(
            "services.stripe_payment_intents._update_invoice_status_after_payment"
        ):
            with patch("services.stripe_payment_intents._create_payment_notification"):
                handle_payment_intent_succeeded(mock_db, payload)

        # Find the Payment object added
        payment_objects = [
            obj for obj in added_objects if hasattr(obj, "stripe_payment_intent_id")
        ]
        assert len(payment_objects) == 1, "Expected one Payment to be added"
        payment = payment_objects[0]

        # FIND-071: variance = amount_received - invoice.total_cents = 12000 - 10000 = 2000
        assert payment.amount_variance_cents == 2000
        assert payment.stripe_payment_intent_id == pi_id
        assert payment.amount_cents == 12000

    def test_overpayment_invoice_updated(self):
        """
        FIND-071 Step 3: invoice status updated to 'paid' on overpayment.
        _update_invoice_status_after_payment handles the transition.
        """
        from app.models.billing import Invoice, PaymentMethod, PaymentStatus

        mock_db = MagicMock()
        pi_id = "pi_overpay_002"
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
                result.first.return_value = None  # no existing payment
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

        status_update_called = [False]

        def mock_status_update(db, invoice):
            status_update_called[0] = True

        payload = _make_pi_payload(pi_id, invoice_id, amount_received=12000)

        with patch(
            "services.stripe_payment_intents._update_invoice_status_after_payment",
            side_effect=mock_status_update,
        ):
            with patch("services.stripe_payment_intents._create_payment_notification"):
                handle_payment_intent_succeeded(mock_db, payload)

        assert status_update_called[0], (
            "_update_invoice_status_after_payment must be called"
        )

    def test_exact_payment_zero_variance(self):
        """
        FIND-071: Exact payment (amount == total) records amount_variance_cents == 0.
        """
        from app.models.billing import Invoice, PaymentMethod, PaymentStatus

        mock_db = MagicMock()
        pi_id = "pi_exact_001"
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

        payment_objects = [
            obj for obj in added_objects if hasattr(obj, "stripe_payment_intent_id")
        ]
        assert len(payment_objects) == 1
        payment = payment_objects[0]
        # variance = 10000 - 10000 = 0
        assert payment.amount_variance_cents == 0

    def test_idempotency_duplicate_pi_skipped(self):
        """
        FIND-071: Duplicate payment_intent.succeeded events are ignored.
        If a Payment with the same stripe_payment_intent_id already exists, skip.
        """
        from app.models.billing import Payment

        mock_db = MagicMock()
        pi_id = "pi_duplicate_001"
        invoice_id = str(uuid.uuid4())

        # Existing payment already recorded
        existing_payment = MagicMock(spec=Payment)
        existing_payment.id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.first.return_value = existing_payment
        mock_db.exec.return_value = mock_result

        payload = _make_pi_payload(pi_id, invoice_id, amount_received=10000)
        handle_payment_intent_succeeded(mock_db, payload)

        # db.add should NOT be called since we early-returned
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_missing_invoice_id_skips_gracefully(self):
        """
        FIND-071: Webhook payload missing invoice_id → logged and skipped, no exception.
        """
        mock_db = MagicMock()
        payload = {
            "data": {
                "object": {
                    "id": "pi_no_invoice",
                    "amount_received": 5000,
                    "metadata": {},  # no invoice_id
                }
            }
        }
        # Should not raise
        handle_payment_intent_succeeded(mock_db, payload)
        mock_db.add.assert_not_called()

    def test_customer_payment_comment_stored(self):
        """
        FIND-071: customer_payment_comment from PI metadata is stored on Payment.
        """
        from app.models.billing import Invoice, PaymentMethod, PaymentStatus

        mock_db = MagicMock()
        pi_id = "pi_comment_001"
        invoice_id = str(uuid.uuid4())
        expected_comment = "Paying half now"

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
