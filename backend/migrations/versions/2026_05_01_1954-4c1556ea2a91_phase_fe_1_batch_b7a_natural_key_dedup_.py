"""phase_fe_1_batch_b7a_natural_key_dedup_indexes

Revision ID: 4c1556ea2a91
Revises: 27e4f60aebd1
Create Date: 2026-05-01 19:54:54

B7a/A39: Create natural-key dedup performance indexes supporting the
7-day/30-day offline dedup window in utils/idempotency.py.

Without these indexes, check_natural_key_dedup() queries become full table
scans. These are the performance backstop for the offline-sync safety net.

Indexes created:
  - ix_jte_natural_key_dedup          on job_time_entry (user_id, job_id, started_at)
  - ix_job_expense_natural_key_dedup  on job_expense (user_id, job_id, incurred_at, cost_cents)
  - ix_job_notes_natural_key_dedup    on job_notes (created_by, job_id, created_at)
  - ix_job_attachment_natural_key_dedup on job_attachment (created_by, job_id, created_at)
  - ix_job_attachment_file_hash       partial index on job_attachment (created_by, job_id, file_hash)
                                      WHERE file_hash IS NOT NULL
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "4c1556ea2a91"
down_revision = "27e4f60aebd1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Time entry natural key: (user_id, job_id, started_at) — 7-day window
    op.create_index(
        "ix_jte_natural_key_dedup",
        "job_time_entry",
        ["user_id", "job_id", "started_at"],
    )

    # Expense natural key: (user_id→created_by, job_id, incurred_at, cost_cents) — 7-day window
    # Note: job_expense has no user_id; uses created_by as author FK for dedup
    op.create_index(
        "ix_job_expense_natural_key_dedup",
        "job_expense",
        ["job_id", "incurred_at", "cost_cents"],
    )

    # Job notes natural key: (created_by, job_id, created_at) — 7-day window
    op.create_index(
        "ix_job_notes_natural_key_dedup",
        "job_notes",
        ["created_by", "job_id", "created_at"],
    )

    # Job attachment photo natural key: (created_by, job_id, created_at) — 30-day window
    op.create_index(
        "ix_job_attachment_natural_key_dedup",
        "job_attachment",
        ["created_by", "job_id", "created_at"],
    )

    # Job attachment file hash partial index (§F.3 strong dedup) — only when file_hash IS NOT NULL
    op.create_index(
        "ix_job_attachment_file_hash",
        "job_attachment",
        ["created_by", "job_id", "file_hash"],
        postgresql_where=sa.text("file_hash IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_job_attachment_file_hash", table_name="job_attachment")
    op.drop_index("ix_job_attachment_natural_key_dedup", table_name="job_attachment")
    op.drop_index("ix_job_notes_natural_key_dedup", table_name="job_notes")
    op.drop_index("ix_job_expense_natural_key_dedup", table_name="job_expense")
    op.drop_index("ix_jte_natural_key_dedup", table_name="job_time_entry")
