"""phase_fe_1_batch_b18_invoice_composite_indexes

FIND-074 (S3 Medium) — Add 2 composite indexes on invoice for tenant-scoped queries.

Indexes added:
  - idx_invoice_tenant_status (tenant_id, status_id) — powers invoice list filtered by status
  - idx_invoice_tenant_created_at (tenant_id, created_at DESC) — powers invoice list ordered by date

Revision ID: 5d46297ce425
Revises: 2a06b786eba8
Create Date: 2026-05-12 17:04:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "5d46297ce425"
down_revision = "2a06b786eba8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "idx_invoice_tenant_status",
        "invoice",
        ["tenant_id", "status_id"],
    )
    op.execute(
        "CREATE INDEX idx_invoice_tenant_created_at "
        "ON invoice (tenant_id, created_at DESC)"
    )


def downgrade() -> None:
    op.drop_index("idx_invoice_tenant_created_at", table_name="invoice")
    op.drop_index("idx_invoice_tenant_status", table_name="invoice")
