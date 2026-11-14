"""phase_fe_1_batch_b8_mobile_sync_event_audit

Revision ID: 7137111db267
Revises: 1db2921ed26b
Create Date: 2026-05-02 09:28:00.000000

B8/A48: Create mobile_sync_event_audit table — append-only owner resolution audit log.
FK references mobile_sync_owner_escalation.id (B7b table).
"""

from alembic import op

revision: str = "7137111db267"
down_revision: str | None = "1db2921ed26b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE mobile_sync_event_audit (
            id                               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id                        UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
            escalation_id                    UUID NOT NULL REFERENCES mobile_sync_owner_escalation(id) ON DELETE RESTRICT,
            originator_user_id               UUID NOT NULL REFERENCES "user"(id) ON DELETE RESTRICT,
            resolver_user_id                 UUID NOT NULL REFERENCES "user"(id) ON DELETE RESTRICT,
            resolution_action                TEXT NOT NULL,
            resolution_channel               TEXT NOT NULL DEFAULT 'web',
            tech_local_snapshot_at_commit    JSONB NULL,
            server_state_snapshot_at_commit  JSONB NULL,
            post_commit_state                JSONB NULL,
            resolved_at                      TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT mobile_sync_event_audit_channel_chk
                CHECK (resolution_channel IN ('web', 'voice'))
        )
    """)

    op.execute("""
        CREATE INDEX idx_mobile_sync_event_audit_escalation
            ON mobile_sync_event_audit (escalation_id)
    """)

    op.execute("""
        CREATE INDEX idx_mobile_sync_event_audit_tenant_resolver
            ON mobile_sync_event_audit (tenant_id, resolver_user_id, resolved_at DESC)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_mobile_sync_event_audit_tenant_resolver")
    op.execute("DROP INDEX IF EXISTS idx_mobile_sync_event_audit_escalation")
    op.execute("DROP TABLE IF EXISTS mobile_sync_event_audit")
