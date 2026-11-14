# Implementation Prompt: C-B3 — Stripe Bootstrap Script (Products, Prices, Meters)

**Mode**: Pilot Python Engineer
**Batch**: C-B3
**Source plan**: `pilot-launch-plan.md` §2.0 row 14h + §2.1a Order C-3
**Design doc**: `batch-c-b3-design.md`
**Estimated session**: 5–6 hours
**Platform**: Backend only (`backend/`)
**Frontend companion**: None

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document
- **`dev-docs/architecture-design/batch-designs/batch-c-b3-design.md`** — the batch design doc (sections A–G)
- **`dev-docs/integrations/stripe/stripe-ops-runbook.md`** — the Stripe operational reference (account structure, existing objects, script usage, testing approach)
- **`dev-docs/integrations/stripe/stripe-pricing-config.md`** — the existing manual Dashboard setup (confirmed price IDs, metadata patterns)

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify before use.
- **Rule 11**: If ANY test fails during your work — fix it before declaring the batch done.
- **Rule 14 (Ruff)**: Run ruff only against changed files: `CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')` then `ruff check --fix $CHANGED_PY && ruff format $CHANGED_PY && ruff check $CHANGED_PY`.
- **Rule 16 (verify, don't assume)**: Query `information_schema.columns` for every table you touch.

**This is an ops script, not application code.** No new endpoints, no new models, no Alembic migration. The script calls the Stripe API to create/adopt objects and emits a JSON mapping file.

**Stripe API version**: Pin to `2025-03-31.basil` or later. Legacy usage-records billing was removed — every metered price must reference a Billing Meter. `SubscriptionItem.create_usage_record()` is dead.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the count. This batch doesn't add tests (ops script), but the baseline must still pass at the end.

---

## Pre-Work: Run MCP Verification Queries

```sql
-- Confirm stripe_price_id columns and current values
SELECT tier_name, stripe_price_id_monthly, stripe_price_id_annual FROM subscription_tier ORDER BY display_order;
-- Expected: charter has NULL; starter/teams have existing test-mode price IDs
```

---

## Pre-Work: Read These Source Files

```
backend/services/stripe_subscriptions.py     ← why: existing Stripe service — understand current patterns
backend/app/models/subscription.py            ← why: SubscriptionTier model — has stripe_price_id columns
backend/migrations/scripts/seed_platform.py  ← why: tier seed data — understand current pricing
backend/.env.example                          ← why: STRIPE_SECRET_KEY env var pattern
dev-docs/integrations/stripe/stripe-pricing-config.md      ← why: existing price IDs (§4) + metadata patterns
dev-docs/integrations/stripe/stripe-ops-runbook.md        ← why: the operational reference for this script
dev-docs/architecture-design/batch-designs/batch-c-b3-design.md ← why: the batch design doc
```

Also verify the Stripe Python library is installed:
```bash
pip show stripe | head -3
```

---

## Context: What This Batch Does

Creates `backend/scripts/stripe_bootstrap.py` — an idempotent script that manages all Stripe objects for the Pilot subscription billing model. The script has 5 modes:

1. **`--audit`** — read-only report of existing Stripe objects vs. what the script would create
2. **`--adopt-existing`** — add `metadata.pilot_key` to existing manually-created objects
3. **create (default)** — create missing objects (Charter price, pass-through product, meters, overage prices, lane add-ons)
4. **`--update-db`** — write generated price IDs to `subscription_tier` columns
5. **`--migrate-prices`** — detect amount changes, create new prices, archive old ones (for future use)

Plus `--dry-run` (preview) and `--i-am-sure` (live-mode guard).

### Existing objects (already in Stripe — adopt, don't duplicate)

2 Products (Pilot Starter, Pilot Teams) + 8 Prices (4 test + 4 live) were created manually via Dashboard. They use `lookup_key` metadata. The script adopts them by adding `metadata.pilot_key`. See design doc §F.2 for the exact adoption mapping.

### New objects to create

| Object | Key | Details |
|---|---|---|
| Charter monthly price | `price_charter_monthly` | $49.00/mo on Starter product, metadata: `{pilot_key, tier_name: charter, price_locked: true, cohort: charter_1}` |
| Carrier fees product | `prod_passthrough` | "Carrier fees (pass-through)" |
| Voice AI minutes meter | `meter_voice_minutes` | event: `voice_minutes`, sum aggregation, by_id customer mapping |
| SMS segments meter | `meter_sms_segments` | event: `sms_segments`, sum aggregation, by_id customer mapping |
| Voice overage price | `price_voice_overage` | $0.05/min, metered, references `meter_voice_minutes` |
| SMS overage price | `price_sms_overage` | $0.05/segment, metered, references `meter_sms_segments` |
| Lane add-on +1 | `price_lane_addon_1` | $10.00/mo, quantity-based |
| Lane add-on +5 | `price_lane_addon_5` | $40.00/mo, quantity-based |

**Meters must be created BEFORE metered prices** — the overage prices reference the meter IDs.

### Pricing (all rounded to whole dollars per Tom's decision 2026-08-04)

| Price | Amount |
|---|---|
| Charter monthly | $49.00/mo (4900¢) |
| Starter monthly | $59.00/mo (5900¢) — existing, adopted |
| Starter annual | $588.00/yr (58800¢) — existing, adopted |
| Teams monthly | $179.00/mo (17900¢) — existing, adopted |
| Teams annual | $1,788.00/yr (178800¢) — existing, adopted |
| Voice overage | $0.05/min (5¢) |
| SMS overage | $0.05/segment (5¢) |
| Lane add-on +1 | $10.00/mo (1000¢) |
| Lane add-on +5 | $40.00/mo (4000¢) |

---

## Task 1 — Create `backend/scripts/` directory

```bash
mkdir -p backend/scripts
touch backend/scripts/__init__.py
```

---

## Task 2 — Write `stripe_bootstrap.py`

File: `backend/scripts/stripe_bootstrap.py`

The script must implement all 5 modes. Read the design doc §F.1 for the exact CLI interface and §F.2-F.3 for the object definitions.

### Key implementation requirements:

1. **API key selection**: `--mode test` reads `STRIPE_SECRET_KEY` env var (must be `sk_test_...`). `--mode live` reads `STRIPE_LIVE_SECRET_KEY` env var (must be `sk_live_...`) and requires `--i-am-sure`.

2. **Idempotent lookup**: Before creating any object, search by `metadata.pilot_key`. If found, reuse. If not, create.

3. **`--audit` mode**: List all Products, Prices, and Meters in the Stripe account. Classify each as:
   - **managed** — has `metadata.pilot_key` (the script owns it)
   - **orphaned** — no `pilot_key` (created manually via Dashboard)
   Print a summary table. Do NOT make any changes.

4. **`--adopt-existing` mode**: For each existing object that matches by name (Products) or `lookup_key` (Prices), add `metadata.pilot_key` via `stripe.Product.modify()` / `stripe.Price.modify()`. Do NOT change amounts or create new objects.

   Adoption mapping (from design doc §F.2):
   - Pilot Starter product → `pilot_key: prod_starter`
   - Pilot Teams product → `pilot_key: prod_teams`
   - Price with `lookup_key: pilot_starter_monthly` → `pilot_key: price_starter_monthly`
   - Price with `lookup_key: pilot_starter_annual` → `pilot_key: price_starter_annual`
   - Price with `lookup_key: pilot_teams_monthly` → `pilot_key: price_teams_monthly`
   - Price with `lookup_key: pilot_teams_annual` → `pilot_key: price_teams_annual`

5. **Create mode (default)**: Create only missing objects. Order: Products → Meters → Prices (meters before metered prices). All objects get `metadata.pilot_key`.

6. **`--update-db` mode**: After creating/adopting, write the price IDs to `subscription_tier.stripe_price_id_monthly`/`stripe_price_id_annual` columns via SQL UPDATE. Use the `DATABASE_URL` env var for the connection.

7. **`--migrate-prices` mode**: For each price in the script config, look up by `pilot_key`. If the amount differs from the config, create a new Price, archive the old one (`active=false`), update the JSON file + DB. Exclude price-locked tiers (Charter — filter on `price_locked=true` in tier config).

8. **`--dry-run` mode**: Print what would be created/modified without calling the Stripe API.

9. **Output file**: After any mode that creates or adopts objects, emit `stripe_ids.{mode}.json` with all 14 object IDs (3 products + 2 meters + 9 prices). Include existing IDs alongside new ones.

### Script structure (starting point — adjust to match what you find):

```python
#!/usr/bin/env python3
"""Stripe Bootstrap Script — creates/adopts Products, Prices, and Meters.

Usage:
    python scripts/stripe_bootstrap.py --mode test --audit
    python scripts/stripe_bootstrap.py --mode test --adopt-existing
    python scripts/stripe_bootstrap.py --mode test
    python scripts/stripe_bootstrap.py --mode test --update-db
    python scripts/stripe_bootstrap.py --mode test --migrate-prices
    python scripts/stripe_bootstrap.py --mode test --dry-run
    python scripts/stripe_bootstrap.py --mode live --i-am-sure
"""
import argparse
import json
import os
import sys
from pathlib import Path

import stripe

# Pin API version
stripe.api_version = "2025-03-31.basil"

# Object definitions — the source of truth for what should exist
PRODUCTS = {
    "prod_starter": {"name": "Pilot for Trades — Starter", "description": "..."},
    "prod_teams": {"name": "Pilot for Trades — Teams", "description": "..."},
    "prod_passthrough": {"name": "Carrier fees (pass-through)", "description": "..."},
}

METERS = {
    "meter_voice_minutes": {"display_name": "Voice AI minutes", "event_name": "voice_minutes", ...},
    "meter_sms_segments": {"display_name": "SMS segments", "event_name": "sms_segments", ...},
}

PRICES = {
    "price_charter_monthly": {"product": "prod_starter", "amount": 4900, "recurring": "month", "metadata": {...}},
    "price_starter_monthly": {"product": "prod_starter", "amount": 5900, "recurring": "month", "metadata": {...}},
    # ... 7 more
}

# Existing objects to adopt (lookup_key → pilot_key)
ADOPTION_MAP = {
    # Products: lookup by name
    "Pilot Starter": "prod_starter",
    "Pilot Teams": "prod_teams",
    # Prices: lookup by lookup_key metadata
    "pilot_starter_monthly": "price_starter_monthly",
    "pilot_starter_annual": "price_starter_annual",
    "pilot_teams_monthly": "price_teams_monthly",
    "pilot_teams_annual": "price_teams_annual",
}
```

Read the design doc §F.2-F.3 for the complete object definitions and metadata.

---

## Task 3 — Run `--audit` mode

```bash
cd <repo>/backend
source .venv/bin/activate
python scripts/stripe_bootstrap.py --mode test --audit
```

Verify the output shows:
- 2 existing Products (Pilot Starter, Pilot Teams) — classified as orphaned
- 4 existing test-mode Prices — classified as orphaned
- 0 existing Meters
- Report of what the script would create (5 new objects)

---

## Task 4 — Run `--adopt-existing` mode

```bash
python scripts/stripe_bootstrap.py --mode test --adopt-existing
```

Verify:
- 2 Products adopted (pilot_key metadata added)
- 4 Prices adopted (pilot_key metadata added)
- No new objects created

---

## Task 5 — Run create mode (default)

```bash
python scripts/stripe_bootstrap.py --mode test
```

Verify:
- Charter monthly price created on Starter product ($49.00/mo)
- Carrier fees product created
- 2 Meters created (voice_minutes, sms_segments)
- 2 overage prices created (referencing meters)
- 2 lane add-on prices created
- `stripe_ids.test.json` emitted with all 14 IDs

Re-run to verify idempotency:
```bash
python scripts/stripe_bootstrap.py --mode test
# Should produce the same IDs — no duplicates created
```

---

## Task 6 — Run `--update-db`

```bash
python scripts/stripe_bootstrap.py --mode test --update-db
```

Verify via MCP:
```sql
SELECT tier_name, stripe_price_id_monthly, stripe_price_id_annual FROM subscription_tier ORDER BY display_order;
-- charter should now have the charter_monthly price ID
-- starter/teams should have their adopted price IDs
```

---

## Task 7 — Write README

File: `backend/scripts/README-stripe-bootstrap.md`

Document:
- The 5 modes + `--dry-run` + `--i-am-sure`
- The workflow (audit → adopt → create → update-db)
- The output file format
- The environment variables needed
- Cross-reference to `stripe-ops-runbook.md`

---

## Task 8 — Update `stripe-pricing-config.md`

File: `dev-docs/integrations/stripe/stripe-pricing-config.md`

Add a header note:
```markdown
> **⚠️ SUPERSEDED by the bootstrap script (C-B3)**: The manual Dashboard process below is superseded by `backend/scripts/stripe_bootstrap.py`. This doc is retained as a historical reference for the pricing model decisions. For the current operational process, see `stripe-ops-runbook.md`.
```

---

## Task 9 — Gitignore live IDs

File: `backend/.gitignore`

Add:
```
scripts/stripe_ids.live.json
```

Commit `stripe_ids.test.json` (test-mode IDs are not secrets).

---

## Final Verification

### Phase 1 — Script runs successfully

```bash
cd <repo>/backend
source .venv/bin/activate

# Verify the script runs in all modes
python scripts/stripe_bootstrap.py --mode test --audit
python scripts/stripe_bootstrap.py --mode test --dry-run

# Verify the JSON file exists and has all 14 IDs
python -c "
import json
ids = json.load(open('scripts/stripe_ids.test.json'))
assert len(ids['products']) == 3, f'Expected 3 products, got {len(ids[\"products\"])}'
assert len(ids['meters']) == 2, f'Expected 2 meters, got {len(ids[\"meters\"])}'
assert len(ids['prices']) == 9, f'Expected 9 prices, got {len(ids[\"prices\"])}'
print('✅ All 14 Stripe object IDs present')
"

# Verify DB was updated
python -c "
from sqlalchemy import create_engine, text
import os
engine = create_engine(os.environ['DATABASE_URL'])
with engine.connect() as conn:
    result = conn.execute(text('SELECT tier_name, stripe_price_id_monthly FROM subscription_tier WHERE tier_name = :tn'), {'tn': 'charter'})
    row = result.first()
    assert row and row[1] is not None, 'Charter tier has no stripe_price_id_monthly'
    print(f'✅ Charter stripe_price_id_monthly = {row[1]}')
"
```

### Phase 2 — Lint + unit tests

```bash
# Lint changed files only
CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')
if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY
    ruff format $CHANGED_PY
    ruff check $CHANGED_PY
fi

# Unit tests must still pass (no new tests — ops script)
python -m pytest -m unit --tb=short -q 2>&1 | tail -10

echo "=== C-B3 FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done

Update `pilot-launch-plan.md` §2.0 row 14h status when complete:

- [ ] Pre-modification regression baseline captured
- [ ] All MCP pre-work queries run
- [ ] All mandatory source files read (including runbook + pricing config)
- [ ] `backend/scripts/stripe_bootstrap.py` created with all 5 modes + `--dry-run` + `--i-am-sure`
- [ ] `--audit` mode lists existing objects and classifies as managed/orphaned
- [ ] `--adopt-existing` mode adds `metadata.pilot_key` to existing 2 Products + 4 Prices
- [ ] Create mode creates 5 new objects (Charter price, pass-through product, 2 meters, 2 overage prices, 2 lane add-ons)
- [ ] Meters created BEFORE metered prices (dependency order)
- [ ] All new objects have `metadata.pilot_key` for idempotent lookup
- [ ] `stripe_ids.test.json` emitted with all 14 object IDs (3 products + 2 meters + 9 prices)
- [ ] Script is idempotent — re-running produces the same IDs
- [ ] `--dry-run` works (no Stripe API calls)
- [ ] `--i-am-sure` guard prevents accidental live-mode runs
- [ ] `--update-db` populates `subscription_tier.stripe_price_id_monthly`/`stripe_price_id_annual` for all 4 tiers
- [ ] `README-stripe-bootstrap.md` created
- [ ] `stripe-pricing-config.md` updated with superseded note
- [ ] `stripe_ids.test.json` committed; `stripe_ids.live.json` gitignored
- [ ] `ruff check --fix && ruff format` on changed files — zero issues
- [ ] `pytest -m unit` passes — zero failures
- [ ] Completion Summary added to launch plan

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** to `pilot-launch-plan.md` Appendix B.
2. Update `pilot-launch-plan.md` §2.0 row 14h status to `✅ COMPLETE`.

```markdown
### C-B3 — Stripe Bootstrap Script: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X passed, Y failed (0 new tests — ops script)

#### What Was Accomplished

- `stripe_bootstrap.py` created with 5 modes: --audit, --adopt-existing, create, --update-db, --migrate-prices
- 2 existing Products + 4 existing Prices adopted (metadata.pilot_key added)
- 5 new objects created: Charter monthly price, Carrier fees product, 2 Billing Meters, 2 overage prices, 2 lane add-on prices
- `stripe_ids.test.json` emitted with all 14 object IDs
- DB updated: all 4 tiers have stripe_price_id_monthly/annual populated
- `stripe-pricing-config.md` marked as superseded
- `stripe_ids.live.json` gitignored

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/scripts/stripe_bootstrap.py` | Created — idempotent bootstrap script with 5 modes |
| `backend/scripts/__init__.py` | Created — package init |
| `backend/scripts/stripe_ids.test.json` | Created — 14 Stripe object IDs (committed) |
| `backend/scripts/README-stripe-bootstrap.md` | Created — usage documentation |
| `backend/.gitignore` | Updated — added `scripts/stripe_ids.live.json` |
| `dev-docs/integrations/stripe/stripe-pricing-config.md` | Updated — superseded note + runbook cross-reference |
```

---

## Handoff Instructions

After C-B3 is complete and committed:

1. Commit with message: `C-B3: Stripe bootstrap script — adopt existing + create missing objects + stripe_ids.test.json`
2. Notify that C-B4 (Stripe subscription creation + webhooks) can begin — it depends on C-B3 ✅.
3. C-B4 will create `core/stripe_config.py` to load `stripe_ids.{mode}.json` at runtime.
4. The `stripe_ids.test.json` file must be committed so all developers have the same mapping.
