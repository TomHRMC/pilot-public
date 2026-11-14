"""seed_missing_lookup_tables_batch_1

Seeds 21 lookup tables that had 0 rows in the live database and no Alembic
migration to populate them. Also promotes 8 tables from seed_test_data.py to
Alembic so they reach production automatically on deploy.

Tables seeded (system-level, tenant_id=NULL where applicable):
  - platform_role            (3 rows)
  - subscription_status      (4 rows)
  - jwk_status               (3 rows — no tenant_id)
  - sso_provider             (2 rows — code PK, no id/tenant_id)
  - customer_lifecycle_status(4 rows)
  - site_lifecycle_status    (3 rows)
  - supplier_lifecycle_status(2 rows)
  - supplier_item_category   (9 rows)
  - supplier_item_uom        (8 rows)
  - job_expense_category     (3 rows)
  - qpl_contact_action_type  (4 rows)
  - webhook_event_type       (3 rows — code PK, no id/tenant_id)
  - tenant_user_status       (3 new rows: invited, suspended, pending)
  - address_type             (4 rows — promoted from seed_test_data.py)
  - contact_type             (4 rows — promoted from seed_test_data.py)
  - taxability_code          (3 rows — promoted from seed_test_data.py)
  - currency                 (4 rows — promoted from seed_test_data.py)
  - job_status               (5 rows — promoted from seed_test_data.py)
  - app_service_category     (1 row  — promoted from seed_test_data.py)
  - app_service_provider     (1 row  — promoted from seed_test_data.py)
  - app_service              (1 row  — promoted from seed_test_data.py)

BEFORE UPDATE triggers don't fire on INSERT. No session_replication_role needed
on RDS — audit.log_changes() has the 'unknown_' entity_id fallback for code-PK tables.

Revision ID: dd4ed7ed5f3b
Revises: 381db126998f
Create Date: 2026-05-31 22:16:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "dd4ed7ed5f3b"
down_revision = "381db126998f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------------------------------------------------------------------
    # BEFORE UPDATE triggers don't fire on INSERT. audit.log_changes() has the
    # 'unknown_' entity_id fallback for non-UUID PKs (code-PK tables).
    # No session_replication_role bypass needed on RDS.
    # ---------------------------------------------------------------------------

    # ---------------------------------------------------------------------------
    # platform_role (3 rows)
    # PK: code (VARCHAR). No id UUID, no tenant_id.
    # permissions is JSONB.
    # ---------------------------------------------------------------------------
    op.execute("""
        INSERT INTO platform_role (code, name, description, permissions,
                                   is_default, is_active, created_at, updated_at)
        VALUES
            (
                'accountant',
                'Platform Accountant (Read-Only)',
                'Read-only access across all tenants; no write, no impersonation.',
                '{"read_all": true, "write": [], "impersonate_tenant": false, "manage_jwks": false}'::jsonb,
                false, true, now(), now()
            ),
            (
                'owner',
                'Platform Owner (Read/Write)',
                'Full read, selected write incl. JWKS and plan management; can impersonate tenants.',
                '{"read_all": true, "write": ["tenants", "users", "suppliers", "billing", "jwks", "plans", "notifications"], "impersonate_tenant": true, "manage_jwks": true}'::jsonb,
                false, true, now(), now()
            ),
            (
                'support',
                'Platform Support',
                'Limited write (tenants, users, billing, notifications); can impersonate tenants.',
                '{"read_all": true, "write": ["tenants", "users", "billing", "notifications"], "impersonate_tenant": true, "manage_jwks": false}'::jsonb,
                false, true, now(), now()
            )
        ON CONFLICT DO NOTHING;
    """)

    # ---------------------------------------------------------------------------
    # subscription_status (4 rows)
    # PK: id UUID. Has tenant_id.
    # ---------------------------------------------------------------------------
    op.execute("""
        INSERT INTO subscription_status (id, tenant_id, code, name,
                                         is_billing_active, created_at, updated_at)
        VALUES
            (gen_random_uuid(), NULL, 'trial',    'Trial',    true,  now(), now()),
            (gen_random_uuid(), NULL, 'active',   'Active',   true,  now(), now()),
            (gen_random_uuid(), NULL, 'past_due', 'Past Due', true,  now(), now()),
            (gen_random_uuid(), NULL, 'canceled', 'Canceled', false, now(), now())
        ON CONFLICT DO NOTHING;
    """)

    # ---------------------------------------------------------------------------
    # jwk_status (3 rows)
    # PK: id UUID. NO tenant_id column.
    # ---------------------------------------------------------------------------
    # jwk_status is AppendOnly (no updated_at / updated_by columns)
    op.execute("""
        INSERT INTO jwk_status (id, code, name, is_default, is_signable, created_at)
        VALUES
            (gen_random_uuid(), 'active',   'Active',   true,  true,  now()),
            (gen_random_uuid(), 'retiring', 'Retiring', false, false, now()),
            (gen_random_uuid(), 'retired',  'Retired',  false, false, now())
        ON CONFLICT DO NOTHING;
    """)

    # ---------------------------------------------------------------------------
    # sso_provider (2 rows)
    # PK: code (VARCHAR). No id UUID, no tenant_id.
    # ---------------------------------------------------------------------------
    op.execute("""
        INSERT INTO sso_provider (code, name, is_active, created_at, updated_at)
        VALUES
            ('google',    'Google',    true, now(), now()),
            ('microsoft', 'Microsoft', true, now(), now())
        ON CONFLICT DO NOTHING;
    """)

    # ---------------------------------------------------------------------------
    # customer_lifecycle_status (4 rows)
    # PK: id UUID. Has tenant_id.
    # ---------------------------------------------------------------------------
    op.execute("""
        INSERT INTO customer_lifecycle_status (id, tenant_id, code, name,
                                               is_default, is_active, created_at, updated_at)
        VALUES
            (gen_random_uuid(), NULL, 'prospect', 'Prospect', true,  true, now(), now()),
            (gen_random_uuid(), NULL, 'active',   'Active',   false, true, now(), now()),
            (gen_random_uuid(), NULL, 'dormant',  'Dormant',  false, true, now(), now()),
            (gen_random_uuid(), NULL, 'churned',  'Churned',  false, true, now(), now())
        ON CONFLICT DO NOTHING;
    """)

    # ---------------------------------------------------------------------------
    # site_lifecycle_status (3 rows)
    # PK: id UUID. Has tenant_id.
    # ---------------------------------------------------------------------------
    op.execute("""
        INSERT INTO site_lifecycle_status (id, tenant_id, code, name,
                                           is_default, is_active, created_at, updated_at)
        VALUES
            (gen_random_uuid(), NULL, 'active',       'Active',       true,  true, now(), now()),
            (gen_random_uuid(), NULL, 'construction', 'Construction', false, true, now(), now()),
            (gen_random_uuid(), NULL, 'closed',       'Closed',       false, true, now(), now())
        ON CONFLICT DO NOTHING;
    """)

    # ---------------------------------------------------------------------------
    # supplier_lifecycle_status (2 rows)
    # PK: id UUID. Has tenant_id.
    # ---------------------------------------------------------------------------
    op.execute("""
        INSERT INTO supplier_lifecycle_status (id, tenant_id, code, name,
                                               is_default, is_active, created_at, updated_at)
        VALUES
            (gen_random_uuid(), NULL, 'active',     'Active',     true,  true, now(), now()),
            (gen_random_uuid(), NULL, 'deprecated', 'Deprecated', false, true, now(), now())
        ON CONFLICT DO NOTHING;
    """)

    # ---------------------------------------------------------------------------
    # supplier_item_category (9 rows)
    # PK: id UUID. Has tenant_id. Seed from JSON schema seed_rows.
    # ---------------------------------------------------------------------------
    op.execute("""
        INSERT INTO supplier_item_category (id, tenant_id, code, name,
                                            is_active, created_at, updated_at)
        VALUES
            (gen_random_uuid(), NULL, 'wire_cable',     'Wire & Cable',                         true, now(), now()),
            (gen_random_uuid(), NULL, 'conduit_raceway','Conduit, Raceway & Strut',              true, now(), now()),
            (gen_random_uuid(), NULL, 'fittings',       'Fittings',                             true, now(), now()),
            (gen_random_uuid(), NULL, 'wiring_devices', 'Wiring Devices (Switches/Outlets)',    true, now(), now()),
            (gen_random_uuid(), NULL, 'dist_equip',     'Distribution & Control (Breakers/Panels)', true, now(), now()),
            (gen_random_uuid(), NULL, 'lighting',       'Lighting & Controls',                  true, now(), now()),
            (gen_random_uuid(), NULL, 'enclosures',     'Boxes & Enclosures',                   true, now(), now()),
            (gen_random_uuid(), NULL, 'tools_equip',    'Tools & Field Equipment',              true, now(), now()),
            (gen_random_uuid(), NULL, 'fasteners',      'Hardware & Fasteners',                 true, now(), now())
        ON CONFLICT DO NOTHING;
    """)

    # ---------------------------------------------------------------------------
    # supplier_item_uom (8 rows)
    # PK: id UUID. Has tenant_id. Seed from JSON schema seed_rows.
    # ---------------------------------------------------------------------------
    op.execute("""
        INSERT INTO supplier_item_uom (id, tenant_id, code, name,
                                       is_default, is_active, created_at, updated_at)
        VALUES
            (gen_random_uuid(), NULL, 'each',        'Each',        true,  true, now(), now()),
            (gen_random_uuid(), NULL, 'foot',        'Foot',        false, true, now(), now()),
            (gen_random_uuid(), NULL, 'roll',        'Roll',        false, true, now(), now()),
            (gen_random_uuid(), NULL, 'spool',       'Spool',       false, true, now(), now()),
            (gen_random_uuid(), NULL, 'box',         'Box',         false, true, now(), now()),
            (gen_random_uuid(), NULL, 'linear_foot', 'Linear Foot', false, true, now(), now()),
            (gen_random_uuid(), NULL, 'bag',         'Bag',         false, true, now(), now()),
            (gen_random_uuid(), NULL, 'package',     'Package',     false, true, now(), now())
        ON CONFLICT DO NOTHING;
    """)

    # ---------------------------------------------------------------------------
    # job_expense_category (3 rows)
    # PK: code (VARCHAR). Has tenant_id. No id UUID column.
    # ---------------------------------------------------------------------------
    op.execute("""
        INSERT INTO job_expense_category (code, tenant_id, name,
                                          is_default, is_active, created_at, updated_at)
        VALUES
            ('materials', NULL, 'Materials & Supplies', true,  true, now(), now()),
            ('equipment', NULL, 'Equipment Rental',     false, true, now(), now()),
            ('permits',   NULL, 'Permits & Fees',       false, true, now(), now())
        ON CONFLICT DO NOTHING;
    """)

    # ---------------------------------------------------------------------------
    # qpl_contact_action_type (4 rows)
    # PK: id UUID. Has tenant_id.
    # approve/request_change/message are Phase 2 — seeded inactive.
    # ---------------------------------------------------------------------------
    op.execute("""
        INSERT INTO qpl_contact_action_type (id, tenant_id, code, name,
                                              is_default, is_active, created_at, updated_at)
        VALUES
            (gen_random_uuid(), NULL, 'view',           'View',           true,  true,  now(), now()),
            (gen_random_uuid(), NULL, 'approve',        'Approve',        false, false, now(), now()),
            (gen_random_uuid(), NULL, 'request_change', 'Request Change', false, false, now(), now()),
            (gen_random_uuid(), NULL, 'message',        'Message',        false, false, now(), now())
        ON CONFLICT DO NOTHING;
    """)

    # ---------------------------------------------------------------------------
    # webhook_event_type (3 rows)
    # PK: code (VARCHAR). No id UUID, no tenant_id.
    # ---------------------------------------------------------------------------
    op.execute("""
        INSERT INTO webhook_event_type (code, name, is_active, created_at, updated_at)
        VALUES
            ('invoice.paid',   'Invoice Paid',   true, now(), now()),
            ('job.updated',    'Job Updated',    true, now(), now()),
            ('quote.accepted', 'Quote Accepted', true, now(), now())
        ON CONFLICT DO NOTHING;
    """)

    # ---------------------------------------------------------------------------
    # tenant_user_status — 3 new rows (active=1 already exists via seed_test_data.py)
    # ON CONFLICT DO NOTHING safely skips any existing rows.
    # PK: id UUID. Also has tenant_id and code columns.
    # ---------------------------------------------------------------------------
    op.execute("""
        INSERT INTO tenant_user_status (id, tenant_id, code, name, is_default, is_active,
                                        created_at, updated_at)
        VALUES
            (gen_random_uuid(), NULL, 'invited',   'Invited',   false, true, now(), now()),
            (gen_random_uuid(), NULL, 'suspended', 'Suspended', false, true, now(), now()),
            (gen_random_uuid(), NULL, 'pending',   'Pending',   false, true, now(), now())
        ON CONFLICT DO NOTHING;
    """)

    # ---------------------------------------------------------------------------
    # address_type (4 rows) — promoted from seed_test_data.py
    # PK: code (VARCHAR). Has tenant_id.
    # service_location is default (matches seed_test_data.py behaviour).
    # ---------------------------------------------------------------------------
    op.execute("""
        INSERT INTO address_type (code, tenant_id, name, is_default, is_active,
                                   created_at, updated_at)
        VALUES
            ('billing',          NULL, 'Billing Address',  false, true, now(), now()),
            ('service_location', NULL, 'Service Location', true,  true, now(), now()),
            ('mailing',          NULL, 'Mailing Address',  false, true, now(), now()),
            ('shipping',         NULL, 'Shipping Address', false, true, now(), now())
        ON CONFLICT DO NOTHING;
    """)

    # ---------------------------------------------------------------------------
    # contact_type (4 rows) — promoted from seed_test_data.py
    # PK: code (VARCHAR). Has tenant_id.
    # ---------------------------------------------------------------------------
    op.execute("""
        INSERT INTO contact_type (code, tenant_id, name, is_default, is_active,
                                   created_at, updated_at)
        VALUES
            ('primary',       NULL, 'Primary Contact',  true,  true, now(), now()),
            ('billing',       NULL, 'Billing Contact',  false, true, now(), now()),
            ('technical',     NULL, 'Technical Contact',false, true, now(), now()),
            ('decision_maker',NULL, 'Decision Maker',   false, true, now(), now())
        ON CONFLICT DO NOTHING;
    """)

    # ---------------------------------------------------------------------------
    # taxability_code (3 rows) — promoted from seed_test_data.py
    # PK: code (VARCHAR). No tenant_id.
    # ---------------------------------------------------------------------------
    op.execute("""
        INSERT INTO taxability_code (code, name, description, is_active,
                                      created_at, updated_at)
        VALUES
            ('taxable',    'Taxable',    'Standard sales tax applies',                              true, now(), now()),
            ('exempt',     'Tax Exempt', 'No sales tax (customer has exemption certificate)',       true, now(), now()),
            ('zero_rated', 'Zero-Rated', '0% tax rate (different from exempt for reporting)',      true, now(), now())
        ON CONFLICT DO NOTHING;
    """)

    # ---------------------------------------------------------------------------
    # currency (4 rows) — promoted from seed_test_data.py
    # PK: code (VARCHAR). No tenant_id.
    # ---------------------------------------------------------------------------
    op.execute("""
        INSERT INTO currency (code, name, symbol, is_active, created_at, updated_at)
        VALUES
            ('USD', 'US Dollar',       '$',  true, now(), now()),
            ('CAD', 'Canadian Dollar', 'C$', true, now(), now()),
            ('EUR', 'Euro',            '€',  true, now(), now()),
            ('GBP', 'British Pound',   '£',  true, now(), now())
        ON CONFLICT DO NOTHING;
    """)

    # ---------------------------------------------------------------------------
    # job_status (5 rows) — promoted from seed_test_data.py
    # PK: id UUID. Has tenant_id, is_terminal.
    # ---------------------------------------------------------------------------
    op.execute("""
        INSERT INTO job_status (id, tenant_id, code, name,
                                 is_terminal, is_default, is_active, created_at, updated_at)
        VALUES
            (gen_random_uuid(), NULL, 'draft',       'Draft',       false, true,  true, now(), now()),
            (gen_random_uuid(), NULL, 'scheduled',   'Scheduled',   false, false, true, now(), now()),
            (gen_random_uuid(), NULL, 'in_progress', 'In Progress', false, false, true, now(), now()),
            (gen_random_uuid(), NULL, 'completed',   'Completed',   true,  false, true, now(), now()),
            (gen_random_uuid(), NULL, 'cancelled',   'Cancelled',   true,  false, true, now(), now())
        ON CONFLICT DO NOTHING;
    """)

    # ---------------------------------------------------------------------------
    # app_service_category (1 row) — promoted from seed_test_data.py
    # PK: code (VARCHAR). No tenant_id.
    # ---------------------------------------------------------------------------
    op.execute("""
        INSERT INTO app_service_category (code, description, is_active,
                                           created_at, updated_at)
        VALUES
            ('accounting', 'Accounting & Bookkeeping integrations', true, now(), now())
        ON CONFLICT DO NOTHING;
    """)

    # ---------------------------------------------------------------------------
    # app_service_provider (1 row) — promoted from seed_test_data.py
    # PK: code (VARCHAR). No tenant_id.
    # ---------------------------------------------------------------------------
    op.execute("""
        INSERT INTO app_service_provider (code, description, is_active,
                                           created_at, updated_at)
        VALUES
            ('intuit', 'Intuit (QuickBooks Online)', true, now(), now())
        ON CONFLICT DO NOTHING;
    """)

    # ---------------------------------------------------------------------------
    # app_service (1 row) — promoted from seed_test_data.py
    # PK: id UUID. Has tenant_id (NULL = global). FKs to category and provider.
    # external_account_id = NULL (no QB realm yet at system level).
    # ---------------------------------------------------------------------------
    op.execute("""
        INSERT INTO app_service (id, tenant_id, name, category_code, provider_code,
                                  is_active, external_account_id, created_at, updated_at)
        VALUES
            (
                gen_random_uuid(),
                NULL,
                'QuickBooks Online',
                'accounting',
                'intuit',
                true,
                NULL,
                now(),
                now()
            )
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    # Remove only the system-level rows added by this migration.
    # Tenant-specific overrides (tenant_id IS NOT NULL) are untouched.
    # Tables with code PK are keyed on code; UUID-PK tables are keyed on
    # (code, tenant_id IS NULL) to avoid touching tenant rows.
    #
    # Deletes are ordered child-first to respect FK constraints without needing
    # session_replication_role (which requires superuser on RDS).
    op.execute("""
        DELETE FROM app_service
        WHERE tenant_id IS NULL AND name = 'QuickBooks Online'
          AND category_code = 'accounting' AND provider_code = 'intuit';
    """)

    op.execute("""
        DELETE FROM app_service_provider WHERE code = 'intuit';
    """)

    op.execute("""
        DELETE FROM app_service_category WHERE code = 'accounting';
    """)

    op.execute("""
        DELETE FROM job_status
        WHERE tenant_id IS NULL
          AND code IN ('draft', 'scheduled', 'in_progress', 'completed', 'cancelled');
    """)

    op.execute("""
        DELETE FROM currency WHERE code IN ('USD', 'CAD', 'EUR', 'GBP');
    """)

    op.execute("""
        DELETE FROM taxability_code WHERE code IN ('taxable', 'exempt', 'zero_rated');
    """)

    op.execute("""
        DELETE FROM contact_type
        WHERE tenant_id IS NULL
          AND code IN ('primary', 'billing', 'technical', 'decision_maker');
    """)

    op.execute("""
        DELETE FROM address_type
        WHERE tenant_id IS NULL
          AND code IN ('billing', 'service_location', 'mailing', 'shipping');
    """)

    op.execute("""
        DELETE FROM tenant_user_status
        WHERE tenant_id IS NULL
          AND code IN ('invited', 'suspended', 'pending');
    """)

    op.execute("""
        DELETE FROM webhook_event_type
        WHERE code IN ('invoice.paid', 'job.updated', 'quote.accepted');
    """)

    op.execute("""
        DELETE FROM qpl_contact_action_type
        WHERE tenant_id IS NULL
          AND code IN ('view', 'approve', 'request_change', 'message');
    """)

    op.execute("""
        DELETE FROM job_expense_category
        WHERE tenant_id IS NULL
          AND code IN ('materials', 'equipment', 'permits');
    """)

    op.execute("""
        DELETE FROM supplier_item_uom
        WHERE tenant_id IS NULL
          AND code IN ('each', 'foot', 'roll', 'spool', 'box', 'linear_foot', 'bag', 'package');
    """)

    op.execute("""
        DELETE FROM supplier_item_category
        WHERE tenant_id IS NULL
          AND code IN ('wire_cable', 'conduit_raceway', 'fittings', 'wiring_devices',
                       'dist_equip', 'lighting', 'enclosures', 'tools_equip', 'fasteners');
    """)

    op.execute("""
        DELETE FROM supplier_lifecycle_status
        WHERE tenant_id IS NULL AND code IN ('active', 'deprecated');
    """)

    op.execute("""
        DELETE FROM site_lifecycle_status
        WHERE tenant_id IS NULL AND code IN ('active', 'construction', 'closed');
    """)

    op.execute("""
        DELETE FROM customer_lifecycle_status
        WHERE tenant_id IS NULL AND code IN ('prospect', 'active', 'dormant', 'churned');
    """)

    op.execute("""
        DELETE FROM sso_provider WHERE code IN ('google', 'microsoft');
    """)

    op.execute("""
        DELETE FROM jwk_status WHERE code IN ('active', 'retiring', 'retired');
    """)

    op.execute("""
        DELETE FROM subscription_status
        WHERE tenant_id IS NULL
          AND code IN ('trial', 'active', 'past_due', 'canceled');
    """)

    op.execute("""
        DELETE FROM platform_role WHERE code IN ('accountant', 'owner', 'support');
    """)
