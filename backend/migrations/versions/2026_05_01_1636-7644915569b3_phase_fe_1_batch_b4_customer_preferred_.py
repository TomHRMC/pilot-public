"""phase_fe_1_batch_b4_customer_preferred_channel

Revision ID: 7644915569b3
Revises: 16668cf3041e
Create Date: 2026-05-01 16:36:00

Batch B4 — A21: Per-Message Channel Override
Adds preferred_contact_channel column to the customer table.
Default: 'sms' — aligns with MVP assumption that tech-to-customer comms are SMS-first.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "7644915569b3"
down_revision = "16668cf3041e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add preferred_contact_channel as nullable first (safe for existing rows)
    op.execute("""
        ALTER TABLE customer
            ADD COLUMN preferred_contact_channel VARCHAR(10) NOT NULL DEFAULT 'sms'
    """)

    # Add check constraint
    op.execute("""
        ALTER TABLE customer
            ADD CONSTRAINT customer_preferred_contact_channel_chk
                CHECK (preferred_contact_channel IN ('sms', 'email'))
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE customer
            DROP CONSTRAINT IF EXISTS customer_preferred_contact_channel_chk
    """)
    op.execute("""
        ALTER TABLE customer
            DROP COLUMN IF EXISTS preferred_contact_channel
    """)
