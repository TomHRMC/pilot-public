from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.ai import ConversationMessage, ConversationSession, VoiceCommandLog
from tests.test_phase2 import setup_test_user


def test_voice_command_success(
    client: TestClient, db_session: Session, mock_cognito_jwt_verify
):
    headers, user_id, tenant_id = setup_test_user(client, db_session)

    # We need to mock the ai_service functions
    with (
        patch("api.routes.voice.transcribe_audio") as mock_transcribe,
        patch("api.routes.voice.get_embedding") as mock_embedding,
        patch("api.routes.voice.parse_intent") as mock_parse_intent,
    ):
        mock_transcribe.return_value = "Add a 20 amp breaker to the subpanel."
        mock_embedding.return_value = [0.1] * 1024
        mock_parse_intent.return_value = '{"intent": "add_item", "entities": {"item": "20 amp breaker", "panel": "subpanel"}}'

        # We need a fake audio file
        files = {"audio": ("test.m4a", b"dummy audio content", "audio/mp4")}

        response = client.post(
            "/api/v1/voice/command",
            headers=headers,
            files=files,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["transcribed_text"] == "Add a 20 amp breaker to the subpanel."
        assert "parsed_intent" in data
        assert data["parsed_intent"]["intent"] == "add_item"
        assert data["session_id"] is not None

        session_id = data["session_id"]

        # Verify Database Insertions

        # 1. ConversationSession
        session = db_session.exec(
            select(ConversationSession).where(ConversationSession.id == session_id)
        ).first()
        assert session is not None
        assert session.tenant_id == tenant_id

        # 2. ConversationMessage (should be 2: user, assistant)
        messages = db_session.exec(
            select(ConversationMessage)
            .where(ConversationMessage.session_id == session_id)
            .order_by(ConversationMessage.created_at)
        ).all()

        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content_text == "Add a 20 amp breaker to the subpanel."
        assert messages[1].role == "assistant"
        assert "add_item" in messages[1].content_text

        # 3. VoiceCommandLog
        log_entry = db_session.exec(
            select(VoiceCommandLog).where(VoiceCommandLog.message_id == messages[0].id)
        ).first()
        assert log_entry is not None
        assert log_entry.tenant_id == tenant_id
        assert log_entry.intent_detected == "add_item"
        assert log_entry.whisper_latency_ms is not None
        assert log_entry.ollama_latency_ms is not None
        assert log_entry.total_latency_ms is not None
