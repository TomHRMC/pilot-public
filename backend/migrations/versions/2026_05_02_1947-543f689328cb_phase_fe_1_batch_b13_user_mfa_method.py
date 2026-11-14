"""phase_fe_1_batch_b13_user_mfa_method

Revision ID: 543f689328cb
Revises: bf99d70e8223
Create Date: 2026-05-02 19:47:58

A69: Create user_mfa_method table.
Persistent enrollment record per (tenant_id, user_id, method_type).

Note: No created_at/updated_at mixin — audit trigger only.
"""

from alembic import op

revision = "543f689328cb"
down_revision = "bf99d70e8223"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE user_mfa_method (
            mfa_method_id       UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            tenant_id           UUID        NOT NULL REFERENCES tenant(id),
            user_id             UUID        NOT NULL REFERENCES "user"(id),
            method_type         TEXT        NOT NULL,
            enrolled_at         TIMESTAMPTZ NOT NULL,
            last_used_at        TIMESTAMPTZ,
            cognito_method_id   TEXT        NOT NULL,
            verification_status TEXT        NOT NULL DEFAULT 'verified',
            metadata            JSONB,
            CONSTRAINT uq_user_mfa_method_tenant_user_type
                UNIQUE (tenant_id, user_id, method_type)
        )
    """)
    op.execute(
        "CREATE INDEX ix_user_mfa_method_tenant_id ON user_mfa_method(tenant_id)"
    )
    op.execute("CREATE INDEX ix_user_mfa_method_user_id   ON user_mfa_method(user_id)")

    # Audit trigger only — no created_at/updated_at mixin
    op.execute("""
        CREATE TRIGGER audit_user_mfa_method_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.user_mfa_method
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS audit_user_mfa_method_changes ON public.user_mfa_method"
    )
    op.execute("DROP TABLE IF EXISTS user_mfa_method")
