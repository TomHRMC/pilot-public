"""phase_fe_1_batch_b18_qco_line_type_qb_hint

FIND-070 (S2 High) — B18 schema: Add qb_item_name_hint VARCHAR NULL to qco_line_type.
Seed system rows with QB item name hints for 3 system line types.

Column purpose:
  qco_line_type.qb_item_name_hint VARCHAR NULL — human-readable hint used at QB connect
  time to search the tenant's QB Items catalog by name and resolve the per-tenant QB item_id.
  Stored in integration_sync_mapping after lookup. Tenant-custom rows may optionally set
  their own hint; NULL means use generic 'Services' fallback.

Seed data (system rows where tenant_id IS NULL):
  code='labor'    → qb_item_name_hint='Services'
  code='material' → qb_item_name_hint='Materials'
  code='misc'     → qb_item_name_hint='Miscellaneous'
  code='discount' → qb_item_name_hint unchanged (NULL — discounts handled separately in QB)

Revision ID: 2a06b786eba8
Revises: 37a63f686aa1
Create Date: 2026-05-12 16:58:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "2a06b786eba8"
down_revision = "37a63f686aa1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Part 1: Add nullable column
    op.add_column(
        "qco_line_type",
        sa.Column("qb_item_name_hint", sa.String(), nullable=True),
    )

    # Part 2: Seed system rows (tenant_id IS NULL)
    op.execute(
        "UPDATE qco_line_type "
        "SET qb_item_name_hint = 'Services' "
        "WHERE code = 'labor' AND tenant_id IS NULL"
    )
    op.execute(
        "UPDATE qco_line_type "
        "SET qb_item_name_hint = 'Materials' "
        "WHERE code = 'material' AND tenant_id IS NULL"
    )
    op.execute(
        "UPDATE qco_line_type "
        "SET qb_item_name_hint = 'Miscellaneous' "
        "WHERE code = 'misc' AND tenant_id IS NULL"
    )


def downgrade() -> None:
    op.drop_column("qco_line_type", "qb_item_name_hint")
