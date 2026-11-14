"""
B13/A72 — Session History Tests.

Test focus:
- upsert_session_history creates row on first login
- upsert_session_history increments count on subsequent logins
- GET /users/me/session-history/test returns 404 when no row exists
- GET /users/me/session-history/test returns correct data after upsert
- tenant isolation: cannot see another tenant's history

All tests that hit the test endpoint use TEST_TENANT_ID/TEST_USER_ID (from get_test_context()),
not tenant_a/user_tenant_a fixtures (those are separate test tenants).
"""

from datetime import UTC, datetime

from api.routes.account_security import _upsert_session_history
from app.models.security import UserSessionHistory
from core.test_context import get_test_context


class TestUpsertSessionHistory:
    def test_creates_row_on_first_login(self, db_session, tenant_a, user_tenant_a):
        row = _upsert_session_history(
            db=db_session,
            tenant_id=tenant_a.id,
            user_id=user_tenant_a.id,
        )
        assert row.tenant_id == tenant_a.id
        assert row.user_id == user_tenant_a.id
        assert row.total_session_count == 1
        assert row.first_login_at is not None
        assert row.last_login_at is not None
        assert row.first_login_at == row.last_login_at

    def test_increments_count_on_second_login(
        self, db_session, tenant_a, user_tenant_a
    ):
        _upsert_session_history(db_session, tenant_a.id, user_tenant_a.id)
        row2 = _upsert_session_history(db_session, tenant_a.id, user_tenant_a.id)
        assert row2.total_session_count == 2

    def test_first_login_at_unchanged_on_update(
        self, db_session, tenant_a, user_tenant_a
    ):
        row1 = _upsert_session_history(db_session, tenant_a.id, user_tenant_a.id)
        first_ts = row1.first_login_at
        row2 = _upsert_session_history(db_session, tenant_a.id, user_tenant_a.id)
        assert row2.first_login_at == first_ts

    def test_last_login_at_updated(self, db_session, tenant_a, user_tenant_a):
        row1 = _upsert_session_history(db_session, tenant_a.id, user_tenant_a.id)
        first_last = row1.last_login_at
        row2 = _upsert_session_history(db_session, tenant_a.id, user_tenant_a.id)
        assert row2.last_login_at >= first_last


class TestGetSessionHistoryEndpoint:
    def test_returns_404_when_no_row(self, client):
        resp = client.get("/api/v1/users/me/session-history/test")
        assert resp.status_code == 404

    def test_returns_data_after_upsert(self, db_session, client):
        # Must use TEST_TENANT_ID / TEST_USER_ID — same IDs the test endpoint resolves
        ctx = get_test_context()
        _upsert_session_history(db_session, ctx.tenant_id, ctx.id)
        _upsert_session_history(db_session, ctx.tenant_id, ctx.id)
        resp = client.get("/api/v1/users/me/session-history/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_session_count"] == 2
        assert "first_login_at" in data
        assert "last_login_at" in data

    def test_tenant_isolation(self, db_session, client, tenant_b, user_tenant_a):
        """Session history seeded for tenant_b should not appear for test user (TEST_TENANT_ID)."""
        row = UserSessionHistory(
            tenant_id=tenant_b.id,
            user_id=user_tenant_a.id,
            first_login_at=datetime.now(UTC),
            total_session_count=5,
            last_login_at=datetime.now(UTC),
        )
        db_session.add(row)
        db_session.commit()

        # Test endpoint uses TEST_TENANT_ID — no row for that tenant was seeded
        resp = client.get("/api/v1/users/me/session-history/test")
        assert resp.status_code == 404
