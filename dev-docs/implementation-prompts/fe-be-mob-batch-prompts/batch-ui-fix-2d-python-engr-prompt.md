# Implementation Prompt: UI-FIX-2D — Customer Detail Tabs: Backend (Python Engineer)

**Mode**: Pilot Python Engineer  
**Batch**: UI-FIX-2D (Backend half)  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` — UI-FIX-2D row  
**Source decisions**: `dev-docs/architecture-design/batch-designs/ui-fix-2-decisions.md § FIX-018`  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-ui-fix-2d-design.md`  
**Estimated session**: 2–3 hours  
**Platform**: Backend only (`backend/`)  
**Frontend companion**: UI-FIX-2D React Engineer prompt — runs AFTER this batch is complete and `openapi.json` is committed

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, and fixture rules

**Critical rules for this batch:**

- **Rule 1**: Never guess column names. Run MCP verification below before touching any file. If MCP returns an error → **STOP and ask Tom**.
- **Rule 3**: After endpoint changes → run `python export_openapi_json.py` (updates `openapi.json` + `openapi_schema_map.md`).
- **Rule 5**: Never use module-level `TestClient`. Always use the `client` fixture.
- **Rule 6**: `db.get()` permanently banned on tenant-scoped models. Always use tenant-scoped `select()`.
- **Rule 8**: All API error responses MUST follow RFC 7807 Problem Details format.
- **Rule 11**: If ANY test fails — even pre-existing — fix it before declaring done.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count. Fix any unexplained failures before proceeding.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code:

```sql
-- 1. Confirm customer_id on job table
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'job'
  AND column_name IN ('id', 'customer_id', 'tenant_id')
ORDER BY column_name;
-- Expected: all 3 rows, customer_id is uuid NOT NULL

-- 2. Confirm customer_id on quote table
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'quote'
  AND column_name IN ('id', 'customer_id', 'tenant_id')
ORDER BY column_name;
-- Expected: all 3 rows, customer_id is uuid NOT NULL

-- 3. Confirm customer_id on invoice table
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'invoice'
  AND column_name IN ('id', 'customer_id', 'tenant_id')
ORDER BY column_name;
-- Expected: all 3 rows, customer_id is uuid NOT NULL

-- 4. Confirm current alembic head
SELECT version_num FROM public.alembic_version;
```

> **MCP Usage Rule**: Read-only verification only. Never INSERT, UPDATE, or DELETE via MCP.

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/api/routes/jobs.py             ← find _list_jobs_impl(); understand existing params + WHERE clauses
backend/api/routes/quotes.py           ← find _list_quotes_impl(); understand existing params + WHERE clauses
backend/api/routes/invoices.py         ← find _list_invoices_impl(); understand existing params + WHERE clauses
backend/api/schemas/schemas.py         ← PaginatedJobListResponse, PaginatedQuoteListResponse shapes
backend/api/schemas/quotes.py          ← PaginatedQuoteListResponse (may be in separate file)
backend/tests/conftest.py              ← available fixtures
```

Also run:
```bash
grep -n "customer_search\|customer_id\|_list_jobs_impl\|_list_quotes_impl\|_list_invoices_impl" \
  backend/api/routes/jobs.py backend/api/routes/quotes.py backend/api/routes/invoices.py | head -30
```

---

## Background

The customer detail page at `/customers/[id]` has Jobs, Quotes, and Invoices tabs that currently render placeholder components showing "available in other screens." The root cause: all three list endpoints support `?customer_search=` (fuzzy ILIKE on name) but NOT `?customer_id=<uuid>` (exact UUID match).

This batch adds one new optional query parameter — `customer_id: uuid.UUID | None = Query(None)` — to all three list endpoints. Each already JOINs the Customer table (required for `customer_search`), so adding `WHERE [table].customer_id == customer_id` requires no new JOINs.

**No Alembic migration is needed.** `customer_id` is already a NOT NULL column on all three tables.

---

## Task 1 — Add `?customer_id=` to `GET /api/v1/jobs/`

**File**: `backend/api/routes/jobs.py`

Read the file first. Find `_list_jobs_impl()` (the shared implementation called by both the authenticated endpoint and the `/test` endpoint).

Add `customer_id` as an optional parameter alongside the existing `customer_search` parameter:

```python
import uuid  # confirm already imported at top of file

# Add parameter (in function signature, alongside existing params):
customer_id: uuid.UUID | None = Query(None, description="Filter jobs by exact customer UUID"),

# Add filter clause after the tenant_id scope AND after the customer_search ILIKE block:
if customer_id:
    statement = statement.where(Job.customer_id == customer_id)
    count_statement = count_statement.where(Job.customer_id == customer_id)
```

> **Critical**: Add the filter to BOTH `statement` AND `count_statement`. The `count_statement` drives `PaginatedResponse.total` — if the count is unfiltered, the React Engineer's paginator will show wrong page counts.

> Read the file carefully to identify the exact variable names used for the main query and count query — they may be named differently from the examples above. Adjust accordingly.

Also add `customer_id` to the authenticated endpoint signature (the `@router.get` function that calls `_list_jobs_impl()`) if it doesn't automatically pick it up from the impl function.

**Intermediate check:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 2 — Add `?customer_id=` to `GET /api/v1/quotes/`

**File**: `backend/api/routes/quotes.py`

Same pattern as Task 1. Find `_list_quotes_impl()`:

```python
customer_id: uuid.UUID | None = Query(None, description="Filter quotes by exact customer UUID"),

if customer_id:
    statement = statement.where(Quote.customer_id == customer_id)
    count_statement = count_statement.where(Quote.customer_id == customer_id)
```

> Read the file to confirm the ORM model name and the exact variable names. The model may be `Quote`, `QuoteStatus`, or similar depending on how the route is implemented.

**Intermediate check:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 3 — Add `?customer_id=` to `GET /api/v1/invoices/`

**File**: `backend/api/routes/invoices.py`

Same pattern. Find `_list_invoices_impl()`:

```python
customer_id: uuid.UUID | None = Query(None, description="Filter invoices by exact customer UUID"),

if customer_id:
    query = query.where(Invoice.customer_id == customer_id)
    count_query = count_query.where(Invoice.customer_id == customer_id)
```

> The variable names `query` / `count_query` are approximate — read the file for the actual names.

**Intermediate check:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 4 — Regenerate OpenAPI

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
```

Verify all three endpoints show the new `customer_id` parameter:
```bash
grep -A 3 "customer_id" backend/openapi_schema_map.md | grep -A 2 "jobs\|quotes\|invoices" | head -20
```

Or verify programmatically:
```bash
python3 -c "
import json
spec = json.load(open('openapi.json'))
for path in ['/api/v1/jobs/', '/api/v1/quotes/', '/api/v1/invoices/']:
    get_op = spec['paths'].get(path, {}).get('get', {})
    params = [p['name'] for p in get_op.get('parameters', [])]
    print(path, 'customer_id' in params)
"
# Expected: True True True
```

---

## Task 5 — Write Tests

**File**: `backend/tests/domains/field_operations/test_ui_fix_2d_customer_filter.py`

Per `backend/tests/README-adding-tests.md`:

```python
import pytest

pytestmark = [
    pytest.mark.domain_field_operations,
    pytest.mark.unit,
]
```

**Tests to write (minimum 6 — 2 per endpoint):**

For each of the 3 endpoints:

1. `test_{entity}_list_filter_by_customer_id` — create 2 jobs/quotes/invoices for different customers; call `GET /api/v1/{entity}s/test?customer_id={customer_a_id}`; assert only the customer_a record is in `items`; assert customer_b record is NOT in `items`
2. `test_{entity}_list_no_customer_id_returns_all` — without `?customer_id=`, the endpoint returns records for all customers in the tenant (existing behavior unchanged)

Use `test_tenant`, `test_customer`, `client` fixtures. Use `/test` endpoint variants (unauthenticated). Assert by specific IDs from INSERT, never by total count.

For isolation: when creating a second customer for cross-customer tests, use `POST /api/v1/customers/test` to create a second customer within `test_tenant`.

---

## Final Verification

### Phase 1 — Unit Tests Only

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

### Phase 2 — Full Suite

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest --tb=short -q 2>&1 | tail -10

python -m pytest tests/domains/field_operations/ -v 2>&1 | tail -20
grep "customer_id" backend/openapi_schema_map.md | head -10

echo "=== UI-FIX-2D BACKEND FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed (or confirmed with Tom)
- [ ] All 4 MCP pre-work queries run — `customer_id` uuid NOT NULL confirmed on `job`, `quote`, `invoice`
- [ ] All mandatory source files read before writing any code
- [ ] `backend/api/routes/jobs.py` — `_list_jobs_impl()` accepts `?customer_id=` and applies to BOTH main query and count query
- [ ] `backend/api/routes/quotes.py` — `_list_quotes_impl()` accepts `?customer_id=` and applies to BOTH queries
- [ ] `backend/api/routes/invoices.py` — `_list_invoices_impl()` accepts `?customer_id=` and applies to BOTH queries
- [ ] `python export_openapi_json.py` run — `openapi.json` and `openapi_schema_map.md` updated
- [ ] All 3 endpoints verified to show `customer_id` parameter in `openapi.json`
- [ ] New test files use `pytestmark` with `domain_field_operations` + `pytest.mark.unit`
- [ ] No module-level `TestClient` in any test file
- [ ] All new tests use `test_tenant`/`test_customer` fixtures (no hardcoded UUIDs)
- [ ] **Phase 1**: All unit tests pass — zero failures
- [ ] **Phase 2**: Full test suite passes — zero failures
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `ui-fix-2-decisions.md` under UI-FIX-2D Backend row
- [ ] `pilot-launch-plan.md` UI-FIX-2D row updated to reflect backend complete

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** subsection to `dev-docs/architecture-design/batch-designs/ui-fix-2-decisions.md` under the UI-FIX-2D batch section:

```markdown
### UI-FIX-2D (Backend) — customer_id Filter on 3 List Endpoints: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- Added `?customer_id=uuid` filter param to `GET /api/v1/jobs/`, `GET /api/v1/quotes/`, `GET /api/v1/invoices/`
- Applied filter to both data query and count query in all three `_list_*_impl()` functions
- Regenerated `openapi.json` and `openapi_schema_map.md`

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/api/routes/jobs.py` | Updated — customer_id UUID filter param |
| `backend/api/routes/quotes.py` | Updated — customer_id UUID filter param |
| `backend/api/routes/invoices.py` | Updated — customer_id UUID filter param |
| `backend/openapi.json` | Regenerated |
| `backend/openapi_schema_map.md` | Regenerated |
| `backend/tests/domains/field_operations/test_ui_fix_2d_customer_filter.py` | Created — N tests |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/field_operations/test_ui_fix_2d_customer_filter.py` | `domain_field_operations` | N | ✅ |
```

2. Update `dev-docs/analysis/pilot-launch-plan.md` — UI-FIX-2D row: change Status to `🔄 Backend ✅ YYYY-MM-DD — FE ⏳ Pending`.

---

## After This Task — Handoff to React Engineer

Once Phase 2 passes:

1. Run `python export_openapi_json.py` one final time
2. Commit all changes (routes, tests, openapi files)
3. The **UI-FIX-2D React Engineer prompt** can now start

The React Engineer's first step is `pnpm sync-api-types` to pick up the new `customer_id` parameters on the 3 list endpoints.
