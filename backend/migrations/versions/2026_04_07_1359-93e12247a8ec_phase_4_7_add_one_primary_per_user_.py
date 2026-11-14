"""phase_4_7_add_one_primary_per_user_constraint

Revision ID: 93e12247a8ec
Revises: bf8b91d1c8a0
Create Date: 2026-04-07 13:59:37.557848+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "93e12247a8ec"
down_revision: str | None = "bf8b91d1c8a0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Add constraint to ensure only one primary endpoint per user (any channel).

    This replaces the functionality that was lost when we changed ux_global_primary_email
    from WHERE is_primary = true (any channel) to WHERE channel = 'email' AND is_primary = true.

    Business Rule: A user can only have ONE primary contact method at a time
    (either primary email OR primary phone, but not both).
    """
    # Create index to ensure only one primary endpoint per user across all channels
    op.execute(
        sa.text(
            """
        CREATE UNIQUE INDEX ux_one_primary_per_user 
        ON user_endpoint (user_id) 
        WHERE is_primary = true
        """
        )
    )


def downgrade() -> None:
    """
    Remove the one-primary-per-user constraint.
    """
    op.drop_index("ux_one_primary_per_user", table_name="user_endpoint", if_exists=True)
