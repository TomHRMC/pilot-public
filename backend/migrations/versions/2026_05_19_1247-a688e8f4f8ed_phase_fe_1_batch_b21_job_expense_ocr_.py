"""phase_fe_1_batch_b21_job_expense_ocr_columns

Revision ID: a688e8f4f8ed
Revises: a05f647b21fa
Create Date: 2026-05-19 12:47:29.000000

FIND-062 (B21/A96): Add ocr_processed_at + ocr_source columns to job_expense.

These columns support the Receipt OCR pipeline:
  - ocr_processed_at: timestamp when OCR processing completed (NULL = not yet processed)
  - ocr_source: source of the OCR extraction (e.g. 'rapidocr'); NULL = not processed

Both are nullable. No backfill required — existing rows have not been OCR processed.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a688e8f4f8ed"
down_revision = "a05f647b21fa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "job_expense",
        sa.Column("ocr_processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "job_expense",
        sa.Column("ocr_source", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("job_expense", "ocr_source")
    op.drop_column("job_expense", "ocr_processed_at")
