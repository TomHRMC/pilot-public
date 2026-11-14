"""phase_fe_1_batch_b18_quote_template_version_table

FIND-098 (S2 High) — Create quote_template_version table (A25 deferred schema).

Table: quote_template_version
Mixin: AppendOnlyMixin → created_at TIMESTAMPTZ NOT NULL, created_by UUID NULL FK → user.id
Triggers: guard_created_immutable + audit_quote_template_version_changes

Seed step: Insert version_no=1 rows for all existing quote_template records,
capturing current quote_template_line data as content_json.

Revision ID: fca6bd403dcc
Revises: 60cd7250d815
Create Date: 2026-05-12 17:33:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

# revision identifiers, used by Alembic.
revision = "fca6bd403dcc"
down_revision = "60cd7250d815"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Create table ──────────────────────────────────────────────────────────
    op.create_table(
        "quote_template_version",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", PG_UUID(as_uuid=True), nullable=True),
        sa.Column(
            "id",
            PG_UUID(as_uuid=True),
            nullable=False,
            primary_key=True,
        ),
        sa.Column("template_id", PG_UUID(as_uuid=True), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("content_json", JSONB, nullable=False),
        sa.Column("changelog", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["quote_template.id"],
            name="fk_qtv_template_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            name="fk_qtv_created_by",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "template_id",
            "version_no",
            name="uq_quote_template_version_template_version",
        ),
    )
    op.create_index(
        "ix_quote_template_version_template_id",
        "quote_template_version",
        ["template_id"],
    )

    # ── Triggers (AppendOnlyMixin: 2-trigger set) ────────────────────────────
    op.execute("""
        CREATE TRIGGER audit_quote_template_version_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.quote_template_version
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER guard_quote_template_version_created_immutable
        BEFORE UPDATE ON public.quote_template_version
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)

    # ── Seed step: insert version_no=1 for all existing quote_template rows ────
    # Captures the current quote_template_line rows as content_json.
    # Uses ON CONFLICT DO NOTHING to be idempotent.
    op.execute("""
        INSERT INTO quote_template_version (id, template_id, version_no, content_json, created_at)
        SELECT
            gen_random_uuid(),
            qt.id,
            1,
            COALESCE(
                (
                    SELECT jsonb_agg(
                        jsonb_build_object(
                            'id', qtl.id,
                            'qco_line_type_id', qtl.qco_line_type_id,
                            'description', qtl.description,
                            'default_unit_price_cents', qtl.default_unit_price_cents,
                            'default_quantity', qtl.default_quantity,
                            'display_order', qtl.display_order,
                            'customer_visible', qtl.customer_visible,
                            'is_section_header', qtl.is_section_header,
                            'is_active', qtl.is_active
                        ) ORDER BY qtl.display_order
                    )
                    FROM quote_template_line qtl
                    WHERE qtl.quote_template_id = qt.id AND qtl.is_active = true
                ),
                '[]'::jsonb
            ),
            now()
        FROM quote_template qt
        ON CONFLICT (template_id, version_no) DO NOTHING
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS guard_quote_template_version_created_immutable "
        "ON public.quote_template_version"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_quote_template_version_changes "
        "ON public.quote_template_version"
    )
    op.drop_index(
        "ix_quote_template_version_template_id",
        table_name="quote_template_version",
    )
    op.drop_table("quote_template_version")
