"""sd06_invoice_reminder_columns_and_platform_settings

Revision ID: eb757cc7d9eb
Revises: 1923b2d3aa14
Create Date: 2026-07-06 21:09:00.000000

SD-06B: Add invoice reminder tracking columns and 3 new platform_setting_catalog keys.
- invoice.last_reminder_sent_at: nullable TIMESTAMPTZ — NULL means no reminder sent
- invoice.reminder_count: NOT NULL with server_default='0'
- platform_setting_catalog: 3 new keys (invoice_reminder_days_1/2/3)
- platform_setting: null-tenant default rows for the 3 new keys
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "eb757cc7d9eb"
down_revision = "1923b2d3aa14"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Invoice reminder tracking columns ---
    op.add_column(
        "invoice",
        sa.Column("last_reminder_sent_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "invoice",
        sa.Column(
            "reminder_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    # --- New platform_setting_catalog keys for tenant-configurable reminder schedule ---
    # Use SET LOCAL session_replication_role = 'replica' to bypass FK triggers on data inserts
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("""
        INSERT INTO platform_setting_catalog
            (key, label, value_type, category, tenant_editable, allows_user_override,
             description, sort_order, is_active, created_at, updated_at)
        VALUES
            ('invoice_reminder_days_1', 'First invoice reminder (days overdue)', 'integer',
             'billing', true, false,
             'Days overdue before first invoice reminder fires', 110, true, NOW(), NOW()),
            ('invoice_reminder_days_2', 'Second invoice reminder (days overdue)', 'integer',
             'billing', true, false,
             'Days overdue before second invoice reminder fires', 120, true, NOW(), NOW()),
            ('invoice_reminder_days_3', 'Final invoice reminder (days overdue)', 'integer',
             'billing', true, false,
             'Days overdue before final invoice reminder fires', 130, true, NOW(), NOW())
        ON CONFLICT (key) DO NOTHING;
    """)
    # Insert null-tenant default platform_setting rows for each new key
    # id is UUID PK — use gen_random_uuid()
    op.execute("""
        INSERT INTO platform_setting (id, key, tenant_id, value, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'invoice_reminder_days_1', NULL, '1'::jsonb, NOW(), NOW()),
            (gen_random_uuid(), 'invoice_reminder_days_2', NULL, '7'::jsonb, NOW(), NOW()),
            (gen_random_uuid(), 'invoice_reminder_days_3', NULL, '14'::jsonb, NOW(), NOW())
        ON CONFLICT (key, tenant_id) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("""
        DELETE FROM platform_setting WHERE key IN (
            'invoice_reminder_days_1', 'invoice_reminder_days_2', 'invoice_reminder_days_3'
        ) AND tenant_id IS NULL;
    """)
    op.execute("""
        DELETE FROM platform_setting_catalog WHERE key IN (
            'invoice_reminder_days_1', 'invoice_reminder_days_2', 'invoice_reminder_days_3'
        );
    """)
    op.drop_column("invoice", "reminder_count")
    op.drop_column("invoice", "last_reminder_sent_at")
