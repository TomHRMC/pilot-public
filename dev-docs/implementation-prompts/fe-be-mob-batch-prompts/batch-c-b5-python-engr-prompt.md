# Implementation Prompt: C-B5 (Part A — Python Engineer) — Wizard Step 4/5 Conditional Logic + Cohort Cap + Checklist Item

**Mode**: Pilot Python Engineer  
**Batch**: C-B5 Part A  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.0 row 14j  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-c-b5-design.md`  
**Estimated session**: 3–4 hours  
**Platform**: Backend only (`backend/`)  
**Frontend companion**: C-B5 Part B (React Engineer) — runs after this batch closes + `pnpm sync-api-types`. **Requires UI design spec (Tom-gated) before React Engineer starts.**

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; this governs all test file structure, domain markers, and fixture rules

**Before writing any subscription, billing, or entitlement code:**
Read `dev-docs/pilot-operations.md` — covers: tier→plan→ppfv cascade, `is_billing_active` paywall gate, Charter cohort Stripe schedule, notification template resolution order, and all 6 subscription status codes. The billing logic is NOT inferrable from the schema alone.

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 2**: After any model file change → regenerate `backend/db_models_map.md` via `python generate_db_model_map.py app > db_models_map.md`.
- **Rule 3**: After any endpoint change → run `python export_openapi_json.py` (updates both `openapi.json` and `openapi_schema_map.md`).
- **Rule 4**: All Alembic migrations must be written as **blank** migrations (never `--autogenerate`). Data changes use raw `op.execute()` with `SET LOCAL session_replication_role = 'replica';`.
- **Rule 6**: `db.get()` is permanently banned on tenant-scoped models. Always use tenant-scoped `select()` with an explicit `WHERE tenant_id = :tid` clause.
- **Rule 8**: All API error responses MUST follow RFC 7807 Problem Details format.
- **Rule 9**: Every mutation endpoint MUST call `set_audit_context_sync(db, user_id=user.id)` before committing.
- **Rule 11**: If ANY test fails during your work — even one that appears to be a pre-existing failure — **you must fix it before declaring the batch done**.
- **Rule 12 (sync routes)**: Every DB-touching route and `_impl()` is a plain `def` — never `async def`.
- **Rule 13 (Pydantic v2)**: Use v2 idioms only. `model_config = ConfigDict(...)`, `@field_validator`, `.model_dump()`. Money is always integer cents.
- **Rule 15 (audit mixins)**: New tables inherit exactly one mixin from `app/models/mixins.py`. This batch adds a column to an existing table — no new table.
- **Rule 16 (verify, don't assume)**: 186 tables exist. Query `information_schema.columns` for every table you touch this session before writing SQL.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed anyway. Either:
> (a) Confirm with Tom that this is a known, accepted failure with a documented reason before proceeding, OR
> (b) Fix the failure before touching any batch files.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Use it to confirm table names, column types, and existing data. Never use it to INSERT, UPDATE, or DELETE — all data changes go through the application code, seed scripts, or Alembic migrations. If a query fails or returns an error → STOP and ask Tom before proceeding.

```sql
-- 1. Verify tenant_onboarding_checklist columns (confirm no messaging_setup column exists yet)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_onboarding_checklist'
ORDER BY ordinal_position;

-- 2. Verify subscription_tier columns (free_period_days, requires_payment_method, signup_cap, price_locked, is_active)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription_tier'
ORDER BY ordinal_position;

-- 3. Verify tenant columns (free_period_ends_at, charter_member_number, charter_eligible, stripe_customer_id)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant'
ORDER BY ordinal_position;

-- 4. Verify charter tier values
SELECT tier_name, tier_id, free_period_days, requires_payment_method, signup_cap, price_locked, is_active
FROM subscription_tier WHERE tier_name = 'charter';

-- 5. Verify charter_member_number UNIQUE constraint exists
SELECT conname, contype FROM pg_constraint
WHERE conrelid = 'public.tenant'::regclass AND conname LIKE '%charter_member%';

-- 6. Verify current alembic head
SELECT version_num FROM public.alembic_version;
```

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/services/tenant_signup.py              ← why: _process_step_data() step4_tier + step5_confirm handlers to modify
backend/api/routes/signup.py                   ← why: wizard routes — step 4/5 endpoints
backend/api/routes/onboarding_checklist.py     ← why: checklist response schema + _get_checklist_impl to update
backend/app/models/onboarding.py               ← why: TenantOnboardingChecklist model — add messaging_setup field
backend/app/models/core.py                     ← why: Tenant model (free_period_ends_at, charter_member_number, stripe_customer_id)
backend/app/models/subscription.py             ← why: SubscriptionTier model (free_period_days, requires_payment_method, signup_cap)
backend/services/stripe_subscriptions.py       ← why: create_stripe_customer() + create_charter_subscription() (C-B4)
backend/services/onboarding_service.py         ← why: ensure_checklist_exists() function
backend/services/trial_management.py           ← why: activate_trial() — step 5 conditional branching
backend/core/stripe_config.py                  ← why: get_stripe_ids() — used by create_charter_subscription
backend/tests/conftest.py                      ← why: available fixtures
backend/db_models_map.md                       ← why: confirm model names and table mappings
```

Also run these grep commands to find related files:

```bash
grep -rn "_process_step_data\|step4_tier\|step5_confirm" backend/ --include="*.py" -l
grep -rn "ensure_checklist_exists\|TenantOnboardingChecklist" backend/ --include="*.py" -l
```

---

## Background / Context

C-B5 Part A wires the Charter subscription lifecycle into the signup wizard backend. Three changes:

1. **Step 4 (tier selection)**: On Charter tier selection, compute `free_period_ends_at`, assign `charter_member_number` with `signup_cap` enforcement (row lock + `is_active` flip), create Stripe Customer + Charter Subscription
2. **Step 5 (payment/confirmation)**: Branch on `requires_payment_method` — if false (Charter), skip `activate_trial()` and just mark the checklist
3. **Onboarding checklist**: Add `messaging_setup` boolean column (migration)

**One migration required** — add `messaging_setup` column to `tenant_onboarding_checklist`.

### Sync-by-Design (rules §21)

This app is **synchronous by design**: FastAPI 0.135 runs plain `def` routes in a threadpool, and the SQLModel/SQLAlchemy 2.0 `Session` is the **blocking** psycopg2 driver.

- Every route/`_impl()`/service that touches the `Session` MUST be `def` (sync).
- The `with_for_update()` call is a sync SQLAlchemy construct — it works correctly with the sync `Session`.

---

## Task 1 — Alembic Migration: Add `messaging_setup` Column

Create a blank Alembic migration:

```bash
cd <repo>/backend
source .venv/bin/activate
alembic revision -m "c_b5_add_messaging_setup_checklist_column"
```

**Migration content:**

```python
"""c_b5_add_messaging_setup_checklist_column

Revision ID: [auto-generated]
Revises: [current head]
Create Date: 2026-08-04

"""
from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.add_column(
        'tenant_onboarding_checklist',
        sa.Column('messaging_setup', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )
    op.execute("SET LOCAL session_replication_role = 'origin';")


def downgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.drop_column('tenant_onboarding_checklist', 'messaging_setup')
    op.execute("SET LOCAL session_replication_role = 'origin';")
```

**Test the full cycle:**

```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
alembic current   # must show new head revision
```

**Intermediate test run:** `pytest -m unit --tb=short -q | tail -5`

---

## Task 2 — Update `TenantOnboardingChecklist` Model

Add the `messaging_setup` field to `backend/app/models/onboarding.py`:

```python
    # Charter: 10DLC messaging setup (C-B5)
    messaging_setup: bool = Field(
        default=False,
        sa_column=Column(Boolean, server_default=text("false"), nullable=False),
    )
```

Place it after `team_skipped` and before `checklist_hidden` (grouping it with the other completion items).

**Intermediate test run:** `pytest -m unit --tb=short -q | tail -5`

---

## Task 3 — Update Onboarding Checklist Response Schema + Impl

In `backend/api/routes/onboarding_checklist.py`:

1. Add `messaging_setup: bool` to `OnboardingChecklistResponse`
2. Add `messaging_setup=checklist.messaging_setup` to the `_get_checklist_impl()` response construction

**Intermediate test run:** `pytest -m unit --tb=short -q | tail -5`

---

## Task 4 — Update `_process_step_data()` step4_tier Handler

This is the core change. In `backend/services/tenant_signup.py`, replace the existing `step4_tier` block in `_process_step_data()` with the cohort cap + Stripe creation logic from the design doc §F.

**Key implementation details:**

1. **`with_for_update()`** — lock the tier row to prevent concurrent signup cap violations. This is a sync SQLAlchemy construct: `select(SubscriptionTier).where(...).with_for_update()`
2. **Idempotency** — check `tenant.stripe_customer_id` before creating a new Stripe Customer. Check `tenant.charter_member_number` before assigning a new number.
3. **`free_period_ends_at`** — only compute if the tier has `free_period_days` AND the tenant doesn't already have a `free_period_ends_at` (idempotent).
4. **`charter_member_number`** — count existing tenants with non-null `charter_member_number`, assign `count + 1`. Only for charter tier.
5. **`signup_cap` enforcement** — if `tenant.charter_member_number >= tier.signup_cap`, set `tier.is_active = False` in the same transaction.
6. **Stripe Customer + Subscription** — call `create_stripe_customer()` then `create_charter_subscription()` (both from C-B4). Only for charter tier. Non-blocking on failure (log and continue).

**Error handling:**
- Tier not found → 404
- Tier `is_active = false` → 409 with "tier-closed" error (cohort full)
- Stripe API failure → log and continue (non-blocking — wizard still advances)

**Intermediate test run:** `pytest -m unit --tb=short -q | tail -5`

---

## Task 5 — Update `_process_step_data()` step5_confirm Handler

In `backend/services/tenant_signup.py`, update the `step5_confirm` block to branch on `requires_payment_method`:

- **`requires_payment_method = true`** (non-Charter): keep existing `activate_trial()` behavior
- **`requires_payment_method = false`** (Charter): skip `activate_trial()`, mark checklist `tier_selected = True`

The Charter trial is handled by Stripe's `trial_end` — no app-level trial activation needed.

**Intermediate test run:** `pytest -m unit --tb=short -q | tail -5`

---

## Task 6 — Update `get_signup_state()` Response

In `backend/services/tenant_signup.py`, add to the `collected_data` dict in `get_signup_state()`:

```python
"free_period_ends_at": (
    tenant.free_period_ends_at.isoformat()
    if tenant and tenant.free_period_ends_at
    else None
),
"requires_payment_method": (
    tier.requires_payment_method
    if tier
    else True
),
"charter_member_number": (
    tenant.charter_member_number
    if tenant and tenant.charter_member_number
    else None
),
```

You'll need to load the tier from `tenant.current_subscription_tier_id` to get `requires_payment_method`.

**Intermediate test run:** `pytest -m unit --tb=short -q | tail -5`

---

## Task 7 — Write Tests

### Test Requirements

Per `backend/tests/README-adding-tests.md`:

**Domain folder**: `backend/tests/domains/identity_access/` (wizard) + `backend/tests/domains/platform_infrastructure/` (checklist)

**Every new test file MUST:**
- Declare `pytestmark` with both domain marker and `pytest.mark.unit`
- Use the `client` fixture (never module-level `TestClient`)
- Use `test_tenant` and `test_user` fixtures (never hardcoded UUIDs)
- Scope assertions by inserted IDs — never `assert len(all_rows) == N`

**Test files to create:**

| Test File | Domain | Tests | Description |
|---|---|---|---|
| `test_cb5_step4_cohort_cap.py` | `identity_access` | 4 | Charter tier selection assigns `charter_member_number`; `free_period_ends_at` computed; `signup_cap` flips `is_active` at cap; idempotent on re-submit (no duplicate number/customer) |
| `test_cb5_step4_stripe_creation.py` | `identity_access` | 3 | Stripe Customer created; Charter Subscription created with `trial_end`; Stripe failure is non-blocking (wizard still advances) |
| `test_cb5_step5_conditional.py` | `identity_access` | 2 | Charter tier (`requires_payment_method=false`) skips `activate_trial()`; non-Charter tier still calls `activate_trial()` |
| `test_cb5_signup_state_fields.py` | `identity_access` | 2 | `get_signup_state()` returns `free_period_ends_at`, `requires_payment_method`, `charter_member_number` |
| `test_cb5_checklist_messaging.py` | `platform_infrastructure` | 2 | `messaging_setup` field in checklist response; defaults to `false` |

**Mocking Stripe**: Use `unittest.mock.patch` to mock `create_stripe_customer` and `create_charter_subscription` in the step4 tests. Never make real Stripe API calls.

**Intermediate test run after each test file:** `pytest -m unit --tb=short -q | tail -5`

---

## Task 8 — Regenerate OpenAPI + Model Map

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
python generate_db_model_map.py app > db_models_map.md
```

---

## Final Verification Gate

### Phase 1 — Unit Tests Only

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

**Gate**: All unit tests must pass. If any fail → fix before proceeding to Phase 2.

### Phase 2 — Ruff + Full Suite

```bash
# Ruff gate — changed files only
CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')
if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY
    ruff format $CHANGED_PY
    ruff check $CHANGED_PY
fi

# Full test suite
python -m pytest --tb=short -q 2>&1 | tail -10
```

**Gate**: Ruff must be clean on all changed files. Full suite must pass (0 failures).

---

## Definition of Done

### Phase 1 (Unit Tests)
- [ ] Alembic migration created + tested (upgrade/downgrade/upgrade cycle)
- [ ] `TenantOnboardingChecklist` model updated with `messaging_setup` field
- [ ] `OnboardingChecklistResponse` schema + `_get_checklist_impl()` updated
- [ ] `_process_step_data()` step4_tier handler updated with cohort cap + Stripe creation
- [ ] `_process_step_data()` step5_confirm handler updated with `requires_payment_method` branching
- [ ] `get_signup_state()` returns `free_period_ends_at`, `requires_payment_method`, `charter_member_number`
- [ ] All unit tests pass (`pytest -m unit`)

### Phase 2 (Full Suite)
- [ ] `python export_openapi_json.py` run
- [ ] `python generate_db_model_map.py app > db_models_map.md` run
- [ ] Ruff clean on all changed files
- [ ] Full test suite passes (`pytest --tb=short -q`)
- [ ] No new warnings in test output

---

## Completion Summary

When done, append a completion summary to `dev-docs/analysis/pilot-launch-plan.md` Appendix B using the standard format. Also:
1. Add a one-row entry to Appendix A (Completed Work Registry)
2. Mark C-B5 Part A as ✅ in the §2.0 Master Status Table

---

## Handoff Instructions

After Part A is complete:

1. Run `python export_openapi_json.py` — the updated `SignupStateResponse` (with `free_period_ends_at`, `requires_payment_method`, `charter_member_number`) and `OnboardingChecklistResponse` (with `messaging_setup`) must be in the OpenAPI spec.
2. Commit all changes.
3. Notify the React Engineer that Part A is complete and `pnpm sync-api-types` can be run.
4. **⚠️ React Engineer cannot start until the UI design spec is Tom-approved** (see design doc §H). The design spec must be authored by the `pilot-web-ui-designer` mode and cover: wizard step 4 Charter tier card, step 5 confirmation branch, checklist messaging item, and Charter Member badge.
