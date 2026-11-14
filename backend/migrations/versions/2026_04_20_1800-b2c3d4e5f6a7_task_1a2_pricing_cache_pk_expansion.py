"""task_1a2_pricing_cache_pk_expansion

Task 1-A-2 (Part 2): Expand `pricing_cache` primary key to support
per-tenant negotiated prices alongside global prices for the same SKU.

Changes:
  1. Add `id` bigserial surrogate PK
  2. Drop old composite PK (supplier_id, sku)
  3. Add business-key UNIQUE constraint using PostgreSQL 17 NULLS NOT DISTINCT:
       UNIQUE NULLS NOT DISTINCT (supplier_id, sku, tenant_id)
  4. Add index on (supplier_id, sku) for fast lookup
  5. Backfill existing rows

This allows:
  (supplier_id='X', sku='Y', tenant_id=NULL)   ← global price (one allowed per SKU)
  (supplier_id='X', sku='Y', tenant_id=<uuid>) ← per-tenant negotiated price

NULLS NOT DISTINCT means two rows with tenant_id=NULL on the same (supplier_id, sku)
will violate the constraint — ensuring exactly one global price per SKU.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-20 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()

    # -----------------------------------------------------------------------
    # Step 1: Add the new surrogate id column (temporarily nullable)
    # -----------------------------------------------------------------------
    op.add_column(
        "pricing_cache",
        sa.Column("id", sa.BigInteger(), nullable=True),
    )
    conn.execute(sa.text("CREATE SEQUENCE IF NOT EXISTS pricing_cache_id_seq"))
    conn.execute(
        sa.text(
            "UPDATE pricing_cache SET id = nextval('pricing_cache_id_seq') WHERE id IS NULL"
        )
    )
    conn.execute(
        sa.text(
            "ALTER TABLE pricing_cache ALTER COLUMN id SET NOT NULL, "
            "ALTER COLUMN id SET DEFAULT nextval('pricing_cache_id_seq')"
        )
    )
    conn.execute(
        sa.text("ALTER SEQUENCE pricing_cache_id_seq OWNED BY pricing_cache.id")
    )

    # -----------------------------------------------------------------------
    # Step 2: Drop old composite PK and replace with surrogate id PK
    # -----------------------------------------------------------------------
    conn.execute(
        sa.text("ALTER TABLE pricing_cache DROP CONSTRAINT pricing_cache_pkey")
    )
    conn.execute(sa.text("ALTER TABLE pricing_cache ADD PRIMARY KEY (id)"))

    # -----------------------------------------------------------------------
    # Step 3: Add NULLS NOT DISTINCT unique constraint (PostgreSQL 15+/17)
    # Two rows with tenant_id=NULL on the same (supplier_id, sku) are treated
    # as duplicates, ensuring exactly one global price per SKU.
    # -----------------------------------------------------------------------
    conn.execute(
        sa.text(
            "ALTER TABLE pricing_cache "
            "ADD CONSTRAINT uq_pricing_cache_supplier_sku_tenant "
            "UNIQUE NULLS NOT DISTINCT (supplier_id, sku, tenant_id)"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text(
            "ALTER TABLE pricing_cache "
            "DROP CONSTRAINT IF EXISTS uq_pricing_cache_supplier_sku_tenant"
        )
    )

    # Restore old composite PK (will fail if duplicate supplier_id+sku rows exist)
    conn.execute(
        sa.text("ALTER TABLE pricing_cache DROP CONSTRAINT pricing_cache_pkey")
    )
    conn.execute(
        sa.text(
            "ALTER TABLE pricing_cache ADD CONSTRAINT pricing_cache_pkey "
            "PRIMARY KEY (supplier_id, sku)"
        )
    )

    op.drop_column("pricing_cache", "id")
    conn.execute(sa.text("DROP SEQUENCE IF EXISTS pricing_cache_id_seq"))
