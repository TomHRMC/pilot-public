"""phase_fe_1_batch_b18_conv_session_status_add_expired_archived

FIND-112 (S2 High) — Add 'expired' and 'archived' to conversation_session.status CHECK.

Previous: status IN ('active', 'ended', 'abandoned')
After:    status IN ('active', 'ended', 'abandoned', 'expired', 'archived')

Revision ID: cb7cb238d2c3
Revises: 1e0785ece81a
Create Date: 2026-05-12 18:02:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "cb7cb238d2c3"
down_revision = "1e0785ece81a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("conv_session_status_chk", "conversation_session", type_="check")
    op.create_check_constraint(
        "conv_session_status_chk",
        "conversation_session",
        "status IN ('active', 'ended', 'abandoned', 'expired', 'archived')",
    )


def downgrade() -> None:
    op.drop_constraint("conv_session_status_chk", "conversation_session", type_="check")
    op.create_check_constraint(
        "conv_session_status_chk",
        "conversation_session",
        "status IN ('active', 'ended', 'abandoned')",
    )
