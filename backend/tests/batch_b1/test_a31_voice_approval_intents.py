"""
Batch B1 — A31 Test Coverage
============================

A31: Voice Intent Grammar for Approval Actions

Test Coverage:
- INTENT_HANDLERS contains approve_quote, reject_quote, kickback_quote, list_pending_quotes
- All 4 handlers are async coroutines with correct signatures
- approve_quote_via_voice confirm-as-turn: first turn returns confirmation prompt
- approve_quote_via_voice writes pending_confirmation to session context
- reject_quote_via_voice requires a reason
- reject_quote_via_voice requires a quote_id
- kickback_quote_via_voice confirm-as-turn: first turn returns confirmation prompt
- list_pending_quotes_via_voice returns no-quotes message when none pending
"""

import asyncio
import inspect
import uuid
from unittest.mock import MagicMock

from services.voice_action_router import (
    INTENT_HANDLERS,
    approve_quote_via_voice,
    kickback_quote_via_voice,
    list_pending_quotes_via_voice,
    reject_quote_via_voice,
)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def make_mock_user(tenant_id=None):
    user = MagicMock()
    user.id = uuid.uuid4()
    user.tenant_id = tenant_id or uuid.UUID("00000000-0000-0000-0000-000000000001")
    return user


def make_mock_session(context=None):
    session = MagicMock()
    session.context_window_json = context or {}
    return session


# ─────────────────────────────────────────────────────────────────────────────
# A31 — INTENT_HANDLERS registration
# ─────────────────────────────────────────────────────────────────────────────


class TestA31IntentRegistration:
    """Verify all 4 A31 intents are in INTENT_HANDLERS."""

    def test_approve_quote_in_intent_handlers(self):
        assert "approve_quote" in INTENT_HANDLERS

    def test_reject_quote_in_intent_handlers(self):
        assert "reject_quote" in INTENT_HANDLERS

    def test_kickback_quote_in_intent_handlers(self):
        assert "kickback_quote" in INTENT_HANDLERS

    def test_list_pending_quotes_in_intent_handlers(self):
        assert "list_pending_quotes" in INTENT_HANDLERS

    def test_approve_quote_handler_is_correct_function(self):
        assert INTENT_HANDLERS["approve_quote"] is approve_quote_via_voice

    def test_reject_quote_handler_is_correct_function(self):
        assert INTENT_HANDLERS["reject_quote"] is reject_quote_via_voice

    def test_kickback_quote_handler_is_correct_function(self):
        assert INTENT_HANDLERS["kickback_quote"] is kickback_quote_via_voice

    def test_list_pending_quotes_handler_is_correct_function(self):
        assert INTENT_HANDLERS["list_pending_quotes"] is list_pending_quotes_via_voice


# ─────────────────────────────────────────────────────────────────────────────
# A31 — Handler signature tests
# ─────────────────────────────────────────────────────────────────────────────


class TestA31HandlerSignatures:
    """Verify all A31 handlers are async coroutines with correct signatures."""

    def test_approve_quote_is_async(self):
        assert inspect.iscoroutinefunction(approve_quote_via_voice)

    def test_reject_quote_is_async(self):
        assert inspect.iscoroutinefunction(reject_quote_via_voice)

    def test_kickback_quote_is_async(self):
        assert inspect.iscoroutinefunction(kickback_quote_via_voice)

    def test_list_pending_quotes_is_async(self):
        assert inspect.iscoroutinefunction(list_pending_quotes_via_voice)

    def test_approve_quote_has_expected_params(self):
        sig = inspect.signature(approve_quote_via_voice)
        params = list(sig.parameters.keys())
        assert "entities" in params
        assert "current_user" in params
        assert "db" in params
        assert "session" in params

    def test_list_pending_quotes_has_expected_params(self):
        sig = inspect.signature(list_pending_quotes_via_voice)
        params = list(sig.parameters.keys())
        assert "entities" in params
        assert "current_user" in params
        assert "db" in params
        assert "session" in params


# ─────────────────────────────────────────────────────────────────────────────
# A31 — Functional handler tests (using asyncio.run per Python 3.14 compat)
# ─────────────────────────────────────────────────────────────────────────────


class TestA31ApproveQuoteHandler:
    """Test approve_quote_via_voice confirm-as-turn pattern."""

    def test_first_turn_returns_confirmation_prompt(self):
        """First call writes pending_confirmation and returns prompt."""
        result = asyncio.run(
            approve_quote_via_voice(
                entities={"quote_identifier": "Johnson panel"},
                current_user=make_mock_user(),
                db=MagicMock(),
                session=make_mock_session(),
            )
        )
        assert result["action"] == "approve_quote"
        assert result["success"] is True
        assert result.get("requires_confirmation") is True
        assert (
            "confirm" in result["message"].lower() or "yes" in result["message"].lower()
        )

    def test_pending_confirmation_written_to_session(self):
        """Handler must write pending_confirmation to session.context_window_json."""
        mock_session = make_mock_session()
        asyncio.run(
            approve_quote_via_voice(
                entities={"quote_identifier": "panel quote"},
                current_user=make_mock_user(),
                db=MagicMock(),
                session=mock_session,
            )
        )
        assert "pending_confirmation" in mock_session.context_window_json
        assert (
            mock_session.context_window_json["pending_confirmation"]["action"]
            == "approve_quote"
        )


class TestA31RejectQuoteHandler:
    """Test reject_quote_via_voice validation."""

    def test_reject_without_reason_returns_error(self):
        """reject_quote must require a reason."""
        result = asyncio.run(
            reject_quote_via_voice(
                entities={"quote_id": str(uuid.uuid4())},
                current_user=make_mock_user(),
                db=MagicMock(),
                session=make_mock_session(),
            )
        )
        assert result["action"] == "reject_quote"
        assert result["success"] is False
        assert "reason" in result["message"].lower()

    def test_reject_without_quote_id_returns_error(self):
        """reject_quote must require a quote_id."""
        result = asyncio.run(
            reject_quote_via_voice(
                entities={"reason": "Labor cost is too high"},
                current_user=make_mock_user(),
                db=MagicMock(),
                session=make_mock_session(),
            )
        )
        assert result["action"] == "reject_quote"
        assert result["success"] is False


class TestA31KickbackQuoteHandler:
    """Test kickback_quote_via_voice confirm-as-turn pattern."""

    def test_first_turn_returns_confirmation_prompt(self):
        """kickback_quote first turn should request confirmation."""
        result = asyncio.run(
            kickback_quote_via_voice(
                entities={"quote_id": str(uuid.uuid4()), "comment": "Lower labor rate"},
                current_user=make_mock_user(),
                db=MagicMock(),
                session=make_mock_session(),
            )
        )
        assert result["action"] == "kickback_quote"
        assert result["success"] is True
        assert result.get("requires_confirmation") is True


class TestA31ListPendingQuotesHandler:
    """Test list_pending_quotes_via_voice."""

    def test_returns_no_quotes_when_none_pending(self, db_session):
        """list_pending_quotes returns appropriate message when none pending."""
        # Use a random tenant_id that won't have any quotes
        mock_user = make_mock_user(tenant_id=uuid.uuid4())
        result = asyncio.run(
            list_pending_quotes_via_voice(
                entities={},
                current_user=mock_user,
                db=db_session,
                session=make_mock_session(),
            )
        )
        assert result["action"] == "list_pending_quotes"
        assert result["success"] is True
        assert result["pending_count"] == 0
