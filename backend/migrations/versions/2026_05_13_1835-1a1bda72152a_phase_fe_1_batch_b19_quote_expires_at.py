"""phase_fe_1_batch_b19_quote_expires_at

Revision ID: 1a1bda72152a
Revises: bfec576f6650
Create Date: 2026-05-13 18:35:50.935523+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1a1bda72152a"
down_revision: str | None = "bfec576f6650"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # FIND-096: Add expires_at column for quote auto-expiry task
    # NULL (default) = quote never expires; non-NULL = explicit expiration timestamp
    op.add_column(
        "quote", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True)
    )
    # Index for the expiration task query: SELECT WHERE status='sent' AND expires_at < NOW()
    op.create_index("ix_quote_expires_at", "quote", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_quote_expires_at", table_name="quote")
    op.drop_column("quote", "expires_at")
