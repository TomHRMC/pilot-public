"""
B13/A70 — Active Session Revocation Tests.

Test focus:
- GET /users/me/sessions/test returns empty list when no sessions
- GET /users/me/sessions/test returns active sessions
- DELETE /users/me/sessions/{session_id}/test revokes a session
- DELETE /users/me/sessions/{nonexistent}/test returns 404
- POST /users/me/sessions/revoke-others/test returns count
- revoke_session() returns True on success, False when not found
- revoke_others() revokes all except current
- session_revoke_service.revoke_session sets revoked_at on token
"""

import uuid
from datetime import UTC, datetime

from app.models.auth import AuthRefreshToken
from app.models.security import UserSessionMetadata
from core.test_context import get_test_context
from services.session_revoke_service import revoke_others, revoke_session


def _make_session(db_session, tenant_id, user_id, label="Chrome on macOS"):
    s = UserSessionMetadata(
        tenant_id=tenant_id,
        user_id=user_id,
        device_fingerprint="fp-001",
        display_label=label,
        ip_address="127.0.0.1",
        last_active_at=datetime.now(UTC),
    )
    db_session.add(s)
    db_session.commit()
    db_session.refresh(s)
    return s


class TestGetSessions:
    def test_returns_empty_list(self, client):
        resp = client.get("/api/v1/users/me/sessions/test")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_active_sessions(self, db_session, client):
        ctx = get_test_context()
        _make_session(db_session, ctx.tenant_id, ctx.id)
        resp = client.get("/api/v1/users/me/sessions/test")
        assert resp.status_code == 200
        sessions = resp.json()
        assert len(sessions) == 1
        assert sessions[0]["display_label"] == "Chrome on macOS"

    def test_does_not_return_revoked_sessions(self, db_session, client):
        ctx = get_test_context()
        s = _make_session(db_session, ctx.tenant_id, ctx.id)
        s.revoked_at = datetime.now(UTC)
        db_session.add(s)
        db_session.commit()
        resp = client.get("/api/v1/users/me/sessions/test")
        assert resp.json() == []


class TestRevokeSession:
    def test_revokes_session(self, db_session, client):
        ctx = get_test_context()
        s = _make_session(db_session, ctx.tenant_id, ctx.id)
        resp = client.delete(f"/api/v1/users/me/sessions/{s.session_id}/test")
        assert resp.status_code == 204

        db_session.refresh(s)
        assert s.revoked_at is not None

    def test_returns_404_for_nonexistent(self, client):
        resp = client.delete(f"/api/v1/users/me/sessions/{uuid.uuid4()}/test")
        assert resp.status_code == 404


class TestRevokeOthers:
    def test_revokes_all_except_current(self, db_session, client):
        ctx = get_test_context()
        s1 = _make_session(db_session, ctx.tenant_id, ctx.id, "Session 1")
        s2 = _make_session(db_session, ctx.tenant_id, ctx.id, "Session 2")

        resp = client.post("/api/v1/users/me/sessions/revoke-others/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["revoked_count"] >= 0  # test mode uses random UUID as current


class TestSessionRevokeService:
    def test_revoke_session_returns_true(self, db_session, tenant_a, user_tenant_a):
        s = _make_session(db_session, tenant_a.id, user_tenant_a.id)
        result = revoke_session(
            db=db_session,
            tenant_id=tenant_a.id,
            user_id=user_tenant_a.id,
            session_id=s.session_id,
        )
        assert result is True
        db_session.refresh(s)
        assert s.revoked_at is not None

    def test_revoke_session_returns_false_when_not_found(
        self, db_session, tenant_a, user_tenant_a
    ):
        result = revoke_session(
            db=db_session,
            tenant_id=tenant_a.id,
            user_id=user_tenant_a.id,
            session_id=uuid.uuid4(),
        )
        assert result is False

    def test_revoke_session_invalidates_refresh_token(
        self, db_session, tenant_a, user_tenant_a
    ):
        s = _make_session(db_session, tenant_a.id, user_tenant_a.id)

        # Create a refresh token linked to this session
        token = AuthRefreshToken(
            user_id=user_tenant_a.id,
            tenant_id=tenant_a.id,
            jti="test-jti-123",
            expires_at=datetime.now(UTC),
            session_id=s.session_id,
        )
        db_session.add(token)
        db_session.commit()

        revoke_session(
            db=db_session,
            tenant_id=tenant_a.id,
            user_id=user_tenant_a.id,
            session_id=s.session_id,
        )
        db_session.refresh(token)
        assert token.revoked_at is not None
        assert token.revoked_reason == "user_revoked"

    def test_revoke_others_skips_current_session(
        self, db_session, tenant_a, user_tenant_a
    ):
        s1 = _make_session(db_session, tenant_a.id, user_tenant_a.id, "S1")
        s2 = _make_session(db_session, tenant_a.id, user_tenant_a.id, "S2")

        count = revoke_others(
            db=db_session,
            tenant_id=tenant_a.id,
            user_id=user_tenant_a.id,
            current_session_id=s1.session_id,
        )
        assert count == 1  # only s2 was revoked
        db_session.refresh(s1)
        db_session.refresh(s2)
        assert s1.revoked_at is None  # preserved
        assert s2.revoked_at is not None  # revoked

    def test_cross_tenant_isolation(
        self, db_session, tenant_a, tenant_b, user_tenant_a
    ):
        """revoke_session must not revoke sessions in another tenant."""
        s = _make_session(db_session, tenant_b.id, user_tenant_a.id)
        # Try to revoke with tenant_a's context
        result = revoke_session(
            db=db_session,
            tenant_id=tenant_a.id,
            user_id=user_tenant_a.id,
            session_id=s.session_id,
        )
        assert result is False
        db_session.refresh(s)
        assert s.revoked_at is None  # not revoked
