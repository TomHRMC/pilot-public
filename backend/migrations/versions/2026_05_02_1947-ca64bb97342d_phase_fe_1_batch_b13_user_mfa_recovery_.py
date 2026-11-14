"""phase_fe_1_batch_b13_user_mfa_recovery_code

Revision ID: ca64bb97342d
Revises: 543f689328cb
Create Date: 2026-05-02 19:47:58

A69: Create user_mfa_recovery_code table.
Bcrypt-hashed backup recovery codes; 10 codes per set_id group.

Note: No created_at/updated_at mixin — audit trigger only.
"""

from alembic import op

revision = "ca64bb97342d"
down_revision = "543f689328cb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE user_mfa_recovery_code (
            code_id      UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            tenant_id    UUID        NOT NULL REFERENCES tenant(id),
            user_id      UUID        NOT NULL REFERENCES "user"(id),
            code_hash    TEXT        NOT NULL,
            generated_at TIMESTAMPTZ NOT NULL,
            used_at      TIMESTAMPTZ,
            set_id       UUID        NOT NULL
        )
    """)
    op.execute(
        "CREATE INDEX ix_user_mfa_recovery_code_tenant_id ON user_mfa_recovery_code(tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_user_mfa_recovery_code_user_id   ON user_mfa_recovery_code(user_id)"
    )
    op.execute(
        "CREATE INDEX ix_user_mfa_recovery_code_set_id    ON user_mfa_recovery_code(set_id)"
    )

    # Audit trigger only — no created_at/updated_at mixin
    op.execute("""
        CREATE TRIGGER audit_user_mfa_recovery_code_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.user_mfa_recovery_code
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS audit_user_mfa_recovery_code_changes ON public.user_mfa_recovery_code"
    )
    op.execute("DROP TABLE IF EXISTS user_mfa_recovery_code")
