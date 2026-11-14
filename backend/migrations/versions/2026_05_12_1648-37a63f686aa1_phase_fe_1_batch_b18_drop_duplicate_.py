"""phase_fe_1_batch_b18_drop_duplicate_user_endpoint_indexes

FIND-067 (S4 Low) — Drop 2 duplicate partial unique indexes on user_endpoint.

Duplicates being dropped:
  - idx_user_endpoint_primary_email (user_id WHERE channel='email' AND is_primary=true)
    → exact duplicate of ux_user_email_primary
  - idx_user_endpoint_email_value_lower (lower(value) WHERE channel='email' AND is_primary=true)
    → exact duplicate of ux_global_primary_email

Canonical indexes retained (created in earlier phase migrations):
  - ux_user_email_primary
  - ux_global_primary_email

Revision ID: 37a63f686aa1
Revises: bb2c8fd5f1de
Create Date: 2026-05-12 16:48:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "37a63f686aa1"
down_revision = "bb2c8fd5f1de"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index(
        "idx_user_endpoint_primary_email",
        table_name="user_endpoint",
        if_exists=True,
    )
    op.drop_index(
        "idx_user_endpoint_email_value_lower",
        table_name="user_endpoint",
        if_exists=True,
    )


def downgrade() -> None:
    # Recreate the dropped indexes (restore to pre-FIND-067 state)
    op.create_index(
        "idx_user_endpoint_primary_email",
        "user_endpoint",
        ["user_id"],
        unique=True,
        postgresql_where="channel='email' AND is_primary = true",
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_user_endpoint_email_value_lower "
        "ON user_endpoint (lower(value)) "
        "WHERE channel='email' AND is_primary = true"
    )
