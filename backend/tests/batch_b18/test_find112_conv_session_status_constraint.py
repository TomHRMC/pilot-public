"""
FIND-112 (S2 High) — Add 'expired','archived' to conversation_session.status CHECK.

Test coverage:
  1. All 5 valid values accepted: active, ended, abandoned, expired, archived
  2. Invalid value rejected by CHECK constraint
  3. Previously valid values still valid (regression guard)
"""

import uuid
from datetime import UTC, datetime

import pytest


class TestFind112StatusConstraint:
    def _insert_session(self, db_session, tenant_id, user_id, status):
        from sqlalchemy import text

        now = datetime.now(UTC)
        db_session.exec(
            text(
                "INSERT INTO conversation_session "
                "(id, tenant_id, user_id, status, context_window_json, created_at, updated_at) "
                "VALUES (:id, :tid, :uid, :status, '{}', :now, :now)"
            ).bindparams(
                id=str(uuid.uuid4()),
                tid=str(tenant_id),
                uid=str(user_id),
                status=status,
                now=now,
            )
        )
        db_session.flush()
        db_session.rollback()

    @pytest.mark.parametrize(
        "status", ["active", "ended", "abandoned", "expired", "archived"]
    )
    def test_valid_status_accepted(self, db_session, test_tenant, test_user, status):
        """All 5 valid status values must be accepted by the CHECK constraint."""
        self._insert_session(db_session, test_tenant.id, test_user.id, status)

    @pytest.mark.parametrize("status", ["closed", "deleted", "paused", ""])
    def test_invalid_status_rejected(self, db_session, test_tenant, test_user, status):
        """Invalid status values must be rejected by the CHECK constraint."""
        from sqlalchemy import text

        now = datetime.now(UTC)
        with pytest.raises(Exception):  # IntegrityError or CheckViolation
            db_session.exec(
                text(
                    "INSERT INTO conversation_session "
                    "(id, tenant_id, user_id, status, context_window_json, created_at, updated_at) "
                    "VALUES (:id, :tid, :uid, :status, '{}', :now, :now)"
                ).bindparams(
                    id=str(uuid.uuid4()),
                    tid=str(test_tenant.id),
                    uid=str(test_user.id),
                    status=status,
                    now=now,
                )
            )
            db_session.flush()
        db_session.rollback()

    def test_check_constraint_definition_includes_new_statuses(self, db_session):
        """DB constraint must include 'expired' and 'archived'."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT pg_get_constraintdef(c.oid) "
                "FROM pg_constraint c "
                "JOIN pg_class t ON t.oid = c.conrelid "
                "WHERE t.relname = 'conversation_session' "
                "  AND c.conname = 'conv_session_status_chk'"
            )
        ).first()
        assert result is not None, "conv_session_status_chk must exist"
        defn = result[0]
        assert "expired" in defn, f"CHECK must include 'expired', got: {defn}"
        assert "archived" in defn, f"CHECK must include 'archived', got: {defn}"
