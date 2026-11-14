"""phase_fe_1_batch_b16_help_training_corpus_table

Revision ID: 0c8ae7d64a43
Revises: 756c313524ce
Create Date: 2026-05-03 21:55:45

Creates the help_training_corpus table (A88 - Anonymization Pipeline).
Mixin: MachineLogMixin - audit trigger only.
Written exclusively by the anonymize_help_sessions Celery task.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0c8ae7d64a43"
down_revision = "756c313524ce"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE public.help_training_corpus (
            corpus_id                       UUID        NOT NULL DEFAULT gen_random_uuid(),
            original_session_id_hash        TEXT        NOT NULL,
            anonymized_message_history      JSONB       NOT NULL,
            anonymized_context_payload      JSONB       NULL,
            category_inferred               TEXT        NULL,
            outcome                         TEXT        NOT NULL,
            anonymized_at                   TIMESTAMPTZ NOT NULL,
            created_at                      TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pk_help_training_corpus PRIMARY KEY (corpus_id)
        )
    """)

    # B-tree index on hash for dedup check before inserting
    op.execute("""
        CREATE INDEX ix_help_training_corpus_original_session_id_hash
        ON public.help_training_corpus USING btree (original_session_id_hash)
    """)

    # B-tree index on category for training data filtering
    op.execute("""
        CREATE INDEX ix_help_training_corpus_category_inferred
        ON public.help_training_corpus USING btree (category_inferred)
    """)

    # MachineLogMixin audit trigger
    op.execute("""
        CREATE TRIGGER audit_help_training_corpus_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.help_training_corpus
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS audit_help_training_corpus_changes ON public.help_training_corpus"
    )
    op.execute("DROP INDEX IF EXISTS ix_help_training_corpus_category_inferred")
    op.execute("DROP INDEX IF EXISTS ix_help_training_corpus_original_session_id_hash")
    op.execute("DROP TABLE IF EXISTS public.help_training_corpus")
