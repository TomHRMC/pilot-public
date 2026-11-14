"""phase_fe_1_batch_b14_mobile_push_permission_state

Revision ID: ddae94e9c3e9
Revises: b93540c6e600
Create Date: 2026-05-03 13:10:54

B14/A78: Mobile Push Permission State
- Adds UNIQUE constraint on mobile_device_push_token.device_id (prerequisite for FK)
- Creates mobile_push_permission_state table (StandardAuditMixin, composite PK)
- Seeds RBAC permission: mobile_push_permission.update
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "ddae94e9c3e9"
down_revision = "b93540c6e600"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # 1. Add UNIQUE constraint on mobile_device_push_token.device_id
    #    Required for the FK from mobile_push_permission_state.device_id
    #    Per design doc F6: device_id must be uniquely constrained before use as FK target
    # ============================================================
    op.execute("""
        ALTER TABLE mobile_device_push_token
        ADD CONSTRAINT uq_mobile_device_push_token_device_id UNIQUE (device_id)
    """)

    # ============================================================
    # 2. CREATE mobile_push_permission_state (StandardAuditMixin — 3 triggers)
    # ============================================================
    op.execute("""
        CREATE TABLE mobile_push_permission_state (
            tenant_id                        UUID        NOT NULL REFERENCES tenant(id) ON DELETE RESTRICT,
            user_id                          UUID        NOT NULL REFERENCES "user"(id) ON DELETE RESTRICT,
            device_id                        UUID        NOT NULL REFERENCES mobile_device_push_token(device_id) ON DELETE RESTRICT,
            permission_state                 TEXT        NOT NULL DEFAULT 'not_asked',
            last_state_change_at             TIMESTAMPTZ NOT NULL,
            dismissable_banner_dismissed_at  TIMESTAMPTZ,
            created_at                       TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at                       TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by                       UUID        REFERENCES "user"(id) ON DELETE RESTRICT,
            updated_by                       UUID        REFERENCES "user"(id) ON DELETE RESTRICT,
            CONSTRAINT pk_mobile_push_permission_state PRIMARY KEY (tenant_id, user_id, device_id),
            CONSTRAINT mobile_push_permission_state_state_chk
                CHECK (permission_state IN (
                    'not_asked', 'granted', 'denied_by_user_choice',
                    'denied_by_os', 'revoked_in_settings'
                ))
        )
    """)

    op.execute("""
        CREATE INDEX ix_mobile_push_perm_tenant_user
            ON public.mobile_push_permission_state USING btree (tenant_id, user_id)
    """)

    # Triggers for mobile_push_permission_state
    op.execute("""
        CREATE TRIGGER audit_mobile_push_permission_state_changes
            AFTER INSERT OR DELETE OR UPDATE ON public.mobile_push_permission_state
            FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER trg_mobile_push_permission_state_guard_created_immutable
            BEFORE UPDATE ON public.mobile_push_permission_state
            FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)
    op.execute("""
        CREATE TRIGGER trg_mobile_push_permission_state_set_updated_at
            BEFORE UPDATE ON public.mobile_push_permission_state
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)

    # ============================================================
    # 3. SEED new RBAC permissions
    # ============================================================
    op.execute("""
        UPDATE platform_role
        SET permissions = permissions || '["mobile_push_permission.update"]'::jsonb
        WHERE code IN ('owner', 'technician', 'office_staff', 'accountant')
    """)


def downgrade() -> None:
    # Reverse RBAC permission seeds
    op.execute("""
        UPDATE platform_role
        SET permissions = (
            SELECT jsonb_agg(elem)
            FROM jsonb_array_elements(permissions) AS elem
            WHERE elem::text NOT IN ('"mobile_push_permission.update"')
        )
        WHERE code IN ('owner', 'technician', 'office_staff', 'accountant')
    """)

    # Drop mobile_push_permission_state
    op.execute(
        "DROP TRIGGER IF EXISTS audit_mobile_push_permission_state_changes ON public.mobile_push_permission_state;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_mobile_push_permission_state_guard_created_immutable ON public.mobile_push_permission_state;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_mobile_push_permission_state_set_updated_at ON public.mobile_push_permission_state;"
    )
    op.execute("DROP TABLE IF EXISTS mobile_push_permission_state;")

    # Remove UNIQUE constraint on mobile_device_push_token.device_id
    op.execute("""
        ALTER TABLE mobile_device_push_token
        DROP CONSTRAINT IF EXISTS uq_mobile_device_push_token_device_id
    """)
