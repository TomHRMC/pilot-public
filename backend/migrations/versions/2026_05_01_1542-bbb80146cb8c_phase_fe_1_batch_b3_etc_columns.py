"""phase_fe_1_batch_b3_etc_columns

Revision ID: bbb80146cb8c
Revises: bd3adc4cfa16
Create Date: 2026-05-01 15:42:22.000000

B3/A14: Add ETC (Estimate-to-Complete) columns to job_time_entry.
F2 resolution: use ledger column names + add etc_captured_at (arch addition).

New columns (all nullable — no backfill required):
  hours_remaining_estimate    NUMERIC(6,2)
  hours_remaining_was_overridden BOOLEAN
  override_note               TEXT
  quote_line_id               UUID → quote_line.id RESTRICT
  etc_captured_at             TIMESTAMPTZ

Indexes:
  ix_jte_quote_line_id             on (quote_line_id)
  ix_jte_etc_not_null (partial)    on (job_id, quote_line_id, created_at DESC)
                                   WHERE hours_remaining_estimate IS NOT NULL
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bbb80146cb8c"
down_revision: str | None = "bd3adc4cfa16"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # All nullable — no backfill required
    op.add_column(
        "job_time_entry",
        sa.Column("hours_remaining_estimate", sa.Numeric(6, 2), nullable=True),
    )
    op.add_column(
        "job_time_entry",
        sa.Column("hours_remaining_was_overridden", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "job_time_entry",
        sa.Column("override_note", sa.Text(), nullable=True),
    )
    op.add_column(
        "job_time_entry",
        sa.Column("quote_line_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "job_time_entry",
        sa.Column("etc_captured_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Foreign key: quote_line_id → quote_line.id RESTRICT
    op.create_foreign_key(
        "fk_jte_quote_line",
        "job_time_entry",
        "quote_line",
        ["quote_line_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # Index on quote_line_id for per-task ETC queries
    op.create_index("ix_jte_quote_line_id", "job_time_entry", ["quote_line_id"])

    # Partial index — latest-ETC query pattern
    op.execute(
        """
        CREATE INDEX ix_jte_etc_not_null
        ON job_time_entry (job_id, quote_line_id, created_at DESC)
        WHERE hours_remaining_estimate IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_jte_etc_not_null")
    op.drop_index("ix_jte_quote_line_id", table_name="job_time_entry")
    op.drop_constraint("fk_jte_quote_line", "job_time_entry", type_="foreignkey")
    op.drop_column("job_time_entry", "etc_captured_at")
    op.drop_column("job_time_entry", "quote_line_id")
    op.drop_column("job_time_entry", "override_note")
    op.drop_column("job_time_entry", "hours_remaining_was_overridden")
    op.drop_column("job_time_entry", "hours_remaining_estimate")
