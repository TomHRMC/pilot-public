# Implementation Prompt: MKT-B11-BE — Pricing Model v3.0 DB Migration (Schedule Lanes)

**Mode**: Pilot Python Engineer  
**Batch**: MKT-B11-BE  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §MKT-B11  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-mkt-b11-db-design.md`  
**Estimated session**: 3–4 hours  
**Platform**: Backend only (`backend/`)  
**Frontend companion**: MKT-B11-MKT (marketing pricing page), MKT-B11-DISPATCH (dispatch board redesign) — both depend on this batch closing first

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, and fixture rules
- **`dev-docs/architecture-design/batch-designs/batch-mkt-b11-db-design.md`** — **all sections A–G + Appendix** — this is the authoritative spec for every SQL statement in this batch

**Critical rules for this batch:**

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 4**: All Alembic migrations must be written as **blank** migrations — never `--autogenerate`. Data changes use raw `op.execute()` with `SET LOCAL session_replication_role = 'replica';`.
- **Rule 4b**: Always implement `downgrade()` — never leave it empty. The downgrade for this batch is complex (re-insert deleted rows); document the exact reverse in a comment block.
- **Rule 7**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE data.
- **Rule 10**: `require_permission("resource.action")` uses `feature_code` for tier-gated endpoints. After this batch, valid feature codes are: `schedule_lanes`, `voice_ai_minutes`, `outbound_sms_segments`. The old codes `dispatch_slots` and `data_exports` are deleted — any code referencing them must be updated.
- **Rule 11**: If ANY test fails during your work — even one that appears pre-existing — **fix it before declaring the batch done**. No exceptions without explicit written confirmation from Tom.
- **Schema JSON rule**: After all migrations run and all tests pass, run `python schema_manager.py set` for every modified table and commit the updated `dev-docs/db-design/pilot-db-schema-v2.6h.json`. This is required — the same standard as running tests.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed anyway. Either confirm with Tom that the failure is known and accepted, or fix it before starting batch work. You may NOT start implementation work while tests are in an unexplained failed state.

---

## Pre-Work: Run MCP Verification Queries

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE. If a query fails or returns an error → STOP and ask Tom before proceeding.

Run **all** of these via `postgres-local` MCP before writing any code:

```sql
-- 1. Verify subscription_tier current columns (confirm max_users + max_sms_segments_per_month exist; schedule_lanes does NOT exist yet)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription_tier'
ORDER BY ordinal_position;

-- 2. Verify current subscription_tier rows (should show 4 stale rows: trial/starter/professional/enterprise)
SELECT tier_name, display_label, monthly_price_cents, is_trial, is_active, product_plan_code
FROM public.subscription_tier ORDER BY display_order;

-- 3. Verify current product_plan rows (should show starter_plan/teams/enterprise_plan; no founders_plan)
SELECT code, name, is_active FROM public.product_plan ORDER BY created_at;

-- 4. Verify current product_feature rows (should include dispatch_slots and data_exports to be deleted)
SELECT code, name, unit, is_active FROM public.product_feature ORDER BY code;

-- 5. Verify current ppfv rows (should show 12 stale open rows)
SELECT product_plan_code, product_feature_code, limit_quantity, included_quantity,
       overage_price_cents, limit_enforcement
FROM public.product_plan_product_feature_version
ORDER BY product_plan_code, product_feature_code;

-- 6. Verify GiST constraint name (needed for downgrade)
SELECT conname FROM pg_constraint
WHERE conrelid = 'public.product_plan_product_feature_version'::regclass AND contype = 'x';

-- 7. Verify pppfv_no_overlap constraint columns
SELECT conname, pg_get_constraintdef(oid) AS constraint_def
FROM pg_constraint
WHERE conrelid = 'public.product_plan_product_feature_version'::regclass AND contype = 'x';

-- 8. Verify current alembic head
SELECT version_num FROM public.alembic_version;
```

If **any** of these results differ from what the design doc describes → **STOP and ask Tom** before proceeding. The design doc was authored from a specific DB state; if the DB has changed, the migration SQL may need adjustment.

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/app/models/subscription.py             ← SubscriptionTier, TenantTierOverride, TenantSubscriptionUsage models
backend/app/models/billing.py                  ← ProductPlan, ProductFeature, ProductPlanProductFeatureVersion, ProductPlanVersion models
backend/services/tier_limit_enforcer.py        ← contains dispatch_slots references to replace with schedule_lanes
backend/services/entitlement_service.py        ← contains feature code references to update
backend/migrations/scripts/seed_platform.py   ← PRODUCT_PLANS, TIER_TO_PLAN_MAP, PLAN_FEATURE_LIMITS to rewrite
backend/migrations/scripts/seed_test_tenant.py ← subscription seeding logic to update
backend/api/routes/subscription_tiers.py       ← GET /api/v1/subscription-tiers endpoint + SubscriptionTierResponse schema
backend/db_models_map.md                       ← confirm model names and table mappings
```

Also grep for every occurrence of the deleted feature codes:

```bash
grep -rn "dispatch_slots" backend/app backend/services backend/api backend/tasks --include="*.py"
grep -rn "data_exports" backend/app backend/services backend/api backend/tasks --include="*.py"
grep -rn "max_users\|max_sms_segments_per_month" backend/app backend/services backend/api --include="*.py"
```

Record every file returned. Every occurrence must be updated.

---

## Background / Context

This batch implements the Pricing Model v3.0 DB migration. The old model (Starter/Professional/Enterprise with dispatch_slots, user-count gating) is being replaced by a new model (Founders/Trial/Starter/Teams with schedule_lanes, unlimited users).

**The authoritative spec for all SQL in this batch is the approved design doc**: `batch-mkt-b11-db-design.md`. Read sections B.3 (migration steps), B.4 (target state), F (module interfaces), and G (open questions resolved) before implementing.

**Key business logic from the design doc:**
- `founders` tier: is_active=true, monthly_price_cents=0, schedule_lanes=5 — this is the only tier customers see during the Founders cohort period
- `trial`, `starter`, `teams` tiers: is_active=false — Tom will flip these when general release begins
- `enterprise` tier: deleted entirely — no row inserted
- `dispatch_slots` feature code: deleted — replaced by `schedule_lanes`
- `data_exports` feature code: deleted — data exports are unlimited and untracked
- `max_users` and `max_sms_segments_per_month` columns on `subscription_tier`: dropped — unlimited users is a permanent invariant; SMS limits live in ppfv

---

## Task 1 — Alembic Migration: Rebuild Subscription + Product Plan Tables

**File to create**: `backend/migrations/versions/YYYY_MM_DD_HHMM-<autoid>_mkt_b11_pricing_model_v3.py`

Create a **blank** migration (never `--autogenerate`):
```bash
cd backend && alembic revision -m "mkt_b11_pricing_model_v3_schedule_lanes"
```

Implement `upgrade()` following **exactly** the 7-step sequence from `batch-mkt-b11-db-design.md §B.3`:

```python
def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # STEP 1: Delete all ppfv and ppv stale rows (clear FK dependencies first)
    op.execute("DELETE FROM public.product_plan_product_feature_version;")
    op.execute("DELETE FROM public.product_plan_version;")

    # STEP 2: Delete stale feature rows; insert schedule_lanes
    op.execute("DELETE FROM public.product_feature WHERE code IN ('dispatch_slots', 'data_exports');")
    op.execute("""
        INSERT INTO public.product_feature
        (code, name, unit, description, is_active, created_at, updated_at)
        VALUES
        ('schedule_lanes', 'Schedule Lanes', 'lanes',
         'Concurrent job slots on the dispatch board. One lane = one parallel scheduling row. Any user can be assigned to jobs in any lane.',
         true, NOW(), NOW())
        ON CONFLICT (code) DO NOTHING;
    """)

    # STEP 3: Rebuild product_plan (add founders_plan; set inactive; delete enterprise_plan)
    op.execute("""
        INSERT INTO public.product_plan
        (code, name, description, is_active, created_at, updated_at)
        VALUES
        ('founders_plan', 'Founders Plan',
         'Time-limited founding member cohort plan. 6 months free, then $49/mo locked at Starter limits for life.',
         true, NOW(), NOW())
        ON CONFLICT (code) DO NOTHING;
    """)
    op.execute("UPDATE public.product_plan SET is_active = false, updated_at = NOW() WHERE code IN ('starter_plan', 'teams');")
    op.execute("DELETE FROM public.product_plan WHERE code = 'enterprise_plan';")

    # STEP 4: Rebuild subscription_tier (delete all; drop old columns; add schedule_lanes; insert 4 correct rows)
    op.execute("DELETE FROM public.subscription_tier;")
    op.execute("ALTER TABLE public.subscription_tier DROP COLUMN IF EXISTS max_users;")
    op.execute("ALTER TABLE public.subscription_tier DROP COLUMN IF EXISTS max_sms_segments_per_month;")
    op.execute("ALTER TABLE public.subscription_tier ADD COLUMN IF NOT EXISTS schedule_lanes INTEGER NOT NULL DEFAULT 0;")
    op.execute("""
        INSERT INTO public.subscription_tier
        (tier_id, tier_name, display_label, monthly_price_cents, is_trial,
         trial_duration_days, is_active, display_order, schedule_lanes,
         product_plan_code, created_at, updated_at)
        VALUES
        (gen_random_uuid(), 'founders', 'Founders', 0, false,
         NULL, true, 0, 5, 'founders_plan', NOW(), NOW()),
        (gen_random_uuid(), 'trial', 'Trial', 0, true,
         14, false, 1, 5, 'starter_plan', NOW(), NOW()),
        (gen_random_uuid(), 'starter', 'Starter', 4900, false,
         NULL, false, 2, 5, 'starter_plan', NOW(), NOW()),
        (gen_random_uuid(), 'teams', 'Teams', 14900, false,
         NULL, false, 3, 20, 'teams', NOW(), NOW());
    """)

    # STEP 5: Insert 9 correct ppfv rows (founders_plan × 3, starter_plan × 3, teams × 3)
    op.execute("""
        INSERT INTO public.product_plan_product_feature_version
        (product_plan_code, product_feature_code, limit_quantity, included_quantity,
         overage_price_cents, limit_enforcement, valid_period, recorded_at, created_at)
        VALUES
        ('founders_plan', 'schedule_lanes', 5, 5, NULL, 'block', tstzrange(NOW(), NULL), NOW(), NOW()),
        ('founders_plan', 'voice_ai_minutes', 90, 90, 5, 'soft', tstzrange(NOW(), NULL), NOW(), NOW()),
        ('founders_plan', 'outbound_sms_segments', 100, 100, 5, 'soft', tstzrange(NOW(), NULL), NOW(), NOW()),
        ('starter_plan', 'schedule_lanes', 5, 5, NULL, 'block', tstzrange(NOW(), NULL), NOW(), NOW()),
        ('starter_plan', 'voice_ai_minutes', 90, 90, 5, 'soft', tstzrange(NOW(), NULL), NOW(), NOW()),
        ('starter_plan', 'outbound_sms_segments', 100, 100, 5, 'soft', tstzrange(NOW(), NULL), NOW(), NOW()),
        ('teams', 'schedule_lanes', 20, 20, NULL, 'block', tstzrange(NOW(), NULL), NOW(), NOW()),
        ('teams', 'voice_ai_minutes', 300, 300, 5, 'soft', tstzrange(NOW(), NULL), NOW(), NOW()),
        ('teams', 'outbound_sms_segments', 500, 500, 5, 'soft', tstzrange(NOW(), NULL), NOW(), NOW());
    """)

    # STEP 6: Insert 3 correct ppv rows
    op.execute("""
        INSERT INTO public.product_plan_version
        (product_plan_code, name, price_cents, valid_period, recorded_at, created_at)
        VALUES
        ('founders_plan', 'Founders Plan', 4900, tstzrange(NOW(), NULL), NOW(), NOW()),
        ('starter_plan', 'Starter Plan', 4900, tstzrange(NOW(), NULL), NOW(), NOW()),
        ('teams', 'Teams Plan', 14900, tstzrange(NOW(), NULL), NOW(), NOW());
    """)
```

**`downgrade()`**: The downgrade must re-insert the old stale data and restore the dropped columns. Since this is a dev DB with no real tenant data, a simplified downgrade is acceptable — add the columns back with NULL, drop `schedule_lanes`, and re-insert the old 4 tier rows with placeholder values. Document clearly in a comment block that this downgrade is not production-safe:

```python
def downgrade() -> None:
    # DEV DB ONLY — not production-safe. Restores pre-v3.0 schema skeleton.
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.execute("DELETE FROM public.product_plan_product_feature_version;")
    op.execute("DELETE FROM public.product_plan_version;")
    op.execute("DELETE FROM public.subscription_tier;")
    op.execute("ALTER TABLE public.subscription_tier DROP COLUMN IF EXISTS schedule_lanes;")
    op.execute("ALTER TABLE public.subscription_tier ADD COLUMN IF NOT EXISTS max_users INTEGER;")
    op.execute("ALTER TABLE public.subscription_tier ADD COLUMN IF NOT EXISTS max_sms_segments_per_month INTEGER;")
    op.execute("DELETE FROM public.product_feature WHERE code = 'schedule_lanes';")
    # Note: dispatch_slots and data_exports not re-inserted; product_plan rows not restored.
    # Full downgrade requires a DB restore from backup.
```

**Test the migration cycle after implementing:**
```bash
cd backend && source .venv/bin/activate
alembic upgrade head
alembic downgrade -1
alembic upgrade head
alembic current   # must show new head revision
```

**Intermediate unit test run after migration works:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```
Fix any failures before proceeding to Task 2.

---

## Task 2 — Update SQLModel: SubscriptionTier Model

**File**: `backend/app/models/subscription.py`

Update the `SubscriptionTier` SQLModel class:
- **Remove** `max_users` field
- **Remove** `max_sms_segments_per_month` field  
- **Add** `schedule_lanes: int = Field(nullable=False)` field

After editing, regenerate the DB model map:
```bash
python generate_db_model_map.py
grep "SubscriptionTier" backend/db_models_map.md
```

**Intermediate unit test run:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 3 — Update SubscriptionTierResponse Schema

**File**: `backend/api/routes/subscription_tiers.py` (or wherever `SubscriptionTierResponse` is defined — verify with `grep -rn "SubscriptionTierResponse" backend/ --include="*.py"`)

Update the `SubscriptionTierResponse` Pydantic schema:
- **Remove** `max_users` field
- **Remove** `max_sms_segments_per_month` field
- **Add** `schedule_lanes: int` field

Verify the `GET /api/v1/subscription-tiers` endpoint returns the new field structure. After updating, run:
```bash
python export_openapi_json.py
grep -A 10 "SubscriptionTierResponse" backend/openapi_schema_map.md
```

**Intermediate unit test run:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 4 — Application Code Cleanup: Replace Feature Code References

Search for and update every occurrence of the deleted feature codes in all application code:

```bash
# Step 4a: Find all dispatch_slots references
grep -rn "dispatch_slots" backend/app backend/services backend/api backend/tasks --include="*.py"

# Step 4b: Find all data_exports entitlement references
grep -rn "data_exports" backend/app backend/services backend/api backend/tasks --include="*.py"

# Step 4c: Find all max_users / max_sms_segments references
grep -rn "max_users\|max_sms_segments_per_month" backend/app backend/services backend/api --include="*.py"
```

For each occurrence:
- `dispatch_slots` → replace with `schedule_lanes`
- `data_exports` entitlement checks → remove entirely (data exports are now unlimited and untracked; no enforcement needed)
- `max_users` references → remove (unlimited users; no enforcement)
- `max_sms_segments_per_month` references → remove (SMS limits now live entirely in ppfv)

Pay special attention to:
- **`backend/services/tier_limit_enforcer.py`** — likely references both `dispatch_slots` and `max_users`
- **`backend/services/entitlement_service.py`** — may reference `data_exports` entitlement checks
- Any Celery tasks that write to `usage_ledger` with `product_feature_code='data_exports'` or `'dispatch_slots'` → update to `'schedule_lanes'` or remove if `data_exports`

**Also implement** the new `get_effective_schedule_lanes()` helper per design doc §F.2:

```python
# In backend/services/tier_limit_enforcer.py or backend/services/entitlement_service.py
def get_effective_schedule_lanes(tenant_id: UUID, db: Session) -> int:
    """
    Returns effective lane count for tenant:
      1. Check tenant_product_feature_override for 'schedule_lanes' (add-ons)
      2. Fall back to active plan's ppfv limit_quantity
    Raises ValueError if no lane config found (misconfigured plan).
    """
    from sqlmodel import select
    from app.models.billing import ProductPlanProductFeatureVersion, Subscription
    from app.models.subscription import TenantTierOverride

    # Priority 1: tenant-specific override (purchased add-on lanes)
    override = db.exec(
        select(TenantProductFeatureOverride).where(
            TenantProductFeatureOverride.tenant_id == tenant_id,
            TenantProductFeatureOverride.product_feature_code == "schedule_lanes",
            TenantProductFeatureOverride.enabled == True,
        )
    ).first()
    if override:
        return override.limit_quantity

    # Priority 2: plan ppfv limit
    result = db.exec(
        select(ProductPlanProductFeatureVersion.limit_quantity)
        .join(Subscription, Subscription.product_plan_code == ProductPlanProductFeatureVersion.product_plan_code)
        .where(
            Subscription.tenant_id == tenant_id,
            Subscription.is_active == True,
            ProductPlanProductFeatureVersion.product_feature_code == "schedule_lanes",
        )
    ).first()
    if result is None:
        raise ValueError(f"No schedule_lanes configuration found for tenant {tenant_id}")
    return result
```

**Intermediate unit test run:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 5 — Update Seed Scripts

### 5a — `seed_platform.py`

**File**: `backend/migrations/scripts/seed_platform.py`

Rewrite `PRODUCT_PLANS`, `TIER_TO_PLAN_MAP`, and `PLAN_FEATURE_LIMITS` per design doc §F.3:

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

Also update `mode_seed()` to handle the new `enforcement` and `overage_cents` keys per feature dict (not a flat int). Also update `mode_inspect()` and `mode_show()` to reflect the new feature set.

### 5b — `seed_test_tenant.py`

**File**: `backend/migrations/scripts/seed_test_tenant.py`

Update the subscription seeding section to explicitly use `founders_plan` per design doc §F.4. Replace any "first active plan alphabetically" or `starter_plan` reference with an explicit `founders_plan` lookup:

```python
# Use founders_plan explicitly
plan_row = db.execute(
    text("SELECT code FROM public.product_plan WHERE code = 'founders_plan' LIMIT 1")
).first()
```

Also update the `subscription_tier` seed lookup — it should now find the `founders` tier (not `trial` or `starter`):

```python
# Use founders tier explicitly (not is_trial=true anymore, since founders is is_trial=false)
tier_row = db.execute(
    text("SELECT tier_id FROM public.subscription_tier WHERE tier_name = 'founders' LIMIT 1")
).first()
```

**Intermediate unit test run:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 6 — Update JSON Schema File

After all migrations have run and all tests pass, update the master JSON schema file for every modified table:

```bash
cd <repo>/backend

python schema_manager.py set subscription_tier
python schema_manager.py set product_plan
python schema_manager.py set product_feature
python schema_manager.py set product_plan_product_feature_version
python schema_manager.py set product_plan_version
python schema_manager.py set tenant_product_feature_override
```

Verify the output for each table shows the correct column list (no `max_users`, no `max_sms_segments_per_month`, `schedule_lanes` present on `subscription_tier`; `dispatch_slots` and `data_exports` absent from `product_feature`).

**If `schema_manager.py` fails** → STOP immediately and ask Tom. Do NOT manually edit the JSON file.

Commit the updated `dev-docs/db-design/pilot-db-schema-v2.6h.json`.

---

## Task 7 — Write Tests

**Test file**: `backend/tests/domains/subscriptions_usage/test_mkt_b11_pricing_v3.py`

```python
pytestmark = [
    pytest.mark.domain_subscriptions_usage,
    pytest.mark.unit,
]
```

Required tests:

```python
class TestSubscriptionTierV3:
    """Verifies subscription_tier table reflects v3.0 schema and data."""

    def test_founders_tier_is_only_active_tier(self, client, test_tenant):
        """GET /subscription-tiers?active_only=true returns only founders tier."""
        resp = client.get("/api/v1/subscription-tiers/test?active_only=true")
        assert resp.status_code == 200
        tiers = resp.json()
        assert len(tiers) == 1
        assert tiers[0]["tier_name"] == "founders"

    def test_founders_tier_has_schedule_lanes(self, client, test_tenant):
        """founders tier response includes schedule_lanes=5."""
        resp = client.get("/api/v1/subscription-tiers/test")
        assert resp.status_code == 200
        founders = next(t for t in resp.json() if t["tier_name"] == "founders")
        assert founders["schedule_lanes"] == 5

    def test_no_max_users_in_response(self, client, test_tenant):
        """SubscriptionTierResponse does not expose max_users (column dropped)."""
        resp = client.get("/api/v1/subscription-tiers/test")
        for tier in resp.json():
            assert "max_users" not in tier
            assert "max_sms_segments_per_month" not in tier

    def test_teams_tier_has_20_schedule_lanes(self, client, test_tenant):
        """teams tier has schedule_lanes=20."""
        resp = client.get("/api/v1/subscription-tiers/test")
        teams = next((t for t in resp.json() if t["tier_name"] == "teams"), None)
        assert teams is not None
        assert teams["schedule_lanes"] == 20

    def test_enterprise_tier_absent(self, client, test_tenant):
        """enterprise tier is not present (deleted in v3.0)."""
        resp = client.get("/api/v1/subscription-tiers/test")
        tier_names = [t["tier_name"] for t in resp.json()]
        assert "enterprise" not in tier_names


class TestProductPlanV3:
    """Verifies product_plan table reflects v3.0 data."""

    def test_founders_plan_is_active(self, db_session):
        """founders_plan is the only active product_plan."""
        from app.models.billing import ProductPlan
        from sqlmodel import select
        active = db_session.exec(
            select(ProductPlan).where(ProductPlan.is_active == True)
        ).all()
        assert len(active) == 1
        assert active[0].code == "founders_plan"

    def test_enterprise_plan_deleted(self, db_session):
        """enterprise_plan row does not exist."""
        from app.models.billing import ProductPlan
        from sqlmodel import select
        enterprise = db_session.exec(
            select(ProductPlan).where(ProductPlan.code == "enterprise_plan")
        ).first()
        assert enterprise is None


class TestProductFeatureV3:
    """Verifies product_feature table reflects v3.0 data."""

    def test_schedule_lanes_feature_exists(self, db_session):
        """schedule_lanes product_feature is present and active."""
        from app.models.billing import ProductFeature
        from sqlmodel import select
        feat = db_session.exec(
            select(ProductFeature).where(ProductFeature.code == "schedule_lanes")
        ).first()
        assert feat is not None
        assert feat.is_active is True

    def test_dispatch_slots_deleted(self, db_session):
        """dispatch_slots product_feature is gone."""
        from app.models.billing import ProductFeature
        from sqlmodel import select
        feat = db_session.exec(
            select(ProductFeature).where(ProductFeature.code == "dispatch_slots")
        ).first()
        assert feat is None

    def test_data_exports_deleted(self, db_session):
        """data_exports product_feature is gone."""
        from app.models.billing import ProductFeature
        from sqlmodel import select
        feat = db_session.exec(
            select(ProductFeature).where(ProductFeature.code == "data_exports")
        ).first()
        assert feat is None


class TestPPFVV3:
    """Verifies product_plan_product_feature_version rows are correct for v3.0."""

    def test_founders_plan_has_9_ppfv_rows(self, db_session):
        """3 plans × 3 features = 9 ppfv rows total."""
        from app.models.billing import ProductPlanProductFeatureVersion
        from sqlmodel import select, func
        count = db_session.exec(select(func.count(ProductPlanProductFeatureVersion.id))).one()
        assert count == 9

    def test_schedule_lanes_uses_block_enforcement(self, db_session):
        """All schedule_lanes ppfv rows use block enforcement (not soft)."""
        from app.models.billing import ProductPlanProductFeatureVersion
        from sqlmodel import select
        rows = db_session.exec(
            select(ProductPlanProductFeatureVersion).where(
                ProductPlanProductFeatureVersion.product_feature_code == "schedule_lanes"
            )
        ).all()
        assert len(rows) == 3  # founders, starter, teams
        for row in rows:
            assert row.limit_enforcement == "block"
            assert row.overage_price_cents is None

    def test_voice_ai_minutes_overage_is_5_cents(self, db_session):
        """All voice_ai_minutes ppfv rows have overage_price_cents=5."""
        from app.models.billing import ProductPlanProductFeatureVersion
        from sqlmodel import select
        rows = db_session.exec(
            select(ProductPlanProductFeatureVersion).where(
                ProductPlanProductFeatureVersion.product_feature_code == "voice_ai_minutes"
            )
        ).all()
        for row in rows:
            assert row.overage_price_cents == 5
            assert row.limit_enforcement == "soft"


class TestGetEffectiveScheduleLanes:
    """Verifies the get_effective_schedule_lanes() helper."""

    @pytest.mark.skip_mock_entitlement_allowed
    def test_returns_plan_base_lanes_when_no_override(self, db_session, test_tenant):
        """Returns 5 for founders plan when no tenant override."""
        from services.tier_limit_enforcer import get_effective_schedule_lanes
        lanes = get_effective_schedule_lanes(test_tenant.id, db_session)
        assert lanes == 5  # founders_plan base
```

> **Note on entitlement tests**: Tests in `TestGetEffectiveScheduleLanes` that exercise the lane enforcement must use `@pytest.mark.skip_mock_entitlement_allowed` so the autouse fixture doesn't bypass the check.

---

## Final Verification

### Phase 1 — Unit Tests Only (run after each task group)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before moving to the next task.

### Phase 2 — Full Suite (run once at the end, before DoD sign-off)

```bash
cd <repo>/backend
source .venv/bin/activate

# Full suite
python -m pytest --tb=short -q 2>&1 | tail -10

# Batch-specific spot check
python -m pytest tests/domains/subscriptions_usage/test_mkt_b11_pricing_v3.py -v 2>&1 | tail -30

# Verify endpoint returns schedule_lanes
grep -A 5 "schedule_lanes" backend/openapi_schema_map.md

echo "=== MKT-B11-BE FINAL VERIFICATION COMPLETE ==="
```

> **Any failure in either phase must be fixed before the batch is declared done.** No "pre-existing failure" exception without explicit written confirmation from Tom.

---

## Definition of Done

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work (or confirmed with Tom)
- [ ] All 8 MCP pre-work queries run — current DB state verified against design doc expectations
- [ ] All mandatory source files read before writing any code
- [ ] **Task 1**: Alembic migration created and tested (upgrade → downgrade → upgrade cycle passes)
- [ ] **Task 2**: `SubscriptionTier` SQLModel updated — `max_users`/`max_sms_segments_per_month` removed, `schedule_lanes` added
- [ ] **Task 3**: `SubscriptionTierResponse` Pydantic schema updated — `max_users`/`max_sms_segments_per_month` removed, `schedule_lanes` added
- [ ] **Task 4**: All `dispatch_slots` references in application code replaced with `schedule_lanes`
- [ ] **Task 4**: All `data_exports` entitlement checks removed from application code (data exports unlimited)
- [ ] **Task 4**: All `max_users`/`max_sms_segments_per_month` enforcement references removed
- [ ] **Task 4**: `get_effective_schedule_lanes()` helper implemented in entitlement/tier service
- [ ] **Task 5a**: `seed_platform.py` — `PRODUCT_PLANS`, `TIER_TO_PLAN_MAP`, `PLAN_FEATURE_LIMITS` rewritten for v3.0
- [ ] **Task 5b**: `seed_test_tenant.py` — subscription seeding updated to use `founders_plan` / `founders` tier explicitly
- [ ] **Task 6**: `python schema_manager.py set` run for all 6 modified tables — output verified
- [ ] **Task 6**: `dev-docs/db-design/pilot-db-schema-v2.6h.json` updated and committed
- [ ] `python export_openapi_json.py` run — `openapi.json` and `openapi_schema_map.md` updated
- [ ] `python generate_db_model_map.py` run — `db_models_map.md` updated
- [ ] All new test files use `pytestmark` with `domain_subscriptions_usage` + `pytest.mark.unit`
- [ ] No module-level `TestClient` in any test file
- [ ] Entitlement tests marked `@pytest.mark.skip_mock_entitlement_allowed` where needed
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures including integration tests
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `pilot-launch-plan.md` §MKT-B11

---

## Completion Summary

After all Definition of Done items are complete, add a Completion Summary subsection to `dev-docs/analysis/pilot-launch-plan.md` §MKT-B11 using this format:

```markdown
### MKT-B11-BE — Pricing Model v3.0 DB Migration: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- Alembic migration `<revision_id>`: deleted 12 stale ppfv rows; deleted 3 stale ppv rows; deleted dispatch_slots + data_exports features; inserted schedule_lanes feature; added founders_plan; set starter_plan/teams is_active=false; deleted enterprise_plan; dropped max_users + max_sms_segments_per_month columns from subscription_tier; added schedule_lanes column; inserted 4 correct tier rows (founders active, trial/starter/teams inactive); inserted 9 correct ppfv rows; inserted 3 correct ppv rows
- Updated SubscriptionTier SQLModel and SubscriptionTierResponse schema to replace old fields with schedule_lanes
- Updated all application code: dispatch_slots → schedule_lanes; data_exports entitlement checks removed; max_users/max_sms enforcement removed
- Implemented get_effective_schedule_lanes() helper
- Rewrote seed_platform.py and seed_test_tenant.py for v3.0 plan structure
- Updated pilot-db-schema-v2.6h.json via schema_manager.py for all 6 modified tables

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/migrations/versions/<id>_mkt_b11_pricing_model_v3_schedule_lanes.py` | Created — Alembic migration |
| `backend/app/models/subscription.py` | Updated — removed max_users/max_sms, added schedule_lanes |
| `backend/api/routes/subscription_tiers.py` | Updated — SubscriptionTierResponse schema |
| `backend/services/tier_limit_enforcer.py` | Updated — dispatch_slots → schedule_lanes; get_effective_schedule_lanes() added |
| `backend/services/entitlement_service.py` | Updated — data_exports checks removed |
| `backend/migrations/scripts/seed_platform.py` | Updated — PRODUCT_PLANS/TIER_TO_PLAN_MAP/PLAN_FEATURE_LIMITS rewritten |
| `backend/migrations/scripts/seed_test_tenant.py` | Updated — founders_plan/founders tier explicit reference |
| `backend/tests/domains/subscriptions_usage/test_mkt_b11_pricing_v3.py` | Created — N tests |
| `backend/openapi.json` | Regenerated |
| `backend/openapi_schema_map.md` | Regenerated |
| `backend/db_models_map.md` | Regenerated |
| `dev-docs/db-design/pilot-db-schema-v2.6h.json` | Updated via schema_manager.py |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/subscriptions_usage/test_mkt_b11_pricing_v3.py` | `domain_subscriptions_usage` | N | ✅ |
```

---

## After This Batch — Next Step

After this batch closes and `pnpm sync-api-types` has been run by the React Engineer:

1. **MKT-B11-MKT** (Marketing React Engineer) — pricing page redesign (Founders + dormant regular release)
2. **MKT-B11-DISPATCH** (Web React Engineer) — dispatch board schedule lane UI redesign

Both depend on this batch completing and OpenAPI being regenerated.
