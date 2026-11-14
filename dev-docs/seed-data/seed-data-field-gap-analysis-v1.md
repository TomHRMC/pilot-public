# Seed Data Field Gap Analysis — v1

**Date**: 2026-07-23  
**Author**: Pilot Architect (automated DB + script analysis)  
**Scope**: All 185 public tables; all 11 seed scripts (Groups A–D)  
**Status**: Gap analysis complete — scope decisions recorded 2026-07-23. Awaiting SD-7 batch.

---

## Purpose

Every field that CAN be populated in the Pilot database MUST have representative data in the seed scripts so that:

1. UI smoke tests exercise real field rendering (not blanks / null states)
2. API tests have diverse, realistic fixture data
3. Demo / sales scenarios are fully lifelike
4. Edge cases are explicitly represented (e.g., a customer with a `dba_name`, a job with GPS variance)

This document catalogs every gap between the live DB schema and the current seed scripts, plus the formal **hold decisions** recorded by Tom on 2026-07-23 that govern which items are deferred and why.

---

## Table of Contents

- [1. Scope Decisions & Holds (2026-07-23)](#1-scope-decisions--holds-2026-07-23)
- [2. Classification Key](#2-classification-key)
- [3. Completely Empty Tables — Status per Gap](#3-completely-empty-tables--status-per-gap)
  - [3A. Seed in SD-7 (approved)](#3a-seed-in-sd-7-approved)
  - [3B. On Hold — pending infrastructure/feature readiness](#3b-on-hold--pending-infrastructurefeature-readiness)
  - [3C. Justifiably Empty (documented §8 README)](#3c-justifiably-empty-documented-8-readme)
- [4. Populated Tables with Unpopulated Fields](#4-populated-tables-with-unpopulated-fields)
- [5. Architectural Decisions for SD-7](#5-architectural-decisions-for-sd-7)
- [6. SD-7 Implementation Scope](#6-sd-7-implementation-scope)

---

## 1. Scope Decisions & Holds (2026-07-23)

These decisions were made by Tom during the gap analysis review. They constrain SD-7 scope. Each hold includes the reason and the **trigger condition** that must be true before the item is un-held.

### 🔴 HOLD — SMS-related fields and tables

**Decision**: Do NOT seed any SMS-related fields or tables until SMS/Telnyx 10DLC is turned on and a campaign is approved.

**Affected items:**
- `customer.sms_opt_in_at`, `customer.sms_opt_in_source`, `customer.sms_consent_attested_by`, `customer.sms_consent_ip_address`, `customer.sms_opted_out`, `customer.sms_opt_out_at`, `customer.sms_opt_in_consent`
- `customer_sms_consent_audit` (entire table)
- `customer_communication_message.carrier_message_id`, `.voice_audio_id`
- `tenant_phone_number` (already seeded as `status=provisioning_failed` — intentional; do NOT change to `active`)
- `sms_quota_period` (entire table — depends on active Telnyx number)
- `notification_outbox` rows with `channel = 'sms'`
- Any `contact_endpoint` rows with `channel = 'sms'`

**Trigger to un-hold**: Telnyx 10DLC campaign approved + `tenant_phone_number.status = 'active'`

---

### 🔴 HOLD — Quote/Invoice Public Links and Contact Actions

**Decision**: Do NOT seed `quote_public_link`, `invoice_public_link`, `public_link_short_code`, or `quote_public_link_contact_action` until the full quote/invoice issuance pipeline (PDF generation → S3 upload → link creation) is operational.

**Affected items:**
- `quote_public_link` (entire table)
- `invoice_public_link` (entire table)
- `public_link_short_code` (entire table — also requires short-link domain registration; see §5)
- `quote_public_link_contact_action` (entire table)

**Note on `quote_acceptance`**: Can be seeded **without** a `quote_public_link_id` (the FK is nullable). We represent it as an *internal* owner-recorded acceptance (customer called verbally, owner recorded it in the system). `accepted_by_user_id = owner_user_id`, `quote_public_link_id = NULL`. This is a real valid workflow.

**Trigger to un-hold**: PDF generation operational + S3 upload path confirmed + short-link domain registered (see §5 for short-link domain recommendation)

---

### 🔴 HOLD — Photo Attachments (`job_attachment`)

**Decision**: Seed photo attachments using **real S3 object keys** only — do not insert fake keys as they break signed URL generation. Tom to upload 2–3 test photos to the dev S3 bucket under `job-attachments/test/` and provide the keys.

**Affected items:**
- `job_attachment` (on hold until real S3 keys provided)

**Trigger to un-hold**: Tom uploads test photos and provides S3 keys. Photos go in `job-attachments/test/photo_001.jpg` etc. Seed script will receive them as constants.

---

### ✅ PROCEED — Notifications (email + in-app only, not SMS)

**Decision**: Seed `notification_event`, `notification_outbox`, and `notification_delivery_attempt` for `channel IN ('email', 'in_app', 'push')` only. Exclude all SMS notification rows.

**Key constraint**: `notification_preference` rows for owner user should be seeded — but only for email/in_app/push channels.

---

### ✅ PROCEED — `contact_endpoint` (phone channel, no SMS sending)

**Decision**: Seed `contact_endpoint` rows for contacts. Phone-channel entries get `consent_status = 'unknown'` and `verification_status = 'pending'`. No SMS carrier interaction is triggered by inserting a row.

---

### ✅ PROCEED — `quote_acceptance` without a public link

**Decision**: Seed `quote_acceptance` for `QUO-900005` (status=`accepted`). Use `accepted_by_user_id = owner_user_id` and `quote_public_link_id = NULL`. Represents a verbal customer acceptance recorded by the owner.

---

### ✅ PROCEED — Subscription/plan usage data (current period only, no history)

**Decision**: Seed current-period usage data only. Do NOT seed historical renewal cycles or past billing periods. Specifically:
- `subscription_usage` — 1 row per `product_feature` for the current billing period
- `sms_quota_period` — **on hold** (SMS not enabled)
- `usage_ledger` — seed current-period entries only
- `tenant_subscription_usage` — seed current-period summary row only

---

### ✅ PROCEED — `customer.dba_name` (company type only)

**Decision**: `dba_name` is only semantically valid for `type = 'company'` customers. Only set it on `Apex Commercial LLC` and `Metro Properties LLC`.

---

### ✅ PROCEED — Tax data (use existing jurisdictions; add test-specific data)

**Decision**: For testing tax calculations, use the existing `tax_rate_version` rows (`US-DEFAULT 6%`, `US-TX-HARRIS 8.25%`, `US-CA-LA 9.5%`). Do NOT create test-only fake jurisdictions — use real ones that match the seeded site addresses (TX site → `US-TX-HARRIS`, NY site → `US-DEFAULT`, CA not yet used). Populate the full tax chain: `quote_line.taxability_code` → `quote_line.tax_rate_pct` → `quote_line.tax_amount_cents` → `quote_line_tax_component` rows.

---

### ✅ PROCEED — Rolling dates (anchor to `NOW()`, not fixed dates)

**Decision**: For job `scheduled_start_at`/`scheduled_end_at`, time entries, and other date-sensitive fields, use **rolling offsets from `NOW()`** (e.g., `NOW() - INTERVAL '30 days'`, `NOW() + INTERVAL '3 days'`) instead of fixed anchored dates like `datetime(2026, 7, 1)`. This ensures the dispatch board and reporting views always show "recent" data regardless of when the seed is run.

**Exception**: The Q-CONV-001 chain (`QUO-900006 → JOB-900001 → INV-900001`) retains fixed dates because its amounts/math are pre-calculated and must be stable.

---

### 🔵 DEFERRED — Supplier catalog expansion (SD-8)

**Decision**: Seed a significantly larger supplier catalog using JSON data files — same pattern as `data/email_templates/`. Create `data/supplier_catalog/wesco.json`, `data/supplier_catalog/graybar.json`, `data/supplier_catalog/platt.json` with 20–30 items each. This is SD-8 scope (separate from SD-7) because it also needs to drive `pricebook_item` seeding. The JSON schema is defined in §5 below.

---

### 🔵 DEFERRED — Template test-fire script (SD-8)

**Decision**: Create a standalone `test_fire_templates.py` script in `migrations/scripts/` for manually firing notification/communication/email templates against real delivery channels. This is a QA tool, NOT part of the seed system. Scope deferred to SD-8. See §5 for the design.

---

### 🔵 DEFERRED — Short-link domain + redirect infrastructure

**Decision**: Register a short-link domain (e.g., `p4t-link.com`) for use in quote/invoice SMS/email links. Infrastructure: Route 53 → CloudFront → Lambda@Edge redirect, mapping `p4t-link.com/{short_code}` → app quote/invoice page. This is cheap (~$12/yr domain, ~$0 Lambda usage). Deferred to the same sprint as public link seeding. Record short codes in `public_link_short_code` table.

---

## 2. Classification Key

| Code | Meaning |
|:---|:---|
| 🔴 P0 | Blocks core product demo — must seed before any customer-facing test |
| 🟠 P1 | Required for realistic field coverage — seed in SD-7 |
| 🟡 P2 | Good-to-have for completeness — seed in SD-7 or SD-8 |
| ⚪ P3 | Justifiably empty (external API dep, or intentionally ephemeral) — no action |
| 🔒 HOLD | Held by formal decision above — do not seed until trigger condition met |

---

## 3. Completely Empty Tables — Status per Gap

### 3A. Seed in SD-7 (approved)

| Table | Priority | Rows | Why needed | Suggested script |
|:---|:---:|:---:|:---|:---|
| `notification_event` | 🔴 P0 | 0 | Upstream trigger for every notification delivery pipeline row | `seed_scenario_notifications.py` |
| `notification_outbox` | 🔴 P0 | 0 | Delivery queue — email + in_app + push channels only (not SMS) | `seed_scenario_notifications.py` |
| `notification_delivery_attempt` | 🔴 P0 | 0 | Delivery attempt log; essential for monitoring UI | `seed_scenario_notifications.py` |
| `notification_preference` | 🟠 P1 | 0 | Per-user channel preference overrides; needed for Preferences settings page | `seed_test_tenant.py` |
| `quote_acceptance` | 🔴 P0 | 0 | `QUO-900005` accepted quote has no acceptance record; seed as internal owner-recorded acceptance (`quote_public_link_id = NULL`) | `seed_scenario_quote_to_cash.py` |
| `quote_line_tax_component` | 🟠 P1 | 0 | 28 quote lines have zero tax components; `invoice_line_tax_component` has 18 — quotes must match | `seed_scenario_quote_to_cash.py` |
| `change_order_line_tax_component` | 🟠 P1 | 0 | 5 CO lines need tax component breakdowns | `seed_scenario_quote_to_cash.py` |
| `quote_approval_comment` | 🟡 P2 | 0 | `QUO-900001` (pending_approval) should have a reviewer comment | `seed_scenario_quote_to_cash.py` |
| `quote_message` | 🟡 P2 | 0 | Customer question on a sent quote — tests the quote thread UI | `seed_scenario_quote_to_cash.py` |
| `quote_pending_edit` | 🟡 P2 | 0 | Tests the track-changes diff UI pattern | `seed_scenario_quote_to_cash.py` |
| `contact_endpoint` | 🟠 P1 | 0 | 3 contacts exist with no channel endpoints; seed phone channel with `consent_status='unknown'` | `seed_scenario_customer_comms.py` |
| `customer_communication` | 🟠 P1 | 0 | The structured comm record (separate from threads); seed 1 on-my-way message for dispatch scenario | `seed_scenario_dispatch.py` |
| `customer_communication_message_read_state` | 🟡 P2 | 0 | 7 already-read messages have no read_state records — needed for "mark as read" regression tests | `seed_scenario_customer_comms.py` |
| `customer_communication_unrouted` | 🟡 P2 | 0 | Tests the unrouted SMS parking lot UI — 1 row with `status=parked` (no SMS sending needed for DB row) | `seed_scenario_customer_comms.py` |
| `job_recurrence_rule` | 🟡 P2 | 0 | Recurring jobs are a product feature; seed 1 active weekly rule | `seed_scenario_dispatch.py` |
| `mobile_device_push_token` | 🟠 P1 | 0 | 4 users have push `user_endpoint` rows but no device token registrations | `seed_test_tenant.py` |
| `mobile_sync_event_audit` | 🟠 P1 | 0 | 2 resolved escalations have no audit trail records | `seed_scenario_mobile_sync.py` |
| `mobile_push_permission_state` | 🟡 P2 | 0 | Push permission state per device; tech user should have `permission_state='granted'` | `seed_scenario_mobile_sync.py` |
| `subscription_usage` | 🟠 P1 | 0 | Per-feature usage meter; seed current-period rows for all 3 `product_feature` codes | `seed_test_tenant.py` |
| `tenant_subscription_usage` | 🟠 P1 | 0 | Monthly usage summary; seed 1 current-period row | `seed_test_tenant.py` |
| `usage_ledger` | 🟠 P1 | 0 | Immutable usage log; seed current-period voice AI + SMS entries | `seed_scenario_reporting.py` |
| `user_dashboard_widget` | 🟠 P1 | 0 | Owner user should have 3 dashboard widget layout rows | `seed_test_tenant.py` |
| `tenant_10dlc_profile` | 🟠 P1 | 0 | `tenant_phone_number` exists but has no 10DLC profile | `seed_test_tenant.py` |
| `tenant_signup` | 🟡 P2 | 0 | Completed signup wizard state record | `seed_test_tenant.py` |
| `tenant_legal_acceptance` | 🟡 P2 | 0 | Terms of service acceptance log for owner user | `seed_test_tenant.py` |
| `tenant_tier_override` | 🟡 P2 | 0 | Tests per-tenant tier override admin flow | `seed_test_tenant.py` |
| `tenant_domain` | 🟡 P2 | 0 | SSO domain verification — seed `pilot.local` domain for test tenant | `seed_test_tenant.py` |
| `tenant_product_feature_override` | 🟡 P2 | 0 | Tests per-tenant feature limit override path | `seed_test_tenant.py` |
| `tenant_user_invite` | 🟡 P2 | 0 | Seed 1 expired invite for a pending-invite UX test | `seed_test_tenant.py` |
| `mfa_grace_period_tracking` | 🟡 P2 | 0 | Tests the MFA grace period enforcement UX | `seed_test_tenant.py` |
| `user_mfa_method` | 🟡 P2 | 0 | Owner user should have an enrolled MFA method (TOTP) | `seed_test_tenant.py` |
| `user_session_history` | 🟡 P2 | 0 | Session analytics; owner user should have at least 1 session summary | `seed_test_tenant.py` |
| `auth_jwk` | 🟠 P1 | 0 | Auth system requires at least 1 active JWK to sign tokens; E2E tests require it | `seed_test_tenant.py` or `seed_core.py` |
| `auth_api_token` | 🟡 P2 | 0 | API token auth flow — seed 1 test token for owner user | `seed_test_tenant.py` |
| `quote_template_line` | 🔴 P0 | 0 | 3 `quote_template` rows exist but ALL are empty shells — a template with zero lines cannot be applied | `seed_core.py` |
| `pricing_cache` | 🟡 P2 | 0 | Supplier price cache entries for seeded Wesco items | `seed_scenario_supplier_catalog.py` |

### 3B. On Hold — pending infrastructure/feature readiness

| Table | Hold reason | Trigger to re-enable |
|:---|:---|:---|
| `quote_public_link` | Public link pipeline (PDF → S3 → link) not operational | PDF gen + S3 upload operational |
| `invoice_public_link` | Same as above | Same |
| `quote_public_link_contact_action` | Depends on `quote_public_link` | After `quote_public_link` is seeded |
| `public_link_short_code` | Requires short-link domain registration | Domain registered; `p4t-link.com` recommended |
| `customer_sms_consent_audit` | SMS not enabled; populating before Telnyx is live creates false compliance data | Telnyx 10DLC campaign approved |
| `sms_quota_period` | Depends on active Telnyx phone number | Same |
| `psp_customer` | Requires real Stripe `psp_customer_id` (documented README §8) | Stripe payment intent flow operational |
| `psp_transaction_log` | Same | Same |
| `job_attachment` | Requires real S3 keys; fake keys break signed URL generation | Tom uploads test photos; provides S3 keys |
| `tenant_calendar_integration` | Requires live OAuth token | Google/Outlook OAuth configured |
| `stripe_webhook_event_processed` | Requires real Stripe webhook events | Stripe webhook flow operational |
| `connector_config` | Requires external API setup | Supplier API credentials obtained |
| `connector_run_log` | Depends on `connector_config` | Same |

### 3C. Justifiably Empty (documented §8 README)

No action needed. These remain correctly excluded per `backend/README-seed-data.md §8`.

| Table | Reason |
|:---|:---|
| `voice_command_log`, `voice_command_entity_link`, `voice_feedback`, `conversation_session`, `conversation_message` | Requires live GPU/Whisper/Ollama session |
| `integration_credential`, `integration_sync_log`, `integration_sync_conflict` | Requires QuickBooks OAuth |
| `help_article`, `help_article_chunk`, `help_training_corpus` | Requires embedding pipeline |
| `auth_email_verification`, `auth_mfa_otp`, `auth_password_reset`, `auth_refresh_token`, `auth_password_history` | Runtime auth flow — ephemeral, no stable seed values |
| `calendar_sync_conflict`, `calendar_sync_log` | Requires live calendar integration |
| `idempotency_key` | Runtime dedup table — ephemeral |
| `user_sso_identity` | Requires real OAuth provider login |

---

## 4. Populated Tables with Unpopulated Fields

### 4A. `customer` (11 rows)

| Field | SD-7 Status | Notes |
|:---|:---|:---|
| `dba_name` | ✅ Seed | **Company-type customers only**: set on `Apex Commercial LLC` → `"Apex Electric Services"` and `Metro Properties LLC` → `"Metro Commercial Properties"` |
| `notes` | ✅ Seed | Add to 2–3 customers: `"Prefers morning appointments"`, `"Has a dog — call ahead"` |
| `taxability_code` | ✅ Seed | Set `"exempt"` on Apex Commercial LLC (commercial tax-exempt); all others leave NULL |
| `last_assigned_tech_id` | ✅ Seed | Set to tech user UUID on customers with completed reporting-scenario jobs |
| `locale` | ✅ Seed | `"en-US"` on 2 customers |
| `timezone` | ✅ Seed | `"America/New_York"` on NY customers, `"America/Chicago"` on TX customers |
| `sms_opt_in_at` | 🔒 HOLD | SMS not enabled — part of consent audit hold |
| `sms_opt_in_source` | 🔒 HOLD | Same |
| `sms_consent_attested_by` | 🔒 HOLD | Same |
| `sms_consent_ip_address` | 🔒 HOLD | Same |
| `sms_opted_out`, `sms_opt_out_at` | 🔒 HOLD | Same |

### 4B. `site` (7 rows)

| Field | SD-7 Status | Notes |
|:---|:---|:---|
| `notes` | ✅ Seed | 2 sites: `"Panel is in the basement. Bring 200A fuses."`, `"Ring doorbell on arrival."` |
| `hazard_notes` | ✅ Seed | Apex HQ: `"Asbestos confirmed in east wall — PPE required before panel work"` |
| `jurisdiction_code` | ✅ Seed | Austin TX site → `"US-TX-HARRIS"` (matches `tax_rate_version`); NY site → `"US-DEFAULT"` |
| `gate_code` | ✅ Seed | 1 site (gated community): `"#5588"` |
| `access_instructions` | ✅ Seed | 1 site: `"Park on the east side. Unit B is second door from the stairwell."` |

### 4C. `job` (14 rows)

| Field | SD-7 Status | Notes |
|:---|:---|:---|
| `quote_version_id` | ✅ Seed | `JOB-900001` (converted from `QUO-900006`) — set to the `quote_version.id` snapshot for that quote |
| `estimated_duration_minutes` | ✅ Seed | All scheduled/in_progress jobs: `240` (4 hrs). All reporting-scenario completed jobs: `180`–`480` depending on job type |
| `scheduled_start_at` / `scheduled_end_at` | ✅ Use rolling dates | Switch from fixed anchor to `NOW() ± INTERVAL` for dispatch scenario jobs (see §1 decision) |
| `external_calendar_event_id` | 🟡 Seed | 1 job: `"gcal_test_evt_pilot_001"` for calendar sync scenario |
| `variance_owner_notified_at` | 🟡 Seed | 1 reporting-scenario job where actual cost exceeded quote |
| `recurrence_rule_id` | 🟡 After `job_recurrence_rule` seeded | Link the recurring dispatch job to its rule |

### 4D. `job_time_entry` (15 rows)

| Field | SD-7 Status | Notes |
|:---|:---|:---|
| `check_in_lat` / `check_in_lng` | ✅ Seed | Set coordinates on 2 reporting entries matching their site addresses (NY: `40.6892, -74.0445`; TX: `30.2672, -97.7431`) |
| `gps_variance_meters` | ✅ Seed | Set `450` on 1 entry (just below 500m alert threshold) — tests variance alert logic |
| `hours_remaining_estimate` | ✅ Seed | All 15 entries should have an ETC at check-in (currently only 4 do) |
| `client_capture_at` | ✅ Seed | All entries should have `client_capture_at = started_at - INTERVAL '2 seconds'` (mobile capture before sync) |
| `server_received_at` | ✅ Seed | Set to `started_at + INTERVAL '3 seconds'` (server received slightly after) |
| `quote_line_id` | 🟡 Seed | Link 2 time entries to their corresponding quote labor lines |

### 4E. `job_expense` (13 rows)

| Field | SD-7 Status | Notes |
|:---|:---|:---|
| `vendor_name` | ✅ Seed | Set `"Home Depot"` on 4 materials expenses, `"Austin Permit Office"` on permit expenses |
| `client_capture_at` | ✅ Seed | All entries: `incurred_at - INTERVAL '1 second'` |
| `server_received_at` | ✅ Seed | All entries: `incurred_at + INTERVAL '5 seconds'` |
| `receipt_object_key` | 🔒 On hold | Wait for Tom to upload test receipt photos to S3 (same hold as `job_attachment`) |
| `ocr_processed_at` | 🔒 On hold | Depends on `receipt_object_key` |
| `ocr_source` | 🔒 On hold | Same |

### 4F. `quote_line` (28 rows)

All tax fields are currently NULL across all 28 rows.

| Field | SD-7 Status | Notes |
|:---|:---|:---|
| `taxability_code` | 🔴 Seed | Labor/material/misc lines → `"taxable"`; Permit Fee lines → `"exempt"` |
| `tax_rate_pct` | 🔴 Seed | `6.00` for NY/default site lines, `8.25` for TX site lines |
| `tax_basis_cents` | 🔴 Seed | `quantity × unit_price_cents` (pre-calculated per line) |
| `tax_amount_cents` | 🔴 Seed | `ROUND(tax_basis_cents × (tax_rate_pct / 100))` |
| `tax_jurisdiction_code` | 🟠 Seed | `"US-DEFAULT"` or `"US-TX-HARRIS"` matching the site |
| `unit_cost_cents` | 🟠 Seed | Internal cost on material lines (e.g., breaker costs $8, sells for $18) — drives margin reporting |
| `cost_source` | 🟠 Seed | `"pricebook"` on catalog-linked lines, `"manual"` on ad-hoc lines |
| `supplier_id` | 🟡 Seed | Link Wesco circuit breaker line to Wesco supplier |
| `supplier_item_id` | 🟡 Seed | Link to specific Wesco breaker item |

### 4G. `invoice` (14 rows)

| Field | SD-7 Status | Notes |
|:---|:---|:---|
| `issued_at` | 🟠 Seed | All `issued`, `paid`, `partial` invoices must have `issued_at` — currently all NULL |
| `payment_terms` | 🟠 Seed | `"net_30"` on issued invoices; `"due_on_receipt"` on completed jobs |
| `customer_notes` | 🟠 Seed | 2 invoices: `"Thank you for your business! Payment due within 30 days."` |
| `terms_and_conditions` | 🟡 Seed | 1 invoice: `"Net 30 days. Late fees apply after due date."` |
| `internal_memo` | 🟡 Seed | 1 invoice: `"Check #4421 received 2026-07-10. Filed."` |
| `pdf_object_key` | 🔒 On hold | Requires PDF generation pipeline (same hold as invoice public link) |

### 4H. `change_order` (2 rows) / `change_order_line` (5 rows)

| Table | Field | SD-7 Status | Notes |
|:---|:---|:---|:---|
| `change_order` | `client_capture_at` | ✅ Seed | `created_at - INTERVAL '2 seconds'` |
| `change_order` | `server_received_at` | ✅ Seed | `created_at + INTERVAL '5 seconds'` |
| `change_order_line` | `taxability_code` | ✅ Seed | Same pattern as `quote_line` |
| `change_order_line` | `tax_rate_pct` | ✅ Seed | Same |
| `change_order_line` | `tax_basis_cents` | ✅ Seed | Same |
| `change_order_line` | `tax_amount_cents` | ✅ Seed | Same |
| `change_order_line` | `supplier_id` | 🟡 Seed | Wesco on material CO lines |

### 4I. `supplier` (3 rows)

| Field | SD-7 Status | Notes |
|:---|:---|:---|
| `website` | ✅ Seed | `"https://wesco.com"`, `"https://graybar.com"`, `"https://platt.com"` |
| `api_auth_type` | 🟡 Seed | `"api_key"` on Wesco |
| `api_base_url` | 🟡 Seed | `"https://api.wesco.com/v1"` on Wesco |

### 4J. `user` (5 rows — 4 test users + system sentinel)

| Field | SD-7 Status | Notes |
|:---|:---|:---|
| `phone_number` | 🔒 HOLD | SMS not enabled — phone numbers used for MFA SMS which is also on hold |
| `email_verified_at` | ✅ Seed | Set to `created_at` on all 4 test users (pre-verified) |
| `last_login_at` | ✅ Seed | Realistic past timestamps per user (owner: `NOW() - INTERVAL '2 hours'`, tech: `NOW() - INTERVAL '1 day'`) |
| `password_updated_at` | 🟡 Seed | Set to `created_at` on all users |

### 4K. `contact` (3 rows — comms scenario)

| Field | SD-7 Status | Notes |
|:---|:---|:---|
| `locale` | 🟡 Seed | `"en-US"` on 2 contacts |
| `timezone` | 🟡 Seed | `"America/Chicago"` on Linda Park |
| `notes` | 🟡 Seed | `"Prefers text over phone calls"` on Linda Park |

### 4L. `nec_calculation_log` (3 rows)

| Field | SD-7 Status | Notes |
|:---|:---|:---|
| `job_id` | ✅ Seed | Link 1 NEC calc to the Panel Upgrade job from reporting scenario |
| `client_capture_at` | ✅ Seed | Offline calc row: `created_at - INTERVAL '3 days'` (captured offline 3 days before sync) |
| `idempotency_key` | 🟡 Seed | All offline calc rows should have an idempotency key |

### 4M. `tenant` (1 row)

| Field | SD-7 Status | Notes |
|:---|:---|:---|
| `trial_started_at` | 🟡 Seed | `'2026-06-01'` (founders cohort start date) |
| `stripe_connect_account_id` | 🟡 Seed | `"acct_test_pilot_dev_001"` — test Stripe Connect account ID |

### 4N. `mobile_sync_owner_escalation` (2 rows)

| Field | SD-7 Status | Notes |
|:---|:---|:---|
| `resolution_payload` | ✅ Seed | Resolved row (status=`resolved`) should have: `{"server_value": {"status": "completed"}, "device_value": {"status": "in_progress"}, "resolution": "use_tech"}` |

### 4O. `quote_template` (3 rows) — `quote_template_line` has 0 rows

| Gap | Priority | SD-7 Status |
|:---|:---:|:---|
| All 3 templates have zero `quote_template_line` rows | 🔴 P0 | Seed in `seed_core.py` — add 2–4 lines per template covering labor + material + misc types |
| `quote_template_version.content_json` is minimal | 🟠 P1 | Each version snapshot should include the seeded template lines as serialized JSON |

### 4P. `tenant_user` (4 rows)

| Field | SD-7 Status | Notes |
|:---|:---|:---|
| `skill_level_code` | ✅ Seed | `"master"` on owner, `"journeyman"` on tech, `"apprentice"` on office staff; accountant → NULL (not field-based) |
| `employee_number` | 🟡 Seed | `"EMP-001"` through `"EMP-003"` on field users |

### 4Q. `payment` (6 rows)

| Field | SD-7 Status | Notes |
|:---|:---|:---|
| `customer_payment_comment` | 🟡 Seed | `"Check #4421 received 2026-07-10"` on the manual check payment |
| `amount_variance_cents` | 🟡 Seed | `-50` on the partial payment (INV-SEED-E) — tests underpayment edge case |
| `stripe_payment_intent_id` | 🟡 Seed | `"pi_test_seed_pilot_001"` on succeeded card payment |

---

## 5. Architectural Decisions for SD-7

### 5.1 Supplier Catalog JSON Data File Pattern

Use the same pattern as `data/email_templates/` — create per-supplier JSON files in `data/supplier_catalog/`:

```
migrations/scripts/data/supplier_catalog/
├── wesco.json
├── graybar.json
└── platt.json
```

**Standard JSON schema per file**:

```json
{
  "supplier": {
    "name": "Wesco Distribution",
    "website": "https://wesco.com",
    "api_auth_type": "api_key",
    "api_base_url": "https://api.wesco.com/v1",
    "lifecycle_status_code": "active"
  },
  "items": [
    {
      "sku": "WES-14-2NM-250",
      "name": "14/2 NM-B Wire 250ft Coil",
      "description": "Southwire 14/2 NM-B with ground, 250ft coil",
      "uom_code": "roll",
      "category_code": "wire_cable",
      "taxability_code": "taxable",
      "is_active": true,
      "current_price": 89.99,
      "currency": "USD"
    }
  ]
}
```

This same schema drives `pricebook_item` seeding — the seed script loads from these JSON files and upserts both `supplier_item` + `supplier_item_price` rows. SD-8 will expand to 20–30 items per supplier.

### 5.2 Template Test-Fire Script (SD-8 scope)

A standalone QA tool `migrations/scripts/test_fire_templates.py`:

```bash
# Fire a quote_accepted notification email to Tom's address
python migrations/scripts/test_fire_templates.py \
  --channel email \
  --template quote_accepted \
  --recipient tom@pilotfortrades.com \
  --tenant-id 00000000-0000-0000-0000-000000000001

# When SMS enabled: fire same template to cell
python migrations/scripts/test_fire_templates.py \
  --channel sms \
  --template invoice_sent \
  --recipient +14105550123 \
  --tenant-id 00000000-0000-0000-0000-000000000001
```

The script resolves the template from `notification_template` or `email_template`, renders variables using test tenant data, and fires via the live delivery service (not queued through Celery — direct sync call). **Not part of the seed system** — manual QA tool only.

### 5.3 Short-Link Domain (p4t-link.com)

Register `p4t-link.com` (or similar). Architecture:

```
Route 53 (p4t-link.com) → CloudFront → Lambda@Edge
Lambda: lookup short_code in public_link_short_code → 302 redirect to app URL
```

Cost: ~$12/yr domain + effectively $0 Lambda (< 1M requests/mo). Short codes stored in `public_link_short_code` table. This is required before `quote_public_link` and `invoice_public_link` seeding can proceed.

### 5.4 Rolling Date Pattern for Dispatch Scenario

Use `NOW()` offsets everywhere the dispatch board, schedule view, or availability calendar needs "current" data:

```python
# In seed scripts — always relative to NOW()
now = datetime.now(UTC)
LAST_MONTH_15 = now.replace(day=15) - timedelta(days=now.day + 15)
YESTERDAY = (now - timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
TODAY_2PM = now.replace(hour=14, minute=0, second=0, microsecond=0)
TOMORROW_9AM = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
NEXT_FRIDAY = ...  # compute actual next Friday
```

**Exception**: Q-CONV-001 chain retains fixed dates (payment math is pre-calculated and must be stable across reseeds).

---

## 6. SD-7 Implementation Scope

### Batch 1 — Core field completeness + tax chain
**Script targets**: `seed_core.py`, `seed_test_tenant.py`, `seed_scenario_quote_to_cash.py`  
**New rows estimated**: ~90 rows across ~20 tables  
**Key deliverables**:
- `quote_template_line` (P0 — templates are unusable without lines)
- `quote_line` tax fields + `quote_line_tax_component`
- `change_order_line` tax fields + `change_order_line_tax_component`
- `quote_acceptance` for QUO-900005 (internal acceptance, no public link)
- `quote_approval_comment`, `quote_message` for pending/sent quotes
- Customer fields: `dba_name`, `notes`, `taxability_code`, `last_assigned_tech_id`, `locale`, `timezone`
- Site fields: `notes`, `hazard_notes`, `jurisdiction_code`, `gate_code`, `access_instructions`
- Invoice fields: `issued_at`, `payment_terms`, `customer_notes`
- Auth: `auth_jwk` (1 active signing key)
- `tenant_user.skill_level_code`, `tenant_user.employee_number`

### Batch 2 — Notification pipeline + mobile + usage metering
**Script targets**: `seed_scenario_notifications.py`, `seed_scenario_mobile_sync.py`, `seed_test_tenant.py`  
**New rows estimated**: ~70 rows across ~18 tables  
**Key deliverables**:
- `notification_event` (3 events: quote_accepted, invoice_sent, dunning_reminder)
- `notification_outbox` (email + in_app + push channels — no SMS)
- `notification_delivery_attempt` (1 per outbox row, status=delivered)
- `notification_preference` (owner user email/in_app/push overrides)
- `mobile_device_push_token` (tech user device token)
- `mobile_sync_event_audit` (resolved escalation audit record)
- `mobile_push_permission_state` (tech user granted state)
- `mobile_sync_owner_escalation.resolution_payload` (fill in resolved row)
- `subscription_usage` (current-period rows for all 3 features)
- `tenant_subscription_usage` (current-period summary)
- `usage_ledger` (current-period voice AI + SMS entries)
- `user_dashboard_widget` (3 widgets for owner)
- `tenant_10dlc_profile`
- `user.email_verified_at`, `user.last_login_at`

### Batch 3 — Dispatch + reporting + supplier + remaining optional fields
**Script targets**: `seed_scenario_dispatch.py`, `seed_scenario_reporting.py`, `seed_scenario_supplier_catalog.py`  
**New rows estimated**: ~100 rows across ~15 tables  
**Key deliverables**:
- Rolling dates for all dispatch scenario job timestamps
- `job.estimated_duration_minutes`, `job.quote_version_id`
- `job_time_entry`: GPS coords, variance meters, ETC, mobile capture timestamps
- `job_expense`: vendor names, mobile capture timestamps
- `job_recurrence_rule` (1 weekly rule)
- `customer_communication` (1 on-my-way record in dispatch)
- `contact_endpoint` rows (phone channel, consent_status=unknown)
- `customer_communication_message_read_state` rows
- `customer_communication_unrouted` (1 parked row)
- `nec_calculation_log.job_id`, `client_capture_at`
- `supplier.website`, `api_auth_type`, `api_base_url`
- `pricing_cache` for Wesco items
- `tenant.trial_started_at`, `tenant.stripe_connect_account_id`
- Remaining `tenant_*` config rows (signup, legal, tier override, domain)

### Summary

| Priority | Tables | Fields |
|:---|:---:|:---:|
| 🔴 P0 | 5 | 12 |
| 🟠 P1 | 28 | 47 |
| 🟡 P2 | 22 | 38 |
| 🔒 HOLD | 13 tables | 10 fields | 
| **SD-7 total (P0+P1+P2)** | **55** | **97** |

---

*This document is updated after each SD-7 batch completes. Authoritative seed state: `backend/README-seed-data.md`.*
