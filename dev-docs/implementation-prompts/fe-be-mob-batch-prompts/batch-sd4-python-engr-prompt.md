# Implementation Prompt: SD-4 — Group C Test Tenant Seed Audit & Expansion

**Mode**: Pilot Python Engineer  
**Batch**: SD-4  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2 P1 — Full UI Seed Data Expansion  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-sd4-design.md`  
**Estimated session**: 2–3 hours  
**Platform**: Backend only (`backend/migrations/scripts/`) — seed scripts only, no application code, no Alembic migrations  
**Frontend companion**: None — but these seed changes are required before the Full UI Seed Data Expansion testing pass

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §16 (Standard Task Workflow), §5 (Model Design), §13 (Alembic)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test structure and seed data coexistence rules

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every column name before writing any SQL in this batch. If MCP returns unexpected results → **STOP and ask Tom**.
- **Rule 2**: This batch is **seed scripts only** — no Alembic migrations, no application code changes, no route files, no model files. All changes stay in `backend/migrations/scripts/seed_platform.py` and `backend/migrations/scripts/seed_test_tenant.py`.
- **Rule 3**: `burden_pct` is stored as a **decimal fraction** (`0.25` = 25%). Never use integer percentages. The formula in the codebase is `int(hourly_rate_cents * (1 + burden_pct))`. Using `0.25` for 25% is correct. Using `25` would produce a 2600% burdened rate.
- **Rule 4**: `labor_rate_version` uses a GiST exclusion constraint on `(tenant_id, skill_level_code)` with overlapping `valid_period`. The open-ended rows `[2026-06-01, NULL)` already exist. Do **NOT** insert new rows for the same `(tenant_id, skill_level_code)` — this violates the constraint. You MUST **UPDATE** the existing rows to set `burden_pct`.
- **Rule 5**: UUID `00000000-0000-0000-0000-000000000005` is newly reserved for the accountant user in this batch. Do not use any other value. Do not use `uuid4()` for this user.
- **Rule 6**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE data.
- **Rule 7**: If ANY test fails during your work → **fix it before declaring the batch done**. No "pre-existing failure" exception without explicit Tom confirmation.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> If any tests are already failing before you start: confirm with Tom before proceeding.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

> **MCP Usage Rule**: Read-only verification only. Never INSERT, UPDATE, or DELETE via MCP.

```sql
-- 1. Verify subscription_tier columns and current annual price ID state
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription_tier'
ORDER BY ordinal_position;

-- 2. Confirm current stripe_price_id values on subscription_tier
SELECT tier_name, stripe_price_id_monthly, stripe_price_id_annual, is_active
FROM subscription_tier ORDER BY display_order;

-- 3. Verify tenant stripe_customer_id column exists and is NULL
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant'
  AND column_name = 'stripe_customer_id';

SELECT id, stripe_customer_id FROM tenant
WHERE id = '00000000-0000-0000-0000-000000000001';

-- 4. Verify user_endpoint columns (channel, value, is_primary, verification_status, consent_status)
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'user_endpoint'
ORDER BY ordinal_position;

-- 5. Confirm current user_endpoint rows for test tenant
SELECT ue.user_id, ue.channel, ue.value, ue.is_primary
FROM user_endpoint ue
JOIN tenant_user tu ON tu.user_id = ue.user_id
WHERE tu.tenant_id = '00000000-0000-0000-0000-000000000001'
ORDER BY ue.user_id, ue.channel;

-- 6. Confirm password_policy columns including lockout fields
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'password_policy'
ORDER BY ordinal_position;

-- 7. Confirm current password_policy row
SELECT min_length, min_uppercase, min_digits, lockout_threshold,
       lockout_window_minutes, lockout_duration_minutes, history_depth
FROM password_policy WHERE tenant_id = '00000000-0000-0000-0000-000000000001';

-- 8. Confirm subscription columns: quantity_seats, billing_anchor
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription'
  AND column_name IN ('quantity_seats', 'billing_anchor');

SELECT quantity_seats, billing_anchor FROM subscription
WHERE tenant_id = '00000000-0000-0000-0000-000000000001';

-- 9. Confirm labor_rate_version current state
SELECT skill_level_code, hourly_rate_cents, burden_pct, valid_period
FROM labor_rate_version
WHERE tenant_id = '00000000-0000-0000-0000-000000000001'
ORDER BY skill_level_code;

-- 10. Confirm discount_version current state (expect 0 rows)
SELECT code, pct_off, amount_off_cents FROM discount_version
WHERE tenant_id = '00000000-0000-0000-0000-000000000001';

-- 11. Confirm tenant_email_branding columns
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_email_branding'
ORDER BY ordinal_position;

-- 12. Confirm no UUID ...0005 user exists yet
SELECT id, email FROM "user" WHERE id = '00000000-0000-0000-0000-000000000005';
```

**Expected results before starting work**:
- `subscription_tier.stripe_price_id_annual` is NULL for all rows
- `tenant.stripe_customer_id` is NULL for `...0001`
- `user_endpoint` has 3 rows (email only, one per user)
- `password_policy.lockout_threshold` is NULL
- `subscription.quantity_seats = 1`, `billing_anchor = NULL`
- `labor_rate_version` has 3 rows, all `burden_pct = 0.0`
- `discount_version` returns 0 rows
- UUID `...0005` does not exist in `user`

---

## Pre-Work: Read These Source Files

Use `read_file` on each before writing any code:

```
backend/migrations/scripts/seed_test_tenant.py    ← full source — understand all existing patterns
backend/migrations/scripts/seed_platform.py       ← find subscription_tier upsert block
backend/migrations/scripts/_db_utils.py           ← understand get_db_session context manager
```

---

## Background

SD-4 enriches Group B (`seed_platform.py`) and Group C (`seed_test_tenant.py`) seed data to support comprehensive UI testing. No application code changes. No Alembic migrations. Two seed script files only.

The batch covers 12 changes across 2 files, organized into 4 logical task groups below.

---

## Task Group 1 — seed_platform.py: Add stripe_price_id_annual (D2)

**File**: `backend/migrations/scripts/seed_platform.py`

**Problem**: `subscription_tier.stripe_price_id_annual` is NULL for all tiers. Tom created annual Stripe prices in test mode on 2026-07-14. The seed script must now populate these values so they survive any DB reset.

**Changes**:

1. At the top of `seed_platform.py`, add price ID constants — test-mode active, live-mode as comments:

```python
# ── Stripe annual price IDs ────────────────────────────────────────────────
# Test-mode (used by this script — targets dev/QA/e2e DBs):
STRIPE_PRICE_ID_ANNUAL_STARTER_TEST = "price_REDACTED07"  # $588/yr
STRIPE_PRICE_ID_ANNUAL_TEAMS_TEST   = "price_REDACTED08"  # $1,788/yr

# Live-mode (production DB — NOT used by this script today).
# When seed scripts are refactored to accept --env dev|production flags,
# pass these values when --env production is given:
# STRIPE_PRICE_ID_ANNUAL_STARTER_LIVE = "price_REDACTED05"  # $588/yr
# STRIPE_PRICE_ID_ANNUAL_TEAMS_LIVE   = "price_REDACTED06"  # $1,788/yr
```

2. In the `subscription_tier` upsert block, add `stripe_price_id_annual` to:
   - The `INSERT` column list and VALUES (use `STRIPE_PRICE_ID_ANNUAL_STARTER_TEST` / `STRIPE_PRICE_ID_ANNUAL_TEAMS_TEST`; pass `None` for `founders` and `trial`)
   - The `ON CONFLICT DO UPDATE` SET clause

```sql
INSERT INTO public.subscription_tier
(..., stripe_price_id_annual, ...)
VALUES (..., :stripe_price_id_annual, ...)
ON CONFLICT (tier_name) DO UPDATE
    SET stripe_price_id_annual = EXCLUDED.stripe_price_id_annual,
        ...
```

> `founders` and `trial` tiers: pass `None` for `stripe_price_id_annual` — free tiers have no Stripe price object.

**Verify after change**:
```bash
python migrations/scripts/seed_platform.py --mode inspect
# Should show: starter stripe_price_id_annual=price_REDACTED...
# Should show: teams   stripe_price_id_annual=price_REDACTED...
```

---

## Task Group 2 — seed_test_tenant.py: Users, Tenant, Endpoints (D3–D6)

**File**: `backend/migrations/scripts/seed_test_tenant.py`

### 2a — Add accountant user constant (D6)

At the top of the file, add:
```python
ACCOUNTANT_USER_ID = UUID("00000000-0000-0000-0000-000000000005")
ACCOUNTANT_EMAIL = "accountant@pilot.local"
ACCOUNTANT_FIRST_NAME = "Dev"
ACCOUNTANT_LAST_NAME = "Accountant"
ACCOUNTANT_DISPLAY_COLOR = "#8B5CF6"  # purple
```

### 2b — Set display_color for owner + office_staff (D5)

Add these constants:
```python
OWNER_DISPLAY_COLOR = "#10B981"   # green
OFFICE_DISPLAY_COLOR = "#F59E0B"  # amber
# TECH keeps: TECH_DISPLAY_COLOR = "#3B82F6"  (blue — already set)
```

Update the `users` list in `mode_seed()` to include `display_color` for all 4 users (owner uses `OWNER_DISPLAY_COLOR`, tech uses `TECH_DISPLAY_COLOR`, office uses `OFFICE_DISPLAY_COLOR`, accountant uses `ACCOUNTANT_DISPLAY_COLOR`).

The existing `ON CONFLICT (id) DO UPDATE SET display_color = EXCLUDED.display_color` already handles the UPDATE path for existing rows — no extra patch needed.

### 2c — Add accountant to users list + role_map (D6)

Add the accountant user dict to the `users` list, and add `(str(ACCOUNTANT_USER_ID), "accountant")` to the `role_map` list.

Update `mode_show()` to mention the 4th user.

### 2d — Set tenant.stripe_customer_id (D4)

Add constant:
```python
STRIPE_CUSTOMER_ID_TEST = "cus_REDACTEDX01"  # Test-mode customer, created 2026-07-14
```

Update the tenant upsert to include `stripe_customer_id` in both the INSERT columns and the `ON CONFLICT DO UPDATE` SET clause:
```sql
INSERT INTO public.tenant
(id, name, is_active, current_subscription_tier_id, created_by, stripe_customer_id, created_at, updated_at)
VALUES (:id, :name, true, :tier_id, :created_by, :stripe_customer_id, NOW(), NOW())
ON CONFLICT (id) DO UPDATE
    SET name = EXCLUDED.name,
        stripe_customer_id = EXCLUDED.stripe_customer_id,
        updated_at = NOW()
```

### 2e — Add in_app + push user_endpoint rows for all users (D3)

After the existing email endpoint logic, add a loop that inserts `in_app` and `push` endpoints for every user.

**Deterministic fake Expo push tokens** (format: `ExponentPushToken[...]` — test-only, no real device registration):
```python
PUSH_TOKENS = {
    str(owner_id):           "ExponentPushToken[test-owner-00000002]",
    str(TECH_USER_ID):       "ExponentPushToken[test-tech-00000003]",
    str(OFFICE_USER_ID):     "ExponentPushToken[test-office-00000004]",
    str(ACCOUNTANT_USER_ID): "ExponentPushToken[test-acct-00000005]",
}
```

**in_app endpoint value**: use the user's email address (in-app channel identifies users by email).

Insert pattern per user × channel (`in_app`, `push`):
```sql
INSERT INTO public.user_endpoint
(id, user_id, channel, value, is_primary, verification_status,
 consent_status, is_active, created_at, updated_at)
VALUES (gen_random_uuid(), :uid, :channel, :value, false, 'verified',
        'opted_in', true, NOW(), NOW())
ON CONFLICT DO NOTHING
```

> `is_primary = false` — email is the primary endpoint; in_app + push are secondary.
> SMS is intentionally absent — Telnyx 10DLC not yet authorized.

**Verify**:
```bash
python migrations/scripts/seed_test_tenant.py --mode inspect
# Should show: [user_endpoint] 12 row(s)  (4 users × 3 channels: email, in_app, push)
```

---

## Task Group 3 — seed_test_tenant.py: Config Tables (D7–D10)

### 3a — Fill password_policy lockout/history fields (D7)

Update the `password_policy` INSERT to include all lockout and history fields:
```sql
INSERT INTO public.password_policy
(id, tenant_id, min_length, min_uppercase, min_digits,
 lockout_threshold, lockout_window_minutes, lockout_duration_minutes,
 history_depth, rotation_days, require_mfa, created_at, updated_at)
VALUES (gen_random_uuid(), :tid, 8, 1, 1, 5, 15, 30, 5, NULL, false, NOW(), NOW())
ON CONFLICT DO NOTHING
```

For the existing row (already inserted without lockout fields), add an UPDATE patch after the INSERT:
```sql
UPDATE public.password_policy
SET lockout_threshold = 5,
    lockout_window_minutes = 15,
    lockout_duration_minutes = 30,
    history_depth = 5,
    updated_at = NOW()
WHERE tenant_id = :tid
  AND lockout_threshold IS NULL
```

### 3b — Set tenant_email_branding.custom_footer (D8)

Add constant:
```python
CUSTOM_FOOTER = "© 2026 Pilot Dev Tenant. All rights reserved."
```

Update `tenant_email_branding` INSERT to include `custom_footer`:
```sql
INSERT INTO public.tenant_email_branding
(tenant_id, brand_color_hex, email_signature, custom_footer, created_at)
VALUES (:tid, '#2563EB', 'Pilot Dev Tenant — dev only', :footer, NOW())
ON CONFLICT DO NOTHING
```

For existing rows, patch if NULL:
```sql
UPDATE public.tenant_email_branding
SET custom_footer = :footer
WHERE tenant_id = :tid AND custom_footer IS NULL
```

### 3c — Update subscription: quantity_seats=4, billing_anchor='2026-07-01' (D10)

The subscription INSERT uses `ON CONFLICT DO NOTHING` — an existing subscription row will not be updated by the INSERT. You must also handle the UPDATE path.

Update the INSERT to include `billing_anchor`:
```sql
INSERT INTO public.subscription
(id, tenant_id, product_plan_code, status_id, quantity_seats,
 billing_anchor, started_at, billing_interval, cancel_at_period_end, is_active,
 created_at, updated_at)
VALUES (gen_random_uuid(), :tid, :plan_code, :status_id, 4,
        '2026-07-01', NOW(), 'monthly', false, true, NOW(), NOW())
ON CONFLICT DO NOTHING
```

After the INSERT, add an UPDATE patch for existing rows:
```sql
UPDATE public.subscription
SET quantity_seats = 4,
    billing_anchor = '2026-07-01',
    updated_at = NOW()
WHERE tenant_id = :tid
  AND (quantity_seats <> 4 OR billing_anchor IS NULL)
```

---

## Task Group 4 — seed_test_tenant.py: Pricing & Discounts (D12–D13)

### 4a — UPDATE labor_rate_version burden_pct (D12)

⚠️ **CRITICAL**: Do NOT insert new rows. UPDATE existing rows only.

The open-ended rows `[2026-06-01, NULL)` already exist. Inserting a new row with the same `(tenant_id, skill_level_code)` and overlapping range violates the GiST exclusion constraint.

After the existing labor rate INSERT block, add UPDATE logic:
```python
burden_updates = [
    ("master",     Decimal("0.25")),  # $120 × 1.25 = $150.00/hr burdened
    ("journeyman", Decimal("0.20")),  # $85 × 1.20 = $102.00/hr burdened
    ("apprentice", Decimal("0.15")),  # $55 × 1.15 = $63.25/hr burdened
]
for skill_level, burden in burden_updates:
    db.execute(
        text("""
            UPDATE public.labor_rate_version
            SET burden_pct = :pct
            WHERE tenant_id = :tid AND skill_level_code = :code
        """),
        {"tid": tid, "pct": burden, "code": skill_level},
    )
    print(f"  ✅ [labor_rate_version] Updated '{skill_level}' burden_pct → {burden}")
```

Import `Decimal` from the `decimal` module at the top of the file if not already imported.

### 4b — Add mode_inspect() coverage for discount_version (D13)

The discount rows are already defined in the existing `discount_rows` list in `mode_seed()`. No change needed to the INSERT logic — the rows simply need to be seeded on the next run.

However, `mode_inspect()` currently has NO `discount_version` block. Add one after the `tenant_markup_version` block:

```python
discounts = db.execute(
    text("""
        SELECT code, pct_off, amount_off_cents,
               lower(valid_period) AS valid_from,
               upper(valid_period) AS valid_until
        FROM public.discount_version
        WHERE tenant_id = :tid
        ORDER BY code
    """),
    {"tid": tid},
).fetchall()
print(f"\n  [discount_version]  {len(discounts)} row(s)")
for d in discounts:
    if d.pct_off is not None:
        print(f"    '{d.code}'  {d.pct_off}% off  valid: [{d.valid_from} → {d.valid_until or 'open'}]")
    else:
        print(f"    '{d.code}'  ${d.amount_off_cents / 100:.2f} off  valid: [{d.valid_from} → {d.valid_until or 'open'}]")
```

**Verify discount rows ARE in the DB after seeding**:
```bash
python migrations/scripts/seed_test_tenant.py --mode inspect
# Should show: [discount_version]  2 row(s)
#   'NEW_CUSTOMER'  $25.00 off  valid: [2026-01-01... → open]
#   'SUMMER_PROMO'  10% off     valid: [2024-06-01... → 2024-08-31...]
```

---

## Task Group 5 — README-seed-data.md Updates

**File**: `backend/README-seed-data.md`

Update §4 Group C table to reflect all new rows:

| Table | Before | After SD-4 |
|---|---|---|
| `user` | 3 rows | **4 rows** (add `accountant@pilot.local` UUID `...0005`) |
| `user_endpoint` | 3 rows (email only) | **12 rows** (4 users × 3 channels: email, in_app, push) |
| `tenant_user` | 3 rows | **4 rows** |
| `password_policy` | 1 row (min_length=8, min_uppercase=1, min_digits=1) | **1 row** (+ lockout_threshold=5, window=15m, duration=30m, history_depth=5) |
| `tenant_email_branding` | 1 row (no footer) | **1 row** (custom_footer set) |
| `subscription` | 1 row (seats=1, billing_anchor=NULL) | **1 row** (seats=4, billing_anchor=2026-07-01) |
| `labor_rate_version` | 3 rows (burden_pct=0.0) | **3 rows** (master=0.25, journeyman=0.20, apprentice=0.15) |
| `discount_version` | 0 rows | **2 rows** (SUMMER_PROMO + NEW_CUSTOMER) |

Update §5 Deterministic UUIDs to add:

| Entity | UUID | Email |
|---|---|---|
| Accountant User | `00000000-0000-0000-0000-000000000005` | `accountant@pilot.local` |

Update §4 Group B `subscription_tier` row to note `stripe_price_id_annual` now set for `starter` + `teams`.

---

## Verification Checkpoints

**After Task Group 1** (seed_platform.py):
```bash
cd <repo>/backend && source .venv/bin/activate
python migrations/scripts/seed_platform.py --mode inspect
# Confirm: starter stripe_price_id_annual=price_REDACTED07
# Confirm: teams   stripe_price_id_annual=price_REDACTED08
```

**After Task Groups 2–4** (seed_test_tenant.py):
```bash
python migrations/scripts/seed_test_tenant.py
python migrations/scripts/seed_test_tenant.py --mode inspect
```

Expected inspect output:
```
[tenant]  1 row(s)
  00000000-...-0001  "Pilot Dev Tenant"  is_active=True

[user]  4 row(s)
  ...0002  dev@pilot.local         role=owner
  ...0003  tech@pilot.local        role=technician
  ...0004  office@pilot.local      role=office_staff
  ...0005  accountant@pilot.local  role=accountant

[user_endpoint]  12 row(s)
  ...0002  channel=email    value=dev@pilot.local           status=verified  consent=opted_in
  ...0002  channel=in_app   value=dev@pilot.local           status=verified  consent=opted_in
  ...0002  channel=push     value=ExponentPushToken[...]    status=verified  consent=opted_in
  ... (similar for ...0003, ...0004, ...0005)

[password_policy]  1 row(s)  min_length=8  (lockout_threshold=5)
[tenant_email_branding]  1 row(s)  brand_color=#2563EB
[tenant_onboarding_checklist]  1 row(s)  dismissed=True

[subscription]  1 row(s)  plan=founders_plan  is_active=True
  (quantity_seats=4, billing_anchor=2026-07-01)

[labor_rate_version]  3 row(s)
  apprentice  @ 5500¢/hr  ($55.00/hr)  burden=0.15  → burdened=$63.25/hr
  journeyman  @ 8500¢/hr  ($85.00/hr)  burden=0.20  → burdened=$102.00/hr
  master      @ 12000¢/hr ($120.00/hr) burden=0.25  → burdened=$150.00/hr

[tenant_markup_version]  1 row(s)  pct=20.0
[discount_version]  2 row(s)
  'NEW_CUSTOMER'  $25.00 off  valid: [2026-01-01... → open]
  'SUMMER_PROMO'  10% off     valid: [2024-06-01... → 2024-08-31...]
```

---

## Final Verification

### Phase 1 — Unit Tests Only

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass. This batch does not add new application code, so no new test files are required. The seed scripts are verified via their own `--mode inspect` output.

> **If unit tests fail** that were passing at baseline — investigate before proceeding. These scripts modify shared seed data (UUIDs `...0001`–`...0005`). If a test was relying on `burden_pct=0.0` or `quantity_seats=1` or missing endpoints, it must be fixed.

### Phase 2 — Full Suite

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest --tb=short -q 2>&1 | tail -10

echo "=== SD-4 FINAL VERIFICATION COMPLETE ==="
```

---

## Test Requirements

This batch modifies **only seed scripts** — no new application code is added. Therefore:
- **No new test files are required.**
- The seed scripts are self-verifying via `--mode inspect`.
- If any existing test breaks due to the seed data changes (e.g., a test that asserts `burden_pct=0.0` on the master labor rate), fix the test — the old value was wrong.

**Known test areas to watch**: 
- Tests in `tests/domains/catalog_pricing/` that create `labor_rate_version` rows should use past closed date ranges (GiST safe) — they won't conflict with the open-ended seeded rows. Verify they still pass.
- Tests in `tests/domains/subscriptions_usage/` that reference `test_tenant.stripe_customer_id` — confirm they use the `test_tenant` fixture (which now has `cus_REDACTEDX01`) and don't assert `stripe_customer_id IS NULL`.

---

## Definition of Done

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed (or confirmed with Tom)
- [ ] All 12 MCP pre-work queries run and results match expected pre-implementation state
- [ ] All mandatory source files read before writing any code
- [ ] **Task Group 1**: `seed_platform.py` — `stripe_price_id_annual` set for starter + teams (test-mode IDs)
- [ ] **Task Group 2a**: `ACCOUNTANT_USER_ID` constant added (`...0005`), 4th user in `users` list
- [ ] **Task Group 2b**: `OWNER_DISPLAY_COLOR = "#10B981"` and `OFFICE_DISPLAY_COLOR = "#F59E0B"` set
- [ ] **Task Group 2c**: `accountant@pilot.local` in `role_map` as `"accountant"`
- [ ] **Task Group 2d**: `STRIPE_CUSTOMER_ID_TEST = "cus_REDACTEDX01"` set on tenant upsert
- [ ] **Task Group 2e**: `in_app` + `push` endpoints added for all 4 users (12 total user_endpoint rows)
- [ ] **Task Group 3a**: `password_policy` lockout/history fields set (threshold=5, window=15, duration=30, history=5)
- [ ] **Task Group 3b**: `tenant_email_branding.custom_footer` set
- [ ] **Task Group 3c**: `subscription.quantity_seats=4`, `billing_anchor='2026-07-01'` — both INSERT and UPDATE path
- [ ] **Task Group 4a**: `labor_rate_version` burden_pct UPDATED (not inserted): master=0.25, journeyman=0.20, apprentice=0.15
- [ ] **Task Group 4b**: `discount_version` inspect block added to `mode_inspect()`; 2 discount rows present after seed run
- [ ] **Task Group 5**: `backend/README-seed-data.md` §4 Group C + §5 UUID table updated
- [ ] `python migrations/scripts/seed_platform.py --mode inspect` shows annual price IDs set
- [ ] `python migrations/scripts/seed_test_tenant.py --mode inspect` shows all 12 expected data points
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures including any pre-existing
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `pilot-launch-plan.md` Appendix B

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** to `dev-docs/analysis/pilot-launch-plan.md` Appendix B using the format below.
2. Update `backend/README-seed-data.md` §10 Roadmap to note SD-4 as ✅ Complete with date.

```markdown
### SD-4 — Group C Test Tenant Seed Audit & Expansion: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- Added 4th test user `accountant@pilot.local` (UUID `...0005`, role=accountant, color=#8B5CF6)
- Set display_color for owner (#10B981) and office_staff (#F59E0B)
- Set `tenant.stripe_customer_id = 'cus_REDACTEDX01'` (test-mode Stripe customer)
- Added in_app + push user_endpoint rows for all 4 users (12 total endpoints)
- Filled password_policy lockout/history fields (threshold=5, window=15m, duration=30m, history=5)
- Set tenant_email_branding.custom_footer
- Updated subscription quantity_seats=4, billing_anchor=2026-07-01
- Updated labor_rate_version burden_pct: master=0.25, journeyman=0.20, apprentice=0.15
- Seeded discount_version: SUMMER_PROMO (10%) + NEW_CUSTOMER ($25 off); added inspect coverage
- Populated subscription_tier.stripe_price_id_annual for starter + teams (test-mode IDs)
- Updated README-seed-data.md §4/§5 to reflect all new seed state

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/migrations/scripts/seed_platform.py` | Updated — stripe_price_id_annual added to subscription_tier upsert |
| `backend/migrations/scripts/seed_test_tenant.py` | Updated — 11 enhancements across users, endpoints, config, pricing |
| `backend/README-seed-data.md` | Updated — §4 Group C + §5 UUID table |
```

---

## After This Batch — Next Step

Once SD-4 is complete, run the full reseed sequence to populate all Group C data in the dev DB:

```bash
cd <repo>/backend
source .venv/bin/activate

python migrations/scripts/seed_platform.py
python migrations/scripts/seed_test_tenant.py
python migrations/scripts/seed_test_tenant.py --mode inspect
```

Then Tom can proceed with the **Web UI Full Regression** pass (per launch plan P1 — Systematic UI + Integration Testing).
