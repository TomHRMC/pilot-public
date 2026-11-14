"""task_1d3_invoice_public_link_table

Revision ID: 3b2ac47ee8ab
Revises: a834b0fecf38
Create Date: 2026-04-21 16:31:59.000000

Task 1-D-3: Create invoice_public_link table.
=================================================
New table provides a secure, revocable, time-boxed token for a customer to view
and pay an invoice without authenticating — analogous to quote_public_link.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

# revision identifiers, used by Alembic.
revision = "3b2ac47ee8ab"
down_revision = "a834b0fecf38"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # 1. Create the invoice_public_link table with explicit constraint names
    # ------------------------------------------------------------------ #
    op.create_table(
        "invoice_public_link",
        sa.Column("id", PG_UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", PG_UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_id", PG_UUID(as_uuid=True), nullable=False),
        sa.Column("contact_id", PG_UUID(as_uuid=True), nullable=True),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_uses", sa.Integer(), server_default="0", nullable=False),
        sa.Column("used_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(), server_default="active", nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", PG_UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", PG_UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="invoice_public_link_pkey"),
        sa.UniqueConstraint("token_hash", name="uq_invoice_public_link_token_hash"),
        sa.CheckConstraint(
            "status IN ('active', 'revoked', 'expired')",
            name="invoice_public_link_status_chk",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
            name="fk_invoice_public_link_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoice.id"],
            name="fk_invoice_public_link_invoice",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["contact_id"],
            ["contact.id"],
            name="fk_invoice_public_link_contact",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
            name="fk_invoice_public_link_created_by",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["user.id"],
            name="fk_invoice_public_link_updated_by",
            ondelete="RESTRICT",
        ),
    )

    # ------------------------------------------------------------------ #
    # 2. Indexes
    # ------------------------------------------------------------------ #
    op.create_index(
        "ix_invoice_public_link_tenant_id", "invoice_public_link", ["tenant_id"]
    )
    op.create_index(
        "idx_invoice_public_link_invoice", "invoice_public_link", ["invoice_id"]
    )
    op.create_index(
        "idx_invoice_public_link_contact", "invoice_public_link", ["contact_id"]
    )

    # ------------------------------------------------------------------ #
    # 3. Apply standard AevoFab Triggers
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE TRIGGER audit_invoice_public_link_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.invoice_public_link
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER trg_invoice_public_link_guard_created_immutable
        BEFORE UPDATE ON public.invoice_public_link
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)
    op.execute("""
        CREATE TRIGGER trg_invoice_public_link_set_updated_at
        BEFORE UPDATE ON public.invoice_public_link
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)


def downgrade() -> None:
    # Triggers drop automatically when the table is dropped,
    # but dropping them explicitly is safer for complex environments.
    op.execute(
        "DROP TRIGGER IF EXISTS audit_invoice_public_link_changes ON invoice_public_link"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_invoice_public_link_guard_created_immutable ON invoice_public_link"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_invoice_public_link_set_updated_at ON invoice_public_link"
    )

    op.drop_table("invoice_public_link")
