"""phase_fe_1_batch_b14_onboarding_checklist

Revision ID: b93540c6e600
Revises: 406e23abca54
Create Date: 2026-05-03 13:04:19

B14/A77: Onboarding Checklist
- Creates tenant_onboarding_checklist table (StandardAuditMixin)
- Seeds RBAC permissions: onboarding_checklist.skip_item, onboarding_checklist.dismiss
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "b93540c6e600"
down_revision = "406e23abca54"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # 1. CREATE tenant_onboarding_checklist (StandardAuditMixin — 3 triggers)
    # ============================================================
    op.execute("""
        CREATE TABLE tenant_onboarding_checklist (
            tenant_id                          UUID        NOT NULL,
            account_created                    BOOLEAN     NOT NULL DEFAULT false,
            legal_accepted                     BOOLEAN     NOT NULL DEFAULT false,
            tier_selected                      BOOLEAN     NOT NULL DEFAULT false,
            first_customer_added               BOOLEAN     NOT NULL DEFAULT false,
            first_customer_added_at            TIMESTAMPTZ,
            catalog_setup                      BOOLEAN     NOT NULL DEFAULT false,
            catalog_setup_at                   TIMESTAMPTZ,
            quickbooks_connected               BOOLEAN     NOT NULL DEFAULT false,
            quickbooks_skipped                 BOOLEAN     NOT NULL DEFAULT false,
            calendar_connected                 BOOLEAN     NOT NULL DEFAULT false,
            calendar_skipped                   BOOLEAN     NOT NULL DEFAULT false,
            team_invited                       BOOLEAN     NOT NULL DEFAULT false,
            team_skipped                       BOOLEAN     NOT NULL DEFAULT false,
            checklist_hidden                   BOOLEAN     NOT NULL DEFAULT false,
            checklist_dismissed_permanently    BOOLEAN     NOT NULL DEFAULT false,
            created_at                         TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at                         TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by                         UUID        REFERENCES "user"(id) ON DELETE RESTRICT,
            updated_by                         UUID        REFERENCES "user"(id) ON DELETE RESTRICT,
            CONSTRAINT pk_tenant_onboarding_checklist PRIMARY KEY (tenant_id),
            CONSTRAINT fk_tenant_onboarding_checklist_tenant_id
                FOREIGN KEY (tenant_id) REFERENCES tenant(id) ON DELETE RESTRICT
        )
    """)

    # Triggers for tenant_onboarding_checklist
    op.execute("""
        CREATE TRIGGER audit_tenant_onboarding_checklist_changes
            AFTER INSERT OR DELETE OR UPDATE ON public.tenant_onboarding_checklist
            FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER trg_tenant_onboarding_checklist_guard_created_immutable
            BEFORE UPDATE ON public.tenant_onboarding_checklist
            FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)
    op.execute("""
        CREATE TRIGGER trg_tenant_onboarding_checklist_set_updated_at
            BEFORE UPDATE ON public.tenant_onboarding_checklist
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()
    """)

    # ============================================================
    # 2. SEED new RBAC permissions
    # ============================================================
    op.execute("""
        UPDATE platform_role
        SET permissions = permissions || '["onboarding_checklist.skip_item","onboarding_checklist.dismiss"]'::jsonb
        WHERE code IN ('owner', 'accountant')
    """)


def downgrade() -> None:
    # Reverse RBAC permission seeds
    op.execute("""
        UPDATE platform_role
        SET permissions = (
            SELECT jsonb_agg(elem)
            FROM jsonb_array_elements(permissions) AS elem
            WHERE elem::text NOT IN (
                '"onboarding_checklist.skip_item"',
                '"onboarding_checklist.dismiss"'
            )
        )
        WHERE code IN ('owner', 'accountant')
    """)

    # Drop tenant_onboarding_checklist
    op.execute(
        "DROP TRIGGER IF EXISTS audit_tenant_onboarding_checklist_changes ON public.tenant_onboarding_checklist;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_tenant_onboarding_checklist_guard_created_immutable ON public.tenant_onboarding_checklist;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_tenant_onboarding_checklist_set_updated_at ON public.tenant_onboarding_checklist;"
    )
    op.execute("DROP TABLE IF EXISTS tenant_onboarding_checklist;")
