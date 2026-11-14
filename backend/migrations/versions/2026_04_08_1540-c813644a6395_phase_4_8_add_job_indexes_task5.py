"""phase_4_8_add_job_indexes_task5

Revision ID: c813644a6395
Revises: 32576bae5ff3
Create Date: 2026-04-08 15:40:05.590397+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c813644a6395"
down_revision: str | None = "32576bae5ff3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Index 1: Job tenant-scoped status list with time ordering
    # Query pattern: "Show me all 'in_progress' jobs for this tenant, newest first"
    op.create_index(
        "idx_job_tenant_status_created_at",
        "job",
        ["tenant_id", "status_id", sa.text("created_at DESC")],
    )

    # Index 2: Job expense tenant-scoped time ordering
    # Query pattern: "Show me all expenses for this tenant this month"
    op.create_index(
        "idx_job_expense_tenant",
        "job_expense",
        ["tenant_id", sa.text("incurred_at DESC")],
    )


def downgrade() -> None:
    # Drop indexes in reverse order
    op.drop_index("idx_job_expense_tenant", table_name="job_expense")
    op.drop_index("idx_job_tenant_status_created_at", table_name="job")
