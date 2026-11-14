# Python Engineer Implementation Prompt — Standard Inclusions

**Purpose**: This file is the authoritative checklist and template guide for any AI agent creating a Pilot Python Engineer implementation prompt. Every prompt targeting the `pilot-python-engineer` mode MUST include all sections marked **REQUIRED**. Sections marked **CONDITIONAL** apply only when the described condition is true.

**Location**: `backend/python-engr-std-prompt-inclusions.md`
**Consumed by**: Pilot Architect mode when writing implementation prompts
**Last updated**: 2026-08-16 (§14 Phase 2 gate: full suite is now vendor-deselected by default per Tom's standing instruction; §15 DoD + anti-patterns aligned)

> **Cross-reference**: This file is the *prompt template* companion to the mode's *hard rules* in [`.roo/rules-pilot-python-engineer/python-engineer-rules.md`](../.roo/rules-pilot-python-engineer/python-engineer-rules.md). The rules file is the authority (§1–§25); this file translates those rules into the sections a prompt must contain. When the two conflict, the rules file wins — but they should never conflict, so if you find a divergence, flag it for Tom.

> **Confirmed stack (2026-07-28)** — cite these where a rule depends on a version:
> Python 3.11 · FastAPI 0.135 / Starlette 0.52 · Pydantic 2.12 · SQLModel 0.0.37 on SQLAlchemy 2.0 (**sync `Session`**) · Ruff 0.15 · Alembic (blank migrations only) · pytest ≥7 (`--strict-markers`). The DB has **186 `public` tables + 1 `audit` table** (when written; 193 tables in total at hibernation) — no engineer holds this in their head, which is *why* MCP verification is mandatory, not optional.

---

## 1. MANDATORY STOP Section (REQUIRED)

Every prompt MUST open with a `⚠️ MANDATORY STOP: Read These First` section immediately after the header block. This is not optional and must be the first substantive content the engineer reads.

```markdown
## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **[`.roo/rules-pilot-python-engineer/python-engineer-rules.md`](../.roo/rules-pilot-python-engineer/python-engineer-rules.md)** — full document; the 25 hard rules are non-negotiable STOPs
- **[`dev-docs/architecture-design/pilot-python-engineer-methods.md`](../dev-docs/architecture-design/pilot-python-engineer-methods.md)** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **[`backend/tests/README-adding-tests.md`](tests/README-adding-tests.md)** — full document; this governs all test file structure, domain markers, and fixture rules
```

**Always call out the highest-risk rules for the specific batch.** Common critical rules:

```markdown
Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 2**: After any model file change → regenerate `backend/db_models_map.md` via `python generate_db_model_map.py`.
- **Rule 3**: After any endpoint change → run `python export_openapi_json.py` (updates both `openapi.json` and `openapi_schema_map.md`).
- **Rule 4**: All Alembic migrations must be written as **blank** migrations (never `--autogenerate`). Data changes use raw `op.execute()` with `SET LOCAL session_replication_role = 'replica';`.
- **Rule 5**: Never use module-level `TestClient` in any test file. Always use the `client` fixture from `conftest.py`.
- **Rule 6**: `db.get()` is permanently banned on tenant-scoped models. Always use tenant-scoped `select()` with an explicit `WHERE tenant_id = :tid` clause.
- **Rule 7**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE data — all data changes go through the application code.
- **Rule 8**: All API error responses MUST follow RFC 7807 Problem Details format (`{"type": "https://...", "title": "...", "status": N, "detail": "..."}`). Non-standard error shapes break the frontend `<NotificationBanner>` severity routing.
- **Rule 9**: Every mutation endpoint MUST call `set_audit_context_sync(db, user_id=user.id)` before committing. Without this, `actor_id` is NULL in `audit_log` for that operation — silent audit attribution loss.
- **Rule 10**: `require_permission("resource.action")` has an optional `feature_code` parameter. For any endpoint that should be subscription-tier-gated, include `feature_code="feature_name"`. Valid feature codes live in `app/models/subscription.py` as `ProductFeature` rows.
- **Rule 11**: If ANY test fails during your work — even one that appears to be a pre-existing failure or caused by a previous batch — **you must fix it before declaring the batch done**. There is no "not my fault" exception. If you cannot identify the root cause → STOP and ask Tom.
- **Rule 12 (sync routes — rules §21)**: This app is **synchronous by design**. Every DB-touching route and `_impl()` is a plain `def` — FastAPI offloads `def` routes to a threadpool. **Never convert a handler that touches the sync `Session` to `async def`** — that runs the blocking psycopg2 call on the event loop and stalls all requests. Only use `async def` for handlers that exclusively `await` non-blocking I/O (e.g. `httpx.AsyncClient`) and never touch the `Session`.
- **Rule 13 (Pydantic v2 — rules §22)**: Use v2 idioms only. Banned v1 carryover: `class Config`, `@validator`, `.dict()`, `.json()`, `.parse_obj()`. Use `model_config = ConfigDict(...)`, `@field_validator` / `@model_validator`, `.model_dump()`, `.model_validate()`. Every route needs `response_model`. Money is always integer cents (`_cents: int`) — never a float.
- **Rule 14 (Ruff — rules §23)**: Ruff 0.15 is the linter+formatter. Run ruff **only against the files you changed** (not the whole codebase) — `git diff --name-only HEAD -- '*.py'` to get the list, then `ruff check --fix <files> && ruff format <files>`. **Fix ALL errors in those files** — including pre-existing ones you did not create. This is the iterative cleanup approach: each batch cleans the files it touches, and the codebase converges on zero violations over time. Do not hand-order imports (isort `I` is enforced); use modern typing (`str | None`, `list[X]`). No unjustified `# noqa`.
- **Rule 15 (audit mixins — rules §24)**: New tables inherit exactly one mixin from `app/models/mixins.py` (`StandardAuditMixin` / `AppendOnlyMixin` / `MachineLogMixin`) — never hand-declare `created_at`/`updated_at`. Add `tenant_id` explicitly (mixins do not provide it). All timestamps are TIMESTAMPTZ → the UTC-aware datetime rule is non-negotiable.
- **Rule 16 (verify, don't assume — rules §25)**: 186+ tables exist (193 at hibernation). "I'm pretty sure the column is X" is the exact failure the MCP-verify and `db_models_map.md` rules prevent. Query `information_schema.columns` for every table you touch this session before writing SQL.
```

Include only the rules that are relevant to the specific batch. Do not list all 16 every time if only 4 apply — but Rules 1, 12, and 16 (verify-before-write, sync-routes, no-assume) apply to nearly every backend batch.

---

## 2. Pre-Work: Regression Baseline (REQUIRED)

Every prompt MUST include a regression baseline capture command before any work starts. This gives the engineer a known-good test count to protect.

```markdown
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
>
> You may NOT start implementation work while tests are in an unexplained failed state.
```

---

## 3. Pre-Work: MCP Verification Queries (REQUIRED)

Every prompt MUST include at least 2–5 `postgres-local` MCP queries to verify the DB state before any code is written. The queries must be specific to the batch — never generic.

> **Canonical query patterns**: Use the exact SQL from [`dev-docs/db-design/postgres-mcp-guide.md`](../dev-docs/db-design/postgres-mcp-guide.md) — it has verified snippets for columns, PKs, FKs, indexes, triggers, functions, and CHECK/EXCLUDE constraints. **Always filter by `table_schema IN ('public', 'audit')`** — without the filter you either get empty arrays or thousands of system objects. Do NOT use SQLite syntax (`PRAGMA`, `SHOW TABLES`) — this is strictly PostgreSQL.

> **Engineer safety net — independent column verification (MANDATORY)**: Before writing ANY SQL statement, Alembic migration code, or SQLModel field reference in this batch, run `SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_schema = 'public' AND table_name = '<table>' ORDER BY ordinal_position;` for **every table you will touch**. The Architect's prompt may contain column names derived from the JSON schema file or a prior session — those may be stale or wrong. The live DB is the only authoritative source. If any column name in the prompt does not match what MCP returns → use the MCP-returned name, not the prompt's name, and note the discrepancy in your Completion Summary. Do NOT ask the Architect to re-do the prompt — just correct it inline and proceed.

```markdown
## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

```sql
-- 1. [Describe what this confirms]
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'your_table_name'
ORDER BY ordinal_position;

-- 2. [Verify a table exists or doesn't exist]
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name = 'expected_table';

-- 3. [Verify a trigger or function exists]
SELECT proname FROM pg_proc WHERE proname = 'set_updated_at';
```

**Standard useful patterns for MCP queries:**

```sql
-- Find tables matching a name pattern
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name LIKE '%keyword%'
ORDER BY table_name;

-- Check all columns on a table
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'tablename'
ORDER BY ordinal_position;

-- Verify a constraint exists
SELECT conname, contype FROM pg_constraint 
WHERE conrelid = 'public.tablename'::regclass;

-- Check a trigger exists
SELECT trigger_name FROM information_schema.triggers
WHERE event_object_table = 'tablename';

-- Check a user/role has correct permissions
SELECT u.email, pr.code AS role_code, pr.permissions
FROM "user" u
JOIN tenant_user tu ON u.id = tu.user_id
JOIN tenant_user_role tur ON tu.id = tur.tenant_user_id
JOIN platform_role pr ON tur.role_id = pr.id
WHERE u.email = 'dev@pilot.local';

-- Verify current alembic head
SELECT version_num FROM public.alembic_version;
```

---

## 4. Pre-Work: Mandatory File Reads (REQUIRED)

Every prompt MUST list every source file the engineer must read using `read_file` before writing any code. Never assume the engineer knows what's in a file — even recently-modified files may have changed.

```markdown
## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/app/models/relevant_model.py          ← [why: e.g., understand StandardAuditMixin usage]
backend/api/routes/relevant_route.py          ← [why: e.g., understand existing endpoint patterns]
backend/api/schemas/relevant_schema.py        ← [why: understand existing Pydantic request/response shapes before adding fields]
backend/migrations/versions/most_recent.py   ← [why: migration pattern reference]
backend/tests/conftest.py                    ← [why: understand available fixtures]
backend/db_models_map.md                     ← [why: confirm model names and table mappings]
```

> **The `api/schemas/` layer is separate from `app/models/`**: `app/models/` contains SQLModel ORM classes. `api/schemas/` contains Pydantic `BaseModel` request/response shapes for endpoints. Any change to what an API endpoint accepts or returns requires updating BOTH the ORM model AND the Pydantic schema in `api/schemas/[domain].py`.

Also run these grep commands to find related files:

```bash
grep -rn "ClassName\|function_name" backend/ --include="*.py" -l
```
```

---

## 5. Alembic Migration Standards (CONDITIONAL — when batch includes a migration)

When the batch creates an Alembic migration, include these requirements:

```markdown
### Alembic Migration Rules

Per `pilot-python-engineer-methods.md` §13:

1. **Always use blank migrations** — never `alembic revision --autogenerate` for data or trigger changes:
   ```bash
   alembic revision -m "descriptive_migration_name"
   ```

2. **Always add the replica role setting** at the start of `upgrade()` for seed/data migrations:
   ```python
   def upgrade() -> None:
       op.execute("SET LOCAL session_replication_role = 'replica';")
       # ... rest of migration
   ```

3. **Always implement `downgrade()`** — never leave it empty. Downgrade must exactly reverse the upgrade.

4. **Test the full cycle** after every migration:
   ```bash
   alembic upgrade head
   alembic downgrade -1
   alembic upgrade head
   alembic current   # must show new head revision
   ```

5. **Use `ON CONFLICT DO NOTHING`** for all seed data INSERTs so the migration is idempotent.

6. **3-Part Pattern for adding NOT NULL columns to existing tables**:
   - Part 1: Add column as nullable
   - Part 2: Backfill existing rows with safe defaults via `op.execute()`
   - Part 3: Lock NOT NULL and set server default via `op.alter_column()`
```

---

## 6. Test Writing Standards (REQUIRED when batch adds new code)

Every prompt that adds new backend functionality MUST specify test requirements. Always reference `README-adding-tests.md`.

```markdown
### Test Requirements

Per [`backend/tests/README-adding-tests.md`](tests/README-adding-tests.md):

**Every new test file MUST:**
- Declare `pytestmark` with both domain marker and `pytest.mark.unit`:
  ```python
  pytestmark = [
      pytest.mark.domain_your_domain,   # e.g., pytest.mark.domain_crm
      pytest.mark.unit,
  ]
  ```
- Use the `client` fixture (never module-level `TestClient`)
- Use `test_tenant` and `test_user` fixtures (never hardcoded UUIDs like `'00000000-0000-0000-0000-000000000001'`)
- Scope assertions by inserted IDs — never `assert len(all_rows) == N` (seed data makes total counts unpredictable)
- Be placed in the correct domain folder under `backend/tests/domains/<domain>/`

**Test Resilience Rule (MANDATORY — applies to every test, new or modified):**

Tests run against a shared database that contains persistent seed data (`seed_test_tenant.py`, `seed_scenario_*.py`) and may contain scenario data used for manual UI testing. Every test must be resilient to this environment:

- **Never UPDATE or DELETE rows you did not INSERT** in the current test. If a test needs a record in a specific state, INSERT a new one — never mutate shared seed rows.
- **Never assert on total row counts** for a table. Seed data and other tests' data will be present. Always filter by the specific ID(s) you inserted in this test: `assert result.id == inserted.id`.
- **Never assume a table is empty** before your test runs. Use `second_tenant` for "empty state" behavior — `test_tenant` always has seeded rows. If you need isolation, insert into `second_tenant` or `tenant_a`/`tenant_b`.
- **Cleaning up is optional but scoped**: If a test does clean up after itself, `DELETE` only rows it inserted (filter by the exact ID returned at insert time). Never issue `DELETE FROM table WHERE tenant_id = test_tenant_id` — that would wipe all scenario data for the shared test tenant.
- **The `db_session` fixture is the correct isolation mechanism**: Every test runs in a transaction that is rolled back after the test. This is the primary cleanup mechanism. Use it. Do not add manual `db.delete()` calls unless the test is explicitly testing soft-delete behavior.

```python
# ✅ CORRECT — scoped by inserted ID
def test_create_customer(client, test_tenant, mock_cognito_jwt):
    resp = client.post("/api/v1/customers/test", json={...})
    customer_id = resp.json()["id"]
    
    # Assert only on the record you just created
    get_resp = client.get(f"/api/v1/customers/{customer_id}")
    assert get_resp.json()["id"] == customer_id

# ❌ WRONG — counts all customers in tenant (seed data breaks this)
def test_customer_list(client, test_tenant, mock_cognito_jwt):
    client.post("/api/v1/customers/test", json={...})
    resp = client.get("/api/v1/customers/")
    assert len(resp.json()) == 1  # FAILS if seed data added any customers
```

**Domain folder mapping** (from `README-adding-tests.md`):
| Domain | Folder |
|---|---|
| Auth / permissions / MFA / sessions | `identity_access/` |
| Customers / sites / contacts | `crm/` |
| Quotes / discounts / templates | `sales_quoting/` |
| Invoices / Stripe / public links | `invoicing_billing/` |
| Jobs / change orders / LOTO / ETC / GPS | `field_operations/` |
| Notifications / comms / SMS / push | `notifications_comms/` |
| QuickBooks sync / OAuth / conflicts | `quickbooks/` |
| Subscriptions / entitlements / Stripe lifecycle | `subscriptions_usage/` |
| Audit logs / deletion pathways | `audit_compliance/` |
| Pricebook / supplier prices / labor rates | `catalog_pricing/` |
| Tax rate versions | `tax_calculation/` |
| Voice intents / conversation sessions | `voice_ai/` |
| Dispatch board / assignments / conflicts | `scheduling_dispatch/` |
| Offline sync / photo upload / dedup | `mobile_offline/` |
| Help chat / RAG / feedback | `help_support/` |
| Platform settings / dashboard / reports / webhooks | `platform_infrastructure/` |
| NEC calculators / calculation logs | `nec_calculations/` |

**Available fixtures from `conftest.py`** (do not re-declare these):

*Infrastructure:*
- `db_session` — transaction-wrapped PostgreSQL session, auto-rolls back after each test
- `client` — FastAPI TestClient with `get_db` overridden to use `db_session`

*Authentication:*
- `mock_cognito_jwt_verify` — patches `verify_cognito_jwt` globally
- `mock_jwt_for_user` — callable: `token = mock_jwt_for_user(user.email)`
- `mock_cognito_jwt` — callable: patches JWT AND injects `Authorization` header into client automatically

*Tenant & User Context:*
- `test_tenant` — canonical test tenant (used with unauthenticated `/test` endpoints)
- `test_user` — canonical test user (`email = dev@pilot.local`)
- `second_tenant` — a second isolated tenant; **use for "empty state" tests** (test_tenant always has seeded rows)
- `tenant_a` / `tenant_b` — two fully isolated tenants for **cross-tenant IDOR/security tests**
- `user_tenant_a` / `user_tenant_b` — owners linked to `tenant_a` / `tenant_b`

*Domain Entity Fixtures (avoid creating entities manually when these exist):*
- `test_customer`, `test_site`, `test_contact` — CRM entities in `test_tenant`
- `test_job` — Job in draft status in `tenant_a`
- `test_quote_status`, `test_quote_version` — Quote + child QuoteVersion
- `test_invoice_status` — InvoiceStatus (code: draft)
- `test_supplier`, `test_notification_outbox`, `test_notification_event`
- `test_webhook_endpoint`, `test_webhook_event`
- `test_app_service`, `test_qco_line_type`
- `utc_now`, `aware_datetime` — timezone-aware datetime helpers

**Autouse fixtures (run on every test automatically — you do not declare them):**

| Autouse Fixture | What it does | Opt-out marker |
|---|---|---|
| `mock_cognito_jwks` | Patches AWS Cognito JWKS — no real AWS call | None needed |
| `mock_ai_services` | Patches all Ollama + Whisper HTTP calls | `@pytest.mark.requires_ollama` / `@pytest.mark.requires_whisper` |
| `mock_entitlement_allowed` | Bypasses all subscription entitlement checks (returns `is_allowed=True`) | `@pytest.mark.skip_mock_entitlement_allowed` |

> **If your test exercises entitlement gating** (i.e., tests that a feature is blocked for a specific subscription tier): you MUST add `@pytest.mark.skip_mock_entitlement_allowed` — otherwise `mock_entitlement_allowed` silently bypasses the check and the test always passes.

**For "empty state" tests**: use `second_tenant` fixture — `test_tenant` always has seeded rows from `seed_test_tenant.py`.

**For temporal range tables** (`labor_rate_version`, `tenant_markup_version`): use past closed date ranges (e.g., `[2019-01-01, 2020-01-01)`) to avoid GiST exclusion violations with the open-ended seeded rows.
```

---

## 7. Schema Manager (CONDITIONAL — when batch adds/modifies DB schema)

When the batch changes the DB schema (new tables, columns, constraints), include this:

```markdown
### Schema JSON Sync

After the Alembic migration runs and all tests pass, update the master JSON schema file (`dev-docs/db-design/pilot-db-schema-v2.6h.json`) via the path-based CRUD tool [`backend/schema_manager.py`](schema_manager.py). Read [`backend/README-schema_manager.md`](README-schema_manager.md) for the full command reference before your first mutation.

**`schema_manager.py` uses dot-notation `--path` traversal — NOT positional `<table> <column> <type>` args.** The verbs are `get`, `set`, `delete`, `array-append`, `array-remove`, `array-update`. Values come from `--value` (simple scalars/arrays as a JSON string) or `--payload <file.json>` (dicts/complex objects — always prefer a temp file to avoid CLI quote-escaping).

```bash
cd <repo>/backend

# 1. Inspect current state first (path is dot-notation into the JSON tree):
python schema_manager.py get --path tables.job.columns

# 2. Add/overwrite a column — write the payload to a temp file, then set by path:
cat << 'EOF' > temp_payload.json
{ "type": "text", "nullable": true, "description": "Optional external integration ID." }
EOF
python schema_manager.py set --path tables.job.columns.external_id --payload temp_payload.json

# 3. Append to an array (index / FK / constraint / trigger / seed_row):
python schema_manager.py array-append --path tables.job.check_constraints --payload temp_payload.json

# 4. Clean up the temp file:
rm temp_payload.json
```

Path levels: root (`version`, `functions`, `design_decisions`, `tables`) → table (`tables.job`) → column (`tables.job.columns.status`) → arrays (`tables.job.indexes`, `.foreign_keys`, `.check_constraints`, `.exclusion_constraints`, `.triggers`, `.seed_rows`).

**NEVER edit the JSON with `sed`, `awk`, `grep`, or inline Python — line-based editing corrupts the JSON and has cost hours of manual repair.** If `schema_manager.py` errors:
1. **STOP immediately**
2. **Ask Tom** — quote the exact command and the exact error
3. Do NOT proceed with manual edits or workarounds

> ⚠️ There is no `--sync` or `--diff` flag. This is a manual path-based mutator, not an autogenerator — every schema change must be applied deliberately, one path at a time.
```

---

## 8. OpenAPI Regeneration (CONDITIONAL — when batch adds/modifies endpoints)

When the batch adds or modifies any API endpoint:

```markdown
### Regenerate OpenAPI

After all tests pass (and after the changed-files ruff gate — see §21):

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
```

This generates **two files** with different audiences:
- `backend/openapi.json` — machine-readable spec, consumed by frontend `pnpm sync-api-types` to generate TypeScript types
- `backend/openapi_schema_map.md` — human/agent-readable endpoint summary, consumed by the React Engineer agent as the primary endpoint reference

Verify new endpoints appear in the human-readable map:
```bash
grep -A 5 "your-new-endpoint-path" backend/openapi_schema_map.md
```
```

---

## 9. DB Model Map Regeneration (CONDITIONAL — when batch adds/modifies models)

When the batch adds or modifies any SQLModel class:

```markdown
### Regenerate DB Model Map + Import Map

Both scripts write to **stdout** and must be redirected to their target file (per rules §2.1–§2.2). They do NOT edit the file in place.

After any `app/models/*.py` change — regenerate `db_models_map.md`:
```bash
cd <repo>/backend && source .venv/bin/activate
python generate_db_model_map.py app > db_models_map.md
```

After adding ANY new test file — regenerate `app_model_imports.md` (the deduplicated model-import list the React Engineer and future prompts rely on):
```bash
python generate_app_import_map.py tests > app_model_imports.md
```

Verify the new model appears under **DB Tables** (not Enums/Schemas/Helpers):
```bash
grep "YourModelName" backend/db_models_map.md
```

> The `app` / `tests` positional arg is the directory to scan. Omitting it defaults to `.` (model map) or `tests` (import map) — always pass the arg explicitly so the output is complete.
```

---

## 10. Mutation Endpoint Audit Context (CONDITIONAL — when batch adds mutation endpoints)

When the batch adds any `POST`, `PATCH`, `PUT`, or `DELETE` endpoint that performs DB writes with an authenticated user context:

```markdown
### Audit Context Requirement

Every mutation endpoint MUST call `set_audit_context_sync()` before the first `db.add()` or `db.commit()`. This sets the PostgreSQL session variable that the `audit_log` trigger reads to record the actor.

```python
from core.db import get_db, set_audit_context_sync

@router.post("/resource")
def create_resource(
    ...,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    # REQUIRED: set audit context before any DB write
    set_audit_context_sync(db, user_id=current_user.id)
    
    # Now proceed with DB writes
    resource = Resource(tenant_id=current_user.tenant_id, ...)
    db.add(resource)
    db.commit()
    ...
```

**Without this call, `actor_id` is NULL in `audit_log` for this operation** — silent audit attribution loss that is hard to detect in testing but violates the audit trail requirement.
```

---

## 11. New Entity `/test` Endpoint Pattern (CONDITIONAL — when batch adds a new entity type)

When the batch adds a new entity (new DB table + CRUD routes), a corresponding unauthenticated `/test` endpoint MUST be added so the test suite can create seed data via the `client` fixture.

```markdown
### `/test` Endpoint Pattern

Every new entity with a `POST` create endpoint MUST have a corresponding unauthenticated `/test` counterpart. The test suite uses `/api/v1/[entity]/test` to create data without JWT auth — without this, test helpers cannot seed the entity.

**Standard pattern** (use `TestUserContext` from `core.test_context`):

```python
from core.test_context import TestUserContext, get_test_context

def _create_[entity]_impl(
    entity_in: [Entity]Create,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
) -> [Entity]:
    """Shared creation logic — called by both authenticated and test endpoints."""
    entity = [Entity](
        tenant_id=user_context.tenant_id,
        ...
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


@router.post("/[entity]", response_model=[Entity]Response, status_code=201)
def create_[entity](
    entity_in: [Entity]Create,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    set_audit_context_sync(db, user_id=current_user.id)
    return _create_[entity]_impl(entity_in, db, current_user)


@router.post("/[entity]/test", response_model=[Entity]Response, status_code=201)
def create_[entity]_test(
    entity_in: [Entity]Create,
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
):
    """Test-only endpoint — bypasses JWT, uses canonical test tenant context."""
    return _create_[entity]_impl(entity_in, db, ctx)
```

Read an existing route file (e.g., `api/routes/quotes.py`) to see the full established pattern before implementing.
```

---

## 12. Celery Task Structure (CONDITIONAL — when batch adds a Celery background task)

When the batch adds a new Celery background task in `backend/tasks/`:

```markdown
### Celery Task Structure

All Celery tasks MUST follow the two-layer pattern — separating the business logic from the Celery entry point so the logic can be unit tested without a running worker:

```python
# backend/tasks/[task_name].py

from core.celery_app import celery_app
from core.db import get_db
from sqlmodel import Session

def _[task_name]_impl(param: str, db: Session) -> dict:
    """
    Pure business logic — accepts an injected Session.
    This is the testable layer.
    """
    # ... logic here
    return {"result": "..."}


@celery_app.task
def [task_name](param: str) -> dict:
    """
    Celery entry point — creates its own session, calls _impl.
    Do not put business logic here.
    """
    with next(get_db()) as db:
        return _[task_name]_impl(param, db)
```

**Testing the task**: test `_[task_name]_impl()` directly with the `db_session` fixture — never call `.delay()` or `.apply()` in unit tests.

Reference: `backend/tasks/profitability_rollup.py` for the established pattern.
```

---

## 13. RFC 7807 Error Response Standard (REQUIRED awareness — applies to all endpoint changes)

This is not a conditional section — it is a standing requirement for ALL endpoints. Include it in the MANDATORY STOP critical rules whenever the batch touches error responses or adds new endpoints.

```markdown
### RFC 7807 Error Format

All API error responses MUST use RFC 7807 Problem Details format. The frontend `apiClient` parses this format to drive severity routing in `<NotificationBanner>`.

```python
# ✅ REQUIRED — RFC 7807 shape
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={
        "type": "https://errors.pilotfortrades.com/not-found",
        "title": "Resource not found",
        "status": 404,
        "detail": f"Quote {quote_id} does not exist in this tenant.",
    },
)

# ❌ BANNED — plain string detail
raise HTTPException(status_code=404, detail="Not found")
```

Return `404` (not `403`) when a tenant-scoped record is not found — prevents UUID enumeration attacks (never reveal whether a record exists in another tenant).
```

---

## 14. Final Verification Gate (REQUIRED)

Every prompt MUST end with a two-phase final verification block. **Unit tests run first (fast, during development). The full suite runs only once, at the end, before DoD sign-off — with the slow vendor/live-service suites excluded by default** (Tom's standing instruction, 2026-08-16: `integration`, `e2e`, `requires_telnyx`, `requires_stripe`, `requires_sendgrid`, `requires_redis` add 9+ minutes and hit vendor/test-mode APIs; include them only when the batch modifies the code they cover).

```markdown
## Final Verification

### Phase 1 — Unit Tests Only (run after each task group during development)

```bash
cd <repo>/backend
source .venv/bin/activate

# Unit tests only — fast feedback loop during implementation
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before moving to the next task. Fix any unit failure — including failures that appear to be caused by code outside your batch — before proceeding.

### Phase 2 — Lint (changed files only) + Full Suite, Vendor-Deselected (run once, at the very end, before DoD sign-off)

```bash
cd <repo>/backend
source .venv/bin/activate

# Lint + format gate (rules §23) — CHANGED FILES ONLY, not the whole codebase
# Get the Python files changed this session (staged + unstaged vs HEAD; excludes deletions)
# The sed strips the "backend/" prefix because git diff returns repo-root-relative paths
# but ruff runs from inside backend/ and needs backend/-relative paths
CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')

if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY     # lint + isort (I) + pyupgrade (UP) autofix
    ruff format $CHANGED_PY          # format (line-length 88)
    ruff check $CHANGED_PY           # re-check: any remaining errors need manual fixing
fi

# Full suite — vendor/live-service suites deselected (Tom's standing instruction 2026-08-16;
# they add 9+ min: Telnyx/Stripe/SendGrid vendor APIs, Redis-dependent, e2e).
# All six markers are registered in backend/pytest.ini; conftest auto-marks vendor tests
# with `integration`, so this expression is doubly safe under --strict-markers.
python -m pytest -m "not integration and not requires_telnyx and not requires_stripe and not requires_sendgrid and not requires_redis and not e2e" --tb=short -q 2>&1 | tail -15

# Vendor-suite inclusion rule: if this batch modified code those suites cover
# (services/telnyx*, Stripe billing/webhooks, SendGrid dispatch, Redis-dependent modules),
# ALSO run the affected marker suite(s) before sign-off — e.g.:
#   python -m pytest -m requires_telnyx --tb=short -q 2>&1 | tail -10
# (may need vendor env vars — coordinate with Tom) and record the result in the Completion Summary.
# State the inclusion call explicitly in every prompt's Phase 2 block.

# Batch-specific spot checks
python -m pytest tests/domains/your_domain/ -v 2>&1 | tail -20
grep -A 5 "your-endpoint" backend/openapi_schema_map.md

echo "=== [BATCH-NAME] FINAL VERIFICATION COMPLETE ==="
```

> **Warning-clean is part of done.** `ruff` must report no remaining issues **in your changed files** (no unjustified `# noqa`), and the pytest run must be free of `DeprecationWarning` noise (see Rule 10 — use `HTTP_422_UNPROCESSABLE_CONTENT`; and Rule 13 — no Pydantic v1 carryover). **Do not run `ruff check .` against the entire codebase** — it surfaces hundreds of pre-existing unrelated errors. Scope to changed files only (rules §23).

> **Any failure in either phase — unit or the vendor-deselected full suite — must be fixed before the batch is declared done.** There is no "pre-existing failure" exception without explicit written confirmation from Tom. If you cannot identify the root cause of a failing test → STOP and ask Tom before proceeding.
```

---

## 15. Definition of Done Checklist (REQUIRED)

Every prompt MUST include a Definition of Done checklist with individual checkboxes. The checklist must:
- Start with baseline capture
- Include all MCP pre-work verification items
- List every file created or modified
- Include all test file items
- Show BOTH the unit-only pass and the full-suite pass as separate required items
- End with final test count delta and completion summary instruction

```markdown
## Definition of Done

Check off each item **in this prompt doc** as it completes:

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work (or confirmed with Tom)
- [ ] All MCP pre-work queries run — [specific result confirmed] (every touched table verified via `information_schema.columns`, rules §25)
- [ ] All mandatory source files read before writing any code (including `api/schemas/[domain].py`)
- [ ] [Specific implementation item 1]
- [ ] [Specific implementation item 2]
- [ ] All DB-touching routes/`_impl()` are sync `def` — no `async def` on the blocking `Session` (rules §21)
- [ ] Only Pydantic v2 idioms used; every new route has `response_model`; money is integer cents (rules §22)
- [ ] New tables inherit the correct mixin (`StandardAuditMixin`/`AppendOnlyMixin`/`MachineLogMixin`) + explicit `tenant_id`; no hand-rolled timestamps (rules §24)
- [ ] `set_audit_context_sync()` called at the start of every new mutation endpoint (if endpoints added)
- [ ] All new API errors follow RFC 7807 Problem Details format
- [ ] All new test files use `pytestmark` with domain marker + `pytest.mark.unit`
- [ ] No module-level `TestClient` in any test file
- [ ] All new tests use `test_tenant` and `test_user` fixtures (no hardcoded UUIDs)
- [ ] Autouse fixture opt-outs applied where needed (`skip_mock_entitlement_allowed`, `requires_ollama`, `requires_whisper`)
- [ ] `python generate_db_model_map.py app > db_models_map.md` run (if models changed) and `python generate_app_import_map.py tests > app_model_imports.md` run (if new test files added)
- [ ] `schema_manager.py` used (path-based `--path`/`--payload`) for any JSON schema change — never edited directly (if schema changed)
- [ ] `python export_openapi_json.py` run — `openapi.json` and `openapi_schema_map.md` updated (if endpoints changed)
- [ ] `ruff check --fix && ruff format` run **on changed files only** (`git diff --name-only HEAD -- '*.py'`) — zero remaining issues in those files (including pre-existing errors), no unjustified `# noqa` (rules §23)
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures including any pre-existing
- [ ] **Phase 2**: Full suite (vendor-deselected) passes — `pytest -m "not integration and not requires_telnyx and not requires_stripe and not requires_sendgrid and not requires_redis and not e2e"` — zero failures, warning-clean; affected vendor marker suites run + recorded if the batch touched Telnyx/Stripe/SendGrid/Redis-covered code
- [ ] Final test count (before → after) documented
- [ ] Completion Summary filled in at this prompt doc's ending `## Appendix — Completion Summary` (ADR-0017 — never the launch plan)
- [ ] Source spec task headers updated to ✅ Complete in any spec doc other than the launch plan (README-seed-data.md §10, FIND doc, traceability catalog, etc.) — if applicable
```

---

## 16. Completion Summary Instruction (REQUIRED)

Every prompt MUST end with an empty `## Appendix — Completion Summary` section and MUST instruct the engineer to fill it in after finishing (ADR-0017). **The prompt doc is the permanent detail record of the work.** The Architect updates the launch plan status-only on close — never instruct the engineer to write summaries into the launch plan or any impl plan.

> **Source spec update rule (MANDATORY)**: If this batch closes tasks that are listed in a source spec document other than `pilot-launch-plan.md` (e.g., `README-seed-data.md` §10, a FIND design doc, a traceability catalog), the Completion Summary step MUST also update that source spec's task header to ✅ Complete with a one-line summary. Any spec file that has a `☐` or "Awaiting implementation" task header must be updated when the batch closes. Failure to do this is the same class of maintenance gap as skipping the Completion Summary appendix.

```markdown
## Completion Summary

After all Definition of Done items are complete:

1. Fill in the **Completion Summary** in the appendix at the end of THIS prompt doc using the format below.
2. **If this batch closes tasks tracked in another source spec** (e.g., `README-seed-data.md` §10 task headers, a FIND design doc, a traceability catalog entry), update those source spec task headers to ✅ Complete with a one-line summary BEFORE declaring the batch done.

```markdown
### [BATCH-NAME] — [Short Description]: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- [Brief description of key change 1]
- [Brief description of key change 2]
- [Root cause analysis if a bug was fixed]

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/path/to/file.py` | Created / Updated — [what changed] |
| ... | ... |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/domain/test_file.py` | `domain_name` | N | ✅ |
```
```

---

## 17. Complete Prompt Header Block (REQUIRED)

Every prompt must start with a consistent header block:

```markdown
# Implementation Prompt: [BATCH-CODE] — [Descriptive Name]

**Mode**: Pilot Python Engineer  
**Batch**: [BATCH-CODE]  
**Source plan**: [`dev-docs/analysis/[plan-file].md`](link) §[section]  
**Design doc**: [`dev-docs/architecture-design/batch-designs/[design-file].md`](link)  ← omit if no design doc
**Estimated session**: [X–Y hours]  
**Platform**: Backend only (`backend/`)  
**Frontend companion**: [Batch name that depends on this] ← omit if none
```

---

## 18. Standard `postgres-local` MCP Usage Note (REQUIRED)

Include this note once in the Pre-Work section to remind the engineer of MCP behavior:

```markdown
> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Use it to confirm table names, column types, and existing data. Never use it to INSERT, UPDATE, or DELETE — all data changes go through the application code, seed scripts, or Alembic migrations. If a query fails or returns an error → STOP and ask Tom before proceeding.
>
> **Two read-only MCP servers exist** (global rule `.roo/rules/02-database-mcp-access.md`): **`postgres-local`** is the default for all verification. **`postgres-prod`** reads production but **requires an SSH tunnel that only Tom controls** — ask Tom to confirm the tunnel is up before your first `postgres-prod` query, and STOP on any connection error (the tunnel is down). Only use `postgres-prod` when the batch is explicitly about production state.
```

> **Authoring note**: nearly all backend batches verify against `postgres-local` only. Do NOT put `postgres-prod` queries in a prompt unless the batch is explicitly about prod drift/incident — and when you do, the prompt must instruct the engineer to ask Tom to confirm the SSH tunnel first.

---

## Quick Reference: Section Order for a Standard Prompt

Use this ordering for every Python Engineer prompt:

```
1. Header block (mode, batch, plan link, estimate)
2. ⚠️ MANDATORY STOP (rules reference + batch-specific critical rules from §1)
3. Pre-Work: Establish Regression Baseline (unit tests only; fix any failures before proceeding)
4. Pre-Work: Run MCP Verification Queries
5. Pre-Work: Read These Source Files (include api/schemas/ files where relevant)
6. Background / Context (what this batch does and why)
7. Task 1 — [Name]
   - What to change
   - Code examples
   - Intermediate unit test run: `pytest -m unit --tb=short -q | tail -5`
8. Task 2 — [Name]  ...repeat...
9. Verification Checkpoints (after critical task groups — always unit tests only)
10. Regeneration + Schema steps (db_models_map.md / app_model_imports.md / schema_manager.py / export_openapi_json.py — whichever apply)
11. Final Verification Gate: Phase 1 (unit) → Phase 2 (ruff + full suite)
12. Test Requirements (if new code added — including autouse fixture opt-outs)
13. Definition of Done checklist (Phase 1 and Phase 2 as separate items)
14. Completion Summary and Details format + instruction
15. "After This Task — Next Step" pointer
```

---

## Anti-Patterns — Never Do These in a Python Engineer Prompt

| Anti-Pattern | Correct Approach |
|---|---|
| Omit the regression baseline | Always capture `pytest -m unit --tb=no -q | tail -5` before any work |
| Allow pre-existing failures to remain | Any failure must be fixed or explicitly confirmed with Tom before proceeding |
| Run integration/vendor tests during development | Use `-m unit` during iteration; the final Phase 2 gate runs the full suite **vendor-deselected** (`-m "not integration and not requires_telnyx and not requires_stripe and not requires_sendgrid and not requires_redis and not e2e"`); vendor marker suites run only when the batch touches the code they cover |
| Skip MCP pre-work queries | Always verify column names and table state before writing SQL |
| Skip the `read_file` mandatory reads | Always list every file to read — including `api/schemas/[domain].py` |
| Allow autogenerate for Alembic migrations | Always use `alembic revision -m "name"` (blank) + raw `op.execute()` |
| Omit `downgrade()` in a migration | Always implement the exact reverse of `upgrade()` |
| Use `db.get()` on tenant-scoped models | Always use `select()` with tenant_id scope |
| Use module-level `TestClient` | Always use the `client` fixture |
| Count all tenant rows in a test assertion | Always scope by inserted IDs — seed data is always present |
| Hardcode UUIDs like `...0001` in tests | Always use `test_tenant` / `test_user` fixtures |
| Skip OpenAPI regeneration after endpoint changes | Always run `python export_openapi_json.py` |
| Skip schema_manager.py after DB schema changes | Always use the path-based CRUD verbs (`get`/`set`/`delete`/`array-append`/`array-remove`/`array-update`) with `--path` + `--value`/`--payload`. There is NO `--sync`, `--diff`, or positional `<table> <column> <type>` form. Never edit the JSON with `sed`/`awk`/inline Python. |
| Redirect regen scripts wrong (or omit the dir arg) | `generate_db_model_map.py app > db_models_map.md` and `generate_app_import_map.py tests > app_model_imports.md` — both print to stdout and need the redirect **and** the explicit dir arg |
| Convert a DB-touching route to `async def` | Keep it sync `def` (rules §21) — FastAPI threadpools `def` routes; `async def` + blocking `Session` stalls the event loop |
| Use Pydantic v1 carryover (`class Config`, `@validator`, `.dict()`) | Use v2 (`model_config = ConfigDict`, `@field_validator`, `.model_dump()`) — v1 emits warnings that pollute the run (rules §22) |
| Hand-declare `created_at`/`updated_at` on a new table | Inherit the correct mixin from `app/models/mixins.py`; add `tenant_id` explicitly (rules §24) |
| Run `ruff check .` against the whole codebase | Scope ruff to **changed files only** (`git diff --name-only --diff-filter=d HEAD -- '*.py' \| sed 's\|^backend/\|\|'`); fix ALL errors in those files including pre-existing ones (rules §23). The `sed` strips the `backend/` prefix because `git diff` returns repo-root-relative paths but ruff runs from inside `backend/`. |
| Encounter F401 errors on barrel-export `__init__.py` files | These are **already handled** via `per-file-ignores` in `pyproject.toml` (`"app/models/__init__.py" = ["F401"]`, etc.). If you add a new import to `app/models/__init__.py`, the F401 on your line is expected and suppressed by the config — do not add `# noqa` comments. If you create a **new** barrel-export `__init__.py`, add it to `[tool.ruff.lint.per-file-ignores]` in `pyproject.toml` with `["F401"]`. |
| Assume a column name from memory | Query `information_schema.columns` for every table this session — 193 tables exist (rules §25) |
| Omit `set_audit_context_sync()` on mutation endpoints | Always call it before the first `db.add()` / `db.commit()` |
| Use plain string `detail` in `HTTPException` | Always use RFC 7807 Problem Details dict |
| Write `require_permission()` without `feature_code` for tier-gated features | Always add `feature_code` for subscription-tier-gated endpoints |
| Write a new entity without a `/test` counterpart | Always add the unauthenticated `/test` endpoint using `TestUserContext` |
| Write a Celery task with business logic in the entry point | Always split into `_impl(param, db)` + `@celery_app.task` wrapper |
| Forget autouse fixture opt-outs in entitlement / AI tests | Always add `skip_mock_entitlement_allowed` / `requires_ollama` / `requires_whisper` where needed |
| End without a Completion Summary appendix + instruction | Always end the prompt with the empty `## Appendix — Completion Summary` and instruct the engineer to fill it in (ADR-0017) |
| Assume `payment.refunded_amount_cents` column exists | That column was intentionally dropped by migration `44b8d8f15789`. The SD-2 refund model uses a new negative-amount payment row (`amount_cents < 0`, `status = refunded`). Never re-add the dropped column without Tom approval. |
| Use `second_tenant` and assume it's empty | `second_tenant` is only empty if no other test has inserted into it in the same session. Always use explicit FK-scoped assertions, never total row counts. |

---

## 19. Platform Operations + Pricing Master — Prompt-Level Callout (CONDITIONAL — billing/subscription batches)

When a batch touches subscription tier logic, entitlement gates, billing intervals, or notification dispatch, include this callout in the MANDATORY STOP section:

```markdown
**Before writing any subscription, billing, or entitlement code:**
Read `dev-docs/product-requirements/mvp-prd.md` _(private)_ **§3.11 (Pricing Table — the master subscription/pricing definition)** and `dev-docs/pilot-operations.md` _(private)_ — covers: tier→plan→ppfv cascade, `is_billing_active` paywall gate, Charter cohort Stripe schedule, notification template resolution order, and all 6 subscription status codes. The billing logic is NOT inferrable from the schema alone.

**Phantom-gate rule (python-engineer-rules §17/§18)**: never wire a `feature_code=` gate for a feature the PRD §3.11 table marks unlimited (users, jobs, quotes, invoices, customers, QB syncs, emails, calendar syncs). A gate requires BOTH a PRD pricing line AND seeded `product_feature` + ppfv rows — a wiring without both is a phantom gate: remove it, don't seed around it. Never invent plan names, prices, limits, enforcement modes, or overage rates; if a value is missing from the master → STOP and ask Tom.
```

When a batch touches the `payment` table, include this callout:

```markdown
**Payment refund model (SD-2 permanent design):**
Refunds = new negative-amount payment row (`amount_cents < 0`, `status = refunded`). The `payment.refunded_amount_cents` / `payment.refunded_at` columns were deliberately dropped by migration `44b8d8f15789`. Do NOT add them back. Do NOT query for them in MCP checks.
```

---

## 20. Seed Data Rollout (REQUIRED — any batch that adds/changes ANY data in the DB)

**⚠️ MANDATORY (Tom, 2026-08-06): Any batch that adds or modifies ANY data in the database — whether a new column, new table, new lookup/reference rows, new enum-like value set, new seed rows in a migration, or changes to existing seed data — MUST include a Seed Data Rollout section.** This is not optional. A prompt that adds DB data without a seed-rollout section is **incomplete and must not be authored or issued.**

**Standing rule (Tom, 2026-07-27): every schema change must roll into BOTH the core/platform seed AND the scenario seeds.** A new column, lookup table, or CHECK-constrained value set is not "done" when the migration lands — it is done when the seed system produces realistic data for it. A prompt that adds schema without a seed-rollout section is incomplete.

When a batch adds or modifies any DB column, lookup/reference table, enum-like value set, or seed data in a migration, the prompt MUST include a **Seed Data Rollout** section covering both layers:

```markdown
## Seed Data Rollout (Core + Scenario)

Per [`backend/README-seed-data.md`](README-seed-data.md) — read §3 (Group A–D model), §6 (run order), and §7 (DELETE safety rule) before editing any seed script.

### Layer 1 — Core / Platform values (Group A / B)
- **New lookup / reference table or platform-default rows** → add to [`seed_core.py`](migrations/scripts/seed_core.py) (Group A) or [`seed_platform.py`](migrations/scripts/seed_platform.py) (Group B), idempotent (`INSERT … ON CONFLICT DO NOTHING`), and update the script's `seed`, `show`, and `inspect` modes.
- If the Alembic migration also seeds these rows (so a fresh `alembic upgrade` is complete), the migration INSERT and the `seed_core.py` INSERT MUST produce **identical rows** (`seed_core.py` is the post-schema-restore recovery path). `StandardAuditMixin` tables need explicit `created_at, updated_at = NOW(), NOW()`.

### Layer 2 — Scenario data (Group D)
- **Every new column on an entity that scenarios already seed** (`customer`, `site`, `job`, `quote`, `invoice`, etc.) MUST be populated with realistic, varied values in the relevant `seed_scenario_*.py` script(s) so the UI/filters have data to exercise. Non-uniform values (not all rows the same) where the field drives a filter or display.
- Look up FK values by business key at runtime — **never hardcode a `gen_random_uuid()`-generated scenario UUID** (README §7 pricebook rule).
- Scenario assignment is `UPDATE` on rows the script already owns — idempotent, value-scoped, follows the DELETE-safety rule (README §7 — `mode_seed` DELETEs must include the full business key).

### Verification
- After seeding: `python migrations/scripts/seed_core.py --mode inspect` (core rows present) + confirm the affected scenario endpoint/board returns the new field with varied values.
- Run `pytest -m unit` after the seed change — a seed row a test doesn't expect will break tests (README §7 "shared DB" rule). Fix any seed-resilience failures (assert-by-ID, never by count).

### README update
- Update [`backend/README-seed-data.md`](README-seed-data.md) §4 (Current Seed State) with the new rows/fields and mark the batch in §10 if it closes a tracked task.
```

Include the Layer 1 subsection only when the batch adds core/platform values; include Layer 2 whenever the batch adds a column to an entity that scenario scripts seed. Most schema batches need both.

---

## 21. Ruff + Modern-Python Standards (REQUIRED awareness — every backend batch)

Reflects rules §22–§23. Include the lint/format step in every prompt's Phase 2 gate; call out the idioms below whenever the batch writes new schemas, models, or type hints.

```markdown
### Lint, Format & Modern-Python Idioms (rules §22–§23)

Before declaring done, run the Ruff gate from `backend/` — **changed files only, never the whole codebase**:

```bash
cd <repo>/backend && source .venv/bin/activate

# Get the Python files you changed this session (staged + unstaged vs HEAD; excludes deletions)
# The sed strips the "backend/" prefix because git diff returns repo-root-relative paths
# but ruff runs from inside backend/ and needs backend/-relative paths
CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')

if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY     # lint + isort (I) + pyupgrade (UP) autofix
    ruff format $CHANGED_PY          # format (line-length 88)
    ruff check $CHANGED_PY           # re-check: any remaining errors need manual fixing
fi
```

Ruff 0.15 config (in `pyproject.toml`): `target-version = "py311"`, rule sets `E,W,F,I,B,UP,N,C4,RUF`, first-party = `app, core, services, tasks, api`.

**Changed-files-only + fix-all-errors policy (rules §23)**:
- **Scope ruff to changed files only** — do NOT run `ruff check .` against the entire codebase. The codebase has pre-existing lint issues across many unrelated files; running the whole tree surfaces hundreds of unrelated errors and is counterproductive.
- **Fix ALL errors in your changed files** — including pre-existing errors on lines you did not modify. `ruff check --fix` auto-fixes many issues; fix the rest manually. If a pre-existing error requires a risky or out-of-scope refactor → STOP and ask Tom.
- **Iterative cleanup philosophy**: Each batch cleans the files it touches. Over time, the entire codebase converges on zero ruff violations without any single batch bearing the burden of a global cleanup.

- **Do NOT hand-order imports** — `I` (isort) sorts them; `ruff check --fix` does it for you.
- **Modern typing only** (`UP`): `str | None` not `Optional[str]`; `list[X]` not `List[X]`; `dict[K, V]` not `Dict`. Pair with `from datetime import UTC, datetime` (Rule 7).
- **No unjustified `# noqa`** — if you must suppress a rule, add a one-line reason. Do not expand the `pyproject.toml` ignore list without Tom's approval (`B008` for `Depends()` is already intentionally ignored).
- **Pydantic v2 only** (rules §22): `model_config = ConfigDict(...)`, `@field_validator`/`@model_validator`, `.model_dump()`/`.model_validate()`. Never `class Config`, `@validator`, `.dict()`, `.parse_obj()`.
- **`response_model` on every route**; **money is integer cents** — never a float column, never float arithmetic on money.
```

---

## 22. Sync-by-Design Callout (CONDITIONAL — batch adds/modifies routes, services, or Celery tasks)

When a batch writes any new route, `_impl()`, or service function, include this callout so the engineer does not "modernize" to `async def` (rules §21):

```markdown
### Sync-by-Design (rules §21)

This app is **synchronous by design**: FastAPI 0.135 runs plain `def` routes in a threadpool, and the SQLModel/SQLAlchemy 2.0 `Session` is the **blocking** psycopg2 driver.

- Every route/`_impl()`/service that touches the `Session` MUST be `def` (sync). Verify against a neighbor file (e.g. `api/routes/customers.py`) — all are `def`.
- Only use `async def` for a handler that *exclusively* `await`s genuinely non-blocking I/O (e.g. an `httpx.AsyncClient` call to Stripe/QuickBooks) and never touches the sync `Session`.
- Mixing `async def` with the blocking `Session` runs psycopg2 on the event loop and stalls **all** requests — the single most damaging concurrency mistake in this stack. When in doubt → `def`.
```
