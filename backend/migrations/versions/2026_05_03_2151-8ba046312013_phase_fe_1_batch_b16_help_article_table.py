"""phase_fe_1_batch_b16_help_article_table

Revision ID: 8ba046312013
Revises: a2c82e3c9940
Create Date: 2026-05-03 21:51:02

Creates the help_article table (A85 — Markdown Corpus).
Mixin: MachineLogMixin — audit trigger only.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "8ba046312013"
down_revision = "ada1196b8f39"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE public.help_article (
            article_id          TEXT        NOT NULL,
            s3_path             TEXT        NOT NULL,
            title               TEXT        NOT NULL,
            category            TEXT        NOT NULL,
            frontmatter_metadata JSONB       NOT NULL DEFAULT '{}'::jsonb,
            last_content_hash   TEXT        NOT NULL,
            last_processed_at   TIMESTAMPTZ NOT NULL,
            last_updated        DATE        NOT NULL,
            audience            TEXT[]      NOT NULL DEFAULT '{}'::text[],
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pk_help_article PRIMARY KEY (article_id)
        )
    """)

    # B-tree index on category
    op.execute("""
        CREATE INDEX ix_help_article_category
        ON public.help_article USING btree (category)
    """)

    # GIN index on audience for array containment (@>) filter
    op.execute("""
        CREATE INDEX ix_help_article_audience
        ON public.help_article USING gin (audience)
    """)

    # MachineLogMixin audit trigger
    op.execute("""
        CREATE TRIGGER audit_help_article_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.help_article
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS audit_help_article_changes ON public.help_article"
    )
    op.execute("DROP INDEX IF EXISTS ix_help_article_audience")
    op.execute("DROP INDEX IF EXISTS ix_help_article_category")
    op.execute("DROP TABLE IF EXISTS public.help_article")
