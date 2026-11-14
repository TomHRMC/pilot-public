# Stripe Pricing Configuration — Pilot for Trades

> **⚠️ SUPERSEDED by the bootstrap script (C-B3)**: The manual Dashboard process below is superseded by `stripe_bootstrap.py`. This doc is retained as a historical reference for the pricing model decisions (annual vs monthly, 20% premium). For the current operational process, see `stripe-ops-runbook.md`.

**Version**: 1.2
**Date**: August 18, 2026
**Author**: Pilot Architect
**Status**: Historical reference — superseded by the bootstrap script (C-B3, August 4, 2026)

> **Scope**: Tenant subscription billing only (Pilot charges tenants monthly). This does NOT cover tenant → customer invoice payments (Stripe Connect — separate P2 design decision).

---

## How to Use This Doc

1. Log in to Stripe Dashboard
2. Switch to **Test mode** first — create both products + all prices (monthly + annual)
3. Copy the `price_...` IDs and run the dev DB SQL updates (§5)
4. Switch to **Live mode** — repeat the same product + price creation
5. Copy the live `price_...` IDs and run the prod DB SQL updates (§5)
6. Enter live keys into AWS Secrets Manager `stripe` (§6)

---

## Pricing Model Clarification

Pilot uses **annual billing as the default** with a month-to-month premium for customers who don't want to commit annually.

| Tier | Annual billing (total/year) | Displayed as | Month-to-month rate | DB columns |
|---|---|---|---|---|
| Starter | $588/year | $49/mo on annual toggle | $59/mo | `annual_price_cents` = 58800 · `monthly_price_cents` = 5900 |
| Teams | $1,788/year | $149/mo on annual toggle | $179/mo | `annual_price_cents` = 178800 · `monthly_price_cents` = 17900 |

**The Stripe prices must charge the actual billing amount** — not the marketing display rate:
- `pilot_starter_monthly` Stripe price = **$59.00/mo** (not $49 — that's the annual effective rate shown on the marketing site)
- `pilot_teams_monthly` Stripe price = **$179.00/mo** (not $149)
- `pilot_starter_annual` Stripe price = **$588.00/year** ($49/mo × 12)
- `pilot_teams_annual` Stripe price = **$1,788.00/year** ($149/mo × 12)

> **Note**: Original monthly prices were created at $49/$149. No subscriptions exist, so just update the prices in Stripe Dashboard to $59/$179 directly. No archiving or migration needed.

---

## 1. Product: Pilot Starter

### 1.1 Product Fields

| Field | Value |
|---|---|
| **Name** | `Pilot Starter` |
| **Description** | Field management for solo contractors and small crews — Voice AI, job management, invoicing, QuickBooks sync. 5 schedule lanes, 90 Voice AI min/mo, 100 SMS segments/mo. |
| **Product category** | Software |
| **Statement descriptor** | Live: `PILOT FOR TRADES` · Test: `PILOT FOR TRADES TEST` |
| **Unit label** | *(leave blank)* |
| **Marketing feature list** | *(leave blank — Pilot uses a custom pricing page, not Stripe's embedded widget)* |

### 1.2 Product Metadata

| Key | Value |
|---|---|
| `tier_name` | `starter` |
| `product_plan_code` | `starter_plan` |
| `schedule_lanes` | `5` |
| `voice_ai_min_mo` | `90` |
| `sms_segments_mo` | `100` |

### 1.3 Price Fields (Monthly)

> **Action**: Edit the **existing** `pilot_starter_monthly` price on the **Pilot Starter** product. Change amount from $49 → $59. Price ID stays the same.

| Field | Value |
|---|---|
| **Pricing type** | Recurring |
| **Amount** | `$59.00` |
| **Include tax in price** | No |
| **Billing period** | Monthly |
| **Unit quantity** | `1` |
| **Pricing model** | Flat rate |
| **Price description** | `Pilot Starter — monthly billing ($59/mo, no annual commitment)` |
| **Lookup key** | `pilot_starter_monthly` |

### 1.4 Price Metadata (Monthly)

| Key | Test Mode Value | Live Mode Value |
|---|---|---|
| `tier_name` | `starter` | `starter` |
| `billing_interval` | `monthly` | `monthly` |
| `lookup_key` | `pilot_starter_monthly` | `pilot_starter_monthly` |
| `env` | `test` | `production` |

### 1.5 Price Fields (Annual)

> **Note**: Add this price to the **same Pilot Starter product** — click "Add another price" on the product page.

| Field | Value |
|---|---|
| **Pricing type** | Recurring |
| **Amount** | `$588.00` |
| **Include tax in price** | No |
| **Billing period** | Yearly |
| **Unit quantity** | `1` |
| **Pricing model** | Flat rate |
| **Price description** | `Pilot Starter — annual billing ($49/mo, billed yearly)` |
| **Lookup key** | `pilot_starter_annual` |

### 1.6 Price Metadata (Annual)

| Key | Test Mode Value | Live Mode Value |
|---|---|---|
| `tier_name` | `starter` | `starter` |
| `billing_interval` | `annual` | `annual` |
| `lookup_key` | `pilot_starter_annual` | `pilot_starter_annual` |
| `env` | `test` | `production` |

---

## 2. Product: Pilot Teams

### 2.1 Product Fields

| Field | Value |
|---|---|
| **Name** | `Pilot Teams` |
| **Description** | Full team operations for 6–20 employee shops — all Starter features plus 20 schedule lanes, 300 Voice AI min/mo, 500 SMS segments/mo, recurring jobs, and live dispatcher GPS. |
| **Product category** | Software |
| **Statement descriptor** | Live: `PILOT FOR TRADES` · Test: `PILOT FOR TRADES TEST` |
| **Unit label** | *(leave blank)* |
| **Marketing feature list** | *(leave blank — Pilot uses a custom pricing page, not Stripe's embedded widget)* |

### 2.2 Product Metadata

| Key | Value |
|---|---|
| `tier_name` | `teams` |
| `product_plan_code` | `teams_plan` |
| `schedule_lanes` | `20` |
| `voice_ai_min_mo` | `300` |
| `sms_segments_mo` | `500` |

### 2.3 Price Fields (Monthly)

> **Action**: Edit the **existing** `pilot_teams_monthly` price on the **Pilot Teams** product. Change amount from $149 → $179. Price ID stays the same.

| Field | Value |
|---|---|
| **Pricing type** | Recurring |
| **Amount** | `$179.00` |
| **Include tax in price** | No |
| **Billing period** | Monthly |
| **Unit quantity** | `1` |
| **Pricing model** | Flat rate |
| **Price description** | `Pilot Teams — monthly billing ($179/mo, no annual commitment)` |
| **Lookup key** | `pilot_teams_monthly` |

### 2.4 Price Metadata (Monthly)

| Key | Test Mode Value | Live Mode Value |
|---|---|---|
| `tier_name` | `teams` | `teams` |
| `billing_interval` | `monthly` | `monthly` |
| `lookup_key` | `pilot_teams_monthly` | `pilot_teams_monthly` |
| `env` | `test` | `production` |

### 2.5 Price Fields (Annual)

> **Note**: Add this price to the **same Pilot Teams product** — click "Add another price" on the product page.

| Field | Value |
|---|---|
| **Pricing type** | Recurring |
| **Amount** | `$1,788.00` |
| **Include tax in price** | No |
| **Billing period** | Yearly |
| **Unit quantity** | `1` |
| **Pricing model** | Flat rate |
| **Price description** | `Pilot Teams — annual billing ($149/mo, billed yearly)` |
| **Lookup key** | `pilot_teams_annual` |

### 2.6 Price Metadata (Annual)

| Key | Test Mode Value | Live Mode Value |
|---|---|---|
| `tier_name` | `teams` | `teams` |
| `billing_interval` | `annual` | `annual` |
| `lookup_key` | `pilot_teams_annual` | `pilot_teams_annual` |
| `env` | `test` | `production` |

---

## 3. What NOT to Create Now

| Item | Reason |
|---|---|
| Founders Stripe price | `founders` tier is $0/mo — the backend free path triggers when `stripe_price_id_monthly IS NULL`. No Stripe price object needed. |
| Trial Stripe price | `trial` tier is $0 and `is_active=false`. No price needed. |
| Add-on prices (+1 lane $10/mo, +5 lanes $40/mo) | Phase 1.5 feature — requires `tenant_subscription_addon` schema and Stripe subscription item logic not yet designed. |

---

## 4. Price IDs — All Confirmed

| Mode | Product | Interval | Price ID | Amount |
|---|---|---|---|---|
| **Live** | Pilot Starter | Monthly | `price_REDACTED01` | $59.00/mo ✅ |
| **Live** | Pilot Starter | Annual | `price_REDACTED05` | $588.00/yr ✅ |
| **Live** | Pilot Teams | Monthly | `price_REDACTED02` | $179.00/mo ✅ |
| **Live** | Pilot Teams | Annual | `price_REDACTED06` | $1,788.00/yr ✅ |
| **Test** | Pilot Starter | Monthly | `price_REDACTED16` | $59.00/mo ✅ |
| **Test** | Pilot Starter | Annual | `price_REDACTED17` | $588.00/yr ✅ |
| **Test** | Pilot Teams | Monthly | `price_REDACTED19` | $179.00/mo ✅ |
| **Test** | Pilot Teams | Annual | `price_REDACTED18` | $1,788.00/yr ✅ |
| **Test** | Pilot Starter (charter rate) | Monthly | `price_REDACTED15` | $49.00/mo ✅ |
| **Live** | Pilot Starter (charter rate) | Monthly | `price_REDACTED11` | $49.00/mo ✅ |

> **Charter tier price IDs — CLASSIFIED 2026-08-18 (DB-MGMT-1 follow-up closed):** the charter monthly price is a price **on the Pilot Starter product** (`prod_starter` per `stripe_bootstrap.py` `PRICES` map) — not a separate product, which is why only Starter/Teams/Passthrough products appear in the Dashboard. Three charter price IDs exist: `price_REDACTED09` = **original test-mode** charter price (first C-B3 test bootstrap; recorded in `batch-c-b4-design.md` §A on 2026-08-04; superseded when the test bootstrap re-ran 2026-08-08 — may show as archived in the Dashboard) · **current test** = `price_REDACTED15` (per `stripe_ids.test.json`) · **live** = `price_REDACTED11` (per `stripe_ids.live.json`). Charter annual = NULL in both modes (no annual charter price). Runtime app behavior is unaffected (IDs load from the JSON mapping files via `core/stripe_config.py`, not from the DB column). **Registry fixed 2026-08-18**: `_env_profiles.py` TEST/LIVE charter slots corrected to the mapping-file values (Tom); remaining step is a dev converge so the DB charter row (`price_…`, MCP-verified 2026-08-18) catches up.
>
> **Test-family realignment — RESOLVED 2026-08-18:** the same 2026-08-08 test bootstrap re-run also minted new starter/teams test IDs (`price_…` family), superseding the 2026-07-14 manually-created family (`price_…` / `price_…`, which still exist in the test account and may show as archived). Tom ruled the **mapping files canonical** (they are what the runtime loads) and updated the `_env_profiles.py` TEST map to the new family; the §4 table above and §5 reference values were updated to match. Live IDs were unaffected — the 2026-08-04 live bootstrap **adopted** the 2026-07-14 live objects, so §4 live rows stand. Remaining step: a dev converge writes the new test family into the dev DB.

---

## 5. DB Updates

> **⚠️ PROCEDURE RETIRED — ADR-0016 / DB-MGMT-1 (2026-08-18):** one-off UPDATE SQL is no longer executed against any environment. Price-ID changes flow through the env-aware seed system: `python migrations/scripts/seed_platform.py --env {dev,e2e,qa}` for non-prod; `DATABASE_URL=<prod tunnel URL> python migrations/scripts/seed_prod_db.py --stripe-mode {test|live}` for prod (Tom executes; typed confirmation `PILOT-PROD-SEED` + Stripe key preflight; idempotent converge-UPDATE on the price-ID slots — charter included now that its mode is classified, see §4 note). The SQL statements below are retained **as the canonical value reference only**. See `backend/README-seed-data.md` §7.6–§7.7.

Run against **dev DB** (test mode price IDs):

```sql
UPDATE subscription_tier SET stripe_price_id_monthly = 'price_REDACTED16' WHERE tier_name = 'starter';
UPDATE subscription_tier SET stripe_price_id_monthly = 'price_REDACTED19'  WHERE tier_name = 'teams';
UPDATE subscription_tier SET stripe_price_id_annual  = 'price_REDACTED17' WHERE tier_name = 'starter';
UPDATE subscription_tier SET stripe_price_id_annual  = 'price_REDACTED18'  WHERE tier_name = 'teams';
```

Run against **production DB** (live mode price IDs — during prod deployment prep):

```sql
UPDATE subscription_tier SET stripe_price_id_monthly = 'price_REDACTED01' WHERE tier_name = 'starter';
UPDATE subscription_tier SET stripe_price_id_monthly = 'price_REDACTED02'  WHERE tier_name = 'teams';
UPDATE subscription_tier SET stripe_price_id_annual  = 'price_REDACTED05' WHERE tier_name = 'starter';
UPDATE subscription_tier SET stripe_price_id_annual  = 'price_REDACTED06'  WHERE tier_name = 'teams';
```

Verify:
```sql
SELECT tier_name, display_label, annual_price_cents, monthly_price_cents,
       stripe_price_id_monthly, stripe_price_id_annual, product_plan_code
FROM subscription_tier
ORDER BY display_order;
```

Expected result (dev DB after all updates):

| tier_name | display_label | annual_price_cents | monthly_price_cents | stripe_price_id_monthly | stripe_price_id_annual | product_plan_code |
|---|---|---|---|---|---|---|
| founders | Founders | 0 | 0 | `NULL` | `NULL` | founders_plan |
| trial | Trial | 0 | 0 | `NULL` | `NULL` | starter_plan |
| starter | Starter | 58800 | 5900 | `price_REDACTED16` ✅ | `price_REDACTED17` ✅ | starter_plan |
| teams | Teams | 178800 | 17900 | `price_REDACTED19` ✅ | `price_REDACTED18` ✅ | teams_plan |

---

## 5. AWS Secrets Manager — Live Keys Entry

Secret name: `stripe`

Enter as a JSON secret in AWS Console → Secrets Manager → `stripe` → **Store a new secret value**:

```json
{
  "secret_key": "sk_live_...",
  "publishable_key": "pk_live_...",
  "webhook_secret": "whsec_..."
}
```

- `secret_key` — from Stripe Dashboard → Developers → API Keys → Live mode secret key
- `publishable_key` — from Stripe Dashboard → Developers → API Keys → Live mode publishable key
- `webhook_secret` — from Stripe Dashboard → Developers → Webhooks → `https://api.pilotfortrades.com/api/v1/webhooks/stripe` → Signing secret

The ECS task definition pulls these three values at container startup via:
```hcl
{ name = "STRIPE_SECRET_KEY",      valueFrom = "...stripe:secret_key::" }
{ name = "STRIPE_PUBLISHABLE_KEY", valueFrom = "...stripe:publishable_key::" }
{ name = "STRIPE_WEBHOOK_SECRET",  valueFrom = "...stripe:webhook_secret::" }
```

---

## 6. Local Dev `.env` Updates

Add to `backend/.env` (test mode keys — same as `.env.e2e`):

```bash
# Stripe — Test Mode (local dev)
STRIPE_SECRET_KEY=sk_test_...          # from Stripe Dashboard → Test mode → API Keys
STRIPE_WEBHOOK_SECRET=whsec_...       # from Stripe Dashboard → Test mode → Webhooks → ngrok endpoint signing secret
```

The ngrok test webhook URL is: `https://your-tunnel.ngrok-free.dev/api/v1/webhooks/stripe`

---

## 7. Annual Pricing — Stripe Dashboard Setup

SD-3 added the schema for annual billing (`stripe_price_id_annual` column on `subscription_tier`). STRIPE-B1 wired the backend routing. The remaining step is creating the annual Stripe prices in the Dashboard.

**⚠️ Tom's pending action items**:

1. **Create annual price for Pilot Starter** — add a new price to the **Pilot Starter** product (§1.5): `$588.00/year` · billing period: `yearly` · lookup key: `pilot_starter_annual`. Do in **Test mode first**, then **Live mode**.
2. **Create annual price for Pilot Teams** — add a new price to the **Pilot Teams** product (§2.5): `$1,788.00/year` · billing period: `yearly` · lookup key: `pilot_teams_annual`. Do in **Test mode first**, then **Live mode**.
3. Once all 4 IDs are known (2 test + 2 live), run the annual SQL in §5 and update §4 table above.

Marketing site display for annual billing (per GTM strategy v3.0 §10.3):

| Tier | Annual billing (shown by default) | Monthly billing (toggle) |
|---|---|---|
| Starter | $49/mo (billed $588/year) | $59/mo |
| Teams | $149/mo (billed $1,788/year) | $179/mo |

---

## 8. Webhook Events Registered ✅

### 8.1 Platform Endpoint (subscription billing)

**URL**: `https://api.pilotfortrades.com/api/v1/webhooks/stripe`
**Secret env var**: `STRIPE_WEBHOOK_SECRET`

All 10 events are registered on the platform webhook endpoint in Stripe Dashboard (confirmed 2026-07-14):

| Event | Handler | Registered |
|---|---|---|
| `charge.refunded` | `_handle_refund_event()` | ✅ |
| `customer.subscription.created` | `handle_subscription_created()` | ✅ |
| `customer.subscription.deleted` | `handle_invoice_payment_failed()` (dunning path) | ✅ |
| `customer.subscription.updated` | `handle_subscription_created()` (upsert pattern) | ✅ |
| `invoice.paid` | logged + no-op (payment already recorded via `payment_intent.succeeded`) | ✅ |
| `invoice.payment_failed` | `handle_invoice_payment_failed()` | ✅ |
| `payment_intent.payment_failed` | `handle_payment_intent_failed()` | ✅ |
| `payment_intent.succeeded` | `handle_payment_intent_succeeded()` | ✅ |
| `refund.created` | `_handle_refund_event()` | ✅ |
| `subscription_schedule.updated` | `handle_subscription_schedule_updated()` | ✅ |

All events are deduplicated via `stripe_webhook_event_processed` table (TEXT PK = Stripe `event_id`).

> **Why `subscription_schedule.updated` and not `customer.subscription.updated`**: Although the event name sounds "global", Stripe fires one event *per schedule* — the payload's `data.object` is a SubscriptionSchedule containing `customer` (identifies which tenant), `phases[]`, `current_phase`, and `metadata.schedule_type`. The handler reads all four of these fields. `customer.subscription.updated` delivers a Subscription object with none of these fields — the handler cannot determine which phase activated and would silently no-op every time. `subscription_schedule.updated` is the correct event.

### 8.2 Connect Endpoint (tenant card payments — STRIPE-CONNECT-1, 2026-08-28)

**URL**: `https://api.pilotfortrades.com/api/v1/webhooks/stripe-connect`
**Secret env var**: `STRIPE_CONNECT_WEBHOOK_SECRET`

Stripe delivers connected-account events (direct charges, account lifecycle, disputes) **only to endpoints registered for connected accounts** — the platform endpoint receives platform-account events only. Two endpoints, two signing secrets, one shared dedup table (`stripe_webhook_event_processed` — event IDs are globally unique).

6 events are registered on the Connect webhook endpoint:

| Event | Handler | Registered |
|---|---|---|
| `account.updated` | `handle_connect_account_updated()` — persists `charges_enabled` / `payouts_enabled` onto the tenant | ✅ sandbox 2026-08-30 · ⬜ prod |
| `account.application.deauthorized` | `handle_connect_deauthorized()` — nulls `stripe_connect_account_id` + flags; enqueues `stripe_connect_disconnected` owner notification | ✅ sandbox 2026-08-30 · ⬜ prod |
| `charge.dispute.created` | `handle_connect_dispute(closed=False)` — enqueues `stripe_dispute_opened` owner notification | ✅ sandbox 2026-08-30 · ⬜ prod |
| `charge.dispute.closed` | `handle_connect_dispute(closed=True)` — enqueues dispute-closed note to owner | ✅ sandbox 2026-08-30 · ⬜ prod |
| `payment_intent.succeeded` | delegates to `handle_payment_intent_succeeded()` (existing handler — resolves via PI metadata, idempotent) | ✅ sandbox 2026-08-30 · ⬜ prod |
| `payment_intent.payment_failed` | delegates to `handle_payment_intent_failed()` (existing handler) | ✅ sandbox 2026-08-30 · ⬜ prod |

> **`payment_intent.succeeded` on the Connect endpoint**: customer card payments on the public `/i/[token]` page arrive at the **Connect** endpoint (not the platform endpoint) because the PI was created with `stripe_account=` (direct charge on the connected account). The Connect handler delegates to the existing `handle_payment_intent_succeeded()` which resolves the invoice via PI metadata and is idempotent by `stripe_payment_intent_id`.

#### Tom's Registration Checklist (sandbox + prod)

> ⚠️ **Environment disambiguation (2026-08-30)**: "sandbox" here means the **HotRMC Sandbox environment** (Dashboard environment picker) — where platform `acct_###` + test connected account `acct_####` live. It is **NOT** the live account's **Test-mode toggle** (that belongs to the subscription-billing/platform endpoint). Webhook events fire only in the environment where the connected accounts exist — a Test-mode endpoint will never receive a Connect event. "Prod" = live mode.

1. **Prerequisite (discovered 2026-08-30)**: enable **Accounts v1 support** in the environment you're registering — Settings → Features, or `https://dashboard.stripe.com/settings/features/feat_accounts_v1_support`. Stripe gates new platforms out of v1 `Account.create` (error: *"Stripe no longer recommends Accounts v1 for new Connect integrations…"*); our integration is v1-architecture by design (ADR-0019: Express + direct charges + Account Links + v1 events). **Do this in BOTH the Sandbox and, later, the live account** (step 10 will fail the same way without it). Accounts v2 migration is a separate post-launch architectural evaluation.
2. **Stripe Dashboard → Developers → Webhooks → Add endpoint**
3. **Endpoint URL**: `https://api.pilotfortrades.com/api/v1/webhooks/stripe-connect`
4. **Description**: `Pilot Connect (tenant card payments)`
5. **Events to send**: select the 6 events listed above
6. **Capture the signing secret** (`whsec_…`) from the endpoint details page
7. **Set the secret**:
   - **Sandbox/dev**: set `STRIPE_CONNECT_WEBHOOK_SECRET` in `backend/.env` (or the sandbox Secrets Manager path)
   - **Prod**: add `STRIPE_CONNECT_WEBHOOK_SECRET` to the `pilot/prod/stripe` secret in AWS Secrets Manager → `aws ecs update-service --force-new-deployment` (no image rebuild needed)
8. **Set the Connect platform key** (`STRIPE_CONNECT_PLATFORM_KEY`):
   - **Sandbox/dev**: the sandbox platform `acct_###` secret key (or leave empty — falls back to `STRIPE_SECRET_KEY` via getattr)
   - **Prod**: add to `pilot/prod/stripe` secret → redeploy

> ⚠️ **Deployed-env prerequisite (added 2026-08-30)**: steps 7–8 require the ECS task-def injection to exist — `local.common_secrets` in `modules/compute/main.tf` must map `STRIPE_CONNECT_PLATFORM_KEY` ← `connect_platform_key` and `STRIPE_CONNECT_WEBHOOK_SECRET` ← `connect_webhook_secret` from the `pilot/prod/stripe` secret, followed by `terraform apply`. Updating the secret JSON alone injects nothing (wired 2026-08-30 during the STRIPE-CONNECT-1 registration tail; `force-new-deployment` without the mapping has no effect). When updating the secret, `put-secret-value` replaces the **whole** JSON — merge the two new keys with the existing three (`publishable_key`/`secret_key`/`webhook_secret`), never overwrite.
9. **Verify**: send a test event via the **Stripe CLI** (the Sandbox UI has no "Send test webhook" button for connected-account endpoints):
   - `stripe trigger payment_intent.succeeded` with the CLI authed to the **HotRMC Sandbox** (`stripe login` → pick the sandbox environment)
   - Inspect in the Sandbox Dashboard: **Developers → Events** (raw event + payload) and **Developers → Webhooks → the Connect endpoint → Recent deliveries** (HTTP status + response body — expect `{"status": "received"}`)
   - ⚠️ **Scoping caveat (verified 2026-08-30)**: `stripe trigger` creates the fixture on the **platform account** — a *platform-account* event, which the connected-accounts endpoint will **not** receive (that scoping is the design, see the note above). Delivery at the Connect endpoint is only exercised by events originating from a connected account — i.e., the real flows in `pilot-operations.md §11.3` (Option B onboarding fires `account.updated`; a 4242 payment on a public link fires `payment_intent.succeeded` with `stripe_account=`). Use CLI triggers to verify platform-side plumbing; use the §11.3 playbook to verify Connect delivery end-to-end.
10. **Repeat for prod** (live mode Dashboard) after the sandbox verification passes

---

## 9. Stripe Product Price IDs — Quick Reference

Update this table as price IDs are confirmed. Same price IDs before/after the amount update — no new IDs generated when editing an existing price amount.

**Price IDs - Live Mode**

| Tier | Interval | Price ID | Amount |
|---|---|---|---|
| starter | monthly | `price_REDACTED01` | $59/mo ✅ |
| starter | annual | `price_REDACTED05` | $588/yr ✅ |
| teams | monthly | `price_REDACTED02` | $179/mo ✅ |
| teams | annual | `price_REDACTED06` | $1,788/yr ✅ |

**Price IDs - Test Mode**

| Tier | Interval | Price ID | Amount |
|---|---|---|---|
| starter | monthly | `price_REDACTED16` | $59/mo ✅ |
| starter | annual | `price_REDACTED17` | $588/yr ✅ |
| teams | monthly | `price_REDACTED19` | $179/mo ✅ |
| teams | annual | `price_REDACTED18` | $1,788/yr ✅ |

---

*Maintained by: Pilot Architect. Update §4 with actual `price_...` IDs after Stripe Dashboard entry.*
