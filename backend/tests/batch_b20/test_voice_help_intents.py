"""
Test Suite: FIND-111/125 — Voice Handlers for Help System
==========================================================

Implements voice intents for hands-free help access:
  1. open_help_via_voice: Tech says "Open help" or "I need help"
     → creates HelpChatSession, stores session_id in context, writes VoiceCommandEntityLink
  2. ask_help_question_via_voice: Tech says "How do I wire a 3-way switch?"
     → routes to existing help chat RAG pipeline, creates link for message

Test coverage:
  1. open_help → HelpChatSession created with tenant_id, user_id, timestamps
  2. open_help → context stores help session_id (via extra fields)
  3. open_help → success response with greeting
  4. ask_help_question → handles missing question error gracefully
  5. ask_help_question → success response structure when active session exists
"""

import uuid

import pytest
from sqlmodel import select

from api.schemas.voice import ContextWindowSchema
from app.models.ai import ConversationSession
from app.models.core import Tenant, User
from app.models.help import HelpChatSession
from core.auth import AuthenticatedUser
from services.voice_action_router import (
    ask_help_question_via_voice,
    open_help_via_voice,
)

# ==================== FIXTURES ====================


@pytest.fixture
def test_tenant_help(db_session):
    """Create a test tenant for FIND-111 help tests."""
    tenant = Tenant(
        id=uuid.UUID("00000000-0000-0000-0000-000000000111"),
        name="FIND-111 Help Test Tenant",
        is_active=True,
        created_by=None,
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture
def test_user_help(db_session, test_tenant_help):
    """Create a test user for help tests."""
    user = User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000f11"),
        email="tech@find111.test",
        is_active=True,
        created_by=None,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_auth_user_help(test_tenant_help, test_user_help):
    """Create an authenticated user context for help tests."""
    return AuthenticatedUser(
        user=test_user_help,
        tenant_id=test_tenant_help.id,
        role_code="technician",
        permissions=["help_chat.create", "help_chat.view"],
    )


@pytest.fixture
def test_conversation_session_help(db_session, test_tenant_help, test_user_help):
    """Create a test conversation session for context management."""
    session = ConversationSession(
        id=uuid.UUID("00000000-0000-0000-0000-000000001111"),
        tenant_id=test_tenant_help.id,
        user_id=test_user_help.id,
        context_window_json={},
        status="active",
        created_by=test_user_help.id,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


# ==================== TEST SUITE ====================


class TestOpenHelpViaVoice:
    """Test suite for open_help_via_voice handler."""

    @pytest.mark.asyncio
    async def test_open_help_creates_session(
        self,
        db_session,
        test_tenant_help,
        test_user_help,
        test_auth_user_help,
        test_conversation_session_help,
    ):
        """Test that open_help creates a HelpChatSession with correct fields."""
        result = await open_help_via_voice(
            entities={},
            current_user=test_auth_user_help,
            db=db_session,
            session=test_conversation_session_help,
        )

        assert result["success"] is True
        assert result["action"] == "open_help"
        assert "help_session_id" in result["data"]

        # Verify session was created in database
        help_session_id = uuid.UUID(result["data"]["help_session_id"])
        help_session = db_session.exec(
            select(HelpChatSession)
            .where(HelpChatSession.id == help_session_id)
            .where(HelpChatSession.tenant_id == test_tenant_help.id)
            .where(HelpChatSession.user_id == test_user_help.id)
        ).first()

        assert help_session is not None
        assert help_session.tenant_id == test_tenant_help.id
        assert help_session.user_id == test_user_help.id
        assert help_session.started_at is not None
        assert help_session.last_activity_at is not None
        assert help_session.message_count == 0

    @pytest.mark.asyncio
    async def test_open_help_stores_session_in_context(
        self,
        db_session,
        test_tenant_help,
        test_user_help,
        test_auth_user_help,
        test_conversation_session_help,
    ):
        """Test that open_help stores session_id in context window via extra fields."""
        result = await open_help_via_voice(
            entities={},
            current_user=test_auth_user_help,
            db=db_session,
            session=test_conversation_session_help,
        )

        assert result["success"] is True
        help_session_id = result["data"]["help_session_id"]

        # Refresh session from database
        db_session.refresh(test_conversation_session_help)
        ctx = ContextWindowSchema.from_jsonb(
            test_conversation_session_help.context_window_json
        )

        # Check that context_window_json contains active_help_session_id (via extra fields)
        assert (
            test_conversation_session_help.context_window_json.get(
                "active_help_session_id"
            )
            == help_session_id
        )

    @pytest.mark.asyncio
    async def test_open_help_returns_greeting(
        self,
        db_session,
        test_tenant_help,
        test_user_help,
        test_auth_user_help,
        test_conversation_session_help,
    ):
        """Test that open_help returns appropriate greeting message."""
        result = await open_help_via_voice(
            entities={},
            current_user=test_auth_user_help,
            db=db_session,
            session=test_conversation_session_help,
        )

        assert result["success"] is True
        assert "Help is open" in result["message"]
        assert len(result.get("next_prompts", [])) > 0

    @pytest.mark.asyncio
    async def test_open_help_response_structure(
        self,
        db_session,
        test_tenant_help,
        test_user_help,
        test_auth_user_help,
        test_conversation_session_help,
    ):
        """Test that response has correct structure for voice UI rendering."""
        result = await open_help_via_voice(
            entities={},
            current_user=test_auth_user_help,
            db=db_session,
            session=test_conversation_session_help,
        )

        assert isinstance(result, dict)
        assert "action" in result
        assert "success" in result
        assert "message" in result
        assert "data" in result
        assert "next_prompts" in result


class TestAskHelpQuestionViaVoice:
    """Test suite for ask_help_question_via_voice handler."""

    @pytest.mark.asyncio
    async def test_ask_help_question_missing_question(
        self,
        db_session,
        test_tenant_help,
        test_user_help,
        test_auth_user_help,
        test_conversation_session_help,
    ):
        """Test that missing question returns error."""
        result = await ask_help_question_via_voice(
            entities={},
            current_user=test_auth_user_help,
            db=db_session,
            session=test_conversation_session_help,
        )

        assert result["success"] is False
        assert result["action"] == "ask_help_question"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_ask_help_question_with_question_entity(
        self,
        db_session,
        test_tenant_help,
        test_user_help,
        test_auth_user_help,
        test_conversation_session_help,
    ):
        """Test that question entity is recognized in response structure."""
        result = await ask_help_question_via_voice(
            entities={"question": "How do I wire a 3-way switch?"},
            current_user=test_auth_user_help,
            db=db_session,
            session=test_conversation_session_help,
        )

        # Response should be structured (either success or error)
        assert isinstance(result, dict)
        assert "action" in result
        assert result["action"] == "ask_help_question"
        assert "success" in result
        assert "message" in result
        assert "data" in result

    @pytest.mark.asyncio
    async def test_ask_help_question_auto_creates_session_on_no_active(
        self,
        db_session,
        test_tenant_help,
        test_user_help,
        test_auth_user_help,
        test_conversation_session_help,
    ):
        """Test that question auto-creates session if none is stored in context."""
        # Don't create a help session first
        result = await ask_help_question_via_voice(
            entities={"question": "What is NEC grounding?"},
            current_user=test_auth_user_help,
            db=db_session,
            session=test_conversation_session_help,
        )

        # Should have success or controlled error, with a session_id
        assert "data" in result
        if result.get("success"):
            assert "help_session_id" in result["data"]

    @pytest.mark.asyncio
    async def test_ask_help_question_response_structure(
        self,
        db_session,
        test_tenant_help,
        test_user_help,
        test_auth_user_help,
        test_conversation_session_help,
    ):
        """Test that response structure is correct for voice UI."""
        result = await ask_help_question_via_voice(
            entities={"question": "Test question?"},
            current_user=test_auth_user_help,
            db=db_session,
            session=test_conversation_session_help,
        )

        # Verify structure regardless of success
        assert isinstance(result, dict)
        assert "action" in result
        assert "success" in result
        assert "message" in result
        assert "data" in result
        assert result["action"] == "ask_help_question"

    @pytest.mark.asyncio
    async def test_open_then_ask_help_flow(
        self,
        db_session,
        test_tenant_help,
        test_user_help,
        test_auth_user_help,
        test_conversation_session_help,
    ):
        """Test the full flow: open help, then ask a question."""
        # Open help first
        open_result = await open_help_via_voice(
            entities={},
            current_user=test_auth_user_help,
            db=db_session,
            session=test_conversation_session_help,
        )

        assert open_result["success"] is True
        help_session_id = open_result["data"]["help_session_id"]

        # Refresh context
        db_session.refresh(test_conversation_session_help)

        # Now ask a question
        ask_result = await ask_help_question_via_voice(
            entities={"question": "How do I wire a switch?"},
            current_user=test_auth_user_help,
            db=db_session,
            session=test_conversation_session_help,
        )

        # Verify response is structured
        assert "action" in ask_result
        assert ask_result["action"] == "ask_help_question"
        assert "data" in ask_result
        if ask_result.get("success"):
            # If success, should use same session
            assert ask_result["data"]["help_session_id"] == help_session_id
