"""
FIND-127 (S4 Low) — Composite partial index on help_chat_session for session
history list endpoint performance.

Target query (_list_sessions_impl):
  SELECT * FROM help_chat_session
  WHERE user_id = ? AND tenant_id = ? AND anonymized_at IS NULL
  ORDER BY last_activity_at DESC LIMIT ? OFFSET ?

New index enables index-only scan for this query:
  ix_help_chat_session_user_tenant_activity
  ON help_chat_session (user_id, tenant_id, last_activity_at DESC)
  WHERE anonymized_at IS NULL

Migration: phase_fe_1_batch_b18_help_chat_session_activity_index (316581e91652)

Test coverage:
  1. DB: index ix_help_chat_session_user_tenant_activity exists
  2. DB: index has WHERE clause (anonymized_at IS NULL)
  3. DB: column order — user_id, tenant_id, last_activity_at in indexdef

Test subfolder: tests/batch_b18/
"""


class TestFind127ActivityIndexExists:
    """Composite partial index must exist on help_chat_session after FIND-127 migration."""

    def test_activity_index_exists(self, db_session):
        """ix_help_chat_session_user_tenant_activity must exist in pg_indexes."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename = 'help_chat_session' "
                "  AND indexname = 'ix_help_chat_session_user_tenant_activity'"
            )
        ).first()

        assert result is not None, (
            "Index 'ix_help_chat_session_user_tenant_activity' missing from help_chat_session — "
            "FIND-127 migration not applied"
        )


class TestFind127ActivityIndexWhereClause:
    """Index must have WHERE anonymized_at IS NULL partial condition."""

    def test_index_has_where_anonymized_at_is_null(self, db_session):
        """Index WHERE clause must filter anonymized_at IS NULL."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE tablename = 'help_chat_session' "
                "  AND indexname = 'ix_help_chat_session_user_tenant_activity'"
            )
        ).first()

        assert result is not None, (
            "ix_help_chat_session_user_tenant_activity index definition not found"
        )
        index_def = result[0].lower()
        assert "anonymized_at is null" in index_def, (
            f"Index must have WHERE (anonymized_at IS NULL) partial condition, "
            f"got definition: {index_def}"
        )


class TestFind127ActivityIndexColumnOrder:
    """Index columns must be (user_id, tenant_id, last_activity_at) — order matters for query performance."""

    def test_index_column_order_user_tenant_activity(self, db_session):
        """user_id must appear before tenant_id, which must appear before last_activity_at."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE tablename = 'help_chat_session' "
                "  AND indexname = 'ix_help_chat_session_user_tenant_activity'"
            )
        ).first()

        assert result is not None, (
            "ix_help_chat_session_user_tenant_activity index definition not found"
        )
        index_def = result[0].lower()

        # All three columns must be present
        assert "user_id" in index_def, f"user_id not in index definition: {index_def}"
        assert "tenant_id" in index_def, (
            f"tenant_id not in index definition: {index_def}"
        )
        assert "last_activity_at" in index_def, (
            f"last_activity_at not in index definition: {index_def}"
        )

        # Column order: user_id first, then tenant_id, then last_activity_at
        assert index_def.index("user_id") < index_def.index("tenant_id"), (
            f"user_id must appear before tenant_id in index, got: {index_def}"
        )
        assert index_def.index("tenant_id") < index_def.index("last_activity_at"), (
            f"tenant_id must appear before last_activity_at in index, got: {index_def}"
        )
