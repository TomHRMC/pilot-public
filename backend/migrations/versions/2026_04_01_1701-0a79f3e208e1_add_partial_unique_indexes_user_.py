"""add_partial_unique_indexes_user_endpoint_task12

Revision ID: 0a79f3e208e1
Revises: 3fb234f4af72
Create Date: 2026-04-01 17:01:47.784776+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0a79f3e208e1"
down_revision: str | None = "3fb234f4af72"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create partial unique indexes on user_endpoint for primary contact logic"""

    # CONCURRENTLY requires running outside transaction block
    # Get connection and commit any existing transaction
    conn = op.get_bind()

    # Close the current transaction to allow CONCURRENTLY operations
    if conn.in_transaction():
        conn.commit()

    # Set connection to autocommit mode for CONCURRENTLY operations
    conn.connection.set_isolation_level(0)  # AUTOCOMMIT

    try:
        # Gap 1: ux_user_email_primary - Only one primary email per user
        # Enforces "Highlander rule" at database level for email endpoints
        # Prevents multiple emails marked as is_primary=true for same user_id
        conn.execute(
            sa.text(
                "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS ux_user_email_primary "
                "ON user_endpoint (user_id) "
                "WHERE channel = 'email' AND is_primary = true"
            )
        )

        # Gap 2: ux_global_primary_email - Only one primary endpoint of ANY type per user
        # Enforces "Highlander rule" across ALL channels (email, phone, sms)
        # Prevents user from having both primary email AND primary phone simultaneously
        conn.execute(
            sa.text(
                "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS ux_global_primary_email "
                "ON user_endpoint (user_id) "
                "WHERE is_primary = true"
            )
        )
    finally:
        # Restore default isolation level (READ COMMITTED)
        conn.connection.set_isolation_level(1)


def downgrade() -> None:
    """Drop partial unique indexes"""

    # CONCURRENTLY requires running outside transaction block
    # Get connection and commit any existing transaction
    conn = op.get_bind()

    # Close the current transaction to allow CONCURRENTLY operations
    if conn.in_transaction():
        conn.commit()

    # Set connection to autocommit mode for CONCURRENTLY operations
    conn.connection.set_isolation_level(0)  # AUTOCOMMIT

    try:
        # Drop ux_global_primary_email
        conn.execute(
            sa.text("DROP INDEX CONCURRENTLY IF EXISTS ux_global_primary_email")
        )

        # Drop ux_user_email_primary
        conn.execute(sa.text("DROP INDEX CONCURRENTLY IF EXISTS ux_user_email_primary"))
    finally:
        # Restore default isolation level (READ COMMITTED)
        conn.connection.set_isolation_level(1)
