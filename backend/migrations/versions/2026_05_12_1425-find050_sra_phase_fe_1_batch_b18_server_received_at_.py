"""phase_fe_1_batch_b18_server_received_at_offline_tables

FIND-050 (S2 High): Add server_received_at TIMESTAMPTZ NULL to the 5 offline-capable tables.

server_received_at records when the server ingested an offline-captured record.
NULL = record created online in real-time.
Non-NULL = record arrived via offline sync batch; delta vs client_capture_at = latency.

Tables:
  job_time_entry, job_expense, job_attachment, change_order, job_notes

Revision ID: find050_sra
Revises: find169_pk_naming
Create Date: 2026-05-12 14:25:38.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "find050_sra"
down_revision = "find169_pk_naming"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "job_time_entry",
        sa.Column("server_received_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "job_expense",
        sa.Column("server_received_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "job_attachment",
        sa.Column("server_received_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "change_order",
        sa.Column("server_received_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "job_notes",
        sa.Column("server_received_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("job_notes", "server_received_at")
    op.drop_column("change_order", "server_received_at")
    op.drop_column("job_attachment", "server_received_at")
    op.drop_column("job_expense", "server_received_at")
    op.drop_column("job_time_entry", "server_received_at")
