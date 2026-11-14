"""phase_7_0_batch_2_tenant_stamping_sales_presales

Revision ID: 7d0f9c2be964
Revises: 687f10bf3c08
Create Date: 2026-04-15 13:55:14.434880+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7d0f9c2be964"
down_revision: str | None = "687f10bf3c08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    tables = [
        "quote_version",
        "quote_line",
        "quote_public_link",
        "quote_public_link_contact_action",
        "quote_line_tax_component",
        "quote_acceptance",
    ]

    # 1. Add nullable columns and constraints
    for table in tables:
        op.add_column(table, sa.Column("tenant_id", sa.Uuid(), nullable=True))
        op.create_foreign_key(
            f"fk_{table}_tenant_id", table, "tenant", ["tenant_id"], ["id"]
        )
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])

    # 2. Backfill data
    op.execute("""
        UPDATE quote_version SET tenant_id = quote.tenant_id 
        FROM quote WHERE quote_version.quote_id = quote.id;
        
        UPDATE quote_line SET tenant_id = quote.tenant_id 
        FROM quote WHERE quote_line.quote_id = quote.id;
        
        UPDATE quote_public_link SET tenant_id = quote.tenant_id 
        FROM quote WHERE quote_public_link.quote_id = quote.id;
        
        UPDATE quote_public_link_contact_action SET tenant_id = quote.tenant_id 
        FROM quote WHERE quote_public_link_contact_action.quote_id = quote.id;
        
        UPDATE quote_line_tax_component SET tenant_id = quote_line.tenant_id 
        FROM quote_line WHERE quote_line_tax_component.quote_line_id = quote_line.id;
        
        UPDATE quote_acceptance SET tenant_id = quote_version.tenant_id 
        FROM quote_version WHERE quote_acceptance.quote_version_id = quote_version.id;
    """)

    # 3. Make columns not null
    for table in tables:
        op.alter_column(table, "tenant_id", nullable=False)


def downgrade() -> None:
    tables = [
        "quote_acceptance",
        "quote_line_tax_component",
        "quote_public_link_contact_action",
        "quote_public_link",
        "quote_line",
        "quote_version",
    ]

    for table in tables:
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        op.drop_constraint(f"fk_{table}_tenant_id", table, type_="foreignkey")
        op.drop_column(table, "tenant_id")
