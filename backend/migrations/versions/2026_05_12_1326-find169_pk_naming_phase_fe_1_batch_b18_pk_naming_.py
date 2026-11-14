"""phase_fe_1_batch_b18_pk_naming_standardization

FIND-169: Rename non-standard PK column names to id/code on 6 tables.
Design rule: every UUID/BigInt PK must be named 'id'; string PKs on lookup
tables must be named 'code'.

Tables renamed:
  UUID → id:
    help_chat_session.session_id       → id
    mobile_sync_session.session_id     → id
    in_app_notification.notification_id → id
  String → code:
    help_article.article_id            → code
    notification_category.category_id  → code
    notification_category_sub_trigger.sub_trigger_id → code

communication_template already has id (no change needed).

FK child columns (e.g. help_chat_message.session_id) KEEP their current names —
they are FK columns, not PKs. Only the parent PK column is renamed.
The FK constraints are dropped, parent PK renamed, then FK constraints
recreated pointing to the new parent PK column name.

Revision ID: find169_pk_naming
Revises: a7c3e5f91b02
Create Date: 2026-05-12 13:26:04.000000

"""

from alembic import op

revision = "find169_pk_naming"
down_revision = "a7c3e5f91b02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ──────────────────────────────────────────────────────────────────────────
    # 1. help_chat_session.session_id → id
    #    FK children: help_chat_message.session_id (CASCADE)
    #                 feedback_submission.from_help_chat_session_id (SET NULL)
    # ──────────────────────────────────────────────────────────────────────────
    # Drop child FK constraints first
    op.drop_constraint(
        "fk_help_chat_message_session_id", "help_chat_message", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_feedback_submission_session_id", "feedback_submission", type_="foreignkey"
    )
    # Drop PK constraint
    op.drop_constraint("pk_help_chat_session", "help_chat_session", type_="primary")
    # Rename PK column
    op.alter_column("help_chat_session", "session_id", new_column_name="id")
    # Recreate PK
    op.create_primary_key("pk_help_chat_session", "help_chat_session", ["id"])
    # Recreate child FK constraints (child FK columns keep their original names)
    op.create_foreign_key(
        "fk_help_chat_message_session_id",
        "help_chat_message",
        "help_chat_session",
        ["session_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_feedback_submission_session_id",
        "feedback_submission",
        "help_chat_session",
        ["from_help_chat_session_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ──────────────────────────────────────────────────────────────────────────
    # 2. mobile_sync_session.session_id → id
    #    FK children: none found
    # ──────────────────────────────────────────────────────────────────────────
    op.drop_constraint(
        "mobile_sync_session_pkey", "mobile_sync_session", type_="primary"
    )
    op.alter_column("mobile_sync_session", "session_id", new_column_name="id")
    op.create_primary_key("mobile_sync_session_pkey", "mobile_sync_session", ["id"])

    # ──────────────────────────────────────────────────────────────────────────
    # 3. in_app_notification.notification_id → id
    #    FK children: none on this column
    # ──────────────────────────────────────────────────────────────────────────
    op.drop_constraint("pk_in_app_notification", "in_app_notification", type_="primary")
    op.alter_column("in_app_notification", "notification_id", new_column_name="id")
    op.create_primary_key("pk_in_app_notification", "in_app_notification", ["id"])

    # ──────────────────────────────────────────────────────────────────────────
    # 4. help_article.article_id → code
    #    FK children: help_article_chunk.article_id (CASCADE)
    # ──────────────────────────────────────────────────────────────────────────
    op.drop_constraint(
        "fk_help_article_chunk_article_id", "help_article_chunk", type_="foreignkey"
    )
    op.drop_constraint("pk_help_article", "help_article", type_="primary")
    op.alter_column("help_article", "article_id", new_column_name="code")
    op.create_primary_key("pk_help_article", "help_article", ["code"])
    # Recreate FK: child column article_id now references help_article.code
    op.create_foreign_key(
        "fk_help_article_chunk_article_id",
        "help_article_chunk",
        "help_article",
        ["article_id"],
        ["code"],
        ondelete="CASCADE",
    )

    # ──────────────────────────────────────────────────────────────────────────
    # 5. notification_category.category_id → code
    #    FK children (all keep their category_id child column name):
    #      notification_category_sub_trigger.category_id (RESTRICT)
    #      notification_default_policy.category_id (RESTRICT)
    #      notification_preference.category_id (RESTRICT)
    #      in_app_notification.category_id (RESTRICT)
    #      notification_outbox.category_id (no rule = NO ACTION)
    # ──────────────────────────────────────────────────────────────────────────
    op.drop_constraint(
        "fk_notif_sub_trigger_category",
        "notification_category_sub_trigger",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_notif_default_policy_category",
        "notification_default_policy",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_notif_pref_category", "notification_preference", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_in_app_notif_category", "in_app_notification", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_notif_outbox_category", "notification_outbox", type_="foreignkey"
    )
    op.drop_constraint(
        "pk_notification_category", "notification_category", type_="primary"
    )
    op.alter_column("notification_category", "category_id", new_column_name="code")
    op.create_primary_key("pk_notification_category", "notification_category", ["code"])
    # Recreate all child FK constraints pointing to notification_category.code
    op.create_foreign_key(
        "fk_notif_sub_trigger_category",
        "notification_category_sub_trigger",
        "notification_category",
        ["category_id"],
        ["code"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_notif_default_policy_category",
        "notification_default_policy",
        "notification_category",
        ["category_id"],
        ["code"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_notif_pref_category",
        "notification_preference",
        "notification_category",
        ["category_id"],
        ["code"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_in_app_notif_category",
        "in_app_notification",
        "notification_category",
        ["category_id"],
        ["code"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_notif_outbox_category",
        "notification_outbox",
        "notification_category",
        ["category_id"],
        ["code"],
    )

    # ──────────────────────────────────────────────────────────────────────────
    # 6. notification_category_sub_trigger.sub_trigger_id → code
    #    FK children: notification_outbox.sub_trigger_id (fk_notif_outbox_sub_trigger)
    # ──────────────────────────────────────────────────────────────────────────
    op.drop_constraint(
        "fk_notif_outbox_sub_trigger", "notification_outbox", type_="foreignkey"
    )
    op.drop_constraint(
        "pk_notif_sub_trigger", "notification_category_sub_trigger", type_="primary"
    )
    op.alter_column(
        "notification_category_sub_trigger", "sub_trigger_id", new_column_name="code"
    )
    op.create_primary_key(
        "pk_notif_sub_trigger", "notification_category_sub_trigger", ["code"]
    )
    op.create_foreign_key(
        "fk_notif_outbox_sub_trigger",
        "notification_outbox",
        "notification_category_sub_trigger",
        ["sub_trigger_id"],
        ["code"],
    )

    # ──────────────────────────────────────────────────────────────────────────
    # 7. Update audit.log_changes() trigger: simplify fallback chain now that
    #    help_article.article_id → code and help_chat_session.session_id → id.
    #    The B16 fallback for article_id/session_id is no longer needed since
    #    both are now 'code' and 'id' respectively (covered by primary branches).
    #    Keeps full correct column names per audit.event schema.
    # ──────────────────────────────────────────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION audit.log_changes()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        SECURITY DEFINER
        AS $$
        DECLARE
            v_user_id    uuid;
            v_actor_type text;
            v_tenant_id  uuid;
            v_entity_id  text;
        BEGIN
            v_user_id := COALESCE(
                NULLIF(current_setting('app.user_id', true), '')::uuid,
                '00000000-0000-0000-0000-000000000000'::uuid
            );

            IF v_user_id = '00000000-0000-0000-0000-000000000000'::uuid THEN
                v_actor_type := 'system';
            ELSE
                v_actor_type := 'user';
            END IF;

            BEGIN
                v_tenant_id := COALESCE(NEW.tenant_id, OLD.tenant_id);
            EXCEPTION
                WHEN undefined_column THEN v_tenant_id := NULL;
            END;

            -- FIND-169: simplified fallback chain.
            -- UUID PKs are now 'id'; string PKs on lookup tables are 'code'.
            -- Removed article_id/session_id fallbacks (both renamed by FIND-169).
            -- Kept message_id/chunk_id/corpus_id/submission_id for other tables.
            BEGIN
                v_entity_id := COALESCE(NEW.id, OLD.id)::text;
            EXCEPTION WHEN undefined_column THEN
                BEGIN
                    v_entity_id := COALESCE(NEW.code, OLD.code)::text;
                EXCEPTION WHEN undefined_column THEN
                    BEGIN
                        v_entity_id := COALESCE(NEW.tenant_id, OLD.tenant_id)::text;
                    EXCEPTION WHEN undefined_column THEN
                        BEGIN
                            v_entity_id := COALESCE(NEW.corpus_id, OLD.corpus_id)::text;
                        EXCEPTION WHEN undefined_column THEN
                            BEGIN
                                v_entity_id := COALESCE(NEW.submission_id, OLD.submission_id)::text;
                            EXCEPTION WHEN undefined_column THEN
                                BEGIN
                                    v_entity_id := COALESCE(NEW.message_id, OLD.message_id)::text;
                                EXCEPTION WHEN undefined_column THEN
                                    BEGIN
                                        v_entity_id := COALESCE(NEW.chunk_id, OLD.chunk_id)::text;
                                    EXCEPTION WHEN undefined_column THEN
                                        v_entity_id := 'unknown_' || TG_TABLE_NAME;
                                    END;
                                END;
                            END;
                        END;
                    END;
                END;
            END;

            INSERT INTO audit.event (
                tenant_id, user_id, actor_type, entity_name, entity_id, action,
                old_values, new_values, occurred_at
            ) VALUES (
                v_tenant_id, v_user_id, v_actor_type, TG_TABLE_NAME::text, v_entity_id, TG_OP,
                CASE WHEN TG_OP IN ('DELETE', 'UPDATE') THEN row_to_json(OLD)::jsonb ELSE NULL END,
                CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN row_to_json(NEW)::jsonb ELSE NULL END,
                NOW()
            );

            RETURN COALESCE(NEW, OLD);
        END;
        $$;
    """)


def downgrade() -> None:
    # Reverse all renames (6. → 1.)

    # 6. notification_category_sub_trigger.code → sub_trigger_id
    op.drop_constraint(
        "fk_notif_outbox_sub_trigger", "notification_outbox", type_="foreignkey"
    )
    op.drop_constraint(
        "pk_notif_sub_trigger", "notification_category_sub_trigger", type_="primary"
    )
    op.alter_column(
        "notification_category_sub_trigger", "code", new_column_name="sub_trigger_id"
    )
    op.create_primary_key(
        "pk_notif_sub_trigger", "notification_category_sub_trigger", ["sub_trigger_id"]
    )
    op.create_foreign_key(
        "fk_notif_outbox_sub_trigger",
        "notification_outbox",
        "notification_category_sub_trigger",
        ["sub_trigger_id"],
        ["sub_trigger_id"],
    )

    # 5. notification_category.code → category_id
    op.drop_constraint(
        "fk_notif_sub_trigger_category",
        "notification_category_sub_trigger",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_notif_default_policy_category",
        "notification_default_policy",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_notif_pref_category", "notification_preference", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_in_app_notif_category", "in_app_notification", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_notif_outbox_category", "notification_outbox", type_="foreignkey"
    )
    op.drop_constraint(
        "pk_notification_category", "notification_category", type_="primary"
    )
    op.alter_column("notification_category", "code", new_column_name="category_id")
    op.create_primary_key(
        "pk_notification_category", "notification_category", ["category_id"]
    )
    op.create_foreign_key(
        "fk_notif_sub_trigger_category",
        "notification_category_sub_trigger",
        "notification_category",
        ["category_id"],
        ["category_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_notif_default_policy_category",
        "notification_default_policy",
        "notification_category",
        ["category_id"],
        ["category_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_notif_pref_category",
        "notification_preference",
        "notification_category",
        ["category_id"],
        ["category_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_in_app_notif_category",
        "in_app_notification",
        "notification_category",
        ["category_id"],
        ["category_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_notif_outbox_category",
        "notification_outbox",
        "notification_category",
        ["category_id"],
        ["category_id"],
    )

    # 4. help_article.code → article_id
    op.drop_constraint(
        "fk_help_article_chunk_article_id", "help_article_chunk", type_="foreignkey"
    )
    op.drop_constraint("pk_help_article", "help_article", type_="primary")
    op.alter_column("help_article", "code", new_column_name="article_id")
    op.create_primary_key("pk_help_article", "help_article", ["article_id"])
    op.create_foreign_key(
        "fk_help_article_chunk_article_id",
        "help_article_chunk",
        "help_article",
        ["article_id"],
        ["article_id"],
        ondelete="CASCADE",
    )

    # 3. in_app_notification.id → notification_id
    op.drop_constraint("pk_in_app_notification", "in_app_notification", type_="primary")
    op.alter_column("in_app_notification", "id", new_column_name="notification_id")
    op.create_primary_key(
        "pk_in_app_notification", "in_app_notification", ["notification_id"]
    )

    # 2. mobile_sync_session.id → session_id
    op.drop_constraint(
        "mobile_sync_session_pkey", "mobile_sync_session", type_="primary"
    )
    op.alter_column("mobile_sync_session", "id", new_column_name="session_id")
    op.create_primary_key(
        "mobile_sync_session_pkey", "mobile_sync_session", ["session_id"]
    )

    # 1. help_chat_session.id → session_id
    op.drop_constraint(
        "fk_help_chat_message_session_id", "help_chat_message", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_feedback_submission_session_id", "feedback_submission", type_="foreignkey"
    )
    op.drop_constraint("pk_help_chat_session", "help_chat_session", type_="primary")
    op.alter_column("help_chat_session", "id", new_column_name="session_id")
    op.create_primary_key("pk_help_chat_session", "help_chat_session", ["session_id"])
    op.create_foreign_key(
        "fk_help_chat_message_session_id",
        "help_chat_message",
        "help_chat_session",
        ["session_id"],
        ["session_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_feedback_submission_session_id",
        "feedback_submission",
        "help_chat_session",
        ["from_help_chat_session_id"],
        ["session_id"],
        ondelete="SET NULL",
    )
