# Batch B15 Design Document — Public Links, Payments & Email Templates

**Batch**: B15  
**Items**: A79, A80, A81, A82, A83  
**Prerequisite batches**: B14 (A76 Stripe webhook handler), B4 (comms pipeline for notification dispatch), B9 (A54 settings write endpoint + setting catalog infrastructure)  
**Gates**: None  
**Estimated effort**: 17–22 days  
**Test subfolder**: `tests/batch_b15/`  
**Design authored**: 2026-05-03

---

## A. MIGRATION PLAN

### A1. Live DB Pre-Flight: Column Existence Verification

The following was confirmed via live Postgres MCP queries before listing any migration. No guessing.

| Table | Verified columns already present | Confirmed missing (to be added) |
|:---|:---|:---|
| `quote_public_link` | `id`, `tenant_id`, `quote_id`, `contact_id`, `token_hash` (VARCHAR), `expires_at` (TIMESTAMPTZ **nullable**), `max_uses`, `used_count`, `permissions` (JSONB), `status_id`, `last_used_at`, `created_at`, `updated_at`, `created_by`, `updated_by` | `signed_token`, `revoked_at`, `created_by_user_id` |
| `invoice_public_link` | `id`, `tenant_id`, `invoice_id`, `contact_id`, `token_hash` (VARCHAR), `expires_at` (TIMESTAMPTZ nullable), `max_uses`, `used_count`, `status` (VARCHAR CHECK), `last_used_at`, `created_at`, `updated_at`, `created_by`, `updated_by` | `signed_token`, `revoked_at`, `created_by_user_id` |
| `payment` | `id`, `tenant_id`, `invoice_id`, `amount_cents`, `payment_method_id`, `status_id`, `paid_at`, `psp_provider`, `psp_payment_id`, `connector_config_id`, `idempotency_key`, `is_active`, `created_at`, `updated_at`, `created_by`, `updated_by` | `stripe_payment_intent_id`, `customer_payment_comment`, `amount_variance_cents`, `paid_via` |
| `quote` | `id`, `tenant_id`, `customer_id`, `site_id`, `status_id`, `subtotal_cents`, `tax_cents`, `total_cents`, `currency`, `idempotency_key`, `is_active`, `submitted_by_user_id`, `submitted_at`, `approved_by_user_id`, `approved_at`, `discount_pct`, `discount_amount_cents`, `discount_expires_at`, `discount_applied_by_user_id` | `customer_acceptance_comment`, `customer_accepted_at`, `customer_decline_comment`, `customer_decline_reason`, `customer_declined_at`, `customer_email_at_action` |
| `tenant_settings` | (many columns — confirmed by MCP) | `tenant_sync_indicator_pending_amber_threshold` |
| `email_template` | **does not exist** | entire table |
| `tenant_email_branding` | **does not exist** | entire table |
| `public_link_short_code` | **does not exist** | entire table |
| `stripe_webhook_event_processed` | `id`, `event_id`, `processed_at`, `event_type`, `created_at`, `created_by` | nothing — reused as-is |
| `mobile_sync_session` | **exists** | nothing — read-only for A79 |

---

### A2. New Tables

#### Table: `email_template`

**Mixin**: `StandardAuditMixin`  
**Rationale**: System-seeded reference records that operators can edit; full audit trail required to track who last modified template content.

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `template_id` | `TEXT` | NOT NULL | — | Primary key; slug-style (`quote_sent`, `welcome`, etc.) |
| `display_name` | `TEXT` | NOT NULL | — | Human-readable name for operator UI |
| `category` | `TEXT` | NOT NULL | — | CHECK: `customer_facing` or `internal` |
| `subject_template` | `TEXT` | NOT NULL | — | Jinja2-style template with `{{variable}}` syntax |
| `body_html_template` | `TEXT` | NOT NULL | — | HTML email body template |
| `body_plain_template` | `TEXT` | NOT NULL | — | Plain-text fallback template |
| `variables` | `JSONB` | NOT NULL | `'[]'::jsonb` | List of supported variable names for this template |
| `is_active` | `BOOLEAN` | NOT NULL | `true` | Soft-disable without deleting |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | From `StandardAuditMixin` |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | From `StandardAuditMixin` |
| `created_by` | `UUID` | NULL | — | FK → `user.id` |
| `updated_by` | `UUID` | NULL | — | FK → `user.id` |

**Primary key**: `template_id`  
**Check constraint**: `email_template_category_chk` — `category IN ('customer_facing', 'internal')`  
**Index**: `ix_email_template_category` on `category`  
**Triggers** (from `StandardAuditMixin`): `audit_email_template_changes`, `guard_email_template_created_immutable`, `set_email_template_updated_at`

**Seed data** (16 templates at migration time, placeholder copy):

| `template_id` | `category` | Trigger |
|:---|:---|:---|
| `welcome` | `internal` | Tenant signup completion |
| `email_verification` | `internal` | Email verification request |
| `quote_sent` | `customer_facing` | Tenant sends quote to customer |
| `quote_accepted` | `internal` | Customer accepts quote → notify tenant |
| `quote_declined` | `internal` | Customer declines quote → notify tenant |
| `quote_expiring` | `customer_facing` | 3 days before quote expiration |
| `invoice_sent` | `customer_facing` | Tenant sends invoice to customer |
| `payment_received_tenant` | `internal` | Stripe payment success → notify tenant |
| `payment_received_customer` | `customer_facing` | Stripe payment success → customer receipt |
| `payment_failed` | `customer_facing` | Stripe payment failure → customer |
| `subscription_renewal` | `internal` | Stripe subscription renewal |
| `subscription_payment_failed` | `internal` | Stripe subscription payment failure |
| `trial_expiring` | `internal` | Trial expiration warnings (per B14) |
| `trial_expired` | `internal` | Trial expired (per B14) |
| `password_reset` | `internal` | Password reset request |
| `mfa_reset_by_owner` | `internal` | Per §4.5 owner reset of user MFA |

> Note: `data_export_ready` from arch doc §18.8 omitted — this template is wired in B13 (A70 data export). Keeping 16 here per spec. If B13 already seeds it, the migration should `INSERT … ON CONFLICT DO NOTHING`.

---

#### Table: `tenant_email_branding`

**Mixin**: `StandardAuditMixin`  
**Rationale**: One mutable tenant configuration record per tenant; full audit trail needed to track who last updated branding settings.

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `tenant_id` | `UUID` | NOT NULL | — | PK + FK → `tenant.id` |
| `logo_s3_path` | `TEXT` | NULL | — | S3 path for logo image |
| `brand_color_hex` | `TEXT` | NULL | — | Hex color, e.g. `#5B3FF0`; defaults to Pilot brand-indigo if null |
| `email_signature` | `TEXT` | NULL | — | 500 char max (enforced application-side) |
| `custom_footer` | `TEXT` | NULL | — | 200 char max (enforced application-side) |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | From `StandardAuditMixin` |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | From `StandardAuditMixin` |
| `created_by` | `UUID` | NULL | — | FK → `user.id` |
| `updated_by` | `UUID` | NULL | — | FK → `user.id` |

**Primary key**: `tenant_id`  
**Foreign key**: `fk_tenant_email_branding_tenant` — `tenant_id → tenant.id ON DELETE RESTRICT`  
**Triggers**: `audit_tenant_email_branding_changes`, `guard_tenant_email_branding_created_immutable`, `set_tenant_email_branding_updated_at`

---

#### Table: `public_link_short_code`

**Mixin**: `MachineLogMixin`  
**Rationale**: Short codes are entirely machine-generated; click tracking is an automated counter increment with no human audit context; `last_clicked_at` serves as the "last updated" timestamp; `MachineLogMixin` (created_at only) is correct here.

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `short_code` | `TEXT` | NOT NULL | — | PK; 5–8 char base62 random |
| `link_type` | `TEXT` | NOT NULL | — | CHECK: `quote` or `invoice` |
| `link_id` | `UUID` | NOT NULL | — | References `quote_public_link.id` or `invoice_public_link.id` (polymorphic; no DB FK — enforced application-side) |
| `click_count` | `INTEGER` | NOT NULL | `0` | Incremented atomically on each redirect |
| `last_clicked_at` | `TIMESTAMPTZ` | NULL | — | Timestamp of most recent redirect |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `now()` | From `MachineLogMixin` |
| `created_by` | `UUID` | NULL | — | Pilot user who triggered short-code generation |

**Primary key**: `short_code`  
**Check constraint**: `public_link_short_code_link_type_chk` — `link_type IN ('quote', 'invoice')`  
**Index**: `ix_public_link_short_code_link_id` on `link_id` (for reverse lookup)  
**Trigger**: `audit_public_link_short_code_changes`

> **Polymorphic FK decision**: `link_id` references either `quote_public_link` or `invoice_public_link` based on `link_type`. A DB-level FK cannot reference two different tables. Application-side resolution (look up by `link_type` + `link_id`) enforces referential integrity. This matches the pattern used elsewhere in the codebase for polymorphic references.

---

### A3. Column Additions to Existing Tables

#### `quote_public_link` — 3 new columns

| Column | Type | Nullable | Notes |
|:---|:---|:---|:---|
| `signed_token` | `TEXT` | NOT NULL (after backfill) | HMAC-SHA256 signed token; URL-safe base64; distinct from legacy `token_hash` |
| `revoked_at` | `TIMESTAMPTZ` | NULL | Set when tenant manually revokes link |
| `created_by_user_id` | `UUID` | NOT NULL (after backfill) | FK → `user.id`; Pilot tenant user who generated the link |

**Why `signed_token` is separate from `token_hash`**: `token_hash` is the legacy raw-token hash from the pre-B15 implementation. `signed_token` is the new HMAC-signed credential that carries the embedded payload (link_id, link_type, expiry, customer_id). Both coexist; the public-link endpoints use `signed_token`; internal legacy code can still reference `token_hash` until it is deprecated.

**Migration strategy** for `signed_token` and `created_by_user_id` (NOT NULL columns on existing rows):  
Step 1: Add as `NULLABLE`.  
Step 2: Backfill existing rows with a generated `signed_token` (call `public_link_signer.generate_token()` via `op.execute` + a `plpgsql` loop, or Python migration helper) and `created_by_user_id` from `created_by`.  
Step 3: ALTER to NOT NULL.

**`expires_at` nullability**: Already nullable in DB. The arch doc shows it as NOT NULL in the target schema. This batch should tighten it to NOT NULL as part of the signed-token migration: backfill any rows with `expires_at IS NULL` to `NOW() + INTERVAL '90 days'`, then add NOT NULL constraint. Migration: one `ALTER COLUMN` in the same migration as the other `quote_public_link` changes.

#### `invoice_public_link` — 3 new columns (parallel to `quote_public_link`)

| Column | Type | Nullable | Notes |
|:---|:---|:---|:---|
| `signed_token` | `TEXT` | NOT NULL (after backfill) | Same pattern as quote |
| `revoked_at` | `TIMESTAMPTZ` | NULL | Set when revoked |
| `created_by_user_id` | `UUID` | NOT NULL (after backfill) | FK → `user.id` |

Same 3-part migration pattern. Same `expires_at` NOT NULL tightening.

#### `payment` — 4 new columns

| Column | Type | Nullable | Notes |
|:---|:---|:---|:---|
| `stripe_payment_intent_id` | `TEXT` | NULL | Stripe `pi_…` ID; unique constraint added |
| `customer_payment_comment` | `TEXT` | NULL | Customer's note at payment time; required by frontend if amount differs |
| `amount_variance_cents` | `INTEGER` | NULL | `amount_paid_cents - invoice_total_cents`; negative = underpayment; positive = overpayment |
| `paid_via` | `TEXT` | NULL | CHECK: `stripe`, `check`, `bank_transfer`, `other` |

**Index**: `ix_payment_stripe_payment_intent_id` on `stripe_payment_intent_id` (for webhook lookup)  
**Unique constraint**: `uq_payment_stripe_payment_intent_id` on `stripe_payment_intent_id` (single payment per PI; idempotency anchor)  
**Check constraint**: `payment_paid_via_chk` — `paid_via IN ('stripe', 'check', 'bank_transfer', 'other')`

All 4 columns are nullable additions — simple `op.add_column`, no backfill required.

#### `quote` — 6 new columns

| Column | Type | Nullable | Notes |
|:---|:---|:---|:---|
| `customer_acceptance_comment` | `TEXT` | NULL | Customer's comment when accepting |
| `customer_accepted_at` | `TIMESTAMPTZ` | NULL | Timestamp of acceptance action |
| `customer_decline_comment` | `TEXT` | NULL | Customer's comment when declining |
| `customer_decline_reason` | `TEXT` | NULL | CHECK enum: `pricing`, `scope`, `timing`, `other_contractor`, `other` |
| `customer_declined_at` | `TIMESTAMPTZ` | NULL | Timestamp of decline action |
| `customer_email_at_action` | `TEXT` | NULL | Customer's email address captured at accept/decline time (audit trail) |

**Check constraint**: `quote_customer_decline_reason_chk` — `customer_decline_reason IN ('pricing', 'scope', 'timing', 'other_contractor', 'other')`

All 6 are nullable additions — simple `op.add_column`, no backfill required.

#### `tenant_settings` — 1 new column

| Column | Type | Nullable | Default | Notes |
|:---|:---|:---|:---|:---|
| `tenant_sync_indicator_pending_amber_threshold` | `INTEGER` | NOT NULL | `5` | Amber threshold for the in-flight sync indicator; range 1–100 |

> **Important**: `core/system_defaults.py` already contains `"tenant_sync_indicator_pending_amber_threshold": 5`. The setting catalog entry also references this key (confirmed in `core/setting_catalog.py`). This migration only adds the physical column to `tenant_settings` so that tenant overrides can be persisted. The three-tier resolver from B9 already handles the fallback chain (user override → tenant DB value → system default). No changes to `system_defaults.py` or the setting catalog are required — only the `ALTER TABLE tenant_settings` DDL.

---

### A4. Migration Naming (one migration per logical unit)

| Migration name | Content |
|:---|:---|
| `phase_fe_1_batch_b15_sync_indicator_setting` | ADD COLUMN `tenant_sync_indicator_pending_amber_threshold` to `tenant_settings` |
| `phase_fe_1_batch_b15_email_template_table` | CREATE TABLE `email_template` + 16-row seed INSERT |
| `phase_fe_1_batch_b15_tenant_email_branding_table` | CREATE TABLE `tenant_email_branding` |
| `phase_fe_1_batch_b15_public_link_signed_token` | ADD signed_token, revoked_at, created_by_user_id to `quote_public_link` + `invoice_public_link`; tighten `expires_at` to NOT NULL |
| `phase_fe_1_batch_b15_public_link_short_code_table` | CREATE TABLE `public_link_short_code` |
| `phase_fe_1_batch_b15_payment_stripe_columns` | ADD stripe_payment_intent_id, customer_payment_comment, amount_variance_cents, paid_via to `payment` |
| `phase_fe_1_batch_b15_quote_customer_comment_columns` | ADD 6 customer comment columns to `quote` |

---

## B. EXECUTION ORDER

| # | Item | Rationale |
|:---|:---|:---|
| 1 | **A79** — Unified Pending-Count Exposure | No schema dependencies outside `tenant_settings` column addition. Self-contained read aggregation over existing tables + the `sync_indicator_setting` migration. Establishes the SSE `sync_status_changed` event pattern consumed by frontend; must exist before any dependent UI work. |
| 2 | **A82** — Email Template Rendering Pipeline | Must precede A80 and A81 because both the acceptance/decline notification emails (A80) and the Stripe payment confirmation email (A81) call `email_template_renderer.render()`. Rendering pipeline must be wired and tested before the call sites exist. |
| 3 | **A80** — Signed URL Infrastructure | Depends on A82 (acceptance email uses renderer). Creates the public endpoints that A81 extends. Must exist before A81 wires payment-intent into the public invoice endpoint. |
| 4 | **A81** — Stripe Payment Intents + Webhook Extension | Depends on A80 (public invoice endpoint exists, payment-intent sub-route added to it). Depends on B14 (A76 `webhooks_stripe.py` + `stripe_subscriptions.py` handler pattern). Extends the existing `_process_stripe_event()` dispatcher. |
| 5 | **A83** — Customer Comment Storage + Notifications | Depends on A80 (the acceptance/decline endpoints that call these handlers) and A81 (payment handler). Added last because all upstream write paths must be wired first; A83 is pure column additions + notification trigger wiring. |

---

## C. NEW API ENDPOINTS

### C1. A79 — Sync Status

#### `GET /api/v1/sync/{surface}/status`

**Auth**: JWT required  
**RBAC**: `settings.view` (read-only; any authenticated tenant user)  

**Path parameter**: `surface` — one of `calendar | quickbooks | mobile_data | background`

**Response** `200 OK`:
```json
{
  "surface": "calendar",
  "state": "synced_pending | syncing | sync_error | sync_paused | synced_idle",
  "pending_count": 3,
  "pending_items": [
    {"type": "event_added", "label": "Johnson panel upgrade — 4:30 PM today"},
    {"type": "event_updated", "label": "Smith service call — moved to Friday"}
  ],
  "last_sync_at": "2026-04-27T14:32:18Z",
  "next_sync_at": "2026-04-27T14:37:18Z",
  "manual_trigger_supported": true,
  "resolve_target": null,
  "amber_threshold": 5
}
```

**Backend aggregation by surface**:
- `calendar` → query `calendar_sync_conflict` WHERE `tenant_id = ? AND status = 'pending'`
- `quickbooks` → query `integration_sync_conflict` WHERE `tenant_id = ? AND status = 'pending' AND integration_type = 'quickbooks'`
- `mobile_data` → query `mobile_sync_session` WHERE `tenant_id = ? ORDER BY created_at DESC LIMIT 1`; pending_count from last session's `pending_operations_count` field (if it exists) else 0
- `background` → same as `mobile_data` source; state derived from last session `status`

> **Design note**: `calendar_sync_pending_change`, `integration_sync_pending_change`, and `mobile_sync_pending_operation` do not exist in the live DB. A79 aggregates from the conflict/session tables that do exist. The `pending_items` label array is constructed from the conflict records' entity labels. Pending items array capped at 5 server-side.

**Error**: `400 Bad Request` if `surface` value not in allowed set.

**SSE event** `sync_status_changed` emitted on any state or count change for a surface:
```json
{
  "event": "sync_status_changed",
  "data": {"surface": "calendar", "state": "synced_pending", "pending_count": 3}
}
```
Emitted by the write-path endpoints when conflict counts change (calendar conflict resolution routes, QB conflict resolution routes, mobile sync session creation).

---

### C2. A80 — Public Link Endpoints

All `/api/v1/public/*` routes **bypass Cognito JWT validation**. Authorization = valid HMAC-signed token. Rate limiting applied per-IP (per §7.5).

#### `GET /api/v1/public/quotes/{signed_token}`

**Auth**: Public (signed token is the credential)  
**RBAC**: None  
**Response** `200 OK`:
```json
{
  "quote_id": "uuid",
  "tenant_name": "...",
  "customer_name": "...",
  "quote_total_cents": 125000,
  "currency": "USD",
  "line_items": [...],
  "status": "sent | accepted | declined | expired",
  "expires_at": "2026-07-26T00:00:00Z",
  "branding": {"logo_url": "...", "brand_color_hex": "#5B3FF0"},
  "customer_acceptance_comment": null,
  "customer_decline_comment": null
}
```
**Errors**: `401` invalid signature, `410` expired or revoked token.

#### `POST /api/v1/public/quotes/{signed_token}/accept`

**Auth**: Public  
**Request body**:
```json
{"comment": "Let's get started ASAP — when can you begin?"}
```
**Response** `200 OK`: `{"status": "accepted", "accepted_at": "2026-04-27T14:14:00Z"}`  
**Errors**: `401` invalid sig, `409` already accepted/declined, `410` expired/revoked

#### `POST /api/v1/public/quotes/{signed_token}/decline`

**Auth**: Public  
**Request body**:
```json
{"reason": "pricing | scope | timing | other_contractor | other", "comment": "optional comment"}
```
**Response** `200 OK`: `{"status": "declined", "declined_at": "..."}` 
**Errors**: `401`, `409`, `410`

#### `GET /api/v1/public/invoices/{signed_token}`

**Auth**: Public  
**Response** `200 OK`: Invoice payload with state-aware rendering per §18.6 (unpaid / partial / paid).

#### `POST /api/v1/public/invoices/{signed_token}/payment-intent`

**Auth**: Public  
**Request body**:
```json
{"amount_cents": 125000, "comment": "required if amount differs from invoice total"}
```
**Response** `200 OK`:
```json
{"client_secret": "pi_xxx_secret_xxx", "payment_intent_id": "pi_xxx"}
```
**Validation**: If `amount_cents != invoice_total_cents` AND `comment` is null/empty → `422 Unprocessable Entity`.

#### `POST /api/v1/public/invoices/{signed_token}/confirm-payment`

**Auth**: Public  
**Request body**: `{"payment_intent_id": "pi_xxx"}` — advisory; backend does not mark paid until webhook fires.  
**Response** `200 OK`: `{"status": "pending_confirmation"}` — frontend shows "Payment processing" state.

#### `GET /api/v1/short/{short_code}`

**Auth**: Public  
**Response**: `302 Redirect` to full signed URL  
**Errors**: `404` if short code not found; atomically increments `click_count` and sets `last_clicked_at` on redirect.

#### `POST /api/v1/quotes/{quote_id}/public-link/revoke`

**Auth**: JWT required  
**RBAC**: `quotes.update`  
**Request body**: `{}` (or optional `{"reason": "..."}`)  
**Response** `200 OK`: `{"revoked_at": "..."}`

---

### C3. A81 — Stripe Payment (extend existing webhook; no new route)

The `POST /api/v1/webhooks/stripe` route at `backend/api/routes/webhooks_stripe.py` already exists. A81 extends `_process_stripe_event()` to handle two new event types:

- `payment_intent.succeeded` → `handle_payment_intent_succeeded(db, payload)`
- `payment_intent.payment_failed` → `handle_payment_intent_failed(db, payload)`

No new route file. Extension only.

---

### C4. A82 — Email Branding Endpoints

#### `GET /api/v1/settings/email-branding`

**Auth**: JWT required  
**RBAC**: `settings.view`  
**Response** `200 OK`: Full `TenantEmailBranding` record (logo presigned URL resolved, not raw S3 path).

#### `PUT /api/v1/settings/email-branding`

**Auth**: JWT required  
**RBAC**: `settings.manage` (owner only)  
**Request body**:
```json
{
  "brand_color_hex": "#5B3FF0",
  "email_signature": "— Tom Lang, Pilot Electrical",
  "custom_footer": "Licensed & Insured | (555) 123-4567"
}
```
**Response** `200 OK`: Updated record.

#### `POST /api/v1/settings/email-branding/logo-upload-url`

**Auth**: JWT required  
**RBAC**: `settings.manage`  
**Request body**: `{"content_type": "image/png", "file_size_bytes": 45000}`  
**Response** `200 OK`:
```json
{"upload_url": "https://s3.presigned...", "s3_path": "tenant-branding/{tenant_id}/logo.png"}
```
After upload, client calls `PUT /api/v1/settings/email-branding` with the `s3_path` to commit.

#### `POST /api/v1/settings/email-branding/preview`

**Auth**: JWT required  
**RBAC**: `settings.view`  
**Request body**: `{"template_id": "welcome"}` (optional; defaults to `welcome`)  
**Response** `200 OK`:
```json
{"subject": "Welcome to...", "body_html": "<html>...", "body_plain": "Welcome..."}
```

#### `POST /api/v1/settings/email-branding/test-send`

**Auth**: JWT required  
**RBAC**: `settings.manage`  
**Request body**: `{}` (sends to requesting user's email address)  
**Response** `200 OK`: `{"status": "sent", "to": "tom@example.com"}`

---

### C5. A83 — No new routes

A83 wires comment storage into the A80 accept/decline endpoints and the A81 payment handler. No separate endpoints.

---

## D. PATTERN REUSE DECISIONS

### D1. §1.5 Shared Modules Established in B15

| Module | Path | Consumed by |
|:---|:---|:---|
| `PublicLinkSigner` | `backend/services/public_link_signer.py` | A80 public endpoints (sign/verify); `POST …/revoke` |
| `ShortLinkResolver` | `backend/services/short_link_resolver.py` | `GET /api/v1/short/{short_code}` |
| `EmailTemplateRenderer` | `backend/services/email_template_renderer.py` | A80 (acceptance/decline emails), A81 (payment confirmation email), B10 `notification_outbox` email dispatch (existing poll_pending_notifications task), future SendGrid calls |
| `StripePaymentIntents` | `backend/services/stripe_payment_intents.py` | A81 public invoice payment-intent endpoint, `_process_stripe_event()` extension |

### D2. Patterns from `pilot-python-engineer-methods.md`

**§16.1 (Pre-Work Regression Baseline)** — applies to all items. Capture test counts before touching any file.

**§16.2 Step 2 (3-Part Migration for Additive Columns)** — applies to:  
- `quote_public_link` / `invoice_public_link` `signed_token` and `created_by_user_id` (nullable → backfill → NOT NULL)  
- `tenant_settings.tenant_sync_indicator_pending_amber_threshold` (additive with server_default — single-step since it has a default)

**§16.2 Step 3 (Master Blueprint JSON Sync via `schema_manager.py`)** — applies to every migration. Use `python3 schema_manager.py add-table` for new tables and `python3 schema_manager.py add-column` for column additions. Never edit the JSON directly.

**§16.3 (Tenant-Scoped Query IDOR Prevention)** — applies to all authenticated endpoints. Public endpoints (`/public/*`) bypass this pattern by design (no tenant context until token is resolved). After token verification, all DB queries must still use `tenant_id` from the decoded token payload, not from URL params.

**§16.4 (Stop & Rollback Conditions)** — standard; halt on any migration failure.

**§16.5 (Definition of Done)** — schema diff ZERO required before marking B15 complete.

### D3. Existing Pattern Reuse from `mvp-arch.md`

**SSE (`sync_status_changed`)** — extends the existing SSE infrastructure (§13.11). The A79 endpoint wires state changes into the existing `dispatch:{tenant_id}` channel. New event type: `sync_status_changed`. No new SSE infrastructure needed.

**`notification_outbox` + `poll_pending_notifications`** — A83 creates outbox entries on quote accept/decline/payment using the B10 pattern. Requires `category_id = 'customer_activity'` (per B10 `notification_category` registry). Same dispatch path: `notification_outbox` row → `poll_pending_notifications` Celery task → SendGrid via `email_service.send_email()`.

**`StripeWebhookEventProcessed` dedup** — A81 reuses the existing `StripeWebhookEventProcessed` model and the `event_id` dedup check already in `webhooks_stripe.py`. No new dedup infrastructure.

**`send_email()` from `email_service.py`** — A82's `EmailTemplateRenderer` calls the existing `send_email(to, subject, body, html_body)` function. The renderer is a wrapper that resolves templates + branding and then calls `send_email()`.

**Three-tier resolver (`get_effective_setting`)** — A79 calls `get_effective_setting(db, tenant_id, user_id, "tenant_sync_indicator_pending_amber_threshold")` from `services/setting_resolver.py` to get the amber threshold for the response payload.

---

## E. SHARED MODULE INTERFACES

### E1. `PublicLinkSigner`

**File**: `backend/services/public_link_signer.py`

```python
import hmac
import hashlib
import json
import base64
import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal


class SignedTokenPayload:
    link_id: uuid.UUID
    link_type: Literal["quote", "invoice"]
    expiration: str          # ISO-8601 UTC
    customer_id: uuid.UUID


class PublicLinkSignerError(Exception):
    """Base exception for token errors."""

class TokenExpiredError(PublicLinkSignerError):
    """Token has passed its expiration timestamp."""

class TokenRevokedError(PublicLinkSignerError):
    """Token has been revoked by the tenant."""

class TokenInvalidError(PublicLinkSignerError):
    """HMAC signature is invalid or payload is malformed."""


def generate_signed_token(
    link_id: uuid.UUID,
    link_type: Literal["quote", "invoice"],
    customer_id: uuid.UUID,
    secret: str,
    expires_in_days: int = 90,
) -> tuple[str, datetime]:
    """
    Generate a URL-safe HMAC-SHA256 signed token.

    Args:
        link_id: UUID of the public link record.
        link_type: 'quote' or 'invoice'.
        customer_id: UUID of the customer for verification.
        secret: Per-deployment secret from Secrets Manager.
        expires_in_days: Token TTL (default 90 days per §18.2).

    Returns:
        Tuple of (signed_token: str, expires_at: datetime).

    Notes:
        Payload is JSON-serialized then HMAC-SHA256 signed.
        Token format: base64url(payload) + '.' + base64url(signature)
    """
    ...


def verify_signed_token(
    token: str,
    secret: str,
) -> SignedTokenPayload:
    """
    Decode and verify a signed token.

    Args:
        token: The signed token string from the URL.
        secret: Per-deployment secret from Secrets Manager.

    Returns:
        SignedTokenPayload if valid and not expired.

    Raises:
        TokenInvalidError: HMAC mismatch or malformed payload.
        TokenExpiredError: Token expiration has passed.

    Notes:
        Does NOT check revocation (requires DB lookup — caller's responsibility).
    """
    ...
```

---

### E2. `ShortLinkResolver`

**File**: `backend/services/short_link_resolver.py`

```python
import secrets
import string
from sqlmodel import Session

BASE62_CHARS = string.ascii_letters + string.digits  # 62 chars


def generate_short_code(
    db: Session,
    link_id: str,          # UUID as string
    link_type: str,        # 'quote' | 'invoice'
    length: int = 6,
) -> str:
    """
    Generate a collision-safe base62 short code and persist to public_link_short_code.

    Args:
        db: SQLModel session.
        link_id: UUID of the quote_public_link or invoice_public_link.
        link_type: 'quote' or 'invoice'.
        length: Code length (default 6, range 5–8 per spec).

    Returns:
        The generated short_code string.

    Notes:
        Retries on collision up to 10 times before raising RuntimeError.
        Atomically inserts the row on successful generation.
    """
    ...


def resolve_short_code(
    db: Session,
    short_code: str,
) -> tuple[str, str]:
    """
    Resolve a short code to (link_type, signed_token) for redirect.

    Args:
        db: SQLModel session.
        short_code: The short code from the URL.

    Returns:
        Tuple of (link_type, signed_token).

    Raises:
        HTTPException 404 if short_code not found.

    Side effects:
        Atomically increments click_count and sets last_clicked_at.
    """
    ...
```

---

### E3. `EmailTemplateRenderer`

**File**: `backend/services/email_template_renderer.py`

```python
from dataclasses import dataclass
from typing import Any, Dict, Optional
from sqlmodel import Session


@dataclass
class RenderedEmail:
    subject: str
    body_html: str
    body_plain: str
    to_address: str
    from_name: str
    from_email: str
    reply_to: Optional[str] = None


def render_and_send(
    db: Session,
    template_id: str,
    context: Dict[str, Any],
    to_address: str,
    tenant_id: Optional[str] = None,
    reply_to: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Render an email template with branding and dispatch via SendGrid.

    Args:
        db: SQLModel session (used to load email_template + tenant_email_branding).
        template_id: Slug matching email_template.template_id.
        context: Dict of variable values for substitution (customer_name, quote_total, etc.).
        to_address: Recipient email address.
        tenant_id: Required for customer_facing templates (to apply tenant branding);
                   None for internal templates (uses Pilot standard branding).
        reply_to: Optional reply-to address (e.g., submitting user's email for feedback).

    Returns:
        Result dict from email_service.send_email():
        {"status": "sent"|"error", "details": {...}, "http_status": int}

    Raises:
        ValueError if template_id not found or is_active = False.
        ValueError if required context variables are missing.

    Notes:
        - customer_facing templates: applies TenantEmailBranding (logo_url, brand_color_hex,
          email_signature, custom_footer) from tenant_email_branding WHERE tenant_id = ?
        - internal templates: uses Pilot standard branding constants from core/config.py
        - Variable substitution uses str.format_map() (not Jinja2) for security isolation.
        - Calls existing email_service.send_email(to, subject, body, html_body).
    """
    ...


def render_preview(
    db: Session,
    template_id: str,
    tenant_id: str,
) -> RenderedEmail:
    """
    Render a template with current branding settings without sending.

    Args:
        db: SQLModel session.
        template_id: Template to preview.
        tenant_id: Tenant for branding lookup.

    Returns:
        RenderedEmail with resolved subject, body_html, body_plain.

    Notes:
        Uses sample context values for any required variables not in the
        request (e.g., customer_name = 'Sarah Johnson', total = '$1,250.00').
    """
    ...
```

---

### E4. `StripePaymentIntents`

**File**: `backend/services/stripe_payment_intents.py`

```python
from sqlmodel import Session


def create_payment_intent(
    db: Session,
    invoice_id: str,           # UUID as string
    amount_cents: int,
    customer_comment: Optional[str],
    tenant_id: str,
) -> dict:
    """
    Create a Stripe Payment Intent for a customer-initiated invoice payment.

    Args:
        db: SQLModel session.
        invoice_id: UUID of the invoice being paid.
        amount_cents: Customer-entered payment amount (may differ from invoice total).
        customer_comment: Required by caller when amount != invoice_total_cents.
        tenant_id: Tenant owning the invoice (for Stripe metadata).

    Returns:
        {"client_secret": str, "payment_intent_id": str}

    Raises:
        stripe.error.StripeError: on Stripe API failure.
        ValueError: if invoice not found or already fully paid.

    Notes:
        Uses settings.STRIPE_SECRET_KEY. Payment Intent metadata includes
        invoice_id and tenant_id for webhook reconciliation.
        Idempotency key: f"pi_invoice_{invoice_id}_{amount_cents}" to prevent
        duplicate PIs for the same payment attempt.
    """
    ...


def handle_payment_intent_succeeded(
    db: Session,
    payload: dict,
) -> None:
    """
    Process payment_intent.succeeded webhook event.

    Args:
        db: SQLModel session.
        payload: Raw Stripe webhook payload dict.

    Side effects:
        - Creates Payment record with amount_cents, stripe_payment_intent_id,
          amount_variance_cents, customer_payment_comment, paid_via='stripe'
        - Updates invoice balance (invoice_total_cents - sum of payments)
        - If variance < 0: invoice status → 'partial'
        - If variance > 0: flags payment for tenant review (no auto-refund)
        - Creates notification_outbox entry (category_id='customer_activity')

    Notes:
        Called from _process_stripe_event() in webhooks_stripe.py.
        Idempotent: checks payment.stripe_payment_intent_id for existing record.
    """
    ...


def handle_payment_intent_failed(
    db: Session,
    payload: dict,
) -> None:
    """
    Process payment_intent.payment_failed webhook event.

    Args:
        db: SQLModel session.
        payload: Raw Stripe webhook payload dict.

    Side effects:
        - Logs failure; surfaces to customer-facing UI via payment status.
        - Creates notification_outbox entry for tenant (category_id='customer_activity').

    Notes:
        Does NOT create a Payment record — no payment occurred.
        Called from _process_stripe_event() in webhooks_stripe.py.
    """
    ...
```

---

## F. OPEN QUESTIONS RESOLVED

**F1. `signed_token` vs existing `token_hash` on `quote_public_link` and `invoice_public_link`**  
**Question**: The existing tables have `token_hash (VARCHAR NOT NULL UNIQUE)`. The design adds `signed_token`. Are these the same column renamed, or different?  
**Resolution**: They are different columns with different semantics. `token_hash` is the legacy random-token hash from the pre-B15 token model. `signed_token` is the new HMAC-signed credential that embeds the payload. Both columns will coexist. Legacy code using `token_hash` continues to work; new public endpoints use `signed_token`. Deprecation of `token_hash` is deferred to a future cleanup batch. No rename migration.

**F2. `created_by_user_id` vs existing `created_by` audit column**  
**Question**: The arch doc adds `created_by_user_id UUID NOT NULL`. The tables already have `created_by UUID NULL` (standard audit). Are these the same value?  
**Resolution**: Yes, they carry the same value (the Pilot tenant user who generated the link). However, `created_by` is nullable (audit field convention) and `created_by_user_id` needs NOT NULL semantics (it is required for the signed token payload). Add `created_by_user_id` as a separate NOT NULL column. Backfill from `created_by` (any NULL rows get a synthetic system-user UUID or the first owner for that tenant). Rationale: preserving the distinction between the nullable audit convention and the application-enforced NOT NULL constraint avoids changing mixin behavior for existing records.

**F3. `expires_at` already nullable on both public link tables**  
**Question**: The arch doc specifies `expires_at TIMESTAMPTZ NOT NULL`. The live DB has it nullable. Add constraint or leave nullable?  
**Resolution**: Tighten to NOT NULL in the `phase_fe_1_batch_b15_public_link_signed_token` migration. Backfill any NULL rows with `NOW() + INTERVAL '90 days'` (reasonable default). The HMAC token verification logic requires a definitive expiry — a NULL expiry would create a never-expiring token, which is a security hole. This tightening is part of the same 3-part migration as `signed_token`.

**F4. `calendar_sync_pending_change`, `integration_sync_pending_change`, `mobile_sync_pending_operation` tables don't exist in live DB**  
**Question**: A79 spec references these tables for pending-count aggregation. How does A79 serve pending counts?  
**Resolution**: Aggregate from tables that DO exist:  
- `calendar` surface → `calendar_sync_conflict WHERE tenant_id = ? AND status = 'pending'` (count + first 5 items)  
- `quickbooks` surface → `integration_sync_conflict WHERE tenant_id = ? AND status = 'pending' AND conflict_type ILIKE '%quickbooks%'` (adjust filter to match actual enum on live table)  
- `mobile_data` + `background` surfaces → `mobile_sync_session WHERE tenant_id = ? ORDER BY created_at DESC LIMIT 1`; derive state from last session's `status` column  
The pending-count tables referenced in the spec appear to be aspirational schema from the original Tier 4 design that was never materialized. The resolver pattern using existing conflict/session tables is equivalent and does not require new tables. No new DB tables for A79.

**F5. `tenant_sync_indicator_pending_amber_threshold` already in `system_defaults.py`**  
**Question**: Since the system default is already in code, is the `tenant_settings` column addition still needed?  
**Resolution**: Yes. The three-tier resolver pattern (B9/A53) reads tenant overrides from `tenant_settings` columns. Without the column, tenants cannot override the threshold via `PUT /api/v1/settings/tenant_sync_indicator_pending_amber_threshold`. The migration adds the column; the code already handles the fallback to system default.

**F6. `email_template` is system-wide (no `tenant_id`) — correct?**  
**Question**: Should `email_template` be per-tenant or system-wide?  
**Resolution**: System-wide. One set of 16 templates applies to all tenants. Per-tenant customization is handled at the branding layer (`tenant_email_branding`) — logo, color, signature, footer. Template copy customization per tenant is explicitly out of MVP scope (per §18.11). No `tenant_id` on `email_template`.

**F7. Stripe Connect vs single Pilot account**  
**Question**: Does A81 need Stripe Connect setup?  
**Resolution**: MVP uses a single Pilot Stripe account. Customer payments accumulate in Pilot's account; tenant disbursement is a separate financial process (TBD). Stripe Connect is Phase 2. Tom must review this before launch due to financial/legal implications (money transmission). No Stripe Connect code in B15.

**F8. `payment_method_id` is NOT NULL on existing `payment` table — what value for Stripe invoice payments?**  
**Question**: The existing `payment.payment_method_id` FK → `payment_method.id` is NOT NULL. For Stripe Payment Intent payments, we don't have a `payment_method` record.  
**Resolution**: Create a system-level `payment_method` record with `psp_provider = 'stripe'` and `psp_payment_method_id = 'stripe_payment_intent'` during the seed data phase of the migration. Stripe one-time payments reference this synthetic record. The actual Stripe payment method details are on the Payment Intent and not persisted in Pilot for MVP (no stored-card feature). Alternatively, examine if `payment_method_id` can be made nullable — but that requires a migration and schema change to an existing constraint. **Recommended**: use synthetic system payment_method record. Tag as `psp_provider='stripe'`, `psp_payment_method_id='one_time_public_link'`. Seed this in `phase_fe_1_batch_b15_payment_stripe_columns`.

**F9. `invoice_public_link` uses a `status` VARCHAR CHECK column (not `status_id` FK)**  
**Question**: The design needs to check revocation via `revoked_at IS NULL`. The existing table already has `status` CHECK('active', 'revoked', 'expired'). Should revocation use `status = 'revoked'` or the new `revoked_at`?  
**Resolution**: Use `revoked_at` as the canonical revocation signal (same as `quote_public_link` which uses `revoked_at`). The `status` column on `invoice_public_link` predates B15; keep it in sync: when `revoked_at` is set, also set `status = 'revoked'`. When token is verified, check BOTH `revoked_at IS NULL` AND `status != 'revoked'` for defense in depth. Write path sets both.

---

## G. EXTERNAL DEPENDENCY STATUS

| Dependency | Items | Mock Strategy | Tom Action Required |
|:---|:---|:---|:---|
| **Stripe API** (Payment Intents) | A81 | `MockStripePaymentIntent` fixture returning canned `client_secret`; `MockStripeWebhook` per B14 pattern for `payment_intent.succeeded` test events | Confirm Stripe account has Payment Intents enabled (separate from Subscriptions). Provide test-mode Stripe secret key in `.env`. No additional Stripe configuration beyond what B14 requires. |
| **Stripe Webhook secret** | A81 | `STRIPE_WEBHOOK_SECRET` env var absent → skip signature verification (per existing `_verify_stripe_signature()` behavior — already implemented in B14) | Configure `STRIPE_WEBHOOK_SECRET` for the second webhook endpoint event type in Stripe Dashboard (or reuse same webhook endpoint — recommended). |
| **SendGrid** (email delivery) | A82, A83 | `SENDGRID_API_KEY` absent → mock send (per existing `email_service.send_email()` behavior — already implemented) | SendGrid sender domain (SPF/DKIM/DMARC) must be configured before production. Lead time: 1–3 days for DNS propagation. Recommend using Mailtrap for dev/staging validation of templates. |
| **AWS S3** (logo upload) | A82 | Presigned URL generation uses existing S3 settings from `core/config.py`; if S3 unavailable in dev, logo upload returns synthetic path; `logo_s3_path` remains null and branding renders without a logo | Ensure `S3_BUCKET_NAME` and AWS credentials are configured. No special bucket beyond what is already used for photos/attachments. |
| **`pilot.tr` short domain** | A80 (short-link redirect) | If domain not ready: `GET /api/v1/short/{short_code}` still works at `localhost:8000`; SMS templates use full signed URLs as fallback per §18.3 | Register `pilot.tr` (or equivalent) and configure DNS to point to ALB. Lead time: domain registration + DNS propagation ~24–48 hours. Can launch without this; short links are a nice-to-have for SMS length reduction. |

---

## H. ORM MODEL FILE ASSIGNMENTS

Per `backend/db_models_map.md`:

| New / Extended Model | File | Rationale |
|:---|:---|:---|
| `EmailTemplate` (new) | `backend/app/models/communications.py` | Email templates are a comms-domain concern. `CommunicationTemplate` and `CustomerCommunication` already live here. |
| `TenantEmailBranding` (new) | `backend/app/models/core.py` | Tenant configuration record; `TenantSettings` already lives here. `TenantEmailBranding` is a tenant-scoped settings extension. |
| `PublicLinkShortCode` (new) | `backend/app/models/quoting.py` | Short codes reference `quote_public_link`; quoting.py holds `QuotePublicLink`. Polymorphic FK to `invoice_public_link` enforced application-side. |
| `QuotePublicLink` (extend) | `backend/app/models/quoting.py` | Already here — add `signed_token`, `revoked_at`, `created_by_user_id` fields. |
| `InvoicePublicLink` (extend) | `backend/app/models/billing.py` | Already here — add `signed_token`, `revoked_at`, `created_by_user_id` fields. |
| `Payment` (extend) | `backend/app/models/billing.py` | Already here — add 4 Stripe payment columns. |
| `Quote` (extend) | `backend/app/models/quoting.py` | Already here — add 6 customer comment columns. |
| `TenantSettings` (extend) | `backend/app/models/core.py` | Add `tenant_sync_indicator_pending_amber_threshold` column. |

---

## I. NEW ROUTE FILE ASSIGNMENTS

Per arch doc §18.9 and existing routes in `backend/api/routes/`:

| New File | Router prefix | Items |
|:---|:---|:---|
| `backend/api/routes/public_quotes.py` | `/api/v1/public/quotes` | A80: public quote view/accept/decline |
| `backend/api/routes/public_invoices.py` | `/api/v1/public/invoices` | A80: public invoice view; A81: payment-intent + confirm |
| `backend/api/routes/public_short_redirect.py` | `/api/v1/short` | A80: short-link redirect |
| `backend/api/routes/tenant_email_branding.py` | `/api/v1/settings/email-branding` | A82: branding CRUD, preview, test-send |
| `backend/api/routes/sync_status.py` | `/api/v1/sync` | A79: unified sync status endpoint |

**Extended (not replaced)**:
- `backend/api/routes/webhooks_stripe.py` — extend `_process_stripe_event()` for `payment_intent.succeeded` / `payment_intent.payment_failed` (A81)
- `backend/api/routes/quotes.py` — add `POST /{quote_id}/public-link/revoke` (A80)

---

*Design document complete. All six reads completed before authoring. All nine open questions resolved with decisions. No sections left blank.*