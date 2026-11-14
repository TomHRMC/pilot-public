"""phase_4_8_add_communication_indexes_task7

Revision ID: e0ec21bc5919
Revises: 19f40c0e56e0
Create Date: 2026-04-08 16:36:56.015326+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e0ec21bc5919"
down_revision: str | None = "19f40c0e56e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add communication domain composite indexes for conversation threading and notification scheduling."""

    # 1. Conversation message session threading (chronological order)
    op.create_index(
        "idx_conv_msg_session_time",
        "conversation_message",
        ["session_id", sa.text("created_at ASC")],
    )

    # 2. Notification outbox status + scheduling (background worker query)
    op.create_index(
        "idx_notif_outbox_status_sched",
        "notification_outbox",
        ["status", "scheduled_at", "next_attempt_at"],
    )

    # 3. Notification outbox channel + status filtering
    op.create_index(
        "idx_notif_outbox_channel_status", "notification_outbox", ["channel", "status"]
    )

    # 4. Notification outbox provider message ID lookup (delivery callbacks)
    op.create_index(
        "idx_notif_outbox_provider_msg", "notification_outbox", ["provider_message_id"]
    )

    # 5. Notification outbox time-series ordering
    op.create_index(
        "idx_notif_outbox_created_at",
        "notification_outbox",
        [sa.text("created_at DESC")],
    )


def downgrade() -> None:
    """Remove communication domain composite indexes."""
    op.drop_index("idx_notif_outbox_created_at", table_name="notification_outbox")
    op.drop_index("idx_notif_outbox_provider_msg", table_name="notification_outbox")
    op.drop_index("idx_notif_outbox_channel_status", table_name="notification_outbox")
    op.drop_index("idx_notif_outbox_status_sched", table_name="notification_outbox")
    op.drop_index("idx_conv_msg_session_time", table_name="conversation_message")
