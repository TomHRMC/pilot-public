"""phase_fe_1_batch_b18_conv_session_context_window_not_null

FIND-113 (S4 Low) — context_window_json NOT NULL + DEFAULT '{}'.

Action:
  1. Backfill NULL rows to '{}'
  2. SET NOT NULL
  3. SET DEFAULT '{}'::jsonb

Revision ID: e9a634b4d799
Revises: cb7cb238d2c3
Create Date: 2026-05-12 18:02:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "e9a634b4d799"
down_revision = "cb7cb238d2c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Part 1: Backfill NULL rows
    op.execute(
        "UPDATE conversation_session "
        "SET context_window_json = '{}'::jsonb "
        "WHERE context_window_json IS NULL"
    )

    # Part 2: Tighten to NOT NULL + set server default
    op.alter_column(
        "conversation_session",
        "context_window_json",
        nullable=False,
        server_default=sa.text("'{}'::jsonb"),
        existing_type=JSONB,
    )


def downgrade() -> None:
    op.alter_column(
        "conversation_session",
        "context_window_json",
        nullable=True,
        server_default=None,
        existing_type=JSONB,
    )
