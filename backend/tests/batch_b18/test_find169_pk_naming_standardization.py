"""
FIND-169 (S2 High) — PK naming standardization: 6 tables

UUID PKs renamed to 'id':
  help_chat_session.session_id       → id
  mobile_sync_session.session_id     → id
  in_app_notification.notification_id → id

String PKs renamed to 'code' (lookup table convention):
  help_article.article_id            → code
  notification_category.category_id  → code
  notification_category_sub_trigger.sub_trigger_id → code

communication_template already had id — no change.

Test subfolder: tests/batch_b18/
"""

import uuid
from datetime import UTC, datetime


# ─────────────────────────────────────────────────────────────────────────────
# Live DB verification — PKs renamed correctly
# ─────────────────────────────────────────────────────────────────────────────
class TestFind169PKColumnNamesInDB:
    """Verify live DB has the new PK column names after migration."""

    def test_help_chat_session_pk_is_id(self, db_session):
        """help_chat_session PK column must be named 'id'."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name='help_chat_session' "
                "AND column_name='id'"
            )
        ).first()
        assert result is not None, "help_chat_session must have a column named 'id'"

    def test_help_chat_session_has_no_session_id_pk(self, db_session):
        """help_chat_session must NOT have a column named 'session_id' as PK."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT c.column_name FROM information_schema.columns c "
                "JOIN information_schema.table_constraints tc ON tc.table_name = c.table_name "
                "JOIN information_schema.key_column_usage kcu ON "
                "  kcu.constraint_name = tc.constraint_name AND kcu.column_name = c.column_name "
                "WHERE tc.constraint_type = 'PRIMARY KEY' "
                "  AND c.table_schema = 'public' "
                "  AND c.table_name = 'help_chat_session' "
                "  AND c.column_name = 'session_id'"
            )
        ).first()
        assert result is None, (
            "help_chat_session PK must not be 'session_id' — should be 'id'"
        )

    def test_mobile_sync_session_pk_is_id(self, db_session):
        """mobile_sync_session PK column must be named 'id'."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT kcu.column_name FROM information_schema.table_constraints tc "
                "JOIN information_schema.key_column_usage kcu "
                "  ON tc.constraint_name = kcu.constraint_name "
                "WHERE tc.constraint_type = 'PRIMARY KEY' "
                "  AND tc.table_schema = 'public' "
                "  AND tc.table_name = 'mobile_sync_session' "
                "  AND kcu.column_name = 'id'"
            )
        ).first()
        assert result is not None, "mobile_sync_session PK must be 'id'"

    def test_in_app_notification_pk_is_id(self, db_session):
        """in_app_notification PK column must be named 'id'."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT kcu.column_name FROM information_schema.table_constraints tc "
                "JOIN information_schema.key_column_usage kcu "
                "  ON tc.constraint_name = kcu.constraint_name "
                "WHERE tc.constraint_type = 'PRIMARY KEY' "
                "  AND tc.table_schema = 'public' "
                "  AND tc.table_name = 'in_app_notification' "
                "  AND kcu.column_name = 'id'"
            )
        ).first()
        assert result is not None, "in_app_notification PK must be 'id'"

    def test_help_article_pk_is_code(self, db_session):
        """help_article PK column must be named 'code'."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT kcu.column_name FROM information_schema.table_constraints tc "
                "JOIN information_schema.key_column_usage kcu "
                "  ON tc.constraint_name = kcu.constraint_name "
                "WHERE tc.constraint_type = 'PRIMARY KEY' "
                "  AND tc.table_schema = 'public' "
                "  AND tc.table_name = 'help_article' "
                "  AND kcu.column_name = 'code'"
            )
        ).first()
        assert result is not None, "help_article PK must be 'code'"

    def test_notification_category_pk_is_code(self, db_session):
        """notification_category PK column must be named 'code'."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT kcu.column_name FROM information_schema.table_constraints tc "
                "JOIN information_schema.key_column_usage kcu "
                "  ON tc.constraint_name = kcu.constraint_name "
                "WHERE tc.constraint_type = 'PRIMARY KEY' "
                "  AND tc.table_schema = 'public' "
                "  AND tc.table_name = 'notification_category' "
                "  AND kcu.column_name = 'code'"
            )
        ).first()
        assert result is not None, "notification_category PK must be 'code'"

    def test_notification_category_sub_trigger_pk_is_code(self, db_session):
        """notification_category_sub_trigger PK column must be named 'code'."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT kcu.column_name FROM information_schema.table_constraints tc "
                "JOIN information_schema.key_column_usage kcu "
                "  ON tc.constraint_name = kcu.constraint_name "
                "WHERE tc.constraint_type = 'PRIMARY KEY' "
                "  AND tc.table_schema = 'public' "
                "  AND tc.table_name = 'notification_category_sub_trigger' "
                "  AND kcu.column_name = 'code'"
            )
        ).first()
        assert result is not None, "notification_category_sub_trigger PK must be 'code'"

    def test_communication_template_still_has_id(self, db_session):
        """communication_template already had 'id' — must remain unchanged."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT kcu.column_name FROM information_schema.table_constraints tc "
                "JOIN information_schema.key_column_usage kcu "
                "  ON tc.constraint_name = kcu.constraint_name "
                "WHERE tc.constraint_type = 'PRIMARY KEY' "
                "  AND tc.table_schema = 'public' "
                "  AND tc.table_name = 'communication_template' "
                "  AND kcu.column_name = 'id'"
            )
        ).first()
        assert result is not None, "communication_template PK 'id' must remain"


# ─────────────────────────────────────────────────────────────────────────────
# ORM model field names match new PK names
# ─────────────────────────────────────────────────────────────────────────────
class TestFind169ORMFieldNames:
    """ORM model classes must use the new field names."""

    def test_help_chat_session_model_uses_id(self):
        from app.models.help import HelpChatSession

        assert hasattr(HelpChatSession, "id"), "HelpChatSession must have field 'id'"
        assert not hasattr(HelpChatSession, "session_id"), (
            "HelpChatSession must not have field 'session_id' — renamed to 'id'"
        )

    def test_mobile_sync_session_model_uses_id(self):
        from app.models.sync import MobileSyncSession

        assert hasattr(MobileSyncSession, "id"), (
            "MobileSyncSession must have field 'id'"
        )
        assert not hasattr(MobileSyncSession, "session_id"), (
            "MobileSyncSession must not have field 'session_id' — renamed to 'id'"
        )

    def test_in_app_notification_model_uses_id(self):
        from app.models.system import InAppNotification

        assert hasattr(InAppNotification, "id"), (
            "InAppNotification must have field 'id'"
        )
        assert not hasattr(InAppNotification, "notification_id"), (
            "InAppNotification must not have field 'notification_id' — renamed to 'id'"
        )

    def test_help_article_model_uses_code(self):
        from app.models.help import HelpArticle

        assert hasattr(HelpArticle, "code"), "HelpArticle must have field 'code'"
        assert not hasattr(HelpArticle, "article_id"), (
            "HelpArticle must not have field 'article_id' — renamed to 'code'"
        )

    def test_notification_category_model_uses_code(self):
        from app.models.system import NotificationCategory

        assert hasattr(NotificationCategory, "code"), (
            "NotificationCategory must have field 'code'"
        )
        assert not hasattr(NotificationCategory, "category_id"), (
            "NotificationCategory must not have field 'category_id' — renamed to 'code'"
        )

    def test_notification_category_sub_trigger_model_uses_code(self):
        from app.models.system import NotificationCategorySubTrigger

        assert hasattr(NotificationCategorySubTrigger, "code"), (
            "NotificationCategorySubTrigger must have field 'code'"
        )
        assert not hasattr(NotificationCategorySubTrigger, "sub_trigger_id"), (
            "NotificationCategorySubTrigger must not have field 'sub_trigger_id' — renamed to 'code'"
        )


# ─────────────────────────────────────────────────────────────────────────────
# FK child columns still work (pointing to new PK names)
# ─────────────────────────────────────────────────────────────────────────────
class TestFind169FKChildColumnsIntact:
    """FK child columns keep their names but reference the new PK column names."""

    def test_help_chat_message_session_fk_intact(self, db_session):
        """help_chat_message.session_id FK must reference help_chat_session.id."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT ccu.column_name AS parent_col "
                "FROM pg_constraint c "
                "JOIN pg_class t ON t.oid = c.conrelid "
                "JOIN information_schema.constraint_column_usage ccu "
                "  ON ccu.constraint_name = c.conname "
                "WHERE c.contype = 'f' "
                "  AND t.relname = 'help_chat_message' "
                "  AND c.conname = 'fk_help_chat_message_session_id'"
            )
        ).first()
        assert result is not None, "FK fk_help_chat_message_session_id must exist"
        assert result[0] == "id", f"FK must reference 'id', got '{result[0]}'"

    def test_help_article_chunk_article_fk_intact(self, db_session):
        """help_article_chunk.article_id FK must reference help_article.code."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT ccu.column_name AS parent_col "
                "FROM pg_constraint c "
                "JOIN pg_class t ON t.oid = c.conrelid "
                "JOIN information_schema.constraint_column_usage ccu "
                "  ON ccu.constraint_name = c.conname "
                "WHERE c.contype = 'f' "
                "  AND t.relname = 'help_article_chunk' "
                "  AND c.conname = 'fk_help_article_chunk_article_id'"
            )
        ).first()
        assert result is not None, "FK fk_help_article_chunk_article_id must exist"
        assert result[0] == "code", f"FK must reference 'code', got '{result[0]}'"

    def test_notification_outbox_sub_trigger_fk_intact(self, db_session):
        """notification_outbox.sub_trigger_id FK must reference notification_category_sub_trigger.code."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT ccu.column_name AS parent_col "
                "FROM pg_constraint c "
                "JOIN pg_class t ON t.oid = c.conrelid "
                "JOIN information_schema.constraint_column_usage ccu "
                "  ON ccu.constraint_name = c.conname "
                "WHERE c.contype = 'f' "
                "  AND t.relname = 'notification_outbox' "
                "  AND c.conname = 'fk_notif_outbox_sub_trigger'"
            )
        ).first()
        assert result is not None, "FK fk_notif_outbox_sub_trigger must exist"
        assert result[0] == "code", f"FK must reference 'code', got '{result[0]}'"


# ─────────────────────────────────────────────────────────────────────────────
# Functional: can create and retrieve rows via new PK names
# ─────────────────────────────────────────────────────────────────────────────
class TestFind169FunctionalInsert:
    """Basic insert+retrieve using new PK field names."""

    def test_help_article_insert_and_retrieve(self, db_session):
        """HelpArticle can be created using 'code' field and retrieved by it."""
        from datetime import date

        from app.models.help import HelpArticle

        now = datetime.now(UTC)
        slug = f"test-article-{uuid.uuid4().hex[:8]}"
        article = HelpArticle(
            code=slug,
            s3_path=f"s3://pilot-help-content/test/{slug}.md",
            title="Test Article",
            category="integrations",
            last_content_hash="abc123",
            last_processed_at=now,
            last_updated=date.today(),
            created_at=now,
        )
        db_session.add(article)
        db_session.commit()
        db_session.refresh(article)

        assert article.code == slug

    def test_notification_category_rows_accessible_by_code(self, db_session):
        """Seeded notification_category rows accessible via .code attribute."""
        from sqlmodel import select

        from app.models.system import NotificationCategory

        rows = db_session.exec(select(NotificationCategory)).all()
        assert len(rows) >= 1
        # All rows should have code attribute (not category_id)
        for row in rows:
            assert isinstance(row.code, str)
            assert len(row.code) > 0
