"""
Batch B2 — A12 Test Coverage
============================

A12: Conversation Message Structured Content Payload with Live/Snapshot Modes

Test Coverage:
- ConversationMessage.structured_content_json field exists on ORM model
- structured_content_json can be NULL for plain-text messages
- structured_content_json stores valid artifact payload shape
- freeze_session_quote_previews freezes live quote_preview messages to snapshot
- freeze_session_quote_previews skips messages already in snapshot mode (never unfreeze)
- freeze_session_quote_previews skips non-quote_preview artifact types
- freeze_session_quote_previews respects excluding_message_id
- freeze_session_quote_previews returns count of frozen messages
- GET /api/v1/voice/sessions/test/{id}/messages returns structured_content_json per message
"""

import uuid
from unittest.mock import patch

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# A12 — ORM field checks
# ─────────────────────────────────────────────────────────────────────────────


class TestA12ORMField:
    """Verify ConversationMessage.structured_content_json field exists."""

    def test_conversation_message_has_structured_content_json(self):
        from app.models.ai import ConversationMessage

        assert hasattr(ConversationMessage, "structured_content_json")

    def test_structured_content_json_is_nullable(
        self, db_session, test_tenant, test_user
    ):
        """Plain-text messages have structured_content_json = NULL."""
        from app.models.ai import ConversationMessage, ConversationSession

        session = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
        )
        db_session.add(session)
        db_session.flush()

        msg = ConversationMessage(
            session_id=session.id,
            tenant_id=session.tenant_id,
            role="user",
            content_text="Create a quote for Tom",
            created_by=test_user.id,
        )
        db_session.add(msg)
        db_session.flush()
        db_session.refresh(msg)

        assert msg.structured_content_json is None

    def test_structured_content_json_stores_artifact_payload(
        self, db_session, test_tenant, test_user
    ):
        """structured_content_json can store a complete artifact payload."""
        from app.models.ai import ConversationMessage, ConversationSession

        session = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
        )
        db_session.add(session)
        db_session.flush()

        artifact_payload = {
            "render_mode": "live",
            "artifact_type": "quote_preview",
            "entity_id": str(uuid.uuid4()),
            "entity_version_id": None,
            "snapshot_payload": None,
            "render_hints": {"newly_added_line_ids": []},
        }

        msg = ConversationMessage(
            session_id=session.id,
            tenant_id=session.tenant_id,
            role="assistant",
            content_text="Created Quote #abc123",
            structured_content_json=artifact_payload,
        )
        db_session.add(msg)
        db_session.flush()
        db_session.refresh(msg)

        assert msg.structured_content_json is not None
        assert msg.structured_content_json["render_mode"] == "live"
        assert msg.structured_content_json["artifact_type"] == "quote_preview"


# ─────────────────────────────────────────────────────────────────────────────
# A12 — freeze_session_quote_previews tests
# ─────────────────────────────────────────────────────────────────────────────


class TestA12FreezeFunction:
    """Unit tests for freeze_session_quote_previews."""

    def _make_session_with_messages(
        self, db_session, test_tenant, test_user, payloads: list
    ) -> tuple:
        """Helper: create a ConversationSession with messages having given payloads."""
        from app.models.ai import ConversationMessage, ConversationSession

        session = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
        )
        db_session.add(session)
        db_session.flush()

        messages = []
        for payload in payloads:
            msg = ConversationMessage(
                session_id=session.id,
                tenant_id=session.tenant_id,
                role="assistant",
                content_text="Quote created",
                structured_content_json=payload,
            )
            db_session.add(msg)
            messages.append(msg)

        db_session.flush()
        return session, messages

    def test_freeze_converts_live_to_snapshot(self, db_session, test_tenant, test_user):
        """freeze_session_quote_previews changes render_mode from live to snapshot."""
        from services.voice_session_service import freeze_session_quote_previews

        entity_id = str(uuid.uuid4())
        live_payload = {
            "render_mode": "live",
            "artifact_type": "quote_preview",
            "entity_id": entity_id,
        }

        session, messages = self._make_session_with_messages(
            db_session, test_tenant, test_user, [live_payload]
        )

        # Mock the entity snapshot (no actual Quote in test DB)
        with patch(
            "services.voice_session_service._capture_entity_snapshot",
            return_value={"captured": True},
        ):
            frozen_count = freeze_session_quote_previews(db_session, session)

        assert frozen_count == 1
        db_session.refresh(messages[0])
        assert messages[0].structured_content_json["render_mode"] == "snapshot"
        assert messages[0].structured_content_json["snapshot_payload"] == {
            "captured": True
        }

    def test_freeze_never_unfreezes_snapshot(self, db_session, test_tenant, test_user):
        """Messages already in snapshot mode are never transitioned back to live."""
        from services.voice_session_service import freeze_session_quote_previews

        snapshot_payload = {
            "render_mode": "snapshot",
            "artifact_type": "quote_preview",
            "entity_id": str(uuid.uuid4()),
            "snapshot_payload": {"already_frozen": True},
        }

        session, messages = self._make_session_with_messages(
            db_session, test_tenant, test_user, [snapshot_payload]
        )

        with patch(
            "services.voice_session_service._capture_entity_snapshot", return_value={}
        ):
            frozen_count = freeze_session_quote_previews(db_session, session)

        # Should not freeze already-frozen messages
        assert frozen_count == 0
        db_session.refresh(messages[0])
        assert messages[0].structured_content_json["render_mode"] == "snapshot"
        assert messages[0].structured_content_json["snapshot_payload"] == {
            "already_frozen": True
        }

    def test_freeze_skips_non_quote_preview_artifacts(
        self, db_session, test_tenant, test_user
    ):
        """freeze_session_quote_previews only freezes quote_preview, not job_preview."""
        from services.voice_session_service import freeze_session_quote_previews

        job_payload = {
            "render_mode": "live",
            "artifact_type": "job_preview",  # Not a quote_preview
            "entity_id": str(uuid.uuid4()),
        }

        session, messages = self._make_session_with_messages(
            db_session, test_tenant, test_user, [job_payload]
        )

        with patch(
            "services.voice_session_service._capture_entity_snapshot", return_value={}
        ):
            frozen_count = freeze_session_quote_previews(db_session, session)

        assert frozen_count == 0
        db_session.refresh(messages[0])
        assert messages[0].structured_content_json["render_mode"] == "live"  # unchanged

    def test_freeze_respects_excluding_message_id(
        self, db_session, test_tenant, test_user
    ):
        """freeze_session_quote_previews skips the excluded message (just-emitted)."""
        from services.voice_session_service import freeze_session_quote_previews

        entity_id = str(uuid.uuid4())
        live_payload_1 = {
            "render_mode": "live",
            "artifact_type": "quote_preview",
            "entity_id": entity_id,
        }
        live_payload_2 = {
            "render_mode": "live",
            "artifact_type": "quote_preview",
            "entity_id": entity_id,
        }

        session, messages = self._make_session_with_messages(
            db_session, test_tenant, test_user, [live_payload_1, live_payload_2]
        )

        # Exclude the second message (just-emitted)
        with patch(
            "services.voice_session_service._capture_entity_snapshot",
            return_value={"snap": True},
        ):
            frozen_count = freeze_session_quote_previews(
                db_session, session, excluding_message_id=messages[1].id
            )

        # Only the first message should be frozen
        assert frozen_count == 1
        db_session.refresh(messages[0])
        db_session.refresh(messages[1])
        assert messages[0].structured_content_json["render_mode"] == "snapshot"
        assert (
            messages[1].structured_content_json["render_mode"] == "live"
        )  # excluded, stays live

    def test_freeze_returns_count_of_frozen_messages(
        self, db_session, test_tenant, test_user
    ):
        """freeze_session_quote_previews returns the count of messages frozen."""
        from services.voice_session_service import freeze_session_quote_previews

        entity_id = str(uuid.uuid4())
        payloads = [
            {
                "render_mode": "live",
                "artifact_type": "quote_preview",
                "entity_id": entity_id,
            },
            {
                "render_mode": "live",
                "artifact_type": "quote_preview",
                "entity_id": entity_id,
            },
            {
                "render_mode": "snapshot",
                "artifact_type": "quote_preview",
                "entity_id": entity_id,
                "snapshot_payload": {},
            },  # already frozen — should NOT count
        ]

        session, messages = self._make_session_with_messages(
            db_session, test_tenant, test_user, payloads
        )

        with patch(
            "services.voice_session_service._capture_entity_snapshot",
            return_value={"s": 1},
        ):
            frozen_count = freeze_session_quote_previews(db_session, session)

        assert frozen_count == 2  # Only the 2 live ones

    def test_freeze_no_structured_messages_returns_zero(
        self, db_session, test_tenant, test_user
    ):
        """freeze_session_quote_previews returns 0 for plain-text-only sessions."""
        from app.models.ai import ConversationMessage, ConversationSession
        from services.voice_session_service import freeze_session_quote_previews

        session = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
        )
        db_session.add(session)
        db_session.flush()

        # Plain text message, no structured_content_json
        msg = ConversationMessage(
            session_id=session.id,
            tenant_id=session.tenant_id,
            role="user",
            content_text="Hello",
        )
        db_session.add(msg)
        db_session.flush()

        frozen_count = freeze_session_quote_previews(db_session, session)
        assert frozen_count == 0


# ─────────────────────────────────────────────────────────────────────────────
# A12 — HTTP: messages endpoint returns structured_content_json
# ─────────────────────────────────────────────────────────────────────────────


class TestA12MessagesEndpoint:
    """Verify the messages endpoint returns structured_content_json field per message."""

    def test_messages_endpoint_includes_structured_content(
        self, client, db_session, test_tenant, test_user
    ):
        """Messages with structured_content_json have the field populated in response."""
        from app.models.ai import ConversationMessage, ConversationSession

        session = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
        )
        db_session.add(session)
        db_session.flush()

        artifact_payload = {
            "render_mode": "live",
            "artifact_type": "quote_preview",
            "entity_id": str(uuid.uuid4()),
            "snapshot_payload": None,
            "render_hints": {},
        }

        msg = ConversationMessage(
            session_id=session.id,
            tenant_id=session.tenant_id,
            role="assistant",
            content_text="Created quote #abc",
            structured_content_json=artifact_payload,
        )
        db_session.add(msg)
        db_session.flush()

        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("TEST_ENDPOINT_ENABLED", "true")
            mp.setenv("ENVIRONMENT", "dev")
            resp = client.get(f"/api/v1/voice/sessions/test/{session.id}/messages")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["messages"]) >= 1

        # Find the assistant message with structured content
        structured_msgs = [
            m for m in data["messages"] if m.get("structured_content_json")
        ]
        assert len(structured_msgs) >= 1
        sc = structured_msgs[0]["structured_content_json"]
        assert sc["render_mode"] == "live"
        assert sc["artifact_type"] == "quote_preview"
