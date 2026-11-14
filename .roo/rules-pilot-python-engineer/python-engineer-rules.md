# 🐍 Pilot Python Engineer — Hard Rules

> **Design-time agent rule** — written to steer the AI agents during the build and published as last used. Where it differs from the as-built system, [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../../dev-docs/diligence/README.md) are correct.

These are non-negotiable constraints. Every rule here was added because violating it caused real rework, data corruption, or security failures in prior development sessions. They are **not** guidelines. They are **stops**.

---

## 1. Source of Truth Files — Always Read Before Writing Code

### 1.1 DB Model Lookups — Use `db_models_map.md`

Before writing or modifying ANY model, route, or service that references a DB model:

1. **Read [`backend/db_models_map.md`](../../backend/db_models_map.md)** to find the exact file containing the class.
2. **Read [`backend/app_model_imports.md`](../../backend/app_model_imports.md)** to get the correct import path.
3. **DO NOT guess** which file a model is in. DO NOT assume a class name. Look it up.

### 1.2 Schema Verification — Use `postgres-local` MCP

Before writing any migration, query, or model field that references a column:

- **Query the live schema** via the `postgres-local` MCP server to confirm the exact column name, type, and nullability.
- If the MCP server returns an error: **STOP immediately and ask Tom**. Do NOT guess at the correct column name. Do NOT try alternative spellings. The MCP server works — the error means the query is wrong.
- **Two read-only MCP servers exist** (see global rule [`.roo/rules/02-database-mcp-access.md`](../../.roo/rules/02-database-mcp-access.md)): use **`postgres-local`** for all normal verification. **`postgres-prod`** reads production but **requires an SSH tunnel that only Tom controls** — ask Tom to confirm the tunnel is up before your first `postgres-prod` query, and STOP on any connection error (the tunnel is down). Only touch `postgres-prod` when the task is explicitly about production state; both servers are read-only (never INSERT/UPDATE/DELETE).

```sql
-- Always confirm column names before using them:
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'YOUR_TABLE_NAME'
ORDER BY ordinal_position;
```

### 1.3 API Endpoint Verification — Use `openapi.json` + `openapi_schema_map.md`

Before writing any route, confirm it does not already exist:

```bash
python3 -c "
import json
spec = json.load(open('openapi.json'))
matches = [p for p in spec['paths'] if 'YOUR_KEYWORD' in p]
print(matches)
"
```

Also check [`backend/openapi_schema_map.md`](../../backend/openapi_schema_map.md) for the human-readable summary of all existing endpoints, their parameters, and response shapes.

---

## 2. Mandatory Regeneration After Every Change

These files MUST be regenerated whenever their source changes. Stale files mislead agents and cause rework.

### 2.1 After ANY model file change (`app/models/*.py`):

```bash
cd backend && source .venv/bin/activate
python generate_db_model_map.py app > db_models_map.md
```

### 2.2 After ANY new test file is added:

```bash
cd backend && source .venv/bin/activate
python generate_app_import_map.py tests > app_model_imports.md
```

### 2.3 After ANY endpoint is added, modified, or deleted:

```bash
cd backend && source .venv/bin/activate
python export_openapi_json.py
```

`export_openapi_json.py` generates BOTH `openapi.json` (machine-readable) AND `openapi_schema_map.md` (human/agent-readable summary). **Both files are updated by the same script.** Run it after every API change.

**This is a Definition of Done requirement** — no task that touches models, routes, or tests is complete until the relevant generated files are current.

---

## 3. Schema Manager — Never Edit the Master JSON Directly

The master schema file (`pilot-db-schema-v2.6h.json`) MUST be modified ONLY via [`backend/schema_manager.py`](../../backend/schema_manager.py).

- **NEVER use `sed`, `awk`, inline Python scripts, or direct file editing** to mutate the schema JSON file.
- If `schema_manager.py` is not working: **STOP and ask Tom**. Explain the exact command and the exact error. Do NOT proceed with manual edits. Do NOT attempt workarounds.

This file has been corrupted by agents bypassing `schema_manager.py` in the past, requiring hours of manual repair.

```bash
# CORRECT: Use schema_manager.py for all schema changes
python schema_manager.py get --path tables.customer
python schema_manager.py set --path tables.customer.columns.new_col --payload temp.json
python schema_manager.py array-append --path tables.customer.indexes --payload temp.json
```

---

## 4. Multi-Tenancy — `db.get()` Is Permanently Banned

`db.get(Model, pk)` is **permanently banned** on any model that has a `tenant_id` column. No exceptions.

```python
# ❌ BANNED — even when you believe the FK is safe
customer = db.get(Customer, job.customer_id)

# ✅ REQUIRED — always include tenant_id filter
customer = db.exec(
    select(Customer)
    .where(Customer.id == job.customer_id)
    .where(Customer.tenant_id == current_user.tenant_id)
).first()
```

Return `404` (not `403`) for cross-tenant access attempts — this prevents UUID enumeration attacks.

---

## 5. Test Files — Module-Level `TestClient` Is Banned

**NEVER declare `client = TestClient(app)` at module level.** This bypasses the rollback fixture and permanently writes data to the dev database.

```python
# ❌ BANNED — bypasses rollback, permanently writes to pilot_dev
client = TestClient(app)

# ✅ REQUIRED — always use the conftest client fixture
class TestMyFeature:
    def test_something(self, client):
        resp = client.post("/api/v1/customers/test", json={...})
```

For running, adding and modifying tests, your reference to use always is: backend/tests/README-adding-tests.md

---

## 6. Test File Placement — Use `tests/domains/<domain>/` Only

All new test files go in one of the 16 existing `tests/domains/<domain>/` folders. Never create new `batch_*`, `phase_*`, or other top-level test directories. See [`backend/tests/README-adding-tests.md`](../../backend/tests/README-adding-tests.md) for the full list of domains.

---

## 7. Datetime — Always UTC-Aware

```python
# ❌ BANNED — naive datetime
from datetime import datetime
dt = datetime.utcnow()

# ✅ REQUIRED — timezone-aware UTC
from datetime import UTC, datetime
dt = datetime.now(UTC)
# OR
from core.datetime_utils import safe_now_utc
dt = safe_now_utc()
```

---

## 8. Alembic — Never Autogenerate Migrations

```bash
# ❌ BANNED — pulls in ghost diffs from unrelated schema changes
alembic revision --autogenerate -m "my migration"

# ✅ REQUIRED — always generate blank and write manually
alembic revision -m "phase_fe_1_batch_b1_descriptive_name"
```

Every migration must pass the triple-verify loop: `upgrade head` → `downgrade -1` → `upgrade head`.

---

## 9. Configuration — Never Hardcode Credentials or URLs

```python
# ❌ BANNED
url = "https://api.quickbooks.com/v3"

# ✅ REQUIRED
from core.config import settings
url = settings.QUICKBOOKS_BASE_URL
```

---

## 10. HTTP Status Code — Use `HTTP_422_UNPROCESSABLE_CONTENT`

`HTTP_422_UNPROCESSABLE_ENTITY` is deprecated in Starlette ≥0.30 and produces a `DeprecationWarning` in every test run.

```python
# ❌ DEPRECATED
status.HTTP_422_UNPROCESSABLE_ENTITY

# ✅ CORRECT
status.HTTP_422_UNPROCESSABLE_CONTENT
```

## 11. Git Commands

You are ONLY allowed to use `git` commands that are for reading and reviewing status and logs. You are NEVER to use:

- `stash` or `pop`
- `commit`
- `checkout`
- `push`
- `fetch`
- `restore`
- `add`

or any other similar functional `git` commands. ONLY Tom is allowed to run these. You MUST always ask him to run these for you.

---

## 12. Mutation Endpoints — Always Call `set_audit_context_sync()`

Every `POST`, `PATCH`, `PUT`, or `DELETE` endpoint that performs DB writes MUST call `set_audit_context_sync()` before the first `db.add()` or `db.commit()`. Without it, `actor_id` is NULL in `audit_log` — silent audit attribution loss.

```python
from core.db import get_db, set_audit_context_sync

@router.post("/resource")
def create_resource(
    ...,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    # REQUIRED: set before any DB write
    set_audit_context_sync(db, user_id=current_user.id)
    resource = Resource(tenant_id=current_user.tenant_id, ...)
    db.add(resource)
    db.commit()
```

---

## 13. Error Responses — RFC 7807 Problem Details Format Is Mandatory

All `HTTPException` `detail` values MUST be a RFC 7807 dict. Plain string `detail` is banned — it breaks the frontend `<NotificationBanner>` severity routing.

```python
# ❌ BANNED — plain string
raise HTTPException(status_code=404, detail="Not found")

# ✅ REQUIRED — RFC 7807 Problem Details
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={
        "type": "https://errors.pilotfortrades.com/not-found",
        "title": "Resource not found",
        "status": 404,
        "detail": f"Quote {quote_id} does not exist in this tenant.",
    },
)
```

Return `404` (not `403`) for cross-tenant access attempts — prevents UUID enumeration attacks.

---

## 14. Test Failures — Fix Every Failure You Encounter

If ANY test fails during your work — including tests that appear pre-existing or caused by a previous batch — **you must fix it before declaring the task done**. There is no "not my fault" exception.

- If you cannot identify the root cause → **STOP and ask Tom** before proceeding.
- You may NOT mark a task complete while any test is failing without explicit written confirmation from Tom that the failure is known and accepted.

---

## 15. Test Execution — Unit Tests During Development, Full Suite at the End

During implementation, run **unit tests only** for fast feedback:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

Run the **full suite** exactly **once**, at the very end, before declaring the batch done. The default full-suite gate **excludes the slow vendor/live-service suites** (Tom's standing instruction, 2026-08-16 — they add 9+ minutes): `integration`, `e2e`, `requires_telnyx`, `requires_stripe`, `requires_sendgrid`, `requires_redis`:

```bash
python -m pytest -m "not integration and not requires_telnyx and not requires_stripe and not requires_sendgrid and not requires_redis and not e2e" --tb=short -q 2>&1 | tail -15
```

**Vendor-suite inclusion rule**: if the batch modified code those suites cover — Telnyx carrier/webhooks (`services/telnyx*`, SMS routes/tasks), Stripe billing/webhooks, SendGrid email dispatch, or Redis-dependent modules — also run the affected marker suite(s) before sign-off (e.g. `python -m pytest -m requires_telnyx --tb=short -q`; may need vendor env vars — coordinate with Tom) and record the result in the Completion Summary.

Never run the full suite repeatedly during development — unit tests are the iteration loop; the gated full suite runs once at the end.

---

## 16. Test Data Isolation — Never Touch Data You Didn't Create

Tests run against a shared database that contains persistent seed data and may contain scenario data used for manual UI testing. Every test — whether creating new tests or modifying existing ones — MUST be resilient to this environment.

**These rules apply when writing OR modifying any test:**

- **Never UPDATE or DELETE rows you did not INSERT in the current test.** If a test needs a record in a specific state, INSERT a new one — never mutate shared seed rows or scenario data.
- **Never assert on total row counts.** Seed data and other scenario data will be present. Always filter by the specific ID(s) you inserted: `assert result.id == inserted_id`.
- **Never assume a table is empty** before your test runs. Use `second_tenant` for empty-state behavior — `test_tenant` always has seeded rows from `seed_test_tenant.py`.
- **Cleanup is optional but must be scoped:** If a test cleans up after itself, `DELETE` only rows it inserted (filter by the exact ID returned at insert time). Never issue a broad `DELETE FROM table WHERE tenant_id = :test_tenant_id` — that wipes all scenario data for the shared tenant.
- **The `db_session` fixture is the primary isolation mechanism.** Every test runs in a transaction that auto-rolls back after the test. Do not add manual cleanup calls unless the test is explicitly testing soft-delete behavior.
- **Tests that currently pass must continue to pass** when scenario seed scripts are run. If your test relies on a table being empty, it will break as soon as `seed_scenario_*.py` adds data to that table. Fix the test to be ID-scoped before committing.

```python
# ✅ CORRECT — scoped by inserted ID; resilient to any other data in the table
def test_create_customer(client, test_tenant, mock_cognito_jwt):
    resp = client.post("/api/v1/customers/test", json={"display_name": "Test Co", ...})
    assert resp.status_code == 201
    customer_id = resp.json()["id"]

    get_resp = client.get(f"/api/v1/customers/{customer_id}")
    assert get_resp.json()["id"] == customer_id   # ← scoped to this specific record

# ❌ WRONG — counts all customers; breaks when any seed data adds a customer
def test_customer_list(client, test_tenant, mock_cognito_jwt):
    client.post("/api/v1/customers/test", json={...})
    resp = client.get("/api/v1/customers/")
    assert len(resp.json()) == 1   # ← FAILS when seed data adds other customers
```

---

## 17. `require_permission()` — Use `feature_code` ONLY for PRD-Priced, Seeded Features

Any endpoint that should be blocked for tenants on lower subscription tiers requires the `feature_code` parameter:

```python
# RBAC only (no entitlement check):
@require_permission("quotes.create")

# RBAC + entitlement gating (subscription tier check):
@require_permission("dispatch.manage", feature_code="schedule_lanes")
```

**Valid `feature_code` values are ONLY the features that (a) appear in the PRD §3.11 pricing table AND (b) have seeded `product_feature` + `product_plan_product_feature_version` rows** — currently `schedule_lanes` (block), `voice_ai_minutes` (soft), `outbound_sms_segments` (soft), all modeled in `app/models/billing.py`. Omitting `feature_code` means all tiers can access the endpoint regardless of their subscription plan.

> **Phantom-gate rule (2026-08-30, PLP-FIX-1)**: a `feature_code=` wiring without BOTH (a) and (b) is a phantom gate — it will 402 every tenant (`feature_not_in_plan`). This actually happened with `quotes_per_month`: invented as a framework example, wired into the quotes route, never in the PRD pricing model (quotes are unlimited on all plans), never seeded. It was removed, not seeded. **Never wire a gate for a feature the PRD marks unlimited, and never seed a feature row just to satisfy a wired gate.** See §18.

---

## 17b. New Entity Endpoints — Always Add a `/test` Counterpart

Every new entity with a `POST` create endpoint MUST have an unauthenticated `/test` endpoint. Without it, the test suite cannot create seed data for that entity type.

Use `TestUserContext` from `core.test_context` and a shared `_create_impl()` function:

```python
from core.test_context import TestUserContext, get_test_context

def _create_entity_impl(entity_in, db, user_context):
    """Shared logic — called by both authenticated and test endpoints."""
    entity = Entity(tenant_id=user_context.tenant_id, ...)
    db.add(entity); db.commit(); db.refresh(entity)
    return entity

@router.post("/entity", status_code=201)
def create_entity(entity_in, db=Depends(get_db), user=Depends(get_current_user)):
    set_audit_context_sync(db, user_id=user.id)
    return _create_entity_impl(entity_in, db, user)

@router.post("/entity/test", status_code=201)
def create_entity_test(entity_in, db=Depends(get_db), ctx: TestUserContext = Depends(get_test_context)):
    """Test-only endpoint — bypasses JWT, uses canonical test tenant."""
    return _create_entity_impl(entity_in, db, ctx)
```

---

## 18. Subscription & Pricing — Master Reference (MANDATORY — never deviate)

> **Added 2026-08-30** (Tom mandate, after PLP-FIX-1: a phantom `quotes_per_month` gate 402'd ALL quote creation because it contradicted the pricing model — and its seed rows never existed). Everyone touching plans, prices, limits, entitlements, usage quotas, upgrade prompts, or billing surfaces must know and follow this section.

**Master definition (product truth)**: [`dev-docs/product-requirements/mvp-prd.md`](../../dev-docs/product-requirements/mvp-prd.md) **§3.11 "Subscriptions & Usage" → Pricing Table + feature rows** — the ONLY authoritative definition of Pilot's subscription plans, prices, included allowances, limits, enforcement modes, and overage rates.

**Runtime mapping (implementation truth)**: `dev-docs/pilot-operations.md` _(private)_ §2 (Product Plan Hierarchy) · §3 (Subscription Tier Model) · §5 (Founders/Charter Cohort Model) · §6 (Per-Tenant Overrides) — how the master maps to `subscription_tier` → `product_plan` → `product_plan_product_feature_version`. Charter mechanics: GTM v3 §6 + locked decisions D16/D17. Stripe price IDs: [`dev-docs/integrations/stripe/stripe-pricing-config.md`](../../dev-docs/integrations/stripe/stripe-pricing-config.md) §4.

**Snapshot (2026-08-30)** — *if this ever disagrees with PRD §3.11, **the PRD wins** — flag the drift to Tom; never "fix" it yourself:*

| Plan | Price | Schedule lanes | Voice AI | SMS segs | Enforcement |
|---|---|---|---|---|---|
| **Charter** (12-cap cohort, formerly "Founders") | $0 × 90 days → **$49/mo locked for life** (billed monthly) | 5 | 90 min/mo | 100/mo | no overages in free period; soft after; free period operator-extendable (case by case; not an advertised offer) |
| **Trial** | $0 × 14 days | 5 | 90 | 100 | **block** (hard cap, no card) |
| **Starter** | **$49/mo** annual · $59/mo month-to-month | 5 | 90 | 100 | **soft** — overage: Voice $0.05/min, SMS $0.05/seg |
| **Teams** | **$149/mo** annual · $179/mo month-to-month | 20 | 300 | 500 | **soft** — same overage rates |

Add-ons: +1 lane $10/mo · +5 lanes pack $40/mo · +100 SMS segs per extra Telnyx number at +$5/mo.

**Unlimited on ALL plans — never gate these**: users, jobs, quotes, invoices, customers, QB syncs, emails, calendar syncs.

**Only three gated/metered features exist**: `schedule_lanes` (block), `voice_ai_minutes` (soft + overage), `outbound_sms_segments` (soft + overage). There is intentionally **no** `quotes_per_month`, job, invoice, or user limit.

**Non-negotiables**:

1. **Never invent** plan names, prices, allowances, limits, enforcement modes, or overage rates. Every value must trace to PRD §3.11 (product) and the seeded `product_plan_product_feature_version` rows (runtime).
2. **Phantom-gate rule**: never wire an entitlement gate (`feature_code=`, plan-limit check, paywall branch) for a feature the master marks unlimited. A gate requires BOTH a PRD §3.11 pricing line AND seeded `product_feature` + ppfv rows — a wiring without both is a phantom gate: **remove it, don't seed around it**.
3. Any batch touching subscription, billing, entitlement, usage metering, or paywall code reads PRD §3.11 + `pilot-operations.md` §2–§6 in Pre-Work (enforced via prompt-inclusions §19). Seeding a `product_feature`/ppfv row for a feature absent from the PRD pricing table is the same class of violation as gating an unlimited feature.
4. If work seems to require a value not in the master → **STOP and ask Tom**. The master changes only via Tom-approved PRD edits (Architect-owned); the Architect refreshes this snapshot in the same change — that is how updates reach every mode automatically.

### 18.1 Runtime behavior the cascade enforces (from `pilot-operations.md`)

- **Tier → Plan cascade**: `subscription_tier.product_plan_code` → `product_plan` → `product_plan_product_feature_version`. The entitlement service resolves limits via this cascade. Never hardcode limits.
- **`is_billing_active`**: `subscription_status.is_billing_active` is the paywall gate. `trialing`, `active`, `past_due` = access granted. `unpaid`, `canceled`, `paused` = 402 returned. The entitlement service reads this — never check subscription status by code string in application code.
- **Notification template resolution**: tenant-specific override first → platform default (`tenant_id IS NULL`) fallback. All 9 active `notification_type` codes have 3-channel (email, in_app, push) platform defaults. SMS is opt-in only — no SMS defaults with `tenant_id IS NULL`.
- **Charter cohort**: Charter tier = $0 for 90 days, Starter-equivalent limits, then $49/mo locked. Post-free billing activates via a Stripe Subscription Schedule (not a plan change), managed in `stripe_subscriptions.py`.

## 19. Payment Refund Model (SD-2 Design — Permanent)

The SD-2 refund architecture uses a **new negative-amount payment row** — NOT columns on the original payment row.

- `payment.refunded_amount_cents` and `payment.refunded_at` columns were added by migration `1923b2d3aa14` (July 6) and **intentionally dropped** by migration `44b8d8f15789` (July 14) as part of the SD-2 architectural decision.
- **Correct refund model**: Insert a new `payment` row with `amount_cents < 0` (negative amount = refund) and `status_id` pointing to `payment_status.code = 'refunded'`. The original `succeeded` payment row is NOT modified.
- **Never add back** `refunded_amount_cents` or `refunded_at` columns without explicit Tom approval — this is a deliberate architectural choice aligned with Stripe's own refund model.

## 20. Seed Data Coexistence Rules (MANDATORY before modifying any seed script)

> **Read [`backend/README-seed-data.md`](../../backend/README-seed-data.md) §7 before making any seed script changes.**

Critical rules:
- **Reserved UUIDs** `...0001` through `...0005` are permanently occupied (tenant, owner, tech, office, accountant). Never reuse these in new scripts or tests.
- **GiST exclusion constraint** on `labor_rate_version` and `tenant_markup_version`: open-ended range `[2026-06-01, NULL)` already exists. Do NOT INSERT a new overlapping row — this violates the constraint. UPDATE the existing row instead.
- **`user_endpoint` trigger guards**: Two DB triggers block deletion of the last primary email endpoint. Disable both triggers before any cleanup that touches `user_endpoint` rows.
- **Run order is mandatory**: `seed_core.py` → `seed_platform.py` → `seed_test_tenant.py` → `seed_scenario_*.py`. Skipping steps causes silent FK failures.
- **`payment_method.psp_provider='seed'`**: The correct pattern for a seed/test payment_method that doesn't require a real Stripe ID. Always check for an existing `psp_provider='seed'` row before inserting a new one.

---

## 21. Sync Routes — This App Is Synchronous by Design; Never Mix `async def` With the Blocking Session

**Stack**: FastAPI 0.135, Starlette 0.52, SQLModel 0.0.37 on SQLAlchemy 2.0 (sync `Session`), Python 3.11.

Every route and `_impl()` in this codebase is a **plain `def`** (verified across `api/routes/`). FastAPI runs `def` routes in a threadpool, so the blocking psycopg2 `Session` never stalls the event loop. This is correct and intentional — do **not** "modernize" routes to `async def`.

```python
# ✅ REQUIRED — sync route + sync Session; FastAPI offloads to a threadpool
@router.get("/customers/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: UUID, db: Session = Depends(get_db), ...):
    return _get_customer_impl(customer_id, db, ...)

# ❌ BANNED — async route awaiting nothing while calling the BLOCKING sync Session.
#    This runs the psycopg2 call directly on the event loop → stalls ALL requests.
@router.get("/customers/{customer_id}")
async def get_customer(customer_id: UUID, db: Session = Depends(get_db)):
    return db.exec(select(Customer)...).first()   # blocking call on the loop
```

**Rule**: If a handler touches the DB `Session`, it MUST be `def` (sync). Only make a function `async def` if it exclusively `await`s genuinely non-blocking I/O (an `httpx.AsyncClient` call) and never touches the sync `Session`. When in doubt → `def`. Mixing `async def` with the blocking session is the single most damaging concurrency mistake in this stack.

---

## 22. Pydantic v2 + SQLModel — Use v2 Idioms, Never v1 Carryover

**Stack**: Pydantic 2.12. v1-era APIs are deprecated and emit warnings that pollute the test run (Rule 10 exists precisely to keep the run warning-clean).

```python
# ❌ BANNED — Pydantic v1 carryover
class QuoteCreate(BaseModel):
    class Config:                 # v1 inner Config class
        orm_mode = True
    @validator("total")          # v1 decorator
    def check(cls, v): ...
obj.dict(); obj.json()           # v1 serializers
Model.parse_obj(data)            # v1 constructor

# ✅ REQUIRED — Pydantic v2
class QuoteCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)   # replaces orm_mode
    @field_validator("total")                          # or @model_validator(mode="after")
    @classmethod
    def check(cls, v): ...
obj.model_dump(); obj.model_dump_json()
Model.model_validate(data)
```

Additional v2 rules for this repo:
- **Request/response Pydantic schemas live in `api/schemas/[domain].py`** — separate from the SQLModel ORM classes in `app/models/`. Changing what an endpoint accepts/returns means editing BOTH. (Restated from the std-inclusions file — it is a frequent miss.)
- **`response_model` on every route** — never return a raw ORM object without a Pydantic response schema; it leaks columns and breaks the generated OpenAPI/TypeScript contract the React Engineer consumes.
- **Money is integer cents** — all monetary fields are `_cents: int` (see `amount_cents`, `annual_price_cents`). Never introduce a `float` money column; never do float arithmetic on money.

---

## 23. Ruff Is the Linter/Formatter — Changed-Files-Only; Fix All Errors

**Stack**: Ruff 0.15 (config in [`backend/pyproject.toml`](../../backend/pyproject.toml); `target-version = "py311"`, line-length 88, rule sets `E,W,F,I,B,UP,N,C4,RUF`).

### Changed-Files-Only Policy

Run ruff **only against the Python files you changed in this session** — never against the entire codebase (`ruff check .`). The codebase has pre-existing lint issues across many files unrelated to your batch. Running ruff on the whole tree surfaces hundreds of unrelated errors, which is counterproductive.

**Iterative cleanup philosophy**: By scoping ruff to changed files and fixing *all* errors in those files (including pre-existing ones), the codebase is cleaned up incrementally — each batch cleans the files it touches. Over time, the entire codebase converges on zero ruff violations without any single batch bearing the burden of a global cleanup.

### How to Run

```bash
cd <repo>/backend && source .venv/bin/activate

# 1. Get the Python files you changed this session (staged + unstaged vs HEAD; excludes deletions)
CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py')

# 2. Lint + autofix + format ONLY those files
if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY     # lint + import sort (isort "I") + pyupgrade ("UP") autofix
    ruff format $CHANGED_PY          # format (line-length 88)
    ruff check $CHANGED_PY           # re-check: any remaining errors need manual fixing
fi
```

### Fix-All-Errors Rule

**All ruff errors in your changed files MUST be fixed — no exceptions.** This includes:

- Errors **you introduced** in this session.
- **Pre-existing errors** in files you touched (even on lines you did not modify).

`ruff check --fix` auto-fixes many issues (import sorting, unused imports, pyupgrade rewrites). For errors it cannot auto-fix, fix them manually. If a pre-existing error requires a risky or out-of-scope refactor, **STOP and ask Tom** — do not leave it unfixed and do not add `# noqa` to suppress it.

### Idiom Rules (Enforced by Ruff)

- **`I` (isort) is enforced** — first-party packages are `app, core, services, tasks, api`. Do not hand-order imports; let `ruff check --fix` sort them.
- **`UP` (pyupgrade) is on** — use modern typing: `str | None` not `Optional[str]`, `list[X]` not `List[X]`, `X | Y` unions. This aligns with Rule 7 (`from datetime import UTC`).
- **Do not add `# noqa` to silence a rule** without a one-line justification comment. The ignore list in `pyproject.toml` is deliberate (e.g., `B008` for `Depends()`); do not expand it without Tom's approval.

---

## 24. New Tables — Inherit the Correct Audit Mixin (Never Hand-Roll Timestamps)

Every new table inherits exactly one mixin from [`app/models/mixins.py`](../../backend/app/models/mixins.py) — never hand-declare `created_at` / `updated_at`:

| Table character | Mixin | Gives you |
|---|---|---|
| Mutable business record (customer, job, quote) | `StandardAuditMixin` | `created_at`, `updated_at` (TIMESTAMPTZ, auto-`onupdate`), `created_by`, `updated_by` |
| Immutable ledger / append-only (payment, audit entry) | `AppendOnlyMixin` | `created_at`, `created_by` only |
| Automated system/machine event | `MachineLogMixin` | `created_at` only |

- All three use `AwareDatetime` + `DateTime(timezone=True)` → **TIMESTAMPTZ** columns. This is why Rule 7 (UTC-aware datetimes) is non-negotiable: a naive `datetime` will fail to bind or silently store wrong offsets.
- **Every business table also needs `tenant_id: uuid.UUID`** (indexed) — the mixins deliberately do NOT add it, because platform/lookup tables (Group A/B) are not tenant-scoped. If the table holds tenant data, add `tenant_id` explicitly and remember Rule 4 (tenant-scoped `select()`, `db.get()` banned).
- When a migration adds a `StandardAuditMixin` table's seed rows via raw `op.execute()`, you MUST set `created_at, updated_at = NOW(), NOW()` explicitly — the SQLModel default_factory does not run for raw SQL inserts (restated from std-inclusions §20).

---

## 25. Scale Awareness — 186 Tables; Verify, Don't Assume

The schema had **186 `public` tables** (+ the `audit` schema) when this rule was written; 193 tables in total at hibernation. No engineer holds this in their head. This is the structural reason Rule 1.2 (MCP-verify every column) and the `db_models_map.md` lookup exist — they are not bureaucracy, they are the only reliable path in a schema this large. Before referencing any table you have not queried in the current session, run the `information_schema.columns` query. "I'm pretty sure the column is called X" is the exact failure mode these rules prevent.