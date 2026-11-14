"""phase_fe_1_batch_b18_job_expense_user_id_dedup

FIND-121 (S2 High) — Add user_id to job_expense; recreate dedup index.

Actions:
  1. Add user_id UUID NOT NULL FK → user.id ON DELETE RESTRICT
  2. Backfill from created_by where available; use test user UUID for rows missing both
  3. Drop old index ix_job_expense_natural_key_dedup (job_id, incurred_at, cost_cents)
  4. Create correct index (user_id, job_id, incurred_at, cost_cents)

Note: user_id = tech who incurred the expense (different from created_by = operator).

Revision ID: d4f05609e2a5
Revises: e9a634b4d799
Create Date: 2026-05-12 18:08:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

# revision identifiers, used by Alembic.
revision = "d4f05609e2a5"
down_revision = "e9a634b4d799"
branch_labels = None
depends_on = None

_TEST_USER_ID = "00000000-0000-0000-0000-000000000002"


def upgrade() -> None:
    # Part 1: Add nullable first (safe for backfill)
    op.add_column(
        "job_expense",
        sa.Column("user_id", PG_UUID(as_uuid=True), nullable=True),
    )

    # Part 2: Backfill — use created_by if present, else fall back to test user
    op.execute(
        "UPDATE job_expense SET user_id = created_by "
        "WHERE user_id IS NULL AND created_by IS NOT NULL"
    )
    op.execute(
        f"UPDATE job_expense SET user_id = '{_TEST_USER_ID}' WHERE user_id IS NULL"
    )

    # Part 3: Lock to NOT NULL + add FK
    op.alter_column("job_expense", "user_id", nullable=False)
    op.create_foreign_key(
        "fk_job_expense_user_id",
        "job_expense",
        "user",
        ["user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_job_expense_user_id", "job_expense", ["user_id"])

    # Part 4: Drop old dedup index and create correct one
    op.drop_index("ix_job_expense_natural_key_dedup", table_name="job_expense")
    op.create_index(
        "ix_job_expense_natural_key_dedup",
        "job_expense",
        ["user_id", "job_id", "incurred_at", "cost_cents"],
    )


def downgrade() -> None:
    op.drop_index("ix_job_expense_natural_key_dedup", table_name="job_expense")
    op.create_index(
        "ix_job_expense_natural_key_dedup",
        "job_expense",
        ["job_id", "incurred_at", "cost_cents"],
    )
    op.drop_index("ix_job_expense_user_id", table_name="job_expense")
    op.drop_constraint("fk_job_expense_user_id", "job_expense", type_="foreignkey")
    op.drop_column("job_expense", "user_id")
