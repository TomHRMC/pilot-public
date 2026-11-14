# Implementation Prompt: Seed Data Phase 0.8 — Post-Delivery Remediation

**Mode**: Pilot Python Engineer  
**Batch**: Seed-Task-03 / Phase 0.8  
**Source plan**: `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` §0.8  
**Analysis reference**: `dev-docs/seed-data/seed-data-analysis-fixes-v1.md`  
**Summary reference**: `dev-docs/seed-data/seed-data-analysis-summary-v1.md`  
**Estimated session**: 2–3 hours  
**Platform**: Backend only (`backend/`)  
**No new schema changes** — no `schema_manager.py` or OpenAPI regeneration required  

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read ALL of these in full:

- **`backend/python-engr-std-prompt-inclusions.md`** — the authoritative standard for every Python Engineer prompt; governs baseline capture, MCP usage, migration rules, test standards, and completion summary format
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic migration pattern), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, and fixture rules

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Always verify with `postgres-local` MCP before writing any SQL. If MCP returns an error → **STOP and ask Tom**.
- **Rule 2**: All Alembic migrations must be written as **blank** migrations (never `--autogenerate`). Data changes use raw `op.execute()`.
- **Rule 3**: Task 8.1 (`conftest.py`) **MUST complete and pass `pytest -k stripe_subscription`** before Task 8.2 (`seed_platform.py`) is touched. Violating this order will break the Stripe lifecycle test.
- **Rule 4**: All seed script INSERTs must use `ON CONFLICT DO NOTHING` — every script is idempotent and safe to run multiple times.
- **Rule 5**: Never use module-level `TestClient` in any test file. Always use the `client` fixture from `conftest.py`.
- **Rule 6**: The `postgres-local` MCP is for read-only verification only. Never use it to INSERT, UPDATE, or DELETE data — all data changes go through the seed scripts or migrations.

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**. All tests passing now must still pass at the end. Do not proceed if new failures appear unexpectedly.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code. If any returns unexpected results → **STOP and report**.

```sql
-- 1. Confirm subscription_status is empty (should be 0 rows)
SELECT code, name, is_billing_active FROM public.subscription_status ORDER BY code;

-- 2. Confirm subscription_tier trial gap
SELECT tier_name, is_trial, product_plan_code 
FROM public.subscription_tier 
ORDER BY display_order;

-- 3. Verify test tenant subscription state (should be 0 rows — that's the bug)
SELECT id, product_plan_code, status_id, is_active 
FROM public.subscription 
WHERE tenant_id = '00000000-0000-0000-0000-000000000001';

-- 4. Confirm subscription_status column schema
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'subscription_status' 
ORDER BY ordinal_position;

-- 5. Verify the unique constraint name (needed for ON CONFLICT)
SELECT conname, contype 
FROM pg_constraint 
WHERE conrelid = 'public.subscription_status'::regclass;

-- 6. Check current alembic head
SELECT version_num FROM public.alembic_version;
```

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/tests/conftest.py                              ← find subscription_status fixture(s)
backend/migrations/scripts/seed_platform.py            ← full file — understand TIER_TO_PLAN_MAP and mode_seed structure
backend/migrations/versions/2026_05_31_2216-dd4ed7ed5f3b_seed_missing_lookup_tables_batch_1.py
                                                        ← lines 87–100 — see what was originally seeded
backend/migrations/scripts/seed_core.py                ← mode_show() and notification_channel definition
backend/migrations/scripts/seed_scenario_dispatch.py   ← mode_inspect() job output block
backend/migrations/scripts/reset_dev_db.py             ← GROUP_D_TABLES list and inspect count loop
```

Also run this search to find ALL `subscription_status` references in `conftest.py`:

```bash
grep -n "subscription_status\|SubscriptionStatus" backend/tests/conftest.py
```

---

## Background: Why This Is Needed

The seed scripts were delivered 2026-06-01. Four gaps were found in a 2026-06-08 analysis session:

1. **`subscription_status` has 0 rows in dev DB** — the `dd4ed7ed5f3b` migration originally inserted 4 rows (`trial`, `active`, `past_due`, `canceled`), but a schema-only DB restore cleared them. `seed_test_tenant.py` queries `WHERE code = 'active'` before creating the subscription row — finding 0 rows, it silently skips subscription creation. The test tenant ends up with **no `subscription` row**, breaking entitlement resolution and billing endpoints.

2. **`conftest.py` inserts its own `subscription_status` rows** — this is what blocked re-seeding: the fixture creates rows with fresh UUIDs at test-time, causing `test_stripe_subscription_lifecycle` to find two `active` rows and fail on UUID assertion. Fix: change the fixture to query the seeded row instead of inserting its own.

3. **`subscription_tier.trial` has `product_plan_code = null`** — the `TIER_TO_PLAN_MAP` in `seed_platform.py` maps only the 3 paid tiers; the `trial` tier was never linked to `starter_plan`, so trial tenant entitlement resolution returns null for all feature checks.

4. **Show/inspect mode gaps** — 5 places where seeded data is not surfaced in `--mode show` or `--mode inspect` output.

---

## Task 8.1 — Update `conftest.py`: Query Seeded Rows, Don't Insert

**File**: `backend/tests/conftest.py`  
**Priority**: 🔴 Critical — **MUST complete before Task 8.2**

### What to find

After reading `conftest.py`, locate any code that **creates** `subscription_status` rows. Typical patterns:

```python
# Pattern A — SQLModel/ORM insert
status = SubscriptionStatus(code="active", name="Active", is_billing_active=True)
db.add(status)
db.commit()

# Pattern B — raw SQL
db.execute(text("INSERT INTO subscription_status (id, code, name, ...) VALUES (...)"))
```

### What to change

Replace any INSERT with a SELECT that queries the persistently-seeded row. The fixture must **assert** the row exists rather than create it — a missing seed row should produce a clear error message:

```python
from sqlalchemy import text

def get_or_assert_subscription_status(db, code: str):
    """Look up a subscription_status row. Raises AssertionError if not found.
    
    IMPORTANT: These rows are seeded by seed_platform.py, NOT by this fixture.
    If this assertion fails, run: python migrations/scripts/seed_platform.py
    """
    row = db.execute(
        text("""
            SELECT id, code, name, is_billing_active 
            FROM public.subscription_status 
            WHERE code = :code AND tenant_id IS NULL
            LIMIT 1
        """),
        {"code": code},
    ).first()
    assert row is not None, (
        f"subscription_status '{code}' not found in DB. "
        f"Run: cd backend && python migrations/scripts/seed_platform.py"
    )
    return row
```

### Verify — critical gate

```bash
cd <repo>/backend
source .venv/bin/activate

# Run ONLY the Stripe tests — must pass (subscription_status table is still empty at this point)
pytest tests/ -k "stripe_subscription" -v 2>&1 | tail -20
```

The Stripe tests will still fail here because `subscription_status` is empty — and that's expected. What you're verifying is that the **reason for failure is now the assert message** ("subscription_status 'active' not found"), not the UUID mismatch. Once Task 8.2 adds the rows, these tests will pass.

---

## Task 8.2 — Add `subscription_status` Rows to `seed_platform.py`

**File**: `backend/migrations/scripts/seed_platform.py`  
**Priority**: 🔴 Critical — run only after Task 8.1 is complete

### The 6 rows

These map 1:1 to Stripe's `subscription.status` field received by `backend/services/stripe_subscriptions.py`:

| `code` | `name` | `is_billing_active` | Stripe meaning |
|---|---|:---:|---|
| `trialing` | Trialing | `true` | Free trial active; sent on checkout before first payment |
| `active` | Active | `true` | Paid and current |
| `past_due` | Past Due | `true` | Payment failing; retrying — access retained |
| `unpaid` | Unpaid | `false` | Retries exhausted — access revoked |
| `canceled` | Canceled | `false` | Subscription canceled — terminal |
| `paused` | Paused | `false` | Stripe pause-collection — access revoked |

> **Note on `trial` vs `trialing`**: The existing migration inserted `trial` (our internal tier code). Stripe sends `trialing` (the checkout phase). Both are needed. `seed_platform.py` handles all 6 including both.

### Where to add the constant

Add `SUBSCRIPTION_STATUS_ROWS` near the top of the file with the other data definitions (after `PLAN_FEATURE_LIMITS`):

```python
SUBSCRIPTION_STATUS_ROWS = [
    {"code": "trialing",  "name": "Trialing",  "is_billing_active": True},
    {"code": "active",    "name": "Active",     "is_billing_active": True},
    {"code": "past_due",  "name": "Past Due",   "is_billing_active": True},
    {"code": "unpaid",    "name": "Unpaid",     "is_billing_active": False},
    {"code": "canceled",  "name": "Canceled",   "is_billing_active": False},
    {"code": "paused",    "name": "Paused",     "is_billing_active": False},
]
```

### Where to add the seed logic in `mode_seed()`

Add after the `notification_template` seeding block, before `db.commit()`:

```python
# ── subscription_status (6 rows — global platform config) ────────────────
for ss in SUBSCRIPTION_STATUS_ROWS:
    existing = db.execute(
        text(
            "SELECT 1 FROM public.subscription_status WHERE code = :code AND tenant_id IS NULL"
        ),
        {"code": ss["code"]},
    ).first()
    if existing:
        print(f"  ℹ️  [subscription_status] '{ss['code']}' already exists")
    else:
        db.execute(
            text("""
                INSERT INTO public.subscription_status
                (id, tenant_id, code, name, is_billing_active, created_at, updated_at)
                VALUES (gen_random_uuid(), NULL, :code, :name, :is_billing_active, NOW(), NOW())
                ON CONFLICT DO NOTHING
            """),
            ss,
        )
        print(f"  ✅ [subscription_status] Inserted '{ss['code']}'")
```

### Verify

```bash
python migrations/scripts/seed_platform.py
# Must show: ✅ [subscription_status] Inserted 'trialing' (plus 5 more)

python migrations/scripts/seed_platform.py  # run again
# Must show: ℹ️ [subscription_status] 'trialing' already exists (all 6)

# Now run the Stripe tests — they must pass
pytest tests/ -k "stripe_subscription" -v 2>&1 | tail -20
```

---

## Task 8.3 — Add `"trial"` Tier to `TIER_TO_PLAN_MAP`

**File**: `backend/migrations/scripts/seed_platform.py`  
**Priority**: 🔴 Critical — same file as Task 8.2; do in the same edit session

### Change

Find `TIER_TO_PLAN_MAP` (near the top of the file) and add the `trial` entry:

```python
# BEFORE
TIER_TO_PLAN_MAP = {
    "starter":      "starter_plan",
    "professional": "professional_plan",
    "enterprise":   "enterprise_plan",
}

# AFTER
TIER_TO_PLAN_MAP = {
    "trial":        "starter_plan",       # ← add this line
    "starter":      "starter_plan",
    "professional": "professional_plan",
    "enterprise":   "enterprise_plan",
}
```

The existing UPDATE logic in `mode_seed()` applies this automatically — no structural changes needed.

### Verify

```bash
python migrations/scripts/seed_platform.py --mode inspect | grep -A 10 "subscription_tier"
# Must show: trial → starter_plan  (was previously "(not linked)")
```

---

## Task 8.4 — Add `subscription_status` to `mode_show()` and `mode_inspect()`

**File**: `backend/migrations/scripts/seed_platform.py`  
**Priority**: 🟡 Important — do in the same edit session as Tasks 8.2 and 8.3

### `mode_show()` addition

After the line that prints notification templates, add:

```python
print(f"\nSubscription Statuses ({len(SUBSCRIPTION_STATUS_ROWS)}):")
for ss in SUBSCRIPTION_STATUS_ROWS:
    billing = "billing_active=true" if ss["is_billing_active"] else "billing_active=false"
    print(f"  {ss['code']:<12}  '{ss['name']}'  [{billing}]")
```

### `mode_inspect()` addition

After the notification template inspect block, add:

```python
# subscription_status
try:
    rows = db.execute(
        text(
            "SELECT code, name, is_billing_active FROM public.subscription_status "
            "WHERE tenant_id IS NULL ORDER BY code"
        )
    ).fetchall()
    print(f"\n  [subscription_status]  {len(rows)} row(s)")
    for r in rows:
        print(
            f"    • {r.code:<12}  '{r.name}'  billing_active={r.is_billing_active}"
        )
except Exception as e:
    print(f"  [subscription_status]  ERROR: {e}")
```

---

## Task 8.5 — New Alembic Migration: 3 Missing `subscription_status` Codes

**Priority**: 🟡 Important — not a dev-env blocker; do after verifying Tasks 8.1–8.4 pass

### Context

Migration `dd4ed7ed5f3b` already inserted 4 codes: `trial`, `active`, `past_due`, `canceled`. The dev DB is empty due to a schema-only restore, not a missing migration. `seed_platform.py` Task 8.2 is the correct dev-restore path for all 6 rows.

This migration ensures a **fresh production `alembic upgrade head`** also gets the 3 codes never in any prior migration: `trialing`, `unpaid`, `paused`.

### Create the migration (blank — never autogenerate)

```bash
cd <repo>/backend
source .venv/bin/activate
alembic revision -m "seed_subscription_status_missing_codes"
```

Open the generated file in `backend/migrations/versions/` and replace the auto-body with:

```python
"""seed subscription_status missing codes (trialing, unpaid, paused)

Revision ID: <auto-generated by alembic>
Revises: 50e2ffd2a388
Create Date: 2026-06-15

Context: Migration dd4ed7ed5f3b already seeds trial/active/past_due/canceled.
This migration adds the 3 Stripe-standard codes never previously migrated.
"""
from alembic import op


def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("""
        INSERT INTO public.subscription_status
            (id, tenant_id, code, name, is_billing_active, created_at, updated_at)
        VALUES
            (gen_random_uuid(), NULL, 'trialing', 'Trialing', true,  now(), now()),
            (gen_random_uuid(), NULL, 'unpaid',   'Unpaid',   false, now(), now()),
            (gen_random_uuid(), NULL, 'paused',   'Paused',   false, now(), now())
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM public.subscription_status
        WHERE code IN ('trialing', 'unpaid', 'paused')
          AND tenant_id IS NULL;
    """)
```

### Apply and verify

```bash
# Apply
alembic upgrade head

# Test downgrade/upgrade cycle (required per methods doc §13)
alembic downgrade -1
alembic upgrade head

# Verify new head
alembic current

# Verify all 3 codes now exist in a fresh-migration context
# (seed_platform.py handled the other 4 via Task 8.2)
```

---

## Task 8.6 — `seed_core.py` `mode_show()`: Add `notification_channel`

**File**: `backend/migrations/scripts/seed_core.py`  
**Priority**: 🟢 Polish

### What and why

`NOTIFICATION_CHANNEL_DEF` is a standalone module-level variable that is not inside `SIMPLE_CODE_TABLES` or `TENANT_NULLABLE_CODE_TABLES`. The `mode_show()` loop only iterates those two dicts — `notification_channel`'s 4 rows (`email`, `sms`, `push`, `in_app`) are completely invisible.

### Change

In `mode_show()`, after the loop that prints both dicts, add:

```python
print(
    f"  [notification_channel] — {len(NOTIFICATION_CHANNEL_DEF['rows'])} rows: "
    f"{', '.join(r['code'] for r in NOTIFICATION_CHANNEL_DEF['rows'])}"
)
```

### Verify

```bash
python migrations/scripts/seed_core.py --mode show | grep notification_channel
# Must print the 4 channel codes
```

---

## Task 8.7 — `seed_core.py` `mode_inspect()`: Add `description` to `notification_category`

**File**: `backend/migrations/scripts/seed_core.py`  
**Priority**: 🟢 Polish

### Change

In `mode_inspect()`, find the `notification_category` query block and add `description` to the SELECT:

```python
# BEFORE
rows = db.execute(
    text("SELECT code, display_label, display_order FROM public.notification_category ORDER BY display_order")
).fetchall()
for r in rows:
    print(f"    • [{r.display_order}] {r.code}  '{r.display_label}'")

# AFTER
rows = db.execute(
    text("SELECT code, display_label, description, display_order FROM public.notification_category ORDER BY display_order")
).fetchall()
for r in rows:
    desc = (r.description[:58] + "…") if r.description and len(r.description) > 58 else (r.description or "")
    print(f"    • [{r.display_order}] {r.code:<32}  '{r.display_label}'")
    print(f"          {desc}")
```

---

## Task 8.8 — `seed_scenario_dispatch.py` `mode_inspect()`: Add `scheduled_end_at`

**File**: `backend/migrations/scripts/seed_scenario_dispatch.py`  
**Priority**: 🟢 Polish

### What and why

The job query in `mode_inspect()` already selects `j.scheduled_end_at` but the print loop only shows `scheduled_start_at`. For dispatch board testing, both start and end times are needed to verify the job window.

### Change

Find the print loop for jobs in `mode_inspect()` and add the end time:

```python
# BEFORE
for j in jobs:
    sched = str(j.scheduled_start_at) if j.scheduled_start_at else "no schedule"
    print(f"    • {j.id}  status={j.status_code}  start={sched}")

# AFTER
for j in jobs:
    sched = str(j.scheduled_start_at) if j.scheduled_start_at else "no schedule"
    end = str(j.scheduled_end_at) if j.scheduled_end_at else "open"
    print(f"    • {j.id}  status={j.status_code}  {sched} → {end}")
```

---

## Task 8.9 — `reset_dev_db.py` `mode_inspect()`: Add Missing Tables to Count Loop

**File**: `backend/migrations/scripts/reset_dev_db.py`  
**Priority**: 🟡 Important — prevents silent data presence

### What and why

`loto_confirmation` and `calendar_sync_conflict` are in `GROUP_D_TABLES` (wiped by `--wipe-only`) but are absent from the `mode_inspect()` count-only loop. If data lands in these tables, `--mode inspect` shows nothing while `--wipe-only` silently deletes it.

### Change

Find the count-only `for table in [...]` loop at the bottom of `mode_inspect()` and add both tables at the top of the list:

```python
for table in [
    "loto_confirmation",        # ← add
    "calendar_sync_conflict",   # ← add
    "invoice",
    "invoice_line",
    "change_order",
    "change_order_line",
    "job_time_entry",
    "job_expense",
    "job_notes",
    "job_attachment",
    "quote_version",
    "entity_address",
    "entity_contact",
    "contact",
]:
```

---

## Verification Checkpoints

### Checkpoint 1 — After Task 8.1 (conftest change only)

```bash
cd <repo>/backend
source .venv/bin/activate

# Stripe tests — should fail with clear assertion message (not UUID mismatch)
pytest tests/ -k "stripe_subscription" -v 2>&1 | grep -E "(PASSED|FAILED|AssertionError)" | head -20
```

Expected: tests fail with message `"subscription_status 'active' not found in DB. Run: python migrations/scripts/seed_platform.py"`

### Checkpoint 2 — After Tasks 8.2 + 8.3 + 8.4

```bash
# Seed platform to insert subscription_status rows
python migrations/scripts/seed_platform.py
# Must show: ✅ [subscription_status] Inserted 'trialing' (and 5 more)

# Verify trial tier now linked
python migrations/scripts/seed_platform.py --mode inspect | grep -A 6 "subscription_tier"
# Must show: trial → starter_plan

# Verify subscription_status in show mode
python migrations/scripts/seed_platform.py --mode show | grep -A 8 "Subscription Status"

# Run Stripe tests — must NOW PASS
pytest tests/ -k "stripe_subscription" -v 2>&1 | tail -10

# Seed test tenant — subscription row must now be created
python migrations/scripts/seed_test_tenant.py
python migrations/scripts/seed_test_tenant.py --mode inspect | grep subscription
# Must show: [subscription] 1 row(s) plan=starter_plan is_active=True
```

### Checkpoint 3 — After Tasks 8.5–8.9

```bash
# Apply the new migration
alembic upgrade head
alembic current

# Verify all polish changes
python migrations/scripts/seed_core.py --mode show | grep notification_channel
python migrations/scripts/seed_core.py --mode inspect | grep -A 20 "notification_category"
python migrations/scripts/seed_scenario_dispatch.py --mode inspect | grep "→"
python migrations/scripts/reset_dev_db.py --mode inspect | grep -E "loto|calendar_sync"
```

### Final Verification Gate

```bash
cd <repo>/backend
source .venv/bin/activate

# 1. Full unit test suite — zero new failures
python -m pytest --tb=short -q 2>&1 | tail -10

# 2. Seed workflow — end-to-end
python migrations/scripts/seed_platform.py
python migrations/scripts/seed_test_tenant.py
python migrations/scripts/seed_scenario_quote_to_cash.py
python migrations/scripts/seed_scenario_dispatch.py

# 3. Inspect all groups
python migrations/scripts/seed_platform.py --mode inspect
python migrations/scripts/seed_test_tenant.py --mode inspect
python migrations/scripts/reset_dev_db.py --mode inspect

echo "=== SEED-TASK-03 / PHASE 0.8 FINAL VERIFICATION COMPLETE ==="
```

---

## Test Requirements

This task modifies seed scripts and `conftest.py` — it does not add new application endpoints. However, verify the following existing test files still pass cleanly after `conftest.py` changes:

```bash
# Stripe lifecycle tests — the ones most sensitive to subscription_status fixture changes
pytest tests/ -k "stripe" -v --tb=short 2>&1 | tail -20

# If any conftest fixture was changed, run the full suite to catch indirect effects
python -m pytest --tb=short -q 2>&1 | tail -5
```

Per `backend/tests/README-adding-tests.md`: any test that queries `subscription_status` must use the `get_or_assert_subscription_status()` pattern — never insert its own rows.

---

## Definition of Done

Update `pilot-app-pre-wkstm-3-prep-plan.md` §0.8.5 milestone checklist when each task is complete. Then add a **Phase 0.8 Completion Summary** subsection to §0.8 (see format guide below).

| Task | Done? |
|---|:---:|
| 8.1 Pre-work MCP queries run — `subscription_status` 0 rows confirmed, schema verified | ☐ |
| 8.1 `conftest.py` — fixture changed to query seeded rows with assert message | ☐ |
| 8.1 `pytest -k "stripe_subscription"` fails with clear assert message (not UUID mismatch) | ☐ |
| 8.2 `SUBSCRIPTION_STATUS_ROWS` constant added to `seed_platform.py` (6 rows) | ☐ |
| 8.2 `mode_seed()` inserts all 6 rows with `ON CONFLICT DO NOTHING` | ☐ |
| 8.2 `seed_platform.py` is idempotent — second run shows all `ℹ️` (no duplicates) | ☐ |
| 8.2 `pytest -k "stripe_subscription"` now **PASSES** | ☐ |
| 8.3 `"trial": "starter_plan"` added to `TIER_TO_PLAN_MAP` | ☐ |
| 8.3 `seed_platform.py --mode inspect` shows `trial → starter_plan` | ☐ |
| 8.4 `seed_platform.py --mode show` prints subscription_status section | ☐ |
| 8.4 `seed_platform.py --mode inspect` shows all 6 subscription_status rows | ☐ |
| 8.5 Alembic migration created — revises `50e2ffd2a388`, inserts 3 missing codes | ☐ |
| 8.5 Migration `upgrade → downgrade → upgrade` cycle passes cleanly | ☐ |
| 8.5 `alembic current` at new head after applying | ☐ |
| 8.6 `seed_core.py --mode show` prints `notification_channel` (4 codes) | ☐ |
| 8.7 `seed_core.py --mode inspect` shows description for each `notification_category` | ☐ |
| 8.8 `seed_scenario_dispatch.py --mode inspect` shows `start → end` for each job | ☐ |
| 8.9 `reset_dev_db.py --mode inspect` shows counts for `loto_confirmation` and `calendar_sync_conflict` | ☐ |
| **End-to-end seed run creates `subscription` row for test tenant** | ☐ |
| **`seed_test_tenant.py --mode inspect` shows `[subscription] 1 row(s) plan=starter_plan`** | ☐ |
| **Full `pytest` — zero new failures vs pre-work baseline** | ☐ |
| **Final test count (before → after) documented** | ☐ |
| **Completion Summary added to prep plan §0.8** | ☐ |

---

## Completion Summary Format

After all tasks are complete, add this section to `pilot-app-pre-wkstm-3-prep-plan.md` §0.8 (after §0.8.5):

```markdown
### Phase 0.8 Completion Summary (YYYY-MM-DD)

**Completed**: YYYY-MM-DD  
**Mode**: Pilot Python Engineer  
**Baseline**: X passed, Y failed  
**Final**: X+N passed, Y failed (net +N new tests from conftest changes)

#### What Was Accomplished

[List the key changes made, one bullet per task — follow the format from BETA-B1 completion summary in `pilot-app-beta-fixes-v1-impl-plan.md` §9]

#### Files Changed

| File | Change |
|---|---|
| `backend/tests/conftest.py` | subscription_status fixture → query seeded rows |
| `backend/migrations/scripts/seed_platform.py` | SUBSCRIPTION_STATUS_ROWS + TIER_TO_PLAN_MAP trial + mode_show/inspect updates |
| `backend/migrations/versions/YYYYMMDD_seed_subscription_status_missing_codes.py` | New migration — 3 missing codes |
| `backend/migrations/scripts/seed_core.py` | notification_channel in show; description in inspect |
| `backend/migrations/scripts/seed_scenario_dispatch.py` | scheduled_end_at in inspect |
| `backend/migrations/scripts/reset_dev_db.py` | loto_confirmation + calendar_sync_conflict in count loop |

#### Next Step

Proceed to **Phase 0.7.3 Step 3** — run the full seed workflow and smoke test the UI.
```

---

## After This Task — Next Step

Once all Definition of Done items are checked and the Completion Summary is added, run the **Phase 0.7.3 Step 3** smoke test from `pilot-app-pre-wkstm-3-prep-plan.md` §0.7.3:

```bash
# Full dev DB population
python migrations/scripts/seed_platform.py
python migrations/scripts/seed_test_tenant.py
python migrations/scripts/seed_scenario_quote_to_cash.py
python migrations/scripts/seed_scenario_dispatch.py

# Then manually verify:
# - Login as dev@pilot.local → dashboard loads
# - /customers → 5 customers visible
# - /quotes → 1 draft quote visible
# - /dispatch → 5 jobs on dispatch board
# - /settings/billing → Starter plan visible
# - /settings/integrations → renders without crash
```
