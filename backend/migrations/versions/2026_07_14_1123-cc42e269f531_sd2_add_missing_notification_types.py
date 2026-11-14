"""sd2_add_missing_notification_types

Revision ID: cc42e269f531
Revises: f3b52caec35b
Create Date: 2026-07-14 11:23:05

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cc42e269f531"
down_revision: str | None = "f3b52caec35b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("""
        INSERT INTO public.notification_type
        (code, tenant_id, audience, name, description, is_active, created_at, updated_at)
        VALUES
          ('job_assigned', NULL, 'tenant', 'Job Assigned',
           'Fired when a technician is assigned to a job', true, NOW(), NOW()),
          ('schedule_changed', NULL, 'tenant', 'Schedule Changed',
           'Fired when a job schedule is updated', true, NOW(), NOW()),
          ('qb_sync_conflict', NULL, 'tenant', 'QB Sync Conflict',
           'Fired when a QuickBooks sync conflict is detected', true, NOW(), NOW()),
          ('qb_conflict_pre_warning', NULL, 'tenant', 'QB Conflict Pre-Warning',
           'Fired before a QB conflict is auto-expired', true, NOW(), NOW()),
          ('gps_variance_alert', NULL, 'tenant', 'GPS Variance Alert',
           'Fired when a tech clock-in GPS is far from the job site', true, NOW(), NOW()),
          ('system_template_updated', NULL, 'tenant', 'System Template Updated',
           'Fired when a system communication template is updated', true, NOW(), NOW())
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM public.notification_type
        WHERE code IN (
          'job_assigned', 'schedule_changed', 'qb_sync_conflict',
          'qb_conflict_pre_warning', 'gps_variance_alert', 'system_template_updated'
        ) AND tenant_id IS NULL
    """)
