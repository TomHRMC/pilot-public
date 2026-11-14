"""phase_8_0_batch_3_indexes_catalog_suppliers

Revision ID: cc75f4532955
Revises: ca8edac7a80c
Create Date: 2026-04-15 22:22:07.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cc75f4532955"
down_revision: str | None = "ca8edac7a80c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- supplier ---
    op.create_index(
        "ix_supplier_lifecycle_status_id", "supplier", ["lifecycle_status_id"]
    )
    op.create_index("ix_supplier_tenant_id", "supplier", ["tenant_id"])

    # --- supplier_item ---
    op.create_index("ix_supplier_item_category_id", "supplier_item", ["category_id"])
    op.create_index("ix_supplier_item_uom_id", "supplier_item", ["uom_id"])
    op.create_index(
        "ix_supplier_item_taxability_code", "supplier_item", ["taxability_code"]
    )

    # --- supplier_item_price ---
    op.create_index(
        "ix_supplier_item_price_tenant_id", "supplier_item_price", ["tenant_id"]
    )
    op.create_index(
        "ix_supplier_item_price_currency", "supplier_item_price", ["currency"]
    )

    # --- app_service ---
    op.create_index("ix_app_service_provider_code", "app_service", ["provider_code"])

    # --- pricebook_item ---
    op.create_index("ix_pricebook_item_uom_id", "pricebook_item", ["uom_id"])
    op.create_index(
        "ix_pricebook_item_taxability_code", "pricebook_item", ["taxability_code"]
    )

    # --- pricing_cache ---
    op.create_index("ix_pricing_cache_currency", "pricing_cache", ["currency"])


def downgrade() -> None:
    op.drop_index("ix_supplier_lifecycle_status_id", table_name="supplier")
    op.drop_index("ix_supplier_tenant_id", table_name="supplier")
    op.drop_index("ix_supplier_item_category_id", table_name="supplier_item")
    op.drop_index("ix_supplier_item_uom_id", table_name="supplier_item")
    op.drop_index("ix_supplier_item_taxability_code", table_name="supplier_item")
    op.drop_index("ix_supplier_item_price_tenant_id", table_name="supplier_item_price")
    op.drop_index("ix_supplier_item_price_currency", table_name="supplier_item_price")
    op.drop_index("ix_app_service_provider_code", table_name="app_service")
    op.drop_index("ix_pricebook_item_uom_id", table_name="pricebook_item")
    op.drop_index("ix_pricebook_item_taxability_code", table_name="pricebook_item")
    op.drop_index("ix_pricing_cache_currency", table_name="pricing_cache")
