"""phase_fe_1_batch_b2_conversation_message_structured_content

Revision ID: c3192a4c4a31
Revises: f7483973f4ef
Create Date: 2026-05-01 13:07:28.548219+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3192a4c4a31"
down_revision: str | None = "f7483973f4ef"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add structured_content_json JSONB column for artifact payloads
    op.add_column(
        "conversation_message",
        sa.Column(
            "structured_content_json", sa.dialects.postgresql.JSONB(), nullable=True
        ),
    )


def downgrade() -> None:
    # Drop the column
    op.drop_column("conversation_message", "structured_content_json")
