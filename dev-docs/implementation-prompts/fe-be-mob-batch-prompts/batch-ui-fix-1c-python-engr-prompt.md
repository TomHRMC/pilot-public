# Implementation Prompt: UI-FIX-1C Part A — Server-Side Pagination & Filters (Backend)

**Mode**: Pilot Python Engineer  
**Batch**: UI-FIX-1C — Part A (Backend)  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §UI Fix — Batch 1  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-ui-fix-1c-design.md`  
**Estimated session**: 6–7 hours  
**Platform**: Backend only (`backend/`)  
**Frontend companion**: UI-FIX-1C Part B (React Engineer) — depends on this batch completing + `python export_openapi_json.py` committed

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs all test file structure, domain markers, and fixture rules

**Critical rules for this batch:**

- **Rule 1**: Never guess column names, data types, or table names. All MCP pre-work queries must be run before writing any filter clause. If MCP returns an error → **STOP and ask Tom**.
- **Rule 2**: After endpoint changes → run `python export_openapi_json.py`. The React Engineer for UI-FIX-1C Part B depends on the updated spec.
- **Rule 3**: No Alembic migration in this batch. Do NOT run `alembic revision`. All changes are route handler + schema additions only.
- **Rule 4**: `db.get()` is permanently banned. All new filter queries use `db.exec(select(...).where(...).where(Model.tenant_id == current_user.tenant_id))`.
- **Rule 7**: `postgres-local` MCP is read-only verification only.
- **Rule 8**: All API error responses must follow RFC 7807 Problem Details format.
- **Rule 11**: If ANY test fails — fix it before declaring the batch done. No "pre-existing" exception.

**Default limit change warning (Rule custom):**  
All endpoints change default `limit` from `100` to `25`. Before changing any default, you must `grep -rn "api/v1/customers\|api/v1/quotes\|api/v1/jobs\|catalog/pricebook" backend/` to find all callers (dispatch board, tests, mobile sync background tasks) and add explicit `limit=200` or appropriate values where needed. This is a breaking change if callers rely on the default.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**. Fix any failures before starting.

---

## Pre-Work: Run MCP Verification Queries

> **MCP Usage Rule**: Read-only verification only. Never INSERT, UPDATE, or DELETE.

```sql
-- 1. Confirm customer table columns for filter clauses
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'customer'
ORDER BY ordinal_position;

-- 2. Confirm job table columns for filter clauses
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'job'
ORDER BY ordinal_position;

-- 3. Confirm quote table columns (especially created_at for date filters)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'quote'
ORDER BY ordinal_position;

-- 4. Confirm pricebook_item table columns for search filter
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'pricebook_item'
ORDER BY ordinal_position;

-- 5. Confirm invoice table columns (for customer_search + issued_from/to)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'invoice'
ORDER BY ordinal_position;

-- 6. Confirm job_status codes (for status filter)
SELECT id, code, name FROM job_status ORDER BY code;

-- 7. Confirm current alembic head (no migration expected, just verify)
SELECT version_num FROM public.alembic_version;
```

---

## Pre-Work: Read These Source Files

```
backend/api/schemas/schemas.py               ← understand InvoiceListResponse shape before adding PaginatedResponse
backend/api/routes/customers.py              ← understand current list_customers() before adding filters
backend/api/routes/quotes.py                 ← understand current list_quotes() before adding filters
backend/api/routes/invoices.py               ← understand current list_invoices() + InvoiceListResponse usage
backend/api/routes/jobs.py                   ← understand current list_jobs() + dispatch board compat
backend/api/routes/catalog.py               ← understand current list_pricebook_items() + check if search exists
backend/db_models_map.md                     ← verify model names for Customer, Quote, Job, PricebookItem
backend/tests/conftest.py                    ← understand available fixtures
```

Also run:

```bash
# Find dispatch board and other callers that may rely on default limit=100
grep -rn "api/v1/jobs\|api/v1/customers\|api/v1/quotes\|catalog/pricebook" backend/ --include="*.py" -l

# Check if catalog route already has a search param
grep -n "search" backend/api/routes/catalog.py

# Find all test files that call these list endpoints
grep -rn "client.get.*customers\|client.get.*quotes\|client.get.*jobs\|client.get.*pricebook" backend/tests/ --include="*.py" -l
```

---

## Background

This batch is Part A of the server-side pagination batch (FIX-014). The React Engineer cannot start until these backend changes are live and `openapi.json` is regenerated.

**Current state** (verified from OpenAPI + source):
| Endpoint | Total? | Pagination | Filter params |
|---|---|---|---|
| `GET /api/v1/customers/` | ❌ | `skip`+`limit` | `search` |
| `GET /api/v1/quotes` | ❌ | `skip`+`limit` | `status` |
| `GET /api/v1/invoices/` | ✅ | `offset`+`limit` | `status`, `overdue`, `due_before`, `due_after` |
| `GET /api/v1/jobs/` | ❌ | `skip`+`limit` | `tech_id`, `scheduled_date` |
| `GET /api/v1/catalog/pricebook` | ❌ | `skip`+`limit` | `is_active` |

**Target state** (all 5 endpoints):
- All return `PaginatedResponse` with `total`, `limit`, `offset`
- `offset` is canonical name (with backward-compat `skip` alias)
- Default `limit` = 25 (down from 100) — **must audit callers first**
- New filter params per entity (see design doc §D)

---

## Task 1 — Add `PaginatedResponse` schema

**File**: `backend/api/schemas/schemas.py`

Read the file first. Add `PaginatedResponse` generic class and 4 entity-specific concrete types. **Add before the existing `InvoiceListResponse` class** (search for it, don't place at end of file):

```python
from typing import TypeVar, Generic

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    """Standardized paginated list response — all list endpoints return this shape."""
    items: list[T]
    total: int
    limit: int
    offset: int


# Concrete paginated types for OpenAPI generation (FastAPI requires concrete types)
class PaginatedCustomerResponse(PaginatedResponse[CustomerResponse]):
    pass


class PaginatedQuoteListResponse(PaginatedResponse[QuoteListItem]):
    pass


class PaginatedJobListResponse(PaginatedResponse[JobListItem]):
    pass


class PaginatedCatalogResponse(PaginatedResponse[PricebookItemResponse]):
    pass
```

> Adjust import if `TypeVar`/`Generic` need adding to the import block. Read the existing import section first.

**Intermediate unit test run:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 2 — Audit Default-Limit Callers (BEFORE changing any route)

Run these searches before changing any `limit` default:

```bash
# Any Python code that calls these endpoints without an explicit limit
grep -rn "get.*api/v1/jobs\|get.*api/v1/customers\|get.*api/v1/quotes\|get.*catalog/pricebook" backend/ --include="*.py"

# Celery tasks and mobile sync services
grep -rn "jobs/\|customers/\|quotes\b\|pricebook" backend/tasks/ --include="*.py"
grep -rn "jobs/\|customers/\|quotes\b\|pricebook" backend/services/ --include="*.py"

# Tests that do NOT pass explicit limit params
grep -rn "client.get.*\"/api/v1/jobs" backend/tests/ --include="*.py"
grep -rn "client.get.*\"/api/v1/customers" backend/tests/ --include="*.py"
```

For any internal caller that relied on default `limit=100`, add `?limit=200` (or appropriate value) to prevent silent truncation. Document each change in your Completion Summary.

---

## Task 3 — Update Customers Endpoint

**File**: `backend/api/routes/customers.py`

Read `list_customers()` (around line 716) before modifying. Changes:

1. Change `response_model=list[CustomerResponse]` → `response_model=PaginatedCustomerResponse`
2. Add `offset: int = Query(0, ge=0)` parameter
3. Add `status: str | None = Query(None, description="active | inactive")` parameter
4. Mark `skip` as `Query(0, deprecated=True, alias="skip")`
5. Compute `effective_offset = offset if offset > 0 else skip`
6. Add filter clause: if `status == "active"`: `Customer.is_active == True`; if `status == "inactive"`: `Customer.is_active == False`
7. Add a `COUNT` query using same filters to get `total`
8. Return `PaginatedCustomerResponse(items=rows, total=count, limit=limit, offset=effective_offset)`
9. Change default `limit` to `25` (after auditing callers in Task 2)

**Count query pattern**:
```python
from sqlalchemy import func

count_stmt = select(func.count(Customer.id)).where(
    Customer.tenant_id == current_user.tenant_id,
    Customer.is_active == True,  # existing active filter
    # ... same WHERE clauses as the data query
)
total = db.exec(count_stmt).one()
```

Also update `list_customers_test()` (around line 423) with same params.

**Intermediate unit test run:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 4 — Update Quotes Endpoint

**File**: `backend/api/routes/quotes.py`

Read `list_quotes()` (around line 1376) before modifying. Changes:

1. Change `response_model=list[QuoteListItem]` → `response_model=PaginatedQuoteListResponse`
2. Add `offset`, `customer_search`, `title_search`, `date_from: datetime | None`, `date_to: datetime | None` params
3. Add backward-compat `skip` alias
4. **`customer_search`**: requires JOIN on `Customer` table. Pattern:
   ```python
   if customer_search:
       stmt = stmt.join(Customer, Quote.customer_id == Customer.id).where(
           Customer.display_name.ilike(f"%{customer_search}%")
       )
   ```
5. **`title_search`**: `Quote.title.ilike(f"%{title_search}%")` — note: `title` is nullable; filter only applies when non-null
6. **`date_from`/`date_to`**: `Quote.created_at >= date_from`, `Quote.created_at <= date_to`
7. Add COUNT query with same filters
8. Return `PaginatedQuoteListResponse(items=rows, total=count, limit=limit, offset=effective_offset)`
9. Change default `limit` to `25`

Also update `list_quotes_test()` (around line 864).

**Intermediate unit test run:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 5 — Update Invoices Endpoint

**File**: `backend/api/routes/invoices.py`

Read `list_invoices()` before modifying. **Do NOT restructure the existing `InvoiceListResponse` return** — just add 3 new filter params:

```python
customer_search: str | None = Query(None),
issued_from: datetime | None = Query(None),
issued_to: datetime | None = Query(None),
```

Add filter clauses (same JOIN pattern as quotes for `customer_search`):
- `customer_search`: JOIN Customer, `Customer.display_name.ilike(...)`
- `issued_from`: `Invoice.issued_at >= issued_from`
- `issued_to`: `Invoice.issued_at <= issued_to`

> Note: `InvoiceListResponse` already has `total`, `limit`, `offset`. Do NOT add `PaginatedInvoiceResponse`. Just update the query and count with the new filters.

Also update `list_invoices_test()`.

**Intermediate unit test run:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 6 — Update Jobs Endpoint

**File**: `backend/api/routes/jobs.py`

Read `list_jobs()` (around line 1003) before modifying. **Critical**: the dispatch board uses `?scheduled_date=YYYY-MM-DD` — do NOT remove this param. Changes:

1. Change `response_model=list[JobListItem]` → `response_model=PaginatedJobListResponse`
2. Add `offset`, `status`, `customer_search`, `scheduled_from: datetime | None`, `scheduled_to: datetime | None` params
3. Keep `scheduled_date` as-is (dispatch board compat)
4. **`status`**: JOIN on `job_status` table → `JobStatus.code == status`
5. **`customer_search`**: JOIN on `Customer` table
6. **`scheduled_from`/`scheduled_to`**: `Job.scheduled_start_at >= scheduled_from`, etc.
7. Add COUNT query
8. Return `PaginatedJobListResponse`
9. Change default `limit` to `25` (after Task 2 audit)

Also update `list_jobs_test()` (around line 779).

**Intermediate unit test run:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 7 — Update Catalog/Pricebook Endpoint

**File**: `backend/api/routes/catalog.py`

Read `list_pricebook_items()` (around line 763) before modifying.

**First**: check `grep -n "search" backend/api/routes/catalog.py` to see if `search` already exists. If it does, just document it and skip adding it. If it doesn't:

1. Change `response_model` to `PaginatedCatalogResponse`
2. Add `offset` alias
3. Add `search: str | None = Query(None)` param — ILIKE on `PricebookItem.name`, `PricebookItem.description`, `PricebookItem.sku`
4. Add COUNT query
5. Return `PaginatedCatalogResponse`
6. Change default `limit` to `25`

Also update `list_pricebook_items_test()` (around line 657).

**Intermediate unit test run:**
```bash
python -m pytest -m unit --tb=short -q 2>&1 | tail -5
```

---

## Task 8 — Regenerate OpenAPI

After all 7 tasks complete and all unit tests pass:

```bash
cd <repo>/backend
source .venv/bin/activate
python export_openapi_json.py
```

Verify all 5 endpoints show new params and `PaginatedResponse` wrapper:

```bash
grep -A 10 "GET /api/v1/customers/" backend/openapi_schema_map.md | head -15
grep -A 5 "PaginatedCustomerResponse\|PaginatedQuoteList\|PaginatedJob" backend/openapi_schema_map.md | head -20
grep -A 5 "customer_search\|title_search\|scheduled_from" backend/openapi_schema_map.md | head -20
```

---

## Test Requirements

Per `backend/tests/README-adding-tests.md`:

**Required new test file**: `backend/tests/domains/platform_infrastructure/test_ui_fix_1c_pagination.py`

```python
pytestmark = [
    pytest.mark.domain_platform_infrastructure,
    pytest.mark.unit,
]
```

**Minimum tests (cover all 5 endpoints):**

```python
# 1. Customers: returns PaginatedResponse with total
def test_list_customers_returns_paginated_response(client, test_tenant, mock_cognito_jwt):
    # POST a customer first, then GET list
    # Assert response has keys: items, total, limit, offset
    # Assert total >= 1 (seed data present — use >=1, NOT ==1)
    ...

# 2. Customers: status=active filter
def test_list_customers_active_filter(client, test_tenant, mock_cognito_jwt):
    # Assert status=active returns only active customers (check is_active in returned items if available)
    ...

# 3. Customers: search filter
def test_list_customers_search_filter(client, test_tenant, mock_cognito_jwt):
    # Create customer with unique display_name, search for it
    # Assert the created customer appears in items by ID
    ...

# 4. Quotes: returns PaginatedResponse with total
def test_list_quotes_returns_paginated_response(client, test_tenant, mock_cognito_jwt):
    ...

# 5. Quotes: title_search filter
def test_list_quotes_title_search(client, test_tenant, mock_cognito_jwt):
    # Create quote with known title, search for it
    ...

# 6. Invoices: customer_search filter appended to existing filters
def test_list_invoices_customer_search(client, test_tenant, mock_cognito_jwt):
    ...

# 7. Jobs: returns PaginatedResponse
def test_list_jobs_returns_paginated_response(client, test_tenant, mock_cognito_jwt):
    ...

# 8. Jobs: status filter
def test_list_jobs_status_filter(client, test_tenant, mock_cognito_jwt):
    # Assert status=draft returns only draft jobs
    ...

# 9. Catalog: returns PaginatedResponse
def test_list_pricebook_returns_paginated_response(client, test_tenant, mock_cognito_jwt):
    ...

# 10. Pagination: offset + limit produce correct slice
def test_pagination_offset_limit(client, test_tenant, mock_cognito_jwt):
    # Create 3+ customers, GET with limit=1&offset=1
    # Assert exactly 1 item returned, total >= 3 (seed data present)
    # Assert items[0].id == second_customer.id (scoped by inserted IDs)
    ...
```

> **Seed data present in `test_tenant`**: Multiple customers, quotes, jobs, invoices already exist from seed scripts. Never `assert total == N` — always `assert total >= N` or assert by specific inserted ID.

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

# Spot-check new tests
python -m pytest tests/domains/platform_infrastructure/test_ui_fix_1c_pagination.py -v 2>&1 | tail -20

# Verify OpenAPI updated
grep -A 5 "PaginatedCustomerResponse" backend/openapi_schema_map.md
grep -A 5 "customer_search" backend/openapi_schema_map.md

echo "=== UI-FIX-1C PART A FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done

Update `dev-docs/architecture-design/batch-designs/ui-fix-1-decisions.md` §Implementation Batches when complete:

- [ ] Regression baseline captured (`pytest -m unit`)
- [ ] Zero pre-existing failures confirmed (or confirmed with Tom)
- [ ] All 7 MCP pre-work queries run — results reviewed
- [ ] All mandatory source files read before writing any code
- [ ] **Task 1**: `PaginatedResponse` + 4 concrete types added to `schemas.py`
- [ ] **Task 2**: Default-limit callers audited — explicit limits added where needed
- [ ] **Task 3**: `list_customers()` + `list_customers_test()` updated — `PaginatedCustomerResponse`, `offset`, `status` params
- [ ] **Task 4**: `list_quotes()` + test updated — `PaginatedQuoteListResponse`, `customer_search`, `title_search`, `date_from`/`date_to`
- [ ] **Task 5**: `list_invoices()` + test updated — `customer_search`, `issued_from`, `issued_to` (InvoiceListResponse structure unchanged)
- [ ] **Task 6**: `list_jobs()` + test updated — `PaginatedJobListResponse`, `status`, `customer_search`, `scheduled_from`/`to` (keep `scheduled_date`)
- [ ] **Task 7**: `list_pricebook_items()` + test updated — `PaginatedCatalogResponse`, `search` added (or documented as already present)
- [ ] All new API errors follow RFC 7807 Problem Details format
- [ ] `test_ui_fix_1c_pagination.py` created — ≥10 unit tests covering all 5 endpoints
- [ ] All new tests use `pytestmark` with domain marker + `pytest.mark.unit`
- [ ] No module-level `TestClient`; no hardcoded UUIDs
- [ ] All assertions scoped by inserted IDs (never `assert len(all_rows) == N` for total counts)
- [ ] **Task 8**: `python export_openapi_json.py` run — `PaginatedResponse` + new params visible in `openapi_schema_map.md`
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`)
- [ ] **Phase 2**: Full test suite passes
- [ ] Final test count documented
- [ ] `ui-fix-1-decisions.md` — UI-FIX-1C Part A noted complete

---

## Handoff Instructions

Before handing off to the React Engineer (UI-FIX-1C Part B):

1. Run `python export_openapi_json.py` — confirm success
2. Commit `backend/openapi.json` and `backend/openapi_schema_map.md` in the same commit
3. Notify React Engineer: **"UI-FIX-1C Part A is complete. Run `pnpm sync-api-types` before starting Part B."**

The React Engineer must update all 5 hooks to handle `PaginatedResult<T>` instead of `T[]` — the type will be available via `@pilot/shared-types` after `pnpm sync-api-types`.

---

## Completion Summary

After all DoD items complete:

1. Add Completion Summary to `ui-fix-1-decisions.md` §Implementation Batches.
2. Add to `pilot-launch-plan.md` Appendix B.

```markdown
### UI-FIX-1C Part A — Server-Side Pagination Backend: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed (+N new tests)

#### What Was Accomplished

- Added PaginatedResponse generic schema + 4 concrete types to schemas.py
- Updated 5 list endpoints with total count, offset standardization, and new filter params
- Audited default-limit callers — [describe any explicit limits added]

#### Files Changed / Created

| File | Action |
|---|---|
| `backend/api/schemas/schemas.py` | Updated — PaginatedResponse + 4 concrete types |
| `backend/api/routes/customers.py` | Updated — PaginatedCustomerResponse, offset, status filter |
| `backend/api/routes/quotes.py` | Updated — PaginatedQuoteListResponse, customer_search, title_search, date range |
| `backend/api/routes/invoices.py` | Updated — customer_search, issued_from, issued_to filter params |
| `backend/api/routes/jobs.py` | Updated — PaginatedJobListResponse, status, customer_search, scheduled range |
| `backend/api/routes/catalog.py` | Updated — PaginatedCatalogResponse, search param |
| `backend/openapi.json` | Regenerated |
| `backend/openapi_schema_map.md` | Regenerated |
| `backend/tests/domains/platform_infrastructure/test_ui_fix_1c_pagination.py` | Created |

#### Tests Added

| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/platform_infrastructure/test_ui_fix_1c_pagination.py` | `domain_platform_infrastructure` | ≥10 | ✅ |
```
