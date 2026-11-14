# Implementation Prompt: SD-3 — Group B Platform Seed Audit & Billing Schema Expansion

**Mode**: Pilot Python Engineer  
**Batch**: SD-3  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2 P1 — DB Management Strategy  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-sd3-design.md`  
**Estimated session**: 4–5 hours  
**Platform**: Backend only (`backend/`)  
**Frontend companion**: None — STRIPE-B1 (annual billing service layer) must follow immediately after SD-3

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, and fixture rules

**Critical rules for this batch:**

- **Rule 1**: Never guess column names. Use `postgres-local` MCP to verify every column name before use. **This batch renames existing columns** — the old names no longer exist after the migration. If MCP returns unexpected results → **STOP and ask Tom**.
- **Rule 2**: **Blank Alembic migrations only** — never `--autogenerate`. Use `alembic revision -m "descriptive_name"`. Both migrations in this batch use `SET LOCAL session_replication_role = 'replica';` because they touch FK columns.
- **Rule 3**: **Always implement `downgrade()`** — the column renames must be exactly reversed.
- **Rule 4**: After any model file change → run `python generate_db_model_map.py` to regenerate `backend/db_models_map.md`.
- **Rule 5**: `db.get()` is permanently banned on tenant-scoped models. Always use `select()` with explicit tenant scope.
- **Rule 6**: Never use module-level `TestClient`. Always use the `client` fixture.
- **Rule 7**: The `postgres-local` MCP is **read-only verification only**. Never use it to INSERT/UPDATE/DELETE.
- **Rule 8**: After SD-3 deploys, `stripe_subscriptions.py` will reference `tier.stripe_price_id` which no longer exists (renamed to `stripe_price_id_monthly`). This is **intentional and acceptable pre-GA** — no real paid tenants exist. Flag this in your Completion Summary. STRIPE-B1 fixes it.
- **Rule 9**: All new test files must use `pytestmark` with domain marker + `pytest.mark.unit`. Scope all assertions by inserted IDs — never assert on total row counts.
- **Rule 10**: The `seed_platform.py` script's `mode_seed()` also contains an idempotent stripe_price_id **patch block** (step 4b in the existing script). Update this block to reference the renamed column `stripe_price_id_monthly`.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current unit-only test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed. Either confirm with Tom that this is a known, accepted failure, or fix it before touching any batch files. You may NOT start implementation while tests are in an unexplained failed state.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

> **MCP Usage Rule**: Read-only verification only. Never INSERT/UPDATE/DELETE via MCP.

```sql
-- 1. Verify subscription_tier current columns (CRITICAL — batch renames these)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription_tier'
ORDER BY ordinal_position;
-- Expected: monthly_price_cents (NOT annual_price_cents), stripe_price_id (NOT stripe_price_id_monthly)
-- If annual_price_cents already exists → migration already ran; verify and adjust accordingly

-- 2. Verify product_plan current codes
SELECT code, name, is_active FROM public.product_plan ORDER BY code;
-- Expected: founders_plan, starter_plan, teams (NOT teams_plan)
-- If teams_plan already exists → Migration 1 already ran; skip Task 1

-- 3. Verify product_plan_version current price_cents
SELECT product_plan_code, price_cents
FROM public.product_plan_version
ORDER BY product_plan_code;
-- Expected: founders_plan=4900 (WRONG — to be fixed), starter_plan=4900, teams=14900

-- 4. Verify subscription rows referencing 'teams' plan code (cascade scope check)
SELECT COUNT(*) AS sub_rows_with_teams
FROM public.subscription
WHERE product_plan_code = 'teams';

-- 5. Verify ppfv rows referencing 'teams'
SELECT COUNT(*) AS ppfv_rows_with_teams
FROM public.product_plan_product_feature_version
WHERE product_plan_code = 'teams';

-- 6. Verify current notification_template gap
SELECT notification_type_code, COUNT(*) AS channel_count
FROM public.notification_template
WHERE tenant_id IS NULL
GROUP BY notification_type_code
ORDER BY notification_type_code;
-- Expected: 3 types × 3 channels = 9 rows (customer_communication_sent, dunning_reminder, quote_accepted)
-- Missing: job_assigned, schedule_changed, qb_sync_conflict, qb_conflict_pre_warning, gps_variance_alert, system_template_updated

-- 7. Verify all 9 active notification_type codes
SELECT code FROM public.notification_type WHERE is_active = true ORDER BY code;
-- Expected: 9 codes (3 original + 6 added by SD-2)

-- 8. Verify current Alembic head
SELECT version_num FROM public.alembic_version;
```

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/app/models/subscription.py              ← SubscriptionTier SQLModel class — field names to rename
backend/migrations/scripts/seed_platform.py     ← Full Group B seed script — 6 changes required
backend/services/stripe_subscriptions.py        ← Reads tier.stripe_price_id — note the breakage after rename (STRIPE-B1 fixes)
backend/migrations/versions/2026_07_09_2021-1635c1bf1d1b_mkt_b11_pricing_model_v3_schedule_lanes.py  ← Most recent migration to product_plan/subscription_tier — pattern reference
backend/tests/README-adding-tests.md            ← Test file rules (mandatory full read)
backend/tests/conftest.py                       ← Available fixtures (scan for subscription-related fixtures)
backend/db_models_map.md                        ← Current model map — verify before and after
```

Also run:
```bash
grep -rn "stripe_price_id\|monthly_price_cents\|teams_plan\|product_plan_code" backend/app/ --include="*.py" -l
grep -rn "stripe_price_id\|monthly_price_cents" backend/api/ --include="*.py" -l
grep -rn "stripe_price_id\|teams_plan\|product_plan_code" backend/tests/ --include="*.py" -l
```

These greps will show you every file that references the columns being renamed. Note them — you must verify none of them break.

---

## Background

This batch closes the Group B (`seed_platform.py`) audit that was run during the SD-2 session on 2026-07-14. The audit found:

1. **Naming inconsistency**: `product_plan.code = 'teams'` should be `'teams_plan'` to match `founders_plan`/`starter_plan` convention.
2. **`product_plan_version` price bug**: `founders_plan` price_cents = 4900 (wrong — set by MKT-B11 migration). The founders plan list price is $0 during the cohort. The $49/mo billing that activates at month 7 is a Stripe Subscription Schedule event (STRIPE-B1 scope), not a plan-price change.
3. **Annual billing schema missing**: `subscription_tier` only has one price column (`monthly_price_cents`) and one Stripe price ID (`stripe_price_id`). The product has two billing intervals: annual (default, $49/$149/mo expressed as per-month) and month-to-month (premium, $59/$179/mo). The schema must support both.
4. **Notification template gap**: SD-2 added 6 new `notification_type` rows. None of them have `notification_template` rows (18 rows missing: 6 types × 3 channels).

**Batch scope**: Schema migrations + SQLModel model updates + `seed_platform.py` update + 18 notification template rows + 2 new documentation files. No new API endpoints. No Celery tasks.

---

## Task 1 — Alembic Migration 1: `teams` → `teams_plan` Rename (FK Cascade)

### What to do

Create a blank Alembic migration that renames `product_plan.code = 'teams'` to `'teams_plan'` and cascades the rename to all FK child tables.

```bash
cd <repo>/backend
source .venv/bin/activate
alembic revision -m "sd3_teams_plan_rename"
```

### Migration content

```python
"""SD-3: Rename product_plan code 'teams' → 'teams_plan' with FK cascade."""

def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # Rename the plan code
    op.execute("""
        UPDATE public.product_plan
        SET code = 'teams_plan', updated_at = NOW()
        WHERE code = 'teams';
    """)

    # Cascade to product_plan_version
    op.execute("""
        UPDATE public.product_plan_version
        SET product_plan_code = 'teams_plan'
        WHERE product_plan_code = 'teams';
    """)

    # Cascade to product_plan_product_feature_version
    op.execute("""
        UPDATE public.product_plan_product_feature_version
        SET product_plan_code = 'teams_plan'
        WHERE product_plan_code = 'teams';
    """)

    # Cascade to subscription_tier
    op.execute("""
        UPDATE public.subscription_tier
        SET product_plan_code = 'teams_plan', updated_at = NOW()
        WHERE product_plan_code = 'teams';
    """)

    # Cascade to subscription (may have rows for test tenant)
    op.execute("""
        UPDATE public.subscription
        SET product_plan_code = 'teams_plan', updated_at = NOW()
        WHERE product_plan_code = 'teams';
    """)


def downgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("UPDATE public.subscription SET product_plan_code = 'teams', updated_at = NOW() WHERE product_plan_code = 'teams_plan';")
    op.execute("UPDATE public.subscription_tier SET product_plan_code = 'teams', updated_at = NOW() WHERE product_plan_code = 'teams_plan';")
    op.execute("UPDATE public.product_plan_product_feature_version SET product_plan_code = 'teams' WHERE product_plan_code = 'teams_plan';")
    op.execute("UPDATE public.product_plan_version SET product_plan_code = 'teams' WHERE product_plan_code = 'teams_plan';")
    op.execute("UPDATE public.product_plan SET code = 'teams', updated_at = NOW() WHERE code = 'teams_plan';")
```

### Apply and verify

```bash
alembic upgrade head

# Verify rename applied
# Use postgres-local MCP:
# SELECT code FROM public.product_plan ORDER BY code;
# Expected: founders_plan, starter_plan, teams_plan (NOT 'teams')

# Verify cascade
# SELECT product_plan_code FROM public.subscription_tier WHERE product_plan_code LIKE 'teams%';
# Expected: teams_plan
```

### Intermediate unit test check

```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

Fix any failures before proceeding.

---

## Task 2 — Alembic Migration 2: Annual Billing Schema + Founders Price Fix

### What to do

Create a second blank Alembic migration that:
1. Renames `subscription_tier.monthly_price_cents` → `annual_price_cents`
2. Renames `subscription_tier.stripe_price_id` → `stripe_price_id_monthly`
3. Adds `subscription_tier.monthly_price_cents` (new column — month-to-month premium price)
4. Adds `subscription_tier.stripe_price_id_annual` (new column — NULL until Tom creates annual Stripe prices)
5. Fixes `product_plan_version.price_cents` for `founders_plan` from 4900 → 0

```bash
alembic revision -m "sd3_annual_billing_schema"
```

### Migration content

```python
"""SD-3: Annual billing schema — column renames + additions + founders_plan price fix."""
import sqlalchemy as sa


def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # ── Step 1: Rename existing columns ──────────────────────────────────────
    # monthly_price_cents → annual_price_cents
    # (holds annual-rate display price per month: $49/$149)
    op.alter_column(
        'subscription_tier', 'monthly_price_cents',
        new_column_name='annual_price_cents',
        schema='public'
    )

    # stripe_price_id → stripe_price_id_monthly
    op.alter_column(
        'subscription_tier', 'stripe_price_id',
        new_column_name='stripe_price_id_monthly',
        schema='public'
    )

    # ── Step 2: Add monthly_price_cents (3-part NOT NULL pattern) ────────────
    # Part 1: Add as nullable
    op.add_column(
        'subscription_tier',
        sa.Column('monthly_price_cents', sa.Integer(), nullable=True),
        schema='public'
    )

    # Part 2: Backfill with correct month-to-month premium prices
    op.execute("""
        UPDATE public.subscription_tier
        SET monthly_price_cents = CASE
            WHEN tier_name = 'starter' THEN 5900
            WHEN tier_name = 'teams'   THEN 17900
            ELSE 0
        END;
    """)

    # Part 3: Lock NOT NULL
    op.alter_column(
        'subscription_tier', 'monthly_price_cents',
        nullable=False,
        schema='public'
    )

    # ── Step 3: Add stripe_price_id_annual (nullable — Tom populates later) ──
    op.add_column(
        'subscription_tier',
        sa.Column('stripe_price_id_annual', sa.Text(), nullable=True),
        schema='public'
    )

    # ── Step 4: Fix founders_plan product_plan_version price_cents ───────────
    # MKT-B11 incorrectly set price_cents=4900 for founders_plan.
    # Founders plan list price is $0 during the free cohort period.
    # The $49/mo billing activating at month 7 is a Stripe Subscription
    # Schedule event (STRIPE-B1 scope) — not a plan-price change.
    op.execute("""
        UPDATE public.product_plan_version
        SET price_cents = 0
        WHERE product_plan_code = 'founders_plan'
          AND price_cents != 0;
    """)


def downgrade() -> None:
    # Restore founders_plan price_cents
    op.execute("""
        UPDATE public.product_plan_version
        SET price_cents = 4900
        WHERE product_plan_code = 'founders_plan'
          AND price_cents = 0;
    """)

    # Drop new columns
    op.drop_column('subscription_tier', 'stripe_price_id_annual', schema='public')
    op.drop_column('subscription_tier', 'monthly_price_cents', schema='public')

    # Rename back
    op.alter_column(
        'subscription_tier', 'stripe_price_id_monthly',
        new_column_name='stripe_price_id',
        schema='public'
    )
    op.alter_column(
        'subscription_tier', 'annual_price_cents',
        new_column_name='monthly_price_cents',
        schema='public'
    )
```

### Apply and verify

```bash
alembic upgrade head

# Verify via MCP:
# SELECT column_name, data_type, is_nullable FROM information_schema.columns
# WHERE table_schema = 'public' AND table_name = 'subscription_tier'
# ORDER BY ordinal_position;
# Expected new columns: annual_price_cents, monthly_price_cents (new), stripe_price_id_monthly, stripe_price_id_annual

# Verify founders_plan price fix:
# SELECT product_plan_code, price_cents FROM public.product_plan_version ORDER BY product_plan_code;
# Expected: founders_plan=0, starter_plan=4900, teams_plan=14900

# Full migration cycle test
alembic downgrade -1
alembic upgrade head
alembic current  # must show new head
```

---

## Task 3 — Update `SubscriptionTier` SQLModel

Update the `SubscriptionTier` class in `backend/app/models/subscription.py` to match the renamed and new columns.

Find the `SubscriptionTier` model and update the relevant fields:

```python
# BEFORE
monthly_price_cents: int = Field(...)
stripe_price_id: str | None = Field(default=None)

# AFTER — rename existing fields
annual_price_cents: int = Field(...)            # was monthly_price_cents — holds display price (annual rate)
monthly_price_cents: int = Field(default=0)    # NEW — month-to-month premium price (5900/17900)
stripe_price_id_monthly: str | None = Field(default=None)  # was stripe_price_id
stripe_price_id_annual: str | None = Field(default=None)   # NEW — populated by Tom after Stripe Dashboard
```

> **Check for `sa_column` overrides**: If `monthly_price_cents` or `stripe_price_id` use `sa_column=Column(...)` overrides for constraints/defaults, update those SA column definitions to match the new column names. Use `read_file` on the model file first to see the exact current field definitions.

After updating the model:

```bash
python generate_db_model_map.py
grep -A 5 "SubscriptionTier" backend/db_models_map.md
# Verify annual_price_cents, monthly_price_cents, stripe_price_id_monthly, stripe_price_id_annual appear
```

### Intermediate unit test check

```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

> **Expected failures**: Any test that references `tier.stripe_price_id` or `tier.monthly_price_cents` in the old sense may fail. Fix each one by updating the field reference to match the new column name. Note all fixed tests in your Completion Summary.

---

## Task 4 — Update `seed_platform.py` (6 Changes)

Update `backend/migrations/scripts/seed_platform.py` with all 6 required changes. Read the full script first.

### Change 1 — `PRODUCT_PLANS`: Update `teams` code

```python
# BEFORE
{"code": "teams", "name": "Teams Plan", "description": "...", "is_active": False}

# AFTER
{"code": "teams_plan", "name": "Teams Plan", "description": "...", "is_active": False}
```

### Change 2 — `TIER_TO_PLAN_MAP`: Update `teams` value

```python
TIER_TO_PLAN_MAP = {
    "founders": "founders_plan",
    "trial": "starter_plan",
    "starter": "starter_plan",
    "teams": "teams_plan",   # ← was "teams"
}
```

### Change 3 — `PLAN_FEATURE_LIMITS`: Update `teams` key

```python
PLAN_FEATURE_LIMITS = {
    "founders_plan": { ... },
    "starter_plan": { ... },
    "teams_plan": { ... },   # ← was "teams"
}
```

### Change 4 — `_SUBSCRIPTION_TIER_ROWS`: Add new price fields, rename `teams` plan code

Update all 4 tier dicts to use the renamed + new columns:

```python
_SUBSCRIPTION_TIER_ROWS = [
    {
        "tier_name": "founders",
        "display_label": "Founders",
        "annual_price_cents": 0,          # renamed from monthly_price_cents
        "monthly_price_cents": 0,         # NEW field
        "is_trial": False,
        "trial_duration_days": None,
        "is_active": True,
        "display_order": 0,
        "schedule_lanes": 5,
        "product_plan_code": "founders_plan",
        "stripe_price_id_monthly": None,  # renamed from stripe_price_id
        "stripe_price_id_annual": None,   # NEW field
    },
    {
        "tier_name": "trial",
        "display_label": "Trial",
        "annual_price_cents": 0,
        "monthly_price_cents": 0,
        "is_trial": True,
        "trial_duration_days": 14,
        "is_active": False,
        "display_order": 1,
        "schedule_lanes": 5,
        "product_plan_code": "starter_plan",
        "stripe_price_id_monthly": None,
        "stripe_price_id_annual": None,
    },
    {
        "tier_name": "starter",
        "display_label": "Starter",
        "annual_price_cents": 4900,        # $49/mo annual display price
        "monthly_price_cents": 5900,       # $59/mo month-to-month premium
        "is_trial": False,
        "trial_duration_days": None,
        "is_active": False,
        "display_order": 2,
        "schedule_lanes": 5,
        "product_plan_code": "starter_plan",
        "stripe_price_id_monthly": "price_REDACTED03",  # test-mode monthly
        "stripe_price_id_annual": None,   # Tom creates annual prices in Stripe Dashboard
    },
    {
        "tier_name": "teams",
        "display_label": "Teams",
        "annual_price_cents": 14900,       # $149/mo annual display price
        "monthly_price_cents": 17900,      # $179/mo month-to-month premium
        "is_trial": False,
        "trial_duration_days": None,
        "is_active": False,
        "display_order": 3,
        "schedule_lanes": 20,
        "product_plan_code": "teams_plan", # ← renamed
        "stripe_price_id_monthly": "price_REDACTED04",  # test-mode monthly
        "stripe_price_id_annual": None,   # Tom creates annual prices in Stripe Dashboard
    },
]
```

Also update the INSERT SQL inside `mode_seed()` (step 4) to reference the new column names:
- Replace `monthly_price_cents` → `annual_price_cents` in INSERT statement
- Add `monthly_price_cents` to INSERT column list
- Replace `stripe_price_id` → `stripe_price_id_monthly` in INSERT statement
- Add `stripe_price_id_annual` to INSERT column list

### Change 5 — Idempotent Stripe Price Patch Block: Rename column reference

Find the `_STRIPE_PRICE_SEED` dict and the UPDATE block below it. Update both to use `stripe_price_id_monthly`:

```python
_STRIPE_PRICE_SEED = {
    "starter": "price_REDACTED03",
    "teams": "price_REDACTED04",
}
for tier_name, price_id in _STRIPE_PRICE_SEED.items():
    result = db.execute(
        text("""
            UPDATE public.subscription_tier
            SET stripe_price_id_monthly = :price_id, updated_at = NOW()
            WHERE tier_name = :tier_name
            AND (stripe_price_id_monthly IS NULL OR stripe_price_id_monthly != :price_id)
        """),  # ← updated column name
        {"price_id": price_id, "tier_name": tier_name},
    )
```

### Change 6 — `product_plan_version` INSERT: Fix price_cents values

Find the `mode_seed()` product_plan_version INSERT block. Replace hardcoded `price_cents = 0` with per-plan values:

```python
PRODUCT_PLAN_PRICES = {
    "founders_plan": 0,      # Free during cohort period (list price = $0)
    "starter_plan": 4900,    # $49/mo annual display price
    "teams_plan": 14900,     # $149/mo annual display price
}

# In the loop that inserts product_plan_version rows:
for plan in PRODUCT_PLANS:
    # ...existing check logic...
    price_cents = PRODUCT_PLAN_PRICES.get(plan["code"], 0)
    db.execute(
        text("""
            INSERT INTO public.product_plan_version
            (product_plan_code, name, price_cents, valid_period, recorded_at, created_at)
            VALUES (:code, :name, :price_cents, tstzrange(now(), NULL), NOW(), NOW())
        """),
        {"code": plan["code"], "name": plan["name"], "price_cents": price_cents},
    )
```

### Also update `mode_inspect()` and `mode_show()`

The inspect and show modes print current state. Update them to reference the renamed fields:
- `monthly_price_cents` references in `mode_inspect()` → `annual_price_cents` (for the `subscription_tier` print)
- Add `monthly_price_cents` and `stripe_price_id_annual` to the show output

### Run and verify

```bash
python migrations/scripts/seed_platform.py --mode show
# Verify all plan codes, prices, and Stripe price IDs print correctly

python migrations/scripts/seed_platform.py --mode inspect
# Verify live DB state matches expected values

python migrations/scripts/seed_platform.py
# Re-run seed (idempotent) — should show "already exists" or "updated" messages
```

---

## Task 5 — Add 18 Notification Template Rows to `seed_platform.py`

Add the following entries to `NOTIFICATION_TEMPLATE_COPY` in `seed_platform.py`. These are v1 placeholder bodies for the 6 notification_type codes added by SD-2.

```python
# SD-3: Placeholder copy for 6 notification_type codes added by SD-2
# Each type needs email, in_app, push templates (18 rows total)

("job_assigned", "email"): {
    "subject": "[Job Assigned] Notification",
    "body": "You have been assigned to job {{job_number}} — {{job_title}}. Scheduled: {{scheduled_date}}.",
},
("job_assigned", "in_app"): {
    "subject": "[Job Assigned] Notification",
    "body": "New job assigned: {{job_number}} — {{job_title}}.",
},
("job_assigned", "push"): {
    "subject": "[Job Assigned] Notification",
    "body": "New job: {{job_number}} — {{job_title}}.",
},
("schedule_changed", "email"): {
    "subject": "[Schedule Changed] Notification",
    "body": "Your schedule has been updated. Job {{job_number}} is now scheduled for {{scheduled_date}}.",
},
("schedule_changed", "in_app"): {
    "subject": "[Schedule Changed] Notification",
    "body": "Schedule updated for job {{job_number}}.",
},
("schedule_changed", "push"): {
    "subject": "[Schedule Changed] Notification",
    "body": "Schedule change: {{job_number}} moved to {{scheduled_date}}.",
},
("qb_sync_conflict", "email"): {
    "subject": "[QuickBooks Sync Conflict] Notification",
    "body": (
        "A sync conflict was detected for {{entity_type}} {{entity_id}} in QuickBooks. "
        "Log in to Pilot to review and resolve."
    ),
},
("qb_sync_conflict", "in_app"): {
    "subject": "[QuickBooks Sync Conflict] Notification",
    "body": "QuickBooks sync conflict: {{entity_type}} {{entity_id}} requires your attention.",
},
("qb_sync_conflict", "push"): {
    "subject": "[QuickBooks Sync Conflict] Notification",
    "body": "QB sync conflict detected — tap to resolve.",
},
("qb_conflict_pre_warning", "email"): {
    "subject": "[QuickBooks Conflict Warning] Notification",
    "body": (
        "A potential QuickBooks sync conflict has been detected for {{entity_type}} {{entity_id}}. "
        "Review before it becomes a blocking conflict."
    ),
},
("qb_conflict_pre_warning", "in_app"): {
    "subject": "[QuickBooks Conflict Warning] Notification",
    "body": "QB conflict warning: {{entity_type}} {{entity_id}} — review now.",
},
("qb_conflict_pre_warning", "push"): {
    "subject": "[QuickBooks Conflict Warning] Notification",
    "body": "QB conflict warning — tap to review before it blocks.",
},
("gps_variance_alert", "email"): {
    "subject": "[GPS Variance Alert] Notification",
    "body": (
        "A GPS variance was detected for technician {{tech_name}} on job {{job_number}}. "
        "Expected location: {{expected_location}}. Actual: {{actual_location}}."
    ),
},
("gps_variance_alert", "in_app"): {
    "subject": "[GPS Variance Alert] Notification",
    "body": "GPS variance detected for {{tech_name}} on job {{job_number}}.",
},
("gps_variance_alert", "push"): {
    "subject": "[GPS Variance Alert] Notification",
    "body": "GPS variance: {{tech_name}} is off-site on job {{job_number}}.",
},
("system_template_updated", "email"): {
    "subject": "[System Template Updated] Notification",
    "body": (
        "A system notification template has been updated. "
        "Template: {{template_name}}. This may affect automated notifications sent to your customers."
    ),
},
("system_template_updated", "in_app"): {
    "subject": "[System Template Updated] Notification",
    "body": "System template updated: {{template_name}}.",
},
("system_template_updated", "push"): {
    "subject": "[System Template Updated] Notification",
    "body": "System update: {{template_name}} template changed.",
},
```

After adding, run:

```bash
python migrations/scripts/seed_platform.py
# Should show 18 new "✅ [notification_template] Created ..." lines
```

Verify via MCP:

```sql
SELECT notification_type_code, COUNT(*) AS channels
FROM public.notification_template
WHERE tenant_id IS NULL
GROUP BY notification_type_code
ORDER BY notification_type_code;
-- Expected: 9 types, each with count=3
```

---

## Task 6 — Write Tests

### Test File 1: `tests/domains/subscriptions_usage/test_sd3_billing_schema.py`

```python
"""
SD-3: Verify subscription_tier billing schema changes.
- annual_price_cents column renamed from monthly_price_cents
- monthly_price_cents new column with correct values
- stripe_price_id_monthly renamed from stripe_price_id
- stripe_price_id_annual new column (nullable)
- teams_plan rename complete
- founders_plan product_plan_version price_cents = 0
"""
import pytest
from sqlmodel import select, text

pytestmark = [
    pytest.mark.domain_subscriptions_usage,
    pytest.mark.unit,
]


class TestSubscriptionTierBillingSchema:

    def test_annual_price_cents_column_exists_on_all_tiers(self, db_session):
        """annual_price_cents must exist and have correct values for all 4 tiers."""
        from app.models.subscription import SubscriptionTier
        tiers = db_session.exec(select(SubscriptionTier)).all()
        tier_map = {t.tier_name: t for t in tiers}

        assert tier_map["founders"].annual_price_cents == 0
        assert tier_map["trial"].annual_price_cents == 0
        assert tier_map["starter"].annual_price_cents == 4900
        assert tier_map["teams"].annual_price_cents == 14900

    def test_monthly_price_cents_new_column_correct_values(self, db_session):
        """monthly_price_cents (month-to-month premium) must have correct values."""
        from app.models.subscription import SubscriptionTier
        tiers = db_session.exec(select(SubscriptionTier)).all()
        tier_map = {t.tier_name: t for t in tiers}

        assert tier_map["founders"].monthly_price_cents == 0
        assert tier_map["trial"].monthly_price_cents == 0
        assert tier_map["starter"].monthly_price_cents == 5900
        assert tier_map["teams"].monthly_price_cents == 17900

    def test_stripe_price_id_monthly_field_exists(self, db_session):
        """stripe_price_id_monthly column must exist; test-mode IDs must be set."""
        from app.models.subscription import SubscriptionTier
        starter = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "starter")
        ).first()
        assert starter is not None
        assert starter.stripe_price_id_monthly is not None
        assert starter.stripe_price_id_monthly.startswith("price_")

    def test_stripe_price_id_annual_field_exists_nullable(self, db_session):
        """stripe_price_id_annual must exist as nullable (Tom populates later)."""
        from app.models.subscription import SubscriptionTier
        starter = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "starter")
        ).first()
        assert starter is not None
        # Column must exist on the model (even if NULL)
        assert hasattr(starter, "stripe_price_id_annual")
        # Annual price IDs are NULL until Tom creates them in Stripe Dashboard
        # (acceptable pre-GA)


class TestTeamsPlanRename:

    def test_teams_plan_code_exists(self, db_session):
        """product_plan must have code='teams_plan' (not 'teams')."""
        from sqlalchemy import text as sa_text
        result = db_session.exec(
            sa_text("SELECT code FROM public.product_plan WHERE code = 'teams_plan'")
        ).first()
        assert result is not None, "teams_plan not found — Migration 1 may not have run"

    def test_teams_code_does_not_exist(self, db_session):
        """Old product_plan code 'teams' must not exist after rename."""
        from sqlalchemy import text as sa_text
        result = db_session.exec(
            sa_text("SELECT code FROM public.product_plan WHERE code = 'teams'")
        ).first()
        assert result is None, "Old 'teams' code still exists — rename migration may have failed"

    def test_teams_plan_subscription_tier_linked(self, db_session):
        """subscription_tier 'teams' tier must reference product_plan_code='teams_plan'."""
        from app.models.subscription import SubscriptionTier
        teams_tier = db_session.exec(
            select(SubscriptionTier).where(SubscriptionTier.tier_name == "teams")
        ).first()
        assert teams_tier is not None
        assert teams_tier.product_plan_code == "teams_plan"


class TestFoundersPlanPriceFix:

    def test_founders_plan_version_price_cents_is_zero(self, db_session):
        """founders_plan product_plan_version.price_cents must be 0.
        
        The MKT-B11 migration incorrectly set this to 4900. Founders plan
        list price is $0 during the free cohort period. The $49/mo billing
        that activates at month 7 is a Stripe Subscription Schedule event
        (STRIPE-B1) — not a plan-price change.
        """
        from sqlalchemy import text as sa_text
        result = db_session.exec(
            sa_text("""
                SELECT price_cents FROM public.product_plan_version
                WHERE product_plan_code = 'founders_plan'
                LIMIT 1
            """)
        ).first()
        assert result is not None, "founders_plan product_plan_version row not found"
        assert result.price_cents == 0, (
            f"founders_plan price_cents should be 0, got {result.price_cents}. "
            "SD-3 Migration 2 may not have run or downgrade was applied."
        )

    def test_starter_plan_version_price_cents_correct(self, db_session):
        """starter_plan product_plan_version.price_cents must be 4900."""
        from sqlalchemy import text as sa_text
        result = db_session.exec(
            sa_text("""
                SELECT price_cents FROM public.product_plan_version
                WHERE product_plan_code = 'starter_plan'
                LIMIT 1
            """)
        ).first()
        assert result is not None
        assert result.price_cents == 4900
```

### Test File 2: `tests/domains/notifications_comms/test_sd3_notification_templates.py`

```python
"""
SD-3: Verify notification template coverage for all 9 active notification_type codes.
All 9 types must have email, in_app, and push templates with tenant_id=NULL.
"""
import pytest
from sqlmodel import text

pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]

EXPECTED_NOTIFICATION_TYPES = {
    "customer_communication_sent",
    "dunning_reminder",
    "quote_accepted",
    "job_assigned",
    "schedule_changed",
    "qb_sync_conflict",
    "qb_conflict_pre_warning",
    "gps_variance_alert",
    "system_template_updated",
}

EXPECTED_CHANNELS = {"email", "in_app", "push"}


class TestNotificationTemplateCoverage:

    def test_all_notification_types_have_templates(self, db_session):
        """Every active notification_type must have a platform-level template for each channel."""
        rows = db_session.exec(
            text("""
                SELECT notification_type_code, channel
                FROM public.notification_template
                WHERE tenant_id IS NULL AND is_active = true
                ORDER BY notification_type_code, channel
            """)
        ).fetchall()

        covered = {}
        for row in rows:
            covered.setdefault(row.notification_type_code, set()).add(row.channel)

        for nt_code in EXPECTED_NOTIFICATION_TYPES:
            assert nt_code in covered, (
                f"notification_type '{nt_code}' has no platform templates (tenant_id=NULL). "
                "Run seed_platform.py to fix."
            )
            missing = EXPECTED_CHANNELS - covered[nt_code]
            assert not missing, (
                f"notification_type '{nt_code}' missing channels: {missing}. "
                "Run seed_platform.py to fix."
            )

    def test_total_platform_template_count_is_27(self, db_session):
        """Platform-level notification_template rows: 9 types × 3 channels = 27 rows.
        
        Uses scoped count (only platform rows, not tenant overrides).
        """
        result = db_session.exec(
            text("""
                SELECT COUNT(*) AS cnt
                FROM public.notification_template
                WHERE tenant_id IS NULL AND is_active = true
            """)
        ).first()
        # Note: may be > 27 if future types/channels are added; use >= for resilience
        assert result.cnt >= 27, (
            f"Expected at least 27 platform notification_template rows (9 types × 3 channels), "
            f"got {result.cnt}. Run seed_platform.py to add missing rows."
        )

    def test_sd2_notification_types_have_non_placeholder_bodies(self, db_session):
        """SD-2 types must have non-empty, non-generic body text in templates."""
        result = db_session.exec(
            text("""
                SELECT notification_type_code, channel, body
                FROM public.notification_template
                WHERE tenant_id IS NULL
                  AND notification_type_code IN (
                    'job_assigned', 'schedule_changed', 'qb_sync_conflict',
                    'qb_conflict_pre_warning', 'gps_variance_alert', 'system_template_updated'
                  )
                  AND is_active = true
            """)
        ).fetchall()

        assert len(result) == 18, (
            f"Expected 18 SD-2 notification_template rows, got {len(result)}. "
            "Run seed_platform.py to add missing rows."
        )
        for row in result:
            assert row.body and len(row.body) > 10, (
                f"Template body for {row.notification_type_code}/{row.channel} "
                "appears empty or too short"
            )
```

---

## Task 7 — Write `pilot-docs-list.md` (Root Level)

Create `/pilot-docs-list.md` at the project root. This is a master registry of all active reference documents.

The document should include:
- A brief purpose statement
- Tables organized by category (one table per category)
- Each row: Doc name (linked) | Path | What it covers | Last updated

Categories to cover:
1. **Product & Strategy** — PRD, roadmap, GTM strategy, brand strategy, FSM market gap analysis
2. **Architecture & Design** — mvp-arch, pilot-architect-methods, batch designs index, architect rules
3. **Implementation Tracking** — launch plan, BE tests list, DLC tasks, batch prompts README
4. **Database & Seed Data** — DB process docs, seed README, MCP guide, schema sync archive
5. **DevOps & Infrastructure** — AWS infrastructure as-built, ops runbook, Stripe pricing config, SDLC repo docs
6. **Testing & QA** — scenario coverage catalog, E2E harness docs, README-adding-tests
7. **Operations Reference** — pilot-operations.md (new in SD-3)

Keep it concise — one table per section, one row per doc. Do NOT duplicate information from the docs themselves.

---

## Task 8 — Write `dev-docs/pilot-operations.md`

Create `dev-docs/pilot-operations.md`. This document explains how Pilot's platform configuration operates at runtime — the "how does all this actually work?" reference.

Required sections (see design doc §G.2 for detailed outlines):

1. **Lookup Tables (Group A)** — What they are; the `(id, code, name)` pattern; how code-string lookups work in application code; how `seed_core.py` is the recovery tool.

2. **Product Plan Hierarchy** — `product_plan` → `product_plan_version` → `product_plan_product_feature_version` cascade. Append-only versioning. How entitlement service reads this. `block` vs `soft` enforcement modes.

3. **Subscription Tier Model** — `subscription_tier` as the customer-visible pricing layer. `annual_price_cents` (display price per month billed annually) vs `monthly_price_cents` (month-to-month premium). How tier maps to `product_plan_code`. How `stripe_price_id_monthly` / `stripe_price_id_annual` connect to Stripe.

4. **Tenant Subscription Lifecycle** — Trial (14-day) → Paywall → Plan selection (annual or monthly) → Stripe checkout → Webhook → `subscription` row created → tier updated. How `subscription.billing_interval` is set. How `renews_at` is maintained.

5. **Founders Cohort Model** — How the founders tier works (is_active=true, $0/mo, same limits as Starter). How the 6-month free period transitions to $49/mo billing (Stripe Subscription Schedule — STRIPE-B1). What happens at month 7.

6. **Per-Tenant Overrides** — `tenant_product_feature_override` (custom feature limits for a specific tenant) and `tenant_tier_override` (move tenant to a different tier). Both are operator-managed via direct SQL during beta. UI management is a Phase 1.5 item.

7. **Notification Template System** — `notification_type` → `notification_template` (platform defaults, `tenant_id=NULL`) → `notification_outbox` delivery queue. How the service resolves the right template (tenant override → platform default). Channel enum: email, in_app, push, sms.

8. **Subscription Status Machine** — How `subscription_status` rows map 1:1 to Stripe's `subscription.status` enum. Which statuses are `is_billing_active=true` (trialing, active, past_due) vs false (unpaid, canceled, paused). How the API paywall reads this.

Keep each section concise (1-2 paragraphs + code or table where helpful). This is a reference doc, not a tutorial.

---

## Task 9 — Update Supporting Documentation

After all code + tests + docs are written:

### 9a — Update `stripe-pricing-config.md`

In `dev-docs/integrations/stripe/stripe-pricing-config.md`:

1. **Remove §3 "What NOT to Create Now"** item for annual prices (it's now part of the plan)
2. **Remove §7 "Open P2 Dev Task — Annual Billing"** (it's now implemented as SD-3 + STRIPE-B1)
3. **Add new §7 "Annual Pricing — Stripe Dashboard Setup"** with Tom's action items:
   - Create annual price for Pilot Starter: `$588.00/year` · lookup key `pilot_starter_annual`
   - Create annual price for Pilot Teams: `$1,788.00/year` · lookup key `pilot_teams_annual`
   - Once IDs are created, update `subscription_tier.stripe_price_id_annual` via idempotent seed script re-run
4. **Update §2 `product_plan_code` metadata** on Teams product from `teams` → `teams_plan`

### 9b — Update `README-seed-data.md` Group B table

In `backend/README-seed-data.md`, update the Group B table to reflect:
- `subscription_tier` row: note `annual_price_cents` rename, `monthly_price_cents` new column, `stripe_price_id_monthly` rename, `stripe_price_id_annual` new column
- `product_plan`: note `teams` renamed to `teams_plan`
- `notification_template`: update row count to "27" (9 types × 3 channels) with note about SD-3 adding 18 rows for SD-2 types

### 9c — Update `pilot-launch-plan.md`

In `dev-docs/analysis/pilot-launch-plan.md`:

1. Add SD-3 to **Appendix A** completed work registry
2. Add **STRIPE-B1** as a new P1 task in §2 Active Dev Work Queue with description:
   > **STRIPE-B1 — Annual Billing Service + Founders Cohort Schedule** — Prerequisite: SD-3 complete. Scope: (1) Update `stripe_subscriptions.py` to route monthly vs annual Stripe price IDs based on `billing_interval`; (2) Add `stripe_schedule_id` column to `subscription`; (3) Implement `create_founders_subscription_schedule()` Stripe Subscription Schedule API call at tenant signup; (4) Webhook handler for `customer.subscription.schedule.updated` Phase 2 activation event; (5) Update `subscription_upgrade` route to accept `billing_interval` in request body.

---

## Schema JSON Sync

After all migrations run and tests pass:

```bash
cd <repo>/backend
python schema_manager.py --help
```

Read the available CRUD commands, then update the JSON schema for:
- `subscription_tier` table: reflect renamed columns (`annual_price_cents`, `stripe_price_id_monthly`) and new columns (`monthly_price_cents`, `stripe_price_id_annual`)

**NEVER edit `dev-docs/db-design/pilot-db-schema-v2.6h.json` directly.** Always use `schema_manager.py`. If `schema_manager.py` is not working → STOP and ask Tom.

---

## Final Verification

### Phase 1 — Unit Tests Only

```bash
cd <repo>/backend
source .venv/bin/activate

python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass. Fix any failure — including failures from code outside your batch — before Phase 2.

### Phase 2 — Full Suite

```bash
cd <repo>/backend
source .venv/bin/activate

# Full suite
python -m pytest --tb=short -q 2>&1 | tail -10

# Batch-specific spot checks
python -m pytest tests/domains/subscriptions_usage/test_sd3_billing_schema.py -v
python -m pytest tests/domains/notifications_comms/test_sd3_notification_templates.py -v

# Verify alembic cycle
alembic downgrade -1
alembic downgrade -1
alembic upgrade head
alembic current

# Verify seed scripts work end-to-end
python migrations/scripts/seed_platform.py --mode show
python migrations/scripts/seed_platform.py --mode inspect

echo "=== SD-3 FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work (or confirmed with Tom)
- [ ] All 8 MCP pre-work queries run with expected results confirmed
- [ ] All mandatory source files read before writing any code
- [ ] **Task 1**: Migration 1 (`teams` → `teams_plan` FK cascade) written, applied, cycle-tested
- [ ] **Task 2**: Migration 2 (annual billing schema + founders price fix) written, applied, cycle-tested
- [ ] **Task 3**: `SubscriptionTier` SQLModel updated with renamed + new fields; `db_models_map.md` regenerated
- [ ] **Task 4**: `seed_platform.py` updated with all 6 changes; `mode_show` and `mode_inspect` updated; seed re-run succeeds
- [ ] **Task 5**: 18 notification template rows added to `seed_platform.py`; seed re-run creates all 18 rows
- [ ] **Task 6**: Two test files written — `test_sd3_billing_schema.py` + `test_sd3_notification_templates.py`
- [ ] **Task 7**: `pilot-docs-list.md` written at project root
- [ ] **Task 8**: `dev-docs/pilot-operations.md` written with all 8 required sections
- [ ] **Task 9a**: `stripe-pricing-config.md` updated (§3, §7 updated; Teams metadata updated)
- [ ] **Task 9b**: `README-seed-data.md` Group B table updated (subscription_tier columns, notification_template count)
- [ ] **Task 9c**: `pilot-launch-plan.md` updated (SD-3 in Appendix A; STRIPE-B1 added as P1 task)
- [ ] `schema_manager.py` run — `subscription_tier` columns updated in JSON schema
- [ ] All new test files use `pytestmark` with domain marker + `pytest.mark.unit`
- [ ] No module-level `TestClient` in any new test file
- [ ] All test assertions scoped by inserted IDs — no total row count assertions
- [ ] Known breakage flagged in Completion Summary: `stripe_subscriptions.py` references `tier.stripe_price_id` (pre-rename name) — STRIPE-B1 fixes this
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `pilot-launch-plan.md` Appendix B

---

## Completion Summary

After all Definition of Done items are complete, add a **Completion Summary** to `dev-docs/analysis/pilot-launch-plan.md` Appendix B using this format:

```markdown
### SD-3 — Group B Platform Seed Audit & Billing Schema Expansion: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- Migration 1: Renamed product_plan code 'teams' → 'teams_plan' with FK cascade to 5 tables
- Migration 2: Renamed subscription_tier columns for annual billing clarity; added monthly_price_cents (month-to-month premium) + stripe_price_id_annual columns; fixed founders_plan product_plan_version price_cents from 4900 → 0
- Updated SubscriptionTier SQLModel with 4 field changes
- Updated seed_platform.py with 6 data changes + 18 new notification_template placeholder rows (6 SD-2 types × 3 channels)
- [Note any test fixes for subscription_tier field reference changes]
- [Note STRIPE-B1 dependency: stripe_subscriptions.py references pre-rename stripe_price_id — will produce AttributeError on paid subscription creation until STRIPE-B1 is complete]
- Written: pilot-docs-list.md (root) + dev-docs/pilot-operations.md

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/migrations/versions/YYYY_*_sd3_teams_plan_rename.py` | Created — Migration 1: teams→teams_plan FK cascade |
| `backend/migrations/versions/YYYY_*_sd3_annual_billing_schema.py` | Created — Migration 2: annual billing schema + founders price fix |
| `backend/app/models/subscription.py` | Updated — SubscriptionTier field renames + new fields |
| `backend/migrations/scripts/seed_platform.py` | Updated — 6 data changes + 18 new notification_template entries |
| `backend/db_models_map.md` | Updated — SubscriptionTier fields regenerated |
| `dev-docs/db-design/pilot-db-schema-v2.6h.json` | Updated — subscription_tier column changes |
| `dev-docs/integrations/stripe/stripe-pricing-config.md` | Updated — §3/§7 updated; Teams metadata updated |
| `backend/README-seed-data.md` | Updated — Group B table; notification_template count |
| `dev-docs/analysis/pilot-launch-plan.md` | Updated — SD-3 in Appendix A; STRIPE-B1 added as P1; Appendix B completion summary |
| `pilot-docs-list.md` | Created — master doc registry (root level) |
| `dev-docs/pilot-operations.md` | Created — platform operations reference |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/subscriptions_usage/test_sd3_billing_schema.py` | `domain_subscriptions_usage` | 7 | ✅ |
| `tests/domains/notifications_comms/test_sd3_notification_templates.py` | `domain_notifications_comms` | 3 | ✅ |
```

---

## After This Batch — Next Step

**STRIPE-B1** must run immediately after SD-3. The `stripe_subscriptions.py` service references `tier.stripe_price_id` which no longer exists after SD-3's migration. Any attempt to create a paid Stripe subscription at runtime will raise `AttributeError`. No real paying tenants exist pre-GA, so this is acceptable during development — but STRIPE-B1 must close before the first paying customer can subscribe.

STRIPE-B1 scope (not part of SD-3):
1. Update `stripe_subscriptions.py` to route `stripe_price_id_monthly` vs `stripe_price_id_annual` based on `billing_interval`
2. Add `stripe_schedule_id` column to `subscription` table
3. Implement `create_founders_subscription_schedule()` — Stripe Subscription Schedule API (6-month free → $49/mo Phase 2)
4. Webhook handler for `customer.subscription.schedule.updated` Phase 2 activation
5. Update subscription upgrade route to accept `billing_interval: Literal["monthly", "annual"]` in request body
