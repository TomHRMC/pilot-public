#!/usr/bin/env python3
"""Check which columns from the checklist exist in the physical database."""

import os

import psycopg2

# Get database URL from environment
db_url = os.getenv(
    "DATABASE_URL", "postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev"
)

# All 200 fields from required-defaults-columns-json.md
checklist = [
    ("tenant", "is_active"),
    # tenant_settings removed (FIND-086): replaced by platform_setting_catalog + platform_setting
    ("platform_setting_catalog", "key"),
    ("platform_setting", "id"),
    ("platform_role", "permissions"),
    ("platform_role", "is_default"),
    ("platform_role", "is_active"),
    ("user", "is_platform_user"),
    ("user", "failed_login_count"),
    ("user", "require_password_reset"),
    ("user", "mfa_enforced"),
    ("user", "preferred_mfa_channel"),
    ("user", "is_active"),
    ("user_endpoint", "is_primary"),
    ("user_endpoint", "verification_status"),
    ("user_endpoint", "consent_status"),
    ("user_endpoint", "is_active"),
    ("user_preference", "preferences"),
    ("tenant_user_role", "permissions"),
    ("tenant_user_role", "is_default"),
    ("tenant_user_role", "is_active"),
    ("tenant_user_status", "is_default"),
    ("tenant_user_status", "is_active"),
    ("tenant_user", "is_active"),
    ("customer_lifecycle_status", "is_default"),
    ("customer_lifecycle_status", "is_active"),
    ("site_lifecycle_status", "is_default"),
    ("site_lifecycle_status", "is_active"),
    ("supplier_lifecycle_status", "is_default"),
    ("supplier_lifecycle_status", "is_active"),
    ("quote_status", "is_terminal"),
    ("quote_status", "is_default"),
    ("quote_status", "is_active"),
    ("job_status", "is_terminal"),
    ("job_status", "is_default"),
    ("job_status", "is_active"),
    ("customer", "type"),
    ("customer", "is_active"),
    ("site", "is_active"),
    ("supplier", "is_active"),
    ("app_service_category", "is_active"),
    ("app_service_provider", "is_active"),
    ("app_service", "is_active"),
    ("contact", "is_active"),
    ("entity_type", "is_default"),
    ("entity_type", "is_active"),
    ("contact_type", "is_default"),
    ("contact_type", "is_active"),
    ("entity_contact", "is_primary"),
    ("address", "country"),
    ("address", "is_active"),
    ("address_type", "is_default"),
    ("address_type", "is_active"),
    ("entity_address", "is_primary"),
    ("entity_address", "is_active"),
    ("quote", "subtotal_cents"),
    ("quote", "tax_cents"),
    ("quote", "total_cents"),
    ("quote", "currency"),
    ("quote", "is_active"),
    ("quote_version", "is_active"),
    ("qco_line_type", "is_default"),
    ("qco_line_type", "is_active"),
    ("quote_line", "quantity"),
    ("quote_line", "unit_price_cents"),
    ("quote_line", "total_cents"),
    ("quote_line", "subtotal_cents"),
    ("quote_line", "is_active"),
    ("taxability_code", "is_active"),
    ("quote_link_status", "is_default"),
    ("quote_link_status", "is_active"),
    ("quote_public_link", "max_uses"),
    ("quote_public_link", "used_count"),
    ("qpl_contact_action_type", "is_default"),
    ("qpl_contact_action_type", "is_active"),
    ("quote_public_link_contact_action", "occurred_at"),
    ("quote_acceptance", "approved_at"),
    ("quote_acceptance", "terms_acknowledged"),
    ("job", "actual_labor_cost_cents"),
    ("job", "actual_material_cost_cents"),
    ("job", "actual_profit_cents"),
    ("job", "is_active"),
    ("job_notes", "customer_visible"),
    ("tenant_markup_version", "valid_period"),
    ("tenant_markup_version", "recorded_at"),
    ("job_expense_category", "is_default"),
    ("job_expense_category", "is_active"),
    ("job_expense", "incurred_at"),
    ("job_expense", "is_billable"),
    ("change_order", "subtotal_cents"),
    ("change_order", "tax_cents"),
    ("change_order", "total_cents"),
    ("change_order", "is_active"),
    ("change_order_line", "quantity"),
    ("change_order_line", "unit_price_cents"),
    ("change_order_line", "total_cents"),
    ("change_order_line", "subtotal_cents"),
    ("change_order_line", "is_active"),
    ("invoice_status", "is_terminal"),
    ("invoice_status", "is_default"),
    ("invoice_status", "is_active"),
    ("invoice", "subtotal_cents"),
    ("invoice", "tax_cents"),
    ("invoice", "total_cents"),
    ("invoice", "balance_due_cents"),
    ("invoice", "currency"),
    ("invoice", "is_active"),
    ("invoice_line", "quantity"),
    ("invoice_line", "unit_price_cents"),
    ("invoice_line", "total_cents"),
    ("invoice_line", "subtotal_cents"),
    ("invoice_line", "is_active"),
    ("invoice_line_tax_component", "is_active"),
    ("payment_status", "is_terminal"),
    ("payment_status", "is_default"),
    ("payment_status", "is_active"),
    ("currency", "is_active"),
    ("payment", "is_active"),
    ("payment_type", "is_active"),
    ("supplier_item_category", "is_active"),
    ("supplier_item_uom", "is_default"),
    ("supplier_item_uom", "is_active"),
    ("supplier_item", "is_active"),
    ("supplier_item_price", "currency"),
    ("supplier_item_price", "valid_period"),
    ("pricing_cache", "currency"),
    ("tax_rate_version", "recorded_at"),
    ("pricebook_item", "is_active"),
    ("pricebook_item_version", "recorded_at"),
    ("product_plan", "is_active"),
    ("product_plan_version", "recorded_at"),
    ("discount_version", "recorded_at"),
    ("product_feature", "is_active"),
    ("product_plan_product_feature_version", "recorded_at"),
    ("product_plan_product_feature_version", "limit_enforcement"),
    ("tenant_product_feature_override", "enabled"),
    ("subscription_status", "is_billing_active"),
    ("subscription", "quantity_seats"),
    ("subscription", "started_at"),
    ("subscription", "billing_interval"),
    ("subscription", "cancel_at_period_end"),
    ("subscription", "is_active"),
    ("subscription_usage", "used_quantity"),
    ("usage_ledger", "occurred_at"),
    ("usage_ledger", "quantity"),
    ("usage_ledger", "is_reported"),
    ("notification_channel", "is_active"),
    ("notification_type", "is_active"),
    ("contact_endpoint", "is_primary"),
    ("contact_endpoint", "consent_status"),
    ("contact_endpoint", "verification_status"),
    ("contact_endpoint", "is_active"),
    # contact_notification_pref, tenant_user_notification_pref, tenant_notification_default
    # removed — FIND-080/B21 legacy table drop (2026-05-18)
    ("notification_template", "is_active"),
    ("notification_event", "occurred_at"),
    ("notification_outbox", "status"),
    ("notification_outbox", "attempt_count"),
    ("notification_outbox", "priority"),
    ("notification_delivery_attempt", "attempted_at"),
    ("notification_delivery_attempt", "retryable"),
    ("auth_refresh_token", "issued_at"),
    ("sso_provider", "is_active"),
    ("auth_mfa_otp", "attempt_count"),
    ("auth_password_history", "changed_at"),
    ("jwk_status", "is_default"),
    ("jwk_status", "is_signable"),
    ("tenant_domain", "is_active"),
    ("tenant_user_invite", "is_active"),
    ("idempotency_key", "first_seen_at"),
    ("idempotency_key", "status"),
    ("webhook_endpoint", "enabled"),
    ("webhook_event_type", "is_active"),
    ("webhook_event", "signature_valid"),
    ("webhook_delivery_attempt", "attempt_no"),
    ("webhook_delivery_attempt", "status"),
    ("webhook_delivery_attempt", "requested_at"),
    ("integration_credential", "connection_status"),
    ("integration_sync_mapping", "sync_preference"),
    ("integration_sync_mapping", "last_synced_at"),
    ("integration_sync_conflict", "status"),
    ("integration_sync_log", "records_processed"),
    ("integration_sync_log", "records_failed"),
    ("conversation_session", "status"),
    ("conversation_session", "is_active"),
    ("voice_command_log", "is_successful"),
    ("connector_config", "mode"),
    ("connector_config", "enabled"),
    ("connector_config", "failure_count"),
    ("connector_run_log", "started_at"),
    ("connector_run_log", "status"),
    ("connector_run_log", "items_fetched"),
]


def main():
    # Connect using psycopg2
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    existing = []
    missing = []

    for table, column in checklist:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = %s 
                AND column_name = %s
            )
        """,
            (table, column),
        )
        exists = cur.fetchone()[0]
        if exists:
            existing.append((table, column))
        else:
            missing.append((table, column))

    print("=== Column Verification Results ===")
    print(f"Total in checklist: {len(checklist)}")
    print(f"Existing: {len(existing)}")
    print(f"Missing: {len(missing)}")
    print()

    if missing:
        print("=== MISSING COLUMNS (Do NOT include in migration) ===")
        for table, column in missing:
            print(f"  - {table}.{column}")
        print()

    print("=== EXISTING COLUMNS (Include in migration) ===")
    for table, column in existing:
        print(f"  - {table}.{column}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
