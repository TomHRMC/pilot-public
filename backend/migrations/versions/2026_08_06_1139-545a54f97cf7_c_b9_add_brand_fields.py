"""c_b9_add_brand_fields

Revision ID: 545a54f97cf7
Revises: 025ac61ea0a6
Create Date: 2026-08-06 11:39:37.431453+00:00

C-B9 Task 1: Add 3 nullable brand registration fields to tenant_10dlc_profile.

Per design doc §B.1:
  - website      TEXT — required by TCR for brand registration (validated at app layer)
  - stock_symbol TEXT — only for publicly traded companies (rare for electrician ICP)
  - vertical     TEXT — business category/use case (e.g. "ELECTRICIAN", "CONTRACTOR")

All 3 columns are intentionally nullable. `website` is required at the application
layer when the tenant submits the provisioning form, not at the DB level, because
the field may be auto-populated from C-SPIKE-2's compliance page in the future.

No data migration needed — no existing rows depend on these columns.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "545a54f97cf7"
down_revision: str | None = "025ac61ea0a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    op.add_column(
        "tenant_10dlc_profile", sa.Column("website", sa.Text(), nullable=True)
    )
    op.add_column(
        "tenant_10dlc_profile", sa.Column("stock_symbol", sa.Text(), nullable=True)
    )
    op.add_column(
        "tenant_10dlc_profile", sa.Column("vertical", sa.Text(), nullable=True)
    )

    op.execute("SET LOCAL session_replication_role = 'origin';")


def downgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    op.drop_column("tenant_10dlc_profile", "vertical")
    op.drop_column("tenant_10dlc_profile", "stock_symbol")
    op.drop_column("tenant_10dlc_profile", "website")

    op.execute("SET LOCAL session_replication_role = 'origin';")
