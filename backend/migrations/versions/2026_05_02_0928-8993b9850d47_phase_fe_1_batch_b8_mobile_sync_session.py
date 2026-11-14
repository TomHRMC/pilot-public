"""phase_fe_1_batch_b8_mobile_sync_session

Revision ID: 8993b9850d47
Revises: 7322cb83efee
Create Date: 2026-05-02 09:28:00.000000

B8/A51: Create mobile_sync_session table — background sync session telemetry.
"""

from alembic import op

revision: str = "8993b9850d47"
down_revision: str | None = "7322cb83efee"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE mobile_sync_session (
            session_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id           UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
            user_id             UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
            device_id           UUID NOT NULL,
            triggered_by        TEXT NOT NULL,
            started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            completed_at        TIMESTAMPTZ NULL,
            outcome             TEXT NULL,
            items_attempted     INTEGER NOT NULL DEFAULT 0,
            items_committed     INTEGER NOT NULL DEFAULT 0,
            items_deferred      INTEGER NOT NULL DEFAULT 0,
            items_failed        INTEGER NOT NULL DEFAULT 0,
            failure_reason      TEXT NULL,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT mobile_sync_session_triggered_by_chk
                CHECK (triggered_by IN ('silent_push', 'os_opportunistic', 'foreground', 'manual')),
            CONSTRAINT mobile_sync_session_outcome_chk
                CHECK (outcome IS NULL OR outcome IN ('success', 'partial', 'failed', 'throttled'))
        )
    """)

    op.execute("""
        CREATE INDEX idx_mobile_sync_session_tenant_user_device
            ON mobile_sync_session (tenant_id, user_id, device_id, started_at DESC)
    """)

    op.execute("""
        CREATE INDEX idx_mobile_sync_session_device_recent
            ON mobile_sync_session (device_id, started_at DESC)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_mobile_sync_session_device_recent")
    op.execute("DROP INDEX IF EXISTS idx_mobile_sync_session_tenant_user_device")
    op.execute("DROP TABLE IF EXISTS mobile_sync_session")
