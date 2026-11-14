"""phase_fe_1_batch_b16_help_chat_session_table

Revision ID: 7047dfd8f83d
Revises: f379c217ae3a
Create Date: 2026-05-03 21:52:59

Creates the help_chat_session table (A84 - Help AI Chat).
Mixin: StandardAuditMixin - 3-trigger set (audit, guard_immutable, set_updated_at).
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "7047dfd8f83d"
down_revision = "f379c217ae3a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE public.help_chat_session (
            session_id          UUID        NOT NULL DEFAULT gen_random_uuid(),
            tenant_id           UUID        NOT NULL,
            user_id             UUID        NOT NULL,
            started_at          TIMESTAMPTZ NOT NULL,
            last_activity_at    TIMESTAMPTZ NOT NULL,
            title               TEXT        NULL,
            outcome             TEXT        NULL,
            message_count       INTEGER     NOT NULL DEFAULT 0,
            anonymized_at       TIMESTAMPTZ NULL,
            created_at          TIMESTAMPTZ NOT NULL,
            updated_at          TIMESTAMPTZ NOT NULL,
            created_by          UUID        NULL,
            updated_by          UUID        NULL,
            CONSTRAINT pk_help_chat_session PRIMARY KEY (session_id),
            CONSTRAINT fk_help_chat_session_tenant_id
                FOREIGN KEY (tenant_id)
                REFERENCES public.tenant (id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_help_chat_session_user_id
                FOREIGN KEY (user_id)
                REFERENCES public.user (id)
                ON DELETE RESTRICT,
            CONSTRAINT help_chat_session_outcome_chk
                CHECK (outcome IN ('resolved', 'escalated', 'abandoned'))
        )
    """)

    # B-tree indexes
    op.execute("""
        CREATE INDEX ix_help_chat_session_tenant_id
        ON public.help_chat_session USING btree (tenant_id)
    """)
    op.execute("""
        CREATE INDEX ix_help_chat_session_user_id
        ON public.help_chat_session USING btree (user_id)
    """)
    op.execute("""
        CREATE INDEX ix_help_chat_session_last_activity_at
        ON public.help_chat_session USING btree (last_activity_at)
    """)

    # Partial index for anonymization pipeline date filter
    op.execute("""
        CREATE INDEX ix_help_chat_session_pending_anonymization
        ON public.help_chat_session USING btree (last_activity_at)
        WHERE anonymized_at IS NULL
    """)

    # StandardAuditMixin - 3-trigger set
    op.execute("""
        CREATE TRIGGER audit_help_chat_session_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.help_chat_session
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER guard_help_chat_session_created_immutable
        BEFORE UPDATE ON public.help_chat_session
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)
    op.execute("""
        CREATE TRIGGER set_help_chat_session_updated_at
        BEFORE UPDATE ON public.help_chat_session
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS set_help_chat_session_updated_at ON public.help_chat_session"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS guard_help_chat_session_created_immutable ON public.help_chat_session"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_help_chat_session_changes ON public.help_chat_session"
    )
    op.execute("DROP INDEX IF EXISTS ix_help_chat_session_pending_anonymization")
    op.execute("DROP INDEX IF EXISTS ix_help_chat_session_last_activity_at")
    op.execute("DROP INDEX IF EXISTS ix_help_chat_session_user_id")
    op.execute("DROP INDEX IF EXISTS ix_help_chat_session_tenant_id")
    op.execute("DROP TABLE IF EXISTS public.help_chat_session")
