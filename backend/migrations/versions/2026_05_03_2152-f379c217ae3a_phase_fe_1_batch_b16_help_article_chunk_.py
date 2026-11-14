"""phase_fe_1_batch_b16_help_article_chunk_table

Revision ID: f379c217ae3a
Revises: 8ba046312013
Create Date: 2026-05-03 21:52:07

Creates the help_article_chunk table (A85 - pgvector embedding storage).
Requires the vector extension (already enabled from B2).
Mixin: MachineLogMixin - audit trigger only.

HNSW index note: deferred - must be created after table is populated.
The process_help_article Celery task creates it on first article processing:
  CREATE INDEX help_article_chunk_embedding_hnsw_idx
  ON public.help_article_chunk USING hnsw (embedding vector_cosine_ops)
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "f379c217ae3a"
down_revision = "8ba046312013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE public.help_article_chunk (
            chunk_id                    UUID        NOT NULL DEFAULT gen_random_uuid(),
            article_id                  TEXT        NOT NULL,
            chunk_order                 INTEGER     NOT NULL,
            section_title               TEXT        NOT NULL,
            chunk_text                  TEXT        NOT NULL,
            chunk_text_with_metadata    TEXT        NOT NULL,
            embedding                   vector(1536) NOT NULL,
            token_count                 INTEGER     NOT NULL,
            created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pk_help_article_chunk PRIMARY KEY (chunk_id),
            CONSTRAINT fk_help_article_chunk_article_id
                FOREIGN KEY (article_id)
                REFERENCES public.help_article (article_id)
                ON DELETE CASCADE
        )
    """)

    # B-tree index on article_id for FK joins
    op.execute("""
        CREATE INDEX ix_help_article_chunk_article_id
        ON public.help_article_chunk USING btree (article_id)
    """)

    # MachineLogMixin audit trigger
    op.execute("""
        CREATE TRIGGER audit_help_article_chunk_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.help_article_chunk
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS audit_help_article_chunk_changes ON public.help_article_chunk"
    )
    op.execute("DROP INDEX IF EXISTS ix_help_article_chunk_article_id")
    op.execute("DROP TABLE IF EXISTS public.help_article_chunk")
