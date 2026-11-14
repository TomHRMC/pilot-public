# Batch Design: UI-FIX-2D — Customer Detail Jobs / Quotes / Invoices Tabs

**Source decisions**: `dev-docs/architecture-design/batch-designs/ui-fix-2-decisions.md § FIX-018`  
**Batch type**: Mixed — Backend (Python Engineer first) + Frontend (React Engineer second)  
**Estimated effort**: ~3h BE + ~4–5h FE = ~7–8h total  
**Depends on**: None — independent of UI-FIX-2B  
**Status**: ⏳ Pending

---

## A. Input Read Summary

| Input | Key finding |
|---|---|
| `ui-fix-2-decisions.md § FIX-018` | Full root cause, decision, backend + frontend changes, UX wireframe — fully resolved |
| MCP: `job` table (2026-07-21) | `customer_id uuid NOT NULL` ✅ confirmed |
| MCP: `quote` table (2026-07-21) | `customer_id uuid NOT NULL` ✅ confirmed |
| MCP: `invoice` table (2026-07-21) | `customer_id uuid NOT NULL` ✅ confirmed |
| `backend/api/routes/jobs.py` | `_list_jobs_impl()` already JOINs Customer; `?customer_search=` ILIKE exists; `?customer_id=` missing |
| `backend/api/routes/quotes.py` | Same pattern — `?customer_search=` ILIKE exists; `?customer_id=` missing |
| `backend/api/routes/invoices.py` | Same pattern — `?customer_search=` ILIKE exists; `?customer_id=` missing |
| Frontend source | `CustomerJobsList`, `CustomerQuotesList`, `CustomerInvoicesList` all render `<CustomerTabDeferredState>` placeholder — no data fetching |

---

## B. Migration Plan

**No Alembic migration required.** All three tables already have `customer_id uuid NOT NULL` confirmed via MCP.

This batch is a **query parameter addition only** — adding `?customer_id=<uuid>` to 3 existing list endpoints.

**MCP pre-work verification queries for the Python Engineer:**

```sql
-- 1. Confirm customer_id on job table
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'job'
  AND column_name IN ('id', 'customer_id', 'tenant_id')
ORDER BY column_name;

-- 2. Confirm customer_id on quote table
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'quote'
  AND column_name IN ('id', 'customer_id', 'tenant_id')
ORDER BY column_name;

-- 3. Confirm customer_id on invoice table
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'invoice'
  AND column_name IN ('id', 'customer_id', 'tenant_id')
ORDER BY column_name;

-- 4. Confirm current alembic head
SELECT version_num FROM public.alembic_version;
```

---

## C. Execution Order

| Step | What | File(s) | Engineer |
|---|---|---|---|
| 1 | Add `?customer_id=` param to `_list_jobs_impl()` | `backend/api/routes/jobs.py` | Python |
| 2 | Add `?customer_id=` param to `_list_quotes_impl()` | `backend/api/routes/quotes.py` | Python |
| 3 | Add `?customer_id=` param to `_list_invoices_impl()` | `backend/api/routes/invoices.py` | Python |
| 4 | Regenerate `openapi.json` + `openapi_schema_map.md` | `backend/export_openapi_json.py` | Python |
| 5 | Write BE unit tests for all 3 new filter params | `backend/tests/domains/field_operations/test_ui_fix_2d_customer_filter.py` | Python |
| 6 | **Handoff**: Python Engineer runs `python export_openapi_json.py`, commits | — | Python |
| 7 | React Engineer runs `pnpm sync-api-types` | — | React |
| 8 | Add `customer_id?: string` to `useJobs` hook | `apps/web/src/features/jobs/hooks/useJobs.ts` | React |
| 9 | Add `customer_id?: string` to `useQuotes` hook | `apps/web/src/features/quotes/hooks/useQuotes.ts` | React |
| 10 | Add `customer_id?: string` to `useInvoices` hook | `apps/web/src/features/invoices/hooks/useInvoices.ts` | React |
| 11 | Rewrite `CustomerJobsList.tsx` with real data | `apps/web/src/features/customers/components/CustomerJobsList.tsx` | React |
| 12 | Rewrite `CustomerQuotesList.tsx` with real data | `apps/web/src/features/customers/components/CustomerQuotesList.tsx` | React |
| 13 | Rewrite `CustomerInvoicesList.tsx` with real data | `apps/web/src/features/customers/components/CustomerInvoicesList.tsx` | React |
| 14 | Update MSW handlers for jobs/quotes/invoices to support `?customer_id=` | `apps/web/src/mocks/handlers/` | React |
| 15 | Write unit + integration tests | `apps/web/src/__tests__/batch_ui_fix_2d/` | React |

---

## D. New API Endpoints

**No new endpoints.** Three existing list endpoints gain one new optional query parameter each.

### `GET /api/v1/jobs/`

**New param**: `customer_id: uuid.UUID | None = Query(None)`

```python
# backend/api/routes/jobs.py — in _list_jobs_impl():
# Add alongside existing customer_search param:
customer_id: uuid.UUID | None = Query(None, description="Filter jobs by exact customer UUID")

# Add filter clause (AFTER tenant_id scope, BEFORE customer_search):
if customer_id:
    statement = statement.where(Job.customer_id == customer_id)
    count_statement = count_statement.where(Job.customer_id == customer_id)
```

### `GET /api/v1/quotes/`

**New param**: `customer_id: uuid.UUID | None = Query(None)`

```python
# backend/api/routes/quotes.py — in _list_quotes_impl():
customer_id: uuid.UUID | None = Query(None, description="Filter quotes by exact customer UUID")

if customer_id:
    statement = statement.where(Quote.customer_id == customer_id)
    count_statement = count_statement.where(Quote.customer_id == customer_id)
```

### `GET /api/v1/invoices/`

**New param**: `customer_id: uuid.UUID | None = Query(None)`

```python
# backend/api/routes/invoices.py — in _list_invoices_impl():
customer_id: uuid.UUID | None = Query(None, description="Filter invoices by exact customer UUID")

if customer_id:
    query = query.where(Invoice.customer_id == customer_id)
    count_query = count_query.where(Invoice.customer_id == customer_id)
```

**Important**: Apply the `customer_id` filter to BOTH the main data query AND the count query — the count is used for `PaginatedResponse.total` (pagination math breaks if count is unfiltered).

Both the authenticated (`/api/v1/...`) and the test (`/api/v1/.../test`) endpoint variants must receive the new param.

---

## E. Pattern Reuse Decisions

| Pattern | Applied How |
|---|---|
| `mvp-arch.md §16` — server-side filter pattern | Same `?customer_id=uuid` approach used by all 5 entity list endpoints (established in UI-FIX-1C) |
| `PilotPaginator` | Preserved in all 3 customer-scoped tabs — pagination stays functional |
| Filter bars from `JobsPage`/`QuotesPage`/`InvoicesPage` | Customer filter input **hidden**; all other filters (status, dates, title search) **visible** |
| `<CustomerTabDeferredState>` | **Deleted** once 3 components are rewritten — it only existed as a placeholder |

---

## F. Shared Module Interfaces

### Hook signature changes

```typescript
// useJobs.ts — add to UseJobsOptions:
customer_id?: string;  // When set, passes ?customer_id= to API; hides customer search in consumer

// useQuotes.ts — add to UseQuotesOptions:
customer_id?: string;

// useInvoices.ts — add to UseInvoicesOptions:
customer_id?: string;
```

### `CustomerJobsList` component interface (after rewrite)

```typescript
// apps/web/src/features/customers/components/CustomerJobsList.tsx
interface CustomerJobsListProps {
  customerId: string;
}
// Renders jobs list scoped to this customer — same UX as JobsPage but:
//   - customer search input hidden
//   - status filter, date range pickers, Search/Clear buttons visible
//   - PilotPaginator for pagination
//   - "+ New Job" button links to /jobs/new?customer_id=${customerId}
//   - Customer column omitted (redundant — we're on their page)
```

### `CustomerQuotesList` component interface (after rewrite)

```typescript
interface CustomerQuotesListProps {
  customerId: string;
}
// Same pattern — shows Quote #, Title, Status, Total, Created
// Customer column omitted; "+ New Quote" links to /quotes/new?customer_id=${customerId}
```

### `CustomerInvoicesList` component interface (after rewrite)

```typescript
interface CustomerInvoicesListProps {
  customerId: string;
}
// Same pattern — shows Invoice #, Status, Aging, Total, Balance Due, Due Date
// Customer column omitted; "+ New Invoice" links to /invoices/new?customer_id=${customerId}
```

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| Why not use `?customer_search=` pre-filled with the customer name? | Brittle: name collisions, ILIKE edge cases, URL hygiene. UUID equality filter is correct for scoped views. |
| Should the Customer column be hidden or shown? | **Hidden** — it is redundant and wastes space when already on a customer's detail page. |
| Should pagination be preserved in the tab views? | **Yes** — `PilotPaginator` is already built and shared. Use it. |
| Should filters other than customer be hidden? | **No** — status, date range, and title search are all useful within a single customer's records. Keep them. Hide only the customer search input. |
| Should `+ New [Entity]` buttons appear in the tabs? | **Yes** — pre-seeded with `?customer_id=` so the creation form opens with this customer pre-selected. RBAC gates apply (same permissions as the main list pages). |
| Does `customer_id` need to be added to the count query too? | **Yes, mandatory** — `PaginatedResponse.total` drives the page count calculation. If the count is unfiltered, pagination shows wrong page counts. |
| Where does `customerId` come from in the tab components? | From the `[id]` route param — the customer detail layout already passes it. Read `customers/[id]/layout.tsx` before implementing to confirm the exact prop chain. |

---

## H. Surface Mockup Reference

Per `ui-fix-2-decisions.md § FIX-018 — UX Details`:

```
Jobs for: Apex Commercial LLC
───────────────────────────────────────────────────────────
[Status ▾ All]  [From: __/__/__]  [To: __/__/__]  [Search] [Clear]   [+ New Job]
───────────────────────────────────────────────────────────
Job #       Status      Scheduled           Duration
JOB-000001  Scheduled   Jul 24, 2026 9:00   4h
JOB-000003  Completed   Jul 10, 2026 8:30   6h
───────────────────────────────────────────────────────────
<< < Page 1 of 1 > >>
```

- No customer name search input (locked to UUID)
- All other filters visible and functional
- `+ New [Entity]` button with `?customer_id=` pre-seed
- Empty state: "No jobs for this customer yet. [+ Create Job]"

---

## I. Component Manifest

| Component / Hook | Destination Path | Action |
|---|---|---|
| `useJobs.ts` | `apps/web/src/features/jobs/hooks/useJobs.ts` | **Update** — add `customer_id?` param |
| `useQuotes.ts` | `apps/web/src/features/quotes/hooks/useQuotes.ts` | **Update** — add `customer_id?` param |
| `useInvoices.ts` | `apps/web/src/features/invoices/hooks/useInvoices.ts` | **Update** — add `customer_id?` param |
| `CustomerJobsList.tsx` | `apps/web/src/features/customers/components/CustomerJobsList.tsx` | **Rewrite** — real data, customer filter hidden |
| `CustomerQuotesList.tsx` | `apps/web/src/features/customers/components/CustomerQuotesList.tsx` | **Rewrite** — real data, customer filter hidden |
| `CustomerInvoicesList.tsx` | `apps/web/src/features/customers/components/CustomerInvoicesList.tsx` | **Rewrite** — real data, customer filter hidden |
| `CustomerTabDeferredState.tsx` | `apps/web/src/features/customers/components/CustomerTabDeferredState.tsx` | **Delete** — placeholder no longer needed |
| MSW handlers (jobs, quotes, invoices) | `apps/web/src/mocks/handlers/` | **Update** — add `customer_id` filter support |
