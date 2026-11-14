"""phase_4_7_enum_to_text_preferred_mfa_channel_task2

Revision ID: 8b2fc717cee6
Revises: 6b15b78db845
Create Date: 2026-04-04 00:03:11.581081+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "8b2fc717cee6"
down_revision: str | None = "6b15b78db845"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Convert user.preferred_mfa_channel from PostgreSQL ENUM to TEXT with CHECK constraint.

    Pre-migration validation (already run via postgres-local MCP):
    - SELECT id, email, preferred_mfa_channel FROM "user"
      WHERE preferred_mfa_channel NOT IN ('email', 'sms', 'totp')
        AND preferred_mfa_channel IS NOT NULL;
    - Result: 0 rows (all data is valid)
    - SELECT preferred_mfa_channel, COUNT(*) FROM "user" GROUP BY preferred_mfa_channel;
    - Result: 1 user with 'email'
    """
    # Step 1: Add temporary CHECK constraint (nullable allowed)
    op.execute("""
        ALTER TABLE "user"
        ADD CONSTRAINT user_preferred_mfa_channel_chk_temp
        CHECK (
          preferred_mfa_channel IS NULL OR
          preferred_mfa_channel::text IN ('email', 'sms', 'totp')
        )
    """)

    # Step 2: Convert column from ENUM to TEXT (with nullable)
    op.alter_column(
        "user",
        "preferred_mfa_channel",
        existing_type=postgresql.ENUM(
            "email", "sms", "totp", name="preferredmfachannel"
        ),
        type_=sa.Text(),
        existing_nullable=False,
        nullable=True,
        postgresql_using="preferred_mfa_channel::text",
    )

    # Step 3: Drop the ENUM type (CASCADE to handle any dependencies)
    op.execute("DROP TYPE IF EXISTS public.preferredmfachannel CASCADE")

    # Step 4: Replace temporary constraint with final version
    op.execute("""
        ALTER TABLE "user"
        DROP CONSTRAINT user_preferred_mfa_channel_chk_temp
    """)

    op.create_check_constraint(
        "user_preferred_mfa_channel_chk",
        "user",
        "preferred_mfa_channel IS NULL OR preferred_mfa_channel IN ('email', 'sms', 'totp')",
    )


def downgrade() -> None:
    """
    Revert user.preferred_mfa_channel from TEXT back to PostgreSQL ENUM.

    WARNING: This will fail if any new channel values were added beyond 'email', 'sms', 'totp'.
    """
    # Step 1: Drop the CHECK constraint
    op.drop_constraint("user_preferred_mfa_channel_chk", "user", type_="check")

    # Step 2: Recreate the ENUM type
    op.execute(
        "CREATE TYPE public.preferredmfachannel AS ENUM ('email', 'sms', 'totp')"
    )

    # Step 3: Convert column from TEXT back to ENUM (set nullable=False, default='email')
    # First set a default for NULL values
    op.execute("""
        UPDATE "user" 
        SET preferred_mfa_channel = 'email' 
        WHERE preferred_mfa_channel IS NULL
    """)

    op.alter_column(
        "user",
        "preferred_mfa_channel",
        existing_type=sa.Text(),
        type_=postgresql.ENUM("email", "sms", "totp", name="preferredmfachannel"),
        nullable=False,
        postgresql_using="preferred_mfa_channel::public.preferredmfachannel",
    )
