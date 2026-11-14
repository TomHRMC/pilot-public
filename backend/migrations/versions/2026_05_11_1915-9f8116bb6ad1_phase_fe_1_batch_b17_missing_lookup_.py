"""phase_fe_1_batch_b17_missing_lookup_table_seeds

FIND-167 (S1 Critical): Seed 4 empty lookup tables that block core invoicing,
quoting, and payment workflows on a fresh production database.

Tables seeded:
  - invoice_status (5 rows): draft, issued, paid, void, writeoff
  - payment_status (4 rows): pending, succeeded, failed, canceled
  - payment_type   (6 rows): card, ach, wallet, bank_debit, manual_check, venmo
  - qco_line_type  (4 rows): labor, material, misc, discount

BEFORE UPDATE triggers don't fire on INSERT (immutability triggers are designed
for application writes, not migration seed inserts).

Revision ID: 9f8116bb6ad1
Revises: 6350c51bc555
Create Date: 2026-05-11 19:15:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "9f8116bb6ad1"
down_revision = "6350c51bc555"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------------------------------------------------------------------
    # BEFORE UPDATE triggers (guard_created_immutable, set_updated_at) don't fire
    # on INSERT. audit.log_changes() has the 'unknown_' entity_id fallback in place.
    # No session_replication_role bypass needed on RDS.
    # ---------------------------------------------------------------------------

    # --- invoice_status (5 rows) ---
    # tenant_id=NULL → system-level rows (available to all tenants)
    op.execute("""
        INSERT INTO invoice_status (id, tenant_id, code, name, is_terminal, is_default, is_active,
                                    created_at, updated_at)
        VALUES
            (gen_random_uuid(), NULL, 'draft',    'Draft',    false, true,  true, now(), now()),
            (gen_random_uuid(), NULL, 'issued',   'Issued',   false, false, true, now(), now()),
            (gen_random_uuid(), NULL, 'paid',     'Paid',     true,  false, true, now(), now()),
            (gen_random_uuid(), NULL, 'void',     'Void',     true,  false, true, now(), now()),
            (gen_random_uuid(), NULL, 'writeoff', 'Write-Off',true,  false, true, now(), now())
        ON CONFLICT DO NOTHING;
    """)

    # --- payment_status (4 rows) ---
    op.execute("""
        INSERT INTO payment_status (id, tenant_id, code, name, is_terminal, is_default, is_active,
                                    created_at, updated_at)
        VALUES
            (gen_random_uuid(), NULL, 'pending',   'Pending',   false, true,  true, now(), now()),
            (gen_random_uuid(), NULL, 'succeeded', 'Succeeded', true,  false, true, now(), now()),
            (gen_random_uuid(), NULL, 'failed',    'Failed',    true,  false, true, now(), now()),
            (gen_random_uuid(), NULL, 'canceled',  'Canceled',  true,  false, true, now(), now())
        ON CONFLICT DO NOTHING;
    """)

    # --- payment_type (6 rows) ---
    # Note: payment_type model has no is_terminal or is_default columns
    op.execute("""
        INSERT INTO payment_type (id, tenant_id, code, name, is_active,
                                  created_at, updated_at)
        VALUES
            (gen_random_uuid(), NULL, 'card',         'Card',         true, now(), now()),
            (gen_random_uuid(), NULL, 'ach',          'ACH',          true, now(), now()),
            (gen_random_uuid(), NULL, 'wallet',       'Wallet',       true, now(), now()),
            (gen_random_uuid(), NULL, 'bank_debit',   'Bank Debit',   true, now(), now()),
            (gen_random_uuid(), NULL, 'manual_check', 'Manual Check', true, now(), now()),
            (gen_random_uuid(), NULL, 'venmo',        'Venmo',        true, now(), now())
        ON CONFLICT DO NOTHING;
    """)

    # --- qco_line_type (4 rows) ---
    # IMPORTANT: schema JSON has corrupt names (copy-paste of address names).
    # Authoritative names from FIND-167 plan entry (Tom's decision 2026-05-08):
    #   labor/Labor, material/Material, misc/Misc, discount/Discount
    op.execute("""
        INSERT INTO qco_line_type (id, tenant_id, code, name, is_default, is_active,
                                   created_at, updated_at)
        VALUES
            (gen_random_uuid(), NULL, 'labor',    'Labor',    true,  true, now(), now()),
            (gen_random_uuid(), NULL, 'material', 'Material', false, true, now(), now()),
            (gen_random_uuid(), NULL, 'misc',     'Misc',     false, true, now(), now()),
            (gen_random_uuid(), NULL, 'discount', 'Discount', false, true, now(), now())
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    # Remove only the system-level rows added by this migration (tenant_id IS NULL).
    # Tenant-specific overrides (tenant_id IS NOT NULL) are untouched.
    op.execute("""
        DELETE FROM invoice_status
        WHERE tenant_id IS NULL
          AND code IN ('draft', 'issued', 'paid', 'void', 'writeoff');
    """)

    op.execute("""
        DELETE FROM payment_status
        WHERE tenant_id IS NULL
          AND code IN ('pending', 'succeeded', 'failed', 'canceled');
    """)

    op.execute("""
        DELETE FROM payment_type
        WHERE tenant_id IS NULL
          AND code IN ('card', 'ach', 'wallet', 'bank_debit', 'manual_check', 'venmo');
    """)

    op.execute("""
        DELETE FROM qco_line_type
        WHERE tenant_id IS NULL
          AND code IN ('labor', 'material', 'misc', 'discount');
    """)
