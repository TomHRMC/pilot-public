"""phase_fe_1_batch_b2_voice_session_title_columns

Revision ID: f7483973f4ef
Revises: ac34c70bc60b
Create Date: 2026-05-01 13:06:28.624495+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f7483973f4ef"
down_revision: str | None = "ac34c70bc60b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add title column (nullable, user-overridable)
    op.add_column("conversation_session", sa.Column("title", sa.Text(), nullable=True))

    # Add title_auto_generated flag (default False - user-set titles are frozen)
    op.add_column(
        "conversation_session",
        sa.Column(
            "title_auto_generated",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )

    # Add archived_at timestamp for session archival
    op.add_column(
        "conversation_session",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create partial index for querying unexported sessions
    op.create_index(
        "ix_conversation_session_archived_at",
        "conversation_session",
        ["archived_at"],
        postgresql_where=sa.text("archived_at IS NOT NULL"),
    )


def downgrade() -> None:
    # Drop index first
    op.drop_index(
        "ix_conversation_session_archived_at", table_name="conversation_session"
    )

    # Drop columns
    op.drop_column("conversation_session", "archived_at")
    op.drop_column("conversation_session", "title_auto_generated")
    op.drop_column("conversation_session", "title")
