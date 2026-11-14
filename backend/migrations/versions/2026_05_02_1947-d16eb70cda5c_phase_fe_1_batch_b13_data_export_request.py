"""phase_fe_1_batch_b13_data_export_request

Revision ID: d16eb70cda5c
Revises: aa299c94248a
Create Date: 2026-05-02 19:47:58

A71: Create data_export_request table.
Tracks async data export pipeline status. ZIP archives streamed to S3.

Note: No created_at/updated_at mixin — audit trigger only.
"""

from alembic import op

revision = "d16eb70cda5c"
down_revision = "aa299c94248a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE data_export_request (
            export_id      UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            tenant_id      UUID        NOT NULL REFERENCES tenant(id),
            user_id        UUID        NOT NULL REFERENCES "user"(id),
            requested_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            status         TEXT        NOT NULL DEFAULT 'pending',
            s3_path        TEXT,
            signed_url     TEXT,
            expires_at     TIMESTAMPTZ,
            data_scope     TEXT        NOT NULL,
            failure_reason TEXT
        )
    """)
    op.execute(
        "CREATE INDEX ix_data_export_request_tenant_id ON data_export_request(tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_data_export_request_user_id   ON data_export_request(user_id)"
    )
    op.execute(
        "CREATE INDEX ix_data_export_request_status    ON data_export_request(status)"
    )

    # Audit trigger only — no updated_at/created_at mixin
    op.execute("""
        CREATE TRIGGER audit_data_export_request_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.data_export_request
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS audit_data_export_request_changes ON public.data_export_request"
    )
    op.execute("DROP TABLE IF EXISTS data_export_request")
