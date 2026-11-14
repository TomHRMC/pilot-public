"""phase_4_8_add_billing_indexes_task4

Revision ID: 32576bae5ff3
Revises: 78ef573fb944
Create Date: 2026-04-08 15:26:41.157048+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "32576bae5ff3"
down_revision: str | None = "78ef573fb944"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add 5 billing domain composite indexes for query performance optimization"""

    # Index 1: Invoice status + due date filtering
    # Pattern: WHERE status_id = '...' AND due_at < NOW() ORDER BY due_at
    op.create_index("idx_invoice_status_due_at", "invoice", ["status_id", "due_at"])

    # Index 2: Invoice time-series ordering
    # Pattern: ORDER BY created_at DESC (invoice list view)
    op.create_index("idx_invoice_created_at", "invoice", [sa.text("created_at DESC")])

    # Index 3: Subscription usage composite
    # Pattern: WHERE subscription_id = '...' AND product_feature_code = '...' ORDER BY period_end DESC
    op.create_index(
        "idx_su_tenant_product_feature_period",
        "subscription_usage",
        ["subscription_id", "product_feature_code", sa.text("period_end DESC")],
    )

    # Index 4: Usage ledger time-series
    # Pattern: WHERE subscription_id = '...' AND product_feature_code = '...' ORDER BY occurred_at DESC
    op.create_index(
        "idx_ul_subscription_product_feature_time",
        "usage_ledger",
        ["subscription_id", "product_feature_code", sa.text("occurred_at DESC")],
    )

    # Index 5: Partial index for unreported usage (requires op.execute for WHERE clause)
    # Pattern: WHERE tenant_id = '...' AND product_feature_code = '...' AND is_reported = false
    op.execute("""
        CREATE INDEX idx_usage_ledger_unreported
        ON usage_ledger (tenant_id, product_feature_code, is_reported)
        WHERE is_reported = false
    """)


def downgrade() -> None:
    """Remove billing domain composite indexes"""
    op.drop_index("idx_usage_ledger_unreported", table_name="usage_ledger")
    op.drop_index("idx_ul_subscription_product_feature_time", table_name="usage_ledger")
    op.drop_index(
        "idx_su_tenant_product_feature_period", table_name="subscription_usage"
    )
    op.drop_index("idx_invoice_created_at", table_name="invoice")
    op.drop_index("idx_invoice_status_due_at", table_name="invoice")
