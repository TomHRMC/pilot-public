"""phase_fe_1_batch_b16_feedback_submission_table

Revision ID: 756c313524ce
Revises: 9bf6ec49c394
Create Date: 2026-05-03 21:54:47

Creates the feedback_submission table (A87 - Feedback Submission).
Mixin: AppendOnlyMixin - 2-trigger set (audit, guard_created_immutable).
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "756c313524ce"
down_revision = "9bf6ec49c394"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE public.feedback_submission (
            submission_id               UUID        NOT NULL DEFAULT gen_random_uuid(),
            tenant_id                   UUID        NOT NULL,
            user_id                     UUID        NOT NULL,
            category                    TEXT        NOT NULL,
            body                        TEXT        NOT NULL,
            from_help_chat_session_id   UUID        NULL,
            email_sent_to               TEXT        NOT NULL,
            email_message_id            TEXT        NULL,
            created_at                  TIMESTAMPTZ NOT NULL,
            created_by                  UUID        NULL,
            CONSTRAINT pk_feedback_submission PRIMARY KEY (submission_id),
            CONSTRAINT fk_feedback_submission_tenant_id
                FOREIGN KEY (tenant_id)
                REFERENCES public.tenant (id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_feedback_submission_user_id
                FOREIGN KEY (user_id)
                REFERENCES public.user (id)
                ON DELETE RESTRICT,
            CONSTRAINT fk_feedback_submission_session_id
                FOREIGN KEY (from_help_chat_session_id)
                REFERENCES public.help_chat_session (session_id)
                ON DELETE SET NULL,
            CONSTRAINT feedback_submission_category_chk
                CHECK (category IN ('bug', 'feature_request', 'question', 'general'))
        )
    """)

    # B-tree indexes
    op.execute("""
        CREATE INDEX ix_feedback_submission_tenant_id
        ON public.feedback_submission USING btree (tenant_id)
    """)
    op.execute("""
        CREATE INDEX ix_feedback_submission_user_id
        ON public.feedback_submission USING btree (user_id)
    """)

    # Partial index for session-linked submissions
    op.execute("""
        CREATE INDEX ix_feedback_submission_from_session_id
        ON public.feedback_submission USING btree (from_help_chat_session_id)
        WHERE from_help_chat_session_id IS NOT NULL
    """)

    # AppendOnlyMixin - 2-trigger set
    op.execute("""
        CREATE TRIGGER audit_feedback_submission_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.feedback_submission
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER guard_feedback_submission_created_immutable
        BEFORE UPDATE ON public.feedback_submission
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS guard_feedback_submission_created_immutable ON public.feedback_submission"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_feedback_submission_changes ON public.feedback_submission"
    )
    op.execute("DROP INDEX IF EXISTS ix_feedback_submission_from_session_id")
    op.execute("DROP INDEX IF EXISTS ix_feedback_submission_user_id")
    op.execute("DROP INDEX IF EXISTS ix_feedback_submission_tenant_id")
    op.execute("DROP TABLE IF EXISTS public.feedback_submission")
