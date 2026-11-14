"""phase_4_7_add_missing_exclude_constraint_task7

Revision ID: e774cd9ebf0e
Revises: c4404f5f3e83
Create Date: 2026-04-07 19:17:15.761723+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e774cd9ebf0e"
down_revision: str | None = "c4404f5f3e83"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Phase 4.7 Task 7: Add Missing EXCLUDE Constraint for Supplier Item Price Overlap Prevention

    Pre-migration validation query (run before applying):
    SELECT
      a.id AS price_a_id,
      b.id AS price_b_id,
      a.supplier_item_id,
      a.tenant_id,
      a.valid_period AS a_period,
      b.valid_period AS b_period
    FROM supplier_item_price a
    JOIN supplier_item_price b
      ON a.supplier_item_id = b.supplier_item_id
      AND a.tenant_id = b.tenant_id
      AND a.id < b.id
    WHERE a.valid_period && b.valid_period;

    Expected result: 0 rows (no overlaps)
    """
    # Step 1: Ensure btree_gist extension exists (required for EXCLUDE with equality operators)
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS btree_gist"))

    # Step 2: Add EXCLUDE constraint to prevent overlapping price date ranges
    # Prevents: same supplier_item_id + tenant_id from having overlapping valid_period
    op.execute(
        sa.text("""
        ALTER TABLE supplier_item_price
        ADD CONSTRAINT sip_no_overlap
        EXCLUDE USING gist (
            supplier_item_id WITH =,
            tenant_id WITH =,
            valid_period WITH &&
        )
    """)
    )


def downgrade() -> None:
    """
    Rollback: Remove EXCLUDE constraint

    Note: We do NOT drop the btree_gist extension as other constraints may depend on it
    """
    # Remove EXCLUDE constraint
    op.execute(
        sa.text("ALTER TABLE supplier_item_price DROP CONSTRAINT sip_no_overlap")
    )
