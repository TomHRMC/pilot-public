"""phase_fe_1_batch_b13_user_session_history

Revision ID: f34992b63714
Revises: 4c262bd92137
Create Date: 2026-05-02 19:47:46

A72: Create user_session_history table (composite PK: tenant_id, user_id).
Upserted on every successful login to track first-login date and session count.

Note: This table has NO created_at/updated_at mixin columns, so
guard_created_fields_immutable and set_updated_at triggers are intentionally
omitted. Only the audit trigger is attached.
"""

from alembic import op

revision = "f34992b63714"
down_revision = "4c262bd92137"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE user_session_history (
            tenant_id UUID NOT NULL REFERENCES tenant(id),
            user_id   UUID NOT NULL REFERENCES "user"(id),
            first_login_at        TIMESTAMPTZ NOT NULL,
            total_session_count   INTEGER     NOT NULL DEFAULT 0,
            last_login_at         TIMESTAMPTZ NOT NULL,
            PRIMARY KEY (tenant_id, user_id)
        )
    """)
    op.execute(
        "CREATE INDEX ix_user_session_history_tenant_id ON user_session_history(tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_user_session_history_user_id ON user_session_history(user_id)"
    )

    # Audit trigger only — no created_at/updated_at mixin on this table
    op.execute("""
        CREATE TRIGGER audit_user_session_history_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.user_session_history
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS audit_user_session_history_changes ON public.user_session_history"
    )
    op.execute("DROP TABLE IF EXISTS user_session_history")
