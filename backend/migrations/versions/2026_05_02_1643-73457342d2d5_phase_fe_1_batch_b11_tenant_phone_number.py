"""phase_fe_1_batch_b11_tenant_phone_number

Revision ID: 73457342d2d5
Revises: 65466ce269db
Create Date: 2026-05-02 16:43:00

B11/A61 — Create tenant_phone_number table.
Stores provisioned Telnyx phone numbers per tenant.
Required FK dependency before customer_communication_thread (Migration 3).
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "73457342d2d5"
down_revision = "65466ce269db"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE tenant_phone_number (
            id                       UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id                UUID        NOT NULL REFERENCES tenant(id) ON DELETE RESTRICT,
            phone_number             TEXT        NOT NULL,
            area_code                TEXT        NOT NULL,
            carrier                  TEXT        NOT NULL DEFAULT 'telnyx',
            carrier_provisioning_id  TEXT        NULL,
            monthly_fee_cents        INTEGER     NOT NULL DEFAULT 100,
            status                   TEXT        NOT NULL DEFAULT 'active',
            provisioned_at           TIMESTAMPTZ NULL,
            released_at              TIMESTAMPTZ NULL,
            created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by               UUID        NULL REFERENCES "user"(id) ON DELETE RESTRICT,
            updated_by               UUID        NULL REFERENCES "user"(id) ON DELETE RESTRICT,
            CONSTRAINT tenant_phone_number_status_chk
                CHECK (status IN ('active', 'released', 'provisioning_failed')),
            CONSTRAINT tenant_phone_number_carrier_chk
                CHECK (carrier IN ('telnyx'))
        );
    """)

    # One active number per tenant
    op.execute("""
        CREATE UNIQUE INDEX uq_tenant_phone_number_active
            ON tenant_phone_number(tenant_id)
            WHERE status = 'active';
    """)

    op.execute("""
        CREATE INDEX idx_tenant_phone_number_tenant_id ON tenant_phone_number(tenant_id);
        CREATE INDEX idx_tenant_phone_number_phone     ON tenant_phone_number(phone_number);
    """)

    # Standard triggers
    op.execute("""
        CREATE TRIGGER audit_tenant_phone_number_changes
            AFTER INSERT OR DELETE OR UPDATE ON public.tenant_phone_number
            FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)
    op.execute("""
        CREATE TRIGGER trg_tenant_phone_number_guard_created_immutable
            BEFORE UPDATE ON public.tenant_phone_number
            FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable();
    """)
    op.execute("""
        CREATE TRIGGER trg_tenant_phone_number_set_updated_at
            BEFORE UPDATE ON public.tenant_phone_number
            FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_tenant_phone_number_set_updated_at ON public.tenant_phone_number;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_tenant_phone_number_guard_created_immutable ON public.tenant_phone_number;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_tenant_phone_number_changes ON public.tenant_phone_number;"
    )
    op.execute("DROP TABLE IF EXISTS tenant_phone_number;")
