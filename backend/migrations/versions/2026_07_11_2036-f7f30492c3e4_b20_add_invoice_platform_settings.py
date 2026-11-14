"""b20_add_invoice_platform_settings

Revision ID: f7f30492c3e4
Revises: 8f5be25d95d5
Create Date: 2026-07-11 20:36:23

B20: Add 3 platform_setting_catalog entries + system default rows for:
  - square_integration_enabled (boolean, category=billing)
  - default_payment_terms (string, category=billing, allowed_values matches chk_invoice_payment_terms)
  - default_billing_mode (string, category=billing, allowed_values matches chk_invoice_billing_mode)

Per design doc §B.3 — allowed_values mirrors the same enums as the DB CHECK constraints
on invoice.payment_terms and invoice.billing_mode (single source of truth).

Notes:
  - platform_setting.id is a UUID PK with no DB server default → use gen_random_uuid().
  - platform_setting unique constraint uq_platform_setting_key_tenant is on (key, tenant_id).
    PostgreSQL treats NULL as NOT EQUAL to NULL in unique constraints, so ON CONFLICT
    does not catch (key, NULL) duplicates. Use WHERE NOT EXISTS instead.
  - session_replication_role='replica' bypasses FK checks during data migration.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "f7f30492c3e4"
down_revision = "8f5be25d95d5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # --- platform_setting_catalog entries (key is PK — ON CONFLICT (key) is safe) ---

    # 1. square_integration_enabled
    op.execute("""
        INSERT INTO platform_setting_catalog (
            key, label, description, value_type, tenant_editable,
            allows_user_override, category, is_active, sort_order,
            created_at, updated_at
        )
        VALUES (
            'square_integration_enabled',
            'Square payment integration enabled',
            'When enabled, tenants can require card-on-file via Square before work begins.',
            'boolean',
            true,
            false,
            'billing',
            true,
            100,
            now(),
            now()
        )
        ON CONFLICT (key) DO NOTHING;
    """)

    # 2. default_payment_terms — allowed_values mirrors chk_invoice_payment_terms
    op.execute("""
        INSERT INTO platform_setting_catalog (
            key, label, description, value_type, tenant_editable,
            allows_user_override, allowed_values, category, is_active, sort_order,
            created_at, updated_at
        )
        VALUES (
            'default_payment_terms',
            'Default invoice payment terms',
            'When invoice.payment_terms is NULL, the invoice builder pre-selects this value.',
            'string',
            true,
            false,
            '["due_on_receipt","net_15","net_30","custom_date"]'::jsonb,
            'billing',
            true,
            101,
            now(),
            now()
        )
        ON CONFLICT (key) DO NOTHING;
    """)

    # 3. default_billing_mode — allowed_values mirrors chk_invoice_billing_mode
    op.execute("""
        INSERT INTO platform_setting_catalog (
            key, label, description, value_type, tenant_editable,
            allows_user_override, allowed_values, category, is_active, sort_order,
            created_at, updated_at
        )
        VALUES (
            'default_billing_mode',
            'Default invoice billing mode',
            'When the invoice builder opens a blank invoice, this is the default tab selection.',
            'string',
            true,
            false,
            '["line_item","progress"]'::jsonb,
            'billing',
            true,
            102,
            now(),
            now()
        )
        ON CONFLICT (key) DO NOTHING;
    """)

    # --- platform_setting system defaults (tenant_id = NULL) ---
    # Use WHERE NOT EXISTS because the unique constraint (key, tenant_id) does NOT
    # match NULL = NULL in PostgreSQL, so ON CONFLICT won't fire for NULL tenant_id rows.

    op.execute("""
        INSERT INTO platform_setting (id, key, value, tenant_id, created_at, updated_at)
        SELECT gen_random_uuid(), 'square_integration_enabled', 'false'::jsonb, NULL, now(), now()
        WHERE NOT EXISTS (
            SELECT 1 FROM platform_setting
            WHERE key = 'square_integration_enabled' AND tenant_id IS NULL
        );
    """)

    op.execute("""
        INSERT INTO platform_setting (id, key, value, tenant_id, created_at, updated_at)
        SELECT gen_random_uuid(), 'default_payment_terms', '"due_on_receipt"'::jsonb, NULL, now(), now()
        WHERE NOT EXISTS (
            SELECT 1 FROM platform_setting
            WHERE key = 'default_payment_terms' AND tenant_id IS NULL
        );
    """)

    op.execute("""
        INSERT INTO platform_setting (id, key, value, tenant_id, created_at, updated_at)
        SELECT gen_random_uuid(), 'default_billing_mode', '"line_item"'::jsonb, NULL, now(), now()
        WHERE NOT EXISTS (
            SELECT 1 FROM platform_setting
            WHERE key = 'default_billing_mode' AND tenant_id IS NULL
        );
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM platform_setting
        WHERE key IN ('square_integration_enabled', 'default_payment_terms', 'default_billing_mode')
          AND tenant_id IS NULL;
    """)
    op.execute("""
        DELETE FROM platform_setting_catalog
        WHERE key IN ('square_integration_enabled', 'default_payment_terms', 'default_billing_mode');
    """)
