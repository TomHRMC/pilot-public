"""add_missing_audit_triggers

Revision ID: e3783b6d2b8d
Revises: 0a26d3a349c2
Create Date: 2026-03-31 20:11:52.161830+00:00

Phase 4.5, Task 6: Add audit triggers to ~80 critical tables for compliance and security.

Context:
- The audit.log_changes() PL/pgSQL function already exists (created in Phase 4, Task 20)
- 12 tables already have audit triggers (customer, invoice, job, quote, payment, site,
  contact, address, job_time_entry, job_expense, supplier_item, pricebook_item)
- This migration adds audit triggers to all remaining critical tables
- Organized by priority: CRITICAL → HIGH → MEDIUM → AUTH

Excluded Tables (pure reference/lookup, no audit needed):
- Status tables: invoice_status, job_status, payment_status, subscription_status, etc.
- Type tables: address_type, contact_type, entity_type, payment_type, etc.
- Category tables: app_service_category, job_expense_category, supplier_item_category, etc.
- Static enums: currency, jwk_status, notification_channel, notification_type, etc.
- Feature definitions: product_feature (template data, not user data)

Reference: dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md Task #6
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e3783b6d2b8d"
down_revision: str | None = "0a26d3a349c2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Add audit triggers to ~80 critical tables for comprehensive change tracking.

    Trigger Pattern:
        CREATE TRIGGER audit_[table]_changes
        AFTER INSERT OR UPDATE OR DELETE ON [table]
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();

    Note: Using "audit_" prefix to match existing trigger naming convention
    (existing triggers use "audit_customer_changes", not "trg_customer_audit_changes")
    """

    # ==========================================================================
    # CRITICAL PRIORITY - Security, Compliance, Legal Protection
    # ==========================================================================

    # User table - CRITICAL for security audit
    op.execute("""
        CREATE TRIGGER audit_user_changes
        AFTER INSERT OR UPDATE OR DELETE ON "user"
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # Tenant table - CRITICAL for compliance
    op.execute("""
        CREATE TRIGGER audit_tenant_changes
        AFTER INSERT OR UPDATE OR DELETE ON tenant
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # Change Order table - CRITICAL for legal protection
    op.execute("""
        CREATE TRIGGER audit_change_order_changes
        AFTER INSERT OR UPDATE OR DELETE ON change_order
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # Subscription table - CRITICAL for revenue audit
    op.execute("""
        CREATE TRIGGER audit_subscription_changes
        AFTER INSERT OR UPDATE OR DELETE ON subscription
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # Product Plan table - CRITICAL for contract compliance
    op.execute("""
        CREATE TRIGGER audit_product_plan_changes
        AFTER INSERT OR UPDATE OR DELETE ON product_plan
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # ==========================================================================
    # HIGH PRIORITY - Master Data, Pricing, Configuration
    # ==========================================================================

    # Supplier table - HIGH for procurement audit
    op.execute("""
        CREATE TRIGGER audit_supplier_changes
        AFTER INSERT OR UPDATE OR DELETE ON supplier
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # Payment Method table - HIGH for PCI compliance
    op.execute("""
        CREATE TRIGGER audit_payment_method_changes
        AFTER INSERT OR UPDATE OR DELETE ON payment_method
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # App Service table - HIGH for debugging
    op.execute("""
        CREATE TRIGGER audit_app_service_changes
        AFTER INSERT OR UPDATE OR DELETE ON app_service
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # Tenant Markup Version - HIGH for pricing history
    op.execute("""
        CREATE TRIGGER audit_tenant_markup_version_changes
        AFTER INSERT OR UPDATE OR DELETE ON tenant_markup_version
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # Supplier Item Price - HIGH for supplier price history
    op.execute("""
        CREATE TRIGGER audit_supplier_item_price_changes
        AFTER INSERT OR UPDATE OR DELETE ON supplier_item_price
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # Tax Rate Version - HIGH for tax history
    op.execute("""
        CREATE TRIGGER audit_tax_rate_version_changes
        AFTER INSERT OR UPDATE OR DELETE ON tax_rate_version
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # Pricebook Item Version - HIGH for pricebook history
    op.execute("""
        CREATE TRIGGER audit_pricebook_item_version_changes
        AFTER INSERT OR UPDATE OR DELETE ON pricebook_item_version
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # Product Plan Version - HIGH for SaaS plan history
    op.execute("""
        CREATE TRIGGER audit_product_plan_version_changes
        AFTER INSERT OR UPDATE OR DELETE ON product_plan_version
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # Product Plan Feature Version - HIGH for feature history
    op.execute("""
        CREATE TRIGGER audit_product_plan_product_feature_version_changes
        AFTER INSERT OR UPDATE OR DELETE ON product_plan_product_feature_version
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # ==========================================================================
    # MEDIUM PRIORITY - Transactional/Operational Tables
    # ==========================================================================

    # Change Order Related
    op.execute("""
        CREATE TRIGGER audit_change_order_attachment_changes
        AFTER INSERT OR UPDATE OR DELETE ON change_order_attachment
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_change_order_line_changes
        AFTER INSERT OR UPDATE OR DELETE ON change_order_line
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_change_order_line_tax_component_changes
        AFTER INSERT OR UPDATE OR DELETE ON change_order_line_tax_component
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # Connector/Integration
    op.execute("""
        CREATE TRIGGER audit_connector_config_changes
        AFTER INSERT OR UPDATE OR DELETE ON connector_config
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_connector_run_log_changes
        AFTER INSERT OR UPDATE OR DELETE ON connector_run_log
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # Contact Related
    op.execute("""
        CREATE TRIGGER audit_contact_endpoint_changes
        AFTER INSERT OR UPDATE OR DELETE ON contact_endpoint
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_contact_notification_pref_changes
        AFTER INSERT OR UPDATE OR DELETE ON contact_notification_pref
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_contact_portal_invite_changes
        AFTER INSERT OR UPDATE OR DELETE ON contact_portal_invite
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # Conversation/Voice
    op.execute("""
        CREATE TRIGGER audit_conversation_message_changes
        AFTER INSERT OR UPDATE OR DELETE ON conversation_message
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_conversation_session_changes
        AFTER INSERT OR UPDATE OR DELETE ON conversation_session
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_voice_command_log_changes
        AFTER INSERT OR UPDATE OR DELETE ON voice_command_log
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # Entity Relationships
    op.execute("""
        CREATE TRIGGER audit_entity_address_changes
        AFTER INSERT OR UPDATE OR DELETE ON entity_address
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_entity_contact_changes
        AFTER INSERT OR UPDATE OR DELETE ON entity_contact
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # Idempotency
    op.execute("""
        CREATE TRIGGER audit_idempotency_key_changes
        AFTER INSERT OR UPDATE OR DELETE ON idempotency_key
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # Integration/QuickBooks
    op.execute("""
        CREATE TRIGGER audit_integration_credential_changes
        AFTER INSERT OR UPDATE OR DELETE ON integration_credential
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_integration_sync_conflict_changes
        AFTER INSERT OR UPDATE OR DELETE ON integration_sync_conflict
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_integration_sync_log_changes
        AFTER INSERT OR UPDATE OR DELETE ON integration_sync_log
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_integration_sync_mapping_changes
        AFTER INSERT OR UPDATE OR DELETE ON integration_sync_mapping
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # Invoice Related
    op.execute("""
        CREATE TRIGGER audit_invoice_line_changes
        AFTER INSERT OR UPDATE OR DELETE ON invoice_line
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_invoice_line_tax_component_changes
        AFTER INSERT OR UPDATE OR DELETE ON invoice_line_tax_component
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # Job Related
    op.execute("""
        CREATE TRIGGER audit_job_assignment_changes
        AFTER INSERT OR UPDATE OR DELETE ON job_assignment
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_job_attachment_changes
        AFTER INSERT OR UPDATE OR DELETE ON job_attachment
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_job_notes_changes
        AFTER INSERT OR UPDATE OR DELETE ON job_notes
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # Notification System
    op.execute("""
        CREATE TRIGGER audit_notification_delivery_attempt_changes
        AFTER INSERT OR UPDATE OR DELETE ON notification_delivery_attempt
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_notification_event_changes
        AFTER INSERT OR UPDATE OR DELETE ON notification_event
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_notification_outbox_changes
        AFTER INSERT OR UPDATE OR DELETE ON notification_outbox
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_notification_template_changes
        AFTER INSERT OR UPDATE OR DELETE ON notification_template
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # Password Policy
    op.execute("""
        CREATE TRIGGER audit_password_policy_changes
        AFTER INSERT OR UPDATE OR DELETE ON password_policy
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # Pricing Cache
    op.execute("""
        CREATE TRIGGER audit_pricing_cache_changes
        AFTER INSERT OR UPDATE OR DELETE ON pricing_cache
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # Payment Service Provider
    op.execute("""
        CREATE TRIGGER audit_psp_customer_changes
        AFTER INSERT OR UPDATE OR DELETE ON psp_customer
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_psp_transaction_log_changes
        AFTER INSERT OR UPDATE OR DELETE ON psp_transaction_log
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # Quote Related
    op.execute("""
        CREATE TRIGGER audit_quote_acceptance_changes
        AFTER INSERT OR UPDATE OR DELETE ON quote_acceptance
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_quote_line_changes
        AFTER INSERT OR UPDATE OR DELETE ON quote_line
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_quote_line_tax_component_changes
        AFTER INSERT OR UPDATE OR DELETE ON quote_line_tax_component
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_quote_message_changes
        AFTER INSERT OR UPDATE OR DELETE ON quote_message
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_quote_public_link_changes
        AFTER INSERT OR UPDATE OR DELETE ON quote_public_link
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_quote_public_link_contact_action_changes
        AFTER INSERT OR UPDATE OR DELETE ON quote_public_link_contact_action
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_quote_version_changes
        AFTER INSERT OR UPDATE OR DELETE ON quote_version
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # Subscription Related
    op.execute("""
        CREATE TRIGGER audit_subscription_usage_changes
        AFTER INSERT OR UPDATE OR DELETE ON subscription_usage
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # Tenant Related
    op.execute("""
        CREATE TRIGGER audit_tenant_domain_changes
        AFTER INSERT OR UPDATE OR DELETE ON tenant_domain
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_tenant_notification_default_changes
        AFTER INSERT OR UPDATE OR DELETE ON tenant_notification_default
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_tenant_product_feature_override_changes
        AFTER INSERT OR UPDATE OR DELETE ON tenant_product_feature_override
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_tenant_settings_changes
        AFTER INSERT OR UPDATE OR DELETE ON tenant_settings
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_tenant_user_changes
        AFTER INSERT OR UPDATE OR DELETE ON tenant_user
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_tenant_user_invite_changes
        AFTER INSERT OR UPDATE OR DELETE ON tenant_user_invite
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_tenant_user_notification_pref_changes
        AFTER INSERT OR UPDATE OR DELETE ON tenant_user_notification_pref
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_tenant_user_role_changes
        AFTER INSERT OR UPDATE OR DELETE ON tenant_user_role
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # User Related
    op.execute("""
        CREATE TRIGGER audit_user_endpoint_changes
        AFTER INSERT OR UPDATE OR DELETE ON user_endpoint
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_user_preference_changes
        AFTER INSERT OR UPDATE OR DELETE ON user_preference
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_user_sso_identity_changes
        AFTER INSERT OR UPDATE OR DELETE ON user_sso_identity
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # Webhook System
    op.execute("""
        CREATE TRIGGER audit_webhook_delivery_attempt_changes
        AFTER INSERT OR UPDATE OR DELETE ON webhook_delivery_attempt
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_webhook_endpoint_changes
        AFTER INSERT OR UPDATE OR DELETE ON webhook_endpoint
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_webhook_event_changes
        AFTER INSERT OR UPDATE OR DELETE ON webhook_event
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    # ==========================================================================
    # AUTH TABLES - Security-Critical
    # ==========================================================================

    op.execute("""
        CREATE TRIGGER audit_auth_api_token_changes
        AFTER INSERT OR UPDATE OR DELETE ON auth_api_token
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_auth_email_verification_changes
        AFTER INSERT OR UPDATE OR DELETE ON auth_email_verification
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_auth_jwk_changes
        AFTER INSERT OR UPDATE OR DELETE ON auth_jwk
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_auth_mfa_otp_changes
        AFTER INSERT OR UPDATE OR DELETE ON auth_mfa_otp
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_auth_password_history_changes
        AFTER INSERT OR UPDATE OR DELETE ON auth_password_history
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_auth_password_reset_changes
        AFTER INSERT OR UPDATE OR DELETE ON auth_password_reset
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_auth_refresh_token_changes
        AFTER INSERT OR UPDATE OR DELETE ON auth_refresh_token
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)

    op.execute("""
        CREATE TRIGGER audit_sso_provider_changes
        AFTER INSERT OR UPDATE OR DELETE ON sso_provider
        FOR EACH ROW EXECUTE FUNCTION audit.log_changes();
    """)


def downgrade() -> None:
    """
    Remove all audit triggers added in this migration.

    Note: Using IF EXISTS to safely handle downgrades even if triggers were
    manually removed or never created.
    """

    # CRITICAL PRIORITY
    op.execute('DROP TRIGGER IF EXISTS audit_user_changes ON "user";')
    op.execute("DROP TRIGGER IF EXISTS audit_tenant_changes ON tenant;")
    op.execute("DROP TRIGGER IF EXISTS audit_change_order_changes ON change_order;")
    op.execute("DROP TRIGGER IF EXISTS audit_subscription_changes ON subscription;")
    op.execute("DROP TRIGGER IF EXISTS audit_product_plan_changes ON product_plan;")

    # HIGH PRIORITY
    op.execute("DROP TRIGGER IF EXISTS audit_supplier_changes ON supplier;")
    op.execute("DROP TRIGGER IF EXISTS audit_payment_method_changes ON payment_method;")
    op.execute("DROP TRIGGER IF EXISTS audit_app_service_changes ON app_service;")
    op.execute(
        "DROP TRIGGER IF EXISTS audit_tenant_markup_version_changes ON tenant_markup_version;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_supplier_item_price_changes ON supplier_item_price;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_tax_rate_version_changes ON tax_rate_version;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_pricebook_item_version_changes ON pricebook_item_version;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_product_plan_version_changes ON product_plan_version;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_product_plan_product_feature_version_changes ON product_plan_product_feature_version;"
    )

    # MEDIUM PRIORITY - Change Order Related
    op.execute(
        "DROP TRIGGER IF EXISTS audit_change_order_attachment_changes ON change_order_attachment;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_change_order_line_changes ON change_order_line;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_change_order_line_tax_component_changes ON change_order_line_tax_component;"
    )

    # Connector/Integration
    op.execute(
        "DROP TRIGGER IF EXISTS audit_connector_config_changes ON connector_config;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_connector_run_log_changes ON connector_run_log;"
    )

    # Contact Related
    op.execute(
        "DROP TRIGGER IF EXISTS audit_contact_endpoint_changes ON contact_endpoint;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_contact_notification_pref_changes ON contact_notification_pref;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_contact_portal_invite_changes ON contact_portal_invite;"
    )

    # Conversation/Voice
    op.execute(
        "DROP TRIGGER IF EXISTS audit_conversation_message_changes ON conversation_message;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_conversation_session_changes ON conversation_session;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_voice_command_log_changes ON voice_command_log;"
    )

    # Entity Relationships
    op.execute("DROP TRIGGER IF EXISTS audit_entity_address_changes ON entity_address;")
    op.execute("DROP TRIGGER IF EXISTS audit_entity_contact_changes ON entity_contact;")

    # Idempotency
    op.execute(
        "DROP TRIGGER IF EXISTS audit_idempotency_key_changes ON idempotency_key;"
    )

    # Integration/QuickBooks
    op.execute(
        "DROP TRIGGER IF EXISTS audit_integration_credential_changes ON integration_credential;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_integration_sync_conflict_changes ON integration_sync_conflict;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_integration_sync_log_changes ON integration_sync_log;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_integration_sync_mapping_changes ON integration_sync_mapping;"
    )

    # Invoice Related
    op.execute("DROP TRIGGER IF EXISTS audit_invoice_line_changes ON invoice_line;")
    op.execute(
        "DROP TRIGGER IF EXISTS audit_invoice_line_tax_component_changes ON invoice_line_tax_component;"
    )

    # Job Related
    op.execute("DROP TRIGGER IF EXISTS audit_job_assignment_changes ON job_assignment;")
    op.execute("DROP TRIGGER IF EXISTS audit_job_attachment_changes ON job_attachment;")
    op.execute("DROP TRIGGER IF EXISTS audit_job_notes_changes ON job_notes;")

    # Notification System
    op.execute(
        "DROP TRIGGER IF EXISTS audit_notification_delivery_attempt_changes ON notification_delivery_attempt;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_notification_event_changes ON notification_event;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_notification_outbox_changes ON notification_outbox;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_notification_template_changes ON notification_template;"
    )

    # Password Policy
    op.execute(
        "DROP TRIGGER IF EXISTS audit_password_policy_changes ON password_policy;"
    )

    # Pricing Cache
    op.execute("DROP TRIGGER IF EXISTS audit_pricing_cache_changes ON pricing_cache;")

    # Payment Service Provider
    op.execute("DROP TRIGGER IF EXISTS audit_psp_customer_changes ON psp_customer;")
    op.execute(
        "DROP TRIGGER IF EXISTS audit_psp_transaction_log_changes ON psp_transaction_log;"
    )

    # Quote Related
    op.execute(
        "DROP TRIGGER IF EXISTS audit_quote_acceptance_changes ON quote_acceptance;"
    )
    op.execute("DROP TRIGGER IF EXISTS audit_quote_line_changes ON quote_line;")
    op.execute(
        "DROP TRIGGER IF EXISTS audit_quote_line_tax_component_changes ON quote_line_tax_component;"
    )
    op.execute("DROP TRIGGER IF EXISTS audit_quote_message_changes ON quote_message;")
    op.execute(
        "DROP TRIGGER IF EXISTS audit_quote_public_link_changes ON quote_public_link;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_quote_public_link_contact_action_changes ON quote_public_link_contact_action;"
    )
    op.execute("DROP TRIGGER IF EXISTS audit_quote_version_changes ON quote_version;")

    # Subscription Related
    op.execute(
        "DROP TRIGGER IF EXISTS audit_subscription_usage_changes ON subscription_usage;"
    )

    # Tenant Related
    op.execute("DROP TRIGGER IF EXISTS audit_tenant_domain_changes ON tenant_domain;")
    op.execute(
        "DROP TRIGGER IF EXISTS audit_tenant_notification_default_changes ON tenant_notification_default;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_tenant_product_feature_override_changes ON tenant_product_feature_override;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_tenant_settings_changes ON tenant_settings;"
    )
    op.execute("DROP TRIGGER IF EXISTS audit_tenant_user_changes ON tenant_user;")
    op.execute(
        "DROP TRIGGER IF EXISTS audit_tenant_user_invite_changes ON tenant_user_invite;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_tenant_user_notification_pref_changes ON tenant_user_notification_pref;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_tenant_user_role_changes ON tenant_user_role;"
    )

    # User Related
    op.execute("DROP TRIGGER IF EXISTS audit_user_endpoint_changes ON user_endpoint;")
    op.execute(
        "DROP TRIGGER IF EXISTS audit_user_preference_changes ON user_preference;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_user_sso_identity_changes ON user_sso_identity;"
    )

    # Webhook System
    op.execute(
        "DROP TRIGGER IF EXISTS audit_webhook_delivery_attempt_changes ON webhook_delivery_attempt;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_webhook_endpoint_changes ON webhook_endpoint;"
    )
    op.execute("DROP TRIGGER IF EXISTS audit_webhook_event_changes ON webhook_event;")

    # AUTH TABLES
    op.execute("DROP TRIGGER IF EXISTS audit_auth_api_token_changes ON auth_api_token;")
    op.execute(
        "DROP TRIGGER IF EXISTS audit_auth_email_verification_changes ON auth_email_verification;"
    )
    op.execute("DROP TRIGGER IF EXISTS audit_auth_jwk_changes ON auth_jwk;")
    op.execute("DROP TRIGGER IF EXISTS audit_auth_mfa_otp_changes ON auth_mfa_otp;")
    op.execute(
        "DROP TRIGGER IF EXISTS audit_auth_password_history_changes ON auth_password_history;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_auth_password_reset_changes ON auth_password_reset;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS audit_auth_refresh_token_changes ON auth_refresh_token;"
    )
    op.execute("DROP TRIGGER IF EXISTS audit_sso_provider_changes ON sso_provider;")
