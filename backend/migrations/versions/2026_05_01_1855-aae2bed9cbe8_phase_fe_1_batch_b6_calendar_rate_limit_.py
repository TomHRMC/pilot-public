"""phase_fe_1_batch_b6_calendar_rate_limit_index

Revision ID: aae2bed9cbe8
Revises: 980940331aec
Create Date: 2026-05-01 18:55:06.000000

B6/A35: Add notification_outbox index for conflict-detection rate-limit queries.

New index on notification_outbox:
  - idx_notif_outbox_tenant_type_hour: (tenant_id, created_at DESC) WHERE channel = 'in_app'

Note: Design doc §G.2 references 'push' channel (APNs/FCM). The live schema only supports
'email', 'sms', 'in_app' channels — 'push' is a B8/A51 deliverable. Index uses 'in_app'
for the B6 rate-limit check. Will be updated in B8 when push channel is added.

Purpose: Makes the A35 rate-limit check (max 4 conflict-detection notifications per tenant
per hour) O(tenant-notifications-per-hour) instead of O(total rows).
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "aae2bed9cbe8"
down_revision: str | None = "980940331aec"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE INDEX idx_notif_outbox_tenant_type_hour
          ON notification_outbox (tenant_id, created_at DESC)
          WHERE channel = 'in_app'
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_notif_outbox_tenant_type_hour")
