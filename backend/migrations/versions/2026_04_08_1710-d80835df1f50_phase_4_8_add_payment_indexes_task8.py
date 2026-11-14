"""phase_4_8_add_payment_indexes_task8

Revision ID: d80835df1f50
Revises: e0ec21bc5919
Create Date: 2026-04-08 17:10:59.657445+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d80835df1f50"
down_revision: str | None = "e0ec21bc5919"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Payment transaction log tenant-scoped time ordering
    # Optimizes queries: WHERE tenant_id = '...' ORDER BY created_at DESC
    op.create_index(
        "idx_psp_tx_log_tenant_time",
        "psp_transaction_log",
        ["tenant_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("idx_psp_tx_log_tenant_time", table_name="psp_transaction_log")
