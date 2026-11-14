#!/usr/bin/env python3
"""
Add all missing CHECK constraints to SQLModel classes.
This script reads model files and adds missing CHECK constraints based on the JSON schema audit.
"""

import re
from pathlib import Path

# Define all missing constraints by model file and class
CONSTRAINTS_TO_ADD = {
    "app/models/system.py": {
        "ConnectorConfig": [
            ("connector_config_mode_chk", "mode IN ('api','scrape','manual')"),
        ],
        "IdempotencyKey": [
            (
                "idempotency_key_status_chk",
                "status IN ('in_progress','succeeded','failed')",
            ),
        ],
        "NotificationOutbox": [
            ("notification_outbox_channel_chk", "channel IN ('email','sms','in_app')"),
            (
                "notification_outbox_recipient_presence_chk",
                "(recipient_contact_id IS NOT NULL OR recipient_user_id IS NOT NULL OR to_address IS NOT NULL)",
            ),
            (
                "notification_outbox_recipient_exclusive_chk",
                "((recipient_contact_id IS NOT NULL)::int + (recipient_user_id IS NOT NULL)::int + (to_address IS NOT NULL)::int) = 1",
            ),
            (
                "notification_outbox_inapp_requires_user_chk",
                "(channel <> 'in_app') OR (recipient_user_id IS NOT NULL)",
            ),
        ],
        "NotificationDeliveryAttempt": [
            (
                "notification_delivery_attempt_status_chk",
                "status IN ('queued','delivered','bounced','rejected','throttled','error')",
            ),
        ],
        "NotificationType": [
            ("notification_type_audience_chk", "audience IN ('tenant','customer')"),
        ],
    },
    "app/models/ai.py": {
        "ConversationMessage": [
            ("conv_msg_role_chk", "role IN ('user', 'assistant', 'system')"),
        ],
        "ConversationSession": [
            ("conv_session_status_chk", "status IN ('active', 'ended', 'abandoned')"),
        ],
    },
    "app/models/quoting.py": {
        "QuoteMessage": [
            (
                "quote_message_action_type_chk",
                "action_type IN ('contact', 'tenant_user', 'system')",
            ),
        ],
    },
    "app/models/billing.py": {
        "Subscription": [
            (
                "subscription_billing_interval_chk",
                "billing_interval IN ('monthly','annual')",
            ),
        ],
        "IntegrationSyncLog": [
            ("isl_status_chk", "status IN ('success', 'failed', 'partial_success')"),
        ],
        "IntegrationSyncMapping": [
            (
                "sync_preference_chk",
                "sync_preference IN ('pilot_master', 'external_master', 'bi_directional')",
            ),
        ],
    },
    "app/models/catalog.py": {
        "PricebookItemVersion": [
            ("piv_valid_period_chk", "NOT isempty(valid_period)"),
        ],
        "SupplierItemPrice": [
            ("sip_valid_period_chk", "NOT isempty(valid_period)"),
        ],
        "TaxRateVersion": [
            ("tax_rate_version_valid_period_chk", "NOT isempty(valid_period)"),
        ],
        "TenantMarkupVersion": [
            ("tmv_valid_period_chk", "NOT isempty(valid_period)"),
            (
                "tmv_markup_presence_chk",
                "(markup_pct IS NOT NULL) OR (markup_amt_cents IS NOT NULL)",
            ),
        ],
        "ProductPlanVersion": [
            ("product_plan_version_valid_period_chk", "NOT isempty(valid_period)"),
        ],
        "ProductPlanProductFeatureVersion": [
            ("pppfv_valid_period_chk", "NOT isempty(valid_period)"),
            (
                "pppfv_limit_enforcement_chk",
                "limit_enforcement IN ('block','allow_overage')",
            ),
        ],
    },
    "app/models/fulfillment.py": {
        "InvoiceLine": [
            (
                "invoice_line_source_type_chk",
                "source_type IN ('quote_line', 'change_order_line', 'ad_hoc')",
            ),
        ],
        "JobExpense": [
            (
                "job_expense_markup_presence_chk",
                "(markup_pct IS NOT NULL) OR (markup_amt_cents IS NOT NULL)",
            ),
        ],
    },
}


def add_check_constraints_to_class(
    content: str, class_name: str, constraints: list
) -> str:
    """Add CHECK constraints to a class that doesn't have __table_args__."""
    # Find the class definition
    class_pattern = rf"(class {class_name}\([^)]+\):\s*\n\s+__tablename__\s*=\s*['\"][^'\"]+['\"]\s*\n)"

    match = re.search(class_pattern, content)
    if not match:
        print(f"  ⚠️  Could not find class {class_name}")
        return content

    # Build the __table_args__ section
    table_args_lines = ["    __table_args__ = (\n"]
    for name, condition in constraints:
        table_args_lines.append("        CheckConstraint(\n")
        table_args_lines.append(f'            "{condition}",\n')
        table_args_lines.append(f'            name="{name}",\n')
        table_args_lines.append("        ),\n")
    table_args_lines.append("    )\n\n")

    table_args_str = "".join(table_args_lines)

    # Insert after __tablename__
    new_content = content[: match.end()] + table_args_str + content[match.end() :]

    return new_content


def update_model_file(file_path: str, classes_to_update: dict):
    """Update a model file with missing CHECK constraints."""
    path = Path(file_path)
    if not path.exists():
        print(f"❌ File not found: {file_path}")
        return False

    content = path.read_text()

    # Check if CheckConstraint is imported
    if "CheckConstraint" not in content:
        # Add import
        import_pattern = r"(from sqlalchemy import [^)]+)"
        import_match = re.search(import_pattern, content)
        if import_match:
            imports = import_match.group(1)
            if "CheckConstraint" not in imports:
                new_imports = imports.rstrip(")") + ", CheckConstraint"
                if not imports.endswith(","):
                    new_imports = imports + ", CheckConstraint"
                content = content.replace(imports, new_imports)

    # Update each class
    for class_name, constraints in classes_to_update.items():
        print(f"  Adding {len(constraints)} constraint(s) to {class_name}")
        content = add_check_constraints_to_class(content, class_name, constraints)

    # Write back
    path.write_text(content)
    print(f"✅ Updated {file_path}")
    return True


def main():
    """Main execution."""
    print("Adding missing CHECK constraints to model files...\n")

    for file_path, classes in CONSTRAINTS_TO_ADD.items():
        print(f"Processing {file_path}:")
        update_model_file(file_path, classes)
        print()

    print("✅ All missing CHECK constraints added!")
    print("\nNext steps:")
    print(
        "1. Run: alembic revision --autogenerate -m 'phase_4_7_add_missing_check_constraints_task6'"
    )
    print("2. Review the migration and remove any audit.event table operations")
    print("3. Run: alembic upgrade head")


if __name__ == "__main__":
    main()
