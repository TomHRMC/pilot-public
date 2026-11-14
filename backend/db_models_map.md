# Pilot for Trades Database Models Map

**Source Directory:** `<repo>/backend/app`

> **Key**: Only **DB Tables** entries are queryable via `select()`. Never use `db.get()` or `select()` against Enum/Schema classes — they are not database tables.

### `models/ai.py`

**DB Tables** (SQLModel `table=True` — queryable via `select()`):
- `ConversationSession` → table: `conversation_session`
- `ConversationMessage` → table: `conversation_message`
- `VoiceFeedback` → table: `voice_feedback`
- `VoiceCommandLog` → table: `voice_command_log`
- `VoiceCommandEntityLink` → table: `voice_command_entity_link`

---
### `models/auth.py`

**DB Tables** (SQLModel `table=True` — queryable via `select()`):
- `TenantUserRole` → table: `tenant_user_role`
- `TenantUserStatus` → table: `tenant_user_status`
- `TenantUser` → table: `tenant_user`
- `TenantDomain` → table: `tenant_domain`
- `TenantUserInvite` → table: `tenant_user_invite`
- `ContactPortalInvite` → table: `contact_portal_invite`
- `AuthRefreshToken` → table: `auth_refresh_token`
- `AuthPasswordReset` → table: `auth_password_reset`
- `AuthEmailVerification` → table: `auth_email_verification`
- `AuthMfaOtp` → table: `auth_mfa_otp`
- `AuthPasswordHistory` → table: `auth_password_history`
- `AuthApiToken` → table: `auth_api_token`
- `SsoProvider` → table: `sso_provider`
- `UserSsoIdentity` → table: `user_sso_identity`
- `JwkStatus` → table: `jwk_status`
- `AuthJwk` → table: `auth_jwk`
- `PasswordPolicy` → table: `password_policy`

---
### `models/billing.py`

**DB Tables** (SQLModel `table=True` — queryable via `select()`):
- `Currency` → table: `currency`
- `InvoiceStatus` → table: `invoice_status`
- `PaymentStatus` → table: `payment_status`
- `PaymentType` → table: `payment_type`
- `Invoice` → table: `invoice`
- `InvoiceLine` → table: `invoice_line`
- `PaymentMethod` → table: `payment_method`
- `Payment` → table: `payment`
- `Subscription` → table: `subscription`
- `UsageLedger` → table: `usage_ledger`
- `ProductPlan` → table: `product_plan`
- `ProductFeature` → table: `product_feature`
- `SubscriptionStatus` → table: `subscription_status`
- `ProductPlanVersion` → table: `product_plan_version`
- `ProductPlanProductFeatureVersion` → table: `product_plan_product_feature_version`
- `TenantProductFeatureOverride` → table: `tenant_product_feature_override`
- `SubscriptionUsage` → table: `subscription_usage`
- `PspCustomer` → table: `psp_customer`
- `PspTransactionLog` → table: `psp_transaction_log`
- `InvoiceLineTaxComponent` → table: `invoice_line_tax_component`
- `InvoicePublicLink` → table: `invoice_public_link`
- `StripeWebhookEventProcessed` → table: `stripe_webhook_event_processed`
- `PaymentSchedule` → table: `payment_schedule`
- `PaymentScheduleLine` → table: `payment_schedule_line`
- `CarrierFeeSchedule` → table: `carrier_fee_schedule`
- `InvoiceSignoff` → table: `invoice_signoff`

---
### `models/catalog.py`

**DB Tables** (SQLModel `table=True` — queryable via `select()`):
- `SupplierLifecycleStatus` → table: `supplier_lifecycle_status`
- `Supplier` → table: `supplier`
- `SupplierItemCategory` → table: `supplier_item_category`
- `SupplierItemUom` → table: `supplier_item_uom`
- `SupplierItem` → table: `supplier_item`
- `SupplierItemPrice` → table: `supplier_item_price`
- `PricingCache` → table: `pricing_cache`
- `TenantMarkupVersion` → table: `tenant_markup_version`
- `TaxRateVersion` → table: `tax_rate_version`
- `LaborRateVersion` → table: `labor_rate_version`
- `DiscountVersion` → table: `discount_version`

---
### `models/communications.py`

**DB Tables** (SQLModel `table=True` — queryable via `select()`):
- `CommunicationTemplate` → table: `communication_template`
- `CustomerCommunication` → table: `customer_communication`
- `EmailTemplate` → table: `email_template`
- `CustomerCommTemplateType` → table: `customer_comm_template_type`
- `UserSmsConsentAudit` → table: `user_sms_consent_audit`

---
### `models/core.py`

**DB Tables** (SQLModel `table=True` — queryable via `select()`):
- `PlatformRole` → table: `platform_role`
- `User` → table: `user`
- `UserPreference` → table: `user_preference`
- `Tenant` → table: `tenant`
- `UserEndpoint` → table: `user_endpoint`
- `TenantEmailBranding` → table: `tenant_email_branding`
- `Tenant10DlcProfile` → table: `tenant_10dlc_profile`
- `EntityType` → table: `entity_type`

---
### `models/crm.py`

**DB Tables** (SQLModel `table=True` — queryable via `select()`):
- `CustomerLifecycleStatus` → table: `customer_lifecycle_status`
- `SiteLifecycleStatus` → table: `site_lifecycle_status`
- `AddressType` → table: `address_type`
- `ContactType` → table: `contact_type`
- `Customer` → table: `customer`
- `CustomerSmsConsentAudit` → table: `customer_sms_consent_audit`
- `Site` → table: `site`
- `Contact` → table: `contact`
- `Address` → table: `address`
- `EntityContact` → table: `entity_contact`
- `EntityAddress` → table: `entity_address`
- `ContactEndpoint` → table: `contact_endpoint`

**Enums / Schemas / Helpers** (NOT DB tables — do not use in `select()` queries):
- CustomerType

---
### `models/fulfillment.py`

**DB Tables** (SQLModel `table=True` — queryable via `select()`):
- `JobType` → table: `job_type`
- `JobStatus` → table: `job_status`
- `JobRecurrenceRule` → table: `job_recurrence_rule`
- `Job` → table: `job`
- `JobNotes` → table: `job_notes`
- `JobAttachment` → table: `job_attachment`
- `JobTimeEntry` → table: `job_time_entry`
- `JobExpenseCategory` → table: `job_expense_category`
- `JobExpense` → table: `job_expense`
- `LotoConfirmation` → table: `loto_confirmation`
- `NecCalculationLog` → table: `nec_calculation_log`

---
### `models/help.py`

**DB Tables** (SQLModel `table=True` — queryable via `select()`):
- `HelpArticle` → table: `help_article`
- `HelpArticleChunk` → table: `help_article_chunk`
- `HelpChatSession` → table: `help_chat_session`
- `HelpChatMessage` → table: `help_chat_message`
- `FeedbackSubmission` → table: `feedback_submission`
- `HelpTrainingCorpus` → table: `help_training_corpus`

---
### `models/legal_acceptance.py`

**DB Tables** (SQLModel `table=True` — queryable via `select()`):
- `TenantLegalAcceptance` → table: `tenant_legal_acceptance`

---
### `models/marketing.py`

**DB Tables** (SQLModel `table=True` — queryable via `select()`):
- `MarketingWaitlistSignup` → table: `marketing_waitlist_signup`
- `MarketingContactSubmission` → table: `marketing_contact_submission`
- `MarketingNewsletterSubscriber` → table: `marketing_newsletter_subscriber`
- `MarketingJobApplication` → table: `marketing_job_application`

---
### `models/mixins.py`

**Enums / Schemas / Helpers** (NOT DB tables — do not use in `select()` queries):
- StandardAuditMixin
- AppendOnlyMixin
- MachineLogMixin

---
### `models/mobile_push_permission.py`

**DB Tables** (SQLModel `table=True` — queryable via `select()`):
- `MobilePushPermissionState` → table: `mobile_push_permission_state`

---
### `models/onboarding.py`

**DB Tables** (SQLModel `table=True` — queryable via `select()`):
- `TenantOnboardingChecklist` → table: `tenant_onboarding_checklist`

---
### `models/platform_setting.py`

**DB Tables** (SQLModel `table=True` — queryable via `select()`):
- `PlatformSettingCatalog` → table: `platform_setting_catalog`
- `PlatformSetting` → table: `platform_setting`

---
### `models/quoting.py`

**DB Tables** (SQLModel `table=True` — queryable via `select()`):
- `QuoteStatus` → table: `quote_status`
- `QcoLineType` → table: `qco_line_type`
- `TaxabilityCode` → table: `taxability_code`
- `QuoteLinkStatus` → table: `quote_link_status`
- `PricebookItem` → table: `pricebook_item`
- `PricebookItemVersion` → table: `pricebook_item_version`
- `Quote` → table: `quote`
- `QuoteVersion` → table: `quote_version`
- `QuoteLine` → table: `quote_line`
- `QuotePublicLink` → table: `quote_public_link`
- `QuoteAcceptance` → table: `quote_acceptance`
- `ChangeOrder` → table: `change_order`
- `QuoteLineTaxComponent` → table: `quote_line_tax_component`
- `ChangeOrderLine` → table: `change_order_line`
- `ChangeOrderLineTaxComponent` → table: `change_order_line_tax_component`
- `ChangeOrderAttachment` → table: `change_order_attachment`
- `QuoteMessage` → table: `quote_message`
- `QplContactActionType` → table: `qpl_contact_action_type`
- `QuotePublicLinkContactAction` → table: `quote_public_link_contact_action`
- `QuoteTemplate` → table: `quote_template`
- `QuoteTemplateVersion` → table: `quote_template_version`
- `QuoteTemplateLine` → table: `quote_template_line`
- `QuotePendingEdit` → table: `quote_pending_edit`
- `QuoteApprovalComment` → table: `quote_approval_comment`
- `PublicLinkShortCode` → table: `public_link_short_code`

---
### `models/reports.py`

**DB Tables** (SQLModel `table=True` — queryable via `select()`):
- `UserDashboardWidget` → table: `user_dashboard_widget`

**Enums / Schemas / Helpers** (NOT DB tables — do not use in `select()` queries):
- WidgetType

---
### `models/scheduling.py`

**DB Tables** (SQLModel `table=True` — queryable via `select()`):
- `JobTechAssignment` → table: `job_tech_assignment`
- `TechAvailability` → table: `tech_availability`
- `TenantCalendarIntegration` → table: `tenant_calendar_integration`
- `CalendarSyncLog` → table: `calendar_sync_log`
- `CalendarSyncConflict` → table: `calendar_sync_conflict`

---
### `models/security.py`

**DB Tables** (SQLModel `table=True` — queryable via `select()`):
- `UserSessionHistory` → table: `user_session_history`
- `MfaGracePeriodTracking` → table: `mfa_grace_period_tracking`
- `UserMfaMethod` → table: `user_mfa_method`
- `UserMfaRecoveryCode` → table: `user_mfa_recovery_code`
- `UserSessionMetadata` → table: `user_session_metadata`
- `DataExportRequest` → table: `data_export_request`

---
### `models/settings.py`

**DB Tables** (SQLModel `table=True` — queryable via `select()`):
- `UserSettingOverride` → table: `user_setting_override`

---
### `models/signup.py`

**DB Tables** (SQLModel `table=True` — queryable via `select()`):
- `TenantSignup` → table: `tenant_signup`

---
### `models/sms.py`

**DB Tables** (SQLModel `table=True` — queryable via `select()`):
- `TenantPhoneNumber` → table: `tenant_phone_number`
- `CustomerCommunicationThread` → table: `customer_communication_thread`
- `CustomerCommunicationMessage` → table: `customer_communication_message`
- `CustomerCommunicationUnrouted` → table: `customer_communication_unrouted`
- `CustomerCommunicationMessageReadState` → table: `customer_communication_message_read_state`
- `SmsQuotaPeriod` → table: `sms_quota_period`
- `TenantMessagingRegistration` → table: `tenant_messaging_registration`

---
### `models/subscription.py`

**DB Tables** (SQLModel `table=True` — queryable via `select()`):
- `SubscriptionTier` → table: `subscription_tier`
- `TenantTierOverride` → table: `tenant_tier_override`
- `TenantSubscriptionUsage` → table: `tenant_subscription_usage`

---
### `models/sync.py`

**DB Tables** (SQLModel `table=True` — queryable via `select()`):
- `MobileSyncEvent` → table: `mobile_sync_event`
- `MobileDevicePushToken` → table: `mobile_device_push_token`
- `MobileSyncSession` → table: `mobile_sync_session`
- `MobilePushRateLimit` → table: `mobile_push_rate_limit`
- `MobileSyncEventAudit` → table: `mobile_sync_event_audit`

---
### `models/system.py`

**DB Tables** (SQLModel `table=True` — queryable via `select()`):
- `WebhookEndpoint` → table: `webhook_endpoint`
- `WebhookEvent` → table: `webhook_event`
- `NotificationCategory` → table: `notification_category`
- `NotificationCategorySubTrigger` → table: `notification_category_sub_trigger`
- `NotificationDefaultPolicy` → table: `notification_default_policy`
- `NotificationPreference` → table: `notification_preference`
- `InAppNotification` → table: `in_app_notification`
- `NotificationOutbox` → table: `notification_outbox`
- `NotificationDeliveryAttempt` → table: `notification_delivery_attempt`
- `IntegrationSyncLog` → table: `integration_sync_log`
- `ConnectorConfig` → table: `connector_config`
- `ConnectorRunLog` → table: `connector_run_log`
- `AuditEvent` → table: `event`
- `AppServiceCategory` → table: `app_service_category`
- `AppServiceProvider` → table: `app_service_provider`
- `AppService` → table: `app_service`
- `IntegrationCredential` → table: `integration_credential`
- `IntegrationSyncMapping` → table: `integration_sync_mapping`
- `IntegrationSyncConflict` → table: `integration_sync_conflict`
- `NotificationChannel` → table: `notification_channel`
- `NotificationType` → table: `notification_type`
- `NotificationTemplate` → table: `notification_template`
- `NotificationEvent` → table: `notification_event`
- `WebhookEventType` → table: `webhook_event_type`
- `WebhookDeliveryAttempt` → table: `webhook_delivery_attempt`
- `IdempotencyKey` → table: `idempotency_key`
- `SyncConflictClassificationMatrix` → table: `sync_conflict_classification_matrix`
- `MobileSyncOwnerEscalation` → table: `mobile_sync_owner_escalation`

---
### `models/tenant_site.py`

**DB Tables** (SQLModel `table=True` — queryable via `select()`):
- `TenantSite` → table: `tenant_site`

---
