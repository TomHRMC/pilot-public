"""phase_4_7_add_missing_default_values_task5

Revision ID: 189c7c0f77fd
Revises: 93e12247a8ec
Create Date: 2026-04-07 14:27:08.537787+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "189c7c0f77fd"
down_revision: str | None = "93e12247a8ec"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add database-level DEFAULT values for 35+ columns across 15+ tables.

    This ensures data consistency even if application code fails to set values.
    All columns already have Field(default=...) in SQLModel classes, but these
    Python defaults don't enforce database-level constraints.
    """

    # Tenant Settings (4 defaults)
    op.execute(
        "ALTER TABLE tenant_settings ALTER COLUMN default_labor_rate_cents SET DEFAULT 8500"
    )
    op.execute(
        "ALTER TABLE tenant_settings ALTER COLUMN default_billable_labor_rate_cents SET DEFAULT 15000"
    )
    op.execute(
        "ALTER TABLE tenant_settings ALTER COLUMN default_quote_validity_days SET DEFAULT 30"
    )
    op.execute(
        "ALTER TABLE tenant_settings ALTER COLUMN default_invoice_terms_days SET DEFAULT 0"
    )

    # Job Financials (3 defaults)
    op.execute("ALTER TABLE job ALTER COLUMN actual_labor_cost_cents SET DEFAULT 0")
    op.execute("ALTER TABLE job ALTER COLUMN actual_material_cost_cents SET DEFAULT 0")
    op.execute("ALTER TABLE job ALTER COLUMN actual_profit_cents SET DEFAULT 0")

    # Quote Totals (4 defaults)
    op.execute("ALTER TABLE quote ALTER COLUMN subtotal_cents SET DEFAULT 0")
    op.execute("ALTER TABLE quote ALTER COLUMN tax_cents SET DEFAULT 0")
    op.execute("ALTER TABLE quote ALTER COLUMN total_cents SET DEFAULT 0")
    op.execute("ALTER TABLE quote ALTER COLUMN currency SET DEFAULT 'USD'")

    # Change Order Totals (3 defaults - no currency column)
    op.execute("ALTER TABLE change_order ALTER COLUMN subtotal_cents SET DEFAULT 0")
    op.execute("ALTER TABLE change_order ALTER COLUMN tax_cents SET DEFAULT 0")
    op.execute("ALTER TABLE change_order ALTER COLUMN total_cents SET DEFAULT 0")

    # Line Item Defaults - Invoice (4 defaults)
    op.execute("ALTER TABLE invoice_line ALTER COLUMN quantity SET DEFAULT 1")
    op.execute("ALTER TABLE invoice_line ALTER COLUMN unit_price_cents SET DEFAULT 0")
    op.execute("ALTER TABLE invoice_line ALTER COLUMN total_cents SET DEFAULT 0")
    op.execute("ALTER TABLE invoice_line ALTER COLUMN subtotal_cents SET DEFAULT 0")

    # Line Item Defaults - Quote (3 defaults - quantity already has default)
    op.execute("ALTER TABLE quote_line ALTER COLUMN unit_price_cents SET DEFAULT 0")
    op.execute("ALTER TABLE quote_line ALTER COLUMN total_cents SET DEFAULT 0")
    op.execute("ALTER TABLE quote_line ALTER COLUMN subtotal_cents SET DEFAULT 0")

    # Line Item Defaults - Change Order (4 defaults)
    op.execute("ALTER TABLE change_order_line ALTER COLUMN quantity SET DEFAULT 1")
    op.execute(
        "ALTER TABLE change_order_line ALTER COLUMN unit_price_cents SET DEFAULT 0"
    )
    op.execute("ALTER TABLE change_order_line ALTER COLUMN total_cents SET DEFAULT 0")
    op.execute(
        "ALTER TABLE change_order_line ALTER COLUMN subtotal_cents SET DEFAULT 0"
    )

    # System/Operational Defaults
    op.execute("ALTER TABLE job_expense ALTER COLUMN is_billable SET DEFAULT true")
    op.execute(
        "ALTER TABLE notification_outbox ALTER COLUMN attempt_count SET DEFAULT 0"
    )
    op.execute("ALTER TABLE notification_outbox ALTER COLUMN priority SET DEFAULT 5")
    op.execute(
        "ALTER TABLE notification_outbox ALTER COLUMN status SET DEFAULT 'pending'"
    )
    op.execute(
        "ALTER TABLE webhook_delivery_attempt ALTER COLUMN attempt_no SET DEFAULT 1"
    )
    op.execute(
        "ALTER TABLE webhook_delivery_attempt ALTER COLUMN status SET DEFAULT 'pending'"
    )
    op.execute(
        "ALTER TABLE idempotency_key ALTER COLUMN status SET DEFAULT 'in_progress'"
    )
    op.execute(
        "ALTER TABLE integration_sync_mapping ALTER COLUMN sync_preference SET DEFAULT 'aevofab_master'"
    )
    op.execute(
        "ALTER TABLE integration_sync_conflict ALTER COLUMN status SET DEFAULT 'pending'"
    )

    # Billing/Subscription Defaults
    op.execute("ALTER TABLE subscription ALTER COLUMN quantity_seats SET DEFAULT 1")
    op.execute(
        "ALTER TABLE subscription ALTER COLUMN billing_interval SET DEFAULT 'monthly'"
    )
    op.execute(
        "ALTER TABLE subscription ALTER COLUMN cancel_at_period_end SET DEFAULT false"
    )
    op.execute(
        "ALTER TABLE subscription_usage ALTER COLUMN used_quantity SET DEFAULT 0"
    )
    op.execute("ALTER TABLE usage_ledger ALTER COLUMN quantity SET DEFAULT 1")
    op.execute("ALTER TABLE usage_ledger ALTER COLUMN is_reported SET DEFAULT false")

    # Voice AI Defaults
    op.execute(
        "ALTER TABLE voice_command_log ALTER COLUMN is_successful SET DEFAULT true"
    )
    op.execute(
        "ALTER TABLE connector_run_log ALTER COLUMN status SET DEFAULT 'running'"
    )
    op.execute("ALTER TABLE connector_run_log ALTER COLUMN items_fetched SET DEFAULT 0")


def downgrade() -> None:
    """Remove all database-level DEFAULT values (reverse order for safety)."""

    # Voice AI Defaults
    op.execute("ALTER TABLE connector_run_log ALTER COLUMN items_fetched DROP DEFAULT")
    op.execute("ALTER TABLE connector_run_log ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE voice_command_log ALTER COLUMN is_successful DROP DEFAULT")

    # Billing/Subscription Defaults
    op.execute("ALTER TABLE usage_ledger ALTER COLUMN is_reported DROP DEFAULT")
    op.execute("ALTER TABLE usage_ledger ALTER COLUMN quantity DROP DEFAULT")
    op.execute("ALTER TABLE subscription_usage ALTER COLUMN used_quantity DROP DEFAULT")
    op.execute(
        "ALTER TABLE subscription ALTER COLUMN cancel_at_period_end DROP DEFAULT"
    )
    op.execute("ALTER TABLE subscription ALTER COLUMN billing_interval DROP DEFAULT")
    op.execute("ALTER TABLE subscription ALTER COLUMN quantity_seats DROP DEFAULT")

    # System/Operational Defaults
    op.execute("ALTER TABLE integration_sync_conflict ALTER COLUMN status DROP DEFAULT")
    op.execute(
        "ALTER TABLE integration_sync_mapping ALTER COLUMN sync_preference DROP DEFAULT"
    )
    op.execute("ALTER TABLE idempotency_key ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE webhook_delivery_attempt ALTER COLUMN status DROP DEFAULT")
    op.execute(
        "ALTER TABLE webhook_delivery_attempt ALTER COLUMN attempt_no DROP DEFAULT"
    )
    op.execute("ALTER TABLE notification_outbox ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE notification_outbox ALTER COLUMN priority DROP DEFAULT")
    op.execute(
        "ALTER TABLE notification_outbox ALTER COLUMN attempt_count DROP DEFAULT"
    )
    op.execute("ALTER TABLE job_expense ALTER COLUMN is_billable DROP DEFAULT")

    # Line Item Defaults - Change Order
    op.execute("ALTER TABLE change_order_line ALTER COLUMN subtotal_cents DROP DEFAULT")
    op.execute("ALTER TABLE change_order_line ALTER COLUMN total_cents DROP DEFAULT")
    op.execute(
        "ALTER TABLE change_order_line ALTER COLUMN unit_price_cents DROP DEFAULT"
    )
    op.execute("ALTER TABLE change_order_line ALTER COLUMN quantity DROP DEFAULT")

    # Line Item Defaults - Quote
    op.execute("ALTER TABLE quote_line ALTER COLUMN subtotal_cents DROP DEFAULT")
    op.execute("ALTER TABLE quote_line ALTER COLUMN total_cents DROP DEFAULT")
    op.execute("ALTER TABLE quote_line ALTER COLUMN unit_price_cents DROP DEFAULT")

    # Line Item Defaults - Invoice
    op.execute("ALTER TABLE invoice_line ALTER COLUMN subtotal_cents DROP DEFAULT")
    op.execute("ALTER TABLE invoice_line ALTER COLUMN total_cents DROP DEFAULT")
    op.execute("ALTER TABLE invoice_line ALTER COLUMN unit_price_cents DROP DEFAULT")
    op.execute("ALTER TABLE invoice_line ALTER COLUMN quantity DROP DEFAULT")

    # Change Order Totals
    op.execute("ALTER TABLE change_order ALTER COLUMN total_cents DROP DEFAULT")
    op.execute("ALTER TABLE change_order ALTER COLUMN tax_cents DROP DEFAULT")
    op.execute("ALTER TABLE change_order ALTER COLUMN subtotal_cents DROP DEFAULT")

    # Quote Totals
    op.execute("ALTER TABLE quote ALTER COLUMN currency DROP DEFAULT")
    op.execute("ALTER TABLE quote ALTER COLUMN total_cents DROP DEFAULT")
    op.execute("ALTER TABLE quote ALTER COLUMN tax_cents DROP DEFAULT")
    op.execute("ALTER TABLE quote ALTER COLUMN subtotal_cents DROP DEFAULT")

    # Job Financials
    op.execute("ALTER TABLE job ALTER COLUMN actual_profit_cents DROP DEFAULT")
    op.execute("ALTER TABLE job ALTER COLUMN actual_material_cost_cents DROP DEFAULT")
    op.execute("ALTER TABLE job ALTER COLUMN actual_labor_cost_cents DROP DEFAULT")

    # Tenant Settings
    op.execute(
        "ALTER TABLE tenant_settings ALTER COLUMN default_invoice_terms_days DROP DEFAULT"
    )
    op.execute(
        "ALTER TABLE tenant_settings ALTER COLUMN default_quote_validity_days DROP DEFAULT"
    )
    op.execute(
        "ALTER TABLE tenant_settings ALTER COLUMN default_billable_labor_rate_cents DROP DEFAULT"
    )
    op.execute(
        "ALTER TABLE tenant_settings ALTER COLUMN default_labor_rate_cents DROP DEFAULT"
    )
