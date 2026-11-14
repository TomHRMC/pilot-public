"""
Batch B2 — A10 Test Coverage
============================

A10: Voice Command Grammar for Session Management

Test Coverage:
- INTENT_HANDLERS contains rename_session, delete_session, open_session, query_session_summary
- All 4 handlers are async coroutines with the correct 4-parameter signature
- rename_session renames the current session (sets title, title_auto_generated=False)
- rename_session returns disambiguation when session_number not found
- rename_session requires new_title entity (returns error when missing)
- delete_session first turn returns requires_confirmation=True
- delete_session second turn (pending_confirmation set) executes soft-delete
- delete_session returns disambiguation when session_number not found
- open_session returns navigate_to data for the target session
- open_session returns disambiguation when session_number not found
- query_session_summary returns the session title/summary
- query_session_summary returns disambiguation for missing session number
"""

import asyncio
import inspect
import uuid
from unittest.mock import MagicMock

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
    session.id = uuid.uuid4()
    session.context_window_json = context or {}
    session.title = None
    session.title_auto_generated = True
    session.context_summary = None
    return session


def run(coro):
    """Run a coroutine synchronously in tests."""
    return asyncio.run(coro)


# ─────────────────────────────────────────────────────────────────────────────
# A10 — INTENT_HANDLERS registration
# ─────────────────────────────────────────────────────────────────────────────


class TestA10IntentRegistration:
    """Verify all 4 A10 intents are registered in INTENT_HANDLERS."""

    def test_rename_session_in_intent_handlers(self):
        from services.voice_action_router import INTENT_HANDLERS

        assert "rename_session" in INTENT_HANDLERS

    def test_delete_session_in_intent_handlers(self):
        from services.voice_action_router import INTENT_HANDLERS

        assert "delete_session" in INTENT_HANDLERS

    def test_open_session_in_intent_handlers(self):
        from services.voice_action_router import INTENT_HANDLERS

        assert "open_session" in INTENT_HANDLERS

    def test_query_session_summary_in_intent_handlers(self):
        from services.voice_action_router import INTENT_HANDLERS

        assert "query_session_summary" in INTENT_HANDLERS

    def test_all_a10_handlers_are_coroutines(self):
        from services.voice_action_router import (
            delete_session_via_voice,
            open_session_via_voice,
            query_session_summary_via_voice,
            rename_session_via_voice,
        )

        for handler in [
            rename_session_via_voice,
            delete_session_via_voice,
            open_session_via_voice,
            query_session_summary_via_voice,
        ]:
            assert inspect.iscoroutinefunction(handler), (
                f"{handler.__name__} must be async"
            )

    def test_all_a10_handlers_have_correct_signature(self):
        from services.voice_action_router import (
            delete_session_via_voice,
            open_session_via_voice,
            query_session_summary_via_voice,
            rename_session_via_voice,
        )

        for handler in [
            rename_session_via_voice,
            delete_session_via_voice,
            open_session_via_voice,
            query_session_summary_via_voice,
        ]:
            sig = inspect.signature(handler)
            params = list(sig.parameters.keys())
            assert params == ["entities", "current_user", "db", "session"], (
                f"{handler.__name__} must have signature (entities, current_user, db, session)"
            )


# ─────────────────────────────────────────────────────────────────────────────
# A10 — rename_session_via_voice
# ─────────────────────────────────────────────────────────────────────────────


class TestA10RenameSession:
    """Unit tests for rename_session_via_voice handler."""

    def test_rename_session_renames_current_session(
        self, db_session, test_tenant, test_user
    ):
        """rename_session sets title on current session and freezes it."""
        from app.models.ai import ConversationSession
        from services.voice_action_router import rename_session_via_voice

        session = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
            title_auto_generated=True,
        )
        db_session.add(session)
        db_session.flush()

        mock_user = make_mock_user(tenant_id=test_tenant.id)
        mock_user.id = test_user.id

        result = run(
            rename_session_via_voice(
                entities={"new_title": "Johnson Panel Upgrade"},
                current_user=mock_user,
                db=db_session,
                session=session,
            )
        )

        assert result["success"] is True
        assert result["action"] == "rename_session"
        # Verify DB was updated
        db_session.refresh(session)
        assert session.title == "Johnson Panel Upgrade"
        assert session.title_auto_generated is False  # user-set → frozen

    def test_rename_session_missing_title_returns_error(
        self, db_session, test_tenant, test_user
    ):
        """rename_session returns failure when no new_title entity provided."""
        from app.models.ai import ConversationSession
        from services.voice_action_router import rename_session_via_voice

        session = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
        )
        db_session.add(session)
        db_session.flush()

        mock_user = make_mock_user(tenant_id=test_tenant.id)
        mock_user.id = test_user.id

        result = run(
            rename_session_via_voice(
                entities={},  # No new_title
                current_user=mock_user,
                db=db_session,
                session=session,
            )
        )

        assert result["success"] is False
        assert result["action"] == "rename_session"

    def test_rename_session_disambiguation_for_missing_number(
        self, db_session, test_tenant, test_user
    ):
        """rename_session returns disambiguation when session_number not found."""
        from app.models.ai import ConversationSession
        from services.voice_action_router import rename_session_via_voice

        session = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
        )
        db_session.add(session)
        db_session.flush()

        mock_user = make_mock_user(tenant_id=test_tenant.id)
        mock_user.id = test_user.id

        result = run(
            rename_session_via_voice(
                entities={"session_number": 9999, "new_title": "Test"},
                current_user=mock_user,
                db=db_session,
                session=session,
            )
        )

        assert result["success"] is True
        assert result.get("requires_disambiguation") is True


# ─────────────────────────────────────────────────────────────────────────────
# A10 — delete_session_via_voice
# ─────────────────────────────────────────────────────────────────────────────


class TestA10DeleteSession:
    """Unit tests for delete_session_via_voice — confirm-as-turn pattern."""

    def test_delete_session_first_turn_returns_confirmation_prompt(
        self, db_session, test_tenant, test_user
    ):
        """First turn writes pending_confirmation and returns requires_confirmation=True."""
        from app.models.ai import ConversationSession
        from services.voice_action_router import delete_session_via_voice

        session = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
            title="Current Session",
        )
        db_session.add(session)
        db_session.flush()

        mock_user = make_mock_user(tenant_id=test_tenant.id)
        mock_user.id = test_user.id

        result = run(
            delete_session_via_voice(
                entities={},  # No session_number → targets current session
                current_user=mock_user,
                db=db_session,
                session=session,
            )
        )

        assert result["success"] is True
        assert result.get("requires_confirmation") is True
        assert result["action"] == "delete_session"
        # Verify pending_confirmation was written
        db_session.refresh(session)
        assert session.context_window_json is not None
        assert "pending_confirmation" in session.context_window_json
        assert (
            session.context_window_json["pending_confirmation"]["action"]
            == "delete_session"
        )

    def test_delete_session_second_turn_executes_soft_delete(
        self, db_session, test_tenant, test_user
    ):
        """Second turn (pending_confirmation set) soft-deletes the target session."""
        from app.models.ai import ConversationSession
        from services.voice_action_router import delete_session_via_voice

        target = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
            title="Target Session",
            is_active=True,
        )
        db_session.add(target)
        db_session.flush()

        # Current session (with pending_confirmation set from first turn)
        current_session = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
            context_window_json={
                "pending_confirmation": {
                    "action": "delete_session",
                    "target_session_id": str(target.id),
                    "target_session_title": "Target Session",
                }
            },
        )
        db_session.add(current_session)
        db_session.flush()

        mock_user = make_mock_user(tenant_id=test_tenant.id)
        mock_user.id = test_user.id

        result = run(
            delete_session_via_voice(
                entities={},
                current_user=mock_user,
                db=db_session,
                session=current_session,
            )
        )

        assert result["success"] is True
        assert result["action"] == "delete_session"
        assert result.get("requires_confirmation") is None
        # Verify soft delete
        db_session.refresh(target)
        assert target.is_active is False
        # Verify pending_confirmation cleared
        db_session.refresh(current_session)
        ctx = current_session.context_window_json or {}
        assert "pending_confirmation" not in ctx

    def test_delete_session_disambiguation_for_missing_number(
        self, db_session, test_tenant, test_user
    ):
        """delete_session returns disambiguation when session_number 9999 not found."""
        from app.models.ai import ConversationSession
        from services.voice_action_router import delete_session_via_voice

        session = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
        )
        db_session.add(session)
        db_session.flush()

        mock_user = make_mock_user(tenant_id=test_tenant.id)
        mock_user.id = test_user.id

        result = run(
            delete_session_via_voice(
                entities={"session_number": 9999},
                current_user=mock_user,
                db=db_session,
                session=session,
            )
        )

        assert result.get("requires_disambiguation") is True


# ─────────────────────────────────────────────────────────────────────────────
# A10 — open_session_via_voice
# ─────────────────────────────────────────────────────────────────────────────


class TestA10OpenSession:
    """Unit tests for open_session_via_voice."""

    def test_open_session_returns_navigate_to(self, db_session, test_tenant, test_user):
        """open_session returns navigate_to path for the target session."""
        from app.models.ai import ConversationSession
        from services.voice_action_router import open_session_via_voice
        from services.voice_session_service import get_sessions_with_numbers

        session = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
            title="Johnson Panel",
        )
        db_session.add(session)
        db_session.flush()

        # Get the session's actual number
        sessions, _, _ = get_sessions_with_numbers(
            db=db_session,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            limit=50,
        )
        target = next((s for s in sessions if s["session_id"] == str(session.id)), None)
        assert target is not None

        mock_user = make_mock_user(tenant_id=test_tenant.id)
        mock_user.id = test_user.id
        mock_session = make_mock_session()

        result = run(
            open_session_via_voice(
                entities={"session_number": target["session_number"]},
                current_user=mock_user,
                db=db_session,
                session=mock_session,
            )
        )

        assert result["success"] is True
        assert result["action"] == "open_session"
        assert "navigate_to" in result["data"]

    def test_open_session_no_session_number_returns_failure(
        self, db_session, test_tenant, test_user
    ):
        """open_session without session_number returns failure."""
        from services.voice_action_router import open_session_via_voice

        mock_user = make_mock_user(tenant_id=test_tenant.id)
        mock_user.id = test_user.id
        mock_session = make_mock_session()

        result = run(
            open_session_via_voice(
                entities={},
                current_user=mock_user,
                db=db_session,
                session=mock_session,
            )
        )

        assert result["success"] is False

    def test_open_session_disambiguation_missing_number(
        self, db_session, test_tenant, test_user
    ):
        """open_session returns disambiguation when session_number not found."""
        from services.voice_action_router import open_session_via_voice

        mock_user = make_mock_user(tenant_id=test_tenant.id)
        mock_user.id = test_user.id
        mock_session = make_mock_session()

        result = run(
            open_session_via_voice(
                entities={"session_number": 9999},
                current_user=mock_user,
                db=db_session,
                session=mock_session,
            )
        )

        assert result.get("requires_disambiguation") is True


# ─────────────────────────────────────────────────────────────────────────────
# A10 — query_session_summary_via_voice
# ─────────────────────────────────────────────────────────────────────────────


class TestA10QuerySessionSummary:
    """Unit tests for query_session_summary_via_voice."""

    def test_query_summary_returns_current_session_title(
        self, db_session, test_tenant, test_user
    ):
        """query_session_summary returns the title of the current session."""
        from app.models.ai import ConversationSession
        from services.voice_action_router import query_session_summary_via_voice

        session = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
            title="Davis Wiring Job",
        )
        db_session.add(session)
        db_session.flush()

        mock_user = make_mock_user(tenant_id=test_tenant.id)
        mock_user.id = test_user.id

        result = run(
            query_session_summary_via_voice(
                entities={},
                current_user=mock_user,
                db=db_session,
                session=session,
            )
        )

        assert result["success"] is True
        assert result["action"] == "query_session_summary"
        assert result["data"]["title"] == "Davis Wiring Job"

    def test_query_summary_no_title_no_summary_graceful(
        self, db_session, test_tenant, test_user
    ):
        """query_session_summary returns graceful message when neither title nor summary."""
        from app.models.ai import ConversationSession
        from services.voice_action_router import query_session_summary_via_voice

        session = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
            title=None,
            context_summary=None,
        )
        db_session.add(session)
        db_session.flush()

        mock_user = make_mock_user(tenant_id=test_tenant.id)
        mock_user.id = test_user.id

        result = run(
            query_session_summary_via_voice(
                entities={},
                current_user=mock_user,
                db=db_session,
                session=session,
            )
        )

        assert result["success"] is True
        assert "doesn't have a title" in result["message"]
