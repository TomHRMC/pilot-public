"""qb_h1_add_display_name_dedup_subtype

QB-H1 Task 5: Add ``display_name_dedup`` to the
``integration_sync_conflict_subtype_chk`` CHECK constraint so the dedup
conflict rows can be inserted.

The existing constraint allows: customer, quote, invoice, expense,
deletion_local, deletion_remote. This migration adds ``display_name_dedup``
to the allowed values list.

Design: dev-docs/architecture-design/batch-designs/batch-qb-h1-design.md §F.4

Revision ID: b1f8b5f00f33
Revises: 3c69652df5d1
Create Date: 2026-08-28 15:30:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "b1f8b5f00f33"
down_revision = "3c69652df5d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the existing constraint and recreate with the new value added.
    op.execute(
        "ALTER TABLE integration_sync_conflict "
        "DROP CONSTRAINT IF EXISTS integration_sync_conflict_subtype_chk;"
    )
    op.execute(
        """
        ALTER TABLE integration_sync_conflict
        ADD CONSTRAINT integration_sync_conflict_subtype_chk
        CHECK (
            conflict_subtype IS NULL
            OR conflict_subtype IN (
                'customer',
                'quote',
                'invoice',
                'expense',
                'deletion_local',
                'deletion_remote',
                'display_name_dedup'
            )
        );
        """
    )


def downgrade() -> None:
    # Revert to the original constraint (without display_name_dedup)
    op.execute(
        "ALTER TABLE integration_sync_conflict "
        "DROP CONSTRAINT IF EXISTS integration_sync_conflict_subtype_chk;"
    )
    op.execute(
        """
        ALTER TABLE integration_sync_conflict
        ADD CONSTRAINT integration_sync_conflict_subtype_chk
        CHECK (
            conflict_subtype IS NULL
            OR conflict_subtype IN (
                'customer',
                'quote',
                'invoice',
                'expense',
                'deletion_local',
                'deletion_remote'
            )
        );
        """
    )
