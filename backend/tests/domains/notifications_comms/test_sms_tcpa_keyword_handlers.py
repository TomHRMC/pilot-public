"""
Tests for: TCPA SMS keyword handlers — STOP reply text, HELP auto-reply
Domain: notifications_comms (PRD §3.7)

Covers:
  - STOP reply body matches SMS Terms & Conditions page text exactly
  - HELP keyword detection (_is_help_keyword)
  - handle_sms_help() sends correct auto-reply body
  - handle_sms_help() works for unknown (unmatched) customer numbers
  - webhooks_sms._process_inbound_sms routes HELP to handle_sms_help
"""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]

# ---------------------------------------------------------------------------
# Canonical message text (DLC-B2: updated to match playbook §8 compliant strings)
# ---------------------------------------------------------------------------
# DLC-B2 Finding 1: Compliant STOP reply per playbook §8
STOP_REPLY_TEXT = (
    "You have been unsubscribed from Pilot for Trades messages. "
    "No further messages will be sent. Reply START to re-subscribe."
)
# DLC-B2 Finding 3: HELP reply is now fixed brand string per playbook §8
# (no longer dynamic — no DB lookup needed)
HELP_REPLY_BRAND = "Pilot for Trades service messages."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_inbound(
    body: str, from_number: str = "+15125551234", to_number: str = "+15125550001"
):
    from services.customer_communication_threading import InboundMessage

    return InboundMessage(
        from_number=from_number,
        to_number=to_number,
        body=body,
        carrier_message_id="test-msg-id",
        received_at="2026-05-02T12:00:00Z",
    )


# ---------------------------------------------------------------------------
# 1. STOP reply text
# ---------------------------------------------------------------------------
class TestStopReplyText:
    """Verify the STOP auto-reply body exactly matches DLC spec §2.4."""

    def test_stop_reply_exact_text(self, db_session, test_tenant, test_customer):
        """handle_sms_opt_out sends the DLC-B2 playbook §8-compliant STOP reply text."""
        from services.customer_communication_threading import handle_sms_opt_out
        from services.sms_carrier import MockSmsCarrier

        inbound = _make_inbound(
            "STOP", from_number=test_customer.mobile_phone or "+15125551234"
        )
        mock_carrier = MockSmsCarrier()

        with patch("services.sms_carrier.get_sms_carrier", return_value=mock_carrier):
            handle_sms_opt_out(db_session, test_customer.id, inbound)

        assert len(mock_carrier.sent_messages) == 1
        sent_body = mock_carrier.sent_messages[0]["body"]
        assert sent_body == STOP_REPLY_TEXT, (
            f"STOP reply does not match DLC-B2 playbook §8.\n"
            f"Expected: {STOP_REPLY_TEXT!r}\n"
            f"Got:      {sent_body!r}"
        )

    def test_stop_reply_to_from_numbers_are_swapped(
        self, db_session, test_tenant, test_customer
    ):
        """Confirmation goes from our number (to_number) to the customer (from_number)."""
        from services.customer_communication_threading import handle_sms_opt_out
        from services.sms_carrier import MockSmsCarrier

        inbound = _make_inbound(
            "STOP",
            from_number=test_customer.mobile_phone or "+15125551234",
            to_number="+15125550001",
        )
        mock_carrier = MockSmsCarrier()

        with patch("services.sms_carrier.get_sms_carrier", return_value=mock_carrier):
            handle_sms_opt_out(db_session, test_customer.id, inbound)

        msg = mock_carrier.sent_messages[0]
        # MockSmsCarrier stores keys as "from" and "to"
        assert msg["from"] == "+15125550001"
        assert msg["to"] == (test_customer.mobile_phone or "+15125551234")


# ---------------------------------------------------------------------------
# 2. HELP keyword detection
# ---------------------------------------------------------------------------
class TestHelpKeywordDetection:
    """Verify _is_help_keyword identifies HELP/INFO variants correctly."""

    @pytest.mark.parametrize(
        "keyword", ["HELP", "help", "Help", "INFO", "info", "Info"]
    )
    def test_help_keywords_detected(self, keyword):
        from api.routes.webhooks_sms import _is_help_keyword

        assert _is_help_keyword(keyword) is True
        assert _is_help_keyword(f"  {keyword}  ") is True

    @pytest.mark.parametrize(
        "body", ["STOP", "START", "Hello", "help me please", "INFO needed"]
    )
    def test_non_exact_help_not_detected(self, body):
        from api.routes.webhooks_sms import _is_help_keyword

        # Only exact single-word match; sentences should not trigger
        if body in ("STOP", "START", "Hello"):
            assert _is_help_keyword(body) is False
        else:
            # Multi-word bodies — strip won't reduce to a known keyword
            assert _is_help_keyword(body) is False

    def test_help_is_not_stop_keyword(self):
        from api.routes.webhooks_sms import _is_stop_keyword

        assert _is_stop_keyword("HELP") is False
        assert _is_stop_keyword("INFO") is False

    def test_help_is_not_optin_keyword(self):
        from api.routes.webhooks_sms import _is_optin_keyword

        assert _is_optin_keyword("HELP") is False
        assert _is_optin_keyword("INFO") is False


# ---------------------------------------------------------------------------
# 3. handle_sms_help() — auto-reply body and routing
# ---------------------------------------------------------------------------
class TestHandleSmsHelp:
    """Verify handle_sms_help sends the DLC spec §2.4-compliant HELP reply."""

    def test_help_reply_contains_required_elements(self):
        """handle_sms_help (no db) sends a DLC-B2 playbook §8-compliant HELP body."""
        from services.customer_communication_threading import handle_sms_help
        from services.sms_carrier import MockSmsCarrier

        inbound = _make_inbound("HELP")
        mock_carrier = MockSmsCarrier()

        with patch("services.sms_carrier.get_sms_carrier", return_value=mock_carrier):
            handle_sms_help(inbound)  # db=None → uses fixed brand string

        assert len(mock_carrier.sent_messages) == 1
        sent_body = mock_carrier.sent_messages[0]["body"]
        # DLC-B2 playbook §8: must include brand, website, email, rates, STOP
        assert HELP_REPLY_BRAND in sent_body
        assert "pilotfortrades.com" in sent_body
        assert "STOP" in sent_body
        assert "Msg & data rates may apply" in sent_body

    def test_help_reply_to_from_numbers_are_swapped(self):
        """Reply goes from our number (to_number) to the sender (from_number)."""
        from services.customer_communication_threading import handle_sms_help
        from services.sms_carrier import MockSmsCarrier

        inbound = _make_inbound(
            "HELP", from_number="+19995550001", to_number="+15125550001"
        )
        mock_carrier = MockSmsCarrier()

        with patch("services.sms_carrier.get_sms_carrier", return_value=mock_carrier):
            handle_sms_help(inbound)

        msg = mock_carrier.sent_messages[0]
        assert msg["from"] == "+15125550001"
        assert msg["to"] == "+19995550001"

    def test_help_works_for_unknown_number(self):
        """HELP auto-reply does not require a matched customer — sends to any number."""
        from services.customer_communication_threading import handle_sms_help
        from services.sms_carrier import MockSmsCarrier

        inbound = _make_inbound("HELP", from_number="+10000000000")
        mock_carrier = MockSmsCarrier()

        with patch("services.sms_carrier.get_sms_carrier", return_value=mock_carrier):
            handle_sms_help(inbound)

        assert len(mock_carrier.sent_messages) == 1

    def test_help_carrier_error_is_logged_not_raised(self, caplog):
        """A carrier send failure logs an error but does not propagate the exception."""
        import logging

        from services.customer_communication_threading import handle_sms_help

        failing_carrier = MagicMock()
        failing_carrier.send_message.side_effect = RuntimeError("carrier down")

        inbound = _make_inbound("HELP")

        with patch(
            "services.sms_carrier.get_sms_carrier", return_value=failing_carrier
        ):
            with caplog.at_level(
                logging.ERROR, logger="services.customer_communication_threading"
            ):
                handle_sms_help(inbound)  # must not raise

        assert any("HELP auto-reply" in r.message for r in caplog.records)

    def test_info_keyword_also_triggers_help_reply(self):
        """INFO keyword is routed identically to HELP — same fixed brand reply (DLC-B2)."""
        from services.customer_communication_threading import handle_sms_help
        from services.sms_carrier import MockSmsCarrier

        inbound = _make_inbound("INFO")
        mock_carrier = MockSmsCarrier()

        with patch("services.sms_carrier.get_sms_carrier", return_value=mock_carrier):
            handle_sms_help(inbound)

        assert len(mock_carrier.sent_messages) == 1
        # DLC-B2: fixed brand string; verify required elements present
        sent_body = mock_carrier.sent_messages[0]["body"]
        assert HELP_REPLY_BRAND in sent_body
        assert "STOP" in sent_body


# ---------------------------------------------------------------------------
# 4. _process_inbound_sms routes HELP correctly
# ---------------------------------------------------------------------------
class TestProcessInboundSmsHelpRouting:
    """Verify _process_inbound_sms calls handle_sms_help for HELP keyword."""

    def test_help_keyword_calls_handle_sms_help(self, db_session):
        """HELP body in _process_inbound_sms → handle_sms_help called, not route_inbound_message."""
        import json

        from api.routes.webhooks_sms import _process_inbound_sms
        from services.sms_carrier import InboundMessage, MockSmsCarrier

        mock_carrier = MockSmsCarrier()
        mock_carrier.parse_inbound_webhook = lambda p: InboundMessage(
            from_number="+15125551234",
            to_number="+15125550001",
            body="HELP",
            carrier_message_id="help-test-id",
            received_at="2026-05-02T12:00:00Z",
        )

        payload = json.dumps(
            {"from": "+15125551234", "to": "+15125550001", "body": "HELP", "id": "x"}
        ).encode()

        # _process_inbound_sms calls next(db_session_factory()) — wrap db_session in a generator
        def _db_factory():
            yield db_session

        with patch("services.sms_carrier.get_sms_carrier", return_value=mock_carrier):
            with patch(
                "services.customer_communication_threading.handle_sms_help"
            ) as mock_help:
                with patch(
                    "services.customer_communication_threading.route_inbound_message"
                ) as mock_route:
                    _process_inbound_sms(payload, _db_factory)
                    # handle_sms_help must be called exactly once
                    mock_help.assert_called_once()
                    # route_inbound_message must NOT be called
                    mock_route.assert_not_called()
