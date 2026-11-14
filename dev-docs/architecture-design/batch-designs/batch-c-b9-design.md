# C-B9 — 10DLC Provisioning State Machine + Stripe Checkout Setup Charge + Sole-Prop OTP Loop

**Batch**: C-B9
**Mode**: Pilot Python Engineer (Part A) → Pilot Web UI Designer → Pilot React Engineer (Part B)
**Prerequisite**: C-B8 ✅ (`carrier_fee_schedule` table + `telnyx_quoting.py` + `GET /messaging/quote` endpoint)
**Source of truth**: `pilot-tech-impl-spec-v1.md` §5.2–5.5, §6.8, §11.2; Q#1 + Q#2 resolutions
**Status**: ✅ Design approved by Tom 2026-08-05 — UI design spec in progress
**Date**: August 5, 2026

---

## Overview

C-B9 implements the full 10DLC provisioning lifecycle: the 12-state machine that takes a tenant from "not started" through brand registration, campaign registration, phone number assignment, and active SMS sending. It adds the Stripe Checkout one-time setup charge (`setup_future_usage: off_session`), the sole-proprietor OTP loop (SMS-delivered per Q#2), and the brand registration input fields needed for the Telnyx API submission.

This is a **mixed batch** (Python + React). Part A (Python Engineer) builds the backend: migration, state machine service, Telnyx carrier methods, Stripe Checkout, webhook handler, API endpoints, Celery tasks. Part B (React Engineer) builds the frontend messaging setup page — but only after a UI design spec is authored by the pilot-web-ui-designer and Tom-approved.

**Secondary task** (from C-B8 research): Add brand registration input fields (`website`, `stock_symbol`, `vertical`) to `tenant_10dlc_profile` so the tenant can enter their brand info in Pilot, which is then submitted to Telnyx via the API.

---

## A. Input Read Summary

| Input | Source | Key findings |
|---|---|---|
| Spec §5.2 — State Machine | `pilot-tech-impl-spec-v1.md` §5.2 | 12 states: `not_started` → `quoting` → `awaiting_payment` → `payment_failed` → `brand_submitted` → `awaiting_otp` (sole prop) → `brand_verified` → `brand_rejected` → `campaign_submitted` → `campaign_rejected` → `number_assigned` → `active` → `suspended`. Persist every transition with audit row. `brand_rejected`/`campaign_rejected` trigger automatic Stripe refund + operator alert. |
| Spec §5.3 — Entity Type Routing | Same, §5.3 | "Does your business have an EIN?" → `standard` (automated) vs `sole_proprietor` (OTP loop). Q#2 resolution: **OTP is SMS-delivered**, not email. Spec §5.3 "email to Telnyx desk" is **incorrect** — must verify against Telnyx help center before building. |
| Spec §5.5 — Setup Charge | Same, §5.5 | One-time Stripe Checkout Session (`mode="payment"`, `setup_future_usage: "off_session"`). Inline `price_data` with quote total. On `checkout.session.completed`: attach PM as `customer.invoice_settings.default_payment_method`, transition to `brand_submitted`, enqueue Telnyx provisioning. |
| Spec §6.8 — Webhooks | Same, §6.8 | `checkout.session.completed` handler: if `metadata.purpose == "a2p_10dlc_setup"` → attach PM, transition, enqueue. Currently a **stub** in `stripe_subscriptions.py`. |
| Spec §11.2 — Telnyx Test Scenarios | Same, §11.2 | 8 scenarios: standard happy path, sole prop happy path, OTP timeout, brand rejected, campaign rejected, checkout abandoned, fee schedule change, month 4 recurring. |
| Q#1 resolution | Same, appendix | Telnyx has no pre-transaction pricing API. `carrier_fee_schedule` is operator-maintained (C-B8 ✅). |
| Q#2 resolution | Same, appendix | OTP delivered via SMS to brand's mobile number, not email. Full request/relay procedure must be verified against Telnyx help center before building. |
| C-B8 Telnyx API research | `telnyx_quoting.py` docstring | Brand registration: `POST /v2/10dlc/brands` — needs entity_type, legal_business_name, dba, ein, phone_number, street, city, state, postal_code, country, email, stock_symbol, website, vertical. Campaign registration: `POST /v2/10dlc/campaigns` — needs brand_id, campaign_name, use_case, description, sample_message_1/2, message_flow, opt_in/out/help keywords + messages, sub_use_cases. |
| C-SPIKE-2 research | `pilot-launch-plan.md` §C-SPIKE-2 | TCR requires website URL + privacy policy + ToS URLs. No SaaS platform hosts these for customers. Proposed: Pilot hosts tenant compliance page at `sms.pilotfortrades.com/{slug}`. **4 open questions for Tom — not yet answered.** |
| Live DB — `tenant_messaging_registration` | MCP (this session) | 18 columns: id, tenant_id, entity_type, status, telnyx_brand_id, telnyx_campaign_id, telnyx_phone_number, quoted_setup_cents, quoted_monthly_cents, stripe_checkout_id, stripe_payment_intent, otp_requested_at, otp_verified_at, failure_reason, created_at, updated_at, created_by, updated_by. PK on id, UNIQUE on tenant_id, FK to tenant. **No CHECK constraint on status** — state validation is in the service layer. |
| Live DB — `tenant_10dlc_profile` | MCP (this session) | 16 columns: tenant_id (PK), legal_business_name, dba_name, ein, hq_address_line1/2, hq_city, hq_state, hq_postal_code, hq_country (default 'US'), support_email, support_phone, + 4 audit. **Missing: website, stock_symbol, vertical** — needed for Telnyx brand registration API. |
| Live DB — `tenant` | MCP (this session) | Has `stripe_customer_id` (TEXT, nullable), `free_period_ends_at`, `charter_member_number`, `charter_eligible`. |
| Existing code — `SmsCarrier` ABC | `sms_carrier.py` | Abstract methods: `provision_number()`, `send_message()`, `verify_webhook_signature()`, `parse_inbound_webhook()`. **No brand/campaign methods** — C-B9 adds `create_brand()`, `get_brand()`, `create_campaign()`, `get_campaign()`. |
| Existing code — `TelnyxSmsCarrier` | `telnyx_sms_carrier.py` | Implements ABC. Has `provision_number()` (phone number acquisition via `client.available_phone_numbers.list()` + `client.number_orders.create()`). Lazy SDK import. **No brand/campaign methods.** |
| Existing code — `handle_checkout_session_completed` | `stripe_subscriptions.py` | **Stub** — logs and returns for `a2p_10dlc_setup` purpose. C-B9 implements the full handler. |
| Existing code — `messaging_quote.py` route | `api/routes/messaging_quote.py` | C-B8's `GET /messaging/quote` + `/test` twin. Reads entity_type from `tenant_messaging_registration`, calls `get_carrier_quote()`. |
| Existing code — `tenant_10dlc_profile.py` route | `api/routes/tenant_10dlc_profile.py` | DLC-1 CRUD: `GET/PUT /settings/10dlc-profile` + `/test` twins. `settings.view` / `settings.manage` RBAC. |
| Existing code — `dlc.py` schemas | `api/schemas/dlc.py` | `Tenant10DlcProfileRequest/Response` + `CarrierQuoteLineItem/Response`. C-B9 extends the profile schemas + adds provisioning schemas. |
| mvp-arch §17 | `mvp-arch.md` §17 | SMS infrastructure: carrier adapter pattern (§17.1), A2P 10DLC compliance (§17.2), number provisioning (§17.3), inbound routing (§17.4). §16 patterns: carrier-agnostic adapter (§17.1), lazy provisioning (§17.3), optimistic UI with pending badges (§16.6), always-preview-before-send (§16.7). |

---

## B. Migration Plan

### B.1 — DB Changes

**One migration** — adds 3 nullable columns to `tenant_10dlc_profile`:

```sql
ALTER TABLE tenant_10dlc_profile
  ADD COLUMN website      TEXT,
  ADD COLUMN stock_symbol TEXT,
  ADD COLUMN vertical     TEXT;
```

These are the 3 fields identified by C-B8's Telnyx API research as missing from the existing profile table. All nullable because:
- `website` — required by TCR for brand registration, but may be auto-populated from C-SPIKE-2's compliance page if Tom approves
- `stock_symbol` — only for publicly traded companies (rare for electrician ICP)
- `vertical` — business category/use case (e.g., "ELECTRICIAN", "CONTRACTOR")

**No new table.** Campaign registration fields (use_case, sample_message, opt_in_keywords, etc.) are **templated in the service layer** — they are standard across all Pilot tenants and do not vary per-tenant. The tenant does not craft their own opt-in keywords; Pilot provides standard ones. Only `campaign_name` is tenant-specific (derived from `tenant.name`).

**No changes to `tenant_messaging_registration`** — the C-B2 table already has all columns needed for the state machine (status, telnyx_brand_id, telnyx_campaign_id, telnyx_phone_number, quoted_*, stripe_*, otp_*).

### B.2 — MCP Verification Queries (pre-migration)

```sql
-- Verify current tenant_10dlc_profile columns (confirm website/stock_symbol/vertical don't exist)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_10dlc_profile'
ORDER BY ordinal_position;

-- Verify tenant_messaging_registration columns (confirm all state machine fields exist)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_messaging_registration'
ORDER BY ordinal_position;

-- Verify tenant has stripe_customer_id column
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant'
  AND column_name = 'stripe_customer_id';
```

### B.3 — Pre-Migration State

- `tenant_10dlc_profile`: 16 columns (no website/stock_symbol/vertical)
- `tenant_messaging_registration`: 18 columns (all state machine fields present from C-B2)
- No existing rows in either table for test tenants (10DLC not yet provisioned)

### B.4 — 3-Part NOT NULL Pattern

Not applicable — all 3 new columns are intentionally nullable. `website` will be required at the application layer when the tenant submits the provisioning form (validated in the API endpoint, not the DB), because the field may be auto-populated from C-SPIKE-2's compliance page in the future.

### B.5 — Audit Columns

No new table created — the existing `tenant_10dlc_profile` already has all 4 audit columns (created_at, updated_at, created_by, updated_by) via `StandardAuditMixin`. The migration only adds 3 data columns.

### B.6 — Temporal Fee Schedule Migration (carrier_fee_schedule)

**✅ Tom decision 2026-08-05**: Adopt the temporal design as part of C-B9. Store sub-cent surcharges with millicents precision.

The C-B8 `carrier_fee_schedule` table (8 seed rows, `amount_cents INTEGER`, `is_active BOOLEAN`) is migrated to a **temporal lookup table** with historical price tracking:

```sql
-- 1. Add temporal + millicents columns
ALTER TABLE carrier_fee_schedule
  ADD COLUMN effective_from  TIMESTAMPTZ NOT NULL DEFAULT now(),
  ADD COLUMN effective_to    TIMESTAMPTZ,
  ADD COLUMN amount_millicents BIGINT;

-- 2. Migrate existing data
UPDATE carrier_fee_schedule SET
  amount_millicents = amount_cents * 1000,
  effective_from = created_at,
  effective_to = NULL;

-- 3. Drop old columns
ALTER TABLE carrier_fee_schedule
  DROP COLUMN amount_cents,
  DROP COLUMN is_active;

-- 4. Make amount_millicents NOT NULL
ALTER TABLE carrier_fee_schedule
  ALTER COLUMN amount_millicents SET NOT NULL;

-- 5. Add GiST exclusion constraint (requires btree_gist extension)
CREATE EXTENSION IF NOT EXISTS btree_gist;
ALTER TABLE carrier_fee_schedule
  ADD CONSTRAINT uq_carrier_fee_schedule_temporal
  EXCLUDE USING gist (
    fee_code WITH =,
    entity_type WITH =,
    tstzrange(effective_from, effective_to) WITH &&
  );

-- 6. Drop the old UNIQUE constraint (replaced by GiST exclusion)
ALTER TABLE carrier_fee_schedule
  DROP CONSTRAINT uq_carrier_fee_schedule_code_entity;

-- 7. Seed new fee codes (brand_vetting, campaign_registration_tmobile, phone_number_assignment, surcharges)
INSERT INTO carrier_fee_schedule
  (fee_code, entity_type, amount_millicents, description, effective_from, effective_to, created_at, updated_at)
VALUES
  ('brand_vetting', 'standard', 4000000, 'External brand vetting (optional)', now(), NULL, now(), now()),
  ('brand_vetting', 'sole_proprietor', 4000000, 'External brand vetting (optional)', now(), NULL, now(), now()),
  ('campaign_registration_tmobile', 'standard', 5000000, 'T-Mobile campaign registration (currently waived)', now(), NULL, now(), now()),
  ('campaign_registration_tmobile', 'sole_proprietor', 5000000, 'T-Mobile campaign registration (currently waived)', now(), NULL, now(), now()),
  ('phone_number_assignment', 'standard', 30, 'Phone number to campaign assignment', now(), NULL, now(), now()),
  ('phone_number_assignment', 'sole_proprietor', 30, 'Phone number to campaign assignment', now(), NULL, now(), now()),
  ('surcharge_att', 'standard', 300, 'Per-segment surcharge (AT&T)', now(), NULL, now(), now()),
  ('surcharge_att', 'sole_proprietor', 300, 'Per-segment surcharge (AT&T)', now(), NULL, now(), now()),
  ('surcharge_tmobile', 'standard', 300, 'Per-segment surcharge (T-Mobile)', now(), NULL, now(), now()),
  ('surcharge_tmobile', 'sole_proprietor', 300, 'Per-segment surcharge (T-Mobile)', now(), NULL, now(), now()),
  ('surcharge_verizon', 'standard', 310, 'Per-segment surcharge (Verizon)', now(), NULL, now(), now()),
  ('surcharge_verizon', 'sole_proprietor', 310, 'Per-segment surcharge (Verizon)', now(), NULL, now(), now())
ON CONFLICT DO NOTHING;
```

**Millicents convention**: 1 millicent = 1/1000 of a cent = $0.00001. Examples:
- $4.00 = 400,000 millicents
- $0.003/segment = 300 millicents
- $0.0031/segment = 310 millicents
- $0.05/segment (overage rate) = 5,000 millicents

**Code changes required**:
- `CarrierFeeSchedule` SQLModel: replace `amount_cents` with `amount_millicents`, add `effective_from`/`effective_to` fields, remove `is_active`
- `get_carrier_quote()` in `telnyx_quoting.py`: query `WHERE effective_to IS NULL` instead of `WHERE is_active = true`, return `amount_millicents`
- `CarrierQuoteLineItem` schema: change `amount_cents: int` to `amount_millicents: int`
- `CarrierQuoteResponse` schema: change `setup_total_cents`/`recurring_monthly_cents` to `setup_total_millicents`/`recurring_monthly_millicents`
- `seed_platform.py`: update carrier_fee_schedule seed block to use `amount_millicents` + `effective_from`/`effective_to`
- C-B8 tests: update assertions from `amount_cents` to `amount_millicents`

**MCP verification query to add to B.2**:
```sql
-- Verify current carrier_fee_schedule columns (confirm amount_cents/is_active exist, amount_millicents/effective_from/effective_to don't)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'carrier_fee_schedule'
ORDER BY ordinal_position;
```

### B.7 — Seed Data Rollout

**⚠️ MANDATORY (Tom, 2026-08-06)**: This batch adds data to the DB — the seed system MUST be updated to produce realistic data for all new fields. See `python-engr-std-prompt-inclusions.md` §20 for the full template.

**Layer 1 — Core/Platform (`seed_platform.py`)**:
- `carrier_fee_schedule`: update seed block to use `amount_millicents` + `effective_from`/`effective_to` for all 20 rows (8 original migrated + 12 new fee codes). Must match migration seed rows exactly. Idempotent (`ON CONFLICT DO NOTHING`).

**Layer 2 — Scenario (`seed_scenario_*.py`)**:
- `tenant_10dlc_profile`: if any scenario scripts create profile rows, populate the 3 new columns (`website`, `stock_symbol`, `vertical`) with realistic, varied values. If no scenario scripts create profile rows, this layer is N/A.

**Verification**: `seed_platform.py --mode inspect` + `pytest -m unit` after seed change.
**README update**: update `backend/README-seed-data.md` §4 (Current Seed State).

---

## C. Execution Order

| Step | Task | Files |
|---|---|---|
| 1 | Alembic migration: add `website`, `stock_symbol`, `vertical` to `tenant_10dlc_profile` | `migrations/versions/{ts}_c_b9_add_brand_fields.py` |
| 1a | Alembic migration: temporal `carrier_fee_schedule` — add `effective_from`/`effective_to`/`amount_millicents`, migrate existing rows, drop `amount_cents`/`is_active`, add GiST exclusion, seed 12 new fee codes (surcharges + brand_vetting + tmobile + phone_assignment) | `migrations/versions/{ts}_c_b9_temporal_fee_schedule.py` |
| 1b | Update `CarrierFeeSchedule` SQLModel — replace `amount_cents` with `amount_millicents`, add `effective_from`/`effective_to`, remove `is_active` | `app/models/billing.py` |
| 1c | Update `get_carrier_quote()` in `telnyx_quoting.py` — query `WHERE effective_to IS NULL`, return `amount_millicents` | `services/telnyx_quoting.py` |
| 1d | Update `CarrierQuoteLineItem` + `CarrierQuoteResponse` schemas — `amount_cents` → `amount_millicents`, `setup_total_cents` → `setup_total_millicents`, `recurring_monthly_cents` → `recurring_monthly_millicents` | `api/schemas/dlc.py` |
| 1e | Update `seed_platform.py` carrier_fee_schedule block — use `amount_millicents` + `effective_from`/`effective_to` | `migrations/scripts/seed_platform.py` |
| 1f | Update C-B8 tests — assertions from `amount_cents` to `amount_millicents` | `tests/domains/subscriptions_usage/test_cb8_carrier_quote.py` |
| 2 | Update `Tenant10DlcProfile` SQLModel with 3 new fields | `app/models/core.py` |
| 3 | Extend `Tenant10DlcProfileRequest/Response` schemas with new fields | `api/schemas/dlc.py` |
| 4 | Update `tenant_10dlc_profile.py` route `_upsert_10dlc_profile_impl` to persist new fields | `api/routes/tenant_10dlc_profile.py` |
| 5 | Add `create_brand()`, `get_brand()`, `create_campaign()`, `get_campaign()`, `get_verticals()`, `list_available_numbers()`, `assign_number_to_campaign()` to `SmsCarrier` ABC | `services/sms_carrier.py` |
| 6 | Implement brand/campaign/verticals/numbers methods in `TelnyxSmsCarrier` (lazy SDK import, `POST /brand`, `GET /brand/{id}`, `POST /campaign`, `GET /campaign/{id}`, `GET /enum/vertical`, `GET /v2/available_phone_numbers`, `POST /phone_number_campaign`) | `services/telnyx_sms_carrier.py` |
| 7 | Implement mock brand/campaign/verticals/numbers methods in `MockSmsCarrier` (deterministic test responses) | `services/sms_carrier.py` |
| 8 | Create `services/messaging_provisioning.py` — state machine service with `transition_status()`, `initiate_provisioning()`, `submit_otp()`, `get_provisioning_status()`, `poll_brand_status()`, `poll_campaign_status()`, `assign_phone_number()` (transitions `awaiting_number_selection` → `number_assigned` → `active`) | `services/messaging_provisioning.py` (new) |
| 9 | Create `services/messaging_checkout.py` — `create_10dlc_checkout_session()` (Stripe Checkout with `setup_future_usage: off_session`, inline `price_data`) | `services/messaging_checkout.py` (new) |
| 10 | Implement `handle_checkout_session_completed()` for `a2p_10dlc_setup` purpose — attach PM, transition to `brand_submitted`, enqueue Celery provisioning task | `services/stripe_subscriptions.py` |
| 11 | Create `api/routes/messaging_provisioning.py` — 8 endpoints + `/test` twins (provision, checkout, otp, status, retry, verticals, available-numbers, assign-number) | `api/routes/messaging_provisioning.py` (new) |
| 12 | Add provisioning schemas to `api/schemas/dlc.py` (including `AvailablePhoneNumber`, `AssignNumberRequest`, `VerticalsResponse`) | `api/schemas/dlc.py` |
| 13 | Register router in `app/main.py` | `app/main.py` |
| 14 | Create Celery tasks: `provision_brand` (post-checkout → create brand → poll), `provision_campaign` (post-brand-verified → create campaign → poll → transition to `awaiting_number_selection`), `check_otp_timeout` (T+18h alert) | `tasks/messaging_provisioning.py` (new) |
| 15 | Register Celery beat schedule for `check_otp_timeout` (hourly) | `core/celery_app.py` or equivalent |
| 16 | Write unit tests (domain: `subscriptions_usage`) | `tests/domains/subscriptions_usage/test_cb9_messaging_provisioning.py` (new) |
| 17 | Regenerate `openapi.json` + `openapi_schema_map.md` + `db_models_map.md` | per standard process |

---

## D. New API Endpoints

All endpoints are tenant-scoped under `/api/v1/tenants/{tenant_id}/messaging/`. RBAC: `settings.manage` for mutations, `settings.view` for reads. Each has a `/test` twin using `get_test_context()`.

### D.1 — `POST /api/v1/tenants/{tenant_id}/messaging/provision`

Initiates or restarts 10DLC provisioning. Creates/updates `tenant_messaging_registration` row with `entity_type` and `status = 'quoting'`. Upserts `tenant_10dlc_profile` with brand data (including new `website`, `stock_symbol`, `vertical` fields). Fetches quote from `carrier_fee_schedule` (C-B8) and stores `quoted_setup_cents` / `quoted_monthly_cents` on the registration row.

**Auth**: `settings.manage` (owner-only)
**Idempotency**: `Idempotency-Key` header supported (24h TTL)

**Request**:
```json
{
  "entity_type": "standard",
  "legal_business_name": "Acme Electric LLC",
  "dba_name": "Acme Electric",
  "ein": "123456789",
  "hq_address_line1": "123 Main St",
  "hq_address_line2": null,
  "hq_city": "Wilmington",
  "hq_state": "DE",
  "hq_postal_code": "19801",
  "hq_country": "US",
  "support_email": "owner@acmeelectric.example.com",
  "support_phone": "+13025551234",
  "website": "https://acmeelectric.example.com",
  "stock_symbol": null,
  "vertical": "ELECTRICIAN"
}
```

**Response** (200):
```json
{
  "registration_id": "uuid",
  "status": "quoting",
  "entity_type": "standard",
  "quote": {
    "entity_type": "standard",
    "setup_total_cents": 2000,
    "recurring_monthly_cents": 533,
    "setup_items": [...],
    "recurring_items": [...]
  }
}
```

**Error codes**:
- 409 — registration already in a non-retryable state (e.g., `active`, `brand_submitted`)
- 422 — validation error (missing required brand fields for the given entity_type)
- 404 — tenant not found

### D.2 — `POST /api/v1/tenants/{tenant_id}/messaging/checkout`

Creates a Stripe Checkout Session for the one-time 10DLC setup charge. Reads the stored quote from the registration row. Transitions status to `awaiting_payment`. Returns the Checkout URL for client-side redirect.

**Auth**: `settings.manage`
**Idempotency**: `Idempotency-Key` header supported

**Request**: empty body (quote is read from registration row)

**Response** (200):
```json
{
  "checkout_url": "https://checkout.stripe.com/c/cs_...",
  "checkout_session_id": "cs_..."
}
```

**Error codes**:
- 409 — status is not `quoting` (must provision first)
- 422 — `quoted_setup_cents` is null (quote not fetched)
- 500 — Stripe API error (logged, RFC 7807)

### D.3 — `POST /api/v1/tenants/{tenant_id}/messaging/otp`

Submits the sole-proprietor OTP code. Only valid when status is `awaiting_otp`. Relays the OTP to Telnyx (per Q#2: SMS-delivered, not email — verify procedure against Telnyx help center before building). On success, transitions to `brand_verified` and enqueues campaign provisioning.

**Auth**: `settings.manage`

**Request**:
```json
{
  "otp_code": "123456"
}
```

**Response** (200):
```json
{
  "status": "brand_verified"
}
```

**Error codes**:
- 409 — status is not `awaiting_otp`
- 422 — OTP code format invalid
- 400 — OTP rejected by Telnyx (RFC 7807 with `failure_reason`)

### D.4 — `GET /api/v1/tenants/{tenant_id}/messaging/status`

Returns the current provisioning state. Used by the frontend to render the state machine progress and determine which UI panel to show (entity type form, quote, checkout, OTP entry, success, error).

**Auth**: `settings.view`

**Response** (200):
```json
{
  "registration_id": "uuid",
  "status": "awaiting_otp",
  "entity_type": "sole_proprietor",
  "telnyx_brand_id": "brand_abc123",
  "telnyx_campaign_id": null,
  "telnyx_phone_number": null,
  "quoted_setup_cents": 1500,
  "quoted_monthly_cents": 367,
  "otp_requested_at": "2026-08-05T14:00:00Z",
  "failure_reason": null,
  "updated_at": "2026-08-05T14:00:00Z"
}
```

**Error codes**:
- 404 — no registration row exists (tenant hasn't started provisioning)

### D.5 — `POST /api/v1/tenants/{tenant_id}/messaging/retry`

Retries from `payment_failed` back to `quoting`. Does NOT re-charge — the previous payment failed, so no refund is needed. Re-fetches the quote (in case carrier fees changed).

**Auth**: `settings.manage`

**Request**: empty body

**Response** (200):
```json
{
  "status": "quoting",
  "quote": { ... }
}
```

**Error codes**:
- 409 — status is not `payment_failed` (retry only valid from this state)

### D.6 — `GET /api/v1/tenants/{tenant_id}/messaging/verticals`

Returns the list of valid business verticals from the carrier's 10DLC API. Proxies Telnyx `/enum/vertical` through the carrier-agnostic `SmsCarrier` ABC — the frontend never calls Telnyx directly (adapter pattern per mvp-arch §17.1). Used to populate the `vertical` dropdown in the brand registration form.

**Auth**: `settings.view`

**Response** (200):
```json
{
  "verticals": ["ENERGY", "TECHNOLOGY", "FINANCE", "HEALTHCARE", "RETAIL", ...]
}
```

**Caching**: The frontend caches this for 1 hour (`staleTime: 3600000`) — verticals rarely change.

### D.7 — `GET /api/v1/tenants/{tenant_id}/messaging/available-numbers`

Returns available phone numbers for a given area code from the carrier. Proxies Telnyx `GET /v2/available_phone_numbers` through the `SmsCarrier` ABC. Used by the `PhoneNumberSelector` component when the tenant picks their number (state `awaiting_number_selection`).

**Auth**: `settings.view`

**Query params**:
- `area_code` (required, string) — 3-digit US area code
- `limit` (optional, int, default 10) — max results

**Response** (200):
```json
{
  "numbers": [
    {
      "phone_number": "+13025551234",
      "locality": "Wilmington",
      "region": "DE",
      "monthly_cost_millicents": 100000
    }
  ]
}
```

**Error codes**:
- 422 — invalid area code format
- 502 — carrier API error (logged, RFC 7807)

### D.8 — `POST /api/v1/tenants/{tenant_id}/messaging/assign-number`

Provisions the selected phone number via the carrier and transitions the registration to `number_assigned` → `active`. Called by the `PhoneNumberSelector` component when the tenant confirms their number selection.

**Auth**: `settings.manage`
**Idempotency**: `Idempotency-Key` header supported

**Request**:
```json
{
  "phone_number": "+13025551234"
}
```

**Response** (200):
```json
{
  "status": "active",
  "telnyx_phone_number": "+13025551234"
}
```

**Error codes**:
- 409 — status is not `awaiting_number_selection`
- 422 — phone number not in the available list (must select from `GET /available-numbers` results)
- 502 — carrier provisioning error (RFC 7807)

---

## E. Pattern Reuse Decisions

| Pattern | Source | How C-B9 uses it |
|---|---|---|
| **Carrier-agnostic adapter layer** | mvp-arch §17.1 | New `create_brand()`, `get_brand()`, `create_campaign()`, `get_campaign()`, `get_verticals()`, `list_available_numbers()`, `assign_number_to_campaign()` methods go on the `SmsCarrier` ABC. `TelnyxSmsCarrier` implements them; `MockSmsCarrier` provides test doubles. No route or service imports the Telnyx SDK directly. The frontend never calls Telnyx directly — all carrier interactions go through the ABC. |
| **Lazy provisioning at first use** | mvp-arch §17.3 | 10DLC provisioning is triggered when the tenant clicks "Set up text messaging" in the post-wizard checklist — not at signup. The `tenant_messaging_registration` row is created on first provisioning request. |
| **Always-preview-before-send** | mvp-arch §16.7 | The itemized quote (from C-B8) is displayed to the tenant **before** the Stripe Checkout redirect. The tenant sees each line item (brand registration, campaign registration, phone number) with costs before paying. |
| **Optimistic UI with pending badges** | mvp-arch §16.6 | The state machine has multiple async steps (brand creation, campaign creation, number assignment). The frontend polls `GET /messaging/status` and shows pending indicators for in-flight transitions. |
| **Idempotency-Key on POST/PATCH** | infra constraints §5 | `POST /messaging/provision` and `POST /messaging/checkout` support `Idempotency-Key` headers (24h TTL) to prevent duplicate provisioning or duplicate Checkout sessions. |
| **RFC 7807 error format** | existing pattern | All error responses use the existing RFC 7807 `ProblemDetails` format with `status`, `detail`, and domain-specific fields. |

---

## F. Shared Module Interfaces

### F.1 — `services/messaging_provisioning.py` (new)

```python
# State machine constants
MESSAGING_STATES = [
    "not_started", "quoting", "awaiting_payment", "payment_failed",
    "brand_submitted", "awaiting_otp", "brand_verified", "brand_rejected",
    "campaign_submitted", "awaiting_number_selection", "campaign_rejected",
    "number_assigned", "active", "suspended",
]

VALID_TRANSITIONS: dict[str, list[str]] = {
    "not_started":              ["quoting"],
    "quoting":                  ["awaiting_payment"],
    "awaiting_payment":         ["payment_failed", "brand_submitted"],
    "payment_failed":           ["quoting"],
    "brand_submitted":          ["awaiting_otp", "brand_verified", "brand_rejected"],
    "awaiting_otp":             ["brand_verified", "quoting"],  # quoting = OTP timeout
    "brand_verified":           ["campaign_submitted"],
    "campaign_submitted":       ["awaiting_number_selection", "campaign_rejected"],
    "awaiting_number_selection": ["number_assigned"],  # tenant picks number → assign
    "number_assigned":          ["active"],
    "active":                   ["suspended"],
    # Terminal: brand_rejected, campaign_rejected, suspended
}

def transition_status(
    db: Session,
    registration: TenantMessagingRegistration,
    new_status: str,
    *,
    failure_reason: str | None = None,
    user_id: uuid.UUID | None = None,
) -> TenantMessagingRegistration:
    """Validate + persist a state transition. Raises ValueError on invalid transition."""

def initiate_provisioning(
    db: Session,
    tenant_id: uuid.UUID,
    entity_type: str,
    profile_data: dict,
    user_id: uuid.UUID,
) -> tuple[TenantMessagingRegistration, dict]:
    """Creates/updates registration + profile, fetches quote, returns (registration, quote)."""

def submit_otp(
    db: Session,
    tenant_id: uuid.UUID,
    otp_code: str,
) -> str:
    """Relays OTP to Telnyx, transitions to brand_verified on success. Returns new status."""

def get_provisioning_status(
    db: Session,
    tenant_id: uuid.UUID,
) -> dict:
    """Returns the current registration state as a dict for the API response."""

def poll_brand_status(
    db: Session,
    registration_id: uuid.UUID,
) -> None:
    """Celery task: polls Telnyx brand status, transitions on verification/rejection."""

def poll_campaign_status(
    db: Session,
    registration_id: uuid.UUID,
) -> None:
    """Celery task: polls Telnyx campaign status, transitions on approval/rejection."""

def provision_phone_number(
    db: Session,
    registration_id: uuid.UUID,
) -> None:
    """Provisions phone number via carrier, transitions to active."""
```

### F.2 — `services/messaging_checkout.py` (new)

```python
def create_10dlc_checkout_session(
    db: Session,
    tenant_id: uuid.UUID,
    registration: TenantMessagingRegistration,
) -> str:
    """
    Creates a Stripe Checkout Session for the one-time 10DLC setup charge.
    Uses mode="payment", setup_future_usage="off_session", inline price_data.
    Stores stripe_checkout_id on the registration row.
    Returns the checkout URL.
    """
```

### F.3 — `SmsCarrier` ABC additions (`services/sms_carrier.py`)

```python
@dataclass
class BrandResult:
    brand_id: str
    status: str  # "pending" | "verified" | "rejected"
    rejection_reason: str | None

@dataclass
class CampaignResult:
    campaign_id: str
    status: str  # "pending" | "approved" | "rejected"
    rejection_reason: str | None

class SmsCarrier(ABC):
    # ... existing methods ...

    @abstractmethod
    def create_brand(self, brand_data: dict) -> BrandResult:
        """Submit brand registration to the carrier's 10DLC API."""

    @abstractmethod
    def get_brand(self, brand_id: str) -> BrandResult:
        """Poll brand registration status."""

    @abstractmethod
    def create_campaign(self, brand_id: str, campaign_data: dict) -> CampaignResult:
        """Submit campaign registration to the carrier's 10DLC API."""

    @abstractmethod
    def get_campaign(self, campaign_id: str) -> CampaignResult:
        """Poll campaign registration status."""

    @abstractmethod
    def get_verticals(self) -> list[str]:
        """Return valid business verticals from the carrier's 10DLC API (GET /enum/vertical)."""

    @abstractmethod
    def list_available_numbers(self, area_code: str, limit: int = 10) -> list[dict]:
        """Return available phone numbers for an area code (GET /v2/available_phone_numbers).
        Each dict: {phone_number, locality, region, monthly_cost_millicents}."""

    @abstractmethod
    def assign_number_to_campaign(self, phone_number: str, campaign_id: str) -> str:
        """Provision + assign a phone number to a campaign. Returns the assigned phone_number."""
```

### F.4 — `TelnyxSmsCarrier` additions (`services/telnyx_sms_carrier.py`)

```python
def create_brand(self, brand_data: dict) -> BrandResult:
    """POST /v2/10dlc/brands — lazy SDK import."""

def get_brand(self, brand_id: str) -> BrandResult:
    """GET /v2/10dlc/brands/{brand_id} — poll status."""

def create_campaign(self, brand_id: str, campaign_data: dict) -> CampaignResult:
    """POST /v2/10dlc/campaigns — campaign registration."""

def get_campaign(self, campaign_id: str) -> CampaignResult:
    """GET /v2/10dlc/campaigns/{campaign_id} — poll status."""

def get_verticals(self) -> list[str]:
    """GET /10dlc/enum/vertical — returns valid business verticals."""

def list_available_numbers(self, area_code: str, limit: int = 10) -> list[dict]:
    """GET /v2/available_phone_numbers — returns available numbers for area_code.
    Maps Telnyx response to {phone_number, locality, region, monthly_cost_millicents}."""

def assign_number_to_campaign(self, phone_number: str, campaign_id: str) -> str:
    """POST /10dlc/phone_number_campaign — assigns number to campaign ($0.03).
    Returns the assigned phone_number."""
```

### F.5 — Campaign template (in `services/messaging_provisioning.py`)

Campaign fields are **templated** — standard across all Pilot tenants:

```python
def _build_campaign_payload(tenant_name: str, entity_type: str) -> dict:
    """Builds the Telnyx campaign registration payload from tenant data + templates."""
    use_case = "SOLE_PROPRIETOR" if entity_type == "sole_proprietor" else "MIXED"
    return {
        "campaign_name": f"{tenant_name} — Customer Messaging",
        "use_case": use_case,
        "description": f"Customer care and appointment notifications for {tenant_name}.",
        "sample_message_1": "Hi, this is {tenant_name} confirming your appointment tomorrow between 8-10 AM. Reply STOP to opt out.",
        "sample_message_2": "Your invoice from {tenant_name} is ready. View it here: [link]",
        "message_flow": "Customer opts in by providing their phone number for appointment notifications and billing communications.",
        "opt_in_keywords": ["START", "YES"],
        "opt_out_keywords": ["STOP", "CANCEL", "UNSUBSCRIBE"],
        "help_keywords": ["HELP"],
        "opt_in_message": "You're subscribed to {tenant_name} messages. Reply STOP to opt out, HELP for help.",
        "opt_out_message": "You've been unsubscribed from {tenant_name} messages. Reply START to resubscribe.",
        "help_message": "{tenant_name}: Reply STOP to opt out. Msg rates may apply.",
        "sub_use_cases": None,
    }
```

### F.6 — `handle_checkout_session_completed` (updated in `stripe_subscriptions.py`)

```python
def handle_checkout_session_completed(db: Session, stripe_event: dict) -> None:
    """checkout.session.completed — 10DLC setup charge handler (C-B9).

    If metadata.purpose == 'a2p_10dlc_setup':
      1. Attach PM as customer.invoice_settings.default_payment_method
      2. Transition registration to 'brand_submitted'
      3. Enqueue Celery task: provision_brand(registration_id)
    """
```

### F.7 — Celery tasks (`tasks/messaging_provisioning.py`, new)

```python
@celery_app.task(name="provision_brand")
def provision_brand_task(registration_id: str) -> None:
    """Post-checkout: create Telnyx brand, poll for verification/rejection."""

@celery_app.task(name="provision_campaign")
def provision_campaign_task(registration_id: str) -> None:
    """Post-brand-verified: create Telnyx campaign, poll for approval/rejection."""

@celery_app.task(name="check_otp_timeout")
def check_otp_timeout_task() -> None:
    """Hourly: find registrations in 'awaiting_otp' > 18h, alert Tom.
    At > 24h, transition back to 'quoting' (no re-charge)."""
```

**Celery beat schedule**:
```python
"check-otp-timeout": {
    "task": "check_otp_timeout",
    "schedule": crontab(minute=0),  # hourly
}
```

---

## G. Open Questions Resolved

| # | Question | Resolution | Source |
|---|---|---|---|
| 1 | Where to store brand registration input fields — on `tenant_messaging_registration` or a companion table? | **Add to `tenant_10dlc_profile`** (3 new columns: `website`, `stock_symbol`, `vertical`). The profile table already stores brand data (legal_business_name, ein, address, etc.) and is the natural home. `tenant_messaging_registration` remains the state machine table only. | Design decision — avoids table proliferation, reuses existing DLC-1 table |
| 2 | Where to store campaign registration fields (use_case, sample_message, opt_in_keywords, etc.)? | **Templated in the service layer** — not stored per-tenant. Campaign fields are standard across all Pilot tenants. Only `campaign_name` is tenant-specific (derived from `tenant.name`). This avoids adding 12+ columns to any table. | Design decision — campaign data is template-driven, not tenant-specific |
| 3 | How does the OTP loop work per Q#2 resolution? | **OTP is SMS-delivered** to the brand's mobile phone number (not email, per Q#2). The spec §5.3 "email to Telnyx desk" description is incorrect. The in-app PIN panel is still correct. **⚠️ The full request/relay procedure must be verified against the Telnyx live help center before building** — Tom must confirm how the PIN request is initiated and how the tenant relays it back. | Q#2 resolution + spec §5.3 caveat |
| 4 | Should C-SPIKE-2's compliance page be part of C-B9 or a separate batch? | **Separate batch (C-B9a, if approved).** C-B9 adds a `website` field to `tenant_10dlc_profile` that accepts any URL. If Tom approves C-SPIKE-2's compliance page, a future C-B9a batch auto-populates this field with the Pilot-hosted compliance page URL. C-B9 is not blocked by this decision. | Design decision — decouples C-B9 from the unresolved C-SPIKE-2 questions |
| 5 | How are refunds handled on `brand_rejected` / `campaign_rejected`? | **Automatic Stripe refund** of the unconsumed portion. `brand_rejected` → full refund (brand fee consumed, campaign + number not). `campaign_rejected` → partial refund (brand + campaign fee consumed, number not). Refund via `stripe.Refund.create(payment_intent=...)`. Operator alert via notification pipeline. | Spec §5.2 |
| 6 | How is the OTP timeout handled? | **Celery beat task (hourly)** checks for registrations in `awaiting_otp` > 18h → alerts Tom. At > 24h → transitions back to `quoting` **without re-charging** (the $4 brand fee is consumed but re-registration under the same Stripe payment is the correct customer treatment). | Spec §5.3 |

### Open Questions for Tom — Resolved (2026-08-05)

| # | Question | Resolution | Impact on C-B9 |
|---|---|---|---|
| T1 | **Verify sole-prop OTP procedure against Telnyx live help center** | **✅ Tom provided the full Telnyx 10DLC API JSON** (`telnyx-10dlc-api.json`, removed from the public snapshot) + developer docs reference (https://developers.telnyx.com/docs/messaging/10dlc/quickstart). OTP procedure documented in `10dlc-registration-automation-requirements.md` §3.7. **⚠️ Still needs**: the exact OTP submission API endpoint is not in the 10DLC API JSON — the OTP flow may be handled outside the 10DLC API (via Telnyx support desk or a separate API). Must verify against Telnyx live help center before building the OTP submission endpoint. | Design is unblocked — the in-app PIN panel + 24h window + T+18h alert are confirmed. The OTP submission endpoint implementation may need adjustment once the exact Telnyx procedure is confirmed. |
| T2 | **C-SPIKE-2 compliance page decision** | **✅ Tom confirmed YES** — Pilot will host compliance pages for customers, at their choice, for a cost. The C-SPIKE-2 batch will resolve the full design (domain, generic vs white-labeled, pricing). | Does NOT block C-B9. C-B9's `website` field accepts any URL. C-SPIKE-2 (now a full batch, not just a spike) will build the compliance page hosting + auto-populate the `website` field. |
| T3 | **Confirm `vertical` values** | **✅ Tom confirmed** the enum endpoints are in the Telnyx API JSON. `/enum/vertical` returns all valid verticals. All 14 enum endpoints are documented with curl commands in `10dlc-registration-automation-requirements.md` §3.5. | C-B9 form design: the `vertical` dropdown should be populated by calling `/enum/vertical` at build time (or caching the results). Do not hardcode vertical values. |

### Additional Design Updates from Tom's Feedback (2026-08-05)

**EntityType mapping**: The Telnyx API uses different enum values than the Pilot spec:

| Pilot `entity_type` | Telnyx `entityType` | Description |
|---|---|---|
| `standard` | `PRIVATE_PROFIT` | Has an EIN — standard brand registration path |
| `sole_proprietor` | `INDIVIDUAL` | No EIN — sole proprietor path with OTP verification |

The `TelnyxSmsCarrier.create_brand()` method must map `entity_type` → `entityType` before calling the Telnyx API.

**Brand schema required fields** (from Telnyx API JSON): `entityType`, `displayName`, `country`, `email`, `brandRelationship`, `vertical`. The `tenant_10dlc_profile` table already stores most of these. C-B9 must also collect `brandRelationship` (default: `SMALL_ACCOUNT` for Pilot tenants) — this is a new field not in the current profile table or the 3-column migration. **Design decision**: add `brand_relationship` as a 4th column to the migration, or default it in the service layer. **Recommendation**: default to `SMALL_ACCOUNT` in the service layer (all Pilot tenants are small accounts) — no new column needed.

**Temporal fee schedule**: ✅ **Tom decision 2026-08-05** — adopt the temporal design as part of C-B9 (not a separate batch). Store sub-cent per-message surcharges with millicents precision (`amount_millicents BIGINT`, 1 millicent = $0.00001) so the DB can be used to compare carrier surcharge rates against Pilot's $0.05/segment overage rate and calculate margins when carriers increase fees. See `10dlc-registration-automation-requirements.md` §4 for the full design. Migration plan in §B.6, execution steps 1a–1f in §C.

### UI Design Spec Handoff Gate Items (resolved 2026-08-06)

The UI design spec (`batch-c-b9-ui-design-spec.md` §14 Handoff Gate) identified 3 follow-up tasks for the Architect. All 3 are now resolved in this design doc:

| # | Handoff item | Resolution | Where in this doc |
|---|---|---|---|
| 3 | **Verticals endpoint** — `GET /messaging/verticals` not in §D | ✅ Added as §D.6. Proxies Telnyx `/enum/vertical` through `SmsCarrier.get_verticals()` ABC method (§F.3). Frontend caches 1h. | §D.6, §F.3, §F.4, §C step 5-7 |
| 4 | **OTP timeout confirmation** — confirm `otp_requested_at` in status response + 24h hard timeout | ✅ Confirmed: `otp_requested_at` is in the `GET /messaging/status` response (§D.4). 24h is the hard timeout per spec §5.3 — Celery beat task alerts Tom at T+18h, transitions to `quoting` at T+24h without re-charge (§F.1, §F.7). **⚠️ Still needs**: exact OTP submission API endpoint verification against Telnyx help center (the 10DLC API JSON does not contain an explicit OTP endpoint). | §D.4, §F.1, §F.7, §G Q#6 |
| 5 | **Phone number selection** — `awaiting_number_selection` state + `GET /available-numbers` + `POST /assign-number` | ✅ Added: new state `awaiting_number_selection` in state machine (§F.1, between `campaign_submitted` and `number_assigned`). Two new endpoints: `GET /messaging/available-numbers` (§D.7) and `POST /messaging/assign-number` (§D.8). Three new carrier methods: `list_available_numbers()`, `assign_number_to_campaign()` (§F.3, §F.4). | §D.7, §D.8, §F.1, §F.3, §F.4, §C steps 5-7, 11-12, 14 |

---

## H. Surface Mockup Reference (Frontend)

### H.1 — Design Spec — ✅ Approved

The UI design spec has been authored by the `pilot-web-ui-designer` mode and **Tom-approved** (2026-08-06).

**Design spec**: `batch-c-b9-ui-design-spec.md` — 14 sections covering all 10 components, 8 hooks, state-driven panel switching, accessibility notes, and token usage.

**Handoff Gate items resolved** (see §G "UI Design Spec Handoff Gate Items" for details):
- ✅ Task 3: `GET /messaging/verticals` endpoint added (§D.6)
- ✅ Task 4: `otp_requested_at` confirmed in status response + 24h timeout (§D.4, §F.7)
- ✅ Task 5: `awaiting_number_selection` state + `GET /available-numbers` + `POST /assign-number` added (§D.7, §D.8, §F.1)

### H.2 — Platform Scope

**Web dashboard only** (`apps/web`) — the 10DLC provisioning flow is a Settings page, not a mobile surface. Mobile users are directed to the web dashboard for messaging setup (the post-wizard checklist item links to the web Settings page).

### H.3 — Surfaces to Design

1. **Messaging Setup page** (`/settings/messaging`) — the main provisioning wizard:
   - **Entity type selector**: "Does your business have an EIN?" → Yes (standard) / No (sole_proprietor). Inline help text explaining the difference (automated vs OTP loop, throughput caps).
   - **Brand registration form**: Pre-filled from `tenant_10dlc_profile` (if exists). Fields: legal_business_name, dba_name, ein, address, city, state, postal_code, country, support_email, support_phone, **website** (new), **stock_symbol** (new, conditional — only if publicly traded), **vertical** (new, dropdown).
   - **Quote display**: Itemized costs from C-B8's `GET /messaging/quote` endpoint. Each line item visible (brand registration, campaign registration, phone number). "Passed through at cost — Pilot adds no markup" disclosure. Total setup + recurring monthly.
   - **Checkout button**: "Continue to payment" → redirects to Stripe Checkout. Returns to `/settings/messaging?status=paid` or `?status=cancelled`.
   - **OTP entry panel** (sole prop only): Appears when status is `awaiting_otp`. "The carrier is texting a PIN to {phone}. Enter it here." Input field + submit button. Timeout warning at T+18h.
   - **Status progress indicator**: Visual state machine progress (not_started → quoting → awaiting_payment → brand_submitted → [awaiting_otp] → brand_verified → campaign_submitted → **awaiting_number_selection** → number_assigned → active). Shows current state + pending states.
   - **Error/retry panel**: On `payment_failed` → "Payment failed. Try again?" button. On `brand_rejected` / `campaign_rejected` → error message + "Contact support" CTA.
   - **Phone number selector**: Appears when status is `awaiting_number_selection`. Tenant searches by area code, sees available numbers, selects one, and confirms. Calls `GET /messaging/available-numbers` then `POST /messaging/assign-number`.
   - **Success state**: On `active` → "Text messaging is active. Your number: {phone}." + link to SMS settings.

2. **Post-wizard checklist item** (already added by C-B5): "Set up text messaging" — links to `/settings/messaging`. Cost disclosure inline: "Carrier registration runs about $13–$37 depending on your business setup. That goes to the phone carrier — we don't take any of it."

### H.4 — §16 Pattern Consumption

| Pattern | How the messaging setup page uses it |
|---|---|
| **Always-preview-before-send** (§16.7) | The itemized quote is displayed before the Stripe Checkout redirect — the tenant sees each cost line before paying |
| **Optimistic UI with pending badges** (§16.6) | State machine transitions are async; the UI polls `GET /messaging/status` and shows pending indicators for in-flight transitions (brand_submitted, campaign_submitted) |
| **System-default/tenant-override** (§16.4) | Campaign fields (opt-in keywords, sample messages) are system defaults — the tenant does not customize them. The brand fields are tenant-specific. |

---

## I. Component Manifest (Frontend)

All new components live in `apps/web` unless noted. The React Engineer prompt will reference the approved UI design spec for exact component names, props, and token usage.

| Component | Destination | Purpose |
|---|---|---|
| `MessagingSetupPage` | `apps/web/src/app/(dashboard)/settings/messaging/page.tsx` | Main page — orchestrates the provisioning flow, polls status |
| `EntityTypeSelector` | `apps/web/src/components/settings/messaging/EntityTypeSelector.tsx` | "Does your business have an EIN?" Yes/No selector with help text |
| `BrandRegistrationForm` | `apps/web/src/components/settings/messaging/BrandRegistrationForm.tsx` | Form for brand registration data (existing 10dlc_profile fields + new website/stock_symbol/vertical) |
| `CarrierQuoteDisplay` | `apps/web/src/components/settings/messaging/CarrierQuoteDisplay.tsx` | Itemized cost quote display (reuses C-B8's `CarrierQuoteResponse` type) |
| `CheckoutRedirectButton` | `apps/web/src/components/settings/messaging/CheckoutRedirectButton.tsx` | "Continue to payment" button → calls `POST /messaging/checkout` → redirects to Stripe URL |
| `OtpEntryPanel` | `apps/web/src/components/settings/messaging/OtpEntryPanel.tsx` | Sole-prop OTP entry (appears when status is `awaiting_otp`) |
| `ProvisioningStatusIndicator` | `apps/web/src/components/settings/messaging/ProvisioningStatusIndicator.tsx` | Visual state machine progress indicator |
| `ProvisioningErrorPanel` | `apps/web/src/components/settings/messaging/ProvisioningErrorPanel.tsx` | Error/retry panel for failed states |
| `PhoneNumberSelector` | `apps/web/src/components/settings/messaging/PhoneNumberSelector.tsx` | Phone number search + selection interface (appears at `awaiting_number_selection` status) |

**Hooks** (TanStack Query v5):
| Hook | Purpose |
|---|---|
| `useInitiateProvisioning` | `POST /messaging/provision` mutation |
| `useCreateCheckout` | `POST /messaging/checkout` mutation |
| `useSubmitOtp` | `POST /messaging/otp` mutation |
| `useProvisioningStatus` | `GET /messaging/status` query (with polling for pending states) |
| `useRetryProvisioning` | `POST /messaging/retry` mutation |
| `useCarrierQuote` | `GET /messaging/quote` query (C-B8, reused) |
| `useCarrierVerticals` | `GET /messaging/verticals` query (1h cache — verticals rarely change) |
| `useAvailablePhoneNumbers` | `GET /messaging/available-numbers?area_code=X` query |
| `useAssignPhoneNumber` | `POST /messaging/assign-number` mutation |

**MSW handlers**: All 8 new endpoints + `/test` twins must be registered in `mocks/handlers/index.ts`.

---

## J. Test Requirements

### J.1 — Unit Tests (Python)

Domain: `subscriptions_usage`
Test file: `tests/domains/subscriptions_usage/test_cb9_messaging_provisioning.py`

| Test | Description |
|---|---|
| `test_initiate_provisioning_standard` | Creates registration + profile, fetches quote, status = quoting |
| `test_initiate_provisioning_sole_proprietor` | Same but entity_type = sole_proprietor |
| `test_initiate_provisioning_idempotent` | Same Idempotency-Key returns same result |
| `test_initiate_provisioning_conflict_active` | 409 when status is already active |
| `test_create_checkout_session` | Creates Stripe Checkout mock, status = awaiting_payment |
| `test_checkout_session_completed_handler` | Webhook handler: attaches PM, transitions to brand_submitted, enqueues task |
| `test_submit_otp_success` | OTP submitted, transitions to brand_verified |
| `test_submit_otp_wrong_state` | 409 when status is not awaiting_otp |
| `test_otp_timeout_transition` | > 24h → transitions back to quoting |
| `test_brand_rejected_refund` | Brand rejected → Stripe refund issued, terminal state |
| `test_campaign_rejected_partial_refund` | Campaign rejected → partial refund, terminal state |
| `test_state_transition_invalid` | ValueError on invalid transition (e.g., not_started → active) |
| `test_retry_from_payment_failed` | payment_failed → quoting (re-fetch quote) |
| `test_retry_wrong_state` | 409 when status is not payment_failed |
| `test_get_provisioning_status` | Returns full status dict |
| `test_get_provisioning_status_not_found` | 404 when no registration exists |
| `test_mock_carrier_create_brand` | MockSmsCarrier.create_brand returns deterministic result |
| `test_mock_carrier_create_campaign` | MockSmsCarrier.create_campaign returns deterministic result |
| `test_campaign_payload_template` | _build_campaign_payload produces correct fields |

### J.2 — Telnyx Test Scenarios (from spec §11.2)

These are integration-level scenarios that use `MockSmsCarrier` to simulate Telnyx responses. They should be covered in the unit test suite above using mock carrier responses:

| # | Scenario | Test |
|---|---|---|
| 1 | Standard (EIN) happy path | `test_initiate_provisioning_standard` + checkout + brand_verified + campaign + number_assigned + active |
| 2 | Sole prop happy path | `test_initiate_provisioning_sole_proprietor` + checkout + awaiting_otp + OTP submitted → brand_verified |
| 3 | Sole prop OTP timeout (>24h) | `test_otp_timeout_transition` |
| 4 | Brand rejected | `test_brand_rejected_refund` |
| 5 | Campaign rejected | `test_campaign_rejected_partial_refund` |
| 6 | Checkout abandoned | Status stays `awaiting_payment` (no webhook fires) |
| 7 | Fee schedule change between quote and payment | Quote honored (stored on registration row); delta logged |
| 8 | Month 4 recurring item creation | **C-B10** — not in C-B9 scope |

---

## K. Cost Impact

**No new infrastructure.** C-B9 uses:
- Existing ECS Fargate (FastAPI + Celery)
- Existing RDS PostgreSQL (3 new nullable columns — negligible storage)
- Existing Stripe account (Checkout Sessions — no new Stripe objects)
- Existing Telnyx account (brand/campaign API calls — no new Telnyx numbers until provisioning completes)
- Existing Celery beat (1 new hourly task)

**No monthly cost delta.** C-B9 is pure application code — no new AWS services, no new third-party APIs, no new infrastructure.

---

## L. Dependencies and Handoff

### L.1 — Python Engineer runs first

Part A (Python Engineer) must complete before Part B (React Engineer) starts. The Python Engineer prompt must end with:
1. Run `python export_openapi_json.py` to regenerate OpenAPI spec
2. Commit the changes
3. Notify the React Engineer

### L.2 — React Engineer Pre-Work

The React Engineer prompt must include `pnpm sync-api-types` as the first Pre-Work step to regenerate `packages/shared-types/src/api-schema.d.ts` from the updated OpenAPI spec.

### L.3 — UI Design Spec Gate

The UI design spec must be authored by `pilot-web-ui-designer` and **Tom-approved** before the React Engineer prompt is written. The Architect coordinates this — the design spec is not part of the Python Engineer's work.

### L.4 — Downstream dependency

C-B10 (recurring 10DLC pass-through subscription item) depends on C-B9 ✅. C-B10 cannot start until C-B9 is complete.
