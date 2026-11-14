"""phase_fe_1_batch_b8_mobile_device_push_token

Revision ID: 7322cb83efee
Revises: fix_audit_log_changes_no_id
Create Date: 2026-05-02 09:28:00.000000

B8/A51: Create mobile_device_push_token table — canonical push token registry.
"""

from alembic import op

revision: str = "7322cb83efee"
down_revision: str | None = "fix_audit_log_changes_no_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE mobile_device_push_token (
            id                               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id                        UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
            user_id                          UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
            device_id                        UUID NOT NULL,
            platform                         TEXT NOT NULL,
            push_token                       TEXT NOT NULL,
            app_version                      TEXT NULL,
            os_version                       TEXT NULL,
            registered_at                    TIMESTAMPTZ NOT NULL DEFAULT now(),
            last_seen_at                     TIMESTAMPTZ NOT NULL DEFAULT now(),
            notification_permission_granted  BOOLEAN NOT NULL DEFAULT TRUE,
            revoked_at                       TIMESTAMPTZ NULL,
            created_at                       TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at                       TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by                       UUID NULL REFERENCES "user"(id) ON DELETE SET NULL,
            updated_by                       UUID NULL REFERENCES "user"(id) ON DELETE SET NULL,
            CONSTRAINT mobile_device_push_token_platform_chk
                CHECK (platform IN ('ios', 'android')),
            CONSTRAINT mobile_device_push_token_tenant_user_device_uq
                UNIQUE (tenant_id, user_id, device_id)
        )
    """)

    op.execute("""
        CREATE INDEX idx_mobile_device_push_token_tenant_user
            ON mobile_device_push_token (tenant_id, user_id)
    """)

    op.execute("""
        CREATE INDEX idx_mobile_device_push_token_active
            ON mobile_device_push_token (tenant_id, user_id, device_id)
            WHERE revoked_at IS NULL
    """)

    # Mandatory triggers per §13.4
    op.execute("""
        CREATE TRIGGER audit_mobile_device_push_token_changes
        AFTER INSERT OR DELETE OR UPDATE ON public.mobile_device_push_token
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)

    op.execute("""
        CREATE TRIGGER trg_mobile_device_push_token_guard_created_immutable
        BEFORE UPDATE ON public.mobile_device_push_token
        FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)

    op.execute("""
        CREATE TRIGGER trg_mobile_device_push_token_set_updated_at
        BEFORE UPDATE ON public.mobile_device_push_token
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_mobile_device_push_token_set_updated_at ON mobile_device_push_token"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_mobile_device_push_token_guard_created_immutable ON mobile_device_push_token"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_mobile_device_push_token_changes ON mobile_device_push_token"
    )
    op.execute("DROP TABLE IF EXISTS mobile_device_push_token")
