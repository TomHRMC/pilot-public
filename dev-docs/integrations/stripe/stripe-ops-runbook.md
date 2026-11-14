# Stripe Operations Runbook — Pilot for Trades

**Version**: 1.2
**Date**: August 10, 2026
**Author**: Pilot Architect
**Status**: ACTIVE — operational reference for all Stripe account management, testing, and the bootstrap script

> **v1.2 — Ops-doc ↔ integration-test alignment review (Architect, 2026-08-10)**: closes the Stripe leg of launch-plan Order 0. Reviewed every procedure/table against `backend/api/routes/webhooks_stripe.py`, `backend/services/stripe_subscriptions.py`, and `backend/tests/domains/subscriptions_usage/`. Fixes applied: (1) §9 handler table — `customer.subscription.deleted` was mis-mapped to `handle_invoice_payment_failed()` (actual: `handle_subscription_deleted()`); `invoice.paid` "no-op" was stale (actual: `handle_invoice_paid()` since C-B4); (2) §9 — documented the PLATFORM-SMS-B1 `platform_payment_failed` SMS dispatch on `invoice.payment_failed`; (3) §7 test inventory expanded 5 → 22 suites with accurate type/invocation. Verified accurate as-is: §1 account structure, §5 bootstrap modes, §6 runtime loading (`core/stripe_config.py`), §7 C-B14 operational constraints (2-interval limit, advancement-underway, metered+trial-pause exclusion, StripeObject `.get()`, stale JSON cache — all match `c-b14-testing-findings.md`), §9 15/15 event registration, §11 rehearsal (correctly gated on C-B14-FIX finding #1). **Confirmed gap (intentional, tracked)**: C-B14-FIX items remain open — the trial→active auto-conversion metered-item gap means rehearsal step 6 (PM attach during trial) is not yet safe to run end-to-end.

> **Companion documents**:
> - `stripe-pricing-config.md` — the pricing model decisions (annual vs monthly, 20% premium) and the original manual Dashboard setup guide (v1.1, July 14). Retained for historical reference; the bootstrap script (C-B3) supersedes the manual process for new object creation.
> - `pilot-tech-impl-spec-v1.md` §6 — the technical implementation spec for the Stripe object model, subscription creation, webhooks, and usage reporting.
> - `pilot-operations.md` — the runtime platform config (tier→plan→ppfv cascade, billing intervals, subscription status codes).

---

## Table of Contents

1. [Account Structure](#1-account-structure)
2. [Environment Mapping](#2-environment-mapping)
3. [Existing Stripe Objects](#3-existing-stripe-objects)
4. [What C-B3 Creates](#4-what-c-b3-creates)
5. [Bootstrap Script Usage](#5-bootstrap-script-usage)
6. [Runtime ID Loading](#6-runtime-id-loading)
7. [Testing Approach](#7-testing-approach)
8. [Pricing Changes](#8-pricing-changes)
9. [Webhook Configuration](#9-webhook-configuration)
10. [Secrets Management](#10-secrets-management)
11. [End-to-End Rehearsal (C-B14)](#11-end-to-end-rehearsal-c-b14)

---

## 1. Account Structure

Pilot for Trades operates under a single Stripe login (Example Holdings, LLC) with three distinct operational contexts:

| Account | Acct ID | Mode | Purpose | Bank Link |
|---|---|---|---|---|
| **HotRMC Live** | `acct_REDACTED01` | Live mode | Live-mode billing (configured and validated; never charged a customer) | HotRMC checking account ✅ |
| **HotRMC Test Mode** | `acct_REDACTED01` (same account, test mode toggle) | Test mode | Dev/QA testing — test cards, test clocks, no real charges | N/A (test mode) |
| **HotRMC Sandbox** | `acct_REDACTEDX01` | Sandbox | Stripe Connect testing (tenant→customer invoice payments) | Stripe Test Bank (routing `110000000`, acct `****6789`) |

**Key distinction**: Live and Test Mode share the same account ID (`acct_REDACTED01`) — they're the same Stripe account with a mode toggle. The Sandbox is a separate account (`acct_REDACTEDX01`) used exclusively for Stripe Connect (customer-facing payment) testing.

**Current state of each account**:

### HotRMC Live
- 2 Products: Pilot Starter, Pilot Teams (created manually via Dashboard)
- 4 Prices: Starter monthly $59, Starter annual $588, Teams monthly $179, Teams annual $1,788
- Stripe profile: "Pilot for Trades", bank account linked to HotRMC checking
- No customers, no transactions, no subscriptions, no invoices
- **Activated for production use** — `pilot/prod/stripe` Secrets Manager has live keys (secret_key, publishable_key, webhook_secret) as of August 4, 2026
- All 14 Stripe objects created via bootstrap script (C-B3): 3 Products, 2 Meters, 9 Prices

### HotRMC Test Mode
- Same 2 Products + 4 Prices as Live (shared account, same objects)
- All 14 Stripe objects created via bootstrap script (C-B3): 3 Products, 2 Meters, 9 Prices
- **Test data purged 2026-08-08** — all previous test transactions, customers, and test clocks deleted via Stripe Dashboard "Delete all test data". Dev tenant `stripe_customer_id` set to NULL in local DB. Clean slate for C-B14 test-clock scenarios.
- Used for: local dev testing, QA testing, Stripe test-clock scenarios (C-B14)

### HotRMC Sandbox
- 1 connected account ("Test account") — enabled, has 1 $100 payment (created by Testing Blueprints)
- No products for the sandbox account itself
- Used for: Stripe Connect testing (tenant→customer invoice payments — separate P2 feature, not part of the Charter build sequence)

---

## 2. Environment Mapping

| Environment | Stripe account | API key type | `STRIPE_MODE` env var | `stripe_ids.*.json` file |
|---|---|---|---|---|
| **Local dev** | HotRMC Test Mode | `sk_test_...` | `test` | `stripe_ids.test.json` |
| **QA / staging** | HotRMC Test Mode | `sk_test_...` | `test` | `stripe_ids.test.json` |
| **Production** | HotRMC Live | `sk_live_...` | `live` | `stripe_ids.live.json` |

The `STRIPE_MODE` env var determines which JSON mapping file the application loads at runtime (see §6). The API key (`STRIPE_SECRET_KEY` env var) determines which Stripe account/mode the API calls hit.

**The Sandbox account is not used by the application** — it's only for manual Stripe Connect testing via the Dashboard. The application's Stripe Connect integration (P2) will use the main account's Connect functionality, not the Sandbox.

> **⚠️ Phase 1 (now) — `production` runs in Stripe TEST mode.** Per the binding `aws-env-mgmt-ops-plan.md` §1/§4, until the first Charter member signs up, the **`production` environment is our integration-testing environment** and its `pilot/prod/stripe` secret holds **test-mode** keys (`sk_test_…` / `pk_test_…` / test `whsec_…`) hitting the shared HotRMC account in test mode. The "QA / staging" row in the table above is **Phase 2** (Charter beta onward) and does not exist yet. So the Environment Mapping table describes the *steady-state* target; the *current* reality is: local dev = test mode, **prod = test mode (integration env)**, no separate QA tier. Every signup performed in prod today is a **test tenant**, purged before the Phase 2 live cutover (`aws-env-mgmt-ops-plan.md` §6–§7). Prod flips to live-mode Stripe keys only at the §7 cutover ceremony.

---

## 3. Existing Stripe Objects

These objects were created manually via the Stripe Dashboard (per `stripe-pricing-config.md` v1.1, July 14). They use `lookup_key` metadata (e.g., `pilot_starter_monthly`), NOT `metadata.pilot_key`.

### Products (2 — exist in both test and live mode)

| Product | Name | Created | Metadata |
|---|---|---|---|
| Pilot Starter | `Pilot Starter` | Manual Dashboard | `tier_name: starter`, `product_plan_code: starter_plan` |
| Pilot Teams | `Pilot Teams` | Manual Dashboard | `tier_name: teams`, `product_plan_code: teams_plan` |

### Prices (10 — 5 test + 5 live, all confirmed; test family realigned to the bootstrap mapping files 2026-08-18)

| Mode | Product | Interval | Price ID | Amount |
|---|---|---|---|---|
| **Live** | Pilot Starter | Monthly | `price_REDACTED01` | $59.00/mo |
| **Live** | Pilot Starter | Annual | `price_REDACTED05` | $588.00/yr |
| **Live** | Pilot Teams | Monthly | `price_REDACTED02` | $179.00/mo |
| **Live** | Pilot Teams | Annual | `price_REDACTED06` | $1,788.00/yr |
| **Live** | Pilot Starter (charter rate) | Monthly | `price_REDACTED11` | $49.00/mo |
| **Test** | Pilot Starter | Monthly | `price_REDACTED16` | $59.00/mo |
| **Test** | Pilot Starter | Annual | `price_REDACTED17` | $588.00/yr |
| **Test** | Pilot Teams | Monthly | `price_REDACTED19` | $179.00/mo |
| **Test** | Pilot Teams | Annual | `price_REDACTED18` | $1,788.00/yr |
| **Test** | Pilot Starter (charter rate) | Monthly | `price_REDACTED15` | $49.00/mo |

### What does NOT exist yet

| Object | Why it's needed | Created by |
|---|---|---|
| Charter monthly price ($49/mo) | Charter tier billing (D17) | C-B3 bootstrap script |
| Carrier fees pass-through product | 10DLC cost pass-through (D24) | C-B3 bootstrap script |
| Voice AI minutes meter | Usage-based billing for overages | C-B3 bootstrap script |
| SMS segments meter | Usage-based billing for overages | C-B3 bootstrap script |
| Voice overage price ($0.05/min) | Overage billing | C-B3 bootstrap script |
| SMS overage price ($0.05/segment) | Overage billing | C-B3 bootstrap script |
| Lane add-on +1 price ($10/mo) | Schedule lane add-on | C-B3 bootstrap script |
| Lane add-on +5 price ($40/mo) | Schedule lane add-on | C-B3 bootstrap script |

---

## 4. What C-B3 Creates

The C-B3 bootstrap script creates only what's **missing**. It does NOT recreate the existing 2 Products or 8 Prices. Instead, it:

1. **Adopts** the existing Pilot Starter and Pilot Teams products (adds `metadata.pilot_key` to them)
2. **Creates** the Charter monthly price on the existing Pilot Starter product
3. **Creates** the Carrier fees pass-through product
4. **Creates** the 2 Billing Meters (Voice AI minutes, SMS segments)
5. **Creates** the 4 new prices (voice overage, SMS overage, lane add-on +1, lane add-on +5)
6. **Emits** `stripe_ids.{mode}.json` with ALL object IDs (existing + new)
7. **Optionally updates** the DB `stripe_price_id_*` columns via `--update-db`

### Object model after C-B3 (per spec §6.2)

**Products** (3 — 2 existing + 1 new):
| Key | Name | Status |
|---|---|---|
| `prod_starter` | "Pilot for Trades — Starter" | **Existing** — adopted (rename + add `pilot_key` metadata) |
| `prod_teams` | "Pilot for Trades — Teams" | **Existing** — adopted (rename + add `pilot_key` metadata) |
| `prod_passthrough` | "Carrier fees (pass-through)" | **New** — created by script |

**Meters** (2 — both new):
| Key | Event name | Status |
|---|---|---|
| `meter_voice_minutes` | `voice_minutes` | **New** |
| `meter_sms_segments` | `sms_segments` | **New** |

**Prices** (9 — 4 existing + 5 new):
| Key | Product | Amount | Status |
|---|---|---|---|
| `price_charter_monthly` | Starter | $49.00/mo | **New** |
| `price_starter_monthly` | Starter | $58.80/mo | **Existing** — adopted |
| `price_starter_annual` | Starter | $588.00/yr | **Existing** — adopted |
| `price_teams_monthly` | Teams | $178.80/mo | **Existing** — adopted |
| `price_teams_annual` | Teams | $1,788.00/yr | **Existing** — adopted |
| `price_voice_overage` | Starter | $0.05/min | **New** (metered) |
| `price_sms_overage` | Starter | $0.05/segment | **New** (metered) |
| `price_lane_addon_1` | Starter | $10.00/mo | **New** |
| `price_lane_addon_5` | Starter | $40.00/mo | **New** |

> **Note on Starter/Teams monthly prices**: The spec §6.2 says Starter monthly = $58.80 and Teams monthly = $178.80 (the 20% flexibility premium). The existing prices are $59.00 and $179.00. The script's `--migrate-prices` mode will detect this $0.20/$0.20 difference and create new prices at the exact spec amounts. The old prices will be archived. Since no subscriptions exist, this is safe.

---

## 5. Bootstrap Script Usage

```bash
cd <repo>/backend
source .venv/bin/activate

# Step 1: AUDIT — see what exists in the Stripe account before making changes.
# Lists all Products, Prices, Meters. Classifies as managed (has pilot_key) or orphaned (manual).
# Read-only — does NOT make any changes.
python scripts/stripe_bootstrap.py --mode test --audit

# Step 2: ADOPT — add metadata.pilot_key to existing objects so the script manages them.
# This tags the existing Pilot Starter/Teams products and their prices with pilot_key.
# Does NOT create new objects. Does NOT change amounts.
python scripts/stripe_bootstrap.py --mode test --adopt-existing

# Step 3: CREATE — create the missing objects (Charter price, pass-through product, meters, overage prices, lane add-ons).
# Idempotent — safe to re-run. Looks up by metadata.pilot_key before creating.
python scripts/stripe_bootstrap.py --mode test

# After purging the Stripe test account, the cached stripe_ids.test.json holds
# stale IDs. --force bypasses the JSON cache and re-queries Stripe for every
# object so missing objects are recreated instead of falsely reported as EXISTS.
python scripts/stripe_bootstrap.py --mode test --force

# Step 4: UPDATE DB — write the generated price IDs to subscription_tier columns.
python scripts/stripe_bootstrap.py --mode test --update-db

# Step 5: MIGRATE PRICES (optional — only if amounts need to change)
# Detects amount differences between script config and existing Stripe prices.
# Creates new prices, archives old ones. Excludes price-locked tiers (Charter).
python scripts/stripe_bootstrap.py --mode test --migrate-prices

# Dry run — show what would happen without calling Stripe API
python scripts/stripe_bootstrap.py --mode test --dry-run

# Live mode — requires explicit confirmation (creates in the production Stripe account)
python scripts/stripe_bootstrap.py --mode live --i-am-sure
```

### Mode flag

The `--mode test|live` flag determines which Stripe API key the script uses:
- `--mode test` → reads `STRIPE_SECRET_KEY` env var (must be a `sk_test_...` key)
- `--mode live` → reads `STRIPE_LIVE_SECRET_KEY` env var (must be a `sk_live_...` key); requires `--i-am-sure`

The script does NOT interact with the Sandbox account — that's for Stripe Connect testing only.

---

## 6. Runtime ID Loading

The application loads Stripe object IDs from a JSON mapping file at startup. The file is the **source of truth** — no Stripe ID is hardcoded in application code.

### File location

```
backend/scripts/stripe_ids.test.json   ← dev + QA (committed to git)
backend/scripts/stripe_ids.live.json   ← production only (gitignored, created on prod server)
```

### Loading mechanism (implemented in C-B4)

```python
# core/stripe_config.py (created in C-B4)
import json, os
from pathlib import Path

_cache: dict | None = None

def get_stripe_ids() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    mode = os.getenv("STRIPE_MODE", "test")
    path = Path(__file__).parent.parent / "scripts" / f"stripe_ids.{mode}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Stripe IDs file not found: {path}. "
            f"Run: python scripts/stripe_bootstrap.py --mode {mode}"
        )
    _cache = json.loads(path.read_text())
    return _cache
```

### Environment variables

| Env var | Dev | QA | Prod |
|---|---|---|---|
| `STRIPE_MODE` | `test` | `test` | `live` |
| `STRIPE_SECRET_KEY` | `sk_test_...` | `sk_test_...` | `sk_live_...` (from Secrets Manager) |
| `STRIPE_PUBLISHABLE_KEY` | `pk_test_...` | `pk_test_...` | `pk_live_...` (from Secrets Manager) |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...` (ngrok) | `whsec_...` (ALB) | `whsec_...` (ALB, from Secrets Manager) |

### DB columns vs. JSON file

The `subscription_tier` table has two types of price-related columns:

**Display columns** (`annual_price_cents`, `monthly_price_cents`):
- What the user/customer sees on the pricing page, signup wizard, and dashboard
- Populated by the seed script (source of truth for tier pricing)
- Example: `monthly_price_cents = 5900` → displayed as "$59/mo"

**Billing columns** (`stripe_price_id_monthly`, `stripe_price_id_annual`):
- What the backend uses to create Stripe subscriptions
- Populated by the bootstrap script's `--update-db` flag
- Example: `stripe_price_id_monthly = 'price_REDACTED16'`

The JSON file (`stripe_ids.{mode}.json`) is used for:
- All Stripe object IDs (including non-tier objects: meters, pass-through product, lane add-ons, overage prices)
- C-B4's new subscription creation logic (which will use `get_price_id()` from `core/stripe_config.py`)

All three sources (display columns, billing columns, JSON file) must stay in sync. The `--update-db` flag ensures the billing columns match the JSON file. The seed script ensures the display columns match the tier pricing.

---

## 7. Testing Approach

### Local dev

1. `STRIPE_SECRET_KEY=sk_test_...` in `.env` (test-mode key)
2. `STRIPE_MODE=test` in `.env`
3. `stripe_ids.test.json` committed to git (all devs have the same mapping)
4. Stripe CLI for webhook forwarding: `stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe`
5. Test cards: `4242 4242 4242 4242` (success), `4000 0000 0000 0002` (decline), `4000 0025 0000 3155` (3DS)
6. Test clocks for 90-day Charter flow (spec §6.9)

### QA / staging

1. Same test-mode keys as local dev
2. Webhook endpoint: ALB → `https://api.pilotfortrades.com/api/v1/webhooks/stripe` (test mode)
3. Same `stripe_ids.test.json` file

### Production

1. `STRIPE_SECRET_KEY=sk_live_...` from Secrets Manager `pilot/prod/stripe`
2. `STRIPE_MODE=live`
3. `stripe_ids.live.json` created by running: `python scripts/stripe_bootstrap.py --mode live --i-am-sure` (completed August 4, 2026 — C-B3)
4. Webhook endpoint: ALB → `https://api.pilotfortrades.com/api/v1/webhooks/stripe` (live mode)
5. ✅ **Activated** — `pilot/prod/stripe` has live keys as of August 4, 2026

### Test clock scenarios (C-B14)

Per spec §6.9, test clocks are mandatory for testing the 90-day Charter flow. Each integration test creates its own clocked customer. See spec §11.1 for the 12 Stripe integration scenarios.

### Test suite inventory (what exists, what it proves, how to run)

| Suite | Proves | Type | Invocation |
|---|---|---|---|
| `test_cb14_stripe_scenarios.py` | 12 test-clock Charter lifecycle scenarios: no-card signup→91d conversion, card-at-85d, silent extension at 80d/95d, 10DLC checkout mid-trial, meter events during/post trial, Charter→Teams upgrade, cancel, 12th-signup cap flip, concurrent 11th/12th signups, webhook idempotency | **Integration — hits the real Stripe test-mode API** | Run manually, never in CI without keys: `pytest tests/domains/subscriptions_usage/test_cb14_stripe_scenarios.py` (full run ≈ 7–8 min; requires `STRIPE_SECRET_KEY=sk_test_...` + bootstrapped test objects) |
| `test_cb14_entitlement_scenarios.py` | Charter entitlement gating (data export allowed, Teams-only features blocked) | Unit (mocked Stripe) | `pytest -m unit` |
| `test_cb14_telnyx_scenarios.py` | Telnyx mock carrier scenarios for the Charter flow | Unit (mocked Telnyx) | `pytest -m unit` |
| `test_cb4_create_charter_subscription.py` / `test_cb4_resume_subscription.py` / `test_cb4_resume_endpoint.py` | Charter subscription creation (flat-rate only, no metered items under trial-pause), resume flow + endpoint | Unit (mocked Stripe) | `pytest -m unit` |
| `test_cb4_webhook_handlers.py` / `test_cb6_trial_will_end_webhook.py` | C-B4 webhook handlers (paused/resumed/checkout.completed/PM attached) + trial_will_end T-3 dispatch | Unit (mocked Stripe) | `pytest -m unit` |
| `test_cb4_stripe_config.py` / `test_cb4_report_usage_event.py` | Runtime ID loading (`core/stripe_config.py`) + meter event reporting with idempotency key | Unit | `pytest -m unit` |
| `test_cb12_charter_upgrade.py` | Charter→Teams upgrade: monthly/annual, trial end, metered-item preservation/add-if-missing, forfeiture on error | Unit (mocked Stripe) | `pytest -m unit` |
| `test_cb10_recurring_item.py` | 10DLC carrier-fee recurring pass-through item creation | Unit (mocked Stripe) | `pytest -m unit` |
| `test_cb8_carrier_quote.py` / `test_cb9_messaging_provisioning.py` | Carrier fee quoting + 10DLC provisioning state machine (13 states) | Unit (mocked) | `pytest -m unit` |
| `test_cb13_charter_availability.py` | Public charter-availability endpoint shape + remaining-count math | Unit | `pytest -m unit` |
| `test_stripe_b1_billing_interval_detection.py` / `test_stripe_b1_price_id_routing.py` / `test_stripe_b1_subscription_schedule.py` | STRIPE-B1: billing-interval detection, price-ID routing (annual vs monthly), subscription schedule behavior | Unit (mocked Stripe) | `pytest -m unit` |
| `test_mkt_b11_pricing_v3.py` | GTM v3 pricing correctness on tier config | Unit | `pytest -m unit` |
| `test_sms_quota_mutation_coverage.py` | SMS quota mutation paths (billing-adjacent) | Unit | `pytest -m unit` |
| `test_sd3_billing_schema.py` / `test_sd07_feature_revision.py` | Billing schema seed integrity | Unit | `pytest -m unit` |

> **v1.2 (2026-08-10)**: inventory expanded from 5 suites to all 22 files in `tests/domains/subscriptions_usage/` (paths above are relative to that directory). Only `test_cb14_stripe_scenarios.py` exercises the real Stripe API — everything else is mocked.

**When to re-run the live test-clock scenarios** (the only suite that proves real Stripe behavior):
1. Before the first Charter member signs up (pre-launch gate — combined with §11 manual rehearsal).
2. After any change to `stripe_bootstrap.py`, `core/stripe_config.py`, `services/stripe_subscriptions.py`, or `api/routes/webhooks_stripe.py`.
3. After any Stripe test-data purge (remember: delete `scripts/stripe_ids.test.json` first — stale-cache finding §below).

**⚠️ Mocked unit tests do not catch Stripe API contract bugs** — MagicMock supports `.get()`, real `StripeObject`s do not; MagicMock accepts mutually exclusive params (metered items + trial-pause) that Stripe rejects. Only `test_cb14_stripe_scenarios.py` exercises the real API.

**Operational constraints discovered in C-B14 (2026-08-08)** — see `c-b14-testing-findings.md` for full detail:

- **2-interval advancement limit**: a clock can be advanced max 2 intervals of the shortest subscription interval per call (monthly sub → ≤60 days; use ≤59). `advance_clock_and_wait()` steps in ≤59-day increments, computing each target from the clock's **current `frozen_time`** (never `datetime.now(UTC)`).
- **"Advancement underway" rate limit**: modifications to clocked objects fail while Stripe processes an advance. Timing pattern: 10s sleep after each advancement step; advance call retried 8× at 15s; post-advancement API calls wrapped in `_retry_stripe_call()` (5× at 10s); 5s post-cleanup sleep between tests. Full 12-scenario runtime ≈ 7–8 min.
- **Metered items + trial-pause are mutually exclusive**: subscriptions with `trial_settings.end_behavior.missing_payment_method: pause` cannot contain metered items. Charter subscriptions are created with the flat-rate item only; metered overage items are added (a) on resume/upgrade by `_add_metered_overage_items()` (which also clears the pause behavior to `"cancel"`) and (b) — since **C-B14-FIX (2026-08-12)** — automatically by the `handle_subscription_created()` webhook on the trial→active auto-conversion path (PM added during trial; fires on `customer.subscription.updated` with `status='active'`, idempotent, failure logged not raised).
- **StripeObject has no `.get()`**: use `getattr(obj, "key", None)` or `obj["key"]` on all Stripe API response objects. Mocked tests will not catch `.get()` bugs — MagicMock supports it, StripeObject does not.
- **Stale `stripe_ids.{mode}.json` cache**: after purging Stripe test data, **delete `scripts/stripe_ids.test.json` before re-running the bootstrap** — the script trusts cached IDs and will report "EXISTS" for objects that no longer exist in Stripe.

---

## 8. Pricing Changes

When pricing changes (e.g., Starter goes from $49 to $79 at GA):

1. **Update the script config** — change the amount in `stripe_bootstrap.py`'s price definitions
2. **Run `--migrate-prices`** — the script detects the amount difference, creates a new Price, archives the old one, updates `stripe_ids.{mode}.json` + DB
3. **Existing subscriptions** stay on the old Price (archived prices continue billing at the old amount)
4. **New subscriptions** use the new Price
5. **Price-locked tiers (Charter)** are excluded from migration — filter on `price_locked=true`

**You cannot change a Price's amount in Stripe** — you must create a new Price and archive the old one. This is a Stripe platform constraint, not a Pilot design choice.

---

## 9. Webhook Configuration

### Registered events

15 events are registered on all three webhook endpoints (test-ngrok, test-ALB, live-ALB — each endpoint must independently have all 15; confirmed 2026-08-08, see verification block below):

| Event | Handler |
|---|---|
| `charge.refunded` | `_handle_refund_event()` |
| `customer.subscription.created` | `handle_subscription_created()` |
| `customer.subscription.deleted` | `handle_subscription_deleted()` |
| `customer.subscription.updated` | `handle_subscription_created()` (plan changes — same logic as created for MVP) |
| `invoice.paid` | `handle_invoice_paid()` (upgraded from no-op in C-B4 — see table below) |
| `invoice.payment_failed` | `handle_invoice_payment_failed()` — transitions tenant to payment_failed paywall + dispatches `platform_payment_failed` SMS via `send_platform_account_notification_sms` (PLATFORM-SMS-B1, 2026-08-10 — campaign `CXXXXXX` payment-failed sample) |
| `payment_intent.payment_failed` | `handle_payment_intent_failed()` (customer-facing public-link payment — notify tenant) |
| `payment_intent.succeeded` | `handle_payment_intent_succeeded()` (customer-facing public-link payment) |
| `refund.created` | `_handle_refund_event()` |
| `subscription_schedule.updated` | `handle_subscription_schedule_updated()` |

> **v1.2 alignment fix (2026-08-10)**: `customer.subscription.deleted` previously listed `handle_invoice_payment_failed()` — wrong; code dispatches `handle_subscription_deleted()` (`webhooks_stripe.py`). `invoice.paid` previously said "logged + no-op" — stale; upgraded to `handle_invoice_paid()` in C-B4.

### C-B4 Charter-lifecycle handlers — ✅ IMPLEMENTED (2026-08-04)

C-B4 added the Charter-lifecycle handlers. Verified live in `api/routes/webhooks_stripe.py` (dispatch block ~lines 171–183):

| Event | Handler | Status |
|---|---|---|
| `customer.subscription.trial_will_end` | `handle_subscription_trial_will_end()` — email + push + in-app banner (T-3) | ✅ In code |
| `customer.subscription.paused` | `handle_subscription_paused()` — read-only paywall (SMS stays if 10DLC active) | ✅ In code |
| `customer.subscription.resumed` | `handle_subscription_resumed()` — restore full access | ✅ In code |
| `invoice.paid` | `handle_invoice_paid()` (upgraded from logged no-op) | ✅ In code |
| `checkout.session.completed` | `handle_checkout_session_completed()` — `metadata.purpose == "a2p_10dlc_setup"` → attach PM, transition registration | ✅ In code |
| `payment_method.attached` | `handle_payment_method_attached()` — resume affordance if paused | ✅ In code |

> **⚠️ OPS VERIFICATION REQUIRED (found in v1.1 review, 2026-08-08)**: The 10-event registration above was confirmed **2026-07-14 — before C-B4 existed**. It has NOT been confirmed that the 5 new C-B4 event types (`trial_will_end`, `subscription.paused`, `subscription.resumed`, `checkout.session.completed`, `payment_method.attached`) are registered on the webhook endpoints in the Stripe Dashboard. **If they are not registered, Stripe never sends them and the T-3 warning / paywall-pause / resume flows silently never fire.**
>
> **How to verify (Tom, ~10 min)**:
> 1. Stripe Dashboard → **Developers → Webhooks** (toggle **Test mode** ON, top-right).
> 2. Click the endpoint `https://your-tunnel.ngrok-free.dev/api/v1/webhooks/stripe` (local dev) → check "Events sent" list contains all 15 events (10 original + 5 C-B4).
> 3. Click the endpoint `https://api.pilotfortrades.com/api/v1/webhooks/stripe` → same check.
> 4. Toggle **Test mode OFF** (live) → repeat for the live `api.pilotfortrades.com` endpoint.
> 5. If any of the 5 are missing: endpoint → **… menu → Update events** (or "Add events") → select them → Save. Do this on every endpoint that's missing them.
> 6. Record confirmation here: `[ ] test-ngrok [ ] test-ALB [ ] live-ALB` — 15/15 events each.
>
> **❌ VERIFICATION RESULT (Tom, 2026-08-08): CONFIRMED GAP.** The endpoints are registered for only the **original 10 events** — all 5 C-B4 events are missing: `customer.subscription.trial_will_end`, `customer.subscription.paused`, `customer.subscription.resumed`, `checkout.session.completed`, `payment_method.attached`. **Until these are added, the T-3 trial-ending warning, the pause/resume paywall flows, and the 10DLC Stripe Checkout completion handler never fire.**
>
> **✅ RESOLVED (Tom, 2026-08-08)**: All 5 C-B4 events added. Registered event list confirmed at exactly 15/15:
> `charge.refunded`, `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.deleted`, `customer.subscription.paused`, `customer.subscription.resumed`, `customer.subscription.trial_will_end`, `customer.subscription.updated`, `invoice.paid`, `invoice.payment_failed`, `payment_intent.payment_failed`, `payment_intent.succeeded`, `payment_method.attached`, `refund.created`, `subscription_schedule.updated`.
> - [x] Endpoint(s) verified 15/15 by Tom 2026-08-08 — **⚠️ if only one endpoint was updated, repeat on the remaining ones** (test-ngrok / test-ALB / live-ALB each need all 15)
>
> Fallback note: the T-3 free-period notification also fires via the `free_period_notifications` Celery beat task (daily 09:00 UTC), idempotently — `trial_will_end` registration is belt-and-suspenders.

### Webhook endpoints

Three endpoints exist in Stripe (live-mode and test-mode endpoints at the same URL are independent objects, each with its own signing secret):

| Endpoint | URL | Mode | Signing secret stored in | 15 events? |
|---|---|---|---|---|
| **test-ngrok** | `https://your-tunnel.ngrok-free.dev/api/v1/webhooks/stripe` | Test | local `.env` (`STRIPE_WEBHOOK_SECRET`) | ✅ |
| **test-ALB** | `https://api.pilotfortrades.com/api/v1/webhooks/stripe` | Test | `pilot/prod/stripe` (`webhook_secret`) — Phase 1 test-mode value | ✅ (created `aws-env-mgmt-ops-plan.md` §6 step 2) |
| **live-ALB** | `https://api.pilotfortrades.com/api/v1/webhooks/stripe` | Live | `pilot/prod/stripe` (`webhook_secret`) — Phase 2 live value | ✅ |

> **Same URL, two endpoints**: `api.pilotfortrades.com` exists as **two separate Stripe webhook endpoints** — one created in test mode, one in live mode. Live-mode events (real charges) route to the live endpoint; test-mode events (test cards, test clocks) route to the test endpoint. Each has its own `whsec_` because they verify different event streams.

> **All three endpoints must independently have all 15 events registered** (10 original + 5 C-B4). A webhook endpoint only receives events explicitly selected at creation — missing events are silently never delivered. Verify each endpoint's "Events sent" list in the Stripe Dashboard (toggle Test mode ON for the two test endpoints; OFF for the live endpoint).

All events are deduplicated via `stripe_webhook_event_processed` table (TEXT PK = Stripe `event.id`).

---

## 10. Secrets Management

### AWS Secrets Manager

| Secret name | Contents | Status |
|---|---|---|
| `pilot/prod/stripe` | `secret_key`, `publishable_key`, `webhook_secret` | ✅ Active — live keys loaded August 4, 2026 (C-B3) |

### Local dev `.env`

```bash
STRIPE_SECRET_KEY=sk_test_...          # Test mode secret key
STRIPE_WEBHOOK_SECRET=whsec_...       # Test mode webhook signing secret (ngrok endpoint)
STRIPE_MODE=test                               # Runtime mode for stripe_ids file loading
```

### ECS task definition (production)

```hcl
{ name = "STRIPE_SECRET_KEY",      valueFrom = "...pilot/prod/stripe:secret_key::" }
{ name = "STRIPE_PUBLISHABLE_KEY", valueFrom = "...pilot/prod/stripe:publishable_key::" }
{ name = "STRIPE_WEBHOOK_SECRET",  valueFrom = "...pilot/prod/stripe:webhook_secret::" }
{ name = "STRIPE_MODE",            value = "live" }
```

---

## 11. End-to-End Rehearsal (C-B14)

### Prerequisites

- Stripe CLI running: `stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe`
- `STRIPE_SECRET_KEY=sk_test_...` in `.env`
- `STRIPE_MODE=test` in `.env`
- Local dev server running (`uvicorn app.main:app --reload`)
- Stripe bootstrap objects created: `python scripts/stripe_bootstrap.py --mode test`

### Steps

1. Sign up as a new Charter member through the web app (`/signup`)
2. Complete the wizard (skip Step 4 payment — Charter requires no card)
3. Verify: subscription created in Stripe Dashboard (test mode) with `status=trialing`, `trial_end` = 90 days out
4. Verify: `tenant.charter_eligible=true`, `tenant.charter_member_number` assigned, `tenant.free_period_ends_at` set
5. Verify: `subscription_tier.charter` `is_active=true` (cap not reached)
6. Attach a test card (`4242 4242 4242 4242`) via the billing settings page
7. Verify: `stripe.Customer.modify` called with `invoice_settings.default_payment_method`
8. In Stripe Dashboard, advance the test clock to 91 days (or use the Stripe CLI)
9. Verify: subscription transitions to `active`, invoice paid ($49)
10. Verify: `is_subscription_billing_active() == True` — app fully functional
11. Cancel the subscription
12. Verify: `charter_eligible=false`, subscription `canceled`
13. Attempt to resubscribe — verify Charter option not available (`charter_eligible=false` persists)
14. Clean up: delete the test customer in Stripe Dashboard

### Automated Test Coverage

The 12 Stripe test-clock scenarios in `test_cb14_stripe_scenarios.py` cover the
same lifecycle programmatically. The manual runbook above is for final
pre-launch verification with the real web app UI.

---

## Open Items

- [x] **Tom**: Activate Stripe live mode and replace placeholder keys in Secrets Manager `pilot/prod/stripe` — ✅ Completed August 4, 2026
- [x] **C-B3**: Create the bootstrap script (`stripe_bootstrap.py`) with `--audit`, `--adopt-existing`, `--migrate-prices`, `--update-db`, `--dry-run`, `--i-am-sure` modes — ✅ Completed August 4, 2026
- [x] **C-B4**: Create `core/stripe_config.py` runtime loading module + expand webhook handlers — ✅ Completed
- [x] **C-B14**: Run full test-clock scenarios against the test-mode account — ✅ Completed August 8, 2026 (12/12 passed, ~455s). Findings: `c-b14-testing-findings.md`
> ~~**The 5 items below are scheduled as the C-B14-FIX batch** (P1, Pre-GA — see `pilot-launch-plan.md` §2.3). They are tracked work, not orphaned findings. §11 manual rehearsal stays gated until C-B14-FIX closes (finding #1 affects rehearsal step 6 — PM attach during trial).~~ **C-B14-FIX ✅ COMPLETE 2026-08-12 — all 5 items below resolved; the §11 manual rehearsal gate is CLEARED.**

- [x] **✅ RESOLVED 2026-08-12 — PLP-STRIPE-CHARTER-ROW-1** (discovered 2026-08-11 in the author's own Charter signup test on the pre-release AWS environment — Lang Electric Co., his test tenant, `cus_REDACTEDX02`; `public.subscription` was empty despite both `customer.subscription.created` + `invoice.paid` webhooks processed). Charter now writes the local `subscription` row at creation: (a) **write-at-source** — `create_charter_subscription()` calls the shared `_write_local_charter_subscription_row()` synchronously (status `trialing`, resolved by `code` not a hardcoded UUID; upsert `ON CONFLICT (psp_subscription_id)`; never raises so the wizard can't be crashed by a local-write failure); (b) **webhook fallback** — `handle_subscription_created()` resolves the Charter tier by `metadata.tier_code == "charter"` when the price-ID lookup misses (Charter's `stripe_price_id_monthly IS NULL`). The already-provisioned tenant was corrected via idempotent `backfill_charter_subscription_row.py` (reads `sub_…` from Stripe, never fabricated; safe to re-run). `is_subscription_billing_active()` now finds the billing-active row → paywalled mutations no longer 402. Tests: `tests/domains/subscriptions_usage/test_plp_stripe_charter_row_1.py`. See `pilot-launch-plan.md` Appendix C.
- [x] **✅ RESOLVED 2026-08-12 — C-B14-FIX Task 1** (finding #1 gap): `handle_subscription_created()` now provisions metered items when payload `status='active'` in BOTH the Charter fallback and normal tier branches; Charter branch flips the local row trialing→active (status resolved by code); out-of-order guard prevents active→trialing demotion; metered-step failure is logged, never raised (webhook is fire-and-forget)
- [x] **✅ RESOLVED 2026-08-12 — C-B14-FIX Task 2** (finding #2): `.get()` audit complete — one real fix (`mode_audit()` prices-loop `recurring_obj.get("interval")` → `getattr()`); all other sites safe-dict (audit table in the Appendix C completion summary)
- [x] **✅ RESOLVED 2026-08-12 — C-B14-FIX Task 3** (finding #5): `--force` flag added to `stripe_bootstrap.py` (usage above); bypasses the JSON cache half only — live Stripe lookup always runs
- [x] **✅ RESOLVED 2026-08-12 — C-B14-FIX Task 4** (finding #6): stale `pilot_key={pkey!r}` fragment removed from the meters loop; `mode_audit()` survives empty prices
- [x] **✅ RESOLVED 2026-08-12 — C-B14-FIX Task 5** (finding #7): `extend_free_period()` validates `operator_user_id` exists in `user` before the override upsert → `ValueError("... not found")` → 404 RFC 7807; route already passed the authenticated `platform_user.id` (verified)
- [x] **Tom** (v1.1 review 2026-08-08): verify the 5 C-B4 webhook events are registered — ✅ DONE 2026-08-08 (15/15 confirmed; see §9 for the per-endpoint caveat)

---

*Maintained by: Pilot Architect + DevOps Engineer. Update this runbook whenever the Stripe account structure, webhook configuration, or bootstrap script changes.*
