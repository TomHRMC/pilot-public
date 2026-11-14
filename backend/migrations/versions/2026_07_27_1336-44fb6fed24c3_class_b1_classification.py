"""class_b1_classification

Revision ID: 44fb6fed24c3
Revises: 57475453234c
Create Date: 2026-07-27 13:36:00

CLASS-B1: Job/Site/Customer Classification Foundation

Groups:
  B.1 — job.priority TEXT+CHECK (standard/rush/emergency), 3-part NOT NULL
  B.2 — job_type lookup table + triggers + partial unique indexes + 11 platform seed rows
          + job.job_type_id nullable FK
  B.3 — site.site_type TEXT+CHECK (commercial/residential/industrial), 3-part NOT NULL,
          backfilled from customer.type
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "44fb6fed24c3"
down_revision = "57475453234c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # B.1 — job.priority (TEXT + CHECK, 3-part NOT NULL on existing rows)
    # =========================================================================

    # Step 1: Add nullable
    op.execute("ALTER TABLE job ADD COLUMN priority TEXT;")

    # Step 2: Backfill existing rows
    op.execute("UPDATE job SET priority = 'standard' WHERE priority IS NULL;")

    # Step 3: Lock — default, NOT NULL, CHECK
    op.execute("ALTER TABLE job ALTER COLUMN priority SET DEFAULT 'standard';")
    op.execute("ALTER TABLE job ALTER COLUMN priority SET NOT NULL;")
    op.execute(
        "ALTER TABLE job ADD CONSTRAINT job_priority_chk "
        "CHECK (priority IN ('standard','urgent','emergency'));"
    )

    # =========================================================================
    # B.2 — job_type lookup table
    # =========================================================================

    op.execute(
        """
        CREATE TABLE job_type (
            created_at        TIMESTAMPTZ    NOT NULL,
            updated_at        TIMESTAMPTZ    NOT NULL,
            created_by        UUID           REFERENCES "user"(id) ON DELETE RESTRICT,
            updated_by        UUID           REFERENCES "user"(id) ON DELETE RESTRICT,
            id                UUID           PRIMARY KEY,
            tenant_id         UUID           REFERENCES tenant(id) ON DELETE RESTRICT,
            code              TEXT           NOT NULL,
            label             TEXT           NOT NULL,
            sort_order        INTEGER        NOT NULL DEFAULT 100,
            is_active         BOOLEAN        NOT NULL DEFAULT true
        );
        """
    )

    # Partial unique indexes (two partials required since NULL != NULL in plain unique)
    op.execute(
        "CREATE UNIQUE INDEX uq_job_type_platform_code "
        "ON job_type (code) WHERE tenant_id IS NULL;"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_job_type_tenant_code "
        "ON job_type (tenant_id, code) WHERE tenant_id IS NOT NULL;"
    )
    op.execute("CREATE INDEX ix_job_type_tenant_id ON job_type (tenant_id);")

    # Triggers on job_type — mirror customer trigger set exactly (MCP-verified DDL)
    op.execute(
        "CREATE TRIGGER trg_job_type_set_updated_at "
        "BEFORE UPDATE ON job_type "
        "FOR EACH ROW EXECUTE FUNCTION set_updated_at();"
    )
    op.execute(
        "CREATE TRIGGER audit_job_type_changes "
        "AFTER INSERT OR DELETE OR UPDATE ON job_type "
        "FOR EACH ROW EXECUTE FUNCTION audit.log_changes();"
    )
    op.execute(
        "CREATE TRIGGER trg_job_type_guard_created_immutable "
        "BEFORE UPDATE ON job_type "
        "FOR EACH ROW EXECUTE FUNCTION guard_created_fields_immutable();"
    )

    # Platform-default seed rows (11 rows, tenant_id = NULL, ON CONFLICT DO NOTHING)
    op.execute(
        """
        INSERT INTO job_type (id, tenant_id, code, label, sort_order, is_active, created_at, updated_at)
        VALUES
          (gen_random_uuid(), NULL, 'service_call',       'Service Call',              10,  true, NOW(), NOW()),
          (gen_random_uuid(), NULL, 'troubleshoot',       'Troubleshoot / Diagnostic', 20,  true, NOW(), NOW()),
          (gen_random_uuid(), NULL, 'panel_upgrade',      'Panel Upgrade',             30,  true, NOW(), NOW()),
          (gen_random_uuid(), NULL, 'rewire',             'Rewire',                    40,  true, NOW(), NOW()),
          (gen_random_uuid(), NULL, 'lighting',           'Lighting',                  50,  true, NOW(), NOW()),
          (gen_random_uuid(), NULL, 'generator_install',  'Generator Install',         60,  true, NOW(), NOW()),
          (gen_random_uuid(), NULL, 'ev_charger_install', 'EV Charger Install',        70,  true, NOW(), NOW()),
          (gen_random_uuid(), NULL, 'new_construction',   'New Construction',          80,  true, NOW(), NOW()),
          (gen_random_uuid(), NULL, 'inspection',         'Inspection',                90,  true, NOW(), NOW()),
          (gen_random_uuid(), NULL, 'warranty',           'Warranty',                  100, true, NOW(), NOW()),
          (gen_random_uuid(), NULL, 'other',              'Other',                     999, true, NOW(), NOW())
        ON CONFLICT DO NOTHING;
        """
    )

    # job.job_type_id — nullable FK (no backfill needed; existing jobs have no type)
    op.execute(
        "ALTER TABLE job ADD COLUMN job_type_id UUID "
        "REFERENCES job_type(id) ON DELETE SET NULL;"
    )
    op.execute("CREATE INDEX ix_job_job_type_id ON job (job_type_id);")

    # =========================================================================
    # B.3 — site.site_type (TEXT + CHECK, 3-part NOT NULL, backfilled from customer)
    # =========================================================================

    # Step 1: Add nullable
    op.execute("ALTER TABLE site ADD COLUMN site_type TEXT;")

    # Step 2: Backfill from owning customer (company → commercial, else residential)
    op.execute(
        """
        UPDATE site s SET site_type = CASE
            WHEN c.type = 'company' THEN 'commercial'
            ELSE 'residential'
        END
        FROM customer c
        WHERE s.customer_id = c.id AND s.site_type IS NULL;
        """
    )
    # Safety net for any orphan rows (FK is NOT NULL, so shouldn't happen)
    op.execute("UPDATE site SET site_type = 'residential' WHERE site_type IS NULL;")

    # Step 3: Lock — default, NOT NULL, CHECK
    op.execute("ALTER TABLE site ALTER COLUMN site_type SET DEFAULT 'residential';")
    op.execute("ALTER TABLE site ALTER COLUMN site_type SET NOT NULL;")
    op.execute(
        "ALTER TABLE site ADD CONSTRAINT site_type_chk "
        "CHECK (site_type IN ('commercial','residential','industrial'));"
    )


def downgrade() -> None:
    # =========================================================================
    # Reverse B.3 — site.site_type
    # =========================================================================
    op.execute("ALTER TABLE site DROP CONSTRAINT IF EXISTS site_type_chk;")
    op.execute("ALTER TABLE site DROP COLUMN IF EXISTS site_type;")

    # =========================================================================
    # Reverse B.2 — job.job_type_id + job_type table
    # =========================================================================
    op.execute("DROP INDEX IF EXISTS ix_job_job_type_id;")
    op.execute("ALTER TABLE job DROP COLUMN IF EXISTS job_type_id;")

    # Drop triggers before table
    op.execute(
        "DROP TRIGGER IF EXISTS trg_job_type_guard_created_immutable ON job_type;"
    )
    op.execute("DROP TRIGGER IF EXISTS audit_job_type_changes ON job_type;")
    op.execute("DROP TRIGGER IF EXISTS trg_job_type_set_updated_at ON job_type;")

    # Drop indexes before table
    op.execute("DROP INDEX IF EXISTS ix_job_type_tenant_id;")
    op.execute("DROP INDEX IF EXISTS uq_job_type_tenant_code;")
    op.execute("DROP INDEX IF EXISTS uq_job_type_platform_code;")

    # Drop table (platform seed rows vanish with it)
    op.execute("DROP TABLE IF EXISTS job_type;")

    # =========================================================================
    # Reverse B.1 — job.priority
    # =========================================================================
    op.execute("ALTER TABLE job DROP CONSTRAINT IF EXISTS job_priority_chk;")
    op.execute("ALTER TABLE job DROP COLUMN IF EXISTS priority;")
