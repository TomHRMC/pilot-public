"""phase_fe_1_batch_b14_legal_acceptance_recording

Revision ID: d41e1505e201
Revises: 136379414877
Create Date: 2026-05-03 12:50:22

B14/A74: Legal Acceptance Recording
- Creates tenant_legal_acceptance table (AppendOnlyMixin — immutable)
- Seeds RBAC permission: legal_acceptance.accept
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "d41e1505e201"
down_revision = "136379414877"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # 1. CREATE tenant_legal_acceptance (AppendOnlyMixin — no updated_at, 2 triggers)
    # ============================================================
    op.execute("""
        CREATE TABLE tenant_legal_acceptance (
            acceptance_id         UUID        NOT NULL DEFAULT gen_random_uuid(),
            tenant_id             UUID        NOT NULL,
            user_id               UUID        NOT NULL REFERENCES "user"(id) ON DELETE RESTRICT,
            document_type         TEXT        NOT NULL,
            document_version_hash TEXT        NOT NULL,
            accepted_at           TIMESTAMPTZ NOT NULL,
            ip_address            INET        NOT NULL,
            user_agent            TEXT        NOT NULL,
            created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by            UUID        REFERENCES "user"(id) ON DELETE RESTRICT,
            CONSTRAINT pk_tenant_legal_acceptance PRIMARY KEY (acceptance_id),
            CONSTRAINT fk_tenant_legal_acceptance_tenant_id
                FOREIGN KEY (tenant_id) REFERENCES tenant(id) ON DELETE RESTRICT,
            CONSTRAINT tenant_legal_acceptance_document_type_chk
                CHECK (document_type IN ('tos', 'privacy', 'eula', 'marketing_email_optin'))
        )
    """)

    op.execute("""
        CREATE INDEX ix_tenant_legal_acceptance_tenant_id
            ON public.tenant_legal_acceptance USING btree (tenant_id)
    """)
    op.execute("""
        CREATE INDEX ix_tenant_legal_acceptance_user_document
            ON public.tenant_legal_acceptance USING btree (tenant_id, user_id, document_type)
    """)

    # AppendOnlyMixin: 2 triggers (audit + immutable guard — NO updated_at trigger)
    op.execute("""
        CREATE TRIGGER audit_tenant_legal_acceptance_changes
            AFTER INSERT OR DELETE OR UPDATE ON public.tenant_legal_acceptance
            FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)
    op.execute("""
        CREATE TRIGGER trg_tenant_legal_acceptance_guard_created_immutable
            BEFORE UPDATE ON public.tenant_legal_acceptance
            FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)

    # ============================================================
    # 2. SEED new RBAC permissions
    # ============================================================
    op.execute("""
        UPDATE platform_role
        SET permissions = permissions || '["legal_acceptance.accept"]'::jsonb
        WHERE code IN ('owner', 'technician', 'office_staff', 'accountant')
    """)


def downgrade() -> None:
    # Reverse RBAC permission seeds
    op.execute("""
        UPDATE platform_role
        SET permissions = (
            SELECT jsonb_agg(elem)
            FROM jsonb_array_elements(permissions) AS elem
            WHERE elem::text NOT IN ('"legal_acceptance.accept"')
        )
        WHERE code IN ('owner', 'technician', 'office_staff', 'accountant')
    """)

    # Drop tenant_legal_acceptance
    op.execute(
        "DROP TRIGGER IF EXISTS audit_tenant_legal_acceptance_changes ON public.tenant_legal_acceptance;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_tenant_legal_acceptance_guard_created_immutable ON public.tenant_legal_acceptance;"
    )
    op.execute("DROP TABLE IF EXISTS tenant_legal_acceptance;")
