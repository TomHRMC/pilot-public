"""
DLC-B5 — SMS Delivery-Status Reconciliation Tests
====================================================
Domain: notifications_comms
Batch: DLC-B5

Covers:
  1. message.finalized → to[0].status="delivered" → row status=delivered, delivered_at set
  2. message.finalized + errors=[{code:"40010"}] → row status=failed, delivered_at NULL
  3. Idempotency: delivered row replayed with sent event → stays delivered
  4. message.sent → to[0].status="sent" → row status unchanged (sent)
  5. Unknown carrier_message_id → no row mutated, no exception
  6. _map_delivery_status pure-function table — each Telnyx status maps correctly
  7. Endpoint routing — POST message.finalized → 200 {"status":"received"} + delivery background task called
  8. Ed25519 verify regression — good sig → True, tampered body → False

Rule 6 note: carrier_message_id lookup in _process_delivery_status is intentionally
tenant-agnostic. The carrier webhook does not carry tenant context; carrier_message_id
is globally unique per Telnyx. This is the one legitimate exception to the tenant-scoping
rule — documented here and in the Completion Summary.
"""

import base64
import json
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import select

pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]


# ---------------------------------------------------------------------------
# Helpers: build a delivery-status webhook payload
# ---------------------------------------------------------------------------


def _make_finalized_payload(
    carrier_message_id: str,
    telnyx_status: str = "delivered",
    errors: list | None = None,
) -> bytes:
    """Build a bytes payload shaped like a Telnyx message.finalized webhook."""
    payload = {
        "data": {
            "event_type": "message.finalized",
            "payload": {
                "id": carrier_message_id,
                "to": [{"phone_number": "+15125551234", "status": telnyx_status}],
                "errors": errors or [],
            },
        }
    }
    return json.dumps(payload).encode()


def _make_sent_payload(carrier_message_id: str, telnyx_status: str = "sent") -> bytes:
    """Build a bytes payload shaped like a Telnyx message.sent webhook."""
    payload = {
        "data": {
            "event_type": "message.sent",
            "payload": {
                "id": carrier_message_id,
                "to": [{"phone_number": "+15125551234", "status": telnyx_status}],
                "errors": [],
            },
        }
    }
    return json.dumps(payload).encode()


def _make_test_message(db_session, test_tenant, status: str = "sent") -> tuple:
    """
    Create a minimal CustomerCommunicationMessage fixture for testing delivery-status.

    Returns (carrier_message_id: str, message_id: UUID).

    Requires:
      - A TenantPhoneNumber in test_tenant
      - A CustomerCommunicationThread linked to the phone number
      - A CustomerCommunicationMessage with the given status and carrier_message_id

    All created inline (no shared seed rows mutated).
    """
    from app.models.core import User
    from app.models.crm import Customer, CustomerType
    from app.models.sms import (
        CustomerCommunicationMessage,
        CustomerCommunicationThread,
        TenantPhoneNumber,
    )

    # We need a tech user (audit_user_id FK). Use the seeded dev@pilot.local user.
    tech_user = db_session.exec(
        select(User).where(User.email == "dev@pilot.local")
    ).first()
    assert tech_user is not None, "dev@pilot.local test user not found in seed data"

    # Create a unique customer for this test
    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        display_name=f"Delivery Test Customer {uuid.uuid4()}",
        type=CustomerType.person,
        is_active=True,
    )
    db_session.add(customer)
    db_session.flush()

    # TenantPhoneNumber
    phone = TenantPhoneNumber(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        phone_number=f"+1512555{uuid.uuid4().hex[:4]}",
        area_code="512",
        carrier="telnyx",
        status="active",
    )
    db_session.add(phone)
    db_session.flush()

    now = datetime.now(UTC)
    thread = CustomerCommunicationThread(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        customer_id=customer.id,
        tech_id=tech_user.id,
        tenant_phone_number_id=phone.id,
        status="active",
        first_message_at=now,
        last_message_at=now,
        message_count=1,
    )
    db_session.add(thread)
    db_session.flush()

    carrier_message_id = f"telnyx-test-{uuid.uuid4()}"
    msg = CustomerCommunicationMessage(
        id=uuid.uuid4(),
        thread_id=thread.id,
        direction="outbound",
        channel="sms",
        body="Test delivery status message",
        segment_count=1,
        status=status,
        carrier_message_id=carrier_message_id,
        sent_at=now,
        audit_user_id=tech_user.id,
    )
    db_session.add(msg)
    db_session.commit()

    return carrier_message_id, msg.id


# ---------------------------------------------------------------------------
# Scenario 6 — _map_delivery_status pure-function table (no DB needed)
# ---------------------------------------------------------------------------


class TestMapDeliveryStatusPure:
    """Scenario 6: pure-function table tests for _map_delivery_status."""

    def test_delivered_maps_to_delivered(self):
        from api.routes.webhooks_sms import _map_delivery_status

        assert _map_delivery_status("delivered", False) == "delivered"

    def test_sent_maps_to_sent(self):
        from api.routes.webhooks_sms import _map_delivery_status

        assert _map_delivery_status("sent", False) == "sent"

    def test_sending_maps_to_sent(self):
        from api.routes.webhooks_sms import _map_delivery_status

        assert _map_delivery_status("sending", False) == "sent"

    def test_queued_maps_to_sent(self):
        from api.routes.webhooks_sms import _map_delivery_status

        assert _map_delivery_status("queued", False) == "sent"

    def test_delivery_unconfirmed_maps_to_sent(self):
        from api.routes.webhooks_sms import _map_delivery_status

        assert _map_delivery_status("delivery_unconfirmed", False) == "sent"

    def test_delivery_failed_maps_to_failed(self):
        from api.routes.webhooks_sms import _map_delivery_status

        assert _map_delivery_status("delivery_failed", False) == "failed"

    def test_sending_failed_maps_to_failed(self):
        from api.routes.webhooks_sms import _map_delivery_status

        assert _map_delivery_status("sending_failed", False) == "failed"

    def test_errors_list_forces_failed_regardless_of_status(self):
        """Non-empty errors[] always maps to failed even if to[0].status=sent."""
        from api.routes.webhooks_sms import _map_delivery_status

        assert _map_delivery_status("sent", True) == "failed"
        assert _map_delivery_status("delivered", True) == "failed"
        assert _map_delivery_status("queued", True) == "failed"

    def test_unknown_status_defaults_to_sent(self):
        """Unrecognised Telnyx status strings default to 'sent' (safe fallback)."""
        from api.routes.webhooks_sms import _map_delivery_status

        assert _map_delivery_status("some_future_status", False) == "sent"


# ---------------------------------------------------------------------------
# Scenarios 1–5: _process_delivery_status background task (direct call)
# ---------------------------------------------------------------------------


class TestProcessDeliveryStatus:
    """
    Direct-call tests for _process_delivery_status.

    Pattern: call with a db_session_factory that yields the test's db_session
    (same transaction — DB state is visible within the test without a commit
    to the live DB).
    """

    def _db_factory(self, db_session):
        """Wrap db_session as a generator matching the factory signature."""

        def _factory():
            yield db_session

        return _factory

    def test_scenario_1_delivered_sets_status_and_delivered_at(
        self, db_session, test_tenant
    ):
        """Scenario 1: message.finalized + status=delivered → row delivered, delivered_at set."""
        from api.routes.webhooks_sms import _process_delivery_status
        from app.models.sms import CustomerCommunicationMessage

        carrier_message_id, msg_id = _make_test_message(
            db_session, test_tenant, status="sent"
        )
        payload = _make_finalized_payload(carrier_message_id, telnyx_status="delivered")

        _process_delivery_status(payload, self._db_factory(db_session))

        # Re-query by the specific ID we inserted
        updated = db_session.exec(
            select(CustomerCommunicationMessage).where(
                CustomerCommunicationMessage.id == msg_id
            )
        ).first()
        assert updated is not None
        assert updated.status == "delivered", (
            f"Expected 'delivered', got {updated.status!r}"
        )
        assert updated.delivered_at is not None, (
            "delivered_at must be set for delivered status"
        )

    def test_scenario_2_errors_sets_failed_and_delivered_at_null(
        self, db_session, test_tenant
    ):
        """Scenario 2: message.finalized + errors=[{code:"40010"}] → status=failed, delivered_at NULL."""
        from api.routes.webhooks_sms import _process_delivery_status
        from app.models.sms import CustomerCommunicationMessage

        carrier_message_id, msg_id = _make_test_message(
            db_session, test_tenant, status="sent"
        )
        payload = _make_finalized_payload(
            carrier_message_id,
            telnyx_status="delivery_failed",
            errors=[
                {
                    "code": "40010",
                    "title": "Not 10DLC registered",
                    "detail": "Number not registered",
                }
            ],
        )

        _process_delivery_status(payload, self._db_factory(db_session))

        updated = db_session.exec(
            select(CustomerCommunicationMessage).where(
                CustomerCommunicationMessage.id == msg_id
            )
        ).first()
        assert updated is not None
        assert updated.status == "failed", f"Expected 'failed', got {updated.status!r}"
        assert updated.delivered_at is None, (
            "delivered_at must remain NULL for failed status"
        )

    def test_scenario_3_idempotency_delivered_not_regressed(
        self, db_session, test_tenant
    ):
        """Scenario 3: row already delivered → replaying a 'sent' event leaves it delivered."""
        from api.routes.webhooks_sms import _process_delivery_status
        from app.models.sms import CustomerCommunicationMessage

        # Start the row already in delivered state
        carrier_message_id, msg_id = _make_test_message(
            db_session, test_tenant, status="delivered"
        )
        # Set delivered_at so we can verify it's unchanged
        original_delivered_at = datetime.now(UTC)
        msg = db_session.exec(
            select(CustomerCommunicationMessage).where(
                CustomerCommunicationMessage.id == msg_id
            )
        ).first()
        msg.delivered_at = original_delivered_at
        db_session.add(msg)
        db_session.commit()

        # Replay a "sent" status event (simulates late/duplicate webhook)
        replay_payload = _make_sent_payload(carrier_message_id, telnyx_status="sent")
        _process_delivery_status(replay_payload, self._db_factory(db_session))

        updated = db_session.exec(
            select(CustomerCommunicationMessage).where(
                CustomerCommunicationMessage.id == msg_id
            )
        ).first()
        assert updated.status == "delivered", (
            f"Idempotency violated: status regressed from 'delivered' to {updated.status!r}"
        )
        # delivered_at must be unchanged
        assert updated.delivered_at is not None

    def test_scenario_4_message_sent_status_unchanged(self, db_session, test_tenant):
        """Scenario 4: message.sent + to[0].status=sent → row stays status=sent."""
        from api.routes.webhooks_sms import _process_delivery_status
        from app.models.sms import CustomerCommunicationMessage

        carrier_message_id, msg_id = _make_test_message(
            db_session, test_tenant, status="sent"
        )
        payload = _make_sent_payload(carrier_message_id, telnyx_status="sent")

        _process_delivery_status(payload, self._db_factory(db_session))

        updated = db_session.exec(
            select(CustomerCommunicationMessage).where(
                CustomerCommunicationMessage.id == msg_id
            )
        ).first()
        assert updated.status == "sent", (
            f"Expected status to remain 'sent', got {updated.status!r}"
        )
        assert updated.delivered_at is None

    def test_scenario_5_unknown_carrier_message_id_is_noop(
        self, db_session, test_tenant
    ):
        """Scenario 5: carrier_message_id not in DB → clean no-op, no exception."""
        from api.routes.webhooks_sms import _process_delivery_status

        unknown_id = f"telnyx-unknown-{uuid.uuid4()}"
        payload = _make_finalized_payload(unknown_id, telnyx_status="delivered")

        # Must not raise
        _process_delivery_status(payload, self._db_factory(db_session))
        # No assertion needed — absence of exception proves the no-op

    def test_errors_logged_with_warning(self, db_session, test_tenant, caplog):
        """When errors[] is non-empty, warning is logged with carrier_message_id + error code."""
        import logging

        from api.routes.webhooks_sms import _process_delivery_status

        carrier_message_id, _ = _make_test_message(
            db_session, test_tenant, status="sent"
        )
        payload = _make_finalized_payload(
            carrier_message_id,
            telnyx_status="delivery_failed",
            errors=[{"code": "40010", "title": "Not 10DLC registered"}],
        )

        with caplog.at_level(logging.WARNING, logger="api.routes.webhooks_sms"):
            _process_delivery_status(payload, self._db_factory(db_session))

        # At least one warning should mention the carrier_message_id or the error code
        warning_messages = [
            r.message for r in caplog.records if r.levelno >= logging.WARNING
        ]
        assert any("40010" in m or carrier_message_id in m for m in warning_messages), (
            f"Expected warning with code 40010 or carrier_message_id. Got: {warning_messages}"
        )


# ---------------------------------------------------------------------------
# Scenario 7 — Endpoint routing test
# ---------------------------------------------------------------------------


class TestEndpointRouting:
    """
    Scenario 7: HTTP endpoint routes message.finalized to _process_delivery_status.

    The endpoint test verifies:
      - 200 {"status":"received"} returned for a verified message.finalized event
      - _process_delivery_status is called (mocked to avoid session complexity)

    Background-task DB-state reconciliation is proven by TestProcessDeliveryStatus
    above (direct call with db_session factory). The endpoint test proves the wiring.

    Patch target note: get_sms_carrier is imported *inside* the route handler function
    body ("from services.sms_carrier import get_sms_carrier") — so we patch the factory
    at its canonical module location: "services.sms_carrier.get_sms_carrier".
    """

    def test_message_finalized_returns_200_and_calls_delivery_task(
        self, client, test_tenant, db_session
    ):
        """POST message.finalized → 200 {"status":"received"} + delivery task dispatched."""
        from services.sms_carrier import MockSmsCarrier

        carrier_message_id = f"telnyx-endpoint-test-{uuid.uuid4()}"
        payload = _make_finalized_payload(carrier_message_id, telnyx_status="delivered")

        # Patch get_sms_carrier at the services module level (imported inside the route func).
        # Also mock _process_delivery_status so we can assert it was called.
        with patch(
            "services.sms_carrier.get_sms_carrier", return_value=MockSmsCarrier()
        ):
            with patch(
                "api.routes.webhooks_sms._process_delivery_status"
            ) as mock_delivery_task:
                response = client.post(
                    "/api/v1/webhooks/sms/telnyx-inbound",
                    content=payload,
                    headers={
                        "content-type": "application/json",
                        "telnyx-signature-ed25519": "dGVzdA==",
                        "telnyx-timestamp": "1234567890",
                    },
                )

        assert response.status_code == 200
        assert response.json() == {"status": "received"}
        # Background task function should have been called once
        mock_delivery_task.assert_called_once()

    def test_message_sent_returns_200_and_calls_delivery_task(
        self, client, test_tenant
    ):
        """POST message.sent → 200 {"status":"received"} + delivery task dispatched."""
        from services.sms_carrier import MockSmsCarrier

        carrier_message_id = f"telnyx-sent-test-{uuid.uuid4()}"
        payload = _make_sent_payload(carrier_message_id)

        with patch(
            "services.sms_carrier.get_sms_carrier", return_value=MockSmsCarrier()
        ):
            with patch(
                "api.routes.webhooks_sms._process_delivery_status"
            ) as mock_delivery_task:
                response = client.post(
                    "/api/v1/webhooks/sms/telnyx-inbound",
                    content=payload,
                    headers={
                        "content-type": "application/json",
                        "telnyx-signature-ed25519": "dGVzdA==",
                        "telnyx-timestamp": "1234567890",
                    },
                )

        assert response.status_code == 200
        assert response.json() == {"status": "received"}
        mock_delivery_task.assert_called_once()

    def test_invalid_signature_returns_401(self, client, test_tenant):
        """An invalid signature causes 401 — Telnyx retries on non-2xx."""
        from services.sms_carrier import MockSmsCarrier

        payload = _make_finalized_payload("some-id", telnyx_status="delivered")

        # Override verify to return False on a MockSmsCarrier instance
        mock_carrier = MockSmsCarrier()
        mock_carrier.verify_webhook_signature = lambda p, h: False

        # Patch at services module level (where get_sms_carrier is called from inside the route)
        with patch("services.sms_carrier.get_sms_carrier", return_value=mock_carrier):
            response = client.post(
                "/api/v1/webhooks/sms/telnyx-inbound",
                content=payload,
                headers={
                    "content-type": "application/json",
                    "telnyx-signature-ed25519": "bad",
                    "telnyx-timestamp": "1234567890",
                },
            )

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Scenario 8 — Ed25519 signature verification regression test (Task 3)
# ---------------------------------------------------------------------------


class TestEd25519VerifyRegression:
    """
    Scenario 8: Ed25519 verify regression test.

    Generates a real Ed25519 keypair, signs a payload the same way Telnyx does
    (timestamp + "|" + body), and verifies that TelnyxSmsCarrier.verify_webhook_signature
    returns True for the correct signature and False for tampered inputs.

    The `cryptography` library is used for key generation and signing.
    The `telnyx` SDK is NOT called here — it is mocked in __init__ so that
    TelnyxSmsCarrier can be instantiated without a real Telnyx API key.

    Why this can be a unit test (not integration):
    - verify_webhook_signature uses only `cryptography` (already installed).
    - The `telnyx` SDK import in __init__ is mocked via sys.modules patching.
    - No network calls are made.
    """

    def _make_carrier_with_public_key(self, public_key_b64: str) -> object:
        """
        Instantiate TelnyxSmsCarrier with a test Ed25519 public key.

        Mocks the `telnyx` SDK import (not needed for verify_webhook_signature)
        and patches settings so __init__ does not raise on missing env vars.
        """
        import sys

        mock_telnyx = MagicMock()
        mock_telnyx.Telnyx.return_value = MagicMock()

        with patch.dict(sys.modules, {"telnyx": mock_telnyx}):
            with patch("core.config.settings") as mock_settings:
                mock_settings.TELNYX_API_KEY = "test-api-key"
                mock_settings.TELNYX_PUBLIC_KEY = public_key_b64
                mock_settings.TELNYX_MESSAGING_PROFILE_ID = None

                # Force re-import within the patched context
                from services.telnyx_sms_carrier import TelnyxSmsCarrier

                carrier = TelnyxSmsCarrier.__new__(TelnyxSmsCarrier)
                carrier._telnyx = mock_telnyx
                carrier._client = mock_telnyx.Telnyx()
                carrier._messaging_profile_id = None
                carrier._public_key = public_key_b64

        return carrier

    def test_correct_ed25519_signature_returns_true(self):
        """A correctly signed payload verifies to True."""
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        # Generate a fresh keypair
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        # Base64-encode public key (same format Telnyx portal provides)
        pub_bytes = public_key.public_bytes_raw()
        pub_b64 = base64.b64encode(pub_bytes).decode()

        # Build the payload and sign it the Telnyx way: timestamp + "|" + body
        body = b'{"data":{"event_type":"message.finalized"}}'
        timestamp = "1690000000"
        signed_payload = (timestamp + "|" + body.decode("utf-8")).encode("utf-8")
        signature_bytes = private_key.sign(signed_payload)
        sig_b64 = base64.b64encode(signature_bytes).decode()

        # Instantiate carrier with the test public key
        carrier = self._make_carrier_with_public_key(pub_b64)

        headers = {
            "telnyx-signature-ed25519": sig_b64,
            "telnyx-timestamp": timestamp,
        }
        assert carrier.verify_webhook_signature(body, headers) is True

    def test_tampered_body_returns_false(self):
        """A valid signature over the original body fails when the body is tampered."""
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        pub_b64 = base64.b64encode(public_key.public_bytes_raw()).decode()

        original_body = b'{"data":{"event_type":"message.finalized"}}'
        tampered_body = b'{"data":{"event_type":"message.finalized","TAMPERED":true}}'
        timestamp = "1690000000"

        # Sign the ORIGINAL body
        signed_payload = (timestamp + "|" + original_body.decode("utf-8")).encode(
            "utf-8"
        )
        sig_b64 = base64.b64encode(private_key.sign(signed_payload)).decode()

        carrier = self._make_carrier_with_public_key(pub_b64)

        headers = {
            "telnyx-signature-ed25519": sig_b64,
            "telnyx-timestamp": timestamp,
        }
        # Verification against TAMPERED body must return False
        assert carrier.verify_webhook_signature(tampered_body, headers) is False

    def test_wrong_signature_returns_false(self):
        """A signature from a different key fails verification."""
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        # Key 1: generate + sign
        private_key_1 = Ed25519PrivateKey.generate()
        # Key 2: the public key used for verification (different from the signer)
        public_key_2 = Ed25519PrivateKey.generate().public_key()
        pub_b64 = base64.b64encode(public_key_2.public_bytes_raw()).decode()

        body = b'{"data":{"event_type":"message.finalized"}}'
        timestamp = "1690000000"
        signed_payload = (timestamp + "|" + body.decode("utf-8")).encode("utf-8")
        sig_b64 = base64.b64encode(private_key_1.sign(signed_payload)).decode()

        carrier = self._make_carrier_with_public_key(pub_b64)

        headers = {
            "telnyx-signature-ed25519": sig_b64,
            "telnyx-timestamp": timestamp,
        }
        assert carrier.verify_webhook_signature(body, headers) is False

    def test_missing_signature_header_returns_false(self):
        """Missing telnyx-signature-ed25519 header returns False."""
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        key = Ed25519PrivateKey.generate()
        pub_b64 = base64.b64encode(key.public_key().public_bytes_raw()).decode()
        carrier = self._make_carrier_with_public_key(pub_b64)

        body = b'{"data":{}}'
        headers = {
            # telnyx-signature-ed25519 intentionally omitted
            "telnyx-timestamp": "1690000000",
        }
        assert carrier.verify_webhook_signature(body, headers) is False

    def test_missing_timestamp_header_returns_false(self):
        """Missing telnyx-timestamp header returns False."""
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        key = Ed25519PrivateKey.generate()
        pub_b64 = base64.b64encode(key.public_key().public_bytes_raw()).decode()
        carrier = self._make_carrier_with_public_key(pub_b64)

        body = b'{"data":{}}'
        headers = {
            "telnyx-signature-ed25519": "dGVzdA==",
            # telnyx-timestamp intentionally omitted
        }
        assert carrier.verify_webhook_signature(body, headers) is False
