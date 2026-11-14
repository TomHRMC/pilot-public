"""phase_fe_1_batch_b1_quote_approval_comment

Revision ID: ac34c70bc60b
Revises: b7c2026aee48
Create Date: 2026-05-01 12:00:33

A30 — Approval Comment & Annotation System
Creates: quote_approval_comment table (AppendOnly — no updated_at trigger)
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ac34c70bc60b"
down_revision = "b7c2026aee48"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quote_approval_comment",
        sa.Column(
            "id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("quote_id", sa.UUID(), nullable=False),
        sa.Column("quote_version_id", sa.UUID(), nullable=False),
        sa.Column("target_line_id", sa.UUID(), nullable=True),
        sa.Column("author_user_id", sa.UUID(), nullable=False),
        sa.Column("comment_type", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
            ondelete="RESTRICT",
            name="fk_quote_approval_comment_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["quote_id"],
            ["quote.id"],
            ondelete="RESTRICT",
            name="fk_quote_approval_comment_quote",
        ),
        sa.ForeignKeyConstraint(
            ["quote_version_id"],
            ["quote_version.id"],
            ondelete="RESTRICT",
            name="fk_quote_approval_comment_version",
        ),
        sa.ForeignKeyConstraint(
            ["target_line_id"],
            ["quote_line.id"],
            ondelete="RESTRICT",
            name="fk_quote_approval_comment_target_line",
        ),
        sa.ForeignKeyConstraint(
            ["author_user_id"],
            ["user.id"],
            ondelete="RESTRICT",
            name="fk_quote_approval_comment_author",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            ondelete="RESTRICT",
            name="fk_quote_approval_comment_created_by",
        ),
        sa.CheckConstraint(
            "comment_type IN ('kickback', 'rejection', 'edit_annotation')",
            name="chk_quote_approval_comment_type",
        ),
    )
    op.create_index(
        "ix_quote_approval_comment_quote_id", "quote_approval_comment", ["quote_id"]
    )
    op.create_index(
        "ix_quote_approval_comment_tenant", "quote_approval_comment", ["tenant_id"]
    )
    op.create_index(
        "ix_quote_approval_comment_version",
        "quote_approval_comment",
        ["quote_version_id"],
    )

    # Audit trigger only — AppendOnly table has no updated_at trigger
    op.execute("""
        CREATE TRIGGER audit_quote_approval_comment_changes
          AFTER INSERT OR DELETE OR UPDATE ON public.quote_approval_comment
          FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER trg_quote_approval_comment_guard_created_immutable
          BEFORE UPDATE ON public.quote_approval_comment
          FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_quote_approval_comment_guard_created_immutable ON public.quote_approval_comment"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_quote_approval_comment_changes ON public.quote_approval_comment"
    )
    op.drop_index(
        "ix_quote_approval_comment_version", table_name="quote_approval_comment"
    )
    op.drop_index(
        "ix_quote_approval_comment_tenant", table_name="quote_approval_comment"
    )
    op.drop_index(
        "ix_quote_approval_comment_quote_id", table_name="quote_approval_comment"
    )
    op.drop_table("quote_approval_comment")
