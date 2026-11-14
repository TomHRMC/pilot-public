"""phase_fe_1_batch_b18_help_chat_session_activity_index

FIND-127 (S4 Low) — Add composite partial index on help_chat_session for session
history list endpoint performance.

The query at _list_sessions_impl filters:
  WHERE user_id = ? AND tenant_id = ? AND anonymized_at IS NULL
  ORDER BY last_activity_at DESC

Without this index, the query cannot use any existing index efficiently (the 4
existing single-column indexes only partially cover the predicate).

New index enables perfect index-only scan:
  - user_id first (most selective)
  - tenant_id second
  - last_activity_at DESC for the ORDER BY
  - WHERE anonymized_at IS NULL: sessions soft-deleted via FIND-126 drop out automatically

Revision ID: 316581e91652
Revises: 95c8acb7be77
Create Date: 2026-05-12 18:38:32.000000+00:00
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "316581e91652"
down_revision: str | None = "95c8acb7be77"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX ix_help_chat_session_user_tenant_activity
          ON help_chat_session (user_id, tenant_id, last_activity_at DESC)
          WHERE anonymized_at IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_help_chat_session_user_tenant_activity")
