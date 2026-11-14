"""rename_job_schedule_columns

Revision ID: 9f3ba313aeb1
Revises: 7c521872b3b6
Create Date: 2026-04-24 15:51:55

Renames job.scheduled_start → job.scheduled_start_at
         job.scheduled_end   → job.scheduled_end_at

Also applies the missing trg_calendar_sync_log_guard_created_immutable trigger
that was deferred from task 1-A-3.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "9f3ba313aeb1"
down_revision = "7c521872b3b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Rename columns
    op.alter_column("job", "scheduled_start", new_column_name="scheduled_start_at")
    op.alter_column("job", "scheduled_end", new_column_name="scheduled_end_at")

    # 2. Drop old constraint and index
    op.drop_constraint("ck_job_schedule_range", "job", type_="check")
    op.drop_index("idx_job_scheduled_range", table_name="job")

    # 3. Recreate constraint
    op.create_check_constraint(
        "ck_job_schedule_range",
        "job",
        (
            "((scheduled_start_at IS NULL AND scheduled_end_at IS NULL) OR "
            "(scheduled_start_at IS NOT NULL AND scheduled_end_at IS NOT NULL "
            "AND scheduled_end_at > scheduled_start_at))"
        ),
    )

    # 4. Recreate GiST index
    op.execute("""
        CREATE INDEX idx_job_scheduled_range
        ON public.job USING gist (tenant_id, tstzrange(scheduled_start_at, scheduled_end_at, '[)'::text))
        WHERE (scheduled_start_at IS NOT NULL);
    """)

    # 5. Apply missing trigger to calendar_sync_log (idempotent)
    op.execute("""
        CREATE OR REPLACE TRIGGER trg_calendar_sync_log_guard_created_immutable
        BEFORE UPDATE ON public.calendar_sync_log
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();
    """)


def downgrade() -> None:
    # Drop trigger first
    op.execute(
        "DROP TRIGGER IF EXISTS trg_calendar_sync_log_guard_created_immutable "
        "ON public.calendar_sync_log;"
    )

    # Drop new index and constraint before renaming columns back
    op.drop_index("idx_job_scheduled_range", table_name="job")
    op.drop_constraint("ck_job_schedule_range", "job", type_="check")

    # Rename columns BACK first so constraint/index recreation uses the old names
    op.alter_column("job", "scheduled_start_at", new_column_name="scheduled_start")
    op.alter_column("job", "scheduled_end_at", new_column_name="scheduled_end")

    # Recreate constraint with old column names
    op.create_check_constraint(
        "ck_job_schedule_range",
        "job",
        (
            "((scheduled_start IS NULL AND scheduled_end IS NULL) OR "
            "(scheduled_start IS NOT NULL AND scheduled_end IS NOT NULL "
            "AND scheduled_end > scheduled_start))"
        ),
    )

    # Recreate GiST index with old column names
    op.execute("""
        CREATE INDEX idx_job_scheduled_range
        ON public.job USING gist (tenant_id, tstzrange(scheduled_start, scheduled_end, '[)'::text))
        WHERE (scheduled_start IS NOT NULL);
    """)
