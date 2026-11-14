"""job_ui_b1_job_title

Revision ID: dc2e62a12b1e
Revises: 44fb6fed24c3
Create Date: 2026-07-27 16:02:27

JOB-UI-B1 (Part A): Add job.title — nullable TEXT column.
No backfill (existing jobs retain NULL title).
No CHECK constraint (free-text field).
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "dc2e62a12b1e"
down_revision = "44fb6fed24c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE job ADD COLUMN title TEXT;")


def downgrade() -> None:
    op.execute("ALTER TABLE job DROP COLUMN title;")
