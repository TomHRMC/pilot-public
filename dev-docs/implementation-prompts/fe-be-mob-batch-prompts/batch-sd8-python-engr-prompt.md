# Implementation Prompt: SD-8 — Supplier Catalog Expansion + Template Test-Fire QA Tool

**Mode**: Pilot Python Engineer  
**Batch**: SD-8  
**Source plan**: `backend/README-seed-data.md` §10 → SD-8 Scope  
**Design doc**: N/A (self-contained seed + QA tool batch)  
**Estimated session**: 2–3 hours  
**Platform**: Backend only (`backend/`)  
**Frontend companion**: None  

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §16 (Standard Task Workflow), §13 (Alembic rules)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test structure, domain markers, and fixture rules

**Critical rules for this batch:**

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 7**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE.
- **Rule 5**: Never use module-level `TestClient` in any test file. Always use the `client` fixture from `conftest.py`.
- **Rule 11**: If ANY test fails during your work — fix it before declaring the batch done. No "not my fault" exception.
- **Seed safety rule (MANDATORY)**: In `--mode seed` paths, DELETEs must be scoped to the **exact row** being re-inserted — always include the full business key (`supplier_id + sku`, etc.). Never issue a channel- or supplier-scoped DELETE that could wipe rows not owned by this script. See `backend/README-seed-data.md §7` DELETE safety rule.
- **No Alembic migration**: This batch has no schema changes. No migration required.
- **No OpenAPI changes**: This batch has no API endpoint changes. Do not run `export_openapi_json.py`.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> **If any tests are already failing before you start**: Confirm with Tom that this is a known, accepted failure before proceeding. Do NOT start implementation while tests are in an unexplained failed state.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE.

```sql
-- 1. Verify supplier_item live schema — note description and taxability_code columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'supplier_item'
ORDER BY ordinal_position;

-- 2. Verify supplier live schema — confirm website, api_auth_type, api_base_url exist
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'supplier'
ORDER BY ordinal_position;

-- 3. Verify pricing_cache live schema — critical: price_cents (integer), expires_at (NOT NULL)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'pricing_cache'
ORDER BY ordinal_position;

-- 4. Verify supplier_item_price live schema — this is what the current script uses
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'supplier_item_price'
ORDER BY ordinal_position;

-- 5. Confirm current supplier + item counts in test tenant
SELECT s.name, COUNT(si.id) AS item_count
FROM public.supplier s
LEFT JOIN public.supplier_item si ON si.supplier_id = s.id
WHERE s.tenant_id = '00000000-0000-0000-0000-000000000001'
GROUP BY s.name ORDER BY s.name;

-- 6. Confirm supplier_item_category codes available
SELECT code, name FROM public.supplier_item_category ORDER BY code;

-- 7. Confirm supplier_item_uom codes available
SELECT code, name FROM public.supplier_item_uom ORDER BY code;

-- 8. Verify notification_template schema for test_fire_templates.py
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'notification_template'
ORDER BY ordinal_position;

-- 9. Verify email_template schema
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'email_template'
ORDER BY ordinal_position;
```

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/migrations/scripts/seed_scenario_supplier_catalog.py   ← current script to refactor
backend/migrations/scripts/data/supplier_catalog/wesco.json    ← new catalog file (Architect-provided)
backend/migrations/scripts/data/supplier_catalog/graybar.json  ← new catalog file
backend/migrations/scripts/data/supplier_catalog/platt.json    ← new catalog file
backend/migrations/scripts/data/email_templates/invoice_sent.json   ← JSON pattern reference
backend/services/email_template_renderer.py                    ← render_and_send() function to call
backend/services/email_service.py                              ← send_email() signature
backend/migrations/scripts/reset_dev_db.py                     ← to verify supplier_catalog registered
backend/migrations/scripts/_db_utils.py                        ← get_db_session() pattern
backend/README-seed-data.md                                     ← §4 Group D supplier rows, §7 DELETE safety rule
```

Also run:
```bash
grep -rn "supplier_catalog\|supplier_item_price\|pricing_cache" backend/migrations/scripts/ --include="*.py"
```

---

## Background / Context

SD-8 closes the two remaining items from the SD-8 roadmap defined in `README-seed-data.md §10`:

1. **Supplier catalog expansion**: The existing `seed_scenario_supplier_catalog.py` hard-codes 14 items in Python tuples. The Architect has created 3 JSON data files (same pattern as `data/email_templates/`) containing a comprehensive, realistic electrical supply catalog: **25 Wesco items**, **21 Graybar items**, and **21 Platt items** (62 total, with 1 Platt inactive). The script must be refactored to load from these files.

2. **Template test-fire QA tool**: A standalone CLI script (`test_fire_templates.py`) for manually firing email templates against real SendGrid. This is a **QA/dev tool only** — not part of the seed system, not registered in `reset_dev_db.py`, not run by any automated test. It fires one template synchronously using the existing `email_template_renderer.render_and_send()` service. **Email channel only** for this batch; push/in_app/sms support will be added in a later batch.

---

## Task 1 — Refactor `seed_scenario_supplier_catalog.py` to Load from JSON Files

### What to change

Refactor the existing script to:

1. **Remove all hardcoded item tuples** (`SUPPLIER_ITEMS`, `SUPPLIER_2_ITEMS`, `SUPPLIER_3_ITEMS`, `ALL_SUPPLIERS`).
2. **Load supplier definitions from JSON files** in `data/supplier_catalog/*.json` at script startup, sorted alphabetically by filename.
3. **Populate `description` and `taxability_code`** on `supplier_item` inserts — these fields exist on the live table but were never populated by the old script. The JSON files include both.
4. **Add `pricing_cache` rows** for Wesco items after seeding `supplier_item_price` (see §5.1 in gap analysis). `pricing_cache` is keyed by `(tenant_id, supplier_id, sku)` and uses `price_cents` (integer, multiply dollars × 100) and requires a non-null `expires_at` (set to `NOW() + INTERVAL '90 days'` for seed data).
5. **Preserve all existing modes** (`seed`, `inspect`, `show`, `--reset`) — the external interface is unchanged.
6. **`--reset` must wipe `pricing_cache` rows** for the test tenant before wiping supplier items. Add `pricing_cache` to the reset DELETE chain (FK order: `pricing_cache` → `supplier_item_price` → `supplier_item` → `supplier`).
7. **`--mode inspect`** must show `pricing_cache` row counts alongside the existing output.
8. **`--mode show`** must print the loaded JSON item count per supplier (no DB connection).

### JSON loading pattern

```python
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data" / "supplier_catalog"

def _load_supplier_definitions() -> list[dict]:
    """Load all supplier JSON files from data/supplier_catalog/, sorted by filename."""
    definitions = []
    for json_file in sorted(DATA_DIR.glob("*.json")):
        with open(json_file, "r", encoding="utf-8") as f:
            definitions.append(json.load(f))
    return definitions

SUPPLIER_DEFINITIONS = _load_supplier_definitions()
```

### `supplier_item` insert — include new fields

The refactored INSERT must include `description` and `taxability_code`:

```python
db.execute(
    text("""
        INSERT INTO public.supplier_item
        (id, tenant_id, supplier_id, sku, name, description, uom_id, category_id,
         taxability_code, is_active, created_at, updated_at)
        VALUES (gen_random_uuid(), :tid, CAST(:supplier_id AS uuid), :sku, :name, :description,
                CAST(:uom_id AS uuid), CAST(:category_id AS uuid), :taxability_code, :is_active,
                NOW(), NOW())
        RETURNING id
    """),
    {
        "tid": tid,
        "supplier_id": supplier_id,
        "sku": sku,
        "name": item["name"],
        "description": item.get("description"),
        "uom_id": uom_id,
        "category_id": category_id,
        "taxability_code": item.get("taxability_code"),
        "is_active": item.get("is_active", True),
    },
)
```

### `pricing_cache` insert — Wesco items only (initial scope)

After seeding each supplier item's `supplier_item_price`, seed a `pricing_cache` row for Wesco items:

```python
# pricing_cache: keyed by (tenant_id, supplier_id, sku)
# price_cents = int(round(price_dollars * 100))
# expires_at is NOT NULL — use NOW() + INTERVAL '90 days'
# Check: IF the supplier name is "Wesco Distribution", seed pricing_cache row
if supplier_name == "Wesco Distribution":
    price_cents = int(round(item["current_price_dollars"] * 100))
    existing_cache = db.execute(
        text("""
            SELECT id FROM public.pricing_cache
            WHERE tenant_id = :tid AND supplier_id = CAST(:supplier_id AS uuid) AND sku = :sku
        """),
        {"tid": tid, "supplier_id": supplier_id, "sku": sku},
    ).first()
    if not existing_cache:
        db.execute(
            text("""
                INSERT INTO public.pricing_cache
                (tenant_id, supplier_id, sku, price_cents, currency, expires_at, created_at)
                VALUES (:tid, CAST(:supplier_id AS uuid), :sku, :price_cents, 'USD',
                        NOW() + INTERVAL '90 days', NOW())
            """),
            {"tid": tid, "supplier_id": supplier_id, "sku": sku, "price_cents": price_cents},
        )
        print(f"  ✅ [pricing_cache] {sku} → {price_cents}¢")
```

> **MCP gate**: Before writing the `pricing_cache` INSERT, run MCP query #3 above to confirm exact column names. The Architect's prompt uses `supplier_id` and `sku` as the key — verify these are correct column names in the live table.

### `--reset` wipe order (updated)

The reset must delete in this FK order:

```python
# Reset DELETE order: pricing_cache → supplier_item_price → supplier_item → supplier
tables_and_conditions = [
    ("pricing_cache", "supplier_id IN (SELECT id FROM public.supplier WHERE tenant_id = :tid)"),
    ("supplier_item_price", "supplier_item_id IN (SELECT si.id FROM public.supplier_item si JOIN public.supplier s ON s.id = si.supplier_id WHERE s.tenant_id = :tid)"),
    ("supplier_item", "supplier_id IN (SELECT id FROM public.supplier WHERE tenant_id = :tid)"),
    ("supplier", "tenant_id = :tid"),
]
```

### Verification checkpoint after Task 1

```bash
python migrations/scripts/seed_scenario_supplier_catalog.py --mode show
# Expected: prints 3 suppliers with item counts (25, 21, 21)

python migrations/scripts/seed_scenario_supplier_catalog.py --reset
python migrations/scripts/seed_scenario_supplier_catalog.py
# Expected: 3 suppliers, 66 items, 66 prices, ~25 pricing_cache rows (Wesco only)

python migrations/scripts/seed_scenario_supplier_catalog.py --mode inspect
# Expected: shows all 3 suppliers with item counts + pricing_cache count

python -m pytest -m unit --tb=short -q 2>&1 | tail -5
# Expected: same count as baseline, 0 new failures
```

---

## Task 2 — Create `test_fire_templates.py` QA Tool

### What to create

New file: `backend/migrations/scripts/test_fire_templates.py`

This is a **standalone CLI QA tool** — not part of the seed system:
- NOT registered in `reset_dev_db.py`
- NOT called by any test
- NOT called by `seed_e2e_db.py`
- Uses the live SendGrid integration via `services/email_service.py` or `services/email_template_renderer.py`
- Supports `email` channel only (this batch)

### CLI interface

```bash
# Fire a notification_template by type code
python migrations/scripts/test_fire_templates.py \
  --template-type quote_accepted \
  --channel email \
  --recipient tom@pilotfortrades.com \
  --tenant-id 00000000-0000-0000-0000-000000000001

# Fire an email_template by template_id
python migrations/scripts/test_fire_templates.py \
  --email-template invoice_sent \
  --recipient tom@pilotfortrades.com \
  --tenant-id 00000000-0000-0000-0000-000000000001

# Dry run — renders template, prints to stdout, does NOT send
python migrations/scripts/test_fire_templates.py \
  --email-template quote_sent \
  --recipient tom@pilotfortrades.com \
  --dry-run
```

### Arguments

| Argument | Type | Required | Description |
|:---|:---|:---|:---|
| `--template-type` | str | One of these two | `notification_type_code` from `notification_template` table |
| `--email-template` | str | One of these two | `template_id` from `email_template` table (e.g. `invoice_sent`) |
| `--channel` | str | No | Default `email`. Only `email` supported in this batch. |
| `--recipient` | str | Yes | Email address to send to (e.g. `tom@pilotfortrades.com`) |
| `--tenant-id` | str | No | UUID; defaults to `settings.TEST_TENANT_ID` |
| `--dry-run` | flag | No | If set, renders and prints template without sending. |
| `--locale` | str | No | Default `en` — used to select the correct `notification_template` row |

### Implementation pattern

```python
"""
test_fire_templates.py — Manual QA tool for firing notification and email templates.

NOT part of the seed system. NOT run by tests or automation.
Fires one template via SendGrid (email channel only) for QA verification.

Usage:
  python migrations/scripts/test_fire_templates.py --email-template invoice_sent \
      --recipient tom@pilotfortrades.com
  python migrations/scripts/test_fire_templates.py --template-type quote_accepted \
      --channel email --recipient tom@pilotfortrades.com
  python migrations/scripts/test_fire_templates.py --email-template quote_sent \
      --recipient tom@pilotfortrades.com --dry-run
"""

import argparse
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from core.config import settings
from migrations.scripts._db_utils import get_db_session
```

**For `--email-template` mode**: Call `services.email_template_renderer.render_and_send()` directly with test-data variable substitutions. Read the function signature from `email_template_renderer.py` before implementing.

**For `--template-type` (notification_template) mode**: Query the `notification_template` table for `notification_type_code = :code AND channel = 'email' AND locale = :locale`, then call `services.email_service.send_email()` directly with the resolved `subject` and `body`.

**Variable substitution**: Use a hardcoded test-data context dict for rendering. The script should NOT attempt to load real entity data from the DB — it renders with placeholder values that make the email readable in an inbox:

```python
TEST_RENDER_CONTEXT = {
    "customer_name": "Tom Lang (Test Send)",
    "company_name": "Pilot Dev Tenant",
    "company_domain": "pilotfortrades.com",
    "invoice_total": "955.96",
    "invoice_url": "https://app.pilotfortrades.com/invoices/test-preview",
    "due_date": "2026-08-22",
    "quote_number": "QUO-900004",
    "quote_url": "https://app.pilotfortrades.com/quotes/test-preview",
    "quote_total": "1200.00",
    "job_title": "Panel Upgrade — Test Send",
    "scheduled_date": "2026-08-01",
    "scheduled_time": "9:00 AM",
    "tech_name": "Alex (Tech User)",
}
```

**Print output (always, even without `--dry-run`)**:

```
=== test_fire_templates.py ===
Template type : email_template / invoice_sent
Channel       : email
Recipient     : tom@pilotfortrades.com
Tenant        : 00000000-0000-0000-0000-000000000001
Dry run       : False

[RENDERED SUBJECT]
Invoice from Pilot Dev Tenant — $955.96 due 2026-08-22

[RENDERED BODY (first 200 chars)]
Hi Tom Lang (Test Send),

Your invoice from Pilot Dev Tenant is ready to view and pay online...

Sending via SendGrid...
✅ Send result: {'status': 'sent', 'http_status': 202}
```

**Error handling**: If `--template-type` or `--email-template` is not found in the DB, print a clear error message and exit with code 1. If SendGrid fails, print the error dict and exit with code 1. Never raise unhandled exceptions.

**Channel guard**: If `--channel` is anything other than `email`, print:
```
❌ Only 'email' channel is supported in this version. Push/in_app/sms support will be added later.
```
...and exit with code 1.

### Verification checkpoint after Task 2

```bash
# Verify dry-run works without SendGrid credentials
python migrations/scripts/test_fire_templates.py \
  --email-template invoice_sent \
  --recipient tom@pilotfortrades.com \
  --dry-run
# Expected: prints rendered subject + body, shows "[DRY RUN — not sent]"

python migrations/scripts/test_fire_templates.py \
  --email-template invoice_sent \
  --recipient tom@pilotfortrades.com
# Expected: sends email via SendGrid and prints ✅ Send result

# Verify error case
python migrations/scripts/test_fire_templates.py \
  --email-template nonexistent_template \
  --recipient tom@pilotfortrades.com
# Expected: prints "❌ email_template 'nonexistent_template' not found" and exits 1

python -m pytest -m unit --tb=short -q 2>&1 | tail -5
# Expected: same count as baseline (new script has no tests — it's a QA tool)
```

---

## Task 3 — Update `README-seed-data.md`

Update the following sections in `backend/README-seed-data.md`:

### §2 Script Inventory — `migrations/scripts/` table

Add a new row for `test_fire_templates.py` (under the existing inventory, after `reset_dev_db.py`):

```markdown
| `migrations/scripts/test_fire_templates.py` | QA Tool | Manual template test-fire — email channel only; `--dry-run` supported; NOT part of seed system | No |
```

Also add a note to the `data/email_templates/` row to reference the new `data/supplier_catalog/` directory:
```
| `migrations/scripts/data/supplier_catalog/*.json` | — | Supplier catalog data files: wesco.json (25 items), graybar.json (21 items), platt.json (21 items, 1 inactive) | — |
```

### §4 Group D — Supplier Catalog scenario

Update the supplier catalog table to reflect the expanded item counts:

| Table | Rows | Data | Notes |
|:---|:---:|:---|:---|
| `supplier` | 3 | Wesco Distribution, Graybar Electric, Platt Electric Supply | **SD-8**: `website`, `api_auth_type`, `api_base_url` populated via JSON |
| `supplier_item` | **67** | Wesco: 25 items; Graybar: 21 items; Platt: 21 items (1 inactive — discontinued 60W bulb) | **SD-8**: Loaded from JSON files; `description` and `taxability_code` now populated |
| `supplier_item_price` | **67** | One current price row per item (open-ended valid_period) | **SD-8**: Prices match JSON `current_price_dollars` |
| `pricing_cache` | **~25** | Wesco items only — `price_cents` + 90-day `expires_at` | **SD-8**: New |

### §10 Roadmap — Mark SD-8 Complete

Replace the existing SD-8 roadmap entry stub with the completion block (format matching SD-6/SD-7 entries). The Python Engineer will fill in the actual baseline/final counts and files changed.

---

## Test Requirements

This batch adds **no new API endpoints** and **no new SQLModel classes**. The `test_fire_templates.py` is a CLI QA tool — no automated tests are required or desired for it (it requires a live SendGrid connection).

The refactored `seed_scenario_supplier_catalog.py` is a seed script — no unit tests are written for seed scripts by convention.

**Required verification**: After running the seeder, confirm with `--mode inspect` that item counts match the JSON files. Run the full unit test suite to confirm zero regressions.

---

## Final Verification

### Phase 1 — Unit Tests Only (run after each task during development)

```bash
cd <repo>/backend
source .venv/bin/activate

python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass. Fix any failure before moving to the next task.

### Phase 2 — Full Suite (run once, at the very end, before DoD sign-off)

```bash
cd <repo>/backend
source .venv/bin/activate

# Full suite
python -m pytest --tb=short -q 2>&1 | tail -10

# Seed script smoke test
python migrations/scripts/seed_scenario_supplier_catalog.py --reset
python migrations/scripts/seed_scenario_supplier_catalog.py
python migrations/scripts/seed_scenario_supplier_catalog.py --mode inspect

# QA tool smoke test (dry run — no real send)
python migrations/scripts/test_fire_templates.py \
  --email-template invoice_sent \
  --recipient tom@pilotfortrades.com \
  --dry-run

echo "=== SD-8 FINAL VERIFICATION COMPLETE ==="
```

> **Any failure in either phase must be fixed before declaring SD-8 done.**

---

## Definition of Done

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed (or confirmed with Tom)
- [ ] All 9 MCP pre-work queries run and results match expectations
- [ ] All mandatory source files read before writing any code
- [ ] **Task 1**: `seed_scenario_supplier_catalog.py` refactored to load from JSON files
- [ ] **Task 1**: All 3 JSON files load correctly — 25 Wesco, 21 Graybar, 21 Platt items
- [ ] **Task 1**: `supplier_item` INSERT now populates `description` and `taxability_code`
- [ ] **Task 1**: `pricing_cache` rows seeded for all Wesco items (~25 rows)
- [ ] **Task 1**: `--reset` correctly wipes `pricing_cache` before `supplier_item_price`
- [ ] **Task 1**: `--mode inspect` shows pricing_cache row count
- [ ] **Task 1**: `--mode show` prints item count per supplier from JSON (no DB)
- [ ] **Task 2**: `test_fire_templates.py` created in `migrations/scripts/`
- [ ] **Task 2**: `--dry-run` flag renders and prints without sending
- [ ] **Task 2**: `--email-template` mode renders and sends via SendGrid
- [ ] **Task 2**: `--template-type` mode queries `notification_template` and sends via SendGrid
- [ ] **Task 2**: Non-email channel returns clear error and exits 1
- [ ] **Task 2**: Unknown template returns clear error and exits 1
- [ ] **Task 3**: `README-seed-data.md` §2 updated with `test_fire_templates.py` entry + data dir note
- [ ] **Task 3**: `README-seed-data.md` §4 Group D supplier rows updated with correct counts
- [ ] **Task 3**: `README-seed-data.md` §10 SD-8 entry marked ✅ Complete with completion block
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `README-seed-data.md §10`

---

## Completion Summary

After all Definition of Done items are complete, add a **Completion Summary** subsection to `backend/README-seed-data.md` §10 under the SD-8 heading using the format below:

```markdown
### SD-8 — Supplier Catalog Expansion + Template Test-Fire QA Tool ✅ Complete (YYYY-MM-DD)

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests — note: 0 expected for this batch)

#### What Was Accomplished

- Refactored `seed_scenario_supplier_catalog.py` to load from JSON data files (same pattern as `data/email_templates/`)
- Expanded catalog from 14 to 67 items: Wesco (25), Graybar (21), Platt (21 active + 1 inactive)
- `supplier_item.description` and `.taxability_code` now populated from JSON
- `pricing_cache` seeded for all 25 Wesco items with 90-day TTL
- Created `test_fire_templates.py` standalone QA tool — email channel only; `--dry-run` supported
- Updated `README-seed-data.md` §2, §4, §10

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/migrations/scripts/seed_scenario_supplier_catalog.py` | Updated — JSON-driven loader, description/taxability_code fields, pricing_cache seeding |
| `backend/migrations/scripts/test_fire_templates.py` | Created — QA tool for manual template test-fire |
| `backend/migrations/scripts/data/supplier_catalog/wesco.json` | Created (Architect-provided — do not modify) |
| `backend/migrations/scripts/data/supplier_catalog/graybar.json` | Created (Architect-provided — do not modify) |
| `backend/migrations/scripts/data/supplier_catalog/platt.json` | Created (Architect-provided — do not modify) |
| `backend/README-seed-data.md` | Updated — §2, §4, §10 |
```

---

## After This Batch — Next Step

SD-8 closes the last two items in the SD-8 roadmap. The next seed data work is **SD-7 Batch 2** (notification pipeline + mobile + usage metering), which is tracked separately. After SD-8, check `backend/README-seed-data.md §10` for the current SD-7 Batch 2 status.
