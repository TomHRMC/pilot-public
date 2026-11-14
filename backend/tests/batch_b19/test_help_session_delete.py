"""
FIND-126: Help Chat Session Soft-Delete (anonymized_at)

Tests the DELETE /api/v1/help/sessions/{session_id} endpoint.
Implements soft-delete via anonymized_at = now() timestamp.
RBAC: help_chat.delete_own_history permission required.
Tenant isolation: user can only delete their own sessions.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.help import HelpChatMessage, HelpChatSession
from core.test_context import get_test_context


class TestHelpSessionDeleteOwnSession:
    """Tests for deleting user's own help chat session."""

    def test_delete_own_session_sets_anonymized_at(
        self, client: TestClient, db_session: Session
    ):
        """DELETE own session sets anonymized_at timestamp."""
        ctx = get_test_context()

        # Create a session
        now_utc = datetime.now(UTC)
        session = HelpChatSession(
            tenant_id=ctx.tenant_id,
            user_id=ctx.id,
            started_at=now_utc,
            last_activity_at=now_utc,
            title="Test Session",
            message_count=0,
            created_at=now_utc,
            updated_at=now_utc,
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        session_id = session.id

        # DELETE the session via test endpoint
        response = client.delete(f"/api/v1/help/sessions/{session_id}/test")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Session deleted"
        assert UUID(data["session_id"]) == session_id

        # Verify session in DB has anonymized_at set
        updated_session = db_session.exec(
            select(HelpChatSession).where(HelpChatSession.id == session_id)
        ).first()

        assert updated_session is not None
        assert updated_session.anonymized_at is not None

    def test_delete_own_session_removes_from_list(
        self, client: TestClient, db_session: Session
    ):
        """DELETE own session removes it from GET /sessions list."""
        ctx = get_test_context()
        now_utc = datetime.now(UTC)

        # Create session
        session = HelpChatSession(
            tenant_id=ctx.tenant_id,
            user_id=ctx.id,
            started_at=now_utc,
            last_activity_at=now_utc,
            title="To Delete",
            message_count=1,
            created_at=now_utc,
            updated_at=now_utc,
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        session_id = session.id

        # Verify it appears in list before deletion
        response = client.get("/api/v1/help/sessions/test")
        assert response.status_code == 200
        sessions_before = response.json()["sessions"]
        # Schema maps 'id' to 'session_id' via alias
        assert any(
            UUID(s.get("session_id") or s.get("id")) == session_id
            for s in sessions_before
        )

        # Delete the session
        response = client.delete(f"/api/v1/help/sessions/{session_id}/test")
        assert response.status_code == 200

        # Verify it no longer appears in list after deletion
        response = client.get("/api/v1/help/sessions/test")
        assert response.status_code == 200
        sessions_after = response.json()["sessions"]
        assert not any(
            UUID(s.get("session_id") or s.get("id")) == session_id
            for s in sessions_after
        )

    def test_delete_session_persists_messages(
        self, client: TestClient, db_session: Session
    ):
        """DELETE session does not delete HelpChatMessage rows (audit trail)."""
        ctx = get_test_context()
        now_utc = datetime.now(UTC)

        # Create session with messages
        session = HelpChatSession(
            tenant_id=ctx.tenant_id,
            user_id=ctx.id,
            started_at=now_utc,
            last_activity_at=now_utc,
            title="With Messages",
            message_count=2,
            created_at=now_utc,
            updated_at=now_utc,
        )
        db_session.add(session)
        db_session.flush()

        msg = HelpChatMessage(
            session_id=session.id,
            tenant_id=ctx.tenant_id,
            role="user",
            content="Test question",
            voice_used=False,
            created_at=now_utc,
        )
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(session)

        session_id = session.id
        message_count_before = db_session.exec(
            select(HelpChatMessage).where(HelpChatMessage.session_id == session_id)
        ).first()
        assert message_count_before is not None

        # Delete the session
        response = client.delete(f"/api/v1/help/sessions/{session_id}/test")
        assert response.status_code == 200

        # Messages still exist (audit trail preserved)
        message_after = db_session.exec(
            select(HelpChatMessage).where(HelpChatMessage.session_id == session_id)
        ).first()
        assert message_after is not None
        assert message_after.content == "Test question"


class TestHelpSessionDeleteTenantIsolation:
    """Tests for tenant isolation on DELETE endpoint."""

    def test_delete_another_user_session_in_same_tenant_returns_404(
        self, client: TestClient, db_session: Session
    ):
        """Cannot delete another user's session via hard FK isolation."""
        from app.models.core import User

        ctx = get_test_context()
        now_utc = datetime.now(UTC)

        # Create a different user in the same tenant
        other_user = User(
            tenant_id=ctx.tenant_id,
            email=f"other_user_{uuid4()}@test.example.com",
            hashed_password="dummy_hash",
            verified_email=True,
            created_at=now_utc,
            updated_at=now_utc,
        )
        db_session.add(other_user)
        db_session.flush()

        # Create session for the other user
        session = HelpChatSession(
            tenant_id=ctx.tenant_id,
            user_id=other_user.id,
            started_at=now_utc,
            last_activity_at=now_utc,
            title="Other User Session",
            message_count=0,
            created_at=now_utc,
            updated_at=now_utc,
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        session_id = session.id

        # Try to delete from current test user (ctx.id) — not owner
        response = client.delete(f"/api/v1/help/sessions/{session_id}/test")

        assert response.status_code == 404
        assert response.json()["detail"] == "Help chat session not found"

        # Session should NOT be deleted
        session_after = db_session.exec(
            select(HelpChatSession).where(HelpChatSession.id == session_id)
        ).first()
        assert session_after.anonymized_at is None


class TestHelpSessionDeleteUserIsolation:
    """Tests for user isolation on DELETE endpoint (within same tenant)."""

    def test_get_session_does_not_return_other_users_sessions(
        self, client: TestClient, db_session: Session
    ):
        """GET /sessions does not show other users' sessions (filter by user_id)."""
        from app.models.core import User

        ctx = get_test_context()
        now_utc = datetime.now(UTC)

        # Create a different user in the same tenant
        other_user = User(
            tenant_id=ctx.tenant_id,
            email=f"other_user_{uuid4()}@test.example.com",
            hashed_password="dummy_hash",
            verified_email=True,
            created_at=now_utc,
            updated_at=now_utc,
        )
        db_session.add(other_user)
        db_session.flush()

        # Create session for the other user
        session = HelpChatSession(
            tenant_id=ctx.tenant_id,
            user_id=other_user.id,
            started_at=now_utc,
            last_activity_at=now_utc,
            title="Hidden User Session",
            message_count=0,
            created_at=now_utc,
            updated_at=now_utc,
        )
        db_session.add(session)
        db_session.commit()

        # List sessions as current test user
        response = client.get("/api/v1/help/sessions/test")
        assert response.status_code == 200
        sessions = response.json()["sessions"]

        # Other user's session should not appear
        other_session_ids = [UUID(s.get("session_id") or s.get("id")) for s in sessions]
        assert session.id not in other_session_ids


class TestHelpSessionDeleteNotFound:
    """Tests for non-existent session deletion."""

    def test_delete_nonexistent_session_returns_404(
        self, client: TestClient, db_session: Session
    ):
        """Deleting non-existent session returns 404."""
        fake_session_id = uuid4()

        response = client.delete(f"/api/v1/help/sessions/{fake_session_id}/test")

        assert response.status_code == 404
        assert response.json()["detail"] == "Help chat session not found"


class TestHelpSessionDeleteIdempotency:
    """Tests for idempotent soft-delete behavior."""

    def test_redelete_already_deleted_session_returns_404(
        self, client: TestClient, db_session: Session
    ):
        """Re-deleting an already-deleted session returns 404 (idempotent)."""
        ctx = get_test_context()
        now_utc = datetime.now(UTC)

        # Create session
        session = HelpChatSession(
            tenant_id=ctx.tenant_id,
            user_id=ctx.id,
            started_at=now_utc,
            last_activity_at=now_utc,
            title="To Delete Twice",
            message_count=0,
            created_at=now_utc,
            updated_at=now_utc,
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        session_id = session.id

        # First deletion
        response = client.delete(f"/api/v1/help/sessions/{session_id}/test")
        assert response.status_code == 200

        # Verify session is now anonymized
        session_after_first = db_session.exec(
            select(HelpChatSession).where(HelpChatSession.id == session_id)
        ).first()
        assert session_after_first.anonymized_at is not None

        # Second deletion attempt
        response = client.delete(f"/api/v1/help/sessions/{session_id}/test")
        assert response.status_code == 404
        assert response.json()["detail"] == "Help chat session not found"
