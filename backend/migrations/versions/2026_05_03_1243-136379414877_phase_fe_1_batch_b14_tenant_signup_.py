"""phase_fe_1_batch_b14_tenant_signup_state_machine

Revision ID: 136379414877
Revises: 2cb6b20b35d7
Create Date: 2026-05-03 12:43:15

B14/A73: Tenant Signup State Machine
- Creates tenant_signup table (wizard state machine)
- Seeds RBAC permission: tenant.signup.complete (auto during signup wizard)
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "136379414877"
down_revision = "2cb6b20b35d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # 1. CREATE tenant_signup
    # ============================================================
    op.execute("""
        CREATE TABLE tenant_signup (
            tenant_id          UUID        NOT NULL,
            signup_state       TEXT        NOT NULL DEFAULT 'step1_account',
            signup_started_at  TIMESTAMPTZ NOT NULL,
            signup_completed_at TIMESTAMPTZ,
            business_name      TEXT        NOT NULL,
            trade              TEXT        NOT NULL,
            business_size      TEXT        NOT NULL,
            zip                TEXT        NOT NULL,
            time_zone          TEXT        NOT NULL,
            created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by         UUID        REFERENCES "user"(id) ON DELETE RESTRICT,
            updated_by         UUID        REFERENCES "user"(id) ON DELETE RESTRICT,
            CONSTRAINT pk_tenant_signup PRIMARY KEY (tenant_id),
            CONSTRAINT fk_tenant_signup_tenant_id
                FOREIGN KEY (tenant_id) REFERENCES tenant(id) ON DELETE RESTRICT,
            CONSTRAINT tenant_signup_state_chk
                CHECK (signup_state IN (
                    'step1_account', 'step2_legal', 'step3_phone',
                    'step4_tier', 'step5_confirm', 'complete'
                ))
        )
    """)

    op.execute("""
        CREATE INDEX ix_tenant_signup_state
            ON public.tenant_signup USING btree (signup_state)
    """)

    # Triggers for tenant_signup
    op.execute("""
        CREATE TRIGGER audit_tenant_signup_changes
            AFTER INSERT OR DELETE OR UPDATE ON public.tenant_signup
            FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER trg_tenant_signup_guard_created_immutable
            BEFORE UPDATE ON public.tenant_signup
            FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)
    op.execute("""
        CREATE TRIGGER trg_tenant_signup_set_updated_at
            BEFORE UPDATE ON public.tenant_signup
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)

    # ============================================================
    # 2. SEED new RBAC permissions
    # tenant.signup.complete is a public wizard permission — all roles
    # ============================================================
    op.execute("""
        UPDATE platform_role
        SET permissions = permissions || '["tenant.signup.complete"]'::jsonb
        WHERE code IN ('owner', 'technician', 'office_staff', 'accountant')
    """)


def downgrade() -> None:
    # Reverse RBAC permission seeds
    op.execute("""
        UPDATE platform_role
        SET permissions = (
            SELECT jsonb_agg(elem)
            FROM jsonb_array_elements(permissions) AS elem
            WHERE elem::text NOT IN ('"tenant.signup.complete"')
        )
        WHERE code IN ('owner', 'technician', 'office_staff', 'accountant')
    """)

    # Drop tenant_signup
    op.execute(
        "DROP TRIGGER IF EXISTS audit_tenant_signup_changes ON public.tenant_signup;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_tenant_signup_guard_created_immutable ON public.tenant_signup;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_tenant_signup_set_updated_at ON public.tenant_signup;"
    )
    op.execute("DROP TABLE IF EXISTS tenant_signup;")
