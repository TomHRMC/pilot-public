# Implementation Prompt: PLP-STRIPE-CHARTER-ROW-1 — Charter Signup Local `subscription` Row + Backfill

**Mode**: `pilot-python-engineer`
**Batch**: PLP-STRIPE-CHARTER-ROW-1
**Priority / Phase**: P1 · Pre-GA
**Plan**: `pilot-launch-plan.md` §2.3 PLP-STRIPE-CHARTER-ROW-1 (master row 10c · Execution Order 4)
**Design doc**: `batch-plp-stripe-charter-row-1-design.md`
**Estimate**: 2–3h
**Platform**: Backend (Python) — service layer + one-time backfill
**Frontend companion**: none (no endpoint/OpenAPI change)
**Prerequisite**: ALPHA-FIX-1 ✅

---

## ⚠️ MANDATORY STOP: Read These First

Before writing any code, read in full:

1. `pilot-python-engineer-methods.md` — your operating methods.
2. `README-adding-tests.md` — test folder mapping + autouse fixtures.
3. This batch's design doc: `batch-plp-stripe-charter-row-1-design.md` — §D fix plan, §F interfaces, §G resolved questions.
4. `pilot-operations.md §4 + §8` — subscription lifecycle + status machine (this is a **billing/subscription** batch — see §19 callout below).

Do **not** start coding until you have read all four.

### Batch-Specific Critical Rules

- **Rule 3 (MCP-before-SQL)**: Re-run the §Pre-Work MCP queries for `subscription`, `subscription_status`, and the Charter `subscription_tier` in **this** session before writing any INSERT/upsert. Use only column names those queries return.
- **Never hardcode a `status_id` UUID.** Resolve it at runtime via `subscription_status WHERE code='trialing'` (`is_billing_active=True`). The UUID differs per environment (dev/QA/prod) — hardcoding it is the same class of error as guessing a column name.
- **Never hardcode the Charter `product_plan_code` or price ID.** `product_plan_code` comes from the Charter `subscription_tier` row; the Stripe price already resolves per-mode via `core.stripe_config.get_stripe_ids()` — do not touch it.
- **Idempotency is mandatory.** All writes upsert `ON CONFLICT (psp_subscription_id) DO UPDATE`. The create-path helper, the webhook fallback, and the backfill must all be safe to run twice.
- **Do not break the signup wizard.** The local-row write runs inside `create_charter_subscription()`, whose call site treats Stripe failures as non-blocking. A local-write error must be **logged and swallowed** so the wizard still advances and `sub.id` is still returned.
- **Backfill reads the `sub_…` id from Stripe** (`Subscription.list(customer=…)`). Never fabricate a subscription id.
- **RFC 7807**: no endpoints change, but if you add any raised error, use the RFC 7807 shape (no plain-string `detail`).
- **`db.get()` is banned** on tenant-scoped models — use tenant-scoped `select()` with explicit `WHERE`.

---

## Pre-Work: Establish Regression Baseline

Capture the pre-change unit baseline so you can prove no regressions at the end:

```bash
cd backend && pytest -m unit --tb=no -q | tail -5
```

Record the pass/fail/deselected counts in your completion summary.

---

## Pre-Work: Run MCP Verification Queries (`postgres-local`)

Filter every query by schema. Run all of these and confirm the results match the design doc §B before writing SQL:

```sql
-- 1. subscription columns — authoritative INSERT shape
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema='public' AND table_name='subscription'
ORDER BY ordinal_position;

-- 2. subscription_status — resolve the trialing status_id by code (never hardcode)
SELECT id, code, name, is_billing_active
FROM public.subscription_status
WHERE table_schema IS NOT NULL   -- (status table has no tenant scope; return all rows)
ORDER BY code;

-- 3. Charter tier — product_plan_code + confirm price columns are NULL (why the webhook misses)
SELECT tier_id, tier_name, product_plan_code,
       stripe_price_id_monthly, stripe_price_id_annual, free_period_days, signup_cap
FROM public.subscription_tier
WHERE tier_name = 'charter';

-- 4. unique index the upsert targets (confirm psp_subscription_id uniqueness)
SELECT indexname, indexdef FROM pg_indexes
WHERE schemaname='public' AND tablename='subscription';
```

> If query 2's `WHERE table_schema IS NOT NULL` guard confuses the tool, just run `SELECT id, code, name, is_billing_active FROM public.subscription_status ORDER BY code;` — the point is to read every status row and pick `code='trialing'`.

**Expected (per design §B):** `subscription` has the 21 columns listed in §B.2; `subscription_status` PK is `id`, `trialing` has `is_billing_active=true`; Charter tier has NULL `stripe_price_id_monthly`/`_annual` and a non-null `product_plan_code`; a unique index exists on `psp_subscription_id`.

**Production verification (later, for the backfill only):** `postgres-prod` reads production but requires an SSH tunnel that **only Tom controls** — ask Tom to confirm the tunnel is up before your first `postgres-prod` query, and STOP on any connection error. You do **not** need prod for the code fix or unit tests; only for confirming the backfill target and running it.

---

## Pre-Work: Read These Source Files

- `backend/services/stripe_subscriptions.py` — `create_charter_subscription()` (589–639) and `handle_subscription_created()` (109–259). Study the existing upsert (226–251) and status-by-code resolution (179–183) — you will mirror both.
- `backend/services/tenant_signup.py` — step4_tier call site (458–531); confirm the non-blocking `try/except` around `create_charter_subscription()`.
- `backend/services/entitlement_service.py` — `is_subscription_billing_active()` (220–259); this is what your fix must flip to `True`.
- `backend/app/models/billing.py` — the `Subscription` + `SubscriptionStatus` SQLModel classes (field names must match the SQL).
- `backend/README-seed-data.md` — §4 Current Seed State + §7 DELETE-safety, for the backfill/scenario question.

---

## Implementation Tasks (execute in this order — design §C)

1. **Add the shared helper** `_write_local_charter_subscription_row(db, *, tenant_id, stripe_customer_id, stripe_subscription_id, free_period_ends_at)` in `services/stripe_subscriptions.py` (interface in design §F):
   - Load the Charter `subscription_tier` (`tier_name='charter'`) → `product_plan_code`.
   - Resolve `status_id` via `subscription_status WHERE code='trialing' AND is_billing_active=True`.
   - Build the row per design §B.3 (`psp_provider='stripe'`, `billing_interval='monthly'`, `trial_ends_at=renews_at=free_period_ends_at`, `is_active=True`, `stripe_schedule_id=None`).
   - Upsert with `pg_insert(...).on_conflict_do_update(index_elements=["psp_subscription_id"], set_={...})` mirroring lines 226–251. Commit internally.
   - If the Charter tier or trialing status can't be resolved, `logger.error(...)` and return (do not raise) — never crash the caller.

2. **Call the helper at the end of** `create_charter_subscription()` (before `return sub.id`), wrapped so any local-write exception is logged and swallowed (wizard must still advance; `sub.id` still returned).

3. **Add the Charter-metadata fallback** in `handle_subscription_created()`: when the price-ID tier lookup returns `None`, read `subscription.get("metadata", {}).get("tier_code")`; if `== "charter"`, load the Charter tier by `tier_name='charter'` and continue to the existing upsert. Leave every non-Charter path unchanged.

4. **Backfill script/CLI** (idempotent, hand-off to Tom for prod) under `migrations/scripts/` (or extend an existing seed CLI with a guarded one-shot mode): for `psp_customer_id='cus_REDACTEDX02'` (tenant `<tenant_id>`), `stripe.Subscription.list(customer=…)` → pick the trialing/active `sub_…` → call the helper. Safe to run twice.

5. **Tests** (see below).

6. **Two-phase verification gate** + DoD.

---

## Test Requirements

Place tests in the billing/subscription domain folder (per `README-adding-tests.md`); use the autouse tenant/session fixtures. **Scope every assertion by the inserted id / tenant** — never `count()` all rows (seed data breaks that).

Minimum unit tests:

1. **Helper insert** — calling `_write_local_charter_subscription_row(...)` creates exactly one row with `status=trialing`, `is_active=True`, correct `psp_subscription_id`/`psp_customer_id`, `billing_interval='monthly'`, `trial_ends_at==free_period_ends_at`.
2. **Idempotent re-run** — calling the helper twice with the same `psp_subscription_id` yields one row (upsert), not a duplicate.
3. **Create-path** — `create_charter_subscription()` (Stripe mocked to return a `sub_…`) results in the local row existing.
4. **Webhook fallback** — `handle_subscription_created()` with a payload whose price ID matches no tier but `metadata.tier_code='charter'` writes the row; a non-Charter payload with an unknown price still returns early (unchanged).
5. **Paywall flips** — after the helper runs for a tenant, `is_subscription_billing_active(db, tenant_id)` returns `True` (was `False`).
6. **Non-blocking** — a helper that raises internally (e.g., Charter tier missing) does not propagate out of `create_charter_subscription()` (patch to force the error; assert `sub.id` still returned).

---

## Seed Data Rollout (Core + Scenario)

This batch adds a data row (the backfill), so this section is **required** (Rule §11.5 / inclusions §20).

- **Layer 1 — Core/Platform**: **N/A** — `subscription` is tenant/scenario data, not a lookup/reference table. No `seed_core.py`/`seed_platform.py` change.
- **Layer 2 — Scenario data**: check whether any `seed_scenario_*` script provisions a **Charter** tenant (charter tier + `free_period_ends_at`). If yes, extend that scenario to write a `subscription` row via `_write_local_charter_subscription_row(...)` so local/QA data matches prod. If none does, state **"N/A — no scenario seeds a Charter tenant"** in the completion summary.
- **Backfill (one-time, prod)**: the idempotent script from Task 4. Deliver it for Tom to run against prod (Phase-1 integration env); it must be a no-op on re-run.
- **Verification**: `python seed_core.py --mode inspect` (confirm no unintended lookup changes) + `pytest -m unit`.
- **README**: update `README-seed-data.md` §4 Current Seed State **only if** a scenario seed gains a `subscription` row.

---

## No OpenAPI / No `sync-api-types`

No endpoints are added or changed. Do **not** regenerate OpenAPI and do **not** trigger a React Engineer handoff. If you find yourself editing a route, stop — this batch is service-layer only.

---

## Final Verification Gate

### Phase 1 — Unit tests only (during development)

```bash
cd backend && pytest -m unit --tb=short -q | tail -20
```

### Phase 2 — Lint (changed files only) + Full suite (once, at the end)

```bash
# Ruff — changed files only, run from backend/
cd backend && ruff check services/stripe_subscriptions.py <other changed files> && ruff format --check services/stripe_subscriptions.py <other changed files>

# Full suite (stripe + telnyx live suites deselected per Tom, consistent with ALPHA-FIX-1)
cd backend && pytest -q -m "not stripe_live and not telnyx_live" | tail -15
```

Spot checks:
- MCP `postgres-local`: after a create-path test tenant, `SELECT status_id, is_active, psp_subscription_id FROM public.subscription WHERE tenant_id = '<test tid>'` returns one trialing/active row.
- `is_subscription_billing_active()` returns `True` for that tenant.

---

## Definition of Done

- [ ] Phase 1: `pytest -m unit` green (no regressions vs. baseline).
- [ ] `_write_local_charter_subscription_row()` added; idempotent upsert on `psp_subscription_id`; status resolved by `code='trialing'`; no hardcoded UUIDs/plan codes.
- [ ] `create_charter_subscription()` writes the local row before returning `sub.id`; local-write errors are logged and swallowed (wizard unbroken).
- [ ] `handle_subscription_created()` Charter-metadata fallback added; non-Charter paths unchanged.
- [ ] Idempotent backfill script delivered (reads `sub_…` from Stripe; safe to re-run) for `cus_REDACTEDX02`.
- [ ] Tests 1–6 added, scoped by inserted id/tenant.
- [ ] Seed Data Rollout resolved (scenario extended or "N/A" documented); README §4 updated if applicable.
- [ ] No OpenAPI/sync-api-types change.
- [ ] Phase 2: Ruff (changed files) clean + full suite (`not stripe_live and not telnyx_live`) green.
- [ ] Completion summary written in the exact format below.

---

## Completion Summary (write this at the end)

### PLP-STRIPE-CHARTER-ROW-1 — Charter Signup Local `subscription` Row + Backfill: Completion Summary

#### What Was Accomplished
- (bullet the create-path write, webhook fallback, backfill, paywall-flip verification)

#### Files Changed / Created
- (path — one line each)

#### Tests Added
- (test name — what it proves)

#### Verification
- Baseline: `<pre>` → Final: `<post>` (unit); full suite: `<counts>`; Ruff: clean.
- Prod backfill: (run by Tom / pending Tom) — `subscription` row now present for `cus_REDACTEDX02`; `is_subscription_billing_active` → True.

#### Handoff / Master-Doc Sync (for Architect on close)
- Architect to update `pilot-operations.md §4` known-gap callout → resolved, and clear the `stripe-ops-runbook.md` Open Items entry.
