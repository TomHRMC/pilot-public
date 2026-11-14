"""phase_fe_1_batch_b13_user_session_metadata

Revision ID: 97ffd00c829c
Revises: ca64bb97342d
Create Date: 2026-05-02 19:47:58

A70: Create user_session_metadata table.
One row per active browser/device session; linked to auth_refresh_token via session_id FK.

Note: created_at has DEFAULT now() but no updated_at — only audit trigger attached.
"""

from alembic import op

revision = "97ffd00c829c"
down_revision = "ca64bb97342d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE user_session_metadata (
            session_id          UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            tenant_id           UUID        NOT NULL REFERENCES tenant(id),
            user_id             UUID        NOT NULL REFERENCES "user"(id),
            device_fingerprint  TEXT        NOT NULL,
            display_label       TEXT        NOT NULL,
            ip_address          INET        NOT NULL,
            geolocation         TEXT,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            last_active_at      TIMESTAMPTZ NOT NULL,
            revoked_at          TIMESTAMPTZ
        )
    """)
    op.execute(
        "CREATE INDEX ix_user_session_metadata_tenant_id ON user_session_metadata(tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_user_session_metadata_user_id   ON user_session_metadata(user_id)"
    )
    op.execute("""
        CREATE INDEX ix_user_session_metadata_user_id_revoked_at
            ON user_session_metadata(user_id, revoked_at)
    """)

    # Audit trigger only — no updated_at column, so set_updated_at trigger is omitted.
    # guard_created_fields_immutable also omitted (created_at is immutable by application logic).
    op.execute("""
        CREATE TRIGGER audit_user_session_metadata_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.user_session_metadata
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS audit_user_session_metadata_changes ON public.user_session_metadata"
    )
    op.execute("DROP TABLE IF EXISTS user_session_metadata")
