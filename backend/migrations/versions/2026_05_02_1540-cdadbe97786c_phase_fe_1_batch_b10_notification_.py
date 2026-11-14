"""phase_fe_1_batch_b10_notification_dispatcher_gate

Revision ID: cdadbe97786c
Revises: ebb44d137b27
Create Date: 2026-05-02 15:40:59

Scope (A58):
  - Update notification_outbox status CheckConstraint to add 'suppressed_by_preferences'
    (new status set by dispatcher when a notification is suppressed by user preference gate)
  - Pattern: drop existing constraint, add updated constraint (DDL in same transaction)

No new tables or columns. Pure constraint update.
"""

from alembic import op

# revision identifiers
revision = "cdadbe97786c"
down_revision = "ebb44d137b27"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop existing status constraint
    op.execute("""
        ALTER TABLE notification_outbox
        DROP CONSTRAINT IF EXISTS notification_outbox_status_chk
    """)

    # Add updated constraint including 'suppressed_by_preferences'
    op.execute("""
        ALTER TABLE notification_outbox
        ADD CONSTRAINT notification_outbox_status_chk
        CHECK (status IN ('pending', 'sent', 'failed', 'canceled', 'suppressed_by_preferences'))
    """)


def downgrade() -> None:
    # Remove the expanded constraint
    op.execute("""
        ALTER TABLE notification_outbox
        DROP CONSTRAINT IF EXISTS notification_outbox_status_chk
    """)

    # Restore the original 4-value constraint
    # Note: any rows with status='suppressed_by_preferences' must be updated first
    op.execute("""
        UPDATE notification_outbox
        SET status = 'canceled'
        WHERE status = 'suppressed_by_preferences'
    """)

    op.execute("""
        ALTER TABLE notification_outbox
        ADD CONSTRAINT notification_outbox_status_chk
        CHECK (status IN ('pending', 'sent', 'failed', 'canceled'))
    """)
