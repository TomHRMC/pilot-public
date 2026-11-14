# Stripe Bootstrap Script

**Batch**: C-B3
**Script**: [`stripe_bootstrap.py`](stripe_bootstrap.py)
**Created**: August 4, 2026
**Status**: Complete — the operational script used for all Stripe billing objects (project hibernated September 2026)

> **Companion documents**:
> - [`stripe-ops-runbook.md`](../../dev-docs/integrations/stripe/stripe-ops-runbook.md) — the operational reference for the Stripe account structure, testing, and runtime ID loading
> - [`batch-c-b3-design.md`](../../dev-docs/architecture-design/batch-designs/batch-c-b3-design.md) — the batch design doc

---

## Overview

The bootstrap script manages all Stripe objects for the Pilot subscription billing model:

- **3 Products**: Pilot Starter, Pilot Teams, Carrier fees (pass-through)
- **2 Billing Meters**: Voice AI minutes, SMS segments
- **9 Prices**: Charter monthly, Starter monthly/annual, Teams monthly/annual, Voice overage, SMS overage, Lane add-on +1, Lane add-on +5

The script is **idempotent** — it looks up existing objects by `metadata.pilot_key` (Products/Prices) or `event_name` (Meters) before creating, so it's safe to re-run.

---

## Modes

The script has 5 action modes plus 2 modifier flags:

### Action Modes

| Mode | Flag | Description |
|---|---|---|
| **Audit** | `--audit` | Read-only report of existing Stripe objects. Classifies each as managed (has `pilot_key`) or orphaned (manual). No changes. |
| **Adopt-existing** | `--adopt-existing` | Adds `metadata.pilot_key` to existing manually-created objects (2 Products + 4 Prices). Does NOT change amounts or create new objects. |
| **Create** | *(default)* | Creates missing objects. Order: Products → Meters → Prices (meters before metered prices). All new objects get `metadata.pilot_key`. |
| **Update-db** | `--update-db` | Writes generated price IDs to `subscription_tier.stripe_price_id_monthly`/`stripe_price_id_annual` columns via SQL UPDATE. |
| **Migrate-prices** | `--migrate-prices` | Detects amount changes, creates new prices, archives old ones. Excludes price-locked tiers (Charter). Updates JSON file + DB. |

### Modifier Flags

| Flag | Description |
|---|---|
| `--dry-run` | Preview what would happen without calling Stripe API (limited — still lists objects for lookup). |
| `--i-am-sure` | Required for `--mode live` to prevent accidental production changes. |
| `--force` | Ignore cached `stripe_ids.{mode}.json` and re-query Stripe for every object. Use after purging the Stripe account so stale cached IDs don't mask missing objects. Applies to `mode_create` only. |

---

## Usage

### Standard Workflow

```bash
cd <repo>/backend
source .venv/bin/activate
set -a && source .env && set +a

# Step 1: AUDIT — see what exists before making changes
python scripts/stripe_bootstrap.py --mode test --audit

# Step 2: ADOPT — tag existing objects with pilot_key metadata
python scripts/stripe_bootstrap.py --mode test --adopt-existing

# Step 3: CREATE — create missing objects (Charter price, meters, overages, lane add-ons)
python scripts/stripe_bootstrap.py --mode test

# Step 4: UPDATE-DB — write price IDs to subscription_tier columns
python scripts/stripe_bootstrap.py --mode test --update-db
```

### Live Mode

```bash
# Live mode requires --i-am-sure and STRIPE_LIVE_SECRET_KEY env var
python scripts/stripe_bootstrap.py --mode live --i-am-sure --audit
python scripts/stripe_bootstrap.py --mode live --i-am-sure --adopt-existing
python scripts/stripe_bootstrap.py --mode live --i-am-sure
```

> **Note**: `--update-db` for live mode should be run against the production database, not the local dev database.

### Dry Run

```bash
python scripts/stripe_bootstrap.py --mode test --dry-run
```

### Force (after purging the Stripe account)

```bash
# After deleting all objects in the Stripe test account, the cached
# stripe_ids.test.json still holds stale IDs. --force bypasses the JSON
# cache and re-queries Stripe for every object, so missing objects are
# recreated instead of falsely reported as "EXISTS".
python scripts/stripe_bootstrap.py --mode test --force
```

---

## Environment Variables

| Variable | Test Mode | Live Mode |
|---|---|---|
| `STRIPE_SECRET_KEY` | `sk_test_...` | — |
| `STRIPE_LIVE_SECRET_KEY` | — | `sk_live_...` |
| `DATABASE_URL` | Required for `--update-db` | Required for `--update-db` |

---

## Output File

After any mode that creates or adopts objects, the script emits `stripe_ids.{mode}.json`:

```
backend/scripts/stripe_ids.test.json   ← committed to git (test-mode IDs are not secrets)
backend/scripts/stripe_ids.live.json   ← gitignored (live-mode IDs are production-only)
```

### File Format

```json
{
  "mode": "test",
  "created_at": "2026-08-04T16:20:38Z",
  "api_version": "2025-03-31.basil",
  "products": {
    "prod_starter": "prod_XXX",
    "prod_teams": "prod_YYY",
    "prod_passthrough": "prod_ZZZ"
  },
  "meters": {
    "meter_voice_minutes": "mtr_XXX",
    "meter_sms_segments": "mtr_YYY"
  },
  "prices": {
    "price_charter_monthly": "price_XXX",
    "price_starter_monthly": "price_YYY",
    ...
  }
}
```

The application loads this file at runtime via `core/stripe_config.py` (implemented in C-B4). No Stripe ID is hardcoded in application code.

---

## Object Model

### Products (3)

| Key | Name | Status |
|---|---|---|
| `prod_starter` | Pilot for Trades — Starter | Existing (adopted) |
| `prod_teams` | Pilot for Trades — Teams | Existing (adopted) |
| `prod_passthrough` | Carrier fees (pass-through) | Created by script |

### Billing Meters (2)

| Key | Event Name | Aggregation |
|---|---|---|
| `meter_voice_minutes` | `voice_minutes` | sum |
| `meter_sms_segments` | `sms_segments` | sum |

> **Note**: Billing Meters do not support `metadata`. Idempotent lookup is by `event_name` + `status=active`.

### Prices (9)

| Key | Product | Amount | Type |
|---|---|---|---|
| `price_charter_monthly` | Starter | $49.00/mo | Licensed (price_locked) |
| `price_starter_monthly` | Starter | $59.00/mo | Licensed |
| `price_starter_annual` | Starter | $588.00/yr | Licensed |
| `price_teams_monthly` | Teams | $179.00/mo | Licensed |
| `price_teams_annual` | Teams | $1,788.00/yr | Licensed |
| `price_voice_overage` | Starter | $0.05/min | Metered (voice_minutes) |
| `price_sms_overage` | Starter | $0.05/segment | Metered (sms_segments) |
| `price_lane_addon_1` | Starter | $10.00/mo | Licensed |
| `price_lane_addon_5` | Starter | $40.00/mo | Licensed |

---

## Pricing Changes

When pricing changes (e.g., Starter goes from $59 to $79 at GA):

1. Update the amount in the `PRICES` dict in `stripe_bootstrap.py`
2. Run `--migrate-prices` — the script detects the amount difference, creates a new Price, archives the old one, updates `stripe_ids.{mode}.json` + DB
3. Existing subscriptions stay on the old Price (archived prices continue billing at the old amount)
4. New subscriptions use the new Price
5. Price-locked tiers (Charter) are excluded from migration

> **Stripe constraint**: You cannot change a Price's amount — you must create a new Price and archive the old one.

---

## Cross-References

- [`stripe-ops-runbook.md`](../../dev-docs/integrations/stripe/stripe-ops-runbook.md) — account structure, testing approach, webhook config, secrets management
- [`stripe-pricing-config.md`](../../dev-docs/integrations/stripe/stripe-pricing-config.md) — historical reference for the original manual Dashboard setup (superseded by this script)
- [`batch-c-b3-design.md`](../../dev-docs/architecture-design/batch-designs/batch-c-b3-design.md) — batch design doc with full object model and adoption mapping
- `pilot-tech-impl-spec-v1.md` _(private)_ §6 — technical implementation spec for the Stripe object model

---

*Maintained by: Pilot Python Engineer. Update this README whenever the script's modes, object model, or output format changes.*
