"""phase_fe_1_batch_b7b_job_attachment_upload_tracking

Revision ID: 91bf9dafe0e5
Revises: 98dfa5001716
Create Date: 2026-05-01 21:18:38

B7b / A41 — Resumable Photo Upload Pipeline
Adds upload_status, s3_upload_session_id, upload_completed_at, expense_id
to job_attachment for S3 multipart upload tracking.

Design doc §F.2: Extending job_attachment (not a new photo table).
pilot_photo_id maps to job_attachment.id in API responses.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "91bf9dafe0e5"
down_revision = "98dfa5001716"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # 1. Add upload_status (nullable TEXT with CHECK)                      #
    # ------------------------------------------------------------------ #
    op.add_column(
        "job_attachment",
        sa.Column("upload_status", sa.Text(), nullable=True),
    )
    op.execute("""
        ALTER TABLE public.job_attachment
        ADD CONSTRAINT chk_job_attachment_upload_status
        CHECK (upload_status IS NULL OR upload_status IN ('pending_upload', 'uploading', 'complete', 'failed'));
    """)

    # ------------------------------------------------------------------ #
    # 2. Add s3_upload_session_id (nullable TEXT)                          #
    # ------------------------------------------------------------------ #
    op.add_column(
        "job_attachment",
        sa.Column("s3_upload_session_id", sa.Text(), nullable=True),
    )

    # ------------------------------------------------------------------ #
    # 3. Add upload_completed_at (nullable TIMESTAMPTZ)                    #
    # ------------------------------------------------------------------ #
    op.add_column(
        "job_attachment",
        sa.Column("upload_completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ------------------------------------------------------------------ #
    # 4. Add expense_id FK → job_expense.id ON DELETE SET NULL             #
    # ------------------------------------------------------------------ #
    op.add_column(
        "job_attachment",
        sa.Column("expense_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_job_attachment_expense",
        "job_attachment",
        "job_expense",
        ["expense_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ------------------------------------------------------------------ #
    # 5. Partial index for cleanup task: pending/uploading rows            #
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE INDEX ix_job_attachment_pending_uploads
        ON public.job_attachment (tenant_id, job_id)
        WHERE upload_status IN ('pending_upload', 'uploading');
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS public.ix_job_attachment_pending_uploads;")
    op.drop_constraint(
        "fk_job_attachment_expense", "job_attachment", type_="foreignkey"
    )
    op.drop_column("job_attachment", "expense_id")
    op.drop_column("job_attachment", "upload_completed_at")
    op.drop_column("job_attachment", "s3_upload_session_id")
    op.execute(
        "ALTER TABLE public.job_attachment DROP CONSTRAINT IF EXISTS chk_job_attachment_upload_status;"
    )
    op.drop_column("job_attachment", "upload_status")
