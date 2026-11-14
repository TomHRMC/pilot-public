"""phase_fe_1_batch_b18_job_expense_markup_pct_required

FIND-061 (S2 High): Tighten job_expense.markup_pct to NOT NULL DEFAULT 0.

Current state:
  - Column is NULLABLE (nullable=True)
  - A permissive CHECK constraint `job_expense_markup_presence_chk` allows either
    markup_pct OR markup_amt_cents to be non-null

Target state after this migration:
  - Backfill: any existing NULL markup_pct → 0 (cost-pass-through / zero markup)
  - Column: ALTER COLUMN markup_pct SET NOT NULL, SET DEFAULT 0
  - Drop: `job_expense_markup_presence_chk` CHECK constraint (superseded by NOT NULL)
  - Note: markup_amt_cents remains optional (NULL-able) — fixed-amount markup use case preserved

Revision ID: e715853ce770
Revises: find050_sra
Create Date: 2026-05-12 16:17:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e715853ce770"
down_revision = "find050_sra"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Part 1: Backfill existing NULL markup_pct rows to 0
    op.execute("UPDATE job_expense SET markup_pct = 0 WHERE markup_pct IS NULL;")

    # Part 2: Tighten column — NOT NULL + DEFAULT 0
    op.alter_column(
        "job_expense",
        "markup_pct",
        nullable=False,
        server_default=sa.text("0"),
    )

    # Part 3: Drop permissive CHECK constraint (no longer needed — NOT NULL alone enforces intent)
    op.drop_constraint(
        "job_expense_markup_presence_chk",
        "job_expense",
        type_="check",
    )


def downgrade() -> None:
    # Restore CHECK constraint
    op.create_check_constraint(
        "job_expense_markup_presence_chk",
        "job_expense",
        "(markup_pct IS NOT NULL) OR (markup_amt_cents IS NOT NULL)",
    )

    # Restore column to nullable, remove server default
    op.alter_column(
        "job_expense",
        "markup_pct",
        nullable=True,
        server_default=None,
    )
