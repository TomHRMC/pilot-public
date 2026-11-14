> **📦 ARCHIVED 2026-08-20 — REMEDIATION TRACKED HERE IS COMPLETE.** This 2026-06-15 status summary recorded "Phase 0.8 remediation pending implementation"; that remediation (and Phase 0.9) has since landed. The living seed-system authority is `backend/README-seed-data.md` (2026-08-18 — 20-script inventory, env-aware seeds, §7 gotchas). Archived to `dev-docs/seed-data/archived/` per Tom's decision. **Frozen reference — do not update.**

---

# Seed Data System — Analysis & Status Summary v1.0

**Created**: 2026-06-15  
**Analyst**: Pilot Architect  
**Session scope**: Analysis of seed scripts, live DB state, and gap identification conducted 2026-06-08 through 2026-06-15  
**Status**: Phase 0.8 remediation pending implementation

---

## Table of Contents

1. [Context: Where Seed Data Fits in the Workstream Plan](#1-context-where-seed-data-fits-in-the-workstream-plan)
2. [What Was Delivered (Steps 1 & 2 — Completed)](#2-what-was-delivered-steps-1--2--completed)
3. [Live DB State — Verified 2026-06-08](#3-live-db-state--verified-2026-06-08)
4. [Gaps Found in Post-Delivery Analysis](#4-gaps-found-in-post-delivery-analysis)
5. [Phase 0.8 Remediation — What Needs To Happen](#5-phase-08-remediation--what-needs-to-happen)
6. [Phase 0.7.3 Step 3 — Dev DB Population](#6-phase-073-step-3--dev-db-population)
7. [Seed Script Reference](#7-seed-script-reference)
8. [Key Decision Log](#8-key-decision-log)

---

## 1. Context: Where Seed Data Fits in the Workstream Plan

The full context lives in `pilot-app-pre-wkstm-3-prep-plan.md`. Summary of where we stand:

| Phase | Description | Status |
|---|---|---|
| Phase 0.1–0.6 | DB state inventory, strategy, seed data model, implementation design | ✅ Complete |
| Phase 0.7.1 | Alembic data migrations (13 missing lookup tables + system user + comm templates) | ✅ Complete |
| Phase 0.7.2 | Dev/QA seed scripts (6 scripts) | ✅ Complete |
| **Phase 0.8** | **Post-delivery seed remediation (gaps found 2026-06-08)** | **☐ Pending** |
| Phase 0.7.3 | Run seed scripts → populate dev DB → smoke test UI | ☐ Blocked by 0.8 |
| Phase 1 | Code quality gates (Ruff, TypeScript strict, Cosmic Ray Tier 3–4) | Partially done |
| Phase 2 | E2E harness execution | ☐ Pending Phase 0 |

**Why Phase 0.8 must happen before Phase 0.7.3**: The seed workflow will silently fail in two critical places without the 0.8 fixes. See §4 for details.

**What was already finished before this analysis**: Both beta fix plans (web BETA-B1–B7 and mobile MOB-B0–B5) are fully complete. The UI is functionally done. The only blocker to meaningful beta testing is getting real data into the dev DB.

---

## 2. What Was Delivered (Steps 1 & 2 — Completed)

### Step 1 — Alembic Data Migrations (2026-05-31)

Three migration files delivered in `backend/migrations/versions/`:

| Migration | Revision | Tables / Rows |
|---|---|---|
| `seed_missing_lookup_tables_batch_1` | `dd4ed7ed5f3b` | 21 tables, 73 rows |
| `seed_system_user_sentinel` | `4d035847177f` | 1 row (system user `00000000-0000-0000-0000-000000000000`) |
| `seed_communication_template_gap_fill` | `5ec7fe1e46d8` | 8 rows (4 template types × 2 channels) |

Post-migration DB counts verified for all 21 tables — see §0.7.1 in the prep plan.

**Unit test regression**: 3,691 passed / 0 failed after migrations. 4 test files updated to use get-or-create pattern for globally seeded lookup rows.

### Step 2 — Dev/QA Seed Scripts (2026-06-01)

Six scripts delivered in `backend/migrations/scripts/`:

| Script | Group | Purpose |
|---|---|---|
| `_db_utils.py` | Shared | SQLModel Session context manager |
| `seed_core.py` | A | Re-inserts 20+ lookup tables (schema-only restore recovery) |
| `seed_platform.py` | B | 3 product plans + feature limits + notification templates |
| `seed_test_tenant.py` | C | Test tenant + 3 users + pricing engine + subscription |
| `seed_scenario_quote_to_cash.py` | D | 5 customers + sites + pricebook + draft quote |
| `seed_scenario_dispatch.py` | D | 5 jobs + assignments + PTO block |
| `reset_dev_db.py` | D control | Interactive wipe/reseed panel |

**End-to-end verification run confirmed**: 28 total Group D rows, wipe→reseed cycle clean, test baseline 1 failed / 3,690 passed.

### Deterministic UUIDs (permanent — never reuse)

| Entity | UUID | Email |
|---|---|---|
| Test Tenant | `00000000-0000-0000-0000-000000000001` | — |
| Owner User | `00000000-0000-0000-0000-000000000002` | `dev@pilot.local` |
| Technician User | `00000000-0000-0000-0000-000000000003` | `tech@pilot.local` |
| Office Staff User | `00000000-0000-0000-0000-000000000004` | `office@pilot.local` |

---

## 3. Live DB State — Verified 2026-06-08

Queried via `postgres-local` MCP. Key findings:

### `subscription_status` — 0 rows

The `seed_missing_lookup_tables_batch_1` migration was verified complete on 2026-05-31 with 4 rows. As of 2026-06-08, the table is **empty**. Root cause: either a DB reset cleared the data, or the migration's data was not persistent across environment changes. The table schema is correct; the rows are missing.

```sql
-- Verified 2026-06-08
SELECT code, name FROM public.subscription_status;
-- Result: 0 rows
```

### `subscription_tier.trial` — `product_plan_code = null`

```sql
SELECT tier_name, is_trial, product_plan_code FROM public.subscription_tier;
-- trial | true  | null       ← gap
-- starter | false | starter_plan
-- professional | false | professional_plan
-- enterprise | false | enterprise_plan
```

### `notification_category` — 8 rows (correct, matches seed script)

### `notification_default_policy` — 24 rows (correct, matches seed script)

---

## 4. Gaps Found in Post-Delivery Analysis

Full details with code examples in `seed-data-analysis-fixes-v1.md`.

### Gap 1 — `subscription_status` 0 Rows Breaks Subscription Creation (Critical)

**Effect**: `seed_test_tenant.py` queries `WHERE code = 'active'` before inserting the `subscription` row. With 0 rows, it prints a warning and **silently skips subscription creation**. The test tenant ends up with no `subscription` row — breaking `entitlement_service.py`, `tier_limit_enforcer.py`, and any endpoint that reads subscription state.

**Root cause of omission**: A previous agent removed `subscription_status` from all seed scripts to fix a test UUID conflict. That was the wrong fix — the real fix is to update `conftest.py` to query the seeded row instead of inserting its own.

### Gap 2 — `subscription_tier.trial` Has No `product_plan_code` (Critical)

**Effect**: Trial tenant entitlement resolution via `tenant → subscription_tier → product_plan` returns null for all trial users. The `trial` tier is never mapped in `seed_platform.py` `TIER_TO_PLAN_MAP`.

### Gap 3 — `conftest.py` Inserts Its Own `subscription_status` Rows (Blocks Fix 1)

**Effect**: This is the underlying cause of the original bad removal. `conftest.py` inserts fresh `subscription_status` rows with generated UUIDs at test-time. If persistent rows are added without updating `conftest.py` first, `test_stripe_subscription_lifecycle` will fail again with two `active` rows having different UUIDs.

**Fix order constraint**: Task 8.1 (`conftest.py` change) MUST run before Task 8.2 (adding `subscription_status` to `seed_platform.py`).

### Gap 4 — No Alembic Migration for Production Hardening

`subscription_status` rows need to exist in a migration so production deploys get them automatically via `alembic upgrade head` without requiring a manual seed script run.

### Show/Inspect Mode Gaps (5 found across 4 scripts)

| # | Script | Mode | Gap |
|---|---|---|---|
| 7.1 | `seed_core.py` | `--mode show` | `notification_channel` (4 rows) never printed |
| 7.2 | `seed_core.py` | `--mode inspect` | `notification_category.description` omitted |
| 7.3 | `seed_platform.py` | both | Will need `subscription_status` section after Gap 1 fix |
| 7.4 | `seed_scenario_dispatch.py` | `--mode inspect` | `scheduled_end_at` missing from job output |
| 7.5 | `reset_dev_db.py` | `--mode inspect` | `loto_confirmation` + `calendar_sync_conflict` invisible (but silently wiped) |

---

## 5. Phase 0.8 Remediation — What Needs To Happen

Full checklist with code snippets in `pilot-app-pre-wkstm-3-prep-plan.md` §0.8.

### The 6 Rows for `subscription_status`

These map 1:1 to Stripe's `subscription.status` field handled by `stripe_subscriptions.py`:

| `code` | `name` | `is_billing_active` | Access |
|---|---|:---:|---|
| `trialing` | Trialing | `true` | Full access |
| `active` | Active | `true` | Full access |
| `past_due` | Past Due | `true` | Full access (retrying) |
| `unpaid` | Unpaid | `false` | Revoked |
| `canceled` | Canceled | `false` | Revoked — terminal |
| `paused` | Paused | `false` | Revoked |

### Implementation Order (11 tasks, see §0.8.5 in prep plan)

```
1. Task 8.1 → update conftest.py (query seeded rows, don't insert)
2. Task 8.2 → add 6 subscription_status rows to seed_platform.py
3. Task 8.3 → add "trial": "starter_plan" to TIER_TO_PLAN_MAP
4. Task 8.4 → add subscription_status to mode_show() + mode_inspect() in seed_platform.py
5. Tasks 8.6–8.9 → show/inspect polish (seed_core.py, dispatch, reset_dev_db.py)
6. Run: python migrations/scripts/seed_platform.py
7. Run: python migrations/scripts/seed_test_tenant.py  → subscription row now created
8. Run: pytest — verify zero new failures
9. Task 8.5 → new Alembic migration (production hardening — not dev blocker)
10. Proceed to Phase 0.7.3 Step 3 (smoke tests)
```

### Implementation prompt

`dev-docs/implementation-prompts/seed-data/task-seed-03-phase-0.8-impl.md`

---

## 6. Phase 0.7.3 Step 3 — Dev DB Population

Once Phase 0.8 is complete and `pytest` passes clean, run the following in order:

```bash
cd backend
source .venv/bin/activate

# Step 1 — Verify Alembic is at head
alembic current

# Step 2 — Re-insert all lookup data (no-op if already present from migrations)
python migrations/scripts/seed_core.py

# Step 3 — Platform config (plans + subscription_status after 0.8 fix)
python migrations/scripts/seed_platform.py

# Step 4 — Test tenant + users + pricing engine + subscription
python migrations/scripts/seed_test_tenant.py

# Step 5 — Scenario data
python migrations/scripts/seed_scenario_quote_to_cash.py
python migrations/scripts/seed_scenario_dispatch.py

# Step 6 — Verify
python migrations/scripts/seed_test_tenant.py --mode inspect
python migrations/scripts/reset_dev_db.py --mode inspect
```

**Expected result after Step 6:**

| Table | Expected |
|---|---|
| `subscription_status` | 6 rows |
| `subscription` (test tenant) | 1 row, plan=`starter_plan`, status=`active` |
| `customer` | 5 rows |
| `site` | 3 rows |
| `pricebook_item` | 5 rows |
| `quote` | 1 row (draft) |
| `quote_line` | 2 rows |
| `job` | 5 rows |
| `job_tech_assignment` | 3 rows |
| `tech_availability` | 1 row (PTO block) |
| `labor_rate_version` | 3 rows |
| `tenant_markup_version` | 1 row |

**Smoke tests (all should pass without error):**
- Login as `dev@pilot.local` → dashboard loads
- Navigate to `/customers` → 5 customers visible
- Navigate to `/quotes` → 1 draft quote visible
- Navigate to `/dispatch` → 5 jobs visible on dispatch board
- Navigate to `/settings/billing` → subscription tier visible (Starter)
- Navigate to `/settings/integrations` → renders without crash

---

## 7. Seed Script Reference

### Quick Commands

```bash
cd backend && source .venv/bin/activate

# Run full seed stack (after 0.8 fixes)
python migrations/scripts/seed_platform.py
python migrations/scripts/seed_test_tenant.py
python migrations/scripts/seed_scenario_quote_to_cash.py
python migrations/scripts/seed_scenario_dispatch.py

# Inspect current state
python migrations/scripts/seed_core.py --mode inspect
python migrations/scripts/seed_platform.py --mode inspect
python migrations/scripts/seed_test_tenant.py --mode inspect
python migrations/scripts/reset_dev_db.py --mode inspect

# Reset scenario data (preserve Group A/B/C)
python migrations/scripts/reset_dev_db.py --wipe-only

# Full tenant reset (preserves lookup/platform rows, resets tenant config)
python migrations/scripts/seed_test_tenant.py --reset
python migrations/scripts/seed_test_tenant.py   # re-seed
```

### Script Group Ownership

| Group | Script(s) | Wipes/Reseeds | Never touches |
|---|---|---|---|
| A | `seed_core.py` | — (no wipe) | Everything |
| B | `seed_platform.py` | — (no wipe) | Groups A, C, D |
| C | `seed_test_tenant.py` | `--reset` wipes Group C + D config | Groups A, B |
| D | `seed_scenario_*.py`, `reset_dev_db.py` | `--reset` / `--wipe-only` wipes Group D | Groups A, B, C |

### Known Constraints

| Constraint | Detail |
|---|---|
| Reserved UUIDs | `...0001` through `...0004` are permanently occupied. Future scripts use `gen_random_uuid()`. |
| Open-ended GiST ranges | `tenant_markup_version` and `labor_rate_version` use `[2026-06-01, NULL)` open ranges. No scenario script may insert another open-ended row for the same `(tenant_id, category)`. Use past closed ranges for historical test data. |
| Run order | `seed_platform.py` → `seed_test_tenant.py` → `seed_scenario_*.py`. The subscription row in step 2 requires `product_plan_code` FK from step 1. |
| Test isolation | Tests must scope assertions by inserted IDs, not count all tenant rows. `test_tenant` always has seeded rows; use `second_tenant` for "empty state" tests. |
| `created_at`/`updated_at` | All `StandardAuditMixin` tables have `NOT NULL` without server defaults. Always include `NOW(), NOW()` explicitly in raw SQL INSERTs. |

---

## 8. Key Decision Log

| Decision | Rationale | Reference |
|---|---|---|
| `subscription_status` belongs in `seed_platform.py` (Group B), not `seed_core.py` (Group A) | It's logically platform config (same class as `product_plan`), not a lookup table. Alembic migration owns it for production; seed script is the dev/restore fallback. | §0.8.1 in prep plan |
| `trial` tier maps to `starter_plan` entitlements | Trial tenants get baseline feature limits to enable all UI surfaces. `-1` (unlimited) would be too permissive for billing validation. | §0.8.2 in prep plan |
| `conftest.py` must change BEFORE seed rows are added | Adding persistent rows while `conftest.py` still inserts its own creates two `active` rows → UUID assertion failure in `test_stripe_subscription_lifecycle`. | §0.8.3 in prep plan, Finding 3 in fixes doc |
| `subscription_status` rows: 6 not 4 | Original migration had `trial, active, past_due, canceled`. Analysis added `trialing` (Stripe's pre-active trial state), `unpaid` (retry exhausted), and `paused` (Stripe pause-collection). These are all live Stripe statuses the webhook handler receives. | §0.8.1 in prep plan |
| Show/inspect gaps 7.1–7.5 included in 0.8 scope | Gap 7.5 (`reset_dev_db.py` silent table absence) is operationally significant — data can be silently present but invisible, misleading clean-state verification. | §7 in fixes doc |
| `seed_scenario_customer_comms.py` and `seed_scenario_reporting.py` deferred | Not yet written (as noted in prep plan §0.5). These are not required for Phase 0.7.3 Step 3 smoke tests. Plan when deeper beta testing is needed. | §0.3 in prep plan |
