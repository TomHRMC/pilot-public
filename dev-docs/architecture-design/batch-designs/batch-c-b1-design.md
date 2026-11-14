# Batch C-B1 — Charter Rename Inventory (D14)

**Batch code**: C-B1
**Design doc owner**: Pilot Architect
**Created**: August 2, 2026
**Status**: ✅ Complete — Part A (Python) + Part B (React) done 2026-08-04 (see completion summaries)
**Plan link**: `pilot-launch-plan.md`
**Batch type**: Mixed — Backend (Python) + Frontend (Marketing React + Web React)
**Engineers**: Pilot Python Engineer (Part A, first) → Pilot React Engineer (Part B, after)
**Prerequisite**: SIGNUP-UI-FIX-1 ✅
**Source of truth**: `pilot-gtm-strategy-v3.md` §6.1 (D14) + `pilot-tech-impl-spec-v1.md` §2

---

## Problem Statement

The GTM strategy v3 retires the terms "Founder," "Founding Tester," "Founding Member," and "Early Access" in favor of a single term: **Charter**. Per D14: "All three prior terms are removed from code, database, marketing site, and documentation." Per the tech impl spec §12: "C-B1 must land first and alone. It touches the same files as most other batches; deferring it means doing that work twice."

This is a pure rename batch — no new features, no new endpoints, no new schema columns, no new UI patterns. The only structural change is a data-level DB migration (UPDATE statements, not DDL).

---

## A. Input Read Summary

| Input | Section(s) read | What it established |
|---|---|---|
| `pilot-gtm-strategy-v3.md` | §6.1 (Naming), §10 (D14), §9.2 (Site Changes) | The rename mandate: "Founder/Founding Tester/Founding Member/Early Access" → "Charter". Site changes: `/early-access` → `/charter` (308 redirect), CTA "Get Early Access" → "Be one of the first twelve", `WaitlistForm` → `CharterApplicationForm` |
| `pilot-tech-impl-spec-v1.md` | §2 (Rename Inventory), §2.2 (Rename Table), §2.3 (Do NOT Rename), §2.4 (Migration) | Exact layer-by-layer rename table. Do-not-rename list (Tom = founder). Migration approach (data UPDATE, not DDL). Guard test requirement. |
| `postgres-local` MCP | `subscription_tier` columns + rows | Live schema: `tier_name` (not `code`), `display_label` (not `display_name`), `annual_price_cents`/`monthly_price_cents` (not `price_cents`). Current rows: `founders` (active, $0), `trial`, `starter`, `teams`. No `enterprise` row. |
| `postgres-local` MCP | `product_plan` columns | Live schema: `code` (PK), `name`, `description`, `is_active`. Current row: `founders_plan` / `Founders Plan`. |
| `postgres-local` MCP | Tables with `product_plan_code` column | 4 tables reference `product_plan.code`: `product_plan_product_feature_version`, `product_plan_version`, `subscription`, `subscription_tier`. All must be updated atomically. |
| Codebase search (`rg`) | backend `*.py`, frontend `*.ts/tsx`, infrastructure `*.tf/yml` | 138 backend matches (12 files), 91 frontend matches (~25 files), 0 infrastructure matches. Full inventory in blast radius summary. |
| `README-seed-data.md` | §8 (table inventory), §10 (expected output) | 5 references to `founders`/`founders_plan` in the seed data reference doc — must be updated. |
| `python-engr-std-prompt-inclusions.md` | §1 (critical rules) | 1 reference to "founders cohort Stripe schedule" in mandatory-read instruction — must be updated. |

---

## B. Migration Plan

### B.1 — DB changes

One new Alembic migration: data-level UPDATE only (no DDL). Uses `session_replication_role = replica` to disable FK triggers during the atomic rename of `product_plan.code` (PK referenced by 4 tables).

**Pre-migration state** (verified via MCP 2026-08-02):
- `subscription_tier`: 4 rows — `founders` (active, $0), `trial` (inactive, 14-day), `starter` (inactive, $588/$59), `teams` (inactive, $1788/$179)
- `product_plan`: 3 rows — `founders_plan` (active), `starter_plan` (inactive), `teams_plan` (inactive)
- No `enterprise` row in either table (D10 already satisfied)

**Migration SQL** (all column names verified via MCP):

```sql
-- Step 1: Disable FK triggers for atomic PK rename
SET session_replication_role = replica;

-- Step 2: Rename product_plan PK + display name
UPDATE public.product_plan
  SET code = 'charter_plan', name = 'Charter',
      description = 'Charter program plan. 90 days free, then $49/mo locked at Starter limits for as long as subscribed.'
  WHERE code = 'founders_plan';

-- Step 3: Rename subscription_tier
UPDATE public.subscription_tier
  SET tier_name = 'charter', display_label = 'Charter', product_plan_code = 'charter_plan'
  WHERE tier_name = 'founders';

-- Step 4: Update all FK references to product_plan.code
UPDATE public.product_plan_version
  SET product_plan_code = 'charter_plan'
  WHERE product_plan_code = 'founders_plan';

UPDATE public.product_plan_product_feature_version
  SET product_plan_code = 'charter_plan'
  WHERE product_plan_code = 'founders_plan';

UPDATE public.subscription
  SET product_plan_code = 'charter_plan'
  WHERE product_plan_code = 'founders_plan';

-- Step 5: Re-enable FK triggers
SET session_replication_role = origin;
```

**Guard test** (in the migration's upgrade or a post-migration test):
```python
def test_no_founders_tier_exists(db_session):
    """Post-migration guard: no 'founders' tier or 'founders_plan' plan exists."""
    tier = db_session.execute(text(
        "SELECT 1 FROM subscription_tier WHERE tier_name = 'founders'"
    )).first()
    assert tier is None, "founders tier still exists — migration did not run"
    plan = db_session.execute(text(
        "SELECT 1 FROM product_plan WHERE code = 'founders_plan'"
    )).first()
    assert plan is None, "founders_plan still exists — migration did not run"
```

### B.2 — MCP verification queries (pre-work for Python Engineer)

Before running the migration, verify:
```sql
SELECT tier_name, display_label, product_plan_code, is_active FROM subscription_tier WHERE tier_name = 'founders';
SELECT code, name, is_active FROM product_plan WHERE code = 'founders_plan';
SELECT count(*) FROM subscription WHERE product_plan_code = 'founders_plan';
```

### B.3 — No new columns, no new tables, no DDL

This migration is purely data-level. No `ALTER TABLE`, no `CREATE TABLE`, no new columns.

---

## C. Execution Order

### Part A — Backend (Python Engineer, runs first)

| Step | Task | Files |
|---|---|---|
| A1 | Create Alembic migration (data UPDATE per §B.1) | `backend/migrations/versions/2026_08_02_XXXX-XXXX_c_b1_charter_rename.py` |
| A2 | Rename seed script constants, keys, and values | `backend/migrations/scripts/seed_platform.py` — `TIER_TO_PLAN_MAP`, `PLAN_FEATURE_LIMITS`, `PRODUCT_PLAN_PRICES`, `PRODUCT_PLANS`, tier seed dict |
| A3 | Rename seed test tenant references | `backend/migrations/scripts/seed_test_tenant.py` — `founders_tier` variable → `charter_tier`, all `'founders'`/`'founders_plan'` string literals |
| A4 | Rename Stripe subscription service | `backend/services/stripe_subscriptions.py` — `create_founders_subscription_schedule()` → `create_charter_subscription_schedule()`, metadata keys `founders_cohort` → `charter_cohort`, `founders_free_period` → `charter_free_period`, `founders_paid_period` → `charter_paid_period`, all log messages |
| A5 | Update billing model comment | `backend/app/models/billing.py` — comment "founders cohort" → "Charter cohort" |
| A6 | Rename all backend test references | 6 test files — `founders_tier` fixtures → `charter_tier`, `tier_name == "founders"` → `tier_name == "charter"`, `founders_plan` → `charter_plan`, all assertion strings |
| A7 | Update seed data README | `backend/README-seed-data.md` — all `founders`/`founders_plan`/`Founders` references → `charter`/`charter_plan`/`Charter` |
| A8 | Update Python Engineer prompt inclusions | `backend/python-engr-std-prompt-inclusions.md` — "founders cohort" → "Charter cohort" |
| A9 | Run migration + reseed + run tests | `alembic upgrade head` → `python -m migrations.scripts.seed_platform --mode reset` → `pytest -m unit --tb=no -q` |
| A10 | Regenerate OpenAPI (if any schema field names changed — they don't, but verify) | `python export_openapi_json.py` |
| A11 | Handoff: commit + notify React Engineer | `pnpm sync-api-types` not needed (no API shape change, only data values) |

### Part B — Frontend (React Engineer, runs after Part A)

| Step | Task | Files |
|---|---|---|
| B1 | Rename site mode type + logic | `frontend/apps/marketing/src/lib/useSiteMode.ts` — `SiteMode = "founders" \| "general"` → `"charter" \| "general"`, `FOUNDERS_MODE` → `CHARTER_MODE`, `isFoundersMode` → `isCharterMode`, `hasFounders` → `hasCharter` |
| B2 | Create `/charter` page (rename + rebuild `/early-access`) | `frontend/apps/marketing/src/app/charter/page.tsx` (new) — content per GTM §6. Update `early-access/page.tsx` to 308 redirect to `/charter` |
| B3 | Rename marketing CTAs + routes | Header, Footer, page.tsx, BlogCta, BlogPostLayout, TradePageTemplate, contact, features, blog, about, sign-up, pricing, pricing-preview, sitemap, not-found — all `/early-access` → `/charter`, "Be One of the First" → "Be one of the first twelve", "Get Early Access" → "Be one of the first twelve" |
| B4 | Rename pricing page components | `pricing/page.tsx` — `foundersFeatures` → `charterFeatures`, `foundersIncludedItems` → `charterIncludedItems`, `foundersFaqs` → `charterFaqs`, `PricingPageFounders` → `PricingPageCharter` |
| B5 | Rename forms | `WaitlistForm.tsx` → `CharterApplicationForm.tsx` (rename file + component), `HeroWaitlistForm.tsx` → `HeroCharterForm.tsx`, `source = "early_access_page"` → `source = "charter_page"` |
| B6 | Rename web app signup text | `signup/plan/page.tsx`, `signup/account/page.tsx` — "Join the Founders program" → "Join the Charter program" (or per GTM §6.8: "Be one of the first twelve"), "Founders mode" comments → "Charter mode" |
| B7 | Rename web app mock data + tests | `dispatchBoardHandlers.ts` — `MOCK_FOUNDERS_TIER` → `MOCK_CHARTER_TIER`, `tier_name: "founders"` → `"charter"`, `display_label: "Founders"` → `"Charter"`. 6 test files — all `founders`/`Founders` references in fixtures and assertions. |
| B8 | Update sitemap | `sitemap.ts` — `/early-access` → `/charter` |
| B9 | Run frontend tests | `pnpm --filter marketing test` + `pnpm --filter web test` |

### Files explicitly NOT modified (with rationale)

| File | Rationale |
|---|---|
| `backend/tasks/marketing_notifications.py` | "Tom Lang, Founder" — refers to Tom, not the plan (spec §2.3) |
| `frontend/apps/marketing/src/app/about/page.tsx` | "founder story", "founder-heading", "I'm Tom Lang, the founder" — refers to Tom (spec §2.3) |
| `frontend/apps/marketing/src/app/careers/page.tsx` | "founder access", "solo-founder company" — refers to Tom (spec §2.3) |
| `backend/migrations/versions/2026_07_09_2021-*.py` | Existing migration — git history is immutable (spec §2.3) |
| `backend/migrations/versions/2026_07_14_*.py` | Existing migrations — immutable |
| `backend/migrations/scripts/batch-results/*.txt` | Historical inspection logs — not code |

---

## D. New API Endpoints

**None.** This is a pure rename batch. No new endpoints, no changed endpoint signatures, no changed response shapes. The API will return `tier_name: "charter"` instead of `tier_name: "founders"`, but the response schema is unchanged.

---

## E. Pattern Reuse Decisions

| Pattern | How it applies |
|---|---|
| **System-default / tenant-override** (§16) | Not applicable — no override logic changes |
| **Mode-aware UI** (existing `useSiteMode`) | The mode type changes from `"founders" \| "general"` to `"charter" \| "general"`, but the pattern is unchanged — still derives mode from active tiers |
| **308 permanent redirect** | `/early-access` → `/charter` per GTM §9.2. Keep the route for inbound links. |

---

## F. Shared Module Interfaces

### F.1 — Function renames (backend)

| Was | Now | File |
|---|---|---|
| `create_founders_subscription_schedule()` | `create_charter_subscription_schedule()` | `services/stripe_subscriptions.py` |
| `handle_subscription_schedule_updated()` (checks `founders_cohort`) | Same name, checks `charter_cohort` | `services/stripe_subscriptions.py` |

### F.2 — Stripe metadata key renames

| Was | Now |
|---|---|
| `schedule_type: "founders_cohort"` | `schedule_type: "charter_cohort"` |
| `phase: "founders_free_period"` | `phase: "charter_free_period"` |
| `phase: "founders_paid_period"` | `phase: "charter_paid_period"` |
| `cohort: "founders"` | `cohort: "charter_1"` |

**Note**: Existing Stripe objects in test mode will be recreated in C-B3 (Stripe bootstrap). C-B1 only changes the code that SETS metadata on new objects.

### F.3 — Frontend type renames

| Was | Now | File |
|---|---|---|
| `SiteMode = "founders" \| "general"` | `SiteMode = "charter" \| "general"` | `useSiteMode.ts` |
| `isFoundersMode` | `isCharterMode` | `useSiteMode.ts` |
| `FOUNDERS_MODE` | `CHARTER_MODE` | `useSiteMode.ts` |
| `MOCK_FOUNDERS_TIER` | `MOCK_CHARTER_TIER` | `dispatchBoardHandlers.ts` |

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| Should `product_plan.code` be `charter_plan` or reuse `starter_plan`? | **`charter_plan`** — Charter is a distinct plan with its own price lock, signup cap, and free period. Per spec §9.2: "Charter resolves to exactly the Starter entitlement set" but it is a separate plan row for reporting and price-lock exclusion. |
| Should the `/early-access` route be deleted or redirected? | **308 permanent redirect** to `/charter` (GTM §9.2: "Keep the route for existing inbound links; add `/charter` and redirect"). |
| Should existing Alembic migrations be edited? | **No** — git history is immutable (spec §2.3). The rename is a new migration, not editing old ones. |
| Should `batch-results/*.txt` inspection logs be updated? | **No** — they are historical run output, not code. They will be stale but harmless. |
| Does the OpenAPI spec change? | **No** — the response schema is unchanged. Only the `tier_name` data value changes from `"founders"` to `"charter"`. `pnpm sync-api-types` is not needed. |
| What about the `founders` tier's `annual_price_cents: 0` and `monthly_price_cents: 0`? | **Not changed in C-B1.** The Charter pricing ($49/mo flat) is set in C-B2 (schema + seed data update). C-B1 is rename-only. |

---

## H. Surface Mockup Reference

**Not applicable.** This is a rename batch — no new UI surfaces, no pixel-level design changes. The `/charter` page content is specified in GTM §6 and will be authored by the React Engineer directly from the GTM doc's copy blocks (§6.7, §9.3). No designer-mode spec is needed for C-B1.

The `/charter` page rebuild (replacing `/early-access`) is a content swap, not a new design — the existing page layout is retained with updated copy per GTM §6.

---

## I. Component Manifest

### New components (file renames, not new functionality)

| Component | Destination | Note |
|---|---|---|
| `CharterApplicationForm` | `frontend/apps/marketing/src/components/forms/CharterApplicationForm.tsx` | Renamed from `WaitlistForm.tsx` |
| `HeroCharterForm` | `frontend/apps/marketing/src/components/HeroCharterForm.tsx` | Renamed from `HeroWaitlistForm.tsx` |
| `CharterPage` | `frontend/apps/marketing/src/app/charter/page.tsx` | New route; content from GTM §6. `/early-access` becomes 308 redirect. |

### Renamed components (same file, renamed internal identifiers)

| Component | File | Change |
|---|---|---|
| `PricingPageFounders` → `PricingPageCharter` | `pricing/page.tsx` | Function rename + data array renames |
| `useSiteMode` return type | `useSiteMode.ts` | `isFoundersMode` → `isCharterMode`, `FOUNDERS_MODE` → `CHARTER_MODE` |

### No new `packages/ui` components

---

## Estimate

- **Part A (Python)**: 2–3 hours (migration + 4 source files + 6 test files + 2 docs)
- **Part B (React)**: 3–4 hours (~15 marketing files + 8 web files, mostly find-and-replace + `/charter` page content)
- **Total**: 5–7 hours

---

## Definition of Done

### Phase 1 (unit tests only)

- [ ] Alembic migration created + runs successfully (`alembic upgrade head`)
- [ ] Guard test passes (no `founders`/`founders_plan` in DB)
- [ ] `pytest -m unit --tb=no -q` passes with 0 failures
- [ ] All backend `founders`/`founding` references renamed (except do-not-rename list)
- [ ] `rg -i 'founder' backend/ --type py` returns only: `marketing_notifications.py` (Tom), migration files (immutable), test files with "founder approval" in override reason text

### Phase 2 (full suite)

- [ ] `pnpm --filter marketing test` passes
- [ ] `pnpm --filter web test` passes
- [ ] `/early-access` returns 308 redirect to `/charter`
- [ ] `/charter` page renders with GTM §6 copy
- [ ] Pricing page shows "Charter" (not "Founders")
- [ ] Signup plan/account pages show "Charter" text (not "Founders")
- [ ] All frontend `founders`/`Founders` references renamed (except about/careers pages = Tom)
- [ ] `rg -i 'founder' frontend/ --type ts --type tsx` returns only: about page, careers page, and comments referencing Tom

---

*End of batch design. Engineer prompts will be authored as `batch-c-b1-python-engr-prompt.md` (Part A, first) and `batch-c-b1-react-engr-prompt.md` (Part B, after Part A closes).*
