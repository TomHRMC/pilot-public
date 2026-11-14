# Batch MKT-B11 — DB Design Doc: Pricing Model v3.0 (Schedule Lanes)

**Status**: ⏳ AWAITING TOM APPROVAL — do not begin Part B until approved  
**Date**: July 9, 2026  
**Author**: Pilot Architect  
**Revision**: v1.2 — Tom feedback applied July 9, 2026 (second pass). Trial inactive; enterprise deleted entirely; data_exports feature removed; 9 ppfv rows; Founders upgrade path resolved.

> **Scope of this doc**: Part A only — the full DB design spec for the Python Engineer to implement. Parts B–E (engineer prompts) will be written after Tom approves this doc.

---

## Table of Contents

- [Batch MKT-B11 — DB Design Doc: Pricing Model v3.0 (Schedule Lanes)](#batch-mkt-b11--db-design-doc-pricing-model-v30-schedule-lanes)
  - [Table of Contents](#table-of-contents)
  - [A. Input Read Summary](#a-input-read-summary)
  - [B. Migration Plan](#b-migration-plan)
    - [B.1 Pre-Migration DB State (MCP Verified)](#b1-pre-migration-db-state-mcp-verified)
    - [B.2 What Changes and How](#b2-what-changes-and-how)
    - [B.3 Migration Steps — Ordered](#b3-migration-steps--ordered)
    - [B.4 Target State After Migration](#b4-target-state-after-migration)
  - [C. Execution Order](#c-execution-order)
  - [D. New API Endpoints](#d-new-api-endpoints)
  - [E. Pattern Reuse Decisions](#e-pattern-reuse-decisions)
  - [F. Shared Module Interfaces](#f-shared-module-interfaces)
    - [F.1 — Application Code Cleanup: Feature Code References](#f1--application-code-cleanup-feature-code-references)
    - [F.2 — Lane Enforcement Helper (New or Updated)](#f2--lane-enforcement-helper-new-or-updated)
    - [F.3 — `seed_platform.py` Constants Rewrite](#f3--seed_platformpy-constants-rewrite)
    - [F.4 — `seed_test_tenant.py` Subscription Plan](#f4--seed_test_tenantpy-subscription-plan)
  - [G. Open Questions Resolved](#g-open-questions-resolved)
  - [Appendix — JSON Schema File Update Checklist](#appendix--json-schema-file-update-checklist)

---

## A. Input Read Summary

| Input | Key Finding |
|---|---|
| `dev-docs/db-design/postgres-mcp-guide.md` | MCP query patterns confirmed; all queries filtered by `table_schema = 'public'` |
| `dev-docs/architecture-design/pilot-architect-methods.md` §3 | Standard Architecture Design Workflow §A–G followed |
| `dev-docs/product-requirements/mvp-prd.md` §3.11 | Schedule Lanes = concurrent job slot; Trial = hard-cap tier (inactive until general release); Founders = $0 (6 mo free) → $49 locked at Starter limits forever |
| `dev-docs/marketing-analysis/gtm-pricing-strategy-v1.md` D1–D15 | Founders/Trial/Starter/Teams; Enterprise removed; overage 5¢/min and 5¢/seg; data exports unlimited and untracked |
| `dev-docs/marketing-analysis/gtm-feature-tier-matrix-v1.md` §1, §2.1 | Lane counts: Founders=5, Trial=5, Starter=5, Teams=20; add-on +1=$10, +5=$40 |
| MCP: `subscription_tier` live rows | 4 stale rows — all wrong. No `schedule_lanes` column. |
| MCP: `product_plan` live rows | 3 rows: `starter_plan`, `teams`, `enterprise_plan`. No `founders_plan`. |
| MCP: `product_feature` live rows | 4 rows including stale `dispatch_slots` (→ delete) and `data_exports` (→ delete, not tracked). |
| MCP: `product_plan_product_feature_version` | 12 stale open rows — all wrong values. All deleted. |
| MCP: `product_plan_version` | 3 stale rows with `price_cents=0`. `teams` plan missing its version entirely. |
| MCP: GiST constraint `pppfv_no_overlap` | EXCLUDE USING gist on `(product_plan_code, product_feature_code, valid_period &&)`. Deleting stale rows means no GiST conflict on new INSERTs. |
| MCP: FKs on ppfv | FK to `product_feature(code)`. Delete ppfv rows before deleting feature rows. |
| `seed_platform.py` / `seed_test_tenant.py` | Stale constants throughout. Full rewrite of data constants required. |

---

## B. Migration Plan

### B.1 Pre-Migration DB State (MCP Verified)

**`subscription_tier` — current 4 stale rows:**

| tier_name | price_cents | is_trial | max_users | is_active | schedule_lanes | product_plan_code |
|---|---|---|---|---|---|---|
| `trial` | 0 | true | 5 ⚠️ | true | *(missing)* ⚠️ | `starter_plan` |
| `starter` | **14,900** ⚠️ | false | **5** ⚠️ | true | *(missing)* ⚠️ | `starter_plan` |
| `professional` | 24,900 ⚠️ | false | **15** ⚠️ | true | *(missing)* ⚠️ | **`professional_plan`** ⚠️ |
| `enterprise` | 44,900 | false | 50 ⚠️ | true | *(missing)* ⚠️ | `enterprise_plan` |

**`product_plan` — current 3 stale rows:**

| code | is_active |
|---|---|
| `starter_plan` | true |
| `teams` | true |
| `enterprise_plan` | true |

**`product_feature` — current 4 rows (2 being deleted):**

| code | unit | status |
|---|---|---|
| `voice_ai_minutes` | minutes | ✅ keep |
| `data_exports` | count | ❌ delete — not tracked/charged |
| `dispatch_slots` | slots | ❌ delete — replaced by `schedule_lanes` |
| `outbound_sms_segments` | segments | ✅ keep |

**`product_plan_product_feature_version` — 12 stale open rows (all deleted).**

**`product_plan_version` — 3 stale rows (all price=0, all deleted).**

---

### B.2 What Changes and How

> **Assumption**: Dev DB with no real tenant data. Delete stale rows and columns. Clean slate. Python Engineer fixes any broken tests and API endpoints as part of this batch.

| # | Table | Current | Action | Method |
|---|---|---|---|---|
| 1 | `subscription_tier` | 4 wrong rows | Delete all 4; insert 4 correct rows | DELETE + INSERT |
| 2 | `subscription_tier.max_users` | Unused, misleading | **DROP column** | `ALTER TABLE DROP COLUMN` |
| 3 | `subscription_tier.max_sms_segments_per_month` | Always NULL, redundant | **DROP column** | `ALTER TABLE DROP COLUMN` |
| 4 | `subscription_tier` | Missing `schedule_lanes` | **ADD `schedule_lanes INT NOT NULL`** | `ALTER TABLE ADD COLUMN` (safe after rows deleted) |
| 5 | `product_plan` | No `founders_plan` | INSERT `founders_plan` | INSERT |
| 6 | `product_plan.starter_plan.is_active` | true | false (dormant until general release) | UPDATE |
| 7 | `product_plan.teams.is_active` | true | false (dormant until general release) | UPDATE |
| 8 | `product_plan.enterprise_plan` | exists | **DELETE row entirely** | DELETE |
| 9 | `product_feature.data_exports` | active | **DELETE row** (after ppfv rows deleted) | DELETE |
| 10 | `product_feature.dispatch_slots` | active | **DELETE row** (after ppfv rows deleted) | DELETE |
| 11 | `product_feature.schedule_lanes` | does not exist | INSERT new row | INSERT |
| 12 | `product_plan_product_feature_version` | 12 stale rows | **DELETE all** | DELETE |
| 13 | `product_plan_product_feature_version` | missing correct rows | INSERT **9 correct rows** (3 plans × 3 features) | INSERT |
| 14 | `product_plan_version` | 3 stale rows | **DELETE all** | DELETE |
| 15 | `product_plan_version` | missing correct rows | INSERT 3 rows: founders_plan, starter_plan, teams | INSERT |

> **Why only 3 features (no `data_exports`)**: Data exports are unlimited and untracked on all plans. No metering, no charging, no overage. Tracking them via `usage_ledger` and `product_plan_product_feature_version` adds complexity with zero business value. Remove the feature entirely from the entitlement system.

---

### B.3 Migration Steps — Ordered

> All Alembic migrations must be idempotent. Use `IF EXISTS`, `IF NOT EXISTS`, and existence-check guards throughout.

---

#### STEP 1 — Delete ppfv and ppv stale rows (clear FK dependencies first)

```sql
-- Clear all stale ppfv rows (covers dispatch_slots, data_exports, voice_ai_minutes, sms for all plans)
DELETE FROM public.product_plan_product_feature_version;

-- Clear all stale ppv rows
DELETE FROM public.product_plan_version;
```

---

#### STEP 2 — Delete stale feature rows; insert `schedule_lanes`

```sql
-- Delete dispatch_slots and data_exports (ppfv rows already gone)
DELETE FROM public.product_feature WHERE code IN ('dispatch_slots', 'data_exports');

-- Insert schedule_lanes
INSERT INTO public.product_feature
(code, name, unit, description, is_active, created_at, updated_at)
VALUES
('schedule_lanes', 'Schedule Lanes', 'lanes',
 'Concurrent job slots on the dispatch board. One lane = one parallel scheduling row. Any user can be assigned to jobs in any lane.',
 true, NOW(), NOW())
ON CONFLICT (code) DO NOTHING;
```

---

#### STEP 3 — Rebuild `product_plan` (add founders_plan; set inactive; delete enterprise_plan)

```sql
-- Add founders_plan
INSERT INTO public.product_plan
(code, name, description, is_active, created_at, updated_at)
VALUES
('founders_plan', 'Founders Plan',
 'Time-limited founding member cohort plan. 6 months free, then $49/mo locked at Starter limits for life.',
 true, NOW(), NOW())
ON CONFLICT (code) DO NOTHING;

-- Set starter_plan and teams to inactive (dormant until general release)
UPDATE public.product_plan
SET is_active = false, updated_at = NOW()
WHERE code IN ('starter_plan', 'teams');

-- Delete enterprise_plan entirely
DELETE FROM public.product_plan WHERE code = 'enterprise_plan';
```

> **`product_plan.is_active` = marketing site page switch flag:**  
> `founders_plan.is_active=true` → Founders page renders (CTA: "Join as a Founding Member")  
> `starter_plan.is_active=true` → Regular release pricing page renders (Starter/Teams cards)  
> Tom flips these flags via direct DB update — zero code deploy required.

---

#### STEP 4 — Rebuild `subscription_tier`

```sql
-- Delete all stale subscription_tier rows
DELETE FROM public.subscription_tier;

-- Drop unused columns
ALTER TABLE public.subscription_tier DROP COLUMN IF EXISTS max_users;
ALTER TABLE public.subscription_tier DROP COLUMN IF EXISTS max_sms_segments_per_month;

-- Add schedule_lanes column (table is now empty — NOT NULL safe)
ALTER TABLE public.subscription_tier
ADD COLUMN IF NOT EXISTS schedule_lanes INTEGER NOT NULL DEFAULT 0;

-- Insert 4 correct v3.0 tier rows
INSERT INTO public.subscription_tier
(tier_id, tier_name, display_label, monthly_price_cents, is_trial,
 trial_duration_days, is_active, display_order, schedule_lanes,
 product_plan_code, created_at, updated_at)
VALUES
-- founders: free, 6 months (Stripe trial), Starter limits, ACTIVE (open for Founding Member signups)
(gen_random_uuid(), 'founders', 'Founders', 0, false,
 NULL, true, 0, 5, 'founders_plan', NOW(), NOW()),

-- trial: 14-day hard-cap, Starter limits, INACTIVE (turns on when Starter/Teams go live)
(gen_random_uuid(), 'trial', 'Trial', 0, true,
 14, false, 1, 5, 'starter_plan', NOW(), NOW()),

-- starter: $49/mo, INACTIVE until general release
(gen_random_uuid(), 'starter', 'Starter', 4900, false,
 NULL, false, 2, 5, 'starter_plan', NOW(), NOW()),

-- teams: $149/mo, INACTIVE until general release
(gen_random_uuid(), 'teams', 'Teams', 14900, false,
 NULL, false, 3, 20, 'teams', NOW(), NOW());
```

> **Trial `is_active=false`**: Trial only makes sense when Starter or Teams are live and a customer can convert to a paid plan. During the Founders cohort period, new signups go directly to the `founders` tier. When Tom flips `starter_plan.is_active=true` for general release, he also flips `trial.is_active=true` at the same time. The two flags are flipped together.

> **Enterprise tier**: Removed entirely. No row inserted.

> **`founders.monthly_price_cents = 0`**: The 6-month free period is the entry price. The post-free-period $49 locked price lives in `product_plan_version.price_cents = 4900`. Stripe handles the free period via subscription trial; when trial ends, Stripe bills $49/mo. Founders stay on `founders_plan` forever at $49 — they do not convert to `starter_plan`.

---

#### STEP 5 — Insert 9 correct `product_plan_product_feature_version` rows

```sql
-- ── founders_plan × 3 features ────────────────────────────────────────────
INSERT INTO public.product_plan_product_feature_version
(product_plan_code, product_feature_code, limit_quantity, included_quantity,
 overage_price_cents, limit_enforcement, valid_period, recorded_at, created_at)
VALUES
-- schedule_lanes: block enforcement (add-ons write to tenant_product_feature_override)
('founders_plan', 'schedule_lanes', 5, 5, NULL, 'block', tstzrange(NOW(), NULL), NOW(), NOW()),
-- voice_ai_minutes: 90 min, $0.05/min overage, soft cap
('founders_plan', 'voice_ai_minutes', 90, 90, 5, 'soft', tstzrange(NOW(), NULL), NOW(), NOW()),
-- outbound_sms_segments: 100 segs, $0.05/seg overage, soft cap
('founders_plan', 'outbound_sms_segments', 100, 100, 5, 'soft', tstzrange(NOW(), NULL), NOW(), NOW());

-- ── starter_plan × 3 features ─────────────────────────────────────────────
INSERT INTO public.product_plan_product_feature_version
(product_plan_code, product_feature_code, limit_quantity, included_quantity,
 overage_price_cents, limit_enforcement, valid_period, recorded_at, created_at)
VALUES
('starter_plan', 'schedule_lanes', 5, 5, NULL, 'block', tstzrange(NOW(), NULL), NOW(), NOW()),
('starter_plan', 'voice_ai_minutes', 90, 90, 5, 'soft', tstzrange(NOW(), NULL), NOW(), NOW()),
('starter_plan', 'outbound_sms_segments', 100, 100, 5, 'soft', tstzrange(NOW(), NULL), NOW(), NOW());

-- ── teams × 3 features ────────────────────────────────────────────────────
INSERT INTO public.product_plan_product_feature_version
(product_plan_code, product_feature_code, limit_quantity, included_quantity,
 overage_price_cents, limit_enforcement, valid_period, recorded_at, created_at)
VALUES
('teams', 'schedule_lanes', 20, 20, NULL, 'block', tstzrange(NOW(), NULL), NOW(), NOW()),
('teams', 'voice_ai_minutes', 300, 300, 5, 'soft', tstzrange(NOW(), NULL), NOW(), NOW()),
('teams', 'outbound_sms_segments', 500, 500, 5, 'soft', tstzrange(NOW(), NULL), NOW(), NOW());
```

> **`chk_pppfv_overage_price_required_when_soft`** constraint: requires `overage_price_cents IS NOT NULL` when `limit_enforcement = 'soft'`. All soft rows supply `overage_price_cents = 5`. `schedule_lanes` uses `block` enforcement so `NULL` overage is permitted.

---

#### STEP 6 — Insert 3 correct `product_plan_version` rows

```sql
INSERT INTO public.product_plan_version
(product_plan_code, name, price_cents, valid_period, recorded_at, created_at)
VALUES
-- founders_plan: $49/mo locked price (post-6-month free period; free period = Stripe trial)
('founders_plan', 'Founders Plan', 4900, tstzrange(NOW(), NULL), NOW(), NOW()),
-- starter_plan: $49/mo
('starter_plan', 'Starter Plan', 4900, tstzrange(NOW(), NULL), NOW(), NOW()),
-- teams: $149/mo (was entirely missing from live DB)
('teams', 'Teams Plan', 14900, tstzrange(NOW(), NULL), NOW(), NOW());
```

---

#### STEP 7 — `tenant_product_feature_override` — Schedule Lane Add-On Mechanism

No schema migration required. Existing columns cover the need: `tenant_id`, `product_feature_code`, `limit_quantity`, `enabled`.

**Add-On Purchase Logic** (Python Engineer implementation):

When a tenant purchases a lane add-on:
1. Read tenant's base lanes from `ppfv.limit_quantity` where `product_feature_code = 'schedule_lanes'`
2. Read any existing `tenant_product_feature_override` row for `schedule_lanes`
3. Calculate `new_total = base_lanes + all_purchased_add_on_lanes`
4. Upsert `tenant_product_feature_override`: `limit_quantity = new_total`

**Lane Enforcement Query Spec** (called at job-scheduling time):

```sql
SELECT COALESCE(
  (
    SELECT tpfo.limit_quantity
    FROM public.tenant_product_feature_override tpfo
    WHERE tpfo.tenant_id = :tid
      AND tpfo.product_feature_code = 'schedule_lanes'
      AND tpfo.enabled = true
  ),
  (
    SELECT ppfv.limit_quantity
    FROM public.product_plan_product_feature_version ppfv
    JOIN public.subscription s ON s.product_plan_code = ppfv.product_plan_code
    WHERE s.tenant_id = :tid
      AND s.is_active = true
      AND ppfv.product_feature_code = 'schedule_lanes'
      AND ppfv.valid_period @> NOW()
  )
) AS effective_lanes;
```

**Add-On Pricing Reference** (Stripe catalog, not in DB):

| Add-On | Lanes Added | Monthly Price |
|---|---|---|
| Single lane | +1 | $10/mo |
| Lane pack | +5 | $40/mo |

---

### B.4 Target State After Migration

**`subscription_tier` — 4 rows:**

> Columns: `tier_id`, `tier_name`, `display_label`, `monthly_price_cents`, `is_trial`, `trial_duration_days`, `is_active`, `display_order`, `schedule_lanes`, `stripe_price_id`, `product_plan_code`, `created_at`, `updated_at`, `created_by`, `updated_by`  
> **Dropped**: `max_users`, `max_sms_segments_per_month`  
> **Added**: `schedule_lanes INT NOT NULL`

| tier_name | display_label | price_cents | is_trial | schedule_lanes | **is_active** | display_order | product_plan_code |
|---|---|---|---|---|---|---|---|
| `founders` | Founders | 0 | false | 5 | **true** | 0 | `founders_plan` |
| `trial` | Trial | 0 | true | 5 | **false** | 1 | `starter_plan` |
| `starter` | Starter | 4,900 | false | 5 | **false** | 2 | `starter_plan` |
| `teams` | Teams | 14,900 | false | 20 | **false** | 3 | `teams` |

**`product_plan` — 3 rows (enterprise deleted):**

| code | name | is_active |
|---|---|---|
| `founders_plan` | Founders Plan | **true** |
| `starter_plan` | Starter Plan | **false** |
| `teams` | Teams Plan | **false** |

**`product_feature` — 3 rows (dispatch_slots + data_exports deleted):**

| code | name | unit | is_active |
|---|---|---|---|
| `voice_ai_minutes` | Voice AI minutes | minutes | true |
| `outbound_sms_segments` | Outbound SMS Segments | segments | true |
| `schedule_lanes` | Schedule Lanes | lanes | true |

**`product_plan_product_feature_version` — 9 new open rows:**

| plan_code | feature_code | limit_qty | incl_qty | overage_cents | enforcement |
|---|---|---|---|---|---|
| `founders_plan` | `schedule_lanes` | 5 | 5 | NULL | block |
| `founders_plan` | `voice_ai_minutes` | 90 | 90 | 5 | soft |
| `founders_plan` | `outbound_sms_segments` | 100 | 100 | 5 | soft |
| `starter_plan` | `schedule_lanes` | 5 | 5 | NULL | block |
| `starter_plan` | `voice_ai_minutes` | 90 | 90 | 5 | soft |
| `starter_plan` | `outbound_sms_segments` | 100 | 100 | 5 | soft |
| `teams` | `schedule_lanes` | 20 | 20 | NULL | block |
| `teams` | `voice_ai_minutes` | 300 | 300 | 5 | soft |
| `teams` | `outbound_sms_segments` | 500 | 500 | 5 | soft |

**`product_plan_version` — 3 new open rows:**

| product_plan_code | name | price_cents | valid_period |
|---|---|---|---|
| `founders_plan` | Founders Plan | 4,900 | [2026-07-09, ∞) |
| `starter_plan` | Starter Plan | 4,900 | [2026-07-09, ∞) |
| `teams` | Teams Plan | 14,900 | [2026-07-09, ∞) |

---

## C. Execution Order

| Step | Task | Table(s) | Type | Dependency |
|---|---|---|---|---|
| 1 | Delete all ppfv and ppv rows | `product_plan_product_feature_version`, `product_plan_version` | Alembic migration | None |
| 2 | Delete `dispatch_slots` + `data_exports`; insert `schedule_lanes` | `product_feature` | Data migration | Step 1 (FK clear) |
| 3 | Insert `founders_plan`; set starter/teams inactive; delete `enterprise_plan` | `product_plan` | Data migration | Step 2 |
| 4 | Delete all subscription_tier rows; drop `max_users` + `max_sms_segments_per_month`; add `schedule_lanes`; insert 4 correct rows | `subscription_tier` | Alembic migration | Step 3 (product_plan_code FK) |
| 5 | Insert 9 correct ppfv rows | `product_plan_product_feature_version` | Data migration | Step 2, 3 |
| 6 | Insert 3 correct ppv rows | `product_plan_version` | Data migration | Step 3 |
| 7 | Grep + replace `dispatch_slots` → `schedule_lanes`; remove `data_exports` references from all application code | `backend/app`, `backend/services`, `backend/api` | Code change | Step 2 |
| 8 | Update `seed_platform.py` constants | Python source | Code change | Step 5, 6 |
| 9 | Update `seed_test_tenant.py` subscription logic | Python source | Code change | Step 8 |
| 10 | Fix any broken tests (removed columns, renamed feature code, removed plans) | `backend/tests` | Code change | Step 7, 8, 9 |
| 11 | Run `python schema_manager.py set` for each modified table | JSON schema | Tool run | Step 10 |
| 12 | Run `pytest -m unit --tb=no -q` — zero new failures | Tests | Verification | Step 11 |

---

## D. New API Endpoints

No new endpoints. Existing endpoints return updated DB data automatically.

The Python Engineer must verify these existing endpoints return correct v3.0 data after migration:

| Endpoint | Expected Response After Migration |
|---|---|
| `GET /api/v1/subscription-tiers?active_only=true` | Returns only `founders` tier (`is_active=true`). Trial, starter, teams excluded. |
| `GET /api/v1/subscription-tiers` | All 4 tiers; includes `schedule_lanes` field; no `max_users` or `max_sms_segments_per_month` |
| `GET /api/v1/product-plans?active_only=true` | Returns only `founders_plan` |
| `GET /api/v1/entitlements` | Returns `schedule_lanes` as feature code; no `dispatch_slots` or `data_exports` |

> **⚠️ Schema change alert**: `schedule_lanes` added; `max_users` + `max_sms_segments_per_month` dropped; feature codes `dispatch_slots` + `data_exports` removed. Python Engineer regenerates `openapi.json` via `python export_openapi_json.py`. React Engineer runs `pnpm sync-api-types` before any frontend work.

---

## E. Pattern Reuse Decisions

| Pattern (from `mvp-arch.md` §16) | Applied Where |
|---|---|
| **Two-Tier Configuration (System-Default / Tenant-Override)** | `tenant_product_feature_override` for lane add-ons. System default = plan lane count (ppfv `limit_quantity`). Tenant override = purchased add-on total. Enforcement: `COALESCE(override, ppfv_limit)`. |
| **Append-Only Temporal Versioning** | `product_plan_version` and `product_plan_product_feature_version` are append-only. In this batch, old rows are deleted (dev DB). In production, close-then-insert would apply. New rows use open `valid_period`. |
| **Data-Driven Tier Configuration** | Tier metadata entirely in DB. Marketing page switch = DB flag flip (`product_plan.is_active`). No hardcoded tier names, prices, or limits in application code. |
| **Idempotent Migrations** | All Alembic migration steps use `IF EXISTS` / `IF NOT EXISTS` guards and `ON CONFLICT DO NOTHING` on INSERTs. |

---

## F. Shared Module Interfaces

### F.1 — Application Code Cleanup: Feature Code References

The Python Engineer must search for and remove all references to the deleted feature codes:

```bash
# Find and replace dispatch_slots → schedule_lanes
grep -r "dispatch_slots" backend/app backend/services backend/api backend/tasks --include="*.py"

# Find and remove data_exports feature references (usage tracking, entitlement checks)
grep -r "data_exports" backend/app backend/services backend/api backend/tasks --include="*.py"
```

Every `dispatch_slots` occurrence → replace with `schedule_lanes`.  
Every `data_exports` entitlement check → remove (data exports are now unlimited and untracked).

### F.2 — Lane Enforcement Helper (New or Updated)

Implement in `backend/services/` (or update existing entitlement service):

```python
def get_effective_schedule_lanes(tenant_id: UUID, db: Session) -> int:
    """
    Returns effective lane count for tenant:
      1. Check tenant_product_feature_override for 'schedule_lanes' (add-ons)
      2. Fall back to plan ppfv limit_quantity
    Returns int. Raises 500 if no lane config found (misconfigured plan).
    """
```

### F.3 — `seed_platform.py` Constants Rewrite

Full rewrite of `PRODUCT_PLANS`, `TIER_TO_PLAN_MAP`, and `PLAN_FEATURE_LIMITS` in `backend/migrations/scripts/seed_platform.py`:

```python
PRODUCT_PLANS = [
    {
        "code": "founders_plan",
        "name": "Founders Plan",
        "description": "Time-limited founding member cohort plan. 6 months free, then $49/mo locked at Starter limits for life.",
        "is_active": True,
    },
    {
        "code": "starter_plan",
        "name": "Starter Plan",
        "description": "For solo contractors starting out",
        "is_active": False,  # dormant until general release
    },
    {
        "code": "teams",
        "name": "Teams Plan",
        "description": "For growing contractors and small teams",
        "is_active": False,  # dormant until general release
    },
    # enterprise_plan: removed — do not seed
]

TIER_TO_PLAN_MAP = {
    "founders": "founders_plan",
    "trial": "starter_plan",   # trial uses starter_plan entitlements
    "starter": "starter_plan",
    "teams": "teams",
}

# feature_code → {limit, overage_cents (None if block enforcement), enforcement}
PLAN_FEATURE_LIMITS = {
    "founders_plan": {
        "schedule_lanes":        {"limit": 5,   "overage_cents": None, "enforcement": "block"},
        "voice_ai_minutes":      {"limit": 90,  "overage_cents": 5,    "enforcement": "soft"},
        "outbound_sms_segments": {"limit": 100, "overage_cents": 5,    "enforcement": "soft"},
    },
    "starter_plan": {
        "schedule_lanes":        {"limit": 5,   "overage_cents": None, "enforcement": "block"},
        "voice_ai_minutes":      {"limit": 90,  "overage_cents": 5,    "enforcement": "soft"},
        "outbound_sms_segments": {"limit": 100, "overage_cents": 5,    "enforcement": "soft"},
    },
    "teams": {
        "schedule_lanes":        {"limit": 20,  "overage_cents": None, "enforcement": "block"},
        "voice_ai_minutes":      {"limit": 300, "overage_cents": 5,    "enforcement": "soft"},
        "outbound_sms_segments": {"limit": 500, "overage_cents": 5,    "enforcement": "soft"},
    },
}
```

The `mode_seed()` logic must be updated to use the new dict structure (with `enforcement` and `overage_cents` keys per feature, not a flat int).

### F.4 — `seed_test_tenant.py` Subscription Plan

Update the subscription seeding section of `backend/migrations/scripts/seed_test_tenant.py` to explicitly use `founders_plan`:

```python
# Use founders_plan explicitly (not "first active plan alphabetically")
plan_row = db.execute(
    text("SELECT code FROM public.product_plan WHERE code = 'founders_plan' LIMIT 1")
).first()
```

---

## G. Open Questions Resolved

| # | Question | Resolution |
|---|---|---|
| **G.1** | `dispatch_slots` rename: UPDATE in-place or new feature + delete old? | **Delete old + insert new.** FK from ppfv has no ON UPDATE CASCADE. Delete ppfv rows for `dispatch_slots` first, then delete the feature row, then insert `schedule_lanes`. All application code greps replace `dispatch_slots` → `schedule_lanes`. |
| **G.2** | `data_exports`: keep or remove from entitlement system? | **Remove entirely.** Data exports are unlimited and untracked on all plans. No metering, no charging. Delete the `product_feature` row and all ppfv rows. Remove entitlement checks from application code. |
| **G.3** | `professional` tier and `enterprise` tier: how to handle? | **Delete both.** `professional` is replaced by the correct `teams` tier row. `enterprise` is removed at v3.0. Dev DB — no compatibility needed. |
| **G.4** | `max_users` and `max_sms_segments_per_month` columns: update or drop? | **Drop both columns.** Unlimited users is a permanent architectural invariant. SMS limits live in ppfv. Both columns were never correctly populated. Drop them. |
| **G.5** | Trial tier `is_active`: true or false? | **false**. Trial only makes sense when Starter or Teams are live and a customer can convert to a paid plan. During the Founders cohort period, all new signups use the `founders` tier. When Tom flips `starter_plan.is_active=true` for general release, he flips `trial.is_active=true` at the same time via the same DB update. |
| **G.6** | `schedule_lanes` ppfv `limit_enforcement`: `'soft'` or `'block'`? | **`'block'`**. The CHECK constraint `chk_pppfv_overage_price_required_when_soft` requires `overage_price_cents IS NOT NULL` when enforcement is soft. Lanes are a discrete resource, not per-overage billed. `block` means "stop scheduling when lanes are full." Add-on purchases write `tenant_product_feature_override.limit_quantity` to unlock more lanes. |
| **G.7** | Founders `product_plan_version.price_cents`: 0 or 4900? | **4900**. Founders stay on `founders_plan` forever at $49/mo. The 6-month free period = Stripe subscription trial. When Stripe trial ends, it bills $49/mo against this plan version. `subscription_tier.monthly_price_cents = 0` reflects "free at signup time" only. |
| **G.8** | Founders upgrade path: can Founders upgrade to Teams? And at what price? | **Founders stay on `founders_plan` at $49/mo for life — Starter limits only.** The lock is on the price AND the feature set (Starter limits). If a Founder's business grows to need 20 lanes or 300 Voice AI minutes, they upgrade to Teams at the full $149/mo. Reasons: (1) D11 explicitly says "Starter limits for life." (2) Giving Founders Teams limits at $49 creates a $100/mo permanent subsidy that distorts economics — Teams customers pay $149 for the same thing. (3) The upgrade conversation is clean and honest: "Your Founding Member plan gives you 5 lanes at $49. You've outgrown that — Teams is $149 for 20 lanes." That is a value sell, not a bait-and-switch. Note: until Teams features beyond limits (recurring jobs, live GPS map, etc.) ship, the upsell is primarily about lane/minute/SMS capacity, which is sufficient justification for the $100 delta for a business with 6+ concurrent jobs. |
| **G.9** | `enterprise_plan` in `product_plan`: deactivate (`is_active=false`) or delete? | **Delete the row entirely.** Enterprise is removed at v3.0 with no plan to re-enable it as a separate tier. Keeping a dormant row adds confusion. Dev DB — clean slate. |
| **G.10** | `professional_plan` orphaned ppv row: what to do? | **Deleted** in Step 1 (DELETE all ppv rows). Gone. |
| **G.11** | Marketing page switch when transitioning from Founders to general release: how does it work? | Tom executes four DB updates together: (1) `UPDATE product_plan SET is_active=true WHERE code IN ('starter_plan', 'teams')` — activates Starter/Teams plans for marketing page switch; (2) `UPDATE product_plan SET is_active=false WHERE code = 'founders_plan'` — closes Founders plan to new signups; (3) `UPDATE subscription_tier SET is_active=true WHERE tier_name IN ('trial', 'starter', 'teams')` — enables Trial/Starter/Teams tiers in signup flow; (4) **`UPDATE subscription_tier SET is_active=false WHERE tier_name = 'founders'`** — closes Founders tier to new signups. All 4 must run together. Existing Founders customers are unaffected — their `tenant.current_subscription_tier_id` and `subscription.product_plan_code` are unchanged; their billing, feature limits, and locked $49/mo rate remain. The marketing site reads `GET /api/v1/subscription-tiers?active_only=true` and renders the appropriate page variant. Zero code deploy. |

---

## Appendix — JSON Schema File Update Checklist

After all migrations run, the Python Engineer must run `python schema_manager.py set` for every modified table:

```bash
cd backend

python schema_manager.py set subscription_tier         # dropped 2 columns, added schedule_lanes
python schema_manager.py set product_plan              # founders_plan added, enterprise deleted
python schema_manager.py set product_feature           # dispatch_slots + data_exports deleted, schedule_lanes added
python schema_manager.py set product_plan_product_feature_version  # all rows replaced
python schema_manager.py set product_plan_version      # all rows replaced
python schema_manager.py set tenant_product_feature_override       # verify no schema change
```

Then commit the updated `dev-docs/db-design/pilot-db-schema-v2.6h.json`.

---

> **⚠️ STOP — Part A Complete (v1.2). Awaiting Tom's final review and approval before Parts B–E are written.**
