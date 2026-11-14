"""convert_user_email_to_citext

Revision ID: c748980dbeee
Revises: cf20e60ce5f3
Create Date: 2026-03-31 17:33:37.446592+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c748980dbeee"
down_revision: str | None = "cf20e60ce5f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Pre-migration data cleanup: Convert all emails to lowercase
    op.execute('UPDATE "user" SET email = LOWER(email);')

    # Check for case-insensitive duplicate emails (should be zero)
    conn = op.get_bind()
    result = conn.execute(
        sa.text("""
        SELECT LOWER(email) as lowercase_email, COUNT(*) as count
        FROM "user"
        GROUP BY LOWER(email)
        HAVING COUNT(*) > 1
    """)
    )
    duplicates = result.fetchall()

    if duplicates:
        raise Exception(
            f"Cannot proceed with citext conversion: Found {len(duplicates)} case-insensitive duplicate emails. "
            f"Please manually resolve duplicates before running this migration. "
            f"Duplicates: {[row[0] for row in duplicates]}"
        )

    # Convert email column from VARCHAR to CITEXT for case-insensitive uniqueness
    op.alter_column(
        "user",
        "email",
        existing_type=sa.VARCHAR(),
        type_=postgresql.CITEXT(),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Revert email column from CITEXT back to VARCHAR
    op.alter_column(
        "user",
        "email",
        existing_type=postgresql.CITEXT(),
        type_=sa.VARCHAR(),
        existing_nullable=False,
    )
