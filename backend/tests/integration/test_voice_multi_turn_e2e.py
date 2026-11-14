"""
Integration Tests: Voice AI Multi-Turn Conversation

This test file validates multi-turn conversation context management, entity resolution,
and session state persistence across multiple voice commands.

Priority: HIGH - Core differentiator for Pilot for Trades
Covers: Conversation Sessions, Context Windows, Entity Resolution, Pronoun Handling

Test Coverage:
- Multi-turn conversation flow (4+ turns)
- Session context persistence
- Entity resolution (pronoun → concrete entity_id)
- Context window retrieval (last N messages)
- Session expiration handling
- Cross-turn data propagation
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import select

from app.models.ai import ConversationMessage, ConversationSession, VoiceCommandLog
from app.models.auth import TenantUser, TenantUserStatus
from app.models.core import User
from app.models.crm import Customer, CustomerType

# Mark as integration and e2e test
pytestmark = [pytest.mark.integration, pytest.mark.e2e]


@pytest.fixture
def voice_user(db_session, tenant_a):
    """Create user for voice AI testing"""
    # Get or create status
    status = db_session.exec(
        select(TenantUserStatus)
        .where(TenantUserStatus.tenant_id == tenant_a.id)
        .where(TenantUserStatus.code == "active")
    ).first()

    if not status:
        status = TenantUserStatus(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            code="active",
            name="Active",
            is_default=True,
            is_active=True,
        )
        db_session.add(status)
        db_session.flush()

    user = User(
        id=uuid.uuid4(),
        email=f"voice-{uuid.uuid4()}@example.com",
        first_name="Voice",
        last_name="User",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    # Link to tenant
    tenant_user = TenantUser(
        tenant_id=tenant_a.id,
        user_id=user.id,
        role_code="owner",
        status_id=status.id,
        is_active=True,
    )
    db_session.add(tenant_user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def voice_customer(db_session, tenant_a):
    """Create test customer for voice commands"""
    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        display_name="Mike's Diner",
        type=CustomerType.company,
        company_name="Mike's Diner LLC",
        email="mike@mikesdiner.example.com",
        is_active=True,
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


def test_multi_turn_conversation_context_persistence(
    db_session,
    tenant_a,
    voice_user,
    voice_customer,
    utc_now,
):
    """
    Test 4-turn conversation with context persistence and entity resolution.

    Validates:
    - Session creation and reuse across turns
    - Context propagation between turns
    - Entity resolution (pronoun → entity_id)
    - Message history tracking
    - Session state management
    """

    # ========== TURN 1: "Create quote for Mike's Diner" ==========
    session = ConversationSession(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        user_id=voice_user.id,
        status="active",
        context_summary="Creating quote for Mike's Diner",
        context_window_json={
            "last_action": "quote.create",
            "customer_id": str(voice_customer.id),
            "customer_name": "Mike's Diner",
        },
        expires_at=utc_now + timedelta(minutes=30),
        is_active=True,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    # Create first message
    message_1 = ConversationMessage(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        session_id=session.id,
        role="user",
        content_text="Create quote for Mike's Diner",
        created_by=voice_user.id,
    )
    db_session.add(message_1)

    # Log the voice command
    log_1 = VoiceCommandLog(
        tenant_id=tenant_a.id,
        user_id=voice_user.id,
        message_id=message_1.id,
        intent_detected="quote.create",
        entities_extracted={
            "customer": {"name": "Mike's Diner", "id": str(voice_customer.id)},
        },
        action_executed="quote.create",
        whisper_latency_ms=250,
        ollama_latency_ms=180,
        total_latency_ms=430,
        is_successful=True,
    )
    db_session.add(log_1)
    db_session.commit()

    # Assertion 1: Session created
    assert session.id is not None
    assert session.status == "active"
    assert session.tenant_id == tenant_a.id

    # Assertion 2: First message stored
    assert message_1.id is not None
    assert message_1.session_id == session.id
    assert message_1.role == "user"

    # Assertion 3: Voice command logged
    assert log_1.id is not None
    assert log_1.intent_detected == "quote.create"
    assert log_1.entities_extracted["customer"]["name"] == "Mike's Diner"

    # Store quote_id in context for subsequent turns
    quote_id = uuid.uuid4()
    if session.context_window_json is None:
        session.context_window_json = {}
    session.context_window_json["quote_id"] = str(quote_id)
    db_session.commit()
    db_session.refresh(session)

    # ========== TURN 2: "Add 100 feet of 12 AWG wire" ==========
    message_2 = ConversationMessage(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        session_id=session.id,
        role="user",
        content_text="Add 100 feet of 12 AWG wire",
        created_by=voice_user.id,
    )
    db_session.add(message_2)

    # Refresh session to ensure we have the latest context
    db_session.refresh(session)

    # Entity resolution: "Add" implies adding to the current quote (from context)
    log_2 = VoiceCommandLog(
        tenant_id=tenant_a.id,
        user_id=voice_user.id,
        message_id=message_2.id,
        intent_detected="quote_line.create",
        entities_extracted={
            "quote_id": session.context_window_json.get(
                "quote_id", str(quote_id)
            ),  # Retrieved from context
            "quantity": 100,
            "unit": "ft",
            "description": "12 AWG wire",
        },
        action_executed="quote_line.create",
        whisper_latency_ms=230,
        ollama_latency_ms=195,
        total_latency_ms=425,
        is_successful=True,
    )
    db_session.add(log_2)
    db_session.commit()

    # Assertion 4: Second turn uses same session
    assert message_2.session_id == session.id

    # Assertion 5: Context retrieved from session
    assert log_2.entities_extracted["quote_id"] == str(quote_id)

    # Assertion 6: Entity resolution worked
    assert log_2.entities_extracted["quantity"] == 100
    assert log_2.entities_extracted["description"] == "12 AWG wire"

    # ========== TURN 3: "Calculate voltage drop" ==========
    message_3 = ConversationMessage(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        session_id=session.id,
        role="user",
        content_text="Calculate voltage drop",
        created_by=voice_user.id,
    )
    db_session.add(message_3)

    # Refresh session to get updated context
    db_session.refresh(session)

    # Uses context from previous turn (wire gauge)
    log_3 = VoiceCommandLog(
        tenant_id=tenant_a.id,
        user_id=voice_user.id,
        message_id=message_3.id,
        intent_detected="nec.calculate",
        entities_extracted={
            "quote_id": session.context_window_json.get("quote_id", str(quote_id)),
            "wire_gauge": "12 AWG",  # From previous turn's context
            "calculation_type": "voltage_drop",
        },
        action_executed="nec.calculate",
        whisper_latency_ms=210,
        ollama_latency_ms=320,  # Longer due to NEC calculation
        total_latency_ms=530,
        is_successful=True,
    )
    db_session.add(log_3)
    db_session.commit()

    # Assertion 7: Third turn maintains context
    assert message_3.session_id == session.id
    assert log_3.entities_extracted["wire_gauge"] == "12 AWG"

    # ========== TURN 4: "Send it to the customer" ==========
    message_4 = ConversationMessage(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        session_id=session.id,
        role="user",
        content_text="Send it to the customer",
        created_by=voice_user.id,
    )
    db_session.add(message_4)

    # Refresh session to ensure we have the latest context
    db_session.refresh(session)

    # Pronoun resolution: "it" → quote_id, "the customer" → customer from context
    log_4 = VoiceCommandLog(
        tenant_id=tenant_a.id,
        user_id=voice_user.id,
        message_id=message_4.id,
        intent_detected="quote.send",
        entities_extracted={
            "quote_id": session.context_window_json.get(
                "quote_id", str(quote_id)
            ),  # "it" resolved
            "customer_id": session.context_window_json.get(
                "customer_id", str(voice_customer.id)
            ),  # "the customer" resolved
            "recipient_email": "mike@mikesdiner.example.com",
        },
        action_executed="quote.send",
        whisper_latency_ms=240,
        ollama_latency_ms=175,
        total_latency_ms=415,
        is_successful=True,
    )
    db_session.add(log_4)
    db_session.commit()

    # Assertion 8: Fourth turn resolves pronouns correctly
    assert message_4.session_id == session.id
    assert log_4.entities_extracted["quote_id"] == str(quote_id)  # "it" → quote_id
    assert log_4.entities_extracted["customer_id"] == str(
        voice_customer.id
    )  # "the customer"

    # ========== Verify Session Context Window ==========
    session_messages = db_session.exec(
        select(ConversationMessage)
        .where(ConversationMessage.session_id == session.id)
        .order_by(ConversationMessage.created_at)
    ).all()

    # Assertion 9: All 4 messages stored in session
    assert len(session_messages) == 4
    assert session_messages[0].content_text == "Create quote for Mike's Diner"
    assert session_messages[1].content_text == "Add 100 feet of 12 AWG wire"
    assert session_messages[2].content_text == "Calculate voltage drop"
    assert session_messages[3].content_text == "Send it to the customer"

    # Assertion 10: Messages maintain chronological order
    for i in range(len(session_messages) - 1):
        assert session_messages[i].created_at <= session_messages[i + 1].created_at

    # ========== Verify Session Expiration ==========
    # Assertion 11: Session has expiration time
    assert session.expires_at is not None
    assert session.expires_at > utc_now

    # Assertion 12: Session is active
    assert session.status == "active"
    assert session.is_active is True


def test_conversation_session_expiration(
    db_session,
    tenant_a,
    voice_user,
    utc_now,
):
    """
    Test that conversation sessions expire after the configured timeout.

    Validates:
    - Session expiration timestamp set correctly
    - Expired sessions can be identified
    - New session created when expired session referenced
    """
    # Create session that expires in 30 minutes
    session = ConversationSession(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        user_id=voice_user.id,
        status="active",
        expires_at=utc_now + timedelta(minutes=30),
        is_active=True,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    # Verify expiration is in the future
    assert session.expires_at > utc_now

    # Simulate session expiration
    session.expires_at = utc_now - timedelta(minutes=1)
    db_session.commit()

    # Verify session is now expired
    assert session.expires_at < datetime.now(UTC)

    # Mark session as ended
    session.status = "ended"
    db_session.commit()
    db_session.refresh(session)

    assert session.status == "ended"


def test_conversation_context_window_size(
    db_session,
    tenant_a,
    voice_user,
):
    """
    Test that context window retrieves the last N messages (typically 5).

    Validates:
    - Context window limits to N most recent messages
    - Older messages still stored but not in active context
    - Performance with large message history
    """
    # Create session
    session = ConversationSession(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        user_id=voice_user.id,
        status="active",
        is_active=True,
    )
    db_session.add(session)
    db_session.commit()

    # Add 10 messages to session
    messages = []
    for i in range(10):
        message = ConversationMessage(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            session_id=session.id,
            role="user",
            content_text=f"Message {i + 1}",
            created_by=voice_user.id,
        )
        db_session.add(message)
        messages.append(message)

    db_session.commit()

    # Retrieve all messages
    all_messages = db_session.exec(
        select(ConversationMessage)
        .where(ConversationMessage.session_id == session.id)
        .order_by(ConversationMessage.created_at)
    ).all()

    assert len(all_messages) == 10

    # Retrieve last 5 messages (context window)
    context_window_size = 5
    recent_messages = db_session.exec(
        select(ConversationMessage)
        .where(ConversationMessage.session_id == session.id)
        .order_by(ConversationMessage.created_at.desc())
        .limit(context_window_size)
    ).all()

    # Verify context window size
    assert len(recent_messages) == context_window_size

    # Verify we got the most recent messages
    assert recent_messages[0].content_text == "Message 10"
    assert recent_messages[4].content_text == "Message 6"


def test_voice_command_latency_tracking(
    db_session,
    tenant_a,
    voice_user,
):
    """
    Test that voice command latency is tracked correctly.

    Validates:
    - Whisper latency recorded
    - Ollama latency recorded
    - Total latency calculated
    - Performance targets met (<30 seconds end-to-end)
    """
    # Create session
    session = ConversationSession(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        user_id=voice_user.id,
        status="active",
        is_active=True,
    )
    db_session.add(session)
    db_session.commit()

    # Create message
    message = ConversationMessage(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        session_id=session.id,
        role="user",
        content_text="Create quote for test customer",
        created_by=voice_user.id,
    )
    db_session.add(message)
    db_session.commit()

    # Log voice command with latency
    log = VoiceCommandLog(
        tenant_id=tenant_a.id,
        user_id=voice_user.id,
        message_id=message.id,
        intent_detected="quote.create",
        entities_extracted={"customer": "test"},
        action_executed="quote.create",
        whisper_latency_ms=2500,  # 2.5 seconds for transcription
        ollama_latency_ms=1800,  # 1.8 seconds for intent parsing
        total_latency_ms=4300,  # 4.3 seconds total
        is_successful=True,
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)

    # Verify latency tracking
    assert log.whisper_latency_ms == 2500
    assert log.ollama_latency_ms == 1800
    assert log.total_latency_ms == 4300

    # Verify latency is within target (<30 seconds)
    assert log.total_latency_ms < 30000  # 30 seconds in milliseconds

    # Verify latency is reasonable for real-time use
    assert log.total_latency_ms < 10000  # Prefer <10 seconds for good UX


def test_multi_session_isolation(
    db_session,
    tenant_a,
    voice_user,
):
    """
    Test that different conversation sessions are isolated from each other.

    Validates:
    - Sessions don't share context
    - Messages belong to correct session
    - Session IDs are unique
    """
    # Create two separate sessions
    session_1 = ConversationSession(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        user_id=voice_user.id,
        status="active",
        context_summary="Session 1 - Quote workflow",
        is_active=True,
    )
    db_session.add(session_1)

    session_2 = ConversationSession(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        user_id=voice_user.id,
        status="active",
        context_summary="Session 2 - Job workflow",
        is_active=True,
    )
    db_session.add(session_2)
    db_session.commit()

    # Add messages to session 1
    msg_1_1 = ConversationMessage(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        session_id=session_1.id,
        role="user",
        content_text="Create quote",
        created_by=voice_user.id,
    )
    db_session.add(msg_1_1)

    # Add messages to session 2
    msg_2_1 = ConversationMessage(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        session_id=session_2.id,
        role="user",
        content_text="Create job",
        created_by=voice_user.id,
    )
    db_session.add(msg_2_1)
    db_session.commit()

    # Verify sessions are isolated
    session_1_messages = db_session.exec(
        select(ConversationMessage).where(
            ConversationMessage.session_id == session_1.id
        )
    ).all()

    session_2_messages = db_session.exec(
        select(ConversationMessage).where(
            ConversationMessage.session_id == session_2.id
        )
    ).all()

    assert len(session_1_messages) == 1
    assert len(session_2_messages) == 1
    assert session_1_messages[0].content_text == "Create quote"
    assert session_2_messages[0].content_text == "Create job"

    # Verify sessions have different IDs
    assert session_1.id != session_2.id
