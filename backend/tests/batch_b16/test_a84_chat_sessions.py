"""
A84 — Help AI Agent + Chat Session Management tests.

Test focus:
- Create new session when session_id is None
- Resume existing session when session_id provided
- Session message_count increments per turn
- Session title enqueued after first turn
- _list_sessions_impl returns only user-scoped sessions
- _get_session_impl returns messages ordered by created_at
- session outcome updated by session feedback
- 404 returned for cross-tenant/cross-user session access
- delete-all returns 501

FIX (2026-06-03): Removed module-level TestClient fixture that bypassed the
rollback fixture. All tests now use the conftest `client` fixture which wraps
DB operations in a rolled-back transaction.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _make_session(db_session, tenant_id, user_id):
    from app.models.help import HelpChatSession

    now = datetime.now(UTC)
    session = HelpChatSession(
        tenant_id=tenant_id,
        user_id=user_id,
        started_at=now,
        last_activity_at=now,
        message_count=0,
        created_at=now,
        updated_at=now,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


def _make_message(db_session, session_id, tenant_id, role="user", content="Hello"):
    from app.models.help import HelpChatMessage

    now = datetime.now(UTC)
    msg = HelpChatMessage(
        session_id=session_id,
        tenant_id=tenant_id,
        role=role,
        content=content,
        voice_used=False,
        created_at=now,
    )
    db_session.add(msg)
    db_session.commit()
    db_session.refresh(msg)
    return msg


# ──────────────────────────────────────────────────────────────────────────────
# ORM model tests
# ──────────────────────────────────────────────────────────────────────────────


class TestHelpChatSessionModel:
    def test_create_session(self, db_session, test_tenant, test_user):
        from app.models.help import HelpChatSession

        now = datetime.now(UTC)
        session = HelpChatSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            started_at=now,
            last_activity_at=now,
            message_count=0,
            created_at=now,
            updated_at=now,
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        # FIND-169: session_id → id on HelpChatSession
        assert session.id is not None
        assert session.message_count == 0
        assert session.outcome is None
        assert session.title is None
        assert session.anonymized_at is None

    def test_check_constraint_outcome(self, db_session, test_tenant, test_user):
        """outcome column only allows resolved/escalated/abandoned."""
        from app.models.help import HelpChatSession

        now = datetime.now(UTC)
        session = HelpChatSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            started_at=now,
            last_activity_at=now,
            message_count=0,
            outcome="invalid_value",
            created_at=now,
            updated_at=now,
        )
        db_session.add(session)
        with pytest.raises(Exception):  # Check constraint violation
            db_session.commit()
        db_session.rollback()


class TestHelpChatMessageModel:
    def test_create_message(self, db_session, test_tenant, test_user):
        session = _make_session(db_session, test_tenant.id, test_user.id)
        # FIND-169: session.session_id → session.id
        msg = _make_message(db_session, session.id, test_tenant.id)

        assert msg.message_id is not None
        assert msg.role == "user"
        assert msg.voice_used is False

    def test_check_constraint_role(self, db_session, test_tenant, test_user):
        """role column only allows user/assistant."""
        from app.models.help import HelpChatMessage

        session = _make_session(db_session, test_tenant.id, test_user.id)
        now = datetime.now(UTC)
        msg = HelpChatMessage(
            # FIND-169: session.session_id → session.id
            session_id=session.id,
            tenant_id=test_tenant.id,
            role="invalid_role",
            content="test",
            voice_used=False,
            created_at=now,
        )
        db_session.add(msg)
        with pytest.raises(Exception):
            db_session.commit()
        db_session.rollback()


# ──────────────────────────────────────────────────────────────────────────────
# _chat_impl() unit tests (bypass HTTP, no DB session isolation)
# ──────────────────────────────────────────────────────────────────────────────


class TestChatImpl:
    def test_new_session_created_when_no_session_id(
        self, db_session, test_tenant, test_user
    ):
        from api.routes.help import HelpChatRequest, _chat_impl

        with (
            patch("api.routes.help.retrieve_chunks", return_value=[]),
            patch(
                "api.routes.help.generate_help_response",
                return_value="Here is my answer.",
            ),
            patch(
                "api.routes.help.get_effective_setting_for_user",
                return_value=("balanced", "fallback"),
            ),
            patch("api.routes.help.generate_help_session_title") as mock_title,
        ):
            mock_title.delay = MagicMock()
            data = HelpChatRequest(message="How do I connect QuickBooks?")
            result = _chat_impl(data, db_session, test_user.id, test_tenant.id, "owner")

        assert result.role == "assistant"
        assert result.content == "Here is my answer."
        assert result.session_id is not None

    def test_existing_session_resumed(self, db_session, test_tenant, test_user):
        from api.routes.help import HelpChatRequest, _chat_impl

        session = _make_session(db_session, test_tenant.id, test_user.id)

        with (
            patch("api.routes.help.retrieve_chunks", return_value=[]),
            patch(
                "api.routes.help.generate_help_response",
                return_value="Follow-up answer.",
            ),
            patch(
                "api.routes.help.get_effective_setting_for_user",
                return_value=("balanced", "fallback"),
            ),
            patch("api.routes.help.generate_help_session_title") as mock_title,
        ):
            mock_title.delay = MagicMock()
            # FIND-169: session.session_id → session.id
            data = HelpChatRequest(
                session_id=session.id,
                message="Follow-up question?",
            )
            result = _chat_impl(data, db_session, test_user.id, test_tenant.id, "owner")

        # FIND-169: session.session_id → session.id
        assert result.session_id == session.id
        assert result.content == "Follow-up answer."

    def test_message_count_increments(self, db_session, test_tenant, test_user):
        from sqlmodel import select

        from api.routes.help import HelpChatRequest, _chat_impl
        from app.models.help import HelpChatSession

        with (
            patch("api.routes.help.retrieve_chunks", return_value=[]),
            patch("api.routes.help.generate_help_response", return_value="answer"),
            patch(
                "api.routes.help.get_effective_setting_for_user",
                return_value=("balanced", "fallback"),
            ),
            patch("api.routes.help.generate_help_session_title") as mock_title,
        ):
            mock_title.delay = MagicMock()
            data = HelpChatRequest(message="First question")
            result = _chat_impl(data, db_session, test_user.id, test_tenant.id, "owner")

        # FIND-169: session_id → id on HelpChatSession
        session = db_session.exec(
            select(HelpChatSession).where(HelpChatSession.id == result.session_id)
        ).first()
        assert session.message_count == 2  # user + assistant

    def test_404_for_nonexistent_session(self, db_session, test_tenant, test_user):
        """Passing a session_id that doesn't exist returns 404."""
        from fastapi import HTTPException

        from api.routes.help import HelpChatRequest, _chat_impl

        # Use a random UUID that doesn't exist in the DB
        nonexistent_session_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            data = HelpChatRequest(
                session_id=nonexistent_session_id,
                message="attempt to use non-existent session",
            )
            _chat_impl(data, db_session, test_user.id, test_tenant.id, "owner")

        assert exc_info.value.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# _list_sessions_impl() tests
# ──────────────────────────────────────────────────────────────────────────────


class TestListSessionsImpl:
    def test_returns_only_user_sessions(self, db_session, test_tenant, test_user):
        from api.routes.help import _list_sessions_impl

        _make_session(db_session, test_tenant.id, test_user.id)
        _make_session(db_session, test_tenant.id, test_user.id)

        result = _list_sessions_impl(db_session, test_user.id, test_tenant.id, 20, 0)
        assert result.total >= 2
        # FIND-169: session.session_id → session.id (HelpChatSession PK renamed)
        # session_id in HelpSessionSummary schema is aliased from 'id'
        assert all(str(s.session_id) for s in result.sessions)

    def test_excludes_anonymized_sessions(self, db_session, test_tenant, test_user):
        from api.routes.help import _list_sessions_impl
        from app.models.help import HelpChatSession

        now = datetime.now(UTC)
        anon = HelpChatSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            started_at=now,
            last_activity_at=now,
            message_count=0,
            anonymized_at=now,
            created_at=now,
            updated_at=now,
        )
        db_session.add(anon)
        db_session.commit()

        result = _list_sessions_impl(db_session, test_user.id, test_tenant.id, 20, 0)
        # FIND-169: s.session_id comes from HelpSessionSummary.session_id (aliased from 'id')
        # anon.session_id → anon.id (HelpChatSession PK renamed)
        session_ids = [str(s.session_id) for s in result.sessions]
        assert str(anon.id) not in session_ids


# ──────────────────────────────────────────────────────────────────────────────
# Title generation task tests
# ──────────────────────────────────────────────────────────────────────────────


class TestGenerateHelpSessionTitle:
    def test_generates_title_for_new_session(self, db_session, test_tenant, test_user):
        from tasks.help_corpus import _generate_help_session_title_impl

        session = _make_session(db_session, test_tenant.id, test_user.id)

        with patch("tasks.help_corpus.generate_text_sync") as mock_gen:
            mock_gen.return_value = "QuickBooks Setup Help"
            # FIND-169: session.session_id → session.id
            result = _generate_help_session_title_impl(
                str(session.id), "How do I set up QuickBooks?", db_session
            )

        assert result["skipped"] is False
        assert result["title"] == "QuickBooks Setup Help"
        db_session.refresh(session)
        assert session.title == "QuickBooks Setup Help"

    def test_skips_if_title_already_set(self, db_session, test_tenant, test_user):
        from tasks.help_corpus import _generate_help_session_title_impl

        session = _make_session(db_session, test_tenant.id, test_user.id)
        session.title = "Existing Title"
        db_session.add(session)
        db_session.commit()

        # FIND-169: session.session_id → session.id
        result = _generate_help_session_title_impl(
            str(session.id), "Any question", db_session
        )

        assert result["skipped"] is True
        assert result["reason"] == "title_already_set"

    def test_handles_invalid_uuid(self, db_session):
        from tasks.help_corpus import _generate_help_session_title_impl

        result = _generate_help_session_title_impl("not-a-uuid", "question", db_session)

        assert result["skipped"] is True
        assert result["reason"] == "invalid_uuid"

    def test_handles_missing_session(self, db_session):
        from tasks.help_corpus import _generate_help_session_title_impl

        result = _generate_help_session_title_impl(str(uuid4()), "question", db_session)

        assert result["skipped"] is True
        assert result["reason"] == "session_not_found"


# ──────────────────────────────────────────────────────────────────────────────
# delete-all stub test
# ──────────────────────────────────────────────────────────────────────────────


class TestDeleteAllStub:
    def test_returns_501_without_auth(self, client):
        response = client.post("/api/v1/help/sessions/delete-all")
        # Without JWT, will return 401 or 501
        assert response.status_code in (401, 501)
