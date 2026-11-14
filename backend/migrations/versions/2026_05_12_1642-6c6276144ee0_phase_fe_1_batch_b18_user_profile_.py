"""phase_fe_1_batch_b18_user_profile_columns

FIND-066 (S2 High) — B18 schema-only: Add 4 nullable profile columns to user table.

Columns added:
  - phone_number VARCHAR NULL — user profile phone; hooks into SMS MFA re-verification (code in B20)
  - time_zone VARCHAR NULL DEFAULT 'America/New_York' — user-overridable time zone
  - profile_photo_s3_key TEXT NULL — S3 key for profile photo (presigned URL upload pattern A41)
  - language_preference VARCHAR NULL DEFAULT 'en' — PRD §3.5-F12; MVP only supports 'en';
    CHECK constraint added now so Phase 2 expansion only requires a constraint change, not a migration.

No code changes in B18 — columns are schema scaffolding for B20, Task 11.

Revision ID: 6c6276144ee0
Revises: e715853ce770
Create Date: 2026-05-12 16:42:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6c6276144ee0"
down_revision = "e715853ce770"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("phone_number", sa.String(), nullable=True),
    )
    op.add_column(
        "user",
        sa.Column(
            "time_zone",
            sa.String(),
            nullable=True,
            server_default=sa.text("'America/New_York'"),
        ),
    )
    op.add_column(
        "user",
        sa.Column("profile_photo_s3_key", sa.Text(), nullable=True),
    )
    op.add_column(
        "user",
        sa.Column(
            "language_preference",
            sa.String(),
            nullable=True,
            server_default=sa.text("'en'"),
        ),
    )
    op.create_check_constraint(
        "user_language_preference_chk",
        "user",
        "language_preference IS NULL OR language_preference IN ('en')",
    )


def downgrade() -> None:
    op.drop_constraint("user_language_preference_chk", "user", type_="check")
    op.drop_column("user", "language_preference")
    op.drop_column("user", "profile_photo_s3_key")
    op.drop_column("user", "time_zone")
    op.drop_column("user", "phone_number")
