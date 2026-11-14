"""add_internal_version_token_to_sync_mapping

Revision ID: 40a492ca69ce
Revises: b7da45e9a263
Create Date: 2026-03-22 14:10:53.314315+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "40a492ca69ce"
down_revision: str | None = "b7da45e9a263"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add internal_version_token column to integration_sync_mapping table
    op.add_column(
        "integration_sync_mapping",
        sa.Column("internal_version_token", sa.String(), nullable=True),
    )


def downgrade() -> None:
    # Remove internal_version_token column from integration_sync_mapping table
    op.drop_column("integration_sync_mapping", "internal_version_token")
