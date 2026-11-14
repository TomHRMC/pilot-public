"""
Validate all data against CHECK constraints before applying migration.
This script queries the database to find any rows that violate the constraints
that will be added in the migration.
"""

from sqlalchemy import text

from app.core.database import get_db

# List of all CHECK constraints to validate
CONSTRAINTS = [
    {
        "name": "contact_endpoint_channel_chk",
        "table": "contact_endpoint",
        "sql": "SELECT DISTINCT channel FROM contact_endpoint WHERE channel NOT IN ('email', 'sms')",
    },
    {
        "name": "contact_endpoint_verification_status_chk",
        "table": "contact_endpoint",
        "sql": "SELECT DISTINCT verification_status FROM contact_endpoint WHERE verification_status NOT IN ('pending', 'verified', 'failed')",
    },
    {
        "name": "user_endpoint_channel_chk",
        "table": "user_endpoint",
        "sql": "SELECT DISTINCT channel FROM user_endpoint WHERE channel NOT IN ('email', 'sms')",
    },
    {
        "name": "user_endpoint_verification_status_chk",
        "table": "user_endpoint",
        "sql": "SELECT DISTINCT verification_status FROM user_endpoint WHERE verification_status NOT IN ('pending', 'verified', 'failed')",
    },
    {
        "name": "auth_jwk_alg_chk",
        "table": "auth_jwk",
        "sql": "SELECT DISTINCT alg FROM auth_jwk WHERE alg NOT IN ('RS256', 'ES256', 'EdDSA')",
    },
    {
        "name": "connector_config_mode_chk",
        "table": "connector_config",
        "sql": "SELECT DISTINCT mode FROM connector_config WHERE mode NOT IN ('api','scrape','manual')",
    },
    {
        "name": "idempotency_key_status_chk",
        "table": "idempotency_key",
        "sql": "SELECT DISTINCT status FROM idempotency_key WHERE status NOT IN ('processing','complete','failed')",
    },
    {
        "name": "integration_credential_connection_status_chk",
        "table": "integration_credential",
        "sql": "SELECT DISTINCT connection_status FROM integration_credential WHERE connection_status NOT IN ('active','expired','revoked','error')",
    },
    {
        "name": "integration_sync_log_outcome_chk",
        "table": "integration_sync_log",
        "sql": "SELECT DISTINCT outcome FROM integration_sync_log WHERE outcome NOT IN ('success','partial','error','not_found')",
    },
    {
        "name": "integration_sync_mapping_direction_chk",
        "table": "integration_sync_mapping",
        "sql": "SELECT DISTINCT direction FROM integration_sync_mapping WHERE direction NOT IN ('outbound','inbound','bidirectional')",
    },
    {
        "name": "integration_sync_mapping_sync_strategy_chk",
        "table": "integration_sync_mapping",
        "sql": "SELECT DISTINCT sync_strategy FROM integration_sync_mapping WHERE sync_strategy NOT IN ('full','delta','manual')",
    },
    {
        "name": "notification_channel_type_chk",
        "table": "notification_channel",
        "sql": "SELECT DISTINCT type FROM notification_channel WHERE type NOT IN ('email','sms','webhook')",
    },
    {
        "name": "webhook_delivery_attempt_outcome_chk",
        "table": "webhook_delivery_attempt",
        "sql": "SELECT DISTINCT outcome FROM webhook_delivery_attempt WHERE outcome NOT IN ('pending','delivered','failed','timeout')",
    },
    {
        "name": "webhook_endpoint_status_chk",
        "table": "webhook_endpoint",
        "sql": "SELECT DISTINCT status FROM webhook_endpoint WHERE status NOT IN ('enabled','disabled','invalid')",
    },
    {
        "name": "webhook_event_status_chk",
        "table": "webhook_event",
        "sql": "SELECT DISTINCT status FROM webhook_event WHERE status NOT IN ('pending','processing','dispatched','failed','cancelled')",
    },
    {
        "name": "pricebook_item_version_pricing_strategy_chk",
        "table": "pricebook_item_version",
        "sql": "SELECT DISTINCT pricing_strategy FROM pricebook_item_version WHERE pricing_strategy NOT IN ('fixed','tiered','usage','formula')",
    },
    {
        "name": "quote_message_action_type_chk",
        "table": "quote_message",
        "sql": "SELECT DISTINCT action_type FROM quote_message WHERE action_type NOT IN ('created','modified','sent','viewed','accepted','rejected','expired')",
    },
    {
        "name": "conversation_message_role_chk",
        "table": "conversation_message",
        "sql": "SELECT DISTINCT role FROM conversation_message WHERE role NOT IN ('user','assistant','system')",
    },
    {
        "name": "conversation_session_session_status_chk",
        "table": "conversation_session",
        "sql": "SELECT DISTINCT session_status FROM conversation_session WHERE session_status NOT IN ('active','completed','timeout','error')",
    },
    # Numeric constraints
    {
        "name": "webhook_delivery_attempt_http_status_chk",
        "table": "webhook_delivery_attempt",
        "sql": "SELECT http_status FROM webhook_delivery_attempt WHERE http_status IS NOT NULL AND (http_status < 100 OR http_status >= 600)",
    },
    {
        "name": "invoice_line_quantity_chk",
        "table": "invoice_line",
        "sql": "SELECT id, quantity FROM invoice_line WHERE quantity <= 0",
    },
    {
        "name": "change_order_line_quantity_chk",
        "table": "change_order_line",
        "sql": "SELECT id, quantity FROM change_order_line WHERE quantity <= 0",
    },
    {
        "name": "quote_line_quantity_chk",
        "table": "quote_line",
        "sql": "SELECT id, quantity FROM quote_line WHERE quantity <= 0",
    },
    {
        "name": "voice_command_log_intent_confidence_chk",
        "table": "voice_command_log",
        "sql": "SELECT id, intent_confidence FROM voice_command_log WHERE intent_confidence IS NOT NULL AND (intent_confidence < 0 OR intent_confidence > 1)",
    },
]


def main():
    db = next(get_db())
    violations = []

    print("Validating CHECK constraints...")
    print("=" * 80)

    for constraint in CONSTRAINTS:
        try:
            result = db.execute(text(constraint["sql"]))
            rows = result.fetchall()

            if rows:
                print(f"\n❌ VIOLATION: {constraint['name']}")
                print(f"   Table: {constraint['table']}")
                print(f"   Invalid values found: {len(rows)}")
                for row in rows[:5]:  # Show first 5
                    print(f"   - {row}")
                if len(rows) > 5:
                    print(f"   ... and {len(rows) - 5} more")
                violations.append(
                    {
                        "constraint": constraint["name"],
                        "count": len(rows),
                        "samples": rows[:5],
                    }
                )
            else:
                print(f"✓ {constraint['name']}")
        except Exception as e:
            print(f"⚠️  ERROR checking {constraint['name']}: {e}")

    print("\n" + "=" * 80)
    if violations:
        print(f"\n❌ FOUND {len(violations)} CONSTRAINT VIOLATIONS")
        print("\nYou must fix these data issues before applying the migration.")
        return 1
    else:
        print("\n✅ ALL CONSTRAINTS VALIDATED SUCCESSFULLY")
        print("Safe to proceed with migration.")
        return 0


if __name__ == "__main__":
    exit(main())
