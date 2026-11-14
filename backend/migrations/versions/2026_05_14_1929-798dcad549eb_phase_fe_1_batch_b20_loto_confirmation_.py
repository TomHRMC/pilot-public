"""phase_fe_1_batch_b20_loto_confirmation_table

Revision ID: 798dcad549eb
Revises: 1a1bda72152a
Create Date: 2026-05-14 19:29:06

B20/A89 — LOTO Confirmation Table + Configurable Voice Guard

Creates:
  - loto_confirmation table (AppendOnlyMixin: created_at, created_by)
  - 2 triggers: audit_loto_confirmation_changes, trg_loto_confirmation_guard_created_immutable
  - platform_setting_catalog row: loto_confirmation_required
  - platform_setting row (NULL tenant default): loto_confirmation_required = false
  - RBAC permission seed: jobs.loto_confirm → technician + owner roles

Downgrade reverses all of the above.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "798dcad549eb"
down_revision = "1a1bda72152a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # 1. Create loto_confirmation table
    # -----------------------------------------------------------------------
    op.execute("""
        CREATE TABLE loto_confirmation (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
            job_id UUID NOT NULL REFERENCES job(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE RESTRICT,
            confirmed_at TIMESTAMPTZ NOT NULL,
            client_capture_at TIMESTAMPTZ NULL,
            server_received_at TIMESTAMPTZ NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by UUID NULL REFERENCES "user"(id) ON DELETE RESTRICT
        )
    """)

    # -----------------------------------------------------------------------
    # 2. Indexes
    # -----------------------------------------------------------------------
    op.execute("""
        CREATE INDEX ix_loto_confirmation_tenant_id ON loto_confirmation(tenant_id)
    """)
    op.execute("""
        CREATE INDEX ix_loto_confirmation_job_id ON loto_confirmation(job_id)
    """)
    op.execute("""
        CREATE INDEX ix_loto_confirmation_user_id ON loto_confirmation(user_id)
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_loto_confirmation_natural_key
            ON loto_confirmation(user_id, job_id, confirmed_at)
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_loto_confirmation_active_per_job_user
            ON loto_confirmation(job_id, user_id)
            WHERE is_active = true
    """)

    # -----------------------------------------------------------------------
    # 3. Audit trigger (AppendOnlyMixin standard — uses shared audit.log_changes())
    # -----------------------------------------------------------------------
    op.execute("""
        CREATE TRIGGER audit_loto_confirmation_changes
            AFTER INSERT OR UPDATE OR DELETE ON loto_confirmation
            FOR EACH ROW EXECUTE FUNCTION audit.log_changes()
    """)

    # -----------------------------------------------------------------------
    # 4. Immutable guard trigger (AppendOnlyMixin standard — guard created_at/created_by)
    # -----------------------------------------------------------------------
    op.execute("""
        CREATE TRIGGER trg_loto_confirmation_guard_created_immutable
            BEFORE UPDATE ON loto_confirmation
            FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()
    """)

    # -----------------------------------------------------------------------
    # 5. platform_setting_catalog — new loto_confirmation_required row
    # -----------------------------------------------------------------------
    op.execute("""
        INSERT INTO platform_setting_catalog
            (key, label, description, value_type, tenant_editable, allows_user_override,
             category, is_active, sort_order, created_at, updated_at)
        VALUES
            ('loto_confirmation_required',
             'LOTO Confirmation Required',
             'When enabled, Voice AI gates job completion and time-entry stop on LOTO confirmation. '
             'When disabled, LOTO confirmation is available as an optional audit capture.',
             'boolean',
             true,
             false,
             'safety',
             true,
             10,
             now(), now())
    """)

    # -----------------------------------------------------------------------
    # 6. platform_setting — platform default (NULL tenant_id = global default)
    # -----------------------------------------------------------------------
    op.execute("""
        INSERT INTO platform_setting
            (id, key, value, tenant_id, created_at, updated_at)
        VALUES
            (gen_random_uuid(),
             'loto_confirmation_required',
             'false'::jsonb,
             NULL,
             now(), now())
    """)

    # -----------------------------------------------------------------------
    # 7. RBAC: seed jobs.loto_confirm permission → technician + owner roles
    # -----------------------------------------------------------------------
    op.execute("""
        UPDATE tenant_user_role
        SET permissions = permissions || '["jobs.loto_confirm"]'::jsonb
        WHERE code IN ('technician', 'owner')
          AND NOT (permissions @> '["jobs.loto_confirm"]'::jsonb)
    """)


def downgrade() -> None:
    # -----------------------------------------------------------------------
    # 7. RBAC: remove jobs.loto_confirm from technician + owner roles
    # -----------------------------------------------------------------------
    op.execute("""
        UPDATE tenant_user_role
        SET permissions = (
            SELECT jsonb_agg(elem)
            FROM jsonb_array_elements(permissions) AS elem
            WHERE elem::text != '"jobs.loto_confirm"'
        )
        WHERE code IN ('technician', 'owner')
    """)

    # -----------------------------------------------------------------------
    # 6. Remove platform_setting default row
    # -----------------------------------------------------------------------
    op.execute("""
        DELETE FROM platform_setting
        WHERE key = 'loto_confirmation_required'
          AND tenant_id IS NULL
    """)

    # -----------------------------------------------------------------------
    # 5. Remove platform_setting_catalog row
    # -----------------------------------------------------------------------
    op.execute("""
        DELETE FROM platform_setting_catalog
        WHERE key = 'loto_confirmation_required'
    """)

    # -----------------------------------------------------------------------
    # 4 + 3. Drop triggers (shared functions audit.log_changes / guard_created_fields_immutable not dropped)
    # -----------------------------------------------------------------------
    op.execute(
        "DROP TRIGGER IF EXISTS trg_loto_confirmation_guard_created_immutable ON loto_confirmation"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_loto_confirmation_changes ON loto_confirmation"
    )

    # -----------------------------------------------------------------------
    # 2. Drop indexes (dropped automatically with table, but explicit is safer)
    # -----------------------------------------------------------------------
    op.execute("DROP INDEX IF EXISTS uq_loto_confirmation_active_per_job_user")
    op.execute("DROP INDEX IF EXISTS uq_loto_confirmation_natural_key")
    op.execute("DROP INDEX IF EXISTS ix_loto_confirmation_user_id")
    op.execute("DROP INDEX IF EXISTS ix_loto_confirmation_job_id")
    op.execute("DROP INDEX IF EXISTS ix_loto_confirmation_tenant_id")

    # -----------------------------------------------------------------------
    # 1. Drop table
    # -----------------------------------------------------------------------
    op.execute("DROP TABLE IF EXISTS loto_confirmation")
