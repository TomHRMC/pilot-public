"""
tests/batch_b4/test_a22_voice_comms.py

B4 / A22 — Voice Intent Grammar for Customer Communications

Tests the 4 voice handler functions directly (not through HTTP) using the
§17.4 pattern: test handler functions directly without Celery or HTTP.

Test focus areas (from design doc):
  - All 4 handlers registered in INTENT_HANDLERS
  - Happy path: handler returns pending_confirmation=True + summary_prompt
  - Confirm-as-turn: pending_confirmation written to session.context_window_json
  - Customer resolution: from session context (active_customer_id)
  - Customer resolution: fuzzy name match from entities
  - No customer found → clarification response (no pending_confirmation)
  - No customer name and no context → clarification response
  - Ambiguous match (multiple) → disambiguation response
  - Missing mobile_phone → error response (success=False)
  - INTENT_HANDLERS registry has all 4 A22 keys
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from app.models.ai import ConversationSession
from app.models.crm import Customer
from services.voice_action_router import (
    INTENT_HANDLERS,
    _resolve_customer_for_voice,
    tell_customer_arrived_via_voice,
    tell_customer_completed_via_voice,
    tell_customer_running_late_via_voice,
    tell_customer_via_voice,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_customer(db_session, test_tenant, test_user):
    # NOTE: Name must be unique enough to not match seeded customers.
    # "Tom Johnson" was colliding with seeded "Mary Johnson" in fuzzy-match tests.
    # Using "Zzetaq" prefix to guarantee uniqueness vs dev seed data.
    customer = Customer(
        tenant_id=test_tenant.id,
        display_name="Zzetaq Electrician",
        first_name="Zzetaq",
        last_name="Electrician",
        mobile_phone="+15125550030",
        email="zzetaq@example-voice-test.com",
        preferred_contact_channel="sms",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


@pytest.fixture
def test_customer_no_phone(db_session, test_tenant, test_user):
    customer = Customer(
        tenant_id=test_tenant.id,
        display_name="No Phone Voice",
        first_name="No",
        last_name="Phone",
        mobile_phone=None,
        email="novoice@example.com",
        preferred_contact_channel="sms",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


@pytest.fixture
def voice_session(db_session, test_tenant, test_user):
    """A real ConversationSession in the DB.
    Handlers call db.add(session) so we need a real mapped object.
    """
    session = ConversationSession(
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        title="A22 Test Session",
        context_window_json={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


@pytest.fixture
def mock_session_for_resolve(test_tenant, test_user):
    """MagicMock session — safe for _resolve_customer_for_voice which only reads."""
    session = MagicMock(spec=ConversationSession)
    session.id = uuid.uuid4()
    session.tenant_id = test_tenant.id
    session.context_window_json = {}
    return session


@pytest.fixture
def mock_user_context(test_tenant, test_user):
    """TestUserContext-compatible object."""
    ctx = MagicMock()
    ctx.id = test_user.id
    ctx.tenant_id = test_tenant.id
    ctx.display_name = "Mike the Tech"
    return ctx


# ---------------------------------------------------------------------------
# Test: INTENT_HANDLERS registration
# ---------------------------------------------------------------------------


class TestIntentHandlerRegistration:
    def test_all_four_a22_handlers_registered(self):
        assert "tell_customer" in INTENT_HANDLERS
        assert "tell_customer_running_late" in INTENT_HANDLERS
        assert "tell_customer_arrived" in INTENT_HANDLERS
        assert "tell_customer_completed" in INTENT_HANDLERS

    def test_handler_callables(self):
        for key in (
            "tell_customer",
            "tell_customer_running_late",
            "tell_customer_arrived",
            "tell_customer_completed",
        ):
            assert callable(INTENT_HANDLERS[key])


# ---------------------------------------------------------------------------
# Test: Customer resolution helper (uses MagicMock session — no db.add)
# ---------------------------------------------------------------------------


class TestResolveCustomerForVoice:
    def test_resolves_from_session_context(
        self,
        db_session,
        test_tenant,
        test_user,
        test_customer,
        mock_session_for_resolve,
        mock_user_context,
    ):
        """If active_customer_id in context, returns that customer."""
        mock_session_for_resolve.context_window_json = {
            "active_customer_id": str(test_customer.id)
        }
        result = _resolve_customer_for_voice(
            entities={},
            current_user=mock_user_context,
            db=db_session,
            session=mock_session_for_resolve,
        )
        assert isinstance(result, Customer)
        assert result.id == test_customer.id

    def test_resolves_fuzzy_name_match(
        self,
        db_session,
        test_tenant,
        test_user,
        test_customer,
        mock_session_for_resolve,
        mock_user_context,
    ):
        """Fuzzy match on display_name from entities.

        Search term must uniquely match the test_customer fixture and NOT match
        any seeded customer. "Zzetaq" is unique enough to guarantee a single match.
        """
        mock_session_for_resolve.context_window_json = {}
        result = _resolve_customer_for_voice(
            entities={"customer_name": "Zzetaq"},
            current_user=mock_user_context,
            db=db_session,
            session=mock_session_for_resolve,
        )
        assert isinstance(result, Customer)
        assert result.id == test_customer.id

    def test_no_name_and_no_context_returns_clarification(
        self,
        db_session,
        test_tenant,
        test_user,
        mock_session_for_resolve,
        mock_user_context,
    ):
        """No customer_name and no active_customer_id → clarification dict."""
        mock_session_for_resolve.context_window_json = {}
        result = _resolve_customer_for_voice(
            entities={},
            current_user=mock_user_context,
            db=db_session,
            session=mock_session_for_resolve,
        )
        assert isinstance(result, dict)
        assert result.get("clarification_needed") is True
        assert result["success"] is False

    def test_no_match_returns_clarification(
        self,
        db_session,
        test_tenant,
        test_user,
        mock_session_for_resolve,
        mock_user_context,
    ):
        """Name not found → clarification dict."""
        mock_session_for_resolve.context_window_json = {}
        result = _resolve_customer_for_voice(
            entities={"customer_name": "XyzNonExistentCustomer999"},
            current_user=mock_user_context,
            db=db_session,
            session=mock_session_for_resolve,
        )
        assert isinstance(result, dict)
        assert result.get("clarification_needed") is True

    def test_multiple_matches_returns_disambiguation(
        self,
        db_session,
        test_tenant,
        test_user,
        mock_session_for_resolve,
        mock_user_context,
    ):
        """Multiple matches → disambiguation dict."""
        for i in range(2):
            c = Customer(
                tenant_id=test_tenant.id,
                display_name=f"Smith Ambig {i}",
                first_name=f"A{i}",
                last_name="Smith",
                mobile_phone=f"+1512555{9000 + i}",
                preferred_contact_channel="sms",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            db_session.add(c)
        db_session.commit()

        mock_session_for_resolve.context_window_json = {}
        result = _resolve_customer_for_voice(
            entities={"customer_name": "Smith Ambig"},
            current_user=mock_user_context,
            db=db_session,
            session=mock_session_for_resolve,
        )
        assert isinstance(result, dict)
        assert result.get("clarification_needed") is True
        assert "Smith Ambig" in result["message"]


# ---------------------------------------------------------------------------
# Test: tell_customer_via_voice (on_my_way)
# Uses real voice_session fixture to satisfy db.add(session).
# ---------------------------------------------------------------------------


class TestTellCustomerViaVoice:
    @pytest.mark.asyncio
    async def test_happy_path_returns_pending_confirmation(
        self,
        db_session,
        test_tenant,
        test_user,
        test_customer,
        voice_session,
        mock_user_context,
    ):
        """Happy path: returns pending_confirmation=True with summary."""
        voice_session.context_window_json = {
            "active_customer_id": str(test_customer.id)
        }
        db_session.add(voice_session)
        db_session.commit()

        result = await tell_customer_via_voice(
            entities={"eta": "10:30 AM", "site_address": "1 Oak St"},
            current_user=mock_user_context,
            db=db_session,
            session=voice_session,
        )

        assert result["success"] is True
        assert result["pending_confirmation"] is True
        assert test_customer.display_name in result["recipient"]
        assert result["actual_channel"] == "sms"

    @pytest.mark.asyncio
    async def test_pending_confirmation_written_to_session(
        self,
        db_session,
        test_tenant,
        test_user,
        test_customer,
        voice_session,
        mock_user_context,
    ):
        """pending_confirmation key written to session.context_window_json."""
        voice_session.context_window_json = {
            "active_customer_id": str(test_customer.id)
        }
        db_session.add(voice_session)
        db_session.commit()

        await tell_customer_via_voice(
            entities={"eta": "noon"},
            current_user=mock_user_context,
            db=db_session,
            session=voice_session,
        )

        db_session.refresh(voice_session)
        ctx = voice_session.context_window_json
        assert "pending_confirmation" in ctx
        assert ctx["pending_confirmation"]["intent_type"] == "tell_customer"
        assert ctx["pending_confirmation"]["entities"]["customer_id"] == str(
            test_customer.id
        )

    @pytest.mark.asyncio
    async def test_no_customer_returns_clarification(
        self,
        db_session,
        test_tenant,
        test_user,
        voice_session,
        mock_user_context,
    ):
        """No customer in context and no name → clarification (success=False)."""
        voice_session.context_window_json = {}
        db_session.add(voice_session)
        db_session.commit()

        result = await tell_customer_via_voice(
            entities={},
            current_user=mock_user_context,
            db=db_session,
            session=voice_session,
        )
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_no_phone_returns_error(
        self,
        db_session,
        test_tenant,
        test_user,
        test_customer_no_phone,
        voice_session,
        mock_user_context,
    ):
        """Customer has no phone → error response (success=False)."""
        voice_session.context_window_json = {
            "active_customer_id": str(test_customer_no_phone.id)
        }
        db_session.add(voice_session)
        db_session.commit()

        result = await tell_customer_via_voice(
            entities={},
            current_user=mock_user_context,
            db=db_session,
            session=voice_session,
        )
        assert result["success"] is False
        assert (
            "phone" in result["message"].lower()
            or "mobile" in result["message"].lower()
            or "sms" in result["message"].lower()
        )


# ---------------------------------------------------------------------------
# Test: tell_customer_running_late_via_voice
# ---------------------------------------------------------------------------


class TestTellCustomerRunningLateViaVoice:
    @pytest.mark.asyncio
    async def test_happy_path(
        self,
        db_session,
        test_tenant,
        test_user,
        test_customer,
        voice_session,
        mock_user_context,
    ):
        voice_session.context_window_json = {
            "active_customer_id": str(test_customer.id)
        }
        db_session.add(voice_session)
        db_session.commit()

        result = await tell_customer_running_late_via_voice(
            entities={"minutes_late": "20"},
            current_user=mock_user_context,
            db=db_session,
            session=voice_session,
        )

        assert result["success"] is True
        assert result["action"] == "tell_customer_running_late"
        assert result["pending_confirmation"] is True

    @pytest.mark.asyncio
    async def test_pending_confirmation_has_running_late_template(
        self,
        db_session,
        test_tenant,
        test_user,
        test_customer,
        voice_session,
        mock_user_context,
    ):
        voice_session.context_window_json = {
            "active_customer_id": str(test_customer.id)
        }
        db_session.add(voice_session)
        db_session.commit()

        await tell_customer_running_late_via_voice(
            entities={"minutes_late": "15"},
            current_user=mock_user_context,
            db=db_session,
            session=voice_session,
        )

        db_session.refresh(voice_session)
        ctx = voice_session.context_window_json
        assert (
            ctx["pending_confirmation"]["entities"]["template_code"] == "running_late"
        )


# ---------------------------------------------------------------------------
# Test: tell_customer_arrived_via_voice
# ---------------------------------------------------------------------------


class TestTellCustomerArrivedViaVoice:
    @pytest.mark.asyncio
    async def test_happy_path(
        self,
        db_session,
        test_tenant,
        test_user,
        test_customer,
        voice_session,
        mock_user_context,
    ):
        voice_session.context_window_json = {
            "active_customer_id": str(test_customer.id)
        }
        db_session.add(voice_session)
        db_session.commit()

        result = await tell_customer_arrived_via_voice(
            entities={},
            current_user=mock_user_context,
            db=db_session,
            session=voice_session,
        )

        assert result["success"] is True
        assert result["action"] == "tell_customer_arrived"
        assert result["pending_confirmation"] is True

        db_session.refresh(voice_session)
        ctx = voice_session.context_window_json
        assert ctx["pending_confirmation"]["entities"]["template_code"] == "arrived"


# ---------------------------------------------------------------------------
# Test: tell_customer_completed_via_voice
# ---------------------------------------------------------------------------


class TestTellCustomerCompletedViaVoice:
    @pytest.mark.asyncio
    async def test_happy_path(
        self,
        db_session,
        test_tenant,
        test_user,
        test_customer,
        voice_session,
        mock_user_context,
    ):
        voice_session.context_window_json = {
            "active_customer_id": str(test_customer.id)
        }
        db_session.add(voice_session)
        db_session.commit()

        result = await tell_customer_completed_via_voice(
            entities={},
            current_user=mock_user_context,
            db=db_session,
            session=voice_session,
        )

        assert result["success"] is True
        assert result["action"] == "tell_customer_completed"
        assert result["pending_confirmation"] is True

        db_session.refresh(voice_session)
        ctx = voice_session.context_window_json
        assert (
            ctx["pending_confirmation"]["entities"]["template_code"] == "job_complete"
        )

    @pytest.mark.asyncio
    async def test_session_context_updated(
        self,
        db_session,
        test_tenant,
        test_user,
        test_customer,
        voice_session,
        mock_user_context,
    ):
        """After handler runs, active_customer_id and last_action set in session."""
        voice_session.context_window_json = {
            "active_customer_id": str(test_customer.id)
        }
        db_session.add(voice_session)
        db_session.commit()

        await tell_customer_completed_via_voice(
            entities={},
            current_user=mock_user_context,
            db=db_session,
            session=voice_session,
        )

        db_session.refresh(voice_session)
        ctx = voice_session.context_window_json
        assert ctx.get("active_customer_id") == str(test_customer.id)
        assert ctx.get("last_action") == "tell_customer_completed"
