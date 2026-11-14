"""add_temporal_exclusion_constraints_task10

Revision ID: 3b01a0ab356f
Revises: b78d2b0199e8
Create Date: 2026-04-01 15:24:44.920401+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3b01a0ab356f"
down_revision: str | None = "b78d2b0199e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Add temporal exclusion constraints to 6 versioned tables.
    These constraints prevent overlapping date ranges using GIST indexes.

    Authority: dev-docs/db-design/aevofab-db-schema-v2.6h.json
    Task: Phase 4.5 Task 10 - Missing Temporal Exclusion Constraints
    """

    # Enable btree_gist extension (required for EXCLUDE constraints with mixed types)
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist;")

    # 1. tenant_markup_version - Prevent overlapping markup versions per tenant+category
    op.execute("""
        ALTER TABLE tenant_markup_version 
        ADD CONSTRAINT tmv_no_overlap 
        EXCLUDE USING GIST (
          tenant_id WITH =,
          job_expense_category_code WITH =,
          valid_period WITH &&
        );
    """)

    # 2. supplier_item_price - Prevent overlapping price periods per supplier+tenant
    op.execute("""
        ALTER TABLE supplier_item_price 
        ADD CONSTRAINT sip_no_overlap_per_tenant 
        EXCLUDE USING GIST (
          supplier_item_id WITH =,
          tenant_id WITH =,
          valid_period WITH &&
        );
    """)

    # 3. tax_rate_version - Prevent overlapping tax rate versions per jurisdiction
    op.execute("""
        ALTER TABLE tax_rate_version 
        ADD CONSTRAINT tax_rate_version_no_overlap 
        EXCLUDE USING GIST (
          jurisdiction_code WITH =,
          valid_period WITH &&
        );
    """)

    # 4. pricebook_item_version - Prevent overlapping pricebook versions
    op.execute("""
        ALTER TABLE pricebook_item_version 
        ADD CONSTRAINT piv_no_overlap 
        EXCLUDE USING GIST (
          pricebook_item_id WITH =,
          valid_period WITH &&
        );
    """)

    # 5. product_plan_version - Prevent overlapping SaaS plan versions
    op.execute("""
        ALTER TABLE product_plan_version 
        ADD CONSTRAINT product_plan_version_no_overlap 
        EXCLUDE USING GIST (
          product_plan_code WITH =,
          valid_period WITH &&
        );
    """)

    # 6. product_plan_product_feature_version - Prevent overlapping feature versions
    op.execute("""
        ALTER TABLE product_plan_product_feature_version 
        ADD CONSTRAINT pppfv_no_overlap 
        EXCLUDE USING GIST (
          product_plan_code WITH =,
          product_feature_code WITH =,
          valid_period WITH &&
        );
    """)


def downgrade() -> None:
    """
    Remove temporal exclusion constraints.
    Note: Does NOT drop btree_gist extension (may be used elsewhere).
    """

    # Drop constraints in reverse order
    op.execute(
        "ALTER TABLE product_plan_product_feature_version DROP CONSTRAINT IF EXISTS pppfv_no_overlap;"
    )
    op.execute(
        "ALTER TABLE product_plan_version DROP CONSTRAINT IF EXISTS product_plan_version_no_overlap;"
    )
    op.execute(
        "ALTER TABLE pricebook_item_version DROP CONSTRAINT IF EXISTS piv_no_overlap;"
    )
    op.execute(
        "ALTER TABLE tax_rate_version DROP CONSTRAINT IF EXISTS tax_rate_version_no_overlap;"
    )
    op.execute(
        "ALTER TABLE supplier_item_price DROP CONSTRAINT IF EXISTS sip_no_overlap_per_tenant;"
    )
    op.execute(
        "ALTER TABLE tenant_markup_version DROP CONSTRAINT IF EXISTS tmv_no_overlap;"
    )

    # Note: btree_gist extension intentionally NOT dropped
    # It may be used by other features and is harmless to keep
