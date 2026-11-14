"""task_1a2_pricing_cache_tenant_stamping

Task 1-A-2: Add `tenant_id` column to `pricing_cache` table to prevent
cross-tenant cache reads leaking material prices between tenants.

NULL tenant_id = global/shared price (accessible to all tenants).
Non-NULL tenant_id = private negotiated price for that tenant only.

All cache reads must filter: tenant_id IS NULL OR tenant_id = <current_tenant_id>

Revision ID: a1b2c3d4e5f6
Revises: 39ca85621aad
Create Date: 2026-04-20 17:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "39ca85621aad"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Step 1: Add tenant_id column (nullable — existing rows represent global prices)
    op.add_column(
        "pricing_cache",
        sa.Column(
            "tenant_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=True,
            comment=(
                "NULL = global/shared price accessible to all tenants. "
                "Non-NULL = private negotiated price for this tenant only. "
                "Always filter: tenant_id IS NULL OR tenant_id = current_tenant_id"
            ),
        ),
    )

    # Step 2: Backfill — all existing rows were implicitly global; set NULL explicitly
    # (NULL is already the default for new nullable column, but explicit for clarity)
    op.execute("UPDATE pricing_cache SET tenant_id = NULL WHERE tenant_id IS NOT NULL")

    # Step 3: Create index for efficient tenant-scoped cache lookups
    op.create_index(
        "idx_pricing_cache_tenant",
        "pricing_cache",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_pricing_cache_tenant", table_name="pricing_cache")
    op.drop_column("pricing_cache", "tenant_id")
