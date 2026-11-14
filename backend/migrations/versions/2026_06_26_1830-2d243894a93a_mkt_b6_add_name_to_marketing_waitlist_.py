"""mkt_b6_add_name_to_marketing_waitlist_signup

Revision ID: 2d243894a93a
Revises: da7cd01aec0a
Create Date: 2026-06-26 18:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2d243894a93a"
down_revision: str | None = "da7cd01aec0a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # name is nullable — no backfill needed (existing rows have no name)
    op.add_column(
        "marketing_waitlist_signup",
        sa.Column("name", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("marketing_waitlist_signup", "name")
