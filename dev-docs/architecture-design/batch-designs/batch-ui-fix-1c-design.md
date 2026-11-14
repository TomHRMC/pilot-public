# Batch UI-FIX-1C — Server-Side Search, Filter & Pagination (All 5 List Pages)

**Type**: Mixed — Part A: Backend (Python Engineer) → Part B: Frontend (React Engineer)  
**Status**: 🟡 Ready for implementation  
**Designed**: 2026-07-18  
**Source findings**: `dev-docs/architecture-design/batch-designs/ui-fix-1-decisions.md` §FIX-014  
**Estimated effort**: ~17h total (Part A: ~7h Python; Part B: ~10h React)  
**Dependency**: Part B starts ONLY after Part A completes and `pnpm sync-api-types` is run  

---

## Table of Contents

- [Batch UI-FIX-1C — Server-Side Search, Filter \& Pagination (All 5 List Pages)](#batch-ui-fix-1c--server-side-search-filter--pagination-all-5-list-pages)
  - [Table of Contents](#table-of-contents)
  - [A. Input Read Summary](#a-input-read-summary)
  - [B. Migration Plan](#b-migration-plan)
  - [C. Execution Order](#c-execution-order)
    - [Part A — Python Engineer (runs first)](#part-a--python-engineer-runs-first)
    - [Part B — React Engineer (runs after Part A ✅ + `pnpm sync-api-types`)](#part-b--react-engineer-runs-after-part-a---pnpm-sync-api-types)
  - [D. New API Endpoint Changes — Part A (Backend)](#d-new-api-endpoint-changes--part-a-backend)
    - [D.1 — Shared `PaginatedResponse` Schema](#d1--shared-paginatedresponse-schema)
    - [D.2 — Customers: `GET /api/v1/customers/`](#d2--customers-get-apiv1customers)
    - [D.3 — Quotes: `GET /api/v1/quotes`](#d3--quotes-get-apiv1quotes)
    - [D.4 — Invoices: `GET /api/v1/invoices/`](#d4--invoices-get-apiv1invoices)
    - [D.5 — Jobs: `GET /api/v1/jobs/`](#d5--jobs-get-apiv1jobs)
    - [D.6 — Catalog/Pricebook: `GET /api/v1/catalog/pricebook`](#d6--catalogpricebook-get-apiv1catalogpricebook)
    - [D.7 — Default Limit Change](#d7--default-limit-change)
  - [E. Pattern Reuse Decisions](#e-pattern-reuse-decisions)
  - [F. Shared Module Interfaces](#f-shared-module-interfaces)
    - [`LIST_PAGE_SIZE` constant](#list_page_size-constant)
    - [`PilotPaginator` component props](#pilotpaginator-component-props)
    - [Updated hook signatures](#updated-hook-signatures)
  - [G. Open Questions Resolved](#g-open-questions-resolved)
  - [H. Surface Mockup Reference — Part B (Frontend)](#h-surface-mockup-reference--part-b-frontend)
  - [I. Component Manifest — Part B (Frontend)](#i-component-manifest--part-b-frontend)

---

## A. Input Read Summary

| Input | Key finding |
|---|---|
| `FIX-014` | Defined scope: standardized paginated response, `total` count, filter params, `PilotPaginator` component, filter bars |
| `GET /api/v1/customers/` (openapi_schema_map.md) | Params: `skip`, `limit`, `search`. Returns raw array — **no `total`** |
| `GET /api/v1/quotes` (openapi_schema_map.md) | Params: `skip`, `limit`, `status`. Returns raw array — **no `total`**, no `title_search`, no `customer_search` |
| `GET /api/v1/invoices/` | Params: `offset`, `limit`, `status`, `overdue`, `due_before`, `due_after`. Returns `InvoiceListResponse` with `total` ✅ — missing `customer_search`, `issued_from`, `issued_to` |
| `GET /api/v1/jobs/` (openapi_schema_map.md) | Params: `skip`, `limit`, `tech_id`, `scheduled_date`. Returns raw array — **no `total`**, no `status`, no `customer_search`, no `scheduled_from`/`to` |
| `GET /api/v1/catalog/pricebook` (openapi_schema_map.md) | Params: `skip`, `limit`, `is_active`. Returns raw array — **no `total`**, no text search in OpenAPI (but `usePricebook.ts` sends `search` param — backend may silently ignore it) |
| `useCustomers.ts` | Returns `CustomerListItem[]` directly — hook must be updated to handle `PaginatedResponse<CustomerListItem>` |
| `useQuotes.ts` | Returns `QuoteListItem[]` directly — hook must be updated to handle `PaginatedResponse<QuoteListItem>` |
| `useInvoices.ts` | Already returns `InvoiceListResponse` with `total` ✅ — needs `customer_search`, `issued_from`, `issued_to` additions |
| `useJobs.ts` | Returns `JobListItem[]` directly with **no params** — completely static fetch |
| `usePricebook.ts` | Returns `PricebookItem[]` — sends `search` to API (may be silently ignored); hook needs updating |
| MCP — `customer` table | `display_name`, `first_name`, `last_name`, `company_name`, `email`, `mobile_phone`, `is_active` confirmed |
| MCP — `job_status` codes | `cancelled`, `completed`, `draft`, `in_progress`, `scheduled` confirmed |
| MCP — `quote` table | `title`, `created_at`, `customer_id` confirmed — title_search and date_from/to on `created_at` are valid |
| MCP — `pricebook_item` table | `name`, `description`, `sku`, `is_active` confirmed — text search should cover name + description + sku |

**Critical gap discovered**: `usePricebook.ts` sends `?search=` to the catalog endpoint but the OpenAPI shows no such param. Python Engineer must verify via `postgres-local` MCP whether the backend route currently accepts and processes `search` or silently ignores it before implementing.

---

## B. Migration Plan

**No Alembic migrations required.** All changes are:
1. API response schema additions (new `PaginatedResponse` wrapper + per-entity paginated response types)
2. Query parameter additions to existing route handlers
3. Frontend hook updates + new component + page updates

---

## C. Execution Order

### Part A — Python Engineer (runs first)

| # | Task | File(s) | Entity |
|---|---|---|---|
| 1 | Add `PaginatedResponse` generic schema + 5 entity-specific paginated response types | `backend/api/schemas/schemas.py` | All |
| 2 | Update `customers` list endpoint — add `offset` alias, `status` filter, `PaginatedResponse` wrapper | `backend/api/routes/customers.py` | Customers |
| 3 | Update `quotes` list endpoint — add `offset` alias, `customer_search`, `title_search`, `date_from`/`date_to`, `PaginatedResponse` wrapper | `backend/api/routes/quotes.py` | Quotes |
| 4 | Update `invoices` list endpoint — add `customer_search`, `issued_from`/`issued_to` (existing `InvoiceListResponse` already wraps with `total`) | `backend/api/routes/invoices.py` | Invoices |
| 5 | Update `jobs` list endpoint — add `offset` alias, `status` filter, `customer_search`, `scheduled_from`/`scheduled_to`, `PaginatedResponse` wrapper | `backend/api/routes/jobs.py` | Jobs |
| 6 | Update `catalog/pricebook` list endpoint — add `offset` alias, text `search` (if not already), `PaginatedResponse` wrapper | `backend/api/routes/catalog.py` | Catalog |
| 7 | Regenerate OpenAPI | `python export_openapi_json.py` | All |
| 8 | Run tests | `pytest -m unit` then `pytest` | All |

### Part B — React Engineer (runs after Part A ✅ + `pnpm sync-api-types`)

| # | Task | File(s) | Entity |
|---|---|---|---|
| 1 | Add `LIST_PAGE_SIZE = 25` shared constant | `packages/shared-api/src/constants.ts` | All |
| 2 | Create `<PilotPaginator>` component | `apps/web/src/components/PilotPaginator.tsx` | All |
| 3 | Update `useCustomers` hook — handle `PaginatedResponse`, add filter params | `useCustomers.ts` | Customers |
| 4 | Update `CustomersPage` — replace Load More with PilotPaginator, add filter bar | `CustomersPage.tsx` | Customers |
| 5 | Update `useQuotes` hook — handle `PaginatedResponse`, add filter params | `useQuotes.ts` | Quotes |
| 6 | Update `QuotesPage` — replace Load More with PilotPaginator, add filter bar, status → dropdown | `QuotesPage.tsx` | Quotes |
| 7 | Update `useInvoices` hook — add `customer_search`, `issued_from`, `issued_to` params | `useInvoices.ts` | Invoices |
| 8 | Update `InvoicesPage` — add customer_search and date pickers to existing filter bar | `InvoicesPage.tsx` | Invoices |
| 9 | Update `useJobs` hook — handle `PaginatedResponse`, add filter params | `useJobs.ts` | Jobs |
| 10 | Update `JobsPage` — replace Load More with PilotPaginator, add filter bar | `JobsPage.tsx` | Jobs |
| 11 | Update `usePricebook` hook — handle `PaginatedResponse` | `usePricebook.ts` | Catalog |
| 12 | Update `CatalogPage` — replace Load More with PilotPaginator, add status dropdown | `CatalogPage.tsx` | Catalog |
| 13 | Update MSW handlers | all 5 handler files | All |
| 14 | Write tests | unit + integration | All |

---

## D. New API Endpoint Changes — Part A (Backend)

### D.1 — Shared `PaginatedResponse` Schema

Add to `backend/api/schemas/schemas.py` — a generic wrapper used by all 5 list endpoints:

```python
from typing import TypeVar, Generic

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    """Standardized paginated list response — all list endpoints return this shape."""
    items: list[T]
    total: int       # Total matching rows in DB (for pagination math)
    limit: int
    offset: int      # Canonical name (all endpoints standardize on offset, not skip)
```

Add 5 entity-specific paginated response types (FastAPI requires concrete types for OpenAPI generation):

```python
class PaginatedCustomerResponse(PaginatedResponse[CustomerResponse]): pass
class PaginatedQuoteListResponse(PaginatedResponse[QuoteListItem]): pass
class PaginatedJobListResponse(PaginatedResponse[JobListItem]): pass
class PaginatedCatalogResponse(PaginatedResponse[PricebookItemResponse]): pass
# Note: InvoiceListResponse already exists with total/limit/offset — update it in place (no new class needed)
```

> **Note on `InvoiceListResponse`**: Already has `total`, `limit`, `offset` shape. Python Engineer must read the existing class and verify it matches the pattern before adding any new fields.

---

### D.2 — Customers: `GET /api/v1/customers/`

**Current params**: `skip`, `limit`, `search`  
**New/changed params**: Add `offset` (alias for `skip`; prefer `offset`), add `status` (`active` | `inactive`)  
**Response change**: `list[CustomerResponse]` → `PaginatedCustomerResponse`

```python
@router.get("/", response_model=PaginatedCustomerResponse)
def list_customers(
    skip: int = Query(0, deprecated=True, description="Use offset instead"),
    offset: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=200),
    search: str | None = Query(None),
    status: str | None = Query(None, description="active | inactive"),  # NEW
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
```

**Filter logic**:
- `search`: ILIKE on `display_name`, `first_name`, `last_name`, `company_name`, `email`, `mobile_phone` (already exists — verify current implementation before modifying)
- `status=active` → `Customer.is_active == True`; `status=inactive` → `Customer.is_active == False`
- Resolved `offset`: use `offset` param; if `skip > 0` and `offset == 0`, treat `skip` as `offset` for backward compat
- Return `PaginatedCustomerResponse(items=rows, total=count_query_result, limit=limit, offset=effective_offset)`

**Also update `/test` variant** with same params.

---

### D.3 — Quotes: `GET /api/v1/quotes`

**Current params**: `skip`, `limit`, `status`  
**New/changed params**: Add `offset` alias, `customer_search`, `title_search`, `date_from`, `date_to`  
**Response change**: `list[QuoteListItem]` → `PaginatedQuoteListResponse`

```python
@router.get("", response_model=PaginatedQuoteListResponse)
def list_quotes(
    skip: int = Query(0, deprecated=True),
    offset: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=200),
    status: str | None = Query(None),                          # existing
    customer_search: str | None = Query(None),                 # NEW — ILIKE on customer display_name
    title_search: str | None = Query(None),                    # NEW — ILIKE on quote.title
    date_from: datetime | None = Query(None),                  # NEW — filter on quote.created_at >=
    date_to: datetime | None = Query(None),                    # NEW — filter on quote.created_at <=
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
```

**Filter logic** (AND logic when multiple filters supplied):
- `customer_search`: JOIN on `customer` table → `Customer.display_name.ilike(f"%{customer_search}%")`
- `title_search`: `Quote.title.ilike(f"%{title_search}%")`
- `date_from`: `Quote.created_at >= date_from`
- `date_to`: `Quote.created_at <= date_to`

> MCP-verified: `quote.title` is `character varying` (nullable), `quote.created_at` is `timestamp with time zone`.

**Also update `/test` variant** with same params.

---

### D.4 — Invoices: `GET /api/v1/invoices/`

**Current params**: `offset`, `limit`, `status`, `overdue`, `due_before`, `due_after`  
**New params**: Add `customer_search`, `issued_from`, `issued_to`  
**Response**: `InvoiceListResponse` already has `total` — no structural change, just new filter params

```python
customer_search: str | None = Query(None),    # NEW — ILIKE on customer display_name
issued_from: datetime | None = Query(None),   # NEW — invoice.issued_at >=
issued_to: datetime | None = Query(None),     # NEW — invoice.issued_at <=
```

> MCP-verified: `invoice.issued_at` is `timestamp with time zone` (nullable).

**Note**: Do NOT rename/change `offset`/`limit`/`overdue`/`due_before`/`due_after` — invoices already has correct pagination. Only add the 3 new filter params.

---

### D.5 — Jobs: `GET /api/v1/jobs/`

**Current params**: `skip`, `limit`, `tech_id`, `scheduled_date`  
**New/changed params**: Add `offset` alias, `status`, `customer_search`, `scheduled_from`, `scheduled_to`  
**Response change**: `list[JobListItem]` → `PaginatedJobListResponse`

```python
@router.get("/", response_model=PaginatedJobListResponse)
def list_jobs(
    skip: int = Query(0, deprecated=True),
    offset: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=200),
    tech_id: UUID | None = Query(None),                        # existing
    scheduled_date: str | None = Query(None),                  # existing — keep for dispatch board compat
    status: str | None = Query(None),                          # NEW — filter by job_status.code
    customer_search: str | None = Query(None),                 # NEW — ILIKE on customer display_name
    scheduled_from: datetime | None = Query(None),             # NEW — job.scheduled_start_at >=
    scheduled_to: datetime | None = Query(None),               # NEW — job.scheduled_start_at <=
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
```

> **Warning**: `scheduled_date` is used by the dispatch board (`GET /api/v1/jobs/?scheduled_date=YYYY-MM-DD`). Do NOT remove it. The new `scheduled_from`/`scheduled_to` are for the JobsPage filter bar. Both can be active simultaneously.

**Also update `/test` variant** with same params.

---

### D.6 — Catalog/Pricebook: `GET /api/v1/catalog/pricebook`

**Current params**: `skip`, `limit`, `is_active`  
**New/changed params**: Add `offset` alias, text `search` (verify current backend behavior first — if search already silently exists, just document it; if not, add it), change response to `PaginatedCatalogResponse`

```python
@router.get("", response_model=PaginatedCatalogResponse)
def list_pricebook_items(
    skip: int = Query(0, deprecated=True),
    offset: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=200),
    is_active: bool = Query(True),                 # existing
    search: str | None = Query(None),              # NEW (or already exists — verify first)
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
```

**`search` filter**: ILIKE on `PricebookItem.name`, `PricebookItem.description`, `PricebookItem.sku`

> MCP-verified: `pricebook_item` has `name` (varchar), `description` (varchar), `sku` (varchar) — all searchable.

---

### D.7 — Default Limit Change

**All endpoints change default `limit` from `100` to `25`**. This is the `LIST_PAGE_SIZE` constant. Existing callers (dispatch board, public invoice, mobile sync) that call these endpoints programmatically should not rely on the default limit — they explicitly pass their own limit. The dispatch board uses `?limit=200` or similar to get all jobs for a date; this is unaffected since the new default is smaller but explicit callers set their own.

---

## E. Pattern Reuse Decisions

| Pattern | Decision |
|---|---|
| Tenant-scoped `select()` | All new filter queries must include `WHERE tenant_id = current_user.tenant_id`. No `db.get()`. |
| `offset` + backward-compat `skip` | Add `offset` as canonical param; `skip` stays as deprecated alias. Logic: `effective_offset = offset if offset > 0 else skip` |
| Count query | Use `SELECT COUNT(*)` with the same filter clauses before the LIMIT/OFFSET fetch to get `total`. SQLAlchemy: `db.exec(select(func.count(Entity.id)).where(...)).one()` |
| `LIST_PAGE_SIZE = 25` | FE-only constant in `packages/shared-api/src/constants.ts`. All 5 page components import from here. |
| PilotPaginator — no `packages/ui/` | The paginator is web-only (not used in mobile or marketing). Lives in `apps/web/src/components/PilotPaginator.tsx`. Mobile has its own infinite-scroll pattern. |
| Filter submission — explicit Search button | Filter inputs do NOT auto-trigger on keystroke. User clicks "Search" to apply. "Clear" resets to defaults. This prevents API spam during typing. |
| Status filter → dropdown | All 5 pages convert status filter pills to `<select>` dropdown per FIX-014 design decision. Default: `""` = All. |
| Sorting — deferred | Column sort remains client-side only (current page). `?sort_by=&sort_dir=` deferred to UI-FIX-1D / Phase 1.5. |
| `InvoicesPage` Overdue toggle preserved | The "Overdue Only" toggle (`?overdue=true`) stays as-is. The new filter bar adds to it, not replacing it. |

---

## F. Shared Module Interfaces

### `LIST_PAGE_SIZE` constant

```typescript
// packages/shared-api/src/constants.ts
export const LIST_PAGE_SIZE = 25;
```

### `PilotPaginator` component props

```typescript
// apps/web/src/components/PilotPaginator.tsx
interface PilotPaginatorProps {
  total: number;       // Total items from API response
  limit: number;       // Items per page
  offset: number;      // Current offset
  onPageChange: (newOffset: number) => void;
}
```

Behavior:
- `<<` → `offset = 0`
- `<` → `offset = max(0, current - limit)`
- `>` → `offset = min(lastPage * limit, current + limit)`
- `>>` → `offset = Math.floor((total - 1) / limit) * limit`
- Center: `Page X of Y` where `X = Math.floor(offset / limit) + 1`, `Y = Math.ceil(total / limit)`
- The page number is an `<input type="number">` — user can type and press Enter to jump
- Disabled state at boundaries
- Renders nothing when `total <= limit` (single page)

### Updated hook signatures

All 4 hooks that currently return a raw array must be updated to return a `PaginatedResponse<T>`:

```typescript
// Generic paginated response shape (matches backend PaginatedResponse)
interface PaginatedResult<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}
```

**Specific hook signature updates:**

```typescript
// useCustomers — adds status param, returns PaginatedResult
useCustomers({ offset?, limit?, search?, status? })
  → PaginatedResult<CustomerListItem>

// useQuotes — adds more filter params, returns PaginatedResult
useQuotes({ offset?, limit?, status?, customer_search?, title_search?, date_from?, date_to? })
  → PaginatedResult<QuoteListItem>

// useInvoices — adds 3 new filter params (existing shape stays)
useInvoices({ offset?, limit?, status?, overdue?, due_before?, due_after?, customer_search?, issued_from?, issued_to? })
  → InvoiceListResponse (existing, already has total)

// useJobs — adds many filter params, returns PaginatedResult
useJobs({ offset?, limit?, tech_id?, scheduled_date?, status?, customer_search?, scheduled_from?, scheduled_to? })
  → PaginatedResult<JobListItem>

// usePricebook — returns PaginatedResult
usePricebook({ offset?, limit?, search?, status? })
  → PaginatedResult<PricebookItem>
```

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| Does `usePricebook.ts` `search` param actually work on the backend? | Python Engineer must verify: `grep -n "search" backend/api/routes/catalog.py` to check current implementation before adding. If it already works but wasn't in OpenAPI, just document it. If not, add the ILIKE filter. |
| Should `skip` be completely removed or kept as alias? | Keep as deprecated alias (`Query(0, deprecated=True)`). This protects any other internal consumers that may use `skip`. Remove in a future cleanup batch. |
| Should the `scheduled_date` dispatch board param be kept? | Yes — the dispatch board uses `?scheduled_date=YYYY-MM-DD` to filter jobs for a specific day. The new `scheduled_from`/`scheduled_to` are range params for the JobsPage filter bar. Both coexist — they're AND-combined if both present. |
| Does the `InvoicesPage` Overdue toggle need changing? | No — `?overdue=true` returns all overdue invoices. The aging column (FIX-010b, done in UI-FIX-1B) shows the bucket. The new `customer_search` + `issued_from`/`issued_to` are additions to the existing filter bar. |
| Where does `PilotPaginator` live? | `apps/web/src/components/PilotPaginator.tsx` — NOT in `packages/ui/`. It's web-specific (uses `next/link` or client state). Mobile has its own scroll patterns. |
| Should `InvoiceListResponse` be renamed to `PaginatedInvoiceResponse`? | No — rename causes too much churn in the frontend (InvoiceListResponse is imported in multiple files). Keep existing name, just add the new filter params to the route handler. |
| Default `limit` change 100 → 25 — any dispatch board breakage? | The dispatch board calls `GET /api/v1/jobs/?scheduled_date=X` and consumes all results for that date. It does NOT rely on the default limit — all scheduling-related fetches should use `?limit=200` or similar. Python Engineer must grep dispatch board callers before changing the default and add explicit limits where needed. |

---

## H. Surface Mockup Reference — Part B (Frontend)

No new surfaces. All 5 pages are modifications of existing list pages.

| Surface | Platform | Filter Bar Inputs | Status Dropdown Options |
|---|---|---|---|
| Customers (`/customers`) | Web | Text: "Search by name, email, phone…" | Active / Inactive / All |
| Quotes (`/quotes`) | Web | Text: "Customer name…" + Text: "Quote title…" + Date From/To | All statuses from STATUS_FILTERS + convert pills → dropdown |
| Invoices (`/invoices`) | Web | Text: "Customer name…" + Date (Issued From/To) | Keep existing status pills (not converted — invoices page already has more complex filter UI) |
| Jobs (`/jobs`) | Web | Text: "Customer name…" + Date (Scheduled From/To) | Draft / Scheduled / In Progress / Completed / Cancelled / All |
| Catalog (`/catalog`) | Web | Text: "Search name, SKU, description…" | Active / Inactive / All |

**Design constraints** (from FIX-014):
- Filter bar above the table
- "Search" button — explicit submit, NOT on-keystroke
- "Clear" button — resets all fields + re-fetches
- Status is `<select>` dropdown (not pills) for all pages where pills existed
- Exception: `InvoicesPage` keeps existing status pills — its filter UI is already more complex and changing it would break existing tests

---

## I. Component Manifest — Part B (Frontend)

| File | Change Type | Notes |
|---|---|---|
| `packages/shared-api/src/constants.ts` | Create or Update | Add `LIST_PAGE_SIZE = 25` |
| `apps/web/src/components/PilotPaginator.tsx` | **Create** | New shared web paginator component |
| `apps/web/src/components/__tests__/PilotPaginator.test.tsx` | **Create** | Unit tests for paginator |
| `apps/web/src/features/customers/hooks/useCustomers.ts` | Update | Add `status`, `offset` params; return `PaginatedResult` |
| `apps/web/src/features/customers/components/CustomersPage.tsx` | Update | Filter bar + PilotPaginator + replace Load More |
| `apps/web/src/features/quotes/hooks/useQuotes.ts` | Update | Add filter params; return `PaginatedResult` |
| `apps/web/src/features/quotes/components/QuotesPage.tsx` | Update | Filter bar + PilotPaginator + status → dropdown + replace Load More |
| `apps/web/src/features/invoices/hooks/useInvoices.ts` | Update | Add `customer_search`, `issued_from`, `issued_to` params |
| `apps/web/src/features/invoices/components/InvoicesPage.tsx` | Update | Add customer search + date inputs to filter bar; add PilotPaginator |
| `apps/web/src/features/jobs/hooks/useJobs.ts` | Update | Add all filter params; return `PaginatedResult` |
| `apps/web/src/features/jobs/components/JobsPage.tsx` | Update | Filter bar + PilotPaginator + replace Load More |
| `apps/web/src/features/catalog/hooks/usePricebook.ts` | Update | Add `offset`; return `PaginatedResult` |
| `apps/web/src/features/catalog/components/CatalogPage.tsx` | Update | Filter bar + PilotPaginator + status → dropdown + replace Load More |
| MSW handlers (5 files) | Update | All 5 list handlers must return `{ items: [...], total: N, limit: 25, offset: 0 }` |
