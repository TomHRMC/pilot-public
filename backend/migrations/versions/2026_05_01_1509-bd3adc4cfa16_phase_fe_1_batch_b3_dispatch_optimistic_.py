"""phase_fe_1_batch_b3_dispatch_optimistic_locking

Revision ID: bd3adc4cfa16
Revises: 846f403de076
Create Date: 2026-05-01 15:09:45.000000

B3/A19: Add version column to job and job_tech_assignment for optimistic concurrency.
B3/A19 (F3): Add variance_owner_notified_at and variance_last_notified_pct to job.

3-part pattern for version (NOT NULL with default):
  1. Add nullable
  2. Backfill to 1
  3. Lock NOT NULL with server_default
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bd3adc4cfa16"
down_revision: str | None = "846f403de076"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ----------------------------------------------------------------
    # job.version — 3-part pattern
    # ----------------------------------------------------------------
    # Part 1 — add nullable
    op.add_column("job", sa.Column("version", sa.Integer(), nullable=True))
    op.add_column(
        "job_tech_assignment", sa.Column("version", sa.Integer(), nullable=True)
    )

    # Part 2 — backfill
    op.execute("UPDATE job SET version = 1 WHERE version IS NULL")
    op.execute("UPDATE job_tech_assignment SET version = 1 WHERE version IS NULL")

    # Part 3 — lock NOT NULL with server_default
    op.alter_column("job", "version", nullable=False, server_default=sa.text("1"))
    op.alter_column(
        "job_tech_assignment", "version", nullable=False, server_default=sa.text("1")
    )

    # ----------------------------------------------------------------
    # F3: Variance notification tracking on job — additive nullable
    # ----------------------------------------------------------------
    op.add_column(
        "job",
        sa.Column(
            "variance_owner_notified_at", sa.DateTime(timezone=True), nullable=True
        ),
    )
    op.add_column(
        "job",
        sa.Column("variance_last_notified_pct", sa.Numeric(5, 1), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("job", "variance_last_notified_pct")
    op.drop_column("job", "variance_owner_notified_at")
    op.drop_column("job_tech_assignment", "version")
    op.drop_column("job", "version")
