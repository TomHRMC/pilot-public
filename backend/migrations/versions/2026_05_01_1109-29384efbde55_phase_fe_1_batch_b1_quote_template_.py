"""phase_fe_1_batch_b1_quote_template_schema

Revision ID: 29384efbde55
Revises: 0711fb10275a
Create Date: 2026-05-01 11:09:44

A25 — Quote Template Schema with Style and Versioning
- Creates quote_template table (new)
- Creates quote_template_line table (new)
- Seeds 3 system templates
- Adds triggers: audit, immutable guard, updated_at on both tables
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "29384efbde55"
down_revision = "0711fb10275a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # 1. Create quote_template table                                      #
    # ------------------------------------------------------------------ #
    op.create_table(
        "quote_template",
        sa.Column(
            "id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("style", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("system_template_id", sa.UUID(), nullable=True),
        sa.Column("forked_from_version", sa.Integer(), nullable=True),
        sa.Column(
            "current_version", sa.Integer(), nullable=False, server_default=sa.text("1")
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "is_system_template",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
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
            name="fk_quote_template_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["system_template_id"],
            ["quote_template.id"],
            ondelete="RESTRICT",
            name="fk_quote_template_system_template_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            ondelete="RESTRICT",
            name="fk_quote_template_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["user.id"],
            ondelete="RESTRICT",
            name="fk_quote_template_updated_by",
        ),
        sa.UniqueConstraint("tenant_id", "name", name="uq_quote_template_tenant_name"),
        sa.CheckConstraint(
            "style IN ('component', 'deliverable', 'lump_sum')",
            name="chk_quote_template_style",
        ),
    )
    op.create_index("ix_quote_template_tenant_id", "quote_template", ["tenant_id"])
    op.create_index(
        "ix_quote_template_system_template_id", "quote_template", ["system_template_id"]
    )

    # ------------------------------------------------------------------ #
    # 2. Create quote_template_line table                                 #
    # ------------------------------------------------------------------ #
    op.create_table(
        "quote_template_line",
        sa.Column(
            "id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("quote_template_id", sa.UUID(), nullable=False),
        sa.Column("parent_line_id", sa.UUID(), nullable=True),
        sa.Column(
            "display_order", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("qco_line_type_id", sa.UUID(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "default_quantity",
            sa.Numeric(12, 3),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "default_unit_price_cents",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "customer_visible",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "is_section_header",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
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
            name="fk_quote_template_line_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["quote_template_id"],
            ["quote_template.id"],
            ondelete="RESTRICT",
            name="fk_quote_template_line_template",
        ),
        sa.ForeignKeyConstraint(
            ["parent_line_id"],
            ["quote_template_line.id"],
            ondelete="RESTRICT",
            name="fk_quote_template_line_parent",
        ),
        sa.ForeignKeyConstraint(
            ["qco_line_type_id"],
            ["qco_line_type.id"],
            name="fk_quote_template_line_qco_type",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            ondelete="RESTRICT",
            name="fk_quote_template_line_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["user.id"],
            ondelete="RESTRICT",
            name="fk_quote_template_line_updated_by",
        ),
    )
    op.create_index(
        "ix_quote_template_line_template_id",
        "quote_template_line",
        ["quote_template_id"],
    )
    op.create_index(
        "ix_quote_template_line_tenant_id", "quote_template_line", ["tenant_id"]
    )
    op.create_index(
        "ix_quote_template_line_parent", "quote_template_line", ["parent_line_id"]
    )

    # ------------------------------------------------------------------ #
    # 3. Triggers on quote_template                                       #
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE TRIGGER audit_quote_template_changes
          AFTER INSERT OR DELETE OR UPDATE ON public.quote_template
          FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER trg_quote_template_guard_created_immutable
          BEFORE UPDATE ON public.quote_template
          FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)
    op.execute("""
        CREATE TRIGGER trg_quote_template_set_updated_at
          BEFORE UPDATE ON public.quote_template
          FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)

    # ------------------------------------------------------------------ #
    # 4. Triggers on quote_template_line                                  #
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE TRIGGER audit_quote_template_line_changes
          AFTER INSERT OR DELETE OR UPDATE ON public.quote_template_line
          FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER trg_quote_template_line_guard_created_immutable
          BEFORE UPDATE ON public.quote_template_line
          FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)
    op.execute("""
        CREATE TRIGGER trg_quote_template_line_set_updated_at
          BEFORE UPDATE ON public.quote_template_line
          FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)

    # ------------------------------------------------------------------ #
    # 5. Seed 3 system templates (tenant_id=NULL, is_system_template=TRUE) #
    # ------------------------------------------------------------------ #
    op.execute("""
        INSERT INTO quote_template (id, tenant_id, name, style, category, is_active, is_system_template, current_version, created_at, updated_at)
        VALUES
          (gen_random_uuid(), NULL, 'Service Call Basic', 'component', 'service_call', TRUE, TRUE, 1, now(), now()),
          (gen_random_uuid(), NULL, 'Installation Standard', 'deliverable', 'installation', TRUE, TRUE, 1, now(), now()),
          (gen_random_uuid(), NULL, 'Fixed Bid Simple', 'lump_sum', NULL, TRUE, TRUE, 1, now(), now())
    """)


def downgrade() -> None:
    # Remove triggers first
    op.execute(
        "DROP TRIGGER IF EXISTS trg_quote_template_line_set_updated_at ON public.quote_template_line"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_quote_template_line_guard_created_immutable ON public.quote_template_line"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_quote_template_line_changes ON public.quote_template_line"
    )

    op.execute(
        "DROP TRIGGER IF EXISTS trg_quote_template_set_updated_at ON public.quote_template"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_quote_template_guard_created_immutable ON public.quote_template"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_quote_template_changes ON public.quote_template"
    )

    # Drop tables in reverse dependency order (line before template)
    op.drop_table("quote_template_line")
    op.drop_table("quote_template")
