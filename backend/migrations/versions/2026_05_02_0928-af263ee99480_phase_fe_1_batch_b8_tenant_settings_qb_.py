"""phase_fe_1_batch_b8_tenant_settings_qb_background_sync

Revision ID: af263ee99480
Revises: 85097a763895
Create Date: 2026-05-02 09:28:00.000000

B8/A50+A51: Add QB auto-expiry settings and background sync settings to tenant_settings.
"""

from alembic import op

revision: str = "af263ee99480"
down_revision: str | None = "85097a763895"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE tenant_settings
            -- QB auto-expiry per entity type (A50) — default OFF per Tier 1 #2 Decision 9
            ADD COLUMN qb_auto_expire_customer_enabled   BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN qb_auto_expire_customer_direction TEXT    NULL,
            ADD COLUMN qb_auto_expire_quote_enabled      BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN qb_auto_expire_quote_direction    TEXT    NULL,
            ADD COLUMN qb_auto_expire_invoice_enabled    BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN qb_auto_expire_invoice_direction  TEXT    NULL,
            ADD COLUMN qb_auto_expire_expense_enabled    BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN qb_auto_expire_expense_direction  TEXT    NULL,
            ADD COLUMN qb_auto_expire_days               INTEGER NULL,
            ADD COLUMN qb_pre_warning_days               INTEGER NULL,
            -- Background sync (A51)
            ADD COLUMN background_sync_enabled           BOOLEAN NOT NULL DEFAULT TRUE,
            ADD COLUMN background_sync_wifi_only         BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN background_sync_battery_floor_pct INTEGER NOT NULL DEFAULT 20,
            ADD COLUMN background_sync_push_interval_minutes  INTEGER NULL
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE tenant_settings
            DROP COLUMN IF EXISTS background_sync_push_interval_minutes,
            DROP COLUMN IF EXISTS background_sync_battery_floor_pct,
            DROP COLUMN IF EXISTS background_sync_wifi_only,
            DROP COLUMN IF EXISTS background_sync_enabled,
            DROP COLUMN IF EXISTS qb_pre_warning_days,
            DROP COLUMN IF EXISTS qb_auto_expire_days,
            DROP COLUMN IF EXISTS qb_auto_expire_expense_direction,
            DROP COLUMN IF EXISTS qb_auto_expire_expense_enabled,
            DROP COLUMN IF EXISTS qb_auto_expire_invoice_direction,
            DROP COLUMN IF EXISTS qb_auto_expire_invoice_enabled,
            DROP COLUMN IF EXISTS qb_auto_expire_quote_direction,
            DROP COLUMN IF EXISTS qb_auto_expire_quote_enabled,
            DROP COLUMN IF EXISTS qb_auto_expire_customer_direction,
            DROP COLUMN IF EXISTS qb_auto_expire_customer_enabled
    """)
