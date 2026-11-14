"""phase_fe_1_batch_b8_mobile_push_rate_limit

Revision ID: 1db2921ed26b
Revises: 8993b9850d47
Create Date: 2026-05-02 09:28:00.000000

B8/A51: Create mobile_push_rate_limit table — per-device server-side rate limiting.
"""

from alembic import op

revision: str = "1db2921ed26b"
down_revision: str | None = "8993b9850d47"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE mobile_push_rate_limit (
            id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id                   UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
            device_id                   UUID NOT NULL,
            last_push_sent_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            push_count_current_window   INTEGER NOT NULL DEFAULT 1,
            window_start_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT mobile_push_rate_limit_device_uq UNIQUE (device_id)
        )
    """)

    op.execute("""
        CREATE INDEX idx_mobile_push_rate_limit_tenant
            ON mobile_push_rate_limit (tenant_id)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_mobile_push_rate_limit_tenant")
    op.execute("DROP TABLE IF EXISTS mobile_push_rate_limit")
