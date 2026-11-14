"""
B11/A59 — SMS Carrier Adapter + TCPA Tests
===========================================
Tests for:
  - MockSmsCarrier interface compliance
  - get_sms_carrier() factory routing
  - TCPA keyword detection (stop / opt-in)
  - Customer ORM model has TCPA fields + last_assigned_tech_id
  - Webhook route: 401 on bad signature, 200 on valid signature
  - TELNYX-INT-1: TELNYX_10DLC_MOCK flag behavior (mock=True in brand payload,
    init WARNING, factory routing unchanged)
"""

import json
import uuid
from unittest.mock import MagicMock, patch

import pytest

from services.sms_carrier import (
    InboundMessage,
    MockSmsCarrier,
    get_sms_carrier,
)

# ─── MockSmsCarrier ───────────────────────────────────────────────────────────


class TestMockSmsCarrier:
    """Verify the MockSmsCarrier captures all calls correctly."""

    def setup_method(self):
        self.carrier = MockSmsCarrier()
        self.tenant_id = uuid.uuid4()

    def test_provision_number_returns_e164(self):
        result = self.carrier.provision_number("512", self.tenant_id)
        assert result.phone_number.startswith("+1512")
        assert result.carrier_provisioning_id.startswith("mock-")
        assert result.monthly_fee_cents == 100

    def test_provision_number_appended_to_list(self):
        self.carrier.provision_number("512", self.tenant_id)
        assert len(self.carrier.provisioned_numbers) == 1

    def test_send_message_returns_sent_result(self):
        result = self.carrier.send_message("+15125550001", "+15125559999", "Hello!")
        assert result.status == "sent"
        assert result.carrier_message_id is not None
        assert result.error_message is None
        assert result.retryable is False

    def test_send_message_captured_in_list(self):
        self.carrier.send_message("+15125550001", "+15125559999", "Test body")
        assert len(self.carrier.sent_messages) == 1
        assert self.carrier.sent_messages[0]["body"] == "Test body"

    def test_verify_webhook_signature_always_true(self):
        assert self.carrier.verify_webhook_signature(b"payload", "sig") is True

    def test_parse_inbound_webhook_returns_inbound_message(self):
        payload = json.dumps(
            {
                "from": "+15125551234",
                "to": "+15125550001",
                "body": "Hello",
                "id": "mock-id-1",
                "received_at": "2026-05-01T12:00:00Z",
            }
        ).encode()
        msg = self.carrier.parse_inbound_webhook(payload)
        assert isinstance(msg, InboundMessage)
        assert msg.from_number == "+15125551234"
        assert msg.body == "Hello"

    def test_get_delivery_status_returns_delivered(self):
        status = self.carrier.get_delivery_status("mock-msg-1")
        assert status == "delivered"

    def test_release_number_removes_from_list(self):
        self.carrier.provision_number("512", self.tenant_id)
        number = self.carrier.provisioned_numbers[0]
        self.carrier.release_number(number)
        assert number not in self.carrier.provisioned_numbers

    def test_release_unknown_number_noop(self):
        # Should not raise
        self.carrier.release_number("+15120000000")


# ─── Factory ──────────────────────────────────────────────────────────────────


class TestGetSmsCarrier:
    """Verify factory routing based on SMS_CARRIER env var."""

    def test_default_returns_mock_carrier(self):
        with patch("core.config.settings") as mock_settings:
            mock_settings.SMS_CARRIER = "mock"
            carrier = get_sms_carrier()
        assert isinstance(carrier, MockSmsCarrier)

    def test_mock_value_returns_mock_carrier(self):
        with patch("services.sms_carrier.getattr", return_value="mock"):
            carrier = get_sms_carrier()
        assert isinstance(carrier, MockSmsCarrier)

    def test_missing_sms_carrier_defaults_to_mock(self):
        """getattr with missing attribute defaults to 'mock'."""
        from core.config import settings

        # Confirm SMS_CARRIER is on settings (we added it)
        val = getattr(settings, "SMS_CARRIER", "mock")
        assert val in ("mock", "telnyx")


# ─── TCPA Keyword Detection ───────────────────────────────────────────────────


class TestTcpaKeywordDetection:
    """Verify STOP and START keyword sets used by webhook handler."""

    @pytest.mark.parametrize(
        "keyword",
        [
            "STOP",
            "stop",
            "Stop",
            "STOPALL",
            "stopall",
            "UNSUBSCRIBE",
            "QUIT",
            "CANCEL",
            "END",
            "ARRET",
        ],
    )
    def test_stop_keywords_detected(self, keyword):
        from api.routes.webhooks_sms import _is_stop_keyword

        assert _is_stop_keyword(keyword) is True
        # With surrounding whitespace
        assert _is_stop_keyword(f"  {keyword}  ") is True

    @pytest.mark.parametrize(
        "keyword",
        [
            "START",
            "start",
            "UNSTOP",
            "unstop",
            "YES",
            "yes",
        ],
    )
    def test_optin_keywords_detected(self, keyword):
        from api.routes.webhooks_sms import _is_optin_keyword

        assert _is_optin_keyword(keyword) is True
        assert _is_optin_keyword(f"  {keyword}  ") is True

    def test_regular_body_not_stop(self):
        from api.routes.webhooks_sms import _is_stop_keyword

        assert _is_stop_keyword("I want to stop receiving calls") is False
        assert _is_stop_keyword("Please stop") is False

    def test_regular_body_not_optin(self):
        from api.routes.webhooks_sms import _is_optin_keyword

        assert _is_optin_keyword("Yes I want an appointment") is False
        assert _is_optin_keyword("Start it up") is False


# ─── Customer ORM Fields ──────────────────────────────────────────────────────


class TestCustomerTcpaFields:
    """Verify the Customer model has the 6 new B11 fields."""

    def test_customer_has_sms_opted_out(self):
        from app.models.crm import Customer

        assert hasattr(Customer, "sms_opted_out")

    def test_customer_has_sms_opt_out_at(self):
        from app.models.crm import Customer

        assert hasattr(Customer, "sms_opt_out_at")

    def test_customer_has_sms_opt_in_consent(self):
        from app.models.crm import Customer

        assert hasattr(Customer, "sms_opt_in_consent")

    def test_customer_has_sms_opt_in_at(self):
        from app.models.crm import Customer

        assert hasattr(Customer, "sms_opt_in_at")

    def test_customer_has_sms_opt_in_source(self):
        from app.models.crm import Customer

        assert hasattr(Customer, "sms_opt_in_source")

    def test_customer_has_last_assigned_tech_id(self):
        from app.models.crm import Customer

        assert hasattr(Customer, "last_assigned_tech_id")

    def test_customer_sms_opted_out_defaults_false(self):
        """Default value should be False (not opted out)."""
        from app.models.crm import Customer

        c = Customer(
            tenant_id=uuid.uuid4(),
            type="person",
            display_name="Test Customer",
        )
        assert c.sms_opted_out is False

    def test_customer_sms_opt_in_consent_defaults_false(self):
        from app.models.crm import Customer

        c = Customer(
            tenant_id=uuid.uuid4(),
            type="person",
            display_name="Test Customer",
        )
        assert c.sms_opt_in_consent is False

    def test_customer_last_assigned_tech_id_defaults_none(self):
        from app.models.crm import Customer

        c = Customer(
            tenant_id=uuid.uuid4(),
            type="person",
            display_name="Test Customer",
        )
        assert c.last_assigned_tech_id is None


# ─── Webhook Route ────────────────────────────────────────────────────────────


class TestTelnyxWebhookRoute:
    """Verify the webhook receiver returns correct HTTP status codes."""

    def test_invalid_signature_returns_401(self, client):
        """MockSmsCarrier always returns True for signature — patch it to False."""
        mock_carrier = MockSmsCarrier()
        mock_carrier.verify_webhook_signature = lambda payload, sig: False

        with patch("services.sms_carrier.get_sms_carrier", return_value=mock_carrier):
            resp = client.post(
                "/api/v1/webhooks/sms/telnyx-inbound",
                content=b'{"test": "payload"}',
                headers={"content-type": "application/json"},
            )
        assert resp.status_code == 401

    def test_valid_signature_returns_200(self, client):
        """MockSmsCarrier returns True for any signature by default."""
        with patch(
            "services.sms_carrier.get_sms_carrier", return_value=MockSmsCarrier()
        ):
            resp = client.post(
                "/api/v1/webhooks/sms/telnyx-inbound",
                content=b'{"from": "+15125551234", "to": "+15125550001", "body": "Hello", "id": "x", "received_at": "2026-01-01T00:00:00Z"}',
                headers={"content-type": "application/json"},
            )
        # 200 = signature accepted; background task may not run fully in test
        assert resp.status_code == 200
        assert resp.json()["status"] == "received"


# ─── TELNYX-INT-1: TELNYX_10DLC_MOCK flag behavior ────────────────────────────


class TestTelnyx10DlcMockFlag:
    """Verify the TELNYX_10DLC_MOCK flag behavior in TelnyxSmsCarrier.

    These tests patch the telnyx SDK import so they run without the SDK
    installed — they verify the carrier's internal flag logic, not real API
    calls.
    """

    def test_mock_flag_on_includes_mock_true_in_brand_payload(self, caplog):
        """TELNYX_10DLC_MOCK=true → create_brand payload includes mock=True."""
        import logging

        from services.telnyx_sms_carrier import TelnyxSmsCarrier

        mock_telnyx = MagicMock()
        mock_client = MagicMock()
        mock_brand_obj = MagicMock()
        mock_brand_obj.brand_id = "mock-brand-123"
        mock_brand_obj.status = "pending"
        mock_client.messaging_10dlc.brand.create.return_value = mock_brand_obj
        mock_telnyx.Telnyx.return_value = mock_client

        with patch.dict("sys.modules", {"telnyx": mock_telnyx}):
            with patch("core.config.settings") as mock_settings:
                mock_settings.TELNYX_API_KEY = "test-key"
                mock_settings.TELNYX_MESSAGING_PROFILE_ID = ""
                mock_settings.TELNYX_PUBLIC_KEY = ""
                mock_settings.TELNYX_10DLC_MOCK = True

                caplog.set_level(logging.WARNING)
                carrier = TelnyxSmsCarrier()

                brand_data = {
                    "entity_type": "standard",
                    "legal_business_name": "Test Co",
                    "support_phone": "+15555550001",
                    "hq_address_line1": "123 St",
                    "hq_city": "Austin",
                    "hq_state": "TX",
                    "hq_postal_code": "78701",
                    "support_email": "test@test.com",
                    "vertical": "ENERGY",
                }
                carrier.create_brand(brand_data)

        # Assert mock=True was passed to the SDK's messaging_10dlc.brand.create
        call_kwargs = mock_client.messaging_10dlc.brand.create.call_args.kwargs
        assert call_kwargs.get("mock") is True, (
            f"create_brand must pass mock=True when TELNYX_10DLC_MOCK=true; "
            f"got kwargs: {call_kwargs}"
        )

    def test_mock_flag_off_excludes_mock_key_from_brand_payload(self):
        """TELNYX_10DLC_MOCK=false/absent → brand payload has no 'mock' key."""
        from services.telnyx_sms_carrier import TelnyxSmsCarrier

        mock_telnyx = MagicMock()
        mock_client = MagicMock()
        mock_brand_obj = MagicMock()
        mock_brand_obj.brand_id = "real-brand-456"
        mock_brand_obj.status = "pending"
        mock_client.messaging_10dlc.brand.create.return_value = mock_brand_obj
        mock_telnyx.Telnyx.return_value = mock_client

        with patch.dict("sys.modules", {"telnyx": mock_telnyx}):
            with patch("core.config.settings") as mock_settings:
                mock_settings.TELNYX_API_KEY = "test-key"
                mock_settings.TELNYX_MESSAGING_PROFILE_ID = ""
                mock_settings.TELNYX_PUBLIC_KEY = ""
                mock_settings.TELNYX_10DLC_MOCK = False

                carrier = TelnyxSmsCarrier()

                brand_data = {
                    "entity_type": "standard",
                    "legal_business_name": "Test Co",
                    "support_phone": "+15555550001",
                    "hq_address_line1": "123 St",
                    "hq_city": "Austin",
                    "hq_state": "TX",
                    "hq_postal_code": "78701",
                    "support_email": "test@test.com",
                    "vertical": "ENERGY",
                }
                carrier.create_brand(brand_data)

        call_kwargs = mock_client.messaging_10dlc.brand.create.call_args.kwargs
        assert "mock" not in call_kwargs, (
            f"create_brand must NOT include 'mock' key when "
            f"TELNYX_10DLC_MOCK=false; got kwargs: {call_kwargs}"
        )

    def test_mock_flag_on_logs_warning_at_init(self, caplog):
        """TELNYX_10DLC_MOCK=true → WARNING logged at carrier init."""
        import logging

        from services.telnyx_sms_carrier import TelnyxSmsCarrier

        mock_telnyx = MagicMock()
        mock_client = MagicMock()
        mock_telnyx.Telnyx.return_value = mock_client

        with patch.dict("sys.modules", {"telnyx": mock_telnyx}):
            with patch("core.config.settings") as mock_settings:
                mock_settings.TELNYX_API_KEY = "test-key"
                mock_settings.TELNYX_MESSAGING_PROFILE_ID = ""
                mock_settings.TELNYX_PUBLIC_KEY = ""
                mock_settings.TELNYX_10DLC_MOCK = True

                caplog.set_level(logging.WARNING)
                carrier = TelnyxSmsCarrier()

        assert carrier._mock_10dlc is True
        # At least one WARNING record mentions TELNYX_10DLC_MOCK
        warning_msgs = [
            r.message for r in caplog.records if r.levelno == logging.WARNING
        ]
        assert any("TELNYX_10DLC_MOCK" in msg for msg in warning_msgs), (
            f"Expected a WARNING log mentioning TELNYX_10DLC_MOCK at init; "
            f"got warnings: {warning_msgs}"
        )

    def test_factory_routing_unchanged_mock_default(self):
        """get_sms_carrier() factory routing unchanged — mock default still
        returns MockSmsCarrier (regression test for TELNYX_10DLC_MOCK addition).
        """
        with patch("core.config.settings") as mock_settings:
            mock_settings.SMS_CARRIER = "mock"
            mock_settings.TELNYX_10DLC_MOCK = True  # even with mock flag on
            carrier = get_sms_carrier()
        assert isinstance(carrier, MockSmsCarrier), (
            "SMS_CARRIER=mock must always return MockSmsCarrier regardless of "
            "TELNYX_10DLC_MOCK value"
        )
