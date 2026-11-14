"""c_b5_add_messaging_setup_checklist_column

Revision ID: e18834169e23
Revises: 28af5f068549
Create Date: 2026-08-04 18:15:00+00:00

C-B5: Adds the messaging_setup boolean column to tenant_onboarding_checklist.
This column tracks completion of the 10DLC text-messaging setup step
(Charter-only, displayed with cost disclosure in the onboarding checklist).

Single-step safe migration: NOT NULL with server_default=false so existing
rows receive false without a backfill pass.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e18834169e23"
down_revision: str | None = "28af5f068549"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.add_column(
        "tenant_onboarding_checklist",
        sa.Column(
            "messaging_setup",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.execute("SET LOCAL session_replication_role = 'origin';")


def downgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.drop_column("tenant_onboarding_checklist", "messaging_setup")
    op.execute("SET LOCAL session_replication_role = 'origin';")
