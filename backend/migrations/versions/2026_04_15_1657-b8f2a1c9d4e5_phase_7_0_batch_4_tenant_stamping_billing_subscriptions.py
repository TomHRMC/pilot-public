"""phase_7_0_batch_4_tenant_stamping_billing_subscriptions

Revision ID: b8f2a1c9d4e5
Revises: 4ae652c5fe7a
Create Date: 2026-04-15 16:57:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8f2a1c9d4e5"
down_revision: str | None = "4ae652c5fe7a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ==============================================================
    # TABLE: invoice_line  (parent: invoice via invoice_id)
    # ==============================================================
    op.add_column("invoice_line", sa.Column("tenant_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_invoice_line_tenant_id", "invoice_line", "tenant", ["tenant_id"], ["id"]
    )
    op.create_index("ix_invoice_line_tenant_id", "invoice_line", ["tenant_id"])
    op.execute("""
        UPDATE invoice_line
        SET tenant_id = invoice.tenant_id
        FROM invoice
        WHERE invoice_line.invoice_id = invoice.id
    """)
    op.alter_column("invoice_line", "tenant_id", nullable=False)

    # ==============================================================
    # TABLE: invoice_line_tax_component  (2-HOP: via invoice_line -> invoice)
    # NOTE: invoice_line must already have tenant_id at this point (set above).
    # ==============================================================
    op.add_column(
        "invoice_line_tax_component", sa.Column("tenant_id", sa.Uuid(), nullable=True)
    )
    op.create_foreign_key(
        "fk_invoice_line_tax_component_tenant_id",
        "invoice_line_tax_component",
        "tenant",
        ["tenant_id"],
        ["id"],
    )
    op.create_index(
        "ix_invoice_line_tax_component_tenant_id",
        "invoice_line_tax_component",
        ["tenant_id"],
    )
    op.execute("""
        UPDATE invoice_line_tax_component
        SET tenant_id = invoice.tenant_id
        FROM invoice_line
        JOIN invoice ON invoice_line.invoice_id = invoice.id
        WHERE invoice_line_tax_component.invoice_line_id = invoice_line.id
    """)
    op.alter_column("invoice_line_tax_component", "tenant_id", nullable=False)

    # ==============================================================
    # TABLE: subscription_usage  (parent: subscription via subscription_id)
    # ==============================================================
    op.add_column(
        "subscription_usage", sa.Column("tenant_id", sa.Uuid(), nullable=True)
    )
    op.create_foreign_key(
        "fk_subscription_usage_tenant_id",
        "subscription_usage",
        "tenant",
        ["tenant_id"],
        ["id"],
    )
    op.create_index(
        "ix_subscription_usage_tenant_id", "subscription_usage", ["tenant_id"]
    )
    op.execute("""
        UPDATE subscription_usage
        SET tenant_id = subscription.tenant_id
        FROM subscription
        WHERE subscription_usage.subscription_id = subscription.id
    """)
    op.alter_column("subscription_usage", "tenant_id", nullable=False)


def downgrade() -> None:
    op.drop_index("ix_subscription_usage_tenant_id", table_name="subscription_usage")
    op.drop_constraint(
        "fk_subscription_usage_tenant_id", "subscription_usage", type_="foreignkey"
    )
    op.drop_column("subscription_usage", "tenant_id")

    op.drop_index(
        "ix_invoice_line_tax_component_tenant_id",
        table_name="invoice_line_tax_component",
    )
    op.drop_constraint(
        "fk_invoice_line_tax_component_tenant_id",
        "invoice_line_tax_component",
        type_="foreignkey",
    )
    op.drop_column("invoice_line_tax_component", "tenant_id")

    op.drop_index("ix_invoice_line_tenant_id", table_name="invoice_line")
    op.drop_constraint("fk_invoice_line_tenant_id", "invoice_line", type_="foreignkey")
    op.drop_column("invoice_line", "tenant_id")
