"""phase_fe_1_batch_b1_quote_pending_edit

Revision ID: b7c2026aee48
Revises: c83719f1152e
Create Date: 2026-05-01 12:00:33

A29 — Pending Edit Storage During Owner Review
Creates: quote_pending_edit table
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "b7c2026aee48"
down_revision = "c83719f1152e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quote_pending_edit",
        sa.Column(
            "id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("quote_id", sa.UUID(), nullable=False),
        sa.Column("quote_version_id", sa.UUID(), nullable=False),
        sa.Column("editor_user_id", sa.UUID(), nullable=False),
        sa.Column("edit_type", sa.Text(), nullable=False),
        sa.Column("target_line_id", sa.UUID(), nullable=True),
        sa.Column("edit_payload", JSONB(), nullable=False),
        sa.Column("annotation", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
            ondelete="RESTRICT",
            name="fk_quote_pending_edit_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["quote_id"],
            ["quote.id"],
            ondelete="RESTRICT",
            name="fk_quote_pending_edit_quote",
        ),
        sa.ForeignKeyConstraint(
            ["quote_version_id"],
            ["quote_version.id"],
            ondelete="RESTRICT",
            name="fk_quote_pending_edit_version",
        ),
        sa.ForeignKeyConstraint(
            ["editor_user_id"],
            ["user.id"],
            ondelete="RESTRICT",
            name="fk_quote_pending_edit_editor",
        ),
        sa.ForeignKeyConstraint(
            ["target_line_id"],
            ["quote_line.id"],
            ondelete="RESTRICT",
            name="fk_quote_pending_edit_target_line",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            ondelete="RESTRICT",
            name="fk_quote_pending_edit_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["user.id"],
            ondelete="RESTRICT",
            name="fk_quote_pending_edit_updated_by",
        ),
        sa.CheckConstraint(
            "edit_type IN ('modify_line', 'add_line', 'delete_line', 'edit_notes')",
            name="chk_quote_pending_edit_type",
        ),
    )
    op.create_index(
        "ix_quote_pending_edit_quote_id", "quote_pending_edit", ["quote_id"]
    )
    op.create_index(
        "ix_quote_pending_edit_editor",
        "quote_pending_edit",
        ["editor_user_id", "quote_version_id"],
    )
    op.create_index("ix_quote_pending_edit_tenant", "quote_pending_edit", ["tenant_id"])

    # Triggers
    op.execute("""
        CREATE TRIGGER audit_quote_pending_edit_changes
          AFTER INSERT OR DELETE OR UPDATE ON public.quote_pending_edit
          FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER trg_quote_pending_edit_guard_created_immutable
          BEFORE UPDATE ON public.quote_pending_edit
          FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)
    op.execute("""
        CREATE TRIGGER trg_quote_pending_edit_set_updated_at
          BEFORE UPDATE ON public.quote_pending_edit
          FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_quote_pending_edit_set_updated_at ON public.quote_pending_edit"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_quote_pending_edit_guard_created_immutable ON public.quote_pending_edit"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_quote_pending_edit_changes ON public.quote_pending_edit"
    )
    op.drop_index("ix_quote_pending_edit_tenant", table_name="quote_pending_edit")
    op.drop_index("ix_quote_pending_edit_editor", table_name="quote_pending_edit")
    op.drop_index("ix_quote_pending_edit_quote_id", table_name="quote_pending_edit")
    op.drop_table("quote_pending_edit")
