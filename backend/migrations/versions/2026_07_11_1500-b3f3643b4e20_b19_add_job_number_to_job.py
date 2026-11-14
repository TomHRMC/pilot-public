"""b19_add_job_number_to_job

Revision ID: b3f3643b4e20
Revises: 1635c1bf1d1b
Create Date: 2026-07-11 15:00:00.000000

Format: JOB-000001 (sequential, tenant-scoped, zero-padded 6 digits)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3f3643b4e20"
down_revision: str | None = "1635c1bf1d1b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Part 1 — Add nullable column
    op.add_column("job", sa.Column("job_number", sa.String(30), nullable=True))

    # Part 2 — Backfill existing rows: sequential per tenant, ordered by created_at
    op.execute("""
        UPDATE job j
        SET job_number = 'JOB-' || LPAD(rn.row_num::text, 6, '0')
        FROM (
            SELECT id, ROW_NUMBER() OVER (PARTITION BY tenant_id ORDER BY created_at) AS row_num
            FROM job
        ) rn
        WHERE j.id = rn.id
        AND j.job_number IS NULL
    """)

    # Part 3 — Apply NOT NULL constraint and unique index
    op.alter_column("job", "job_number", nullable=False)
    op.create_index(
        "ix_job_tenant_job_number", "job", ["tenant_id", "job_number"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_job_tenant_job_number", table_name="job")
    op.drop_column("job", "job_number")
