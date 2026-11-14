# Implementation Prompt: UI-FIX-2B — Multi-Tech Assignment: Backend (Python Engineer)

**Mode**: Pilot Python Engineer  
**Batch**: UI-FIX-2B (Backend half)  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` — UI-FIX-2B row  
**Source decisions**: `dev-docs/architecture-design/batch-designs/ui-fix-2-decisions.md § FIX-015`  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-ui-fix-2b-design.md`  
**Estimated session**: 2–3 hours  
**Platform**: Backend only (`backend/`)  
**Frontend companion**: UI-FIX-2B React Engineer prompt — runs AFTER this batch is complete and `openapi.json` is committed

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, and fixture rules

**Critical rules for this batch:**

- **Rule 1**: Never guess column names, data types, or table names. Run MCP verification queries below before writing any code. If MCP returns an error → **STOP and ask Tom**.
- **Rule 3**: After endpoint changes → run `python export_openapi_json.py` (updates both `openapi.json` and `openapi_schema_map.md`).
- **Rule 5**: Never use module-level `TestClient` in any test file. Always use the `client` fixture from `conftest.py`.
- **Rule 6**: `db.get()` is permanently banned on tenant-scoped models. Always use tenant-scoped `select()` with explicit `WHERE tenant_id = :tid`.
- **Rule 8**: All API error responses MUST follow RFC 7807 Problem Details format.
- **Rule 11**: If ANY test fails during your work — even pre-existing — **fix it before declaring done**.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current unit-only test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> If any tests are already failing before you start: confirm with Tom or fix before proceeding. You may NOT start implementation work while tests are in an unexplained failed state.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

```sql
-- 1. Confirm user name + color columns exist (must match what we're about to add to schema)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'user'
  AND column_name IN ('first_name', 'last_name', 'display_color')
ORDER BY column_name;
-- Expected: 3 rows — all character varying, is_nullable = YES

-- 2. Confirm job_tech_assignment full column list (confirm no migration needed)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'job_tech_assignment'
ORDER BY ordinal_position;
-- Expected: id, tenant_id, job_id, user_id, assigned_by_user_id, role, ordinal, assigned_at, is_active, version

-- 3. Confirm tenant_user JOIN columns (used in _list_tenant_users_impl)
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_user'
ORDER BY ordinal_position;

-- 4. Confirm current alembic head
SELECT version_num FROM public.alembic_version;
```

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE.

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/api/schemas/roles.py                   ← TenantUserWithRoleResponse current fields
backend/api/routes/roles.py                    ← _list_tenant_users_impl() JOIN mapping
backend/app/models/core.py                     ← User model fields (first_name, last_name, display_color)
backend/tests/conftest.py                      ← available fixtures
backend/db_models_map.md                       ← confirm model names
```

Also run:
```bash
grep -n "TenantUserWithRoleResponse" backend/api/schemas/roles.py backend/api/routes/roles.py
grep -n "_list_tenant_users_impl" backend/api/routes/roles.py
```

---

## Background

This batch resolves FIX-015 — the tech assignment UI on both the Dispatch Board and Job Detail page is non-functional because `GET /api/v1/users` returns user records with no name fields (`first_name`, `last_name`, `display_color`). A picker showing only email addresses is unacceptable for a dispatch tool.

**No migration is needed.** The `user` table already has all three columns confirmed via MCP. The JOIN in `_list_tenant_users_impl()` already pulls the `User` model alongside `TenantUser` — the three name fields are simply not mapped into the Pydantic response schema.

This is a 2-file change + OpenAPI regen + tests.

---

## Task 1 — Extend `TenantUserWithRoleResponse` with Name Fields

**File**: `backend/api/schemas/roles.py`

Read the file first. Add three new optional fields to `TenantUserWithRoleResponse`:

```python
# Add after the existing is_active field:
first_name: str | None = Field(None, description="User's first name")
last_name: str | None = Field(None, description="User's last name")
display_color: str | None = Field(None, description="User's avatar display color (hex or named)")
```

Also update the `json_schema_extra` example to include these fields:

```python
"first_name": "John",
"last_name": "Smith",
"display_color": "#4F86C6",
```

**Intermediate check:**
```bash
cd <repo>/backend
source .venv/bin/activate
python -c "from api.schemas.roles import TenantUserWithRoleResponse; print('OK')"
```

---

## Task 2 — Map Name Fields in `_list_tenant_users_impl()`

**File**: `backend/api/routes/roles.py`

Read the file first. Find `_list_tenant_users_impl()` — specifically the section where `TenantUserWithRoleResponse(...)` is constructed (look for the loop over query results that builds the response list).

Add the three new fields to the `TenantUserWithRoleResponse(...)` constructor:

```python
# Add alongside existing user_id=..., email=..., etc.:
first_name=user.first_name,
last_name=user.last_name,
display_color=user.display_color,
```

> The `user` object is available because `_list_tenant_users_impl()` already does `select(TenantUser, User, TenantUserRole).join(User, ...)`. The user variable is in the query result tuple — read the actual code to confirm the exact variable name before adding the mapping.

**Intermediate check:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -8
```

---

## Task 3 — Regenerate OpenAPI

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
```

Verify the new fields appear in the generated spec:
```bash
python3 -c "
import json
spec = json.load(open('openapi.json'))
schema = spec['components']['schemas'].get('TenantUserWithRoleResponse', {})
props = schema.get('properties', {})
print('first_name' in props, 'last_name' in props, 'display_color' in props)
"
# Expected: True True True
```

---

## Task 4 — Write Tests

**File**: `backend/tests/domains/scheduling_dispatch/test_ui_fix_2b_tech_users.py`

Per `backend/tests/README-adding-tests.md`:

```python
import pytest

pytestmark = [
    pytest.mark.domain_scheduling_dispatch,
    pytest.mark.unit,
]
```

**Tests to write (minimum 4):**

1. `test_list_users_includes_first_name` — `GET /api/v1/users/test` returns at least one user whose response contains `first_name` key (not absent from schema)
2. `test_list_users_includes_last_name` — same for `last_name`
3. `test_list_users_includes_display_color` — same for `display_color`
4. `test_list_users_name_fields_nullable` — user with `first_name=None` (create via test tenant where name not set) returns `first_name: null` in response, not missing key

Use the `client` fixture + `/api/v1/users/test` endpoint (unauthenticated test variant). Use `test_tenant` fixture. Assert on the specific user created in the test, not on total count.

---

## Final Verification

### Phase 1 — Unit Tests Only

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass before moving to Phase 2.

### Phase 2 — Full Suite

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest --tb=short -q 2>&1 | tail -10

# Spot check
python -m pytest tests/domains/scheduling_dispatch/ -v 2>&1 | tail -20
grep -A 5 "TenantUserWithRoleResponse" backend/openapi_schema_map.md

echo "=== UI-FIX-2B BACKEND FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting (or confirmed with Tom)
- [ ] All 4 MCP pre-work queries run — `first_name`, `last_name`, `display_color` confirmed on `user` table
- [ ] All mandatory source files read before writing any code
- [ ] `backend/api/schemas/roles.py` — `TenantUserWithRoleResponse` gains `first_name`, `last_name`, `display_color` fields
- [ ] `backend/api/routes/roles.py` — `_list_tenant_users_impl()` maps all three new fields from the JOIN result
- [ ] `python export_openapi_json.py` run — both `openapi.json` and `openapi_schema_map.md` updated
- [ ] New fields verified present in `openapi.json` `TenantUserWithRoleResponse` schema
- [ ] All new test files use `pytestmark` with `domain_scheduling_dispatch` marker + `pytest.mark.unit`
- [ ] No module-level `TestClient` in any test file
- [ ] All new tests use `test_tenant` and `test_user` fixtures (no hardcoded UUIDs)
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `ui-fix-2-decisions.md` under UI-FIX-2B Backend row
- [ ] `pilot-launch-plan.md` UI-FIX-2B row updated to reflect backend complete

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** subsection to `dev-docs/architecture-design/batch-designs/ui-fix-2-decisions.md` under the UI-FIX-2B batch section:

```markdown
### UI-FIX-2B (Backend) — TenantUserWithRoleResponse Name Fields: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- Added `first_name`, `last_name`, `display_color` to `TenantUserWithRoleResponse` Pydantic schema
- Mapped new fields from existing JOIN result in `_list_tenant_users_impl()`
- Regenerated `openapi.json` and `openapi_schema_map.md`

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/api/schemas/roles.py` | Updated — 3 new optional fields on TenantUserWithRoleResponse |
| `backend/api/routes/roles.py` | Updated — mapped first_name, last_name, display_color in _list_tenant_users_impl() |
| `backend/openapi.json` | Regenerated |
| `backend/openapi_schema_map.md` | Regenerated |
| `backend/tests/domains/scheduling_dispatch/test_ui_fix_2b_tech_users.py` | Created — N tests |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/scheduling_dispatch/test_ui_fix_2b_tech_users.py` | `domain_scheduling_dispatch` | N | ✅ |
```

2. Update `dev-docs/analysis/pilot-launch-plan.md` — UI-FIX-2B row: change Status from `⏳ Pending` to `🔄 Backend ✅ YYYY-MM-DD — FE ⏳ Pending`.

---

## After This Task — Handoff to React Engineer

Once Phase 2 passes:

1. Run `python export_openapi_json.py` one final time to ensure `openapi.json` is current
2. Commit all changes (schemas, routes, tests, openapi files)
3. The **UI-FIX-2B React Engineer prompt** can now start — it depends on this batch being complete and `openapi.json` committed

The React Engineer's first step is `pnpm sync-api-types` to pick up the new `first_name`, `last_name`, `display_color` fields on `TenantUserWithRoleResponse`.
