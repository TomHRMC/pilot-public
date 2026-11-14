"""phase_fe_1_batch_b6_calendar_conflict_diff_payload

Revision ID: 41c1340bfa7e
Revises: 87ee9cc8049d
Create Date: 2026-05-01 18:36:00.000000

B6/A32: Add diff-payload columns to calendar_sync_conflict.

New columns:
  - conflict_type TEXT NOT NULL DEFAULT 'modified_modified'
  - base_snapshot JSONB NULL
  - pilot_modified_by_user_id UUID NULL → user.id SET NULL
  - pilot_modified_at TIMESTAMPTZ NOT NULL (backfilled from created_at)
  - external_modified_at TIMESTAMPTZ NOT NULL (backfilled from created_at)
  - urgency_score INTEGER NULL
  - auto_resolved_stale BOOLEAN NOT NULL DEFAULT false

Check constraints:
  - ck_csc_conflict_type: conflict_type IN ('modified_modified','deleted_modified','modified_deleted')
  - ck_resolution expanded to 6 resolution variants

New index:
  - idx_csc_urgency_pending on (tenant_id, urgency_score DESC NULLS LAST) WHERE resolution IS NULL
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "41c1340bfa7e"
down_revision: str | None = "87ee9cc8049d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ----------------------------------------------------------------
    # 1. conflict_type: add nullable, backfill, lock NOT NULL, add CHECK
    # ----------------------------------------------------------------
    op.add_column(
        "calendar_sync_conflict",
        sa.Column("conflict_type", sa.Text(), nullable=True),
    )
    op.execute(
        "UPDATE calendar_sync_conflict SET conflict_type = 'modified_modified' "
        "WHERE conflict_type IS NULL"
    )
    op.alter_column("calendar_sync_conflict", "conflict_type", nullable=False)
    op.execute(
        "ALTER TABLE calendar_sync_conflict ADD CONSTRAINT ck_csc_conflict_type "
        "CHECK (conflict_type IN ('modified_modified','deleted_modified','modified_deleted'))"
    )

    # ----------------------------------------------------------------
    # 2. base_snapshot: nullable JSONB
    # ----------------------------------------------------------------
    op.add_column(
        "calendar_sync_conflict",
        sa.Column("base_snapshot", postgresql.JSONB(), nullable=True),
    )

    # ----------------------------------------------------------------
    # 3. pilot_modified_by_user_id: nullable UUID FK → user.id SET NULL
    # ----------------------------------------------------------------
    op.add_column(
        "calendar_sync_conflict",
        sa.Column("pilot_modified_by_user_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_csc_pilot_modified_by",
        "calendar_sync_conflict",
        "user",
        ["pilot_modified_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ----------------------------------------------------------------
    # 4. pilot_modified_at: add nullable, backfill created_at, lock NOT NULL
    # ----------------------------------------------------------------
    op.add_column(
        "calendar_sync_conflict",
        sa.Column("pilot_modified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "UPDATE calendar_sync_conflict SET pilot_modified_at = created_at "
        "WHERE pilot_modified_at IS NULL"
    )
    op.alter_column("calendar_sync_conflict", "pilot_modified_at", nullable=False)

    # ----------------------------------------------------------------
    # 5. external_modified_at: add nullable, backfill created_at, lock NOT NULL
    # ----------------------------------------------------------------
    op.add_column(
        "calendar_sync_conflict",
        sa.Column("external_modified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "UPDATE calendar_sync_conflict SET external_modified_at = created_at "
        "WHERE external_modified_at IS NULL"
    )
    op.alter_column("calendar_sync_conflict", "external_modified_at", nullable=False)

    # ----------------------------------------------------------------
    # 6. urgency_score: nullable INTEGER
    # ----------------------------------------------------------------
    op.add_column(
        "calendar_sync_conflict",
        sa.Column("urgency_score", sa.Integer(), nullable=True),
    )

    # ----------------------------------------------------------------
    # 7. auto_resolved_stale: NOT NULL BOOLEAN DEFAULT false
    # ----------------------------------------------------------------
    op.add_column(
        "calendar_sync_conflict",
        sa.Column(
            "auto_resolved_stale",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )

    # ----------------------------------------------------------------
    # 8. Drop old ck_resolution, add expanded 6-variant constraint
    # ----------------------------------------------------------------
    op.execute(
        "ALTER TABLE calendar_sync_conflict DROP CONSTRAINT IF EXISTS ck_resolution"
    )
    op.execute(
        """
        ALTER TABLE calendar_sync_conflict ADD CONSTRAINT ck_resolution
        CHECK (
            resolution IS NULL OR resolution IN (
                'accept_local',
                'accept_remote',
                'restore_from_calendar',
                'delete_calendar_too',
                'recreate_calendar_event',
                'delete_pilot_job'
            )
        )
        """
    )

    # ----------------------------------------------------------------
    # 9. New index: urgency-sorted pending conflicts per tenant
    # ----------------------------------------------------------------
    op.execute(
        """
        CREATE INDEX idx_csc_urgency_pending
          ON calendar_sync_conflict (tenant_id, urgency_score DESC NULLS LAST)
          WHERE resolution IS NULL
        """
    )


def downgrade() -> None:
    # Drop urgency index
    op.execute("DROP INDEX IF EXISTS idx_csc_urgency_pending")

    # Restore original 2-variant ck_resolution
    op.execute(
        "ALTER TABLE calendar_sync_conflict DROP CONSTRAINT IF EXISTS ck_resolution"
    )
    op.execute(
        "ALTER TABLE calendar_sync_conflict ADD CONSTRAINT ck_resolution "
        "CHECK (resolution IS NULL OR resolution IN ('accept_local', 'accept_remote'))"
    )

    # Drop new columns in reverse order
    op.drop_column("calendar_sync_conflict", "auto_resolved_stale")
    op.drop_column("calendar_sync_conflict", "urgency_score")
    op.drop_column("calendar_sync_conflict", "external_modified_at")
    op.drop_column("calendar_sync_conflict", "pilot_modified_at")
    op.drop_constraint(
        "fk_csc_pilot_modified_by", "calendar_sync_conflict", type_="foreignkey"
    )
    op.drop_column("calendar_sync_conflict", "pilot_modified_by_user_id")
    op.drop_column("calendar_sync_conflict", "base_snapshot")

    # Drop conflict_type constraint + column
    op.execute(
        "ALTER TABLE calendar_sync_conflict DROP CONSTRAINT IF EXISTS ck_csc_conflict_type"
    )
    op.drop_column("calendar_sync_conflict", "conflict_type")
