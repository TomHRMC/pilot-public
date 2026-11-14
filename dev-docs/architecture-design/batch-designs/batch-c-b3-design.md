# Batch C-B3 — Stripe Bootstrap Script (Products, Prices, Meters)

**Batch code**: C-B3
**Design doc owner**: Pilot Architect
**Created**: August 4, 2026 (reworked August 4, 2026)
**Status**: 🟡 Draft — awaiting Tom approval before engineer prompt is authored
**Plan link**: `pilot-launch-plan.md`
**Batch type**: Backend only (Python Engineer) — ops script, no API endpoints
**Engineer**: Pilot Python Engineer
**Prerequisite**: C-B2 ✅
**Source of truth**: `pilot-tech-impl-spec-v1.md` §6.1-6.3 + `stripe-ops-runbook.md`

---

## Problem Statement

The Commercial Implementation Spec §6.2 defines a new Stripe object model — 3 Products, 9 Prices, 2 Billing Meters. Two Products and four Prices already exist (created manually via Dashboard per `stripe-pricing-config.md` v1.1). This batch creates a bootstrap script that:

1. **Adopts** the existing objects (adds `metadata.pilot_key` so the script can manage them)
2. **Creates** only what's missing (Charter price, pass-through product, meters, overage prices, lane add-ons)
3. **Emits** a `stripe_ids.{mode}.json` mapping file for runtime loading
4. **Optionally updates** the DB price ID columns

The script operates against the HotRMC Stripe account in either test mode or live mode (see `stripe-ops-runbook.md` §1-2 for the account structure).

---

## A. Input Read Summary

| Input | Section(s) read | What it established |
|---|---|---|
| `pilot-tech-impl-spec-v1.md` | §6.1 (API version), §6.2 (object model), §6.3 (bootstrap script requirements) | The full object model: 3 Products, 9 Prices, 2 Meters. Script requirements: idempotent, mode flag, mapping file, live guard. |
| `stripe-ops-runbook.md` | §1-10 (full document) | The three-account structure, environment mapping, existing objects (2 Products + 8 Prices with confirmed IDs), what C-B3 creates, script usage workflow, runtime loading, testing approach, pricing changes, webhook config, secrets. |
| `stripe-pricing-config.md` | §1-9 (full document) | The existing manual Dashboard setup: 2 Products (Pilot Starter, Pilot Teams), 8 confirmed price IDs (4 test + 4 live), `lookup_key` metadata (not `pilot_key`), DB SQL updates, webhook events, Secrets Manager config. |
| `pilot-gtm-strategy-v3.md` | §5.2, §5.3, §10 (D13, D17) | Charter = $49/mo flat (monthly, no annual). Starter = $49/mo annual / $59.00 monthly. Teams = $149/mo annual / $179.00 monthly. 20% monthly premium (D13), rounded to whole dollar. |
| `postgres-local` MCP | `subscription_tier` columns + data (post-C-B2) | `stripe_price_id_monthly`/`stripe_price_id_annual` columns exist. Charter has NULL. Starter/teams have existing test-mode price IDs from the manual setup. |
| Backend file listing | `backend/` root | No `scripts/` directory exists yet. C-B3 creates `backend/scripts/stripe_bootstrap.py`. |

### Existing Stripe objects (from `stripe-pricing-config.md` §4 + runbook §3)

**Products** (2 — exist in both test and live mode, use `lookup_key` metadata):
- Pilot Starter (`prod_...`) — metadata: `tier_name: starter`, `product_plan_code: starter_plan`
- Pilot Teams (`prod_...`) — metadata: `tier_name: teams`, `product_plan_code: teams_plan`

**Prices** (8 — 4 test + 4 live, all confirmed):

| Mode | Product | Interval | Price ID | Amount |
|---|---|---|---|---|
| Test | Starter | Monthly | `price_REDACTED03` | $59.00/mo |
| Test | Starter | Annual | `price_REDACTED07` | $588.00/yr |
| Test | Teams | Monthly | `price_REDACTED04` | $179.00/mo |
| Test | Teams | Annual | `price_REDACTED08` | $1,788.00/yr |
| Live | Starter | Monthly | `price_REDACTED01` | $59.00/mo |
| Live | Starter | Annual | `price_REDACTED05` | $588.00/yr |
| Live | Teams | Monthly | `price_REDACTED02` | $179.00/mo |
| Live | Teams | Annual | `price_REDACTED06` | $1,788.00/yr |

> **Note on amounts**: The spec §6.2 (updated 2026-08-04) uses rounded whole-dollar prices: Starter monthly = $59.00, Teams monthly = $179.00. These match the existing Stripe prices — no `--migrate-prices` step is needed for the initial setup. The `--migrate-prices` mode remains available for future price changes.

---

## B. Migration Plan

### B.1 — No DB migration

This batch creates a standalone Python script. No Alembic migration, no schema changes.

**DB price ID population**: The script's `--update-db` flag writes the generated price IDs to `subscription_tier.stripe_price_id_monthly`/`stripe_price_id_annual` columns via SQL UPDATE. The seed script is NOT involved — it stays the source of truth for tier data (names, prices, limits); the bootstrap script fills in just the Stripe ID columns.

### B.2 — Runtime loading contract (implemented in C-B4)

The application loads `stripe_ids.{mode}.json` at startup via `core/stripe_config.py`:

```python
# core/stripe_config.py (created in C-B4, contract defined here)
import json, os
from pathlib import Path

_cache: dict | None = None

def get_stripe_ids() -> dict:
    """Load and cache the Stripe ID mapping. Mode from STRIPE_MODE env var."""
    global _cache
    if _cache is not None:
        return _cache
    mode = os.getenv("STRIPE_MODE", "test")
    path = Path(__file__).parent.parent / "scripts" / f"stripe_ids.{mode}.json"
    if not path.exists():
        raise FileNotFoundError(f"Stripe IDs file not found: {path}. Run: python scripts/stripe_bootstrap.py --mode {mode}")
    _cache = json.loads(path.read_text())
    return _cache

def get_price_id(key: str) -> str:
    return get_stripe_ids()["prices"][key]

def get_meter_id(key: str) -> str:
    return get_stripe_ids()["meters"][key]

def get_product_id(key: str) -> str:
    return get_stripe_ids()["products"][key]
```

The JSON file is the source of truth for all Stripe object IDs. The DB has two roles:
- `annual_price_cents`/`monthly_price_cents` → **display source** — what the user/customer sees on the pricing page, signup wizard, and dashboard
- `stripe_price_id_monthly`/`stripe_price_id_annual` → **billing source** — what the backend uses to create Stripe subscriptions

The JSON file covers non-tier objects (meters, pass-through product, lane add-ons, overage prices) that don't have DB columns. All three sources (JSON file, display columns, billing columns) must stay in sync — the `--update-db` flag ensures the DB columns match the JSON file.

### B.3 — MCP verification queries (pre-work)

```sql
-- Confirm the stripe_price_id columns and current values
SELECT tier_name, stripe_price_id_monthly, stripe_price_id_annual FROM subscription_tier ORDER BY display_order;
-- Expected: charter has NULL for both; starter/teams have existing test-mode IDs
```

---

## C. Execution Order

| Step | Task | Files |
|---|---|---|
| 1 | Create `backend/scripts/` directory + `__init__.py` | `backend/scripts/__init__.py` |
| 2 | Write `stripe_bootstrap.py` with all modes: `--audit`, `--adopt-existing`, create (default), `--migrate-prices`, `--dry-run`, `--update-db`, `--i-am-sure` | `backend/scripts/stripe_bootstrap.py` |
| 3 | Run `--audit` to see existing Stripe objects | `python scripts/stripe_bootstrap.py --mode test --audit` |
| 4 | Run `--adopt-existing` to tag existing objects with `metadata.pilot_key` | `python scripts/stripe_bootstrap.py --mode test --adopt-existing` |
| 5 | Run default (create missing objects) | `python scripts/stripe_bootstrap.py --mode test` |
| 6 | Verify the generated `stripe_ids.test.json` | `backend/scripts/stripe_ids.test.json` |
| 7 | Run `--update-db` to write price IDs to `subscription_tier` | `python scripts/stripe_bootstrap.py --mode test --update-db` |
| 8 | Run `--migrate-prices` to fix the $59→$58.80 and $179→$178.80 rounding | `python scripts/stripe_bootstrap.py --mode test --migrate-prices` |
| 9 | Write a README for the script | `backend/scripts/README-stripe-bootstrap.md` |
| 10 | Update `stripe-pricing-config.md` — add superseded note + cross-reference runbook | `dev-docs/integrations/stripe/stripe-pricing-config.md` |
| 11 | Commit `stripe_ids.test.json`; add `stripe_ids.live.json` to `.gitignore` | `backend/.gitignore` |

---

## D. New API Endpoints

**None.** This is an ops script, not an API endpoint.

---

## E. Pattern Reuse Decisions

| Pattern | How it applies |
|---|---|
| **Idempotent script** (like `schema_manager.py`) | Look up by `metadata.pilot_key` before creating — safe to re-run |
| **Adopt-existing** | New pattern: add `metadata.pilot_key` to existing objects (created manually) so the script can manage them going forward. Does NOT change amounts or create duplicates. |
| **Mode flag** (`--mode test\|live`) | Determines which Stripe API key to use (`STRIPE_SECRET_KEY` for test, `STRIPE_LIVE_SECRET_KEY` for live). See runbook §2 for environment mapping. |
| **Mapping file** | `stripe_ids.{mode}.json` — the app loads this at runtime so no Stripe ID is hardcoded in application code |
| **Live-mode guard** (`--i-am-sure`) | Refuses to run against live without explicit confirmation |

---

## F. Shared Module Interfaces

### F.1 — Script modes

```bash
# AUDIT — read-only report of existing Stripe objects vs. what the script would create
python scripts/stripe_bootstrap.py --mode test --audit

# ADOPT-EXISTING — add metadata.pilot_key to existing objects (Pilot Starter, Pilot Teams products + their prices)
# Does NOT create new objects. Does NOT change amounts.
python scripts/stripe_bootstrap.py --mode test --adopt-existing

# CREATE (default) — create missing objects (Charter price, pass-through product, meters, overage prices, lane add-ons)
# Idempotent — looks up by metadata.pilot_key before creating.
python scripts/stripe_bootstrap.py --mode test

# UPDATE-DB — write generated price IDs to subscription_tier columns
python scripts/stripe_bootstrap.py --mode test --update-db

# MIGRATE-PRICES — detect amount changes, create new prices, archive old ones
# Excludes price-locked tiers (Charter). Updates JSON file + DB.
python scripts/stripe_bootstrap.py --mode test --migrate-prices

# DRY-RUN — show what would happen without calling Stripe API
python scripts/stripe_bootstrap.py --mode test --dry-run

# LIVE — requires explicit confirmation
python scripts/stripe_bootstrap.py --mode live --i-am-sure
```

### F.2 — Existing object adoption mapping

The `--adopt-existing` mode tags existing objects with `metadata.pilot_key`:

| Existing object | Lookup method | `pilot_key` value | Action |
|---|---|---|---|
| Pilot Starter product | Search by name "Pilot Starter" | `prod_starter` | Add `metadata.pilot_key = prod_starter` |
| Pilot Teams product | Search by name "Pilot Teams" | `prod_teams` | Add `metadata.pilot_key = prod_teams` |
| Starter monthly price | Search by `lookup_key = pilot_starter_monthly` | `price_starter_monthly` | Add `metadata.pilot_key = price_starter_monthly` |
| Starter annual price | Search by `lookup_key = pilot_starter_annual` | `price_starter_annual` | Add `metadata.pilot_key = price_starter_annual` |
| Teams monthly price | Search by `lookup_key = pilot_teams_monthly` | `price_teams_monthly` | Add `metadata.pilot_key = price_teams_monthly` |
| Teams annual price | Search by `lookup_key = pilot_teams_annual` | `price_teams_annual` | Add `metadata.pilot_key = price_teams_annual` |

The script looks up existing objects by their `lookup_key` metadata (the metadata key used in the manual Dashboard setup). If found, it adds `pilot_key` metadata. If not found (e.g., in a fresh Stripe account), it creates the object from scratch.

### F.3 — New objects to create

| Object | Key | Type | Details |
|---|---|---|---|
| Charter monthly price | `price_charter_monthly` | Price on Starter product | $49.00/mo, metadata: `{pilot_key: price_charter_monthly, tier_name: charter, price_locked: true, cohort: charter_1}` |
| Carrier fees product | `prod_passthrough` | Product | Name: "Carrier fees (pass-through)", metadata: `{pilot_key: prod_passthrough}` |
| Voice AI minutes meter | `meter_voice_minutes` | Billing Meter | event: `voice_minutes`, aggregation: sum, customer_mapping: by_id → `stripe_customer_id`, value: `value` |
| SMS segments meter | `meter_sms_segments` | Billing Meter | event: `sms_segments`, aggregation: sum, customer_mapping: by_id → `stripe_customer_id`, value: `value` |
| Voice overage price | `price_voice_overage` | Price on Starter product | $0.05/min, metered, `recurring[meter]=meter_voice_minutes`, metadata: `{pilot_key: price_voice_overage}` |
| SMS overage price | `price_sms_overage` | Price on Starter product | $0.05/segment, metered, `recurring[meter]=meter_sms_segments`, metadata: `{pilot_key: price_sms_overage}` |
| Lane add-on +1 | `price_lane_addon_1` | Price on Starter product | $10.00/mo, quantity-based, metadata: `{pilot_key: price_lane_addon_1}` |
| Lane add-on +5 | `price_lane_addon_5` | Price on Starter product | $40.00/mo, quantity-based, metadata: `{pilot_key: price_lane_addon_5}` |

**Meters must be created BEFORE metered prices** — the overage prices reference the meter IDs.

### F.4 — Output file format (`stripe_ids.test.json`)

```json
{
  "mode": "test",
  "created_at": "2026-08-04T14:00:00Z",
  "api_version": "2025-03-31.basil",
  "products": {
    "prod_starter": "prod_XXX",
    "prod_teams": "prod_YYY",
    "prod_passthrough": "prod_ZZZ"
  },
  "meters": {
    "meter_voice_minutes": "meter_XXX",
    "meter_sms_segments": "meter_YYY"
  },
  "prices": {
    "price_charter_monthly": "price_XXX",
    "price_starter_monthly": "price_REDACTED03",
    "price_starter_annual": "price_REDACTED07",
    "price_teams_monthly": "price_REDACTED04",
    "price_teams_annual": "price_REDACTED08",
    "price_voice_overage": "price_CCC",
    "price_sms_overage": "price_DDD",
    "price_lane_addon_1": "price_EEE",
    "price_lane_addon_5": "price_FFF"
  }
}
```

The existing price IDs (from the manual setup) are included in the JSON file alongside the new ones. The app uses the JSON file as the single source of truth for all Stripe IDs.

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| How does the script handle the existing manually-created objects? | **`--adopt-existing` mode** — looks up by `lookup_key` metadata, adds `pilot_key` metadata. Does NOT create duplicates or change amounts. See §F.2. |
| How does the script handle the three Stripe accounts? | **`--mode test\|live` flag** — test mode uses `STRIPE_SECRET_KEY` (sk_test_...), live mode uses `STRIPE_LIVE_SECRET_KEY` (sk_live_...). The Sandbox account is not used by the script (it's for Stripe Connect testing only). See runbook §1-2. |
| How does the app load IDs at runtime? | **`core/stripe_config.py`** (C-B4) loads `stripe_ids.{mode}.json` at startup, cached in memory. Mode from `STRIPE_MODE` env var. See §B.2. |
| Should the seed script populate Stripe IDs? | **No** — the seed script is the source of truth for tier data. The bootstrap script's `--update-db` flag fills in just the Stripe ID columns. |
| How does pricing change work? | **`--migrate-prices` mode** — detects amount differences, creates new prices, archives old ones. Price-locked tiers excluded. See runbook §8. |
| Should `stripe_ids.test.json` be committed? | **Yes** — test-mode IDs are not secrets. `stripe_ids.live.json` is gitignored. |
| What about the $59→$58.80 rounding difference? | **`--migrate-prices` handles it** — the script config uses the exact spec amounts ($58.80, $178.80). The `--migrate-prices` mode detects the $0.20 difference and creates new prices at the exact amounts. Since no subscriptions exist, this is safe. |
| Should `stripe-pricing-config.md` be archived? | **No** — add a superseded note + cross-reference to the runbook. Retain for pricing rationale (annual vs monthly, 20% premium). |

---

## H. Surface Mockup Reference

**Not applicable.** Backend ops script — no UI surfaces.

---

## I. Component Manifest

**Not applicable.** No frontend components.

---

## Estimate

- **Script implementation**: ~4 hours (5 modes: audit, adopt-existing, create, migrate-prices, update-db; idempotent lookup; mapping file; live guard; existing object reconciliation)
- **Test-mode run + audit + verification**: ~1 hour
- **README + doc updates**: ~30 min
- **Total**: 5–6 hours

---

## Definition of Done

### Phase 1 (script runs successfully in test mode)

- [ ] `backend/scripts/stripe_bootstrap.py` created with all 5 modes
- [ ] `--audit` mode lists existing Stripe objects (2 Products, 4 Prices) and classifies as managed/orphaned
- [ ] `--adopt-existing` mode adds `metadata.pilot_key` to existing Pilot Starter/Teams products + their 4 test-mode prices
- [ ] Default create mode creates: Charter monthly price, Carrier fees product, 2 Meters, 2 overage prices, 2 lane add-on prices
- [ ] Meters created BEFORE metered prices (dependency order)
- [ ] All new objects have `metadata.pilot_key` for idempotent lookup
- [ ] `stripe_ids.test.json` emitted with all 14 object IDs (3 products + 2 meters + 9 prices, including existing IDs)
- [ ] Script is idempotent — re-running produces the same IDs (no duplicates)
- [ ] `--dry-run` works (shows what would be created without calling Stripe API)
- [ ] `--i-am-sure` guard prevents accidental live-mode runs
- [ ] `README-stripe-bootstrap.md` created with usage instructions
- [ ] `stripe-pricing-config.md` updated with superseded note + runbook cross-reference

### Phase 2 (DB update + migration + verification)

- [ ] `--update-db` populates `subscription_tier.stripe_price_id_monthly`/`stripe_price_id_annual` for all 4 tiers
- [ ] `--migrate-prices` creates new prices at exact spec amounts ($58.80, $178.80) and archives old ones ($59.00, $179.00)
- [ ] `stripe_ids.test.json` committed to git
- [ ] `stripe_ids.live.json` added to `.gitignore`
- [ ] `ruff check --fix && ruff format` on changed files — zero issues
- [ ] `pytest -m unit` passes (no new tests — ops script)

---

*End of batch design. Engineer prompt will be authored as `batch-c-b3-python-engr-prompt.md` after Tom approval.*
