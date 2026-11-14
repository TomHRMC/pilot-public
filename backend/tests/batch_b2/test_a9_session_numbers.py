"""
Batch B2 — A9 Test Coverage
============================

A9: Session Number Computation

Test Coverage:
- get_sessions_with_numbers returns correct structure (session_id, session_number, title, etc.)
- session_number is derived from ROW_NUMBER window function (not stored)
- Sessions are user-scoped and tenant-isolated
- resolve_session_by_number returns the correct session for a given number
- resolve_session_by_number returns None for missing session number
- GET /api/v1/voice/sessions/test returns paginated session list
- GET /api/v1/voice/sessions/test/{id}/messages returns message list
- Message list includes structured_content_json field
"""

import uuid

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# Unit tests — service layer (no HTTP)
# ─────────────────────────────────────────────────────────────────────────────


class TestA9SessionNumberService:
    """Unit tests for get_sessions_with_numbers and resolve_session_by_number."""

    def test_get_sessions_with_numbers_returns_list(
        self, db_session, test_tenant, test_user
    ):
        """Service returns a list of sessions with session_number field."""
        from app.models.ai import ConversationSession
        from services.voice_session_service import get_sessions_with_numbers

        # Create two sessions for the test user
        s1 = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
        )
        s2 = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
        )
        db_session.add(s1)
        db_session.add(s2)
        db_session.flush()

        sessions, _next_cursor, _has_more = get_sessions_with_numbers(
            db=db_session,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            limit=20,
        )

        assert isinstance(sessions, list)
        assert len(sessions) >= 2
        for s in sessions:
            assert "session_id" in s
            assert "session_number" in s
            assert isinstance(s["session_number"], int)
            assert s["session_number"] >= 1

    def test_session_numbers_are_unique_per_user(
        self, db_session, test_tenant, test_user
    ):
        """Each session returned has a unique session_number.

        SD-9 fix: seed data now includes conversation_session rows for
        test_user on test_tenant (same day). Delete them within the rollback
        transaction so the test's 3 new sessions get unique numbers without
        collision with seed sessions (Rule 16 - Test Resilience).
        """
        from sqlalchemy import text as _text

        from app.models.ai import ConversationSession
        from services.voice_session_service import get_sessions_with_numbers

        # Delete seeded voice AI rows for this user so the per-day
        # session_number derivation starts fresh. Child-first FK order:
        # feedback -> entity_link -> log -> message -> session
        delete_params = {"tid": str(test_tenant.id), "uid": str(test_user.id)}
        session_subquery = (
            "SELECT id FROM public.conversation_session "
            "WHERE tenant_id = :tid AND user_id = :uid"
        )
        db_session.execute(
            _text("DELETE FROM public.voice_feedback WHERE tenant_id = :tid"),
            {"tid": str(test_tenant.id)},
        )
        db_session.execute(
            _text(
                "DELETE FROM public.voice_command_entity_link WHERE tenant_id = :tid"
            ),
            {"tid": str(test_tenant.id)},
        )
        db_session.execute(
            _text(
                "DELETE FROM public.voice_command_log "
                "WHERE tenant_id = :tid AND user_id = :uid"
            ),
            delete_params,
        )
        db_session.execute(
            _text(
                f"DELETE FROM public.conversation_message WHERE session_id IN ({session_subquery})"
            ),
            delete_params,
        )
        db_session.execute(
            _text(
                "DELETE FROM public.conversation_session "
                "WHERE tenant_id = :tid AND user_id = :uid"
            ),
            delete_params,
        )
        db_session.flush()

        for _ in range(3):
            s = ConversationSession(
                tenant_id=test_tenant.id,
                user_id=test_user.id,
                status="active",
            )
            db_session.add(s)
        db_session.flush()

        sessions, _, _ = get_sessions_with_numbers(
            db=db_session,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            limit=20,
        )

        session_numbers = [s["session_number"] for s in sessions]
        assert len(session_numbers) == len(set(session_numbers)), (
            "Session numbers must be unique"
        )

    def test_resolve_session_by_number_found(self, db_session, test_tenant, test_user):
        """resolve_session_by_number returns the correct session."""
        from app.models.ai import ConversationSession
        from services.voice_session_service import (
            get_sessions_with_numbers,
            resolve_session_by_number,
        )

        s = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
        )
        db_session.add(s)
        db_session.flush()

        # Find what number was assigned
        sessions, _, _ = get_sessions_with_numbers(
            db=db_session,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            limit=50,
        )
        target = next((x for x in sessions if x["session_id"] == str(s.id)), None)
        assert target is not None

        resolved = resolve_session_by_number(
            db=db_session,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            session_number=target["session_number"],
        )
        assert resolved is not None
        assert resolved.id == s.id

    def test_resolve_session_by_number_not_found_returns_none(
        self, db_session, test_tenant, test_user
    ):
        """resolve_session_by_number returns None for a non-existent number."""
        from services.voice_session_service import resolve_session_by_number

        resolved = resolve_session_by_number(
            db=db_session,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            session_number=9999,
        )
        assert resolved is None

    def test_sessions_are_tenant_isolated(self, db_session, test_tenant, test_user):
        """Sessions from a different tenant are not returned."""
        from app.models.ai import ConversationSession
        from app.models.core import Tenant
        from services.voice_session_service import get_sessions_with_numbers

        # Create a different tenant
        other_tenant = Tenant(name=f"OtherTenantA9_{uuid.uuid4()}", is_active=True)
        db_session.add(other_tenant)
        db_session.flush()

        # Create a session for the other tenant (same user_id)
        other_session = ConversationSession(
            tenant_id=other_tenant.id,
            user_id=test_user.id,
            status="active",
        )
        db_session.add(other_session)
        db_session.flush()

        sessions, _, _ = get_sessions_with_numbers(
            db=db_session,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            limit=50,
        )

        session_ids = [s["session_id"] for s in sessions]
        assert str(other_session.id) not in session_ids

    def test_sessions_title_falls_back_to_context_summary(
        self, db_session, test_tenant, test_user
    ):
        """When title is None, title field falls back to context_summary."""
        from app.models.ai import ConversationSession
        from services.voice_session_service import get_sessions_with_numbers

        s = ConversationSession(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
            title=None,
            context_summary="Fallback summary",
        )
        db_session.add(s)
        db_session.flush()

        sessions, _, _ = get_sessions_with_numbers(
            db=db_session,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            limit=50,
        )

        target = next((x for x in sessions if x["session_id"] == str(s.id)), None)
        assert target is not None
        assert target["title"] == "Fallback summary"


# ─────────────────────────────────────────────────────────────────────────────
# HTTP endpoint tests
# ─────────────────────────────────────────────────────────────────────────────


class TestA9SessionListEndpoint:
    """HTTP tests for GET /api/v1/voice/sessions/test"""

    def test_session_list_returns_200(self, client, test_tenant, test_user):
        """GET /api/v1/voice/sessions/test returns 200."""
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("TEST_ENDPOINT_ENABLED", "true")
            mp.setenv("ENVIRONMENT", "dev")
            resp = client.get("/api/v1/voice/sessions/test")
        assert resp.status_code == 200

    def test_session_list_has_correct_shape(self, client, test_tenant, test_user):
        """Response has sessions list, next_cursor, has_more fields."""
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("TEST_ENDPOINT_ENABLED", "true")
            mp.setenv("ENVIRONMENT", "dev")
            resp = client.get("/api/v1/voice/sessions/test")
        assert resp.status_code == 200
        data = resp.json()
        assert "sessions" in data
        assert "has_more" in data
        assert isinstance(data["sessions"], list)

    def test_session_messages_endpoint_404_unknown_session(
        self, client, test_tenant, test_user
    ):
        """GET /api/v1/voice/sessions/test/{id}/messages returns 404 for unknown session."""
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("TEST_ENDPOINT_ENABLED", "true")
            mp.setenv("ENVIRONMENT", "dev")
            resp = client.get(f"/api/v1/voice/sessions/test/{uuid.uuid4()}/messages")
        assert resp.status_code == 404

    def test_session_messages_returns_structured_content_field(
        self, client, db_session, test_tenant, test_user
    ):
        """Messages response includes structured_content_json field."""
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
            content_text="Hello",
            created_by=test_user.id,
        )
        db_session.add(msg)
        db_session.flush()

        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("TEST_ENDPOINT_ENABLED", "true")
            mp.setenv("ENVIRONMENT", "dev")
            resp = client.get(f"/api/v1/voice/sessions/test/{session.id}/messages")

        assert resp.status_code == 200
        data = resp.json()
        assert "messages" in data
        assert len(data["messages"]) >= 1
        # Each message must have structured_content_json key (may be null)
        for m in data["messages"]:
            assert "structured_content_json" in m
