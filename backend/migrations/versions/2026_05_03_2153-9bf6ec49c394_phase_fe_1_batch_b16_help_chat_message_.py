"""phase_fe_1_batch_b16_help_chat_message_table

Revision ID: 9bf6ec49c394
Revises: 7047dfd8f83d
Create Date: 2026-05-03 21:53:43

Creates the help_chat_message table (A84 - Help AI Chat messages).
Includes tenant_id per design doc F.2 decision (matches conversation_message precedent).
Mixin: AppendOnlyMixin - 2-trigger set (audit, guard_created_immutable).
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "9bf6ec49c394"
down_revision = "7047dfd8f83d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE public.help_chat_message (
            message_id          UUID        NOT NULL DEFAULT gen_random_uuid(),
            session_id          UUID        NOT NULL,
            tenant_id           UUID        NOT NULL,
            role                TEXT        NOT NULL,
            content             TEXT        NOT NULL,
            context_payload     JSONB       NULL,
            retrieved_chunks    JSONB       NULL,
            voice_used          BOOLEAN     NOT NULL DEFAULT false,
            created_at          TIMESTAMPTZ NOT NULL,
            created_by          UUID        NULL,
            CONSTRAINT pk_help_chat_message PRIMARY KEY (message_id),
            CONSTRAINT fk_help_chat_message_session_id
                FOREIGN KEY (session_id)
                REFERENCES public.help_chat_session (session_id)
                ON DELETE CASCADE,
            CONSTRAINT fk_help_chat_message_tenant_id
                FOREIGN KEY (tenant_id)
                REFERENCES public.tenant (id)
                ON DELETE RESTRICT,
            CONSTRAINT help_chat_message_role_chk
                CHECK (role IN ('user', 'assistant'))
        )
    """)

    # B-tree indexes
    op.execute("""
        CREATE INDEX ix_help_chat_message_session_id
        ON public.help_chat_message USING btree (session_id)
    """)
    op.execute("""
        CREATE INDEX ix_help_chat_message_tenant_id
        ON public.help_chat_message USING btree (tenant_id)
    """)

    # AppendOnlyMixin - 2-trigger set
    op.execute("""
        CREATE TRIGGER audit_help_chat_message_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.help_chat_message
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER guard_help_chat_message_created_immutable
        BEFORE UPDATE ON public.help_chat_message
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS guard_help_chat_message_created_immutable ON public.help_chat_message"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_help_chat_message_changes ON public.help_chat_message"
    )
    op.execute("DROP INDEX IF EXISTS ix_help_chat_message_tenant_id")
    op.execute("DROP INDEX IF EXISTS ix_help_chat_message_session_id")
    op.execute("DROP TABLE IF EXISTS public.help_chat_message")
