# Batch Design — PLP-STRIPE-CHARTER-ROW-1 — Charter Signup Local `subscription` Row + Backfill

**Version**: 1.0
**Date**: 2026-08-11
**Author**: Pilot Architect
**Owner (impl)**: Python Engineer
**Priority**: P1 · Phase: Pre-GA
**Prerequisite**: ALPHA-FIX-1 ✅ (self-serve Charter signup now reaches the dashboard)
**Estimate**: 2–3h
**Launch-plan entry**: `pilot-launch-plan.md` §2.3 PLP-STRIPE-CHARTER-ROW-1 (master row 10c, Execution Order 4)

---

## Problem Statement

The author's own end-to-end Charter signup test was run against **prod** (the pre-release AWS environment, used for Phase-1 integration testing per `aws-env-mgmt-ops-plan.md`, with Stripe in **test mode**; no customers). His test tenant **Lang Electric Co.** completed signup and landed on the dashboard, but verification via `postgres-prod` MCP found:

- `tenant`: `stripe_customer_id = cus_REDACTEDX02`, `current_subscription_tier_id` set, `free_period_ends_at = 2026-11-09`, `charter_member_number = 1`.
- `tenant_signup`: `signup_state = 'complete'`.
- `stripe_webhook_event_processed`: **both** `customer.subscription.created` **and** `invoice.paid` recorded (processed 2026-08-11T19:30:17Z).
- **`public.subscription`: globally empty (0 rows).**

**Impact:** `is_subscription_billing_active(db, tenant_id)` queries `subscription WHERE is_active = True`; with no row it returns `False` (line 249–250). The API paywall therefore **402s every paywalled mutation** for this (and every future) Charter tenant. The dashboard still loads because it gates on `tenant.current_subscription_tier_id`, which **is** set — this masks the gap from a casual smoke test.

### Root cause — two code paths that both no-op for Charter

1. **Write-at-source is missing.** `create_charter_subscription()` creates the Stripe subscription using `price_charter_monthly` from `stripe_ids.{mode}.json` (via `core.stripe_config.get_stripe_ids()`), logs, and `return sub.id`. It **never inserts a local `subscription` row**. (Contrast: the non-Charter path in `handle_subscription_created()` does upsert one.)
2. **Webhook tier lookup can't match Charter.** `handle_subscription_created()` resolves the tier by price ID (`or_(stripe_price_id_monthly == price_id, stripe_price_id_annual == price_id)`, lines 152–159). The **Charter tier has NULL `stripe_price_id_monthly`/`_annual`** (verified via MCP — Charter bills via `stripe_ids.*.json`, not the tier price columns), so it hits `if not tier: return` at line 161–163 and never reaches the upsert at lines 205–254.

Because the Stripe-side objects DO exist (customer, subscription, paid invoice, both webhooks delivered and deduped), this is purely a **local-persistence gap**, not a Stripe-integration failure.

---

## A. Input Read Summary

| Input | Section / lines | Why it was read | Key fact extracted |
|---|---|---|---|
| `pilot-operations.md` | §4 Tenant Subscription Lifecycle, §8 Subscription Status Machine | Runtime billing/paywall reference (Rule §10.1) | `is_billing_active` gates the paywall; `trialing` is a billing-active status; charter signup path documented |
| `aws-env-mgmt-ops-plan.md` | §1 phase model, §4.1 rule set | Confirm prod=integration env + who writes the local row | §4.1 rule 3: local `subscription` row written ONLY by webhook today — this batch is the sanctioned change to that rule for Charter |
| `create_charter_subscription()` | 589–639 | Primary fix site | Returns `sub.id`; no local insert; has `metadata.tier_code='charter'` + `charter_member_number` |
| `handle_subscription_created()` | 109–259 | Belt-and-suspenders fix site | Early return at 161 on price-lookup miss; upsert pattern (`on_conflict_do_update` on `psp_subscription_id`) at 205–254 |
| `tenant_signup.py` step4_tier | 458–531 | Confirm call site + transaction boundaries | `create_charter_subscription()` called non-blocking after cohort-cap commit; commits internally; failures logged, wizard advances |
| `is_subscription_billing_active()` | 220–259 | Confirm the exact paywall failure | `if not sub: return False` (249–250) when no `is_active` row |
| MCP `postgres-local` — `subscription` columns | live | Ground the INSERT (Rule §3 MCP-before-SQL) | Columns confirmed (see §B) |
| MCP `postgres-local` — `subscription_status` columns/rows | live | Resolve `status_id` by code | PK = `id` (UUID); `code`, `is_billing_active`; `trialing` row is billing-active |
| MCP `postgres-prod` — Lang Electric tenant + `subscription` count | live (Tom's tunnel) | Prove the gap + gather backfill keys | 0 subscription rows; tenant/customer IDs captured for backfill |

---

## B. Migration Plan

**No schema change.** This batch inserts rows into the existing `subscription` table and (optionally) reads `subscription_status`. There is **no Alembic migration** — the write happens in application service code + a one-time backfill.

### B.1 — MCP verification (Python Engineer re-runs before writing any SQL)

```sql
-- subscription columns (authoritative shape for the INSERT)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema='public' AND table_name='subscription'
ORDER BY ordinal_position;

-- subscription_status: resolve the trialing status_id by code (never hardcode the UUID)
SELECT id, code, name, is_billing_active
FROM public.subscription_status
ORDER BY code;

-- Charter tier product_plan_code (for subscription.product_plan_code)
SELECT tier_id, tier_name, product_plan_code,
       stripe_price_id_monthly, stripe_price_id_annual
FROM public.subscription_tier
WHERE tier_name = 'charter';

-- unique index that the upsert targets
SELECT indexname, indexdef FROM pg_indexes
WHERE schemaname='public' AND tablename='subscription';
```

### B.2 — Confirmed `subscription` columns (live, `postgres-local`, 2026-08-11)

`id`, `tenant_id`, `product_plan_code`, `status_id`, `quantity_seats` (default 1), `billing_anchor`, `started_at` (default `now()`), `canceled_at`, `psp_provider`, `psp_subscription_id`, `psp_customer_id`, `billing_interval` (default `'monthly'`), `trial_ends_at`, `renews_at`, `cancel_at_period_end` (default false), `is_active` (default true), `stripe_schedule_id`, + audit cols `created_at`/`updated_at`/`created_by`/`updated_by`.

### B.3 — Row to write for a Charter subscription

| Column | Value |
|---|---|
| `id` | `uuid4()` |
| `tenant_id` | tenant |
| `product_plan_code` | Charter tier's `product_plan_code` (from §B.1 query) |
| `status_id` | `subscription_status.id` WHERE `code='trialing'` (resolved at runtime — **never hardcode**) |
| `quantity_seats` | `1` |
| `started_at` | `datetime.now(UTC)` |
| `psp_provider` | `'stripe'` |
| `psp_subscription_id` | `sub.id` returned by Stripe (`sub_…`) |
| `psp_customer_id` | `stripe_customer_id` (`cus_…`) |
| `billing_interval` | `'monthly'` |
| `trial_ends_at` | `free_period_ends_at` |
| `renews_at` | `free_period_ends_at` (Charter renews at trial end) |
| `is_active` | `True` |
| `stripe_schedule_id` | `None` (schedule handled separately by `create_charter_subscription_schedule`; not in scope) |

> **Status choice — `trialing`, not `active`.** The Charter subscription is created with a Stripe trial (`trial_end` + `missing_payment_method: pause`); it is NOT yet actively billing a card. `trialing` is `is_billing_active = true`, so the paywall opens correctly while accurately reflecting Stripe state. (The existing non-Charter webhook path uses `active` because that path only fires on real conversion — different semantics; do not copy it here.)

### B.4 — Seed Data Rollout (one-time backfill)

This batch **adds a data row** (the backfill), so a Seed Data Rollout section is mandatory (Rule §11.5).

- **Layer 1 (Core/Platform):** none — `subscription` is tenant/scenario data, not a lookup table. No `seed_core.py`/`seed_platform.py` change.
- **Backfill (one-time, idempotent):** create the missing `subscription` row for the already-provisioned Lang Electric tenant using the **same write-at-source helper** the fix introduces (see §F). Keys: `tenant_id = <tenant_id>`, `psp_customer_id = cus_REDACTEDX02`. The Stripe `sub_…` id must be **read from Stripe** (list subscriptions for that customer) rather than guessed — the backfill retrieves it, then upserts on `psp_subscription_id` so a re-run is a no-op.
- **Scenario seeds:** `seed_scenario_*` Charter tenants (if any create a Charter tenant) must also get a `subscription` row so local/QA data matches prod behavior. Python verifies whether any scenario seeds a Charter tenant; if so, extend that seed to write the row via the same helper. If none do, note "N/A — no scenario seeds a Charter tenant" in the completion summary.
- **README:** update `backend/README-seed-data.md` §4 Current Seed State if a scenario seed gains a `subscription` row.

**Backfill execution posture:** the backfill runs against **prod** (Phase-1 integration env) via Tom, not automatically in CI. Deliver it as an idempotent script/CLI (or a guarded `mode_seed` path) the Python Engineer can hand to Tom; it must be safe to run twice.

---

## C. Execution Order

| # | Step | File(s) | Notes |
|---|---|---|---|
| 1 | MCP re-verify `subscription`, `subscription_status`, Charter `subscription_tier`, indexes | — | Rule §3 gate before any SQL |
| 2 | Add `_write_local_charter_subscription_row()` helper (shared by fix + backfill) | `services/stripe_subscriptions.py` | Resolves `trialing` status by code; upsert on `psp_subscription_id` |
| 3 | Call the helper at the end of `create_charter_subscription()` before `return sub.id` | `services/stripe_subscriptions.py` | Write-at-source (primary fix) |
| 4 | Add Charter-metadata fallback to `handle_subscription_created()` tier lookup | `services/stripe_subscriptions.py` | Belt-and-suspenders |
| 5 | Backfill script/CLI for existing Charter tenant(s) | `migrations/scripts/` (or a small CLI) | Idempotent; reads `sub_…` from Stripe; upsert |
| 6 | Unit tests (helper, create-path, webhook-fallback, idempotent re-run) | `backend/tests/unit/...` | See §G |
| 7 | Phase 1 unit gate → Phase 2 full suite + Ruff (changed files) | — | §14 two-phase gate |

---

## D. New API Endpoints

**None.** No new or changed HTTP endpoints. No OpenAPI regeneration, no `pnpm sync-api-types` handoff. This is a service-layer + persistence fix only.

---

## E. Pattern Reuse Decisions

| Pattern | Applies? | Decision |
|---|---|---|
| Upsert `on_conflict_do_update(index_elements=["psp_subscription_id"])` | ✅ | Reuse the exact pattern already in `handle_subscription_created()` (lines 226–251) so create-path and webhook-path converge on one idempotent write |
| Resolve status by `code` not UUID | ✅ | Mirrors `handle_subscription_created()` lines 179–183; use `code='trialing'` here |
| `StandardAuditMixin` (4 audit cols) | ✅ | Inherited by the `Subscription` model; no manual audit-col handling needed (system/no-user context → `created_by`/`updated_by` NULL, which is allowed) |
| Non-blocking Stripe failures in signup | ✅ (unchanged) | The helper runs inside the existing `try/except` in `create_charter_subscription()` call site — a local-write failure must NOT crash the wizard; log and continue (same posture as today) |
| §16 platform UX patterns | ❌ | Backend-only batch — no UI surface |

---

## F. Shared Module Interfaces

```python
# services/stripe_subscriptions.py

def _write_local_charter_subscription_row(
    db: Session,
    *,
    tenant_id: UUID,
    stripe_customer_id: str,
    stripe_subscription_id: str,
    free_period_ends_at: datetime,
) -> None:
    """Upsert the local `subscription` row for a Charter tenant.

    - Resolves product_plan_code from the Charter subscription_tier.
    - Resolves status_id via subscription_status WHERE code='trialing'
      (is_billing_active=True) — never hardcodes the UUID (differs per env).
    - psp_provider='stripe', billing_interval='monthly',
      trial_ends_at=renews_at=free_period_ends_at, is_active=True.
    - Idempotent: ON CONFLICT (psp_subscription_id) DO UPDATE.
    Commits internally (consistent with create_charter_subscription()).
    """
```

- **`create_charter_subscription()`** (line 589): after the Stripe `sub` is created and before `return sub.id`, call `_write_local_charter_subscription_row(db, tenant_id=…, stripe_customer_id=…, stripe_subscription_id=sub.id, free_period_ends_at=…)`. Wrap so a local-write error is logged but still returns `sub.id` (wizard must not break).
- **`handle_subscription_created()`** (line 109): after the price-ID lookup, if `tier is None`, attempt a fallback: read `subscription["metadata"]["tier_code"]`; if `== "charter"`, load the Charter tier by `tier_name='charter'` and continue. This makes the webhook path self-healing without altering non-Charter behavior.
- **Backfill CLI/script**: for the target customer, `stripe.Subscription.list(customer=cus_…)` → take the active/trialing `sub_…` → call `_write_local_charter_subscription_row(...)`. Idempotent via the upsert.

**No Celery tasks, no schedules** added or changed.

---

## G. Open Questions Resolved

1. **`trialing` vs `active` status?** → `trialing` (§B.3). Charter is on a Stripe trial with pause-on-missing-PM; `trialing.is_billing_active = true` opens the paywall correctly and matches Stripe truth. Using `active` would misrepresent state and diverge from the eventual conversion webhook.
2. **Write at source, at the webhook, or both?** → **Both** (§D of the launch card). Write-at-source (a) fixes the create path deterministically and synchronously (no webhook-timing dependency); the webhook fallback (b) makes the event path self-healing and covers any Charter subscription created outside the signup helper. Converging both on the same upsert keeps them idempotent.
3. **Does the webhook change risk non-Charter tenants?** → No. The fallback only triggers when the price-ID lookup returns `None` AND `metadata.tier_code == 'charter'`. Every non-Charter path is unchanged.
4. **Where does the `sub_…` id for the backfill come from?** → Read from Stripe (`Subscription.list(customer=…)`), never fabricated. Upsert on `psp_subscription_id` makes a re-run a no-op.
5. **Migration needed?** → No. Existing table, row insert only; audit cols inherited via mixin.
6. **Does this touch the Charter subscription *schedule*?** → No. `create_charter_subscription_schedule()` / `stripe_schedule_id` are out of scope; leave `stripe_schedule_id = None`. If C-B14/C-B14-FIX later populates it, that path already has its own writer.
7. **Env-specific values?** → `status_id` and `product_plan_code` are resolved by natural key at runtime, so the same code is correct in dev/QA/prod. The Stripe `price_charter_monthly` already resolves per-mode via `get_stripe_ids()` (unchanged).

---

## Definition of Done (design-level acceptance)

- A fresh Charter signup writes exactly one `subscription` row (`status=trialing`, `is_active=True`, correct `psp_*` ids) **synchronously** in `create_charter_subscription()`.
- `is_subscription_billing_active()` returns `True` for a freshly-signed Charter tenant → paywalled mutations no longer 402.
- The webhook path independently produces the same row when the price-ID lookup misses but `metadata.tier_code=='charter'`.
- The idempotent backfill creates the missing row for Lang Electric (`cus_REDACTEDX02`) and is a no-op on re-run.
- Unit tests cover: helper insert, create-path integration, webhook Charter-metadata fallback, idempotent re-run, and `is_subscription_billing_active()` flipping to `True`.
- No new endpoints; no OpenAPI/`sync-api-types` change. Seed Data Rollout + README verified.
- Master-doc sync: on close, Architect updates `pilot-operations.md §4` known-gap callout to "resolved by PLP-STRIPE-CHARTER-ROW-1" and clears the `stripe-ops-runbook.md` Open Items entry.
