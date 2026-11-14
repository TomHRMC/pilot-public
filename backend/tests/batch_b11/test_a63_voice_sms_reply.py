"""
B11/A63 — Voice-to-Text SMS Reply Intent Tests
================================================
Tests for:
  - reply_to_customer_sms_via_voice: Turn 1 preview (confirm-as-turn)
  - reply_to_customer_sms_via_voice: Turn 2 confirmation
  - reply_to_customer_sms_via_voice: empty body rejected
  - INTENT_HANDLERS registry contains 'reply_to_customer_sms'
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest


class TestReplyToCustomerSmsViaVoice:
    """Test the reply_to_customer_sms voice intent handler."""

    @pytest.mark.asyncio
    async def test_intent_registered_in_handler_registry(self):
        """reply_to_customer_sms must be in INTENT_HANDLERS."""
        from services.voice_action_router import INTENT_HANDLERS

        assert "reply_to_customer_sms" in INTENT_HANDLERS

    @pytest.mark.asyncio
    async def test_turn1_preview_requires_confirmation(self):
        """First turn: should return requires_confirmation=True with preview."""
        from services.voice_action_router import reply_to_customer_sms_via_voice

        thread_id = str(uuid.uuid4())
        params = {
            "thread_id": thread_id,
            "body": "I'm on my way, 20 minutes.",
            "customer_name": "Davis Electric",
        }
        context = {}  # empty context = no pending confirmation
        mock_db = MagicMock()
        mock_user = MagicMock()

        result = await reply_to_customer_sms_via_voice(
            params, context, mock_db, mock_user
        )

        assert result["requires_confirmation"] is True
        assert result["success"] is True
        assert "Davis Electric" in result["preview"]
        assert "I'm on my way" in result["preview"]
        assert "pending" in result
        assert result["pending"]["thread_id"] == thread_id
        # pending_confirmation stored in context
        assert (
            context.get("pending_confirmation", {}).get("action")
            == "reply_to_customer_sms"
        )

    @pytest.mark.asyncio
    async def test_turn1_empty_body_rejected(self):
        """If body is empty, Turn 1 returns requires_confirmation=False."""
        from services.voice_action_router import reply_to_customer_sms_via_voice

        params = {"thread_id": str(uuid.uuid4()), "body": ""}
        context = {}
        result = await reply_to_customer_sms_via_voice(
            params, context, MagicMock(), MagicMock()
        )

        assert result["requires_confirmation"] is False
        assert result["success"] is False
        assert "message body" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_turn2_missing_thread_id_returns_error(self):
        """Turn 2 with missing thread_id should return error."""
        from services.voice_action_router import reply_to_customer_sms_via_voice

        context = {
            "pending_confirmation": {
                "action": "reply_to_customer_sms",
                "thread_id": None,
                "body": "Test",
            }
        }
        result = await reply_to_customer_sms_via_voice(
            {}, context, MagicMock(), MagicMock()
        )

        assert result["success"] is False
        assert "Missing" in result["message"]

    @pytest.mark.asyncio
    async def test_segment_count_computed_correctly(self):
        """Single SMS segment for short body."""
        from services.voice_action_router import reply_to_customer_sms_via_voice

        params = {
            "thread_id": str(uuid.uuid4()),
            "body": "Hello",
            "customer_name": "Test",
        }
        context = {}
        result = await reply_to_customer_sms_via_voice(
            params, context, MagicMock(), MagicMock()
        )

        assert result["pending"]["segment_count"] == 1

    @pytest.mark.asyncio
    async def test_long_body_multi_segment(self):
        """Long body > 160 chars should compute multiple segments."""
        from services.voice_action_router import reply_to_customer_sms_via_voice

        long_body = "x" * 320  # 2 segments
        params = {
            "thread_id": str(uuid.uuid4()),
            "body": long_body,
            "customer_name": "Test",
        }
        context = {}
        result = await reply_to_customer_sms_via_voice(
            params, context, MagicMock(), MagicMock()
        )

        assert result["pending"]["segment_count"] == 2

    @pytest.mark.asyncio
    async def test_turn2_clears_pending_confirmation(
        self, db_session, test_tenant, test_user
    ):
        """After successful Turn 2, pending_confirmation is cleared from context."""
        from services.voice_action_router import reply_to_customer_sms_via_voice

        # Mock the _send_reply_impl to avoid real DB threading
        mock_result = MagicMock()
        mock_result.message_id = uuid.uuid4()
        mock_result.segment_count = 1
        mock_result.status = "sent"

        context = {
            "pending_confirmation": {
                "action": "reply_to_customer_sms",
                "thread_id": str(uuid.uuid4()),
                "body": "Confirmed message",
            }
        }

        with patch(
            "api.routes.communications_threads._send_reply_impl",
            return_value=mock_result,
        ):
            mock_user = MagicMock()
            mock_user.tenant_id = test_tenant.id
            result = await reply_to_customer_sms_via_voice(
                {}, context, db_session, mock_user
            )

        # pending_confirmation should be cleared regardless of success/fail
        assert (
            "pending_confirmation" not in context
            or context.get("pending_confirmation") is None
        )
