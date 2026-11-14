"""phase_fe_1_batch_b15_sync_indicator_setting

Revision ID: 220cfa33d815
Revises: ddae94e9c3e9
Create Date: 2026-05-03 13:32:12.000000

B15/A79: Add tenant_sync_indicator_pending_amber_threshold column to tenant_settings.
This column stores per-tenant amber threshold overrides for the sync indicator widget.
The three-tier resolver (B9/A53) reads this column and falls back to system default (5)
if NULL. Since this column has a server_default of 5 and is NOT NULL, all existing rows
are auto-backfilled by the server_default during ALTER TABLE.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "220cfa33d815"
down_revision = "ddae94e9c3e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Simple additive NOT NULL column with server_default — no 3-part pattern needed
    # (server_default handles existing rows atomically in Postgres)
    op.add_column(
        "tenant_settings",
        sa.Column(
            "tenant_sync_indicator_pending_amber_threshold",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("5"),
        ),
    )


def downgrade() -> None:
    op.drop_column("tenant_settings", "tenant_sync_indicator_pending_amber_threshold")
