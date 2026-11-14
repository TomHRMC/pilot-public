"""add_jurisdiction_code_to_site

Revision ID: a2c82e3c9940
Revises: ac82a4136aaf
Create Date: 2026-03-17 16:22:15.154340+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2c82e3c9940"
down_revision: str | None = "ac82a4136aaf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add jurisdiction_code field to site table for tax calculation
    op.add_column(
        "site",
        sa.Column(
            "jurisdiction_code", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
    )


def downgrade() -> None:
    # Remove jurisdiction_code field from site table
    op.drop_column("site", "jurisdiction_code")
