"""phase_fe_1_batch_b13_mfa_grace_period_tracking

Revision ID: bf99d70e8223
Revises: 7b059e2e001b
Create Date: 2026-05-02 19:47:58

A68: Create mfa_grace_period_tracking table (composite PK: tenant_id, user_id).
Tracks per-user MFA grace period state when tenant policy is activated.

Note: No created_at/updated_at mixin — audit trigger only.
"""

from alembic import op

revision = "bf99d70e8223"
down_revision = "7b059e2e001b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE mfa_grace_period_tracking (
            tenant_id                 UUID        NOT NULL REFERENCES tenant(id),
            user_id                   UUID        NOT NULL REFERENCES "user"(id),
            grace_started_at          TIMESTAMPTZ NOT NULL,
            enrolled_at               TIMESTAMPTZ,
            enforcement_activated_at  TIMESTAMPTZ,
            PRIMARY KEY (tenant_id, user_id)
        )
    """)
    op.execute(
        "CREATE INDEX ix_mfa_grace_period_tracking_tenant_id ON mfa_grace_period_tracking(tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_mfa_grace_period_tracking_user_id ON mfa_grace_period_tracking(user_id)"
    )

    # Audit trigger only — no created_at/updated_at mixin
    op.execute("""
        CREATE TRIGGER audit_mfa_grace_period_tracking_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.mfa_grace_period_tracking
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS audit_mfa_grace_period_tracking_changes ON public.mfa_grace_period_tracking"
    )
    op.execute("DROP TABLE IF EXISTS mfa_grace_period_tracking")
