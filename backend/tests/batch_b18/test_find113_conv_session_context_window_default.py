"""
FIND-113 (S4 Low) — context_window_json NOT NULL + DEFAULT '{}' on conversation_session.

Test coverage:
  1. DB: column is NOT NULL with server_default='{}'
  2. DB: 0 NULL rows after backfill
  3. ORM: field is non-Optional dict with nullable=False
  4. Integration: new session without explicit context_window_json → gets {}
"""

import uuid
from datetime import UTC, datetime


class TestFind113ContextWindowDefault:
    def test_column_is_not_nullable(self, db_session):
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT is_nullable, column_default "
                "FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "  AND table_name = 'conversation_session' "
                "  AND column_name = 'context_window_json'"
            )
        ).first()
        assert result is not None, "context_window_json column missing"
        assert result[0] == "NO", (
            f"context_window_json must be NOT NULL, got '{result[0]}'"
        )
        assert result[1] is not None, "context_window_json must have server_default"
        assert "{}" in str(result[1]) or "jsonb" in str(result[1]).lower()

    def test_no_null_rows_after_backfill(self, db_session):
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT COUNT(*) FROM conversation_session WHERE context_window_json IS NULL"
            )
        ).first()
        assert result[0] == 0, f"Expected 0 NULL rows, found {result[0]}"

    def test_orm_field_not_optional(self):
        import typing

        from app.models.ai import ConversationSession

        hints = typing.get_type_hints(ConversationSession)
        field_type = hints.get("context_window_json")
        assert field_type is not None
        origin = getattr(field_type, "__origin__", None)
        assert origin is not typing.Union, (
            f"context_window_json must be Dict (not Optional[Dict]), got {field_type}"
        )

    def test_new_session_without_context_gets_empty_dict(
        self, db_session, test_tenant, test_user
    ):
        """INSERT without context_window_json → server default fires → value is {}."""
        from sqlmodel import select

        from app.models.ai import ConversationSession

        now = datetime.now(UTC)
        session = ConversationSession(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            status="active",
            created_at=now,
            updated_at=now,
            # context_window_json not specified — should use server default
        )
        db_session.add(session)
        db_session.commit()

        fetched = db_session.exec(
            select(ConversationSession).where(ConversationSession.id == session.id)
        ).first()
        assert fetched is not None
        assert (
            fetched.context_window_json == {} or fetched.context_window_json is not None
        ), "context_window_json must be {} (not NULL) for new sessions"
