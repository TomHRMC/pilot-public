"""phase_fe_1_batch_b8_notification_outbox_push_channel

Revision ID: 48798cb37d28
Revises: af263ee99480
Create Date: 2026-05-02 09:28:00.000000

B8/A51: Add 'push' to notification_outbox.channel CHECK constraint.
Current constraint only allows 'email', 'sms', 'in_app'.
This is an additive constraint relaxation — no data migration needed.
"""

from alembic import op

revision: str = "48798cb37d28"
down_revision: str | None = "af263ee99480"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the existing constraint and add the new one with 'push' included
    op.execute("""
        ALTER TABLE notification_outbox
            DROP CONSTRAINT notification_outbox_channel_chk
    """)
    op.execute("""
        ALTER TABLE notification_outbox
            ADD CONSTRAINT notification_outbox_channel_chk
                CHECK (channel IN ('email', 'sms', 'in_app', 'push'))
    """)


def downgrade() -> None:
    # Revert to original 3-value constraint
    # Note: any push-channel rows must be deleted before downgrade
    op.execute("""
        ALTER TABLE notification_outbox
            DROP CONSTRAINT notification_outbox_channel_chk
    """)
    op.execute("""
        ALTER TABLE notification_outbox
            ADD CONSTRAINT notification_outbox_channel_chk
                CHECK (channel IN ('email', 'sms', 'in_app'))
    """)
