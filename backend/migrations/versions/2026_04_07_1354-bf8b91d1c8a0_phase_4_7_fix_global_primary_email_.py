"""phase_4_7_fix_global_primary_email_index_task4

Revision ID: bf8b91d1c8a0
Revises: 68ccc850b4ac
Create Date: 2026-04-07 13:54:07.387322+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bf8b91d1c8a0"
down_revision: str | None = "68ccc850b4ac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Fix ux_global_primary_email index to enforce global email uniqueness.

    BEFORE: Index on user_id (wrong - only prevents one user from having multiple primary emails)
    AFTER: Index on LOWER(value) (correct - prevents multiple users from having same primary email)

    Security Impact:
    - Prevents duplicate primary emails across all users
    - Ensures email-based authentication security (one email = one user)
    - Case-insensitive comparison via LOWER()

    Pre-migration validation confirmed no duplicate primary emails exist in database.
    """
    # Drop the broken index (targets user_id instead of email value)
    op.drop_index("ux_global_primary_email", table_name="user_endpoint", if_exists=True)

    # Create correct index targeting LOWER(value) for case-insensitive global uniqueness
    op.execute(
        sa.text(
            """
        CREATE UNIQUE INDEX ux_global_primary_email
        ON user_endpoint (LOWER(value))
        WHERE channel = 'email' AND is_primary = true
        """
        )
    )


def downgrade() -> None:
    """
    Rollback to broken index (for testing/emergency rollback only).

    WARNING: This recreates the BROKEN index that allows duplicate primary emails.
    Only use for emergency rollback during deployment issues.
    """
    # Drop the correct index
    op.drop_index("ux_global_primary_email", table_name="user_endpoint", if_exists=True)

    # Recreate the broken index (targets user_id - allows duplicate emails)
    op.execute(
        sa.text(
            """
        CREATE UNIQUE INDEX ux_global_primary_email
        ON user_endpoint (user_id)
        WHERE channel = 'email' AND is_primary = true
        """
        )
    )
