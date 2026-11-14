"""task_1c4_job_time_entry_gps_checkin_columns

Revision ID: 1f929341eeb1
Revises: 08bbc78681fa
Create Date: 2026-04-20 21:39:43.000000

Task 1-C-4: Add GPS check-in columns to the `job_time_entry` table:
  - check_in_lat   NUMERIC(10,7) nullable — GPS latitude at clock-in
  - check_in_lng   NUMERIC(10,7) nullable — GPS longitude at clock-in
  - gps_variance_meters INTEGER nullable — GPS accuracy radius at clock-in

These columns record the technician's verified coordinates at clock-in,
enabling the contractor to audit on-site presence for payroll accuracy.
All three columns are nullable — existing time entries will have NULL values,
and the mobile app location permission request logic is addressed in Step 2 (UI).
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1f929341eeb1"
down_revision = "08bbc78681fa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add check_in_lat: NUMERIC(10,7) matches Numeric(10, 7) in ORM — 7 decimal places
    # covers GPS precision to ~1cm (WGS84 standard)
    op.add_column(
        "job_time_entry",
        sa.Column("check_in_lat", sa.Numeric(10, 7), nullable=True),
    )

    # Add check_in_lng: same precision as latitude
    op.add_column(
        "job_time_entry",
        sa.Column("check_in_lng", sa.Numeric(10, 7), nullable=True),
    )

    # Add gps_variance_meters: integer meters — GPS accuracy radius from the device
    op.add_column(
        "job_time_entry",
        sa.Column("gps_variance_meters", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("job_time_entry", "gps_variance_meters")
    op.drop_column("job_time_entry", "check_in_lng")
    op.drop_column("job_time_entry", "check_in_lat")
