"""phase_4_9_normalize_notification_status_spelling_task3

Revision ID: ad336fcaabf3
Revises: c83e6000040c
Create Date: 2026-04-08 19:35:50.862784+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ad336fcaabf3"
down_revision: str | None = "c83e6000040c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Step 1: Normalize data - British spelling to American spelling
    # (Safety update in case any rows have 'cancelled')
    op.execute("""
        UPDATE notification_outbox
        SET status = 'canceled'
        WHERE status = 'cancelled'
    """)

    # Step 2: Drop old constraint (allows British spelling 'cancelled')
    op.drop_constraint(
        "notification_outbox_status_chk", "notification_outbox", type_="check"
    )

    # Step 3: Add new constraint (requires American spelling 'canceled')
    op.create_check_constraint(
        "notification_outbox_status_chk",
        "notification_outbox",
        "status IN ('pending', 'sent', 'failed', 'canceled')",
    )


def downgrade() -> None:
    # Reverse order: Drop new constraint, add old constraint, reverse data
    op.drop_constraint(
        "notification_outbox_status_chk", "notification_outbox", type_="check"
    )

    op.create_check_constraint(
        "notification_outbox_status_chk",
        "notification_outbox",
        "status IN ('pending', 'sent', 'failed', 'cancelled')",
    )

    # Reverse spelling change
    op.execute("""
        UPDATE notification_outbox
        SET status = 'cancelled'
        WHERE status = 'canceled'
    """)
