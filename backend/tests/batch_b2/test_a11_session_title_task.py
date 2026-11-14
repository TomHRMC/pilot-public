"""
Batch B2 — A11 Test Coverage
============================

A11: Ollama-Generated Session Titles

Test Coverage:
- ConversationSession.title field exists on ORM model
- ConversationSession.title_auto_generated field exists and defaults to False
- ConversationSession.archived_at field exists and is nullable
- _generate_session_title_impl skips invalid UUID
- _generate_session_title_impl skips when session not found
- _generate_session_title_impl skips when user has set title (title_auto_generated=False)
- _generate_session_title_impl skips when no messages in session
- _generate_session_title_impl generates and saves title when Ollama succeeds
- _generate_session_title_impl handles Ollama failure gracefully (skips, returns reason)
- title_auto_generated=True allows overwrite, False is frozen
- generate_session_title Celery task is registered
"""

import uuid
from unittest.mock import patch

# ─────────────────────────────────────────────────────────────────────────────
# A11 — ORM field existence checks
# ─────────────────────────────────────────────────────────────────────────────


class TestA11ORMFields:
    """Verify B2 migration added the required fields to ConversationSession."""

    def test_conversation_session_has_title_field(self):
        from app.models.ai import ConversationSession

        assert hasattr(ConversationSession, "title")

    def test_conversation_session_has_title_auto_generated_field(self):
        from app.models.ai import ConversationSession

        assert hasattr(ConversationSession, "title_auto_generated")

    def test_conversation_session_has_archived_at_field(self):
        from app.models.ai import ConversationSession

        assert hasattr(ConversationSession, "archived_at")

    def test_title_auto_generated_defaults_to_false(
        self, db_session, test_tenant, test_user
    ):
        """title_auto_generated defaults to False (user must explicitly set)."""
        from app.models.ai import ConversationSession

        session = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
        )
        db_session.add(session)
        db_session.flush()
        db_session.refresh(session)

        assert session.title_auto_generated is False

    def test_title_is_nullable(self, db_session, test_tenant, test_user):
        """title can be NULL (not set yet)."""
        from app.models.ai import ConversationSession

        session = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
        )
        db_session.add(session)
        db_session.flush()
        db_session.refresh(session)

        assert session.title is None

    def test_archived_at_is_nullable(self, db_session, test_tenant, test_user):
        """archived_at can be NULL (not archived)."""
        from app.models.ai import ConversationSession

        session = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
        )
        db_session.add(session)
        db_session.flush()
        db_session.refresh(session)

        assert session.archived_at is None


# ─────────────────────────────────────────────────────────────────────────────
# A11 — _generate_session_title_impl unit tests (no Celery, stubs Ollama)
# ─────────────────────────────────────────────────────────────────────────────


class TestA11TitleGenerationImpl:
    """Unit tests for the inner implementation function."""

    def test_invalid_uuid_skips(self, db_session):
        """Invalid session_id UUID returns skipped result."""
        from tasks.voice_session_title import _generate_session_title_impl

        result = _generate_session_title_impl("not-a-uuid", db_session)

        assert result["skipped"] is True
        assert result["reason"] == "invalid_uuid"

    def test_session_not_found_skips(self, db_session):
        """Non-existent session_id returns skipped result."""
        from tasks.voice_session_title import _generate_session_title_impl

        result = _generate_session_title_impl(str(uuid.uuid4()), db_session)

        assert result["skipped"] is True
        assert result["reason"] == "session_not_found"

    def test_user_set_title_frozen(self, db_session, test_tenant, test_user):
        """When title_auto_generated=False, task skips and preserves user title."""
        from app.models.ai import ConversationSession
        from tasks.voice_session_title import _generate_session_title_impl

        session = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
            title="My Custom Title",
            title_auto_generated=False,  # user-set
        )
        db_session.add(session)
        db_session.flush()

        result = _generate_session_title_impl(str(session.id), db_session)

        assert result["skipped"] is True
        assert result["reason"] == "user_set_title_frozen"
        assert result["title"] == "My Custom Title"

    def test_no_messages_skips(self, db_session, test_tenant, test_user):
        """Session with no messages returns skipped."""
        from app.models.ai import ConversationSession
        from tasks.voice_session_title import _generate_session_title_impl

        session = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
        )
        db_session.add(session)
        db_session.flush()

        result = _generate_session_title_impl(str(session.id), db_session)

        assert result["skipped"] is True
        assert result["reason"] == "no_messages"

    def test_generates_title_on_ollama_success(
        self, db_session, test_tenant, test_user
    ):
        """When Ollama returns a title, it is saved and title_auto_generated=True."""
        from app.models.ai import ConversationMessage, ConversationSession
        from tasks.voice_session_title import _generate_session_title_impl

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
            content_text="Create a quote for Tom Jones",
            created_by=test_user.id,
        )
        db_session.add(msg)
        db_session.flush()

        with patch(
            "services.ai_service.generate_text_sync", return_value="Tom Jones Quote"
        ):
            result = _generate_session_title_impl(str(session.id), db_session)

        assert result["skipped"] is False
        assert result["title"] == "Tom Jones Quote"
        db_session.refresh(session)
        assert session.title == "Tom Jones Quote"
        assert session.title_auto_generated is True

    def test_ollama_failure_skips_gracefully(self, db_session, test_tenant, test_user):
        """When Ollama raises an exception, task skips gracefully.

        B12 extension: the task now routes through voice_persona_renderer which
        catches Ollama errors and returns empty string. The task treats an empty
        renderer response as a skip (reason='empty_response'). Both code paths
        (renderer failure AND fallback failure) result in skipped=True.

        We patch at the renderer._call_ollama level so the exception propagates
        through the renderer, and also patch the ai_service fallback to ensure
        both inner and outer paths raise.
        """
        from app.models.ai import ConversationMessage, ConversationSession
        from tasks.voice_session_title import _generate_session_title_impl

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
            content_text="Create a quote",
            created_by=test_user.id,
        )
        db_session.add(msg)
        db_session.flush()

        # Patch both renderer and fallback to ensure graceful skip
        with (
            patch(
                "services.voice_persona_renderer._call_ollama",
                side_effect=Exception("Ollama timeout"),
            ),
            patch(
                "services.ai_service.generate_text_sync",
                side_effect=Exception("Ollama timeout"),
            ),
        ):
            result = _generate_session_title_impl(str(session.id), db_session)

        assert result["skipped"] is True
        # After B12: renderer raises → falls through to fallback → fallback raises → ollama_error
        assert result["reason"] is not None
        # Session title should NOT be updated
        db_session.refresh(session)
        assert session.title is None

    def test_auto_generated_title_can_be_overwritten(
        self, db_session, test_tenant, test_user
    ):
        """title_auto_generated=True means the task can overwrite the title."""
        from app.models.ai import ConversationMessage, ConversationSession
        from tasks.voice_session_title import _generate_session_title_impl

        session = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
            title="Old AI Title",
            title_auto_generated=True,  # AI-generated → overwritable
        )
        db_session.add(session)
        db_session.flush()

        msg = ConversationMessage(
            session_id=session.id,
            tenant_id=session.tenant_id,
            role="user",
            content_text="Update the quote for Davis",
            created_by=test_user.id,
        )
        db_session.add(msg)
        db_session.flush()

        with patch(
            "services.ai_service.generate_text_sync", return_value="Davis Quote Update"
        ):
            result = _generate_session_title_impl(str(session.id), db_session)

        assert result["skipped"] is False
        assert result["title"] == "Davis Quote Update"


# ─────────────────────────────────────────────────────────────────────────────
# A11 — Celery task registration
# ─────────────────────────────────────────────────────────────────────────────


class TestA11CeleryRegistration:
    """Verify the generate_session_title task is importable and registered."""

    def test_generate_session_title_task_importable(self):
        from tasks.voice_session_title import generate_session_title

        assert callable(generate_session_title)

    def test_generate_session_title_is_celery_task(self):
        from tasks.voice_session_title import generate_session_title

        # Celery tasks are callable with .delay() and .apply_async()
        assert hasattr(generate_session_title, "delay")
        assert hasattr(generate_session_title, "apply_async")

    def test_voice_session_title_in_celery_imports(self):
        from core.celery_app import celery_app

        imports = celery_app.conf.imports
        assert "tasks.voice_session_title" in imports
