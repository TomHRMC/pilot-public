# Implementation Prompt: C-B2 — Charter Entitlement Schema + `tenant_messaging_registration` Table

**Mode**: Pilot Python Engineer
**Batch**: C-B2
**Source plan**: `pilot-launch-plan.md` §2.0 row 14g + §2.1a Order C-2
**Design doc**: `batch-c-b2-design.md`
**Estimated session**: 3–4 hours
**Platform**: Backend only (`backend/`)
**Frontend companion**: None (frontend consumes the new API fields in C-B5)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, and fixture rules
- **`dev-docs/architecture-design/batch-designs/batch-c-b2-design.md`** — the batch design doc (sections A–G)

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 4**: All Alembic migrations must be written as **blank** migrations (never `--autogenerate`). Data changes use raw `op.execute()` with `SET LOCAL session_replication_role = 'replica';`.
- **Rule 11**: If ANY test fails during your work — even one that appears to be a pre-existing failure — **you must fix it before declaring the batch done**. There is no "not my fault" exception.
- **Rule 14 (Ruff)**: Run ruff **only against the files you changed** — `git diff --name-only HEAD -- '*.py'` to get the list, then `ruff check --fix <files> && ruff format <files>`. Fix ALL errors in those files including pre-existing ones.
- **Rule 15 (audit mixins — rules §24)**: New tables inherit exactly one mixin from `app/models/mixins.py` (`StandardAuditMixin` / `AppendOnlyMixin` / `MachineLogMixin`) — never hand-declare `created_at`/`updated_at`. Add `tenant_id` explicitly (mixins do not provide it). All timestamps are TIMESTAMPTZ → the UTC-aware datetime rule is non-negotiable. **The raw DDL `CREATE TABLE` in the migration MUST include all four audit columns: `created_at`, `updated_at`, `created_by`, `updated_by`** — not just the first two.
- **Rule 16 (verify, don't assume — rules §25)**: 186 tables exist. Query `information_schema.columns` for every table you touch this session before writing SQL.

**Before writing any subscription, billing, or entitlement code:**
Read `dev-docs/pilot-operations.md` — covers: tier→plan→ppfv cascade, `is_billing_active` paywall gate, Charter cohort Stripe schedule, notification template resolution order, and all 6 subscription status codes. The billing logic is NOT inferrable from the schema alone.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed. Either confirm with Tom that this is a known, accepted failure, or fix it before touching any batch files.

---

## Pre-Work: Run MCP Verification Queries

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE — all data changes go through the application code, seed scripts, or Alembic migrations. If a query fails → STOP and ask Tom.

Run **all** of these via `postgres-local` MCP before writing any code:

```sql
-- 1. Verify subscription_tier columns (confirm the 4 new cols don't exist yet)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription_tier'
ORDER BY ordinal_position;
-- Expected: 17 columns, NONE of: free_period_days, requires_payment_method, signup_cap, price_locked

-- 2. Verify tenant columns (confirm the 3 new cols don't exist yet)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant'
ORDER BY ordinal_position;
-- Expected: 14 columns, NONE of: free_period_ends_at, charter_member_number, charter_eligible

-- 3. Verify tenant_tier_override columns (confirm the 1 new col doesn't exist yet)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_tier_override'
ORDER BY ordinal_position;
-- Expected: 10 columns, NO override_free_period_ends_at

-- 4. Verify tenant_messaging_registration does NOT exist yet
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name = 'tenant_messaging_registration';
-- Expected: 0 rows

-- 5. Verify current tier data (post-C-B1: charter, not founders)
SELECT tier_name, display_label, monthly_price_cents, annual_price_cents, is_active, product_plan_code
FROM subscription_tier ORDER BY display_order;
-- Expected: charter (active, $0/$0, charter_plan), trial (inactive), starter (inactive), teams (inactive)

-- 6. Verify the audit columns on an existing table (confirm the 4-column pattern)
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription_tier'
  AND column_name IN ('created_at', 'updated_at', 'created_by', 'updated_by');
-- Expected: all 4 rows returned — every table has all four audit columns
```

**If any of these don't match the expected results → STOP and ask Tom.**

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/app/models/subscription.py          ← why: SubscriptionTier model — add 4 new fields here
backend/app/models/tenant.py                ← why: Tenant model — add 3 new fields here
backend/app/models/mixins.py                ← why: StandardAuditMixin definition — confirm the 4 audit columns
backend/app/models/billing.py               ← why: TenantTierOverride model location (or find it)
backend/api/schemas/subscription.py         ← why: SubscriptionTierResponse Pydantic schema — add new fields
backend/migrations/scripts/seed_platform.py ← why: tier seed dict — add new columns
backend/migrations/versions/2026_08_02_XXXX-XXXX_c_b1_charter_rename.py ← why: C-B1 migration pattern reference (most recent migration)
backend/db_models_map.md                    ← why: confirm model names and table mappings
backend/README-seed-data.md                 ← why: standing reference doc — update with new columns
backend/tests/conftest.py                   ← why: understand available fixtures
```

Also run these to find related files:
```bash
# Find the TenantTierOverride model
grep -rn "TenantTierOverride\|tenant_tier_override" backend/app/models/ --include="*.py"

# Find the subscription schema file
grep -rn "SubscriptionTierResponse" backend/api/schemas/ --include="*.py"

# Find existing model files to determine where TenantMessagingRegistration should live
ls backend/app/models/
```

---

## Context: What This Batch Does

The Commercial Implementation Spec §3 defines new schema for the Charter program lifecycle. This batch adds the columns and creates the new table. **No new endpoints, no new business logic** — just schema + models + seed data + API response fields.

**Schema changes** (all verified safe via MCP — no conflicts with existing columns):

| Table | New columns | Type |
|---|---|---|
| `subscription_tier` | `free_period_days`, `requires_payment_method`, `signup_cap`, `price_locked` | INTEGER, BOOLEAN NOT NULL DEFAULT TRUE, INTEGER, BOOLEAN NOT NULL DEFAULT FALSE |
| `tenant` | `free_period_ends_at`, `charter_member_number`, `charter_eligible` | TIMESTAMPTZ, INTEGER (partial unique), BOOLEAN NOT NULL DEFAULT TRUE |
| `tenant_tier_override` | `override_free_period_ends_at` | TIMESTAMPTZ |
| `tenant_messaging_registration` | **New table** (14 columns + 4 audit = 18 total) | See design doc §B.1 |

**Tier seed data update**: Charter price changes from $0 → $49/mo ($588 annual), plus the 4 new fields populated for all 4 tiers.

**⚠️ Schema drift from spec**: The spec §3.1-3.2 uses hypothetical column names (`code`, `display_name`, `price_cents`). The real columns are `tier_name`, `display_label`, `annual_price_cents`/`monthly_price_cents`. The design doc §B.1 has the corrected SQL — use that, not the spec.

---

## Task 1 — Create Alembic Migration

Create a blank migration:

```bash
cd <repo>/backend
source .venv/bin/activate
alembic revision -m "c_b2_charter_entitlement_schema"
```

Write the migration per design doc §B.1. Key points:

1. **Part 1**: `ALTER TABLE subscription_tier ADD COLUMN` × 4 (all safe — verified via MCP)
2. **Part 2**: `ALTER TABLE tenant ADD COLUMN` × 3 + create 2 indexes (partial index on `free_period_ends_at`, partial unique index on `charter_member_number`)
3. **Part 3**: `ALTER TABLE tenant_tier_override ADD COLUMN` × 1
4. **Part 4**: `CREATE TABLE tenant_messaging_registration` — **MUST include all four audit columns**: `created_at`, `updated_at`, `created_by`, `updated_by` (per Rule 15 + Architect audit mixin rule)
5. **Part 5**: `UPDATE subscription_tier` × 4 (set new field values for each tier) — use `SET LOCAL session_replication_role = replica` for the data UPDATEs
6. **Downgrade**: Reverse all changes — drop table, drop columns, restore old pricing

Test the full cycle:
```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
alembic current   # must show new head revision
```

**Intermediate verification:**
```bash
# Verify the new columns exist
python -c "
from sqlalchemy import create_engine, text
import os
engine = create_engine(os.environ['DATABASE_URL'])
with engine.connect() as conn:
    result = conn.execute(text(\"SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='subscription_tier' AND column_name IN ('free_period_days','requires_payment_method','signup_cap','price_locked')\"))
    print('New subscription_tier cols:', [r[0] for r in result])
    result = conn.execute(text(\"SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name='tenant_messaging_registration'\"))
    print('New table exists:', [r[0] for r in result])
"

python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 2 — Add SQLModel Fields to `subscription_tier`

File: `backend/app/models/subscription.py`

Add 4 new fields to the `SubscriptionTier` model:

```python
free_period_days: int | None = Field(default=None, description="Days at $0 from activation. NULL = no free period.")
requires_payment_method: bool = Field(default=True, description="Whether the signup wizard collects a card.")
signup_cap: int | None = Field(default=None, description="Max tenants that may activate on this tier. NULL = uncapped.")
price_locked: bool = Field(default=False, description="Excludes this tier from future price-migration jobs.")
```

Read the file first. Adjust field names, types, and defaults to match the existing model patterns.

---

## Task 3 — Add SQLModel Fields to `tenant`

File: `backend/app/models/tenant.py`

Add 3 new fields to the `Tenant` model:

```python
free_period_ends_at: datetime | None = Field(default=None, description="App source of truth for free period end. Stripe trial_end mirrors this.")
charter_member_number: int | None = Field(default=None, description="1..12, NULL for non-Charter tenants.")
charter_eligible: bool = Field(default=True, description="Flips false permanently on cancellation or Teams upgrade.")
```

**Note**: `trial_ends_at` already exists on `tenant` — it tracks the 14-day Trial tier period. `free_period_ends_at` is a different concept (90-day Charter free period). Do NOT conflate them.

---

## Task 4 — Add SQLModel Field to `tenant_tier_override`

Find the `TenantTierOverride` model (use the grep command from Pre-Work). Add:

```python
override_free_period_ends_at: datetime | None = Field(default=None, description="Operator-set free period extension (case by case; not an advertised offer).")
```

---

## Task 5 — Create `TenantMessagingRegistration` SQLModel

Create a new model class. Check existing model files to determine the right location (likely `backend/app/models/messaging.py` or a new file in the appropriate domain).

```python
from app.models.mixins import StandardAuditMixin

class TenantMessagingRegistration(StandardAuditMixin, table=True):
    __tablename__ = "tenant_messaging_registration"
    id: uuid.UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenant.id", nullable=False)
    entity_type: str = Field(nullable=False)  # 'sole_proprietor' | 'standard'
    status: str = Field(nullable=False)  # see state machine, spec §5.2
    telnyx_brand_id: str | None = Field(default=None)
    telnyx_campaign_id: str | None = Field(default=None)
    telnyx_phone_number: str | None = Field(default=None)
    quoted_setup_cents: int | None = Field(default=None)
    quoted_monthly_cents: int | None = Field(default=None)
    stripe_checkout_id: str | None = Field(default=None)
    stripe_payment_intent: str | None = Field(default=None)
    otp_requested_at: datetime | None = Field(default=None)
    otp_verified_at: datetime | None = Field(default=None)
    failure_reason: str | None = Field(default=None)
```

**The `StandardAuditMixin` provides `created_at`, `updated_at`, `created_by`, `updated_by` automatically** — do not hand-declare them in the model class. The migration DDL must include all four (Task 1 already does).

**Intermediate verification:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 6 — Update Pydantic Response Schema

File: `backend/api/schemas/subscription.py`

Add the 4 new fields to `SubscriptionTierResponse`:

```python
free_period_days: int | None
requires_payment_method: bool
signup_cap: int | None
price_locked: bool
```

This makes the new fields available in the `GET /api/v1/subscription-tiers` response. The frontend will consume them in C-B5 (wizard conditional logic).

---

## Task 7 — Update Seed Script

File: `backend/migrations/scripts/seed_platform.py`

Add the 4 new columns to the tier seed dict:

```python
{
    "tier_name": "charter",
    "display_label": "Charter",
    "annual_price_cents": 58800,   # $588/yr (= $49/mo × 12)
    "monthly_price_cents": 4900,   # $49/mo flat (annual rate billed monthly)
    "is_trial": False,
    "trial_duration_days": None,
    "is_active": True,
    "display_order": 0,
    "schedule_lanes": 5,
    "product_plan_code": "charter_plan",
    "stripe_price_id_monthly": None,
    "stripe_price_id_annual": None,
    # NEW C-B2 FIELDS:
    "free_period_days": 90,
    "requires_payment_method": False,
    "signup_cap": 12,
    "price_locked": True,
},
```

Update all 4 tier rows with the new fields per design doc §B.1 Part 5.

---

## Task 8 — Run Migration + Reseed + Tests

```bash
cd <repo>/backend
source .venv/bin/activate

# Run migration
alembic upgrade head

# Reseed platform data
python -m migrations.scripts.seed_platform --mode reset

# Verify tier data
python -c "
from sqlalchemy import create_engine, text
import os
engine = create_engine(os.environ['DATABASE_URL'])
with engine.connect() as conn:
    result = conn.execute(text('SELECT tier_name, monthly_price_cents, annual_price_cents, free_period_days, requires_payment_method, signup_cap, price_locked FROM subscription_tier ORDER BY display_order'))
    for row in result:
        print(row)
"

# Run unit tests
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

**Expected tier data after reseed:**
- `charter`: $49/mo, $588 annual, 90 days, false, 12, true
- `trial`: $0, $0, 14 days, false, NULL, false
- `starter`: $59/mo, $588 annual, NULL, true, NULL, false
- `teams`: $179/mo, $1788 annual, NULL, true, NULL, false

---

## Task 9 — Regenerate `db_models_map.md`

```bash
cd <repo>/backend && source .venv/bin/activate
python generate_db_model_map.py app > db_models_map.md
```

Verify the new model appears:
```bash
grep "TenantMessagingRegistration" backend/db_models_map.md
```

---

## Task 10 — Update JSON Schema

Use `schema_manager.py` (path-based CRUD — never edit JSON directly):

```bash
cd <repo>/backend

# Add the 4 new columns to subscription_tier
python schema_manager.py set --path tables.subscription_tier.columns.free_period_days --value '{"type":"integer","nullable":true,"description":"Days at $0 from activation. NULL = no free period."}'
python schema_manager.py set --path tables.subscription_tier.columns.requires_payment_method --value '{"type":"boolean","nullable":false,"default":true,"description":"Whether the signup wizard collects a card."}'
python schema_manager.py set --path tables.subscription_tier.columns.signup_cap --value '{"type":"integer","nullable":true,"description":"Max tenants that may activate on this tier. NULL = uncapped."}'
python schema_manager.py set --path tables.subscription_tier.columns.price_locked --value '{"type":"boolean","nullable":false,"default":false,"description":"Excludes this tier from future price-migration jobs."}'

# Add the 3 new columns to tenant
python schema_manager.py set --path tables.tenant.columns.free_period_ends_at --value '{"type":"timestamp with time zone","nullable":true,"description":"App source of truth for free period end."}'
python schema_manager.py set --path tables.tenant.columns.charter_member_number --value '{"type":"integer","nullable":true,"description":"1..12, NULL for non-Charter tenants."}'
python schema_manager.py set --path tables.tenant.columns.charter_eligible --value '{"type":"boolean","nullable":false,"default":true,"description":"Flips false permanently on cancellation or Teams upgrade."}'

# Add the 1 new column to tenant_tier_override
python schema_manager.py set --path tables.tenant_tier_override.columns.override_free_period_ends_at --value '{"type":"timestamp with time zone","nullable":true,"description":"Operator-set free period extension."}'

# Add the new table (use a temp payload file for the full table definition)
# See schema_manager.py README for the array-append pattern for a new table
```

If `schema_manager.py` errors → STOP and ask Tom. Never edit the JSON with `sed`/`awk`/inline Python.

---

## Task 11 — Regenerate OpenAPI

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
```

Verify the new fields appear in the schema:
```bash
grep -A 2 "free_period_days\|requires_payment_method\|signup_cap\|price_locked" backend/openapi_schema_map.md
```

---

## Task 12 — Update `README-seed-data.md`

File: `backend/README-seed-data.md`

Update the `subscription_tier` table description in §8 to include the 4 new columns and the updated Charter pricing ($49/mo, 90-day free, cap 12, price locked).

Add the `tenant_messaging_registration` table to the table inventory if there's a section for new tables.

---

## Seed Data Rollout (Core + Scenario)

Per `backend/README-seed-data.md` — read §3 (Group A–D model), §6 (run order), and §7 (DELETE safety rule) before editing any seed script.

### Layer 1 — Core / Platform values (Group A / B)

The Alembic migration (Task 1) updates the tier rows in-place via UPDATE. The seed script `seed_platform.py` (Task 7) must produce **identical rows** with the new columns so that a post-schema-restore reseed is consistent.

After the migration + seed script update, verify:
```bash
python -m migrations.scripts.seed_platform --mode inspect
```

### Layer 2 — Scenario data (Group D)

`seed_test_tenant.py` does not need changes — it looks up the tier by name (`charter`), and the new columns have defaults that apply automatically. No scenario data references the new columns yet (they'll be populated by application logic in C-B4+).

### Verification

After seeding:
```bash
python -m migrations.scripts.seed_platform --mode inspect
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

### README update

Task 12 covers the README-seed-data.md update.

---

## Final Verification

### Phase 1 — Unit Tests Only (run after each task group during development)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before moving to Phase 2.

### Phase 2 — Lint (changed files only) + Full Suite

```bash
cd <repo>/backend
source .venv/bin/activate

# Lint + format gate — CHANGED FILES ONLY
CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py')
if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY
    ruff format $CHANGED_PY
    ruff check $CHANGED_PY
fi

# Full suite including integration tests
python -m pytest --tb=short -q 2>&1 | tail -10

# Batch-specific spot checks
python -m pytest tests/domains/subscriptions_usage/ -v 2>&1 | tail -20

# Verify the API returns the new fields
python -c "
from fastapi.testclient import TestClient
from main import app
client = TestClient(app)
resp = client.get('/api/v1/subscription-tiers/test')
data = resp.json()
for tier in data.get('tiers', []):
    print(f\"{tier['tier_name']}: free_period_days={tier.get('free_period_days')}, requires_payment_method={tier.get('requires_payment_method')}, signup_cap={tier.get('signup_cap')}, price_locked={tier.get('price_locked')}\")
"

echo "=== C-B2 FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done

Update `pilot-launch-plan.md` §2.0 row 14g status when complete:

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work
- [ ] All MCP pre-work queries run — 4 new cols confirmed absent, new table confirmed absent, audit columns confirmed on existing tables
- [ ] All mandatory source files read before writing any code (including `mixins.py` for StandardAuditMixin)
- [ ] Alembic migration created — DDL (4+3+1 cols + 1 table) + data UPDATE (tier pricing); `downgrade()` implemented; full cycle tested
- [ ] `tenant_messaging_registration` DDL includes **all four** audit columns (`created_at`, `updated_at`, `created_by`, `updated_by`) — Rule 15
- [ ] `SubscriptionTier` model — 4 new fields added
- [ ] `Tenant` model — 3 new fields added
- [ ] `TenantTierOverride` model — 1 new field added
- [ ] `TenantMessagingRegistration` model created with `StandardAuditMixin`
- [ ] `SubscriptionTierResponse` Pydantic schema — 4 new fields added
- [ ] `seed_platform.py` — tier seed dict updated with new columns + Charter pricing ($49/mo)
- [ ] Migration + reseed successful — tier data verified (charter: $49/mo, 90 days, cap 12, locked)
- [ ] `db_models_map.md` regenerated — `TenantMessagingRegistration` appears
- [ ] `pilot-db-schema-v2.6h.json` updated via `schema_manager.py`
- [ ] `openapi.json` + `openapi_schema_map.md` regenerated — new fields in `SubscriptionTierResponse`
- [ ] `README-seed-data.md` updated with new columns + new table
- [ ] `ruff check --fix && ruff format` run on changed files only — zero remaining issues
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures
- [ ] `GET /api/v1/subscription-tiers/test` returns the 4 new fields in the response
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to launch plan

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** subsection to `pilot-launch-plan.md` Appendix B using the format below.
2. Update `pilot-launch-plan.md` §2.0 row 14g status to `✅ COMPLETE`.
3. Update `backend/README-seed-data.md` §8 with the new columns.

```markdown
### C-B2 — Charter Entitlement Schema: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- Alembic migration: 4 new `subscription_tier` cols + 3 new `tenant` cols + 1 `tenant_tier_override` col + new `tenant_messaging_registration` table (18 cols incl. 4 audit)
- Tier seed data updated: Charter → $49/mo, 90-day free, cap 12, price locked; Trial → 14-day, no card; Starter/Teams → card required
- SQLModel: 8 new fields across 3 models + 1 new model class (`TenantMessagingRegistration`)
- Pydantic: `SubscriptionTierResponse` includes 4 new fields
- JSON schema + OpenAPI + db_models_map + README all regenerated

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/migrations/versions/2026_08_04_XXXX-XXXX_c_b2_charter_schema.py` | Created — DDL + data UPDATE migration |
| `backend/app/models/subscription.py` | Updated — 4 new fields on SubscriptionTier |
| `backend/app/models/tenant.py` | Updated — 3 new fields on Tenant |
| `backend/app/models/[domain].py` | Updated — 1 new field on TenantTierOverride + new TenantMessagingRegistration model |
| `backend/api/schemas/subscription.py` | Updated — 4 new fields on SubscriptionTierResponse |
| `backend/migrations/scripts/seed_platform.py` | Updated — tier seed dict with new columns + Charter pricing |
| `backend/README-seed-data.md` | Updated — new columns + new table |
| `backend/db_models_map.md` | Regenerated |
| `dev-docs/db-design/pilot-db-schema-v2.6h.json` | Updated via schema_manager.py |
| `backend/openapi.json` + `backend/openapi_schema_map.md` | Regenerated |
```

---

## Handoff Instructions

After C-B2 is complete and committed:

1. Run `python export_openapi_json.py` — verify the new fields appear in the OpenAPI spec.
2. Commit all changes with message: `C-B2: Charter entitlement schema — 4+3+1 new cols + tenant_messaging_registration table + tier seed update`
3. Notify that C-B3 (Stripe bootstrap) can begin — it depends on C-B2 ✅.
4. `pnpm sync-api-types` should be run by the next React Engineer who touches subscription-related code, so the frontend types include the new fields.
