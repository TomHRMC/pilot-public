# Missing CHECK Constraints - Phase 4.7 Task 6

## Summary
- **Total in JSON Schema**: 49 constraints
- **Currently in Database**: 16 constraints  
- **Missing**: 33 constraints

## Existing Constraints (Already in DB)
1. ✅ auth_mfa_otp_channel_chk
2. ✅ connector_run_log_status_chk (needs update - different values)
3. ✅ contact_portal_invite_email_chk
4. ✅ customer_email_format_chk
5. ✅ customer_type_chk
6. ✅ integration_credential_status_chk (wrong name: ck_integration_credential_status)
7. ✅ integration_sync_conflict_status_chk (wrong name in JSON: should be isc_status_chk)
8. ✅ notification_outbox_status_chk
9. ✅ tenant_user_invite_email_format_chk
10. ✅ user_email_format_chk
11. ✅ user_platform_mfa_required_chk
12. ✅ user_platform_role_chk
13. ✅ user_preferred_mfa_channel_chk
14. ✅ user_endpoint_email_format_chk
15. ✅ webhook_delivery_attempt_status_chk (needs update - different values)

## Missing Constraints by Model File

### backend/app/models/crm.py
1. **Address**
   - address_has_physical_or_gps_chk: `(line_1 IS NOT NULL AND city IS NOT NULL) OR (latitude IS NOT NULL AND longitude IS NOT NULL)`

2. **Contact**
   - contact_email_format_chk: `(email is null) OR (email ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$')`

3. **ContactEndpoint** 
   - contact_endpoint_email_format_chk: `(channel <> 'email') OR (value ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')`
   - contact_endpoint_channel_chk: `channel IN ('email', 'sms')`
   - contact_endpoint_verification_status_chk: `verification_status IN ('pending', 'verified', 'failed')`
   - contact_endpoint_consent_status_chk: `consent_status IN ('unknown', 'opted_in', 'opted_out')`

### backend/app/models/core.py
4. **UserEndpoint**
   - user_endpoint_channel_chk: `channel IN ('email', 'sms')`
   - user_endpoint_verification_status_chk: `verification_status IN ('pending', 'verified', 'failed')`
   - user_endpoint_consent_status_chk: `consent_status IN ('unknown', 'opted_in', 'opted_out')`

### backend/app/models/auth.py
5. **AuthJwk**
   - auth_jwk_alg_chk: `alg IN ('RS256', 'ES256', 'EdDSA')`

### backend/app/models/system.py
6. **ConnectorConfig**
   - connector_config_mode_chk: `mode IN ('api','scrape','manual')`

7. **IdempotencyKey**
   - idempotency_key_status_chk: `status IN ('in_progress','succeeded','failed')`

8. **NotificationOutbox**
   - notification_outbox_channel_chk: `channel IN ('email','sms','in_app')`
   - notification_outbox_recipient_presence_chk: `(recipient_contact_id IS NOT NULL OR recipient_user_id IS NOT NULL OR to_address IS NOT NULL)`
   - notification_outbox_recipient_exclusive_chk: `((recipient_contact_id IS NOT NULL)::int + (recipient_user_id IS NOT NULL)::int + (to_address IS NOT NULL)::int) = 1`
   - notification_outbox_inapp_requires_user_chk: `(channel <> 'in_app') OR (recipient_user_id IS NOT NULL)`

9. **NotificationDeliveryAttempt**
   - notification_delivery_attempt_status_chk: `status IN ('queued','delivered','bounced','rejected','throttled','error')`

10. **NotificationType**
    - notification_type_audience_chk: `audience IN ('tenant','customer')`

### backend/app/models/ai.py
11. **ConversationMessage**
    - conv_msg_role_chk: `role IN ('user', 'assistant', 'system')`

12. **ConversationSession**
    - conv_session_status_chk: `status IN ('active', 'ended', 'abandoned')`

### backend/app/models/quoting.py
13. **QuoteMessage**
    - quote_message_action_type_chk: `action_type IN ('contact', 'tenant_user', 'system')`

### backend/app/models/billing.py
14. **Subscription**
    - subscription_billing_interval_chk: `billing_interval IN ('monthly','annual')`

15. **IntegrationSyncLog**
    - isl_status_chk: `status IN ('success', 'failed', 'partial_success')`

16. **IntegrationSyncMapping**
    - sync_preference_chk: `sync_preference IN ('pilot_master', 'external_master', 'bi_directional')`

### backend/app/models/catalog.py
17. **PricebookItemVersion**
    - piv_valid_period_chk: `NOT isempty(valid_period)`

18. **SupplierItemPrice**
    - sip_valid_period_chk: `NOT isempty(valid_period)`

19. **TaxRateVersion**
    - tax_rate_version_valid_period_chk: `NOT isempty(valid_period)`

20. **TenantMarkupVersion**
    - tmv_valid_period_chk: `NOT isempty(valid_period)`
    - tmv_markup_presence_chk: `(markup_pct IS NOT NULL) OR (markup_amt_cents IS NOT NULL)`

21. **ProductPlanVersion**
    - product_plan_version_valid_period_chk: `NOT isempty(valid_period)`

22. **ProductPlanProductFeatureVersion**
    - pppfv_valid_period_chk: `NOT isempty(valid_period)`
    - pppfv_limit_enforcement_chk: `limit_enforcement IN ('block','allow_overage')`

### backend/app/models/fulfillment.py
23. **InvoiceLine**
    - invoice_line_source_type_chk: `source_type IN ('quote_line', 'change_order_line', 'ad_hoc')`

24. **JobExpense**
    - job_expense_markup_presence_chk: `(markup_pct IS NOT NULL) OR (markup_amt_cents IS NOT NULL)`

## Notes
- All `NOT isempty(valid_period)` constraints use PostgreSQL range type function
- Email format constraints use case-insensitive regex (`~*`)
- Some existing constraints have wrong names or values and may need updates
