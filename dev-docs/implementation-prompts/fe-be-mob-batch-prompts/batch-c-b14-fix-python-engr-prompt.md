# Implementation Prompt: C-B14-FIX — Post-C-B14 Stripe Hardening Follow-Ups

**Mode**: `pilot-python-engineer`
**Batch**: C-B14-FIX
**Priority / Phase**: P1 · Pre-GA
**Plan**: `pilot-launch-plan.md` §2.3 C-B14-FIX (master row 7 · Execution Order 4 — named next-in-order after PLP-STRIPE-CHARTER-ROW-1 ✅)
**Design doc**: none required — the source findings doc is self-contained: `c-b14-testing-findings.md`. Architect-resolved design decisions are inline in this prompt (§Design Decisions).
**Estimate**: 3–4h
**Platform**: Backend (Python) — webhook service layer + ops script
**Frontend companion**: none (no endpoint/OpenAPI change — do **not** run `pnpm sync-api-types`)
**Prerequisite**: PLP-STRIPE-CHARTER-ROW-1 ✅ (the Charter webhook fallback + `_write_local_charter_subscription_row()` you will build on are in current `main`)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing any code, read in full:

1. `pilot-python-engineer-methods.md` — your operating methods (§13 Alembic, §8 Router Design, §5 Model Design, §16 Standard Task Workflow).
2. `README-adding-tests.md` — test folder mapping + autouse fixtures.
3. `c-b14-testing-findings.md` — the five findings this batch closes (§1 webhook gap, §2 `.get()`, §5 stale cache, §6 audit bug, §7 FK validation).
4. `pilot-operations.md §4 + §8` — **billing/subscription batch (§19 callout)**: the 6 subscription status codes, `is_billing_active` paywall gate, and the tier→plan→ppfv cascade are NOT inferrable from the schema alone.

Do **not** start coding until you have read all four.

### Batch-Specific Critical Rules

- **Rule 1/16 (MCP-before-SQL, verify don't assume)**: Re-run the §Pre-Work MCP queries for `subscription`, `subscription_status`, `subscription_tier`, and `tenant_tier_override` in **this** session before writing any SQL or SQLModel field reference. Use only column names those queries return. If MCP errors → STOP and ask Tom.
- **Never hardcode a `status_id` UUID.** Resolve at runtime via `subscription_status WHERE code='active' AND is_billing_active=True` (or `code='trialing'`). UUIDs differ per environment (dev/QA/prod).
- **Never hardcode Stripe price IDs or `product_plan_code`.** Metered price IDs resolve per-mode via `core.stripe_config.get_stripe_ids()` (`price_voice_overage` / `price_sms_overage`); `product_plan_code` comes from the tier row.
- **The webhook handler must never crash.** `handle_subscription_created()` runs in a fire-and-forget `BackgroundTasks` path (`webhooks_stripe.py` lines 115–120 return 200 immediately; lines 187–189 swallow all exceptions; the dedup row in `stripe_webhook_event_processed` is written **before** processing). A raised exception is NOT retried by Stripe. Every new failure mode you add must be caught, `logger.error(...)`'d, and swallowed.
- **`db.get()` is banned** on tenant-scoped models — tenant-scoped `select()` with explicit `WHERE` only.
- **Sync-by-design (rules §21)**: all service functions you touch are sync `def`. Do not convert anything to `async def`. (The webhook *route* is `async def` because it awaits `request.body()` — leave it exactly as it is; out of scope.)
- **Rule 14 (Ruff)**: changed files only — `git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||'`, then `ruff check --fix` + `ruff format` + `ruff check`. Fix ALL errors in those files, including pre-existing ones on lines you didn't touch.
- **No new endpoints → no `set_audit_context_sync` changes, no OpenAPI regen.** The only route-layer behavior change is internal to an existing service called by an existing route.
- **Pydantic v2 only; money is integer cents.** No new schemas expected — if you find you need one, STOP and ask Tom (scope signal).

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**. If anything is already failing, do NOT proceed — either confirm the known/accepted reason with Tom or fix it first. (Last recorded full-suite state: 4463 passed / 0 failed with `requires_stripe`+`requires_telnyx` deselected, post-ALPHA-FIX-1; PLP-STRIPE-CHARTER-ROW-1 added tests on top.)

---

## Pre-Work: Run MCP Verification Queries (`postgres-local`)

> **MCP Usage Rule**: `postgres-local` is **read-only verification only** — never INSERT/UPDATE/DELETE. All data changes go through application code. If a query errors → STOP and ask Tom. This batch needs **no** `postgres-prod` access; do not use it.

Run **all** of these before writing any code. If any result is unexpected → STOP and ask Tom.

```sql
-- 1. subscription columns — the table Task 1 updates (status flip)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription'
ORDER BY ordinal_position;

-- 2. subscription_status codes — resolve by code, never hardcode UUIDs.
--    Expected 6 rows: active(t), canceled(f), past_due(t), paused(f), trialing(t), unpaid(f)
SELECT code, name, is_billing_active
FROM public.subscription_status
ORDER BY code;

-- 3. subscription_tier — confirm Charter has NULL price columns (why the
--    price-ID lookup misses and the metadata fallback exists)
SELECT tier_id, tier_name, product_plan_code,
       stripe_price_id_monthly, stripe_price_id_annual, signup_cap
FROM public.subscription_tier
ORDER BY display_order;

-- 4. tenant_tier_override columns — the table Task 5 validates an FK into
--    (set_by_operator_user_id is NOT NULL — that is the FK being guarded)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_tier_override'
ORDER BY ordinal_position;

-- 5. Sanity: current alembic head (this batch has NO migration)
SELECT version_num FROM public.alembic_version;
```

**Expected (Architect-verified 2026-08-12):** `subscription` has 21 columns including `status_id`, `psp_subscription_id`, `trial_ends_at`, `is_active`, `stripe_schedule_id`; `subscription_status` has the 6 codes above; Charter tier row has NULL `stripe_price_id_monthly`/`_annual` and non-null `product_plan_code`; `tenant_tier_override.set_by_operator_user_id` is `uuid NOT NULL`.

---

## Pre-Work: Read These Source Files

- `backend/services/stripe_subscriptions.py` — the core file. Study: `handle_subscription_created()` (≈109–295, including the PLP Charter fallback at ≈161–199), `_add_metered_overage_items()` (≈574–622), `_write_local_charter_subscription_row()` (≈625–742), `create_charter_subscription()` (≈745–819), `resume_subscription()` (≈822–928, note step 7b at ≈897–902), `upgrade_charter_to_teams()` (≈931+, note the `getattr` pattern at ≈1009–1012), `handle_subscription_resumed()` (≈1271–1303). **Line numbers will have shifted — navigate by function name.**
- `backend/api/routes/webhooks_stripe.py` — full file. Confirm: `customer.subscription.created` AND `customer.subscription.updated` both route to `handle_subscription_created()` (≈147–151) — **one fix covers both events**. Note the dedup-before-processing design (your error handling must not rely on Stripe retries).
- `backend/services/cohort_dashboard.py` — `extend_free_period()` (≈153–266).
- `backend/api/routes/cohort_dashboard.py` — `extend_member_free_period()` route (≈66–122): it already passes `operator_user_id=platform_user.id` (the authenticated platform user) and maps `ValueError` messages containing "not found" → 404 RFC 7807. Task 5 leverages both.
- `backend/core/auth.py` — `PlatformUser` (≈439–471): `.id` is `user.id` — a real `user`-table UUID, so the FK is satisfiable.
- `backend/api/schemas/cohort.py` — `ExtendFreePeriodRequest` (≈42–46): only `new_free_period_ends_at` + `override_reason` — **no** client-supplied operator ID. Do not add one.
- `backend/scripts/stripe_bootstrap.py` — Tasks 3+4. Study: `_load_existing_ids()` / `_save_ids()` (≈321–343), `_meta()` / `_metadata_to_dict()` (≈356–380 — already StripeObject-safe), `mode_audit()` (≈449–511 — the `pkey` bug is in the meters loop), `mode_create()` (≈603+ — the three `existing = ids[...].get(...) or _find_*` cache-read sites), `main()` argparse block (≈891+).
- `backend/core/stripe_config.py` — `get_stripe_ids()` (per-mode `stripe_ids.{mode}.json` loader).
- `backend/tests/domains/subscriptions_usage/test_cb4_resume_subscription.py` — the mock pattern for `_add_metered_overage_items` (side_effect list of subscription retrieves + mocked `get_stripe_ids`, ≈80–103). Reuse it.
- `backend/tests/domains/subscriptions_usage/test_plp_stripe_charter_row_1.py` — `TestWebhookCharterMetadataFallback` fixtures: how to stand up a Charter tenant + tier + call the webhook handler directly.
- `backend/tests/domains/platform_infrastructure/test_cb11_cohort_dashboard.py` — `TestExtendFreePeriod` (≈326–420): existing service-level tests you will extend in Task 5.
- `backend/tests/conftest.py` — available fixtures.
- `backend/db_models_map.md` — confirm `Subscription`, `SubscriptionStatus`, `SubscriptionTier`, `TenantTierOverride`, `User` model/module locations before importing.

Also run: `grep -rn "handle_subscription_created\|_add_metered_overage_items" backend/ --include="*.py" -l` to catch any caller not listed above.

---

## Background / Context

The C-B14 live Stripe test-clock suite (2026-08-08) surfaced five follow-ups, catalogued in `c-b14-testing-findings.md` §1/§2/§5/§6/§7 and carried in the launch plan §2.3 as **C-B14-FIX**. Charter signup now works end to end on the pre-release AWS environment (the author's own test signups; ALPHA-FIX-1 ✅, PLP-STRIPE-CHARTER-ROW-1 ✅) — which makes **Task 1 a billing gap that would hit the first real customers**: as built, a Charter member who adds a payment method during trial auto-converts to `active` at trial end, but the metered overage items (`price_voice_overage`, `price_sms_overage`) are never attached — Stripe silently never invoices overage for that tenant. The metered items cannot be attached at creation time (Stripe rejects metered items on pause-at-trial-end subscriptions — findings §1), so they are attached post-activation by `_add_metered_overage_items()` — which today is only called from `resume_subscription()` and `upgrade_charter_to_teams()`. The auto-conversion webhook path was missed.

## Design Decisions (Architect-resolved — do not re-litigate; questions → STOP and ask Tom)

- **D1 — One handler covers both events.** `customer.subscription.created` and `customer.subscription.updated` both dispatch to `handle_subscription_created()` (`webhooks_stripe.py` ≈147–151). The fix lives in that one function.
- **D2 — Gate on the payload's `status`.** Only `status == "active"` triggers metered-item provisioning. `trialing` subscriptions keep the pause-at-trial-end config (we WANT pause-on-missing-PM at trial end) and Stripe would reject metered items while that config is present.
- **D3 — Both branches get the fix.** (a) the Charter metadata fallback branch (price lookup misses → `metadata.tier_code == 'charter'`), and (b) the normal tier branch (Starter/Teams match by price ID — the GA signup payment path doesn't exist yet, but `subscription.updated` fires on every plan change/resume, and `upgrade_charter_to_teams()` already assumes metered items exist for Teams).
- **D4 — Charter branch also flips local status trialing→active.** On auto-conversion, Stripe fires `subscription.updated` with `status='active'` — but `customer.subscription.resumed` only fires for *paused* subs, and `handle_invoice_paid()` only logs. Without the flip, the local row stays `trialing` forever (cohort dashboard + `extend_free_period()`'s trialing-gate both read it). The flip resolves `status_id` by `code='active' AND is_billing_active=True` — never a hardcoded UUID. **Do not null `tenant.free_period_ends_at`** — natural trial expiry leaves it in the past, which is factually correct (only the early-upgrade flow nulls it).
- **D5 — Out-of-order guard.** Stripe does not guarantee webhook ordering. If the local row's current status is already `active` and the payload says `trialing` (stale/late event), skip the rewrite and log — never demote active→trialing.
- **D6 — Metered-step failure is logged, never raised.** Wrap the `_add_metered_overage_items()` call in `try/except Exception` → `logger.error(...)` with tenant + subscription IDs → continue. Rationale: the webhook path is fire-and-forget (dedup row written pre-processing; 200 already returned; `BackgroundTasks` swallows). A missed add self-heals on the next `subscription.updated`, `resume_subscription()`, or `upgrade_charter_to_teams()` (the helper is idempotent). Known residual risk, feeds the INT-H1 queued-retry tech-debt item — do NOT redesign the dedup/retry mechanics in this batch.
- **D7 — StripeObject ≠ dict.** `.get()` is safe ONLY on webhook payload dicts (`json.loads` output: `stripe_event`, `payload`, `event_data`) and plain config dicts (e.g. `METERS`, `PRICES`). Any object returned by the Stripe SDK (`stripe.*.retrieve/create/modify/list`, `auto_paging_iter`, and attributes thereof) is a `StripeObject` — `.get()` raises `AttributeError`. Use `getattr(obj, "attr", default)`, `obj["key"]`, or the existing `_meta()` / `_metadata_to_dict()` helpers.
- **D8 — Task 5 is validation-only.** The route already passes the authenticated `platform_user.id` and the request schema carries no operator field — verified by the Architect. The gap is service-level: `extend_free_period()` must validate `operator_user_id` exists in `user` before writing `tenant_tier_override`, raising `ValueError("... not found ...")` so the existing route mapping returns 404 RFC 7807 instead of a raw `ForeignKeyViolation` 500.

---

## Task 1 — Webhook metered-item provisioning (trial→active auto-conversion) — findings §1

**File**: `backend/services/stripe_subscriptions.py`, function `handle_subscription_created()`.

1. Near the top of the function (after the payload extraction at ≈123–125), add:
   ```python
   payload_status = subscription.get("status")
   ```
2. **Charter fallback branch** (the `tier_code == "charter"` block added by PLP-STRIPE-CHARTER-ROW-1, ≈167–197). After the `_write_local_charter_subscription_row(...)` call:
   - **Out-of-order guard (D5)**: before writing, load the existing row (`select(Subscription).where(Subscription.psp_subscription_id == stripe_subscription_id)`) and, if present, resolve its current status code via `SubscriptionStatus`. If current code is `'active'` and `payload_status == 'trialing'` → `logger.info(...)` and `return` (stale event; no demotion).
   - If `payload_status == "active"`:
     1. Flip the local row: resolve `active_status` via `select(SubscriptionStatus).where(code=='active').where(is_billing_active == True)`; set `sub_row.status_id = active_status.id`; `db.add(sub_row); db.commit()`. (Reuse the exact resolution pattern at ≈215–219.)
     2. Ensure metered items:
        ```python
        try:
            stripe = _get_stripe_client()
            _add_metered_overage_items(stripe, stripe_subscription_id)
        except Exception:
            logger.error(
                "handle_subscription_created: failed to add metered overage "
                "items for tenant %s (sub %s) — self-heals on next "
                "subscription.updated / resume / upgrade",
                tenant.id, stripe_subscription_id, exc_info=True,
            )
        ```
   - `payload_status == "trialing"` (or anything else) → existing behavior unchanged (write trialing row, no metered call).
3. **Normal tier branch** (after the existing upsert + `db.commit()` at ≈289–290): if `payload_status == "active"`, run the same guarded `_add_metered_overage_items` block (D3/D6). Acquire `_get_stripe_client()` lazily inside the `status == "active"` branch only — do not change behavior for trialing/paused payloads.
4. Do **not** touch: the `create_subscription()` GA helper, `handle_subscription_resumed()`, `handle_invoice_paid()`, the dedup mechanics, or the webhook route.

**Checkpoint**: `python -m pytest -m unit --tb=short -q tests/domains/subscriptions_usage/ 2>&1 | tail -5` — all green before moving on.

## Task 2 — `.get()`-on-StripeObject audit — findings §2

**Scope**: every Stripe SDK call site in the codebase. The C-B14 live run proved MagicMock-based tests cannot catch this (mocks support `.get()`; real `StripeObject`s don't).

1. Find candidate sites:
   ```bash
   cd <repo>/backend
   grep -rn "stripe\.\(Customer\|Subscription\|PaymentMethod\|Price\|Product\|Invoice\|Charge\|billing\|test_helpers\)\." --include="*.py" services/ api/ scripts/ core/ tasks/ | grep -v tests
   grep -rn "\.get(" --include="*.py" services/stripe_subscriptions.py services/stripe_payment_intents.py services/trial_management.py services/tenant_signup.py scripts/stripe_bootstrap.py api/routes/signup.py
   ```
2. For each `.get(` hit, classify the receiver per **D7**: payload/plain dict → safe, leave it. SDK return object (or an attribute of one) → **fix** to `getattr(obj, "attr", default)` / `obj["key"]` / `_meta()`.
3. Known-safe (already fixed in C-B14 — verify, don't re-edit): `upgrade_charter_to_teams()` (≈1009–1012), `_add_metered_overage_items()` (≈609), `_find_meter_by_key()` (≈421–422), `_meta()` / `_metadata_to_dict()` (≈356–380).
4. **Deliverable**: an audit table in your Completion Summary — every inspected file, every `.get()` site, verdict (safe-dict / fixed / already-safe). Expected result is few or zero fixes; if you find ≥3 real defects, STOP and flag Tom before fixing (scope signal).

## Task 3 — `stripe_bootstrap.py --force` flag — findings §5

**File**: `backend/scripts/stripe_bootstrap.py`.

1. `main()` argparse block (≈891+): add
   ```python
   parser.add_argument(
       "--force",
       action="store_true",
       help="Ignore cached stripe_ids.{mode}.json and re-query Stripe for "
            "every object (use after purging the Stripe account).",
   )
   ```
2. Thread `force: bool = False` through to `mode_create(mode, dry_run, force)`. In each of the three loops (products ≈613, meters ≈637, prices ≈665), change the cache read so `--force` bypasses only the **JSON cache** half — the live Stripe lookup always runs:
   ```python
   existing = (None if force else ids["products"].get(pkey)) or _find_product_by_pilot_key(pkey)
   ```
3. At the top of `mode_create`, when `force`: `_log("FORCE: ignoring cached stripe_ids.%s.json — querying Stripe for all objects", mode)`. `_save_ids` behavior is unchanged (fresh truth overwrites the cache at the end).
4. Scope: `mode_create` only. `--audit` never reads the cache; `mode_adopt_existing` / `--migrate-prices` are out of scope.
5. **Docs**: add the flag to `backend/scripts/README-stripe-bootstrap.md` and one line to the bootstrap section of `stripe-ops-runbook.md` (use case: after purging the Stripe test account, `--force` re-discovers live objects instead of trusting stale `stripe_ids.test.json`).

## Task 4 — `mode_audit()` meters-loop `pkey` bug — findings §6

**File**: `backend/scripts/stripe_bootstrap.py`, `mode_audit()` (≈485–494).

- The meters loop logs `pilot_key={pkey!r}`, but `pkey` is only bound by the *prices* loop above it — with an empty prices list it raises `UnboundLocalError`; with a non-empty list it logs the **stale last price key** (meters don't support metadata, so there is no pilot_key to show).
- Fix: drop the `pilot_key={pkey!r}` fragment from the meters-loop `_log(...)` call (the `event={meter.event_name!r}` fragment already identifies the meter). Do not restructure anything else in the function.

## Task 5 — `extend_free_period()` operator FK validation — findings §7

**File**: `backend/services/cohort_dashboard.py`, `extend_free_period()` (≈153–266).

1. After the tenant/Charter checks (≈176–181) and **before** the `tenant_tier_override` upsert (≈212), add:
   ```python
   from app.models.<user module> import User  # verify module via db_models_map.md

   operator = db.exec(select(User).where(User.id == operator_user_id)).first()
   if not operator:
       raise ValueError(
           f"Operator user {operator_user_id} not found — cannot record override"
       )
   ```
   The existing route maps any `ValueError` containing "not found" → 404 RFC 7807 (`cohort_dashboard.py` ≈100–109) — no route or schema change.
2. Do **not** change the route's `operator_user_id=platform_user.id` pass-through (already correct — D8).

**Checkpoint**: `python -m pytest -m unit --tb=short -q tests/domains/platform_infrastructure/test_cb11_cohort_dashboard.py 2>&1 | tail -5`.

---

## Test Requirements

Per `README-adding-tests.md`. One **new** test file + one **extended** file:

**New**: `backend/tests/domains/subscriptions_usage/test_cb14_fix_stripe_hardening.py`

```python
pytestmark = [
    pytest.mark.domain_subscriptions_usage,
    pytest.mark.unit,
]
```

Mock pattern: copy the `MagicMock` side_effect list + mocked `get_stripe_ids` approach from `test_cb4_resume_subscription.py` (≈80–103); Charter-tenant fixtures from `test_plp_stripe_charter_row_1.py` (`TestWebhookCharterMetadataFallback`). Patch `services.stripe_subscriptions._get_stripe_client` and `core.stripe_config.get_stripe_ids`. Never hardcode UUIDs — use `test_tenant` / `test_user` / inserted rows; scope assertions by inserted IDs (shared-seed rule).

Minimum tests:

1. **Charter auto-conversion** — fallback branch, payload `status='active'` → local row `status_id` resolves to the `code='active'` status AND `_add_metered_overage_items` invoked for the sub (assert `Subscription.modify` called with both overage price IDs; `trial_settings` cleared only when present on the retrieve).
2. **Charter trialing unchanged** — payload `status='trialing'` → no Stripe client acquired / no modify; local status stays `trialing`.
3. **Out-of-order guard (D5)** — local row already `active` + payload `status='trialing'` → no demotion (status remains `active`), info-logged.
4. **Normal path idempotency** — tier matched by price ID, `status='active'`, retrieve shows both overage prices already present → **no** `Subscription.modify` call.
5. **Normal path adds missing** — same but metered items absent → modify called once with both price IDs.
6. **Metered failure swallowed (D6)** — force `Subscription.modify` to raise → handler completes without raising, local row still upserted, `logger.error` emitted (caplog).
7. **`--force` bypasses cache (Task 3)** — patch `scripts.stripe_bootstrap._load_existing_ids` to return a stale product ID and `_find_product_by_pilot_key` to return the live ID; `mode_create("test", dry_run=True, force=True)` must choose the live ID; with `force=False` the stale cached ID wins. (`scripts/__init__.py` exists — `from scripts.stripe_bootstrap import mode_create` works.)
8. **Audit loop survives empty prices (Task 4)** — patch `_list_all_products` → `[]`, `_list_all_prices` → `[]`, `_list_all_meters` → one fake meter (`event_name='voice_minutes'`, `status='active'`, `display_name='Voice AI minutes'`); patch the `_find_*` helpers; call `mode_audit("test", dry_run=False)` → returns normally (today: `UnboundLocalError`) and logs the meter line. Read the `_log` definition before writing this (capture via `caplog`/`capsys` as appropriate).

**Extended**: `backend/tests/domains/platform_infrastructure/test_cb11_cohort_dashboard.py` — add to `TestExtendFreePeriod`:

9. **Operator not found (Task 5)** — `extend_free_period(db=db_session, ..., operator_user_id=uuid.uuid4())` → `pytest.raises(ValueError, match="not found")`; assert no `tenant_tier_override` row was written for that tenant and `tenant.free_period_ends_at` is unchanged.

---

## Regeneration + Schema Steps

- **New test file added** → regenerate the import map:
  ```bash
  cd <repo>/backend && source .venv/bin/activate
  python generate_app_import_map.py tests > app_model_imports.md
  ```
- **OpenAPI regen: NOT required** — no endpoint/signature/schema changes (gate considered; explicitly n/a).
- **`db_models_map.md` regen: NOT required** — no SQLModel changes.
- **`schema_manager.py`: NOT required** — no schema change.
- **Seed Data Rollout: NOT required** (§20 gate considered) — this batch adds/modifies **no** DB data: no migration, no lookup rows, no seed-script changes. It changes runtime code paths only. State this explicitly in your Completion Summary.

---

## Final Verification

### Phase 1 — Unit Tests Only (after each task during development)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before moving to the next task — including failures that appear unrelated to your batch.

### Phase 2 — Lint (changed files only) + Full Suite (once, at the end)

```bash
cd <repo>/backend
source .venv/bin/activate

CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')
if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY
    ruff format $CHANGED_PY
    ruff check $CHANGED_PY
fi

# Full suite, live external services deselected (Tom's standing instruction — ALPHA-FIX-1)
python -m pytest --tb=short -q -m "not requires_stripe and not requires_telnyx" 2>&1 | tail -10

# Batch spot checks
python -m pytest tests/domains/subscriptions_usage/test_cb14_fix_stripe_hardening.py -v 2>&1 | tail -25
python -m pytest tests/domains/platform_infrastructure/test_cb11_cohort_dashboard.py -v 2>&1 | tail -10

echo "=== C-B14-FIX FINAL VERIFICATION COMPLETE ==="
```

Warning-clean is part of done: zero remaining ruff issues in changed files, zero `DeprecationWarning` noise in the run. Any failure in either phase must be fixed before declaring done — no "pre-existing" exception without Tom's written confirmation.

---

## Definition of Done

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) with `pytest -m unit`
- [ ] Zero unexplained pre-existing failures before starting
- [ ] All 5 MCP pre-work queries run; results match the §Pre-Work expectations (every touched table verified via `information_schema.columns`, rules §25)
- [ ] All mandatory source files read before writing code
- [ ] **Task 1**: metered-item provisioning on `status='active'` in BOTH the Charter fallback and normal tier branches; Charter status flip trialing→active by code-resolution; out-of-order guard (D5); failure-swallow with `logger.error` (D6); lazy `_get_stripe_client()`
- [ ] **Task 2**: `.get()` audit executed across all Stripe SDK call sites; fixes applied per D7; audit table produced for the Completion Summary
- [ ] **Task 3**: `--force` flag + `force` threading through `mode_create` (all 3 loops); `README-stripe-bootstrap.md` + `stripe-ops-runbook.md` updated
- [ ] **Task 4**: meters-loop `pkey` fragment removed; audit no longer crashes on empty prices
- [ ] **Task 5**: `operator_user_id` existence validation raising `ValueError("... not found ...")` before the override upsert; no route/schema change
- [ ] All DB-touching code is sync `def` (rules §21); no `db.get()`; no hardcoded status UUIDs / price IDs / plan codes
- [ ] No new endpoints → no OpenAPI regen, no `set_audit_context_sync` additions (verified n/a)
- [ ] All new tests use `pytestmark` (domain + unit), `client`/session fixtures, inserted-ID scoping — no hardcoded UUIDs, no total-count assertions
- [ ] `python generate_app_import_map.py tests > app_model_imports.md` run (new test file)
- [ ] `ruff check --fix && ruff format && ruff check` on **changed files only** — zero remaining issues, no unjustified `# noqa`
- [ ] **Phase 1**: all unit tests pass
- [ ] **Phase 2**: full suite passes with `-m "not requires_stripe and not requires_telnyx"` — zero failures, warning-clean
- [ ] Final test count (before → after) documented
- [ ] Completion Summary appended (see below)

---

## Completion Summary

After all DoD items are complete:

1. Append a **Completion Summary** to `pilot-launch-plan.md` **Appendix C** (end of file — per the plan's maintenance protocol), using this format:

```markdown
### C-B14-FIX — Post-C-B14 Stripe Hardening Follow-Ups: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished
- [Task 1 outcome — webhook metered-item provisioning + status flip + guard]
- [Task 2 outcome — audit result counts: sites inspected / safe / fixed]
- [Task 3 outcome — --force flag]
- [Task 4 outcome — audit bug fix]
- [Task 5 outcome — FK validation]

#### Task 2 Audit Table
| File | `.get()` site | Verdict (safe-dict / fixed / already-safe) |
|---|---|---|

#### Files Changed / Created
| File | Action |
|---|---|

#### Tests Added
| Test File | Domain | Tests | All Pass |
|---|---|---|---|

#### Seed Data Rollout
Not required — no migration, no lookup rows, no seed-script changes (runtime code only).
```

2. **Source-spec updates (mandatory)**: in `c-b14-testing-findings.md` "Summary of Architect Action Items", mark items **2, 3, 4, 5, 6** ✅ with a one-line outcome each. (Items 1, 7, 8 are Architect-owned doc updates — leave them.)
3. In `pilot-launch-plan.md`: mark §2.0 master row 7 ✅ with the one-line outcome and update the §2.3 C-B14-FIX card status line.

---

## After This Task — Next Step

C-B14-FIX closes the Stripe hardening lane of Execution Order 4. Remaining in that order: **C-B16** (Pilot-hosted tenant SMS compliance pages — Architect designs) → **PLATFORM-SMS-B2** (Samples 3+4 senders, §2.4). No frontend handoff is needed for this batch (no OpenAPI change — `pnpm sync-api-types` is NOT required).
