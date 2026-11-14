# Implementation Prompt: C-B15 (Part A) — Tenant Impersonation Backend

**Mode**: Pilot Python Engineer
**Batch**: C-B15 (Part A — Backend)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` row 14v
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-c-b15-design.md` — read §C Part A, §D, §F, §G before starting
**Estimated session**: 3–4 hours
**Platform**: Backend only (`backend/`)
**Frontend companion**: C-B15 Part B (React Engineer) — depends on this batch's OpenAPI regen; **runs only after the C-B15 UI design spec is Tom-approved**

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, fixture rules
- **`dev-docs/architecture-design/batch-designs/batch-c-b15-design.md`** — the authoritative design; endpoint contracts in §D are binding

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 3**: After any endpoint change → run `python export_openapi_json.py` (updates both `openapi.json` and `openapi_schema_map.md`).
- **Rule 5**: Never use module-level `TestClient` in any test file. Always use the `client` fixture from `conftest.py`.
- **Rule 6**: `db.get()` is permanently banned on tenant-scoped models. Always use tenant-scoped `select()`. The `list_operator_tenants` service is a **sanctioned cross-tenant platform read** (same class as `cohort_dashboard.get_cohort_overview()`) — it is the ONLY query in this batch without a `tenant_id` filter.
- **Rule 7**: `postgres-local` MCP is **read-only verification only** — never INSERT/UPDATE/DELETE via MCP.
- **Rule 8**: All API error responses MUST follow RFC 7807 Problem Details format. Non-standard error shapes break the frontend `<NotificationBanner>` severity routing.
- **Rule 11**: If ANY test fails during your work — even one that appears pre-existing — you must fix it before declaring the batch done. No "not my fault" exception.
- **Rule 12 (sync routes — rules §21)**: Every DB-touching route and `_impl()` is a plain `def`. Never `async def` with the blocking `Session`.
- **Rule 13 (Pydantic v2 — rules §22)**: v2 idioms only (`model_config = ConfigDict`, `.model_dump()`). Every route needs `response_model`.
- **Rule 14 (Ruff — rules §23)**: Run ruff on **changed files only** (`git diff --name-only HEAD -- '*.py'`); fix ALL errors in those files, including pre-existing ones.
- **Rule 16 (verify, don't assume — rules §25)**: 186+ tables exist. Query `information_schema.columns` for every table you touch this session before writing SQL.

### Security invariants for this batch (binding — from design §D.4)

1. `X-Impersonate-Tenant` is **silently ignored** for tenant users (normal context returned). Only platform users can activate it.
2. Platform user without the header → existing 403 unchanged.
3. Platform user with header but `impersonate_tenant=false` (accountant role) → 403 RFC 7807.
4. Target tenant must exist and be `is_active=true` → 404 (not found) / 409 (inactive).
5. Impersonated context is always `role_code='owner'` with the owner role's permission list from `tenant_user_role` — never synthetic super-permissions.
6. Every mutation performed under impersonation writes an `audit.event` row (`actor_type='platform'`).

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed anyway. Either (a) confirm with Tom that this is a known, accepted failure, or (b) fix the failure before touching any batch files.

## Pre-Work: Run MCP Verification Queries

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. If a query fails or returns an error → STOP and ask Tom before proceeding. Two read-only MCP servers exist (global rule `.roo/rules/02-database-mcp-access.md`): `postgres-local` is the default; `postgres-prod` requires Tom's SSH tunnel — not needed for this batch.

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

```sql
-- 1. Impersonation permission flags (expect: owner=true, support=true, accountant=false)
SELECT code, permissions -> 'impersonate_tenant' AS can_impersonate, is_active
FROM public.platform_role ORDER BY code;

-- 2. tenant columns used by the selector + impersonation target validation
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant'
  AND column_name IN ('id', 'name', 'is_active', 'current_subscription_tier_id', 'created_at')
ORDER BY ordinal_position;

-- 3. audit.event CHECK constraint allows actor_type='platform'
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conname = 'audit_event_actor_type_chk';

-- 4. audit.event full column list (you will INSERT into this table)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'audit' AND table_name = 'event'
ORDER BY ordinal_position;

-- 5. owner role permission payload (impersonated context uses this verbatim)
SELECT code, permissions FROM public.tenant_user_role WHERE code = 'owner';

-- 6. subscription columns for the tenant-list join
SELECT column_name, data_type FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'subscription'
  AND column_name IN ('tenant_id', 'status_id', 'is_active')
ORDER BY ordinal_position;

-- 7. user table platform columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'user'
  AND column_name IN ('id', 'email', 'is_active', 'is_platform_user', 'platform_role_code')
ORDER BY ordinal_position;
```

> **Engineer safety net — independent column verification (MANDATORY)**: Before writing ANY SQL statement or SQLModel field reference, run the `information_schema.columns` query for **every table you touch**. The prompt's column names were MCP-verified at authoring time, but the live DB is the only authoritative source. If a name mismatches → use the MCP-returned name and note the discrepancy in your Completion Summary.

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/core/auth.py                          ← PlatformUser, get_platform_user(), get_current_user() — you are modifying this file
backend/api/routes/cohort_dashboard.py        ← platform-endpoint patterns (get_platform_user, permission checks, RFC 7807 shapes, /auth/me)
backend/services/cohort_dashboard.py          ← sanctioned cross-tenant platform read pattern
backend/app/models/system.py                  ← AuditEvent model (lines ~681–720) — you will INSERT these rows
backend/api/schemas/cohort.py                 ← existing operator schema shapes (naming conventions)
backend/api/routes/roles.py                   ← /users/me/permissions — inherits your impersonation path automatically; confirm no change needed
backend/app/main.py                           ← router registration + middleware registration points
backend/tests/conftest.py                     ← fixtures: mock_cognito_jwt, test_tenant, test_user, second_tenant, tenant_a/tenant_b
backend/db_models_map.md                      ← confirm User / PlatformRole / TenantUserRole / AuditEvent model mappings
```

Also run:

```bash
grep -rn "get_platform_user\|PlatformUser" backend/ --include="*.py" -l
grep -rn "X-Impersonate-Tenant\|impersonate" backend/ --include="*.py" -l   # expect zero functional matches
```

---

## Background / Context

C-B11 shipped platform auth (`get_platform_user()`) and the operator cohort dashboard as a standalone page. C-B15 Part A adds **tenant impersonation**: a platform user whose `platform_role.permissions.impersonate_tenant == true` (owner, support — NOT accountant) can view and act in the app as any tenant's owner, for support and Charter cohort management. Every tenant-scoped endpoint must work unchanged under impersonation — which is why the impersonation path lives inside `get_current_user()` rather than in a parallel dependency. Impersonation sessions and all impersonated mutations are audit-logged to `audit.event` (spec §8: "Hidden Pilot operator routes, RBAC-gated to the operator role, audit-logged").

**No migration, no seed changes, no schema JSON changes in this batch** (design §B.1, §B.6 — verified). All required columns and the `impersonate_tenant` permission key already exist.

---

## Task 1 — `AuthenticatedUser.impersonator_user_id` + impersonation path in `get_current_user()`

**File**: `backend/core/auth.py`

1. Add to `AuthenticatedUser`:

```python
impersonator_user_id: uuid.UUID | None = None  # set when built via impersonation

@property
def is_impersonated(self) -> bool:
    return self.impersonator_user_id is not None
```

The default keeps every existing constructor call valid.

2. Add module constant `IMPERSONATE_TENANT_HEADER = "x-impersonate-tenant"` and a private helper `_try_impersonation(request, db, user) -> AuthenticatedUser | None` implementing design §F.1:

- Return `None` unless: header present, `user.is_platform_user`, `user.platform_role_code` set.
- Load `PlatformRole` (active). If missing/inactive → return `None` (falls through to the existing 403).
- If `permissions.get("impersonate_tenant")` is not `True` → raise 403 RFC 7807 (`https://errors.pilotfortrades.com/forbidden`, title "Impersonation not permitted").
- Parse the header as UUID; invalid → 400 RFC 7807.
- Load target `Tenant` by id (`select()`, not `db.get()`). Not found → 404 RFC 7807. `is_active=False` → 409 RFC 7807.
- Load `TenantUserRole` `code='owner'` (active) → permission list.
- Set `request.state.impersonator_user_id = user.id` and `request.state.tenant_id = tenant.id` (so downstream middleware + audit context see the impersonated tenant).
- Return `AuthenticatedUser(user=user, tenant_id=tenant.id, role_code="owner", permissions=owner_permissions, impersonator_user_id=user.id)`.

3. In `get_current_user()`, replace the bare 403 at the no-`tenant_user` branch (currently lines ~245–249) with: call `_try_impersonation(...)`; if it returns a context, return it (after the same `request.state` assignments the normal path makes); otherwise raise the existing 403 unchanged.

Intermediate check: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5` — no regressions (nothing calls the new path yet).

## Task 2 — `services/impersonation_service.py` (NEW)

Per design §F.2. Sync `def` functions, injected `Session`:

- `list_operator_tenants(db) -> list[OperatorTenantSummary]` — all tenants, active first then `name` ASC. LEFT JOIN current `subscription` (tenant's active row) → `subscription_status.code`; LEFT JOIN `subscription_tier` on `tenant.current_subscription_tier_id` → `tier_name`. Nullable both.
- `log_impersonation_event(db, *, tenant_id, impersonator_user_id, action, context=None) -> None` — INSERT one `AuditEvent` row: `occurred_at=now (UTC-aware)`, `tenant_id=tenant_id`, `user_id=impersonator_user_id`, `actor_type='platform'`, `user_role=<platform_role_code>`, `entity_name='impersonation'`, `entity_id=str(tenant_id)`, `action=action` (`'start'`/`'end'`/`'request'`), `contextdata=context`. `db.add()` + `db.flush()` — caller commits.
- `start_impersonation(db, *, tenant_id, platform_user) -> ImpersonationSessionResponse` — validate tenant (404/409 as above), call `log_impersonation_event(..., action='start')`, commit, return session payload (`started_at` = `safe_now_utc()`).
- `end_impersonation(db, *, tenant_id, platform_user) -> dict` — call `log_impersonation_event(..., action='end')`, commit, return `{"ended": True}`. Never 404s on a missing prior start row (design §D.3).

## Task 3 — Schemas: `api/schemas/operator.py` (NEW)

Pydantic v2, `ConfigDict`, every field typed:

- `OperatorTenantSummary`: `tenant_id: UUID`, `name: str`, `is_active: bool`, `tier_name: str | None`, `subscription_status: str | None`, `created_at: datetime`
- `OperatorTenantListResponse`: `tenants: list[OperatorTenantSummary]`
- `ImpersonationStartRequest`: `tenant_id: UUID`
- `ImpersonationEndRequest`: `tenant_id: UUID`
- `ImpersonationSessionResponse`: `tenant_id: UUID`, `tenant_name: str`, `impersonator_user_id: UUID`, `role_code: str`, `started_at: datetime`

## Task 4 — Routes: `api/routes/operator_tenants.py` (NEW)

Router: `APIRouter(prefix="/api/v1/operator", tags=["operator"])`. All sync `def`, all `Depends(get_platform_user)`, all errors RFC 7807.

| Endpoint | Permission gate | Behavior |
|---|---|---|
| `GET /tenants` | `platform_user.can_read_all()` else 403 | `list_operator_tenants(db)` → `OperatorTenantListResponse` |
| `POST /impersonation/start` | `permissions.get("impersonate_tenant") is True` else 403 | `set_audit_context_sync(db, user_id=platform_user.id)` → `start_impersonation(...)` |
| `POST /impersonation/end` | same | `set_audit_context_sync(...)` → `end_impersonation(...)` → `{"ended": true}` |

Register the router in `backend/app/main.py` next to the cohort router.

## Task 5 — Impersonated-mutation audit middleware

**File**: `backend/app/main.py` (design §C-A5).

HTTP middleware: after the call, if `getattr(request.state, "impersonator_user_id", None)` is set AND `request.method not in {"GET", "HEAD", "OPTIONS"}` → write one `audit.event` row (`action='request'`, `contextdata={"method": request.method, "path": request.url.path}`) using its own short-lived session from `get_db()`. **Failure to write must never break the request** — wrap in try/except, log the exception, continue. Keep it minimal; do not buffer or batch.

## Task 6 — OpenAPI regen

```bash
cd <repo>/backend && source .venv/bin/activate
python export_openapi_json.py
grep -A 5 "operator/tenants\|impersonation" backend/openapi_schema_map.md
```

All 3 new endpoints must appear.

## Task 7 — Tests: `tests/domains/platform_infrastructure/test_cb15_impersonation.py` (NEW)

`pytestmark = [pytest.mark.domain_platform_infrastructure, pytest.mark.unit]`. Use the `client` fixture and the JWT mock fixtures from `conftest.py` — check how the C-B11 cohort tests build a **platform-user** JWT (`mock_jwt_for_user` against a user row with `is_platform_user=True`, `platform_role_code='owner'`); create such users inside your test (INSERT, scope by your inserted IDs — never mutate shared seed rows).

Test matrix (minimum):

1. Tenant user + `X-Impersonate-Tenant` header → header ignored, normal tenant context (e.g., `/api/v1/users/me/permissions` returns their own tenant).
2. Platform user (owner role) + valid header → `/api/v1/users/me/permissions` returns the **target** tenant id + `role_code='owner'`.
3. Platform user, no header → existing 403 from `get_current_user()` preserved.
4. Platform user with `platform_role_code='accountant'` + header → 403.
5. Header with unknown tenant UUID → 404; inactive tenant → 409; malformed UUID → 400.
6. `GET /api/v1/operator/tenants` returns 200 with a list; assert by your inserted tenant's ID (never row counts).
7. `POST /impersonation/start` writes an `audit.event` row (`entity_name='impersonation'`, `action='start'`, `actor_type='platform'`) — query via `db_session`, scope by your IDs.
8. `POST /impersonation/end` writes the matching `action='end'` row; end-without-start still returns 200.
9. Accountant role → 403 on start/end; tenant JWT → 403 on all three operator endpoints.
10. Mutation under impersonation writes an `action='request'` audit row (pick any simple existing POST the owner role can perform, or test the middleware more directly if simpler — your call, document the choice).

After adding the test file, regenerate the import map: `python generate_app_import_map.py tests > app_model_imports.md`.

---

## Regeneration Steps

- `python export_openapi_json.py` — required (3 new endpoints + `AuthenticatedUser` is not in the schema, but response models are).
- `python generate_app_import_map.py tests > app_model_imports.md` — required (new test file).
- `python generate_db_model_map.py app > db_models_map.md` — **not required** (no SQLModel class added/modified; `AuthenticatedUser` is a Pydantic context object, not a table).
- `schema_manager.py` — **not required** (no schema change).

## Final Verification

### Phase 1 — Unit Tests Only (run after each task group during development)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before moving to the next task. Fix any unit failure — including failures that appear to be caused by code outside your batch — before proceeding.

### Phase 2 — Lint (changed files only) + Full Suite (run once, at the very end, before DoD sign-off)

```bash
cd <repo>/backend
source .venv/bin/activate

CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')
if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY
    ruff format $CHANGED_PY
    ruff check $CHANGED_PY
fi

python -m pytest --tb=short -q 2>&1 | tail -10

# Batch-specific spot checks
python -m pytest tests/domains/platform_infrastructure/ -v 2>&1 | tail -20
grep -A 5 "impersonation" backend/openapi_schema_map.md

echo "=== C-B15 PART A FINAL VERIFICATION COMPLETE ==="
```

> **Warning-clean is part of done.** Any failure in either phase must be fixed before the batch is declared done. If you cannot identify the root cause of a failing test → STOP and ask Tom.

---

## Definition of Done

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work (or confirmed with Tom)
- [ ] All 7 MCP pre-work queries run — platform_role flags, tenant columns, audit.event CHECK + columns, owner role permissions, subscription columns, user platform columns all confirmed
- [ ] All mandatory source files read before writing any code (including `api/schemas/cohort.py`)
- [ ] `AuthenticatedUser.impersonator_user_id` + `is_impersonated` added; `_try_impersonation()` implements all 6 security invariants
- [ ] `services/impersonation_service.py` created per §F.2 (sync `def`, injected `Session`)
- [ ] `api/schemas/operator.py` created (Pydantic v2, `ConfigDict`)
- [ ] `api/routes/operator_tenants.py` created + registered in `app/main.py` — 3 endpoints, `get_platform_user()`, RFC 7807 errors
- [ ] Impersonated-mutation audit middleware registered; write failure cannot break a request
- [ ] `set_audit_context_sync()` called at the start of both mutation endpoints
- [ ] All DB-touching routes/`_impl()` are sync `def` — no `async def` on the blocking `Session` (rules §21)
- [ ] Only Pydantic v2 idioms used; every new route has `response_model` (rules §22)
- [ ] All new API errors follow RFC 7807 Problem Details format
- [ ] New test file uses `pytestmark` domain marker + `pytest.mark.unit`; `client` fixture; no module-level `TestClient`; no hardcoded UUIDs; assertions scoped by inserted IDs
- [ ] `python generate_app_import_map.py tests > app_model_imports.md` run
- [ ] `python export_openapi_json.py` run — all 3 endpoints verified in `openapi_schema_map.md`
- [ ] `ruff check --fix && ruff format` run **on changed files only** — zero remaining issues (rules §23)
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures including any pre-existing
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures including integration tests, warning-clean
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to launch plan (see below)
- [ ] Handoff step completed (see below)

## Completion Summary

After all Definition of Done items are complete, add a **Completion Summary** subsection to `dev-docs/analysis/pilot-launch-plan.md` under the C-B14 summary (same format as the existing C-B14 Part A summary):

```markdown
### C-B15 (Part A — Python Engineer) — Tenant Impersonation Backend: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished
- ...

#### Files Changed / Created
| File | Action |
|---|---|
| ... | ... |

#### Tests Added
| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| ... | ... | ... | ✅ |
```

Also update launch plan row 14v status from `☐ author` to `🔄 Part A ✅ / Part B pending UI spec`.

## Handoff Instructions (MANDATORY — Part B depends on this)

1. Run `python export_openapi_json.py` (final, after all changes) and confirm the 3 new endpoints are in `backend/openapi.json`.
2. Commit all Part A work.
3. State explicitly in your completion output: **"C-B15 Part A complete — OpenAPI regenerated. Part B (React Engineer) is gated on the C-B15 UI design spec being Tom-approved; when issued, its first Pre-Work step is `pnpm sync-api-types`."**

## After This Task — Next Step

- **C-B15 UI design spec** — authored by `pilot-web-ui-designer`, Tom approval gate (Architect Rule §1.5)
- **C-B15 Part B (React Engineer)** — platform shell + banner + selector; prompt issued only after spec approval
- **C-B14-FIX (row 14v2)** — Stripe hardening follow-ups, may be scheduled in parallel
