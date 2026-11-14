# Implementation Prompt: C-B1 (Part A) — Charter Rename Inventory (Backend)

**Mode**: Pilot Python Engineer
**Batch**: C-B1 (Part A — runs first; Part B React Engineer follows after this closes)
**Source plan**: `pilot-launch-plan.md` §2.0 row 14f + §2.1a Order C-1
**Design doc**: `batch-c-b1-design.md`
**Estimated session**: 2–3 hours
**Platform**: Backend only (`backend/`)
**Frontend companion**: C-B1 (Part B — React Engineer, starts after Part A closes)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, and fixture rules
- **`dev-docs/architecture-design/batch-designs/batch-c-b1-design.md`** — the batch design doc (sections A–G)

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 4**: All Alembic migrations must be written as **blank** migrations (never `--autogenerate`). Data changes use raw `op.execute()` with `SET LOCAL session_replication_role = 'replica';`.
- **Rule 11**: If ANY test fails during your work — even one that appears to be a pre-existing failure — **you must fix it before declaring the batch done**. There is no "not my fault" exception.
- **Rule 14 (Ruff)**: Run ruff **only against the files you changed** — `git diff --name-only HEAD -- '*.py'` to get the list, then `ruff check --fix <files> && ruff format <files>`. Fix ALL errors in those files including pre-existing ones.
- **Rule 16 (verify, don't assume)**: 186 tables exist. Query `information_schema.columns` for every table you touch this session before writing SQL.

**This is a pure rename batch.** No new endpoints, no new models, no new columns, no new tables. The only DB change is a data-level UPDATE migration. Do not add features, do not refactor logic, do not "improve" anything you find — rename only.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed. Either confirm with Tom that this is a known, accepted failure, or fix it before touching any batch files.

---

## Pre-Work: Run MCP Verification Queries

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE — all data changes go through the application code, seed scripts, or Alembic migrations. If a query fails → STOP and ask Tom.

Run **all** of these via `postgres-local` MCP before writing any code:

```sql
-- 1. Verify subscription_tier columns (the design doc says tier_name, not code — confirm)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription_tier'
ORDER BY ordinal_position;

-- 2. Verify product_plan columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'product_plan'
ORDER BY ordinal_position;

-- 3. Verify current founders tier row exists
SELECT tier_name, display_label, product_plan_code, is_active
FROM subscription_tier WHERE tier_name = 'founders';

-- 4. Verify current founders_plan product_plan row exists
SELECT code, name, is_active FROM product_plan WHERE code = 'founders_plan';

-- 5. Find ALL tables with a product_plan_code column (FK targets that need updating)
SELECT table_name, column_name
FROM information_schema.columns
WHERE table_schema = 'public' AND column_name = 'product_plan_code'
ORDER BY table_name;

-- 6. Count rows that reference founders_plan (to know the blast radius)
SELECT 'subscription' AS tbl, count(*) FROM subscription WHERE product_plan_code = 'founders_plan'
UNION ALL
SELECT 'product_plan_version', count(*) FROM product_plan_version WHERE product_plan_code = 'founders_plan'
UNION ALL
SELECT 'product_plan_product_feature_version', count(*) FROM product_plan_product_feature_version WHERE product_plan_code = 'founders_plan'
UNION ALL
SELECT 'subscription_tier', count(*) FROM subscription_tier WHERE product_plan_code = 'founders_plan';
```

**Expected results** (verified by Architect 2026-08-02):
- `subscription_tier` has `tier_name` (not `code`), `display_label` (not `display_name`)
- `product_plan` has `code` (PK), `name`, `description`, `is_active`
- 4 tables have `product_plan_code`: `product_plan_product_feature_version`, `product_plan_version`, `subscription`, `subscription_tier`
- `founders` tier exists and is the only active tier
- `founders_plan` product plan exists and is the only active plan

If any of these don't match → use the MCP-returned names, not the design doc's names, and note the discrepancy in your Completion Summary.

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/migrations/scripts/seed_platform.py          ← why: contains founders_plan/founders constants, TIER_TO_PLAN_MAP, PLAN_FEATURE_LIMITS, PRODUCT_PLAN_PRICES
backend/migrations/scripts/seed_test_tenant.py       ← why: contains founders_tier variable, 'founders'/'founders_plan' string literals
backend/services/stripe_subscriptions.py             ← why: contains create_founders_subscription_schedule(), founders_cohort metadata keys
backend/app/models/billing.py                        ← why: contains "founders cohort" comment on stripe_schedule_id column
backend/README-seed-data.md                          ← why: standing reference doc with founders/founders_plan references (§8, §10)
backend/python-engr-std-prompt-inclusions.md         ← why: contains "founders cohort" in mandatory-read instruction (§19)
backend/migrations/versions/2026_07_09_2021-1635c1bf1d1b_mkt_b11_pricing_model_v3_schedule_lanes.py  ← why: reference for migration pattern (DO NOT EDIT — immutable)
backend/tests/domains/subscriptions_usage/test_mkt_b11_pricing_v3.py  ← why: largest test file with founders references
backend/tests/domains/subscriptions_usage/test_sd3_billing_schema.py  ← why: founders_plan price assertions
backend/tests/domains/subscriptions_usage/test_sd07_feature_revision.py ← why: founders_plan existence assertions
backend/tests/domains/subscriptions_usage/test_stripe_b1_subscription_schedule.py ← why: create_founders_subscription_schedule tests
backend/tests/domains/subscriptions_usage/test_stripe_b1_price_id_routing.py ← why: founders tier price ID test
backend/tests/batch_b14/test_a75_subscription_tier_infrastructure.py ← why: founders tier fixture + assertions
backend/tests/batch_tp_b11/test_tp_b11_help_subscription.py ← why: founders tier upgrade test
```

Also run this to confirm the full blast radius:
```bash
cd <repo>/backend
grep -rn -i 'founder\|founding' --include="*.py" . | grep -v __pycache__ | grep -v '.pyc'
```

---

## Context: What This Batch Does

The GTM strategy v3 retires "Founder/Founding Tester/Founding Member/Early Access" in favor of "Charter" (decision D14). This is Part A (backend) of a mixed batch — it must land before Part B (React Engineer) starts, because the frontend references the tier name returned by the API.

**Rename mapping** (from design doc §F):

| Layer | Was | Now |
|---|---|---|
| DB `subscription_tier.tier_name` | `founders` | `charter` |
| DB `subscription_tier.display_label` | `Founders` | `Charter` |
| DB `product_plan.code` | `founders_plan` | `charter_plan` |
| DB `product_plan.name` | `Founders Plan` | `Charter` |
| Backend function | `create_founders_subscription_schedule()` | `create_charter_subscription_schedule()` |
| Stripe metadata | `founders_cohort` | `charter_cohort` |
| Stripe metadata | `founders_free_period` | `charter_free_period` |
| Stripe metadata | `founders_paid_period` | `charter_paid_period` |
| Stripe metadata | `cohort: "founders"` | `cohort: "charter_1"` |

**Do NOT rename** (per design doc §C):
- `backend/tasks/marketing_notifications.py` — "Tom Lang, Founder" refers to Tom, not the plan
- Existing Alembic migration files — git history is immutable
- `backend/migrations/scripts/batch-results/*.txt` — historical inspection logs

---

## Task 1 — Create Alembic Migration

Create a blank migration:

```bash
cd <repo>/backend
source .venv/bin/activate
alembic revision -m "c_b1_charter_rename_founders_to_charter"
```

Write the migration per design doc §B.1. Key points:
- Use `SET LOCAL session_replication_role = 'replica';` at the start of `upgrade()` (disables FK triggers for atomic PK rename)
- UPDATE `product_plan` SET `code = 'charter_plan'`, `name = 'Charter'`, update `description` to the Charter program description
- UPDATE `subscription_tier` SET `tier_name = 'charter'`, `display_label = 'Charter'`, `product_plan_code = 'charter_plan'`
- UPDATE all 4 FK tables: `product_plan_version`, `product_plan_product_feature_version`, `subscription`, `subscription_tier`
- Re-enable: `SET LOCAL session_replication_role = 'origin';`
- Implement `downgrade()` that exactly reverses all UPDATEs
- Test the full cycle: `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head` → `alembic current`

**Intermediate verification:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 2 — Rename Seed Script Constants

File: `backend/migrations/scripts/seed_platform.py`

Rename all `founders`/`Founders`/`founders_plan` references:
- `"code": "founders_plan"` → `"code": "charter_plan"`
- `"name": "Founders Plan"` → `"name": "Charter"`
- `"description": "Time-limited founding member cohort plan..."` → update to Charter description per GTM §6.2
- `TIER_TO_PLAN_MAP`: `"founders": "founders_plan"` → `"charter": "charter_plan"`
- `PLAN_FEATURE_LIMITS`: `"founders_plan"` key → `"charter_plan"`
- `PRODUCT_PLAN_PRICES`: `"founders_plan"` key → `"charter_plan"`
- Tier seed dict: `"tier_name": "founders"` → `"charter"`, `"display_label": "Founders"` → `"Charter"`, `"product_plan_code": "founders_plan"` → `"charter_plan"`
- All comments referencing "founders" → "charter"

---

## Task 3 — Rename Seed Test Tenant References

File: `backend/migrations/scripts/seed_test_tenant.py`

Rename:
- `founders_tier` variable → `charter_tier`
- All `'founders'` string literals in SQL → `'charter'`
- All `'founders_plan'` string literals → `'charter_plan'`
- All comments referencing "founders" → "charter"
- Print statements referencing "founders" → "charter"

---

## Task 4 — Rename Stripe Subscription Service

File: `backend/services/stripe_subscriptions.py`

Rename:
- `create_founders_subscription_schedule()` → `create_charter_subscription_schedule()`
- `handle_subscription_schedule_updated()` — change the metadata check from `"founders_cohort"` to `"charter_cohort"`
- All Stripe metadata keys: `"founders_cohort"` → `"charter_cohort"`, `"founders_free_period"` → `"charter_free_period"`, `"founders_paid_period"` → `"charter_paid_period"`, `"cohort": "founders"` → `"cohort": "charter_1"`
- All log messages and comments referencing "founders" → "charter"

**Important**: Do NOT change the function's behavior — only rename identifiers and string literals.

---

## Task 5 — Update Billing Model Comment

File: `backend/app/models/billing.py`

Update the comment on `stripe_schedule_id`:
- "Stripe Subscription Schedule ID for founders cohort tenants" → "Stripe Subscription Schedule ID for Charter cohort tenants"

---

## Task 6 — Rename All Backend Test References

Rename in all 6 test files:
- `founders_tier` fixture → `charter_tier`
- `tenant_with_founders` fixture → `tenant_with_charter`
- `tier_name == "founders"` → `tier_name == "charter"`
- `display_label == "Founders"` → `display_label == "Charter"`
- `"founders_plan"` → `"charter_plan"`
- `create_founders_subscription_schedule` → `create_charter_subscription_schedule`
- `founders_cohort` → `charter_cohort`
- All assertion strings and comments

**Test files to update:**
1. `backend/tests/batch_b14/test_a75_subscription_tier_infrastructure.py`
2. `backend/tests/batch_tp_b11/test_tp_b11_help_subscription.py`
3. `backend/tests/domains/subscriptions_usage/test_mkt_b11_pricing_v3.py`
4. `backend/tests/domains/subscriptions_usage/test_sd3_billing_schema.py`
5. `backend/tests/domains/subscriptions_usage/test_sd07_feature_revision.py`
6. `backend/tests/domains/subscriptions_usage/test_stripe_b1_subscription_schedule.py`
7. `backend/tests/domains/subscriptions_usage/test_stripe_b1_price_id_routing.py`

**Note**: `backend/tests/batch_b18/test_find103_tenant_tier_override_reason.py` has `"Extended trial per founder approval"` in an override reason string — this is test data, not a code identifier. Update it to `"Extended trial per Charter approval"` for consistency.

**Intermediate verification after each test file:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 7 — Update Seed Data README

File: `backend/README-seed-data.md`

Update all `founders`/`Founders`/`founders_plan` references to `charter`/`Charter`/`charter_plan`:
- §8 table inventory: `subscription_tier` row, `product_plan` row, `product_plan_version` row, `product_plan_product_feature_version` row, `subscription` row
- §10 expected output: `plan=founders_plan` → `plan=charter_plan`

---

## Task 8 — Update Python Engineer Prompt Inclusions

File: `backend/python-engr-std-prompt-inclusions.md`

Update §19 callout:
- "founders cohort Stripe schedule" → "Charter cohort Stripe schedule"

---

## Seed Data Rollout (Core + Scenario)

Per `backend/README-seed-data.md` — read §3 (Group A–D model), §6 (run order), and §7 (DELETE safety rule) before editing any seed script.

### Layer 1 — Core / Platform values (Group A / B)

The Alembic migration (Task 1) renames the `founders`/`founders_plan` rows in-place via UPDATE. The seed script `seed_platform.py` (Task 2) must produce **identical rows** with the new names so that a post-schema-restore reseed is consistent.

After the migration + seed script update, verify:
```bash
cd <repo>/backend
source .venv/bin/activate
python -m migrations.scripts.seed_platform --mode inspect
```

Confirm: `charter_plan` is the only active plan, `charter` is the only active tier.

### Layer 2 — Scenario data (Group D)

`seed_test_tenant.py` (Task 3) references the tier by name. After the rename, it must look up `tier_name = 'charter'` and `product_plan.code = 'charter_plan'`. No scenario data values change — only the lookup keys.

### Verification

After seeding:
```bash
python -m migrations.scripts.seed_platform --mode inspect
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

### README update

Task 7 covers the README-seed-data.md update.

---

## Final Verification

### Phase 1 — Unit Tests Only (run after each task group during development)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before moving to Phase 2.

### Phase 2 — Lint (changed files only) + Full Suite

```bash
cd <repo>/backend
source .venv/bin/activate

# Lint + format gate — CHANGED FILES ONLY
CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py')
if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY
    ruff format $CHANGED_PY
    ruff check $CHANGED_PY
fi

# Full suite including integration tests
python -m pytest --tb=short -q 2>&1 | tail -10

# Batch-specific spot checks
python -m pytest tests/domains/subscriptions_usage/ -v 2>&1 | tail -20

# Verify no founders references remain (excluding do-not-rename files)
grep -rn -i 'founder\|founding' --include="*.py" . | grep -v __pycache__ | grep -v 'marketing_notifications' | grep -v 'migrations/versions/2026_07_'

echo "=== C-B1 (Part A) FINAL VERIFICATION COMPLETE ==="
```

The grep at the end should return **zero results** (all `founder`/`founding` references in `.py` files should be renamed, except `marketing_notifications.py` which refers to Tom, and the two immutable migration files from July).

---

## Definition of Done

Update `pilot-launch-plan.md` §2.0 row 14f status when complete:

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work
- [ ] All MCP pre-work queries run — `subscription_tier` and `product_plan` columns verified, 4 FK tables confirmed
- [ ] All mandatory source files read before writing any code
- [ ] Alembic migration created — data-level UPDATE, `session_replication_role = replica`, `downgrade()` implemented, full cycle tested
- [ ] `seed_platform.py` — all `founders`/`founders_plan` constants/keys/values renamed to `charter`/`charter_plan`
- [ ] `seed_test_tenant.py` — `founders_tier` variable + all string literals renamed
- [ ] `stripe_subscriptions.py` — `create_founders_subscription_schedule()` → `create_charter_subscription_schedule()`, all metadata keys renamed
- [ ] `billing.py` — comment updated
- [ ] All 7 test files — fixtures, assertions, and string literals renamed
- [ ] `README-seed-data.md` — all references updated
- [ ] `python-engr-std-prompt-inclusions.md` — "founders cohort" → "Charter cohort"
- [ ] `ruff check --fix && ruff format` run on changed files only — zero remaining issues
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures
- [ ] `grep -rn -i 'founder\|founding' --include="*.py" .` returns only: `marketing_notifications.py` (Tom) + July migration files (immutable)
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to launch plan

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** subsection to `pilot-launch-plan.md` Appendix B using the format below.
2. Update `pilot-launch-plan.md` §2.0 row 14f status to `✅ Part A (Python) done`.

```markdown
### C-B1 (Part A — Python Engineer) — Charter Rename Inventory: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X passed, Y failed (0 new tests — rename only)

#### What Was Accomplished

- Alembic migration: `founders` → `charter`, `founders_plan` → `charter_plan` (data UPDATE, 4 FK tables updated atomically)
- Seed scripts: all constants/keys/values renamed
- Stripe service: `create_founders_subscription_schedule()` → `create_charter_subscription_schedule()`, metadata keys renamed
- 7 test files: fixtures, assertions, and string literals renamed
- 2 docs updated: README-seed-data.md, python-engr-std-prompt-inclusions.md

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/migrations/versions/2026_08_02_XXXX-XXXX_c_b1_charter_rename.py` | Created — data UPDATE migration |
| `backend/migrations/scripts/seed_platform.py` | Updated — renamed all founders references |
| `backend/migrations/scripts/seed_test_tenant.py` | Updated — renamed founders_tier variable + literals |
| `backend/services/stripe_subscriptions.py` | Updated — renamed function + metadata keys |
| `backend/app/models/billing.py` | Updated — comment |
| `backend/README-seed-data.md` | Updated — all founders references |
| `backend/python-engr-std-prompt-inclusions.md` | Updated — founders cohort → Charter cohort |
| 7 test files | Updated — fixtures, assertions, literals |
```

---

## Handoff Instructions

After Part A is complete and committed:

1. Run `python export_openapi_json.py` — verify the OpenAPI spec still generates cleanly (the `tier_name` data value changed from `"founders"` to `"charter"` but the schema is unchanged).
2. Commit all changes with message: `C-B1 Part A: Charter rename (backend) — founders→charter across DB, services, seeds, tests`
3. Notify the React Engineer that Part A is complete and Part B can begin.
4. `pnpm sync-api-types` is **not needed** — no API shape change, only data values. But the React Engineer should verify their mock data uses `tier_name: "charter"` not `"founders"`.
