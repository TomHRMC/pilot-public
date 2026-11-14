"""phase_4_8_add_quote_indexes_task3

Revision ID: 78ef573fb944
Revises: 6ed2a5c08eb4
Create Date: 2026-04-08 14:09:38.967905+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "78ef573fb944"
down_revision: str | None = "6ed2a5c08eb4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add composite index for tenant-scoped quote list queries with status filtering
    # Query pattern: WHERE tenant_id = '...' AND status_id = '...' ORDER BY created_at DESC
    op.create_index(
        "idx_quote_tenant_status_created_at",
        "quote",
        ["tenant_id", "status_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    # Remove composite index
    op.drop_index("idx_quote_tenant_status_created_at", table_name="quote")
