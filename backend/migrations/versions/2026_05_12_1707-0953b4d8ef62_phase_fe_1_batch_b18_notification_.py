"""phase_fe_1_batch_b18_notification_channel_seed

FIND-077 (S2 High) — Seed notification_channel with 4 MVP rows; replace
notification_outbox.channel CHECK constraint with FK to notification_channel.code.

Actions:
  1. Seed notification_channel: email, sms, push, in_app
  2. DROP notification_outbox_channel_chk CHECK constraint
  3. ADD FK fk_outbox_channel → notification_channel(code) ON DELETE RESTRICT

Note: voice channel deferred to Phase 2 per Tom's decision 2026-05-08.
existing notification_outbox rows only contain 'email', 'sms', 'in_app' —
all valid after FK is enforced.

Revision ID: 0953b4d8ef62
Revises: 5d46297ce425
Create Date: 2026-05-12 17:07:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0953b4d8ef62"
down_revision = "5d46297ce425"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Part 1: Seed the 4 MVP notification channels (idempotent — IF NOT EXISTS via ON CONFLICT DO NOTHING)
    op.execute("""
        INSERT INTO notification_channel (code, name, is_active, created_at, updated_at)
        VALUES
            ('email',  'Email',         true, now(), now()),
            ('sms',    'SMS',           true, now(), now()),
            ('push',   'Push',          true, now(), now()),
            ('in_app', 'In-App Banner', true, now(), now())
        ON CONFLICT (code) DO NOTHING
    """)

    # Part 2: Drop permissive CHECK constraint (superseded by FK)
    op.drop_constraint(
        "notification_outbox_channel_chk",
        "notification_outbox",
        type_="check",
    )

    # Part 3: Add FK — proper relational enforcement; new channels require only a seed row
    op.create_foreign_key(
        "fk_outbox_channel",
        "notification_outbox",
        "notification_channel",
        ["channel"],
        ["code"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    # Remove FK
    op.drop_constraint("fk_outbox_channel", "notification_outbox", type_="foreignkey")

    # Restore CHECK constraint
    op.create_check_constraint(
        "notification_outbox_channel_chk",
        "notification_outbox",
        "channel IN ('email','sms','in_app')",
    )

    # Remove seeded rows (only if they have no dependents — safe for downgrade)
    op.execute("""
        DELETE FROM notification_channel
        WHERE code IN ('email', 'sms', 'push', 'in_app')
          AND NOT EXISTS (
            SELECT 1 FROM notification_outbox
            WHERE notification_outbox.channel = notification_channel.code
          )
    """)
