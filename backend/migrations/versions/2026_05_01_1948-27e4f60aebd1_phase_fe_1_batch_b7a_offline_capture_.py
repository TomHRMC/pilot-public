"""phase_fe_1_batch_b7a_offline_capture_timestamps

Revision ID: 27e4f60aebd1
Revises: aae2bed9cbe8
Create Date: 2026-05-01 19:48:04

B7a/A37: Add client_capture_at TIMESTAMPTZ NULL to five offline-capturable tables,
and file_hash TEXT NULL to job_attachment for natural-key dedup (§F.3).

Tables modified:
  - job_time_entry   → client_capture_at
  - job_expense      → client_capture_at
  - job_attachment   → client_capture_at, file_hash
  - change_order     → client_capture_at
  - job_notes        → client_capture_at
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "27e4f60aebd1"
down_revision = "aae2bed9cbe8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # job_time_entry
    op.add_column(
        "job_time_entry",
        sa.Column("client_capture_at", sa.DateTime(timezone=True), nullable=True),
    )

    # job_expense
    op.add_column(
        "job_expense",
        sa.Column("client_capture_at", sa.DateTime(timezone=True), nullable=True),
    )

    # job_attachment — both client_capture_at and file_hash (§F.3)
    op.add_column(
        "job_attachment",
        sa.Column("client_capture_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("job_attachment", sa.Column("file_hash", sa.Text(), nullable=True))

    # change_order
    op.add_column(
        "change_order",
        sa.Column("client_capture_at", sa.DateTime(timezone=True), nullable=True),
    )

    # job_notes (architecture name: "job_note")
    op.add_column(
        "job_notes",
        sa.Column("client_capture_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("job_notes", "client_capture_at")
    op.drop_column("change_order", "client_capture_at")
    op.drop_column("job_attachment", "file_hash")
    op.drop_column("job_attachment", "client_capture_at")
    op.drop_column("job_expense", "client_capture_at")
    op.drop_column("job_time_entry", "client_capture_at")
