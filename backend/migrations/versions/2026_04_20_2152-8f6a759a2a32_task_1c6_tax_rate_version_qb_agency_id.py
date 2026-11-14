"""task_1c6_tax_rate_version_qb_agency_id

Revision ID: 8f6a759a2a32
Revises: 1f929341eeb1
Create Date: 2026-04-20 21:52:29.000000

Task 1-C-6: Add `external_tax_agency_id` (VARCHAR(100), nullable) to `tax_rate_version`.

This column stores the QuickBooks Online Tax Agency identifier corresponding to
each AevoFab tax jurisdiction. Without this, the QB sync service cannot route
tax amounts to the correct QB liability account, causing tax remittance errors
in the contractor's QuickBooks books.

Column is nullable — existing tax rate versions will have NULL until the QB
sync service maps them via the integrations UI or sync script.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8f6a759a2a32"
down_revision = "1f929341eeb1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add external_tax_agency_id: VARCHAR(100) nullable
    # Stores the QB Online Tax Agency ID (e.g., "TAX_AGENCY_1", "QB:TaxCode:US-TX-HARRIS")
    op.add_column(
        "tax_rate_version",
        sa.Column("external_tax_agency_id", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tax_rate_version", "external_tax_agency_id")
