"""task_1a2_job_scheduling_columns

ALTER TABLE job to add scheduling columns:
  - estimated_duration_minutes  (integer, nullable)
  - external_calendar_event_id  (text, nullable)

Adds 2 check constraints:
  - ck_job_schedule_range
  - ck_job_estimated_duration_positive

Adds 2 indexes:
  - idx_job_scheduled_range  (GIST on tstzrange)
  - uq_job_external_calendar_event  (UNIQUE partial btree)

Revision ID: 6e3c4fa8431d
Revises: 204ec4eb4f09
Create Date: 2026-04-23 21:52:56
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "6e3c4fa8431d"
down_revision = "204ec4eb4f09"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add the two new nullable columns
    op.add_column(
        "job",
        sa.Column("estimated_duration_minutes", sa.Integer(), nullable=True),
    )
    op.add_column(
        "job",
        sa.Column("external_calendar_event_id", sa.Text(), nullable=True),
    )

    # Check constraint: schedule range coherence (both NULL or both set with end > start)
    op.execute("""
        ALTER TABLE public.job
        ADD CONSTRAINT ck_job_schedule_range
        CHECK (
            (scheduled_start IS NULL AND scheduled_end IS NULL)
            OR (
                scheduled_start IS NOT NULL
                AND scheduled_end IS NOT NULL
                AND scheduled_end > scheduled_start
            )
        )
    """)

    # Check constraint: positive duration
    op.execute("""
        ALTER TABLE public.job
        ADD CONSTRAINT ck_job_estimated_duration_positive
        CHECK (estimated_duration_minutes IS NULL OR estimated_duration_minutes > 0)
    """)

    # GIST index for time-range overlap queries
    op.execute("""
        CREATE INDEX idx_job_scheduled_range
        ON public.job
        USING gist (tenant_id, tstzrange(scheduled_start, scheduled_end, '[)'))
        WHERE scheduled_start IS NOT NULL
    """)

    # Unique partial index on external_calendar_event_id per tenant
    op.execute("""
        CREATE UNIQUE INDEX uq_job_external_calendar_event
        ON public.job
        USING btree (tenant_id, external_calendar_event_id)
        WHERE external_calendar_event_id IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS public.uq_job_external_calendar_event;")
    op.execute("DROP INDEX IF EXISTS public.idx_job_scheduled_range;")
    op.execute("""
        ALTER TABLE public.job
        DROP CONSTRAINT IF EXISTS ck_job_estimated_duration_positive
    """)
    op.execute("""
        ALTER TABLE public.job
        DROP CONSTRAINT IF EXISTS ck_job_schedule_range
    """)
    op.drop_column("job", "external_calendar_event_id")
    op.drop_column("job", "estimated_duration_minutes")
