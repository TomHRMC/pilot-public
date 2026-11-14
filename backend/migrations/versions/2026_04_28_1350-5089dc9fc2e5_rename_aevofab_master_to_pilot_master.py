"""rename_aevofab_master_to_pilot_master

Revision ID: 5089dc9fc2e5
Revises: 9f3ba313aeb1
Create Date: 2026-04-28 13:50:18.430615+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5089dc9fc2e5"
down_revision: str | None = "9f3ba313aeb1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop old check constraint
    op.drop_constraint("sync_preference_chk", "integration_sync_mapping")

    # Update any existing rows that still carry the old value
    op.execute(
        "UPDATE integration_sync_mapping "
        "SET sync_preference = 'pilot_master' "
        "WHERE sync_preference = 'aevofab_master'"
    )

    # Update server default on the column
    op.execute(
        "ALTER TABLE integration_sync_mapping "
        "ALTER COLUMN sync_preference SET DEFAULT 'pilot_master'"
    )

    # Recreate constraint with the new allowed values
    op.create_check_constraint(
        "sync_preference_chk",
        "integration_sync_mapping",
        "sync_preference IN ('pilot_master', 'external_master', 'bi_directional')",
    )


def downgrade() -> None:
    op.drop_constraint("sync_preference_chk", "integration_sync_mapping")

    op.execute(
        "UPDATE integration_sync_mapping "
        "SET sync_preference = 'aevofab_master' "
        "WHERE sync_preference = 'pilot_master'"
    )

    op.execute(
        "ALTER TABLE integration_sync_mapping "
        "ALTER COLUMN sync_preference SET DEFAULT 'aevofab_master'"
    )

    op.create_check_constraint(
        "sync_preference_chk",
        "integration_sync_mapping",
        "sync_preference IN ('aevofab_master', 'external_master', 'bi_directional')",
    )
