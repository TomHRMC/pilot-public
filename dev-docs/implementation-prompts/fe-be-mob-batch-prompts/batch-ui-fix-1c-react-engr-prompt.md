# Implementation Prompt: UI-FIX-1C Part B — Server-Side Pagination & Filters (Frontend)

**Mode**: Pilot React Engineer  
**Batch**: UI-FIX-1C — Part B (Frontend)  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §UI Fix — Batch 1  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-ui-fix-1c-design.md`  
**Estimated session**: 9–10 hours  
**Platform**: Web only (`apps/web`)  
**Backend companion**: UI-FIX-1C Part A ✅ must be complete — `pnpm sync-api-types` **REQUIRED** before starting

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-ui-fix-1c-design.md`** — every section (A–I)

**Critical rules for this batch:**

- **Rule 1.1**: Before writing ANY hook or API call, verify the endpoint + params exist in `backend/openapi_schema_map.md`. Grep for `PaginatedCustomerResponse`, `customer_search`, `title_search`, `scheduled_from`. If NOT there → **STOP and ask Tom**.
- **Rule 1.2**: Do NOT invent parameter names. Every param name comes from `openapi_schema_map.md`.
- **Rule 1.3**: Run `pnpm sync-api-types` before starting. Part A added `PaginatedResponse` types to the OpenAPI spec.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new component.
- **Rule 8**: No new npm dependencies without checking `package.json`.
- **Rule 9**: Route files in `app/(authed)/` must NOT have `"use client"` or data fetching.
- **Rule 10**: If ANY test fails — fix it before declaring done.

**Pagination offset vs skip:**  
All 4 hooks that previously sent `?skip=` now send `?offset=`. The backend accepts both but `offset` is canonical. Update hook params accordingly.

**`InvoicesPage` exception:**  
`InvoicesPage` keeps its existing status filter pills (NOT converted to dropdown). The filter bar adds `customer_search` + date pickers alongside the existing UI. Do NOT restructure the invoices page filter UI beyond adding these inputs.

---

## Design Decisions (Do Not Re-Litigate)

| Decision | Outcome | Rationale |
|---|---|---|
| `PilotPaginator` location | `apps/web/src/components/PilotPaginator.tsx` | Web-specific; not in `packages/ui/` |
| Filter submit | Explicit "Search" button — NOT on-keystroke | Prevents API spam during typing |
| Status filter | `<select>` dropdown for Customers, Quotes, Jobs, Catalog | Replaces pills on those 4 pages |
| `InvoicesPage` status filter | Keep existing pills — no change | Already complex filter UI; changing it breaks existing tests |
| Sorting | Client-side only (current page) | Server-side sort deferred to Phase 1.5 |
| `LIST_PAGE_SIZE = 25` | Single constant in `packages/shared-api/src/constants.ts` | All 5 page components import from here |
| `PilotPaginator` hidden when single page | `total <= limit` → render nothing | Avoids pagination controls for small datasets |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend

pnpm --filter web test 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**. Fix any failures before starting.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

Verify the new paginated types exist:

```bash
grep -n "PaginatedCustomerResponse\|PaginatedQuoteList\|PaginatedJob\|PaginatedCatalog\|customer_search\|title_search" frontend/packages/shared-types/src/api-schema.d.ts | head -20
```

> **If `pnpm sync-api-types` fails** (backend not running): write local stubs marked `// TODO: replace with @pilot/shared-types when pnpm sync-api-types delivers this type`. Do not block work.

---

## Pre-Work: Verify Endpoints

```bash
# Verify all new params are in the spec
grep -A 20 "GET /api/v1/customers/" backend/openapi_schema_map.md | head -25
grep -A 20 "GET /api/v1/quotes" backend/openapi_schema_map.md | head -25
grep -A 20 "GET /api/v1/jobs/" backend/openapi_schema_map.md | head -25
grep -A 20 "GET /api/v1/catalog/pricebook" backend/openapi_schema_map.md | head -25

# Confirm PaginatedResponse in spec
grep -A 5 "PaginatedCustomerResponse\|PaginatedJobList" backend/openapi_schema_map.md | head -20
```

**All endpoints confirmed from design doc (verify after Part A runs):**

| Hook | Endpoint | New params | Verified |
|---|---|---|---|
| `useCustomers` | `GET /api/v1/customers/` | `offset`, `status` | Verify after Part A |
| `useQuotes` | `GET /api/v1/quotes` | `offset`, `customer_search`, `title_search`, `date_from`, `date_to` | Verify after Part A |
| `useInvoices` | `GET /api/v1/invoices/` | `customer_search`, `issued_from`, `issued_to` | Verify after Part A |
| `useJobs` | `GET /api/v1/jobs/` | `offset`, `status`, `customer_search`, `scheduled_from`, `scheduled_to` | Verify after Part A |
| `usePricebook` | `GET /api/v1/catalog/pricebook` | `offset`, `search` (verify exists) | Verify after Part A |

---

## Pre-Work: Read These Source Files

```
frontend/apps/web/src/features/customers/hooks/useCustomers.ts
  ← current params, return type (currently CustomerListItem[])

frontend/apps/web/src/features/customers/components/CustomersPage.tsx
  ← current Load More pattern + filter bar structure

frontend/apps/web/src/features/quotes/hooks/useQuotes.ts
  ← current params, return type (currently QuoteListItem[])

frontend/apps/web/src/features/quotes/components/QuotesPage.tsx
  ← current Load More + STATUS_FILTERS pills

frontend/apps/web/src/features/invoices/hooks/useInvoices.ts
  ← current params (already has offset + total)

frontend/apps/web/src/features/invoices/components/InvoicesPage.tsx
  ← existing filter bar structure (keep pills, add new inputs)

frontend/apps/web/src/features/jobs/hooks/useJobs.ts
  ← currently has NO params — completely static fetch

frontend/apps/web/src/features/jobs/components/JobsPage.tsx
  ← understand current structure before adding filter bar

frontend/apps/web/src/features/catalog/hooks/usePricebook.ts
  ← current params + return type

frontend/apps/web/src/features/catalog/components/CatalogPage.tsx
  ← current structure

frontend/apps/web/src/mocks/handlers/index.ts
  ← confirm all handlers before adding/modifying

packages/shared-api/src/constants.ts (or index.ts)
  ← find correct file to add LIST_PAGE_SIZE
```

Also run:

```bash
# Find all 5 list page handler files
find frontend/apps/web/src/mocks/handlers -name "*.ts" | head -20

# Find packages/shared-api exports
ls frontend/packages/shared-api/src/

# Confirm component location for Jobs page
find frontend/apps/web/src/features/jobs/components -name "*.tsx" | head -10

# Confirm constants file location
find frontend/packages/shared-api/src -name "constants.ts" | head -5
```

---

## Context: What This Batch Does

| Entity | Hook change | Page change |
|---|---|---|
| Customers | `skip→offset`, `status`, returns `PaginatedResult` | Filter bar (search + status dropdown) + `PilotPaginator` + remove Load More |
| Quotes | `skip→offset`, 4 new filters, returns `PaginatedResult` | Filter bar (customer + title + dates + status dropdown) + `PilotPaginator` + remove Load More |
| Invoices | Add 3 new filter params to existing hook | Add customer search + date inputs to existing filter bar + `PilotPaginator` |
| Jobs | Completely new params, returns `PaginatedResult` | Filter bar (customer + status + dates) + `PilotPaginator` + remove Load More (if it exists) |
| Catalog | `skip→offset`, returns `PaginatedResult` | Filter bar (search + active/inactive dropdown) + `PilotPaginator` + remove Load More |

---

## STEP 1 — Shared Infrastructure

### Step 1a — Add `LIST_PAGE_SIZE` constant

Find the correct file in `packages/shared-api/src/` (check with `ls frontend/packages/shared-api/src/`). Add:

```typescript
export const LIST_PAGE_SIZE = 25;
```

### Step 1b — Create `PilotPaginator` component

**File**: `apps/web/src/components/PilotPaginator.tsx`

```typescript
"use client";

import React from "react";

interface PilotPaginatorProps {
  total: number;
  limit: number;
  offset: number;
  onPageChange: (newOffset: number) => void;
}

export function PilotPaginator({ total, limit, offset, onPageChange }: PilotPaginatorProps) {
  if (total <= limit) return null; // Hide when all results fit on one page

  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(total / limit);
  const lastOffset = Math.floor((total - 1) / limit) * limit;

  const [inputPage, setInputPage] = React.useState(String(currentPage));

  React.useEffect(() => {
    setInputPage(String(currentPage));
  }, [currentPage]);

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    setInputPage(e.target.value);
  }

  function handleInputKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      const page = parseInt(inputPage, 10);
      if (!isNaN(page) && page >= 1 && page <= totalPages) {
        onPageChange((page - 1) * limit);
      } else {
        setInputPage(String(currentPage)); // reset invalid input
      }
    }
  }

  const btnClass = "px-2 py-1 text-sm text-neutral-600 border border-neutral-200 rounded hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed";

  return (
    <div className="flex items-center gap-2 mt-4 justify-center" data-testid="pilot-paginator">
      <button className={btnClass} onClick={() => onPageChange(0)} disabled={offset === 0} aria-label="First page">«</button>
      <button className={btnClass} onClick={() => onPageChange(Math.max(0, offset - limit))} disabled={offset === 0} aria-label="Previous page">‹</button>
      <span className="flex items-center gap-1 text-sm text-neutral-600">
        Page{" "}
        <input
          type="number"
          value={inputPage}
          onChange={handleInputChange}
          onKeyDown={handleInputKeyDown}
          className="w-12 px-1 py-0.5 text-center border border-neutral-300 rounded text-sm"
          min={1}
          max={totalPages}
          aria-label="Page number"
        />
        {" "}of {totalPages}
      </span>
      <button className={btnClass} onClick={() => onPageChange(offset + limit)} disabled={offset + limit >= total} aria-label="Next page">›</button>
      <button className={btnClass} onClick={() => onPageChange(lastOffset)} disabled={offset >= lastOffset} aria-label="Last page">»</button>
    </div>
  );
}
```

> Read the file first if it already exists. Adjust class names to use exact Pilot design tokens found in the codebase.

**Intermediate verification:**
```bash
pnpm --filter web test -- apps/web/src/components 2>&1 | tail -6
```

---

## STEP 2 — Customers

### Step 2a — Update `useCustomers.ts`

Add `status` param, change `skip` → `offset`, update return type to `PaginatedResult<CustomerListItem>`:

```typescript
// Define locally until pnpm sync-api-types delivers this
interface PaginatedResult<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

interface UseCustomersOptions {
  offset?: number;
  limit?: number;
  search?: string;
  status?: "active" | "inactive" | "";  // empty string = All
}

export const CUSTOMERS_QUERY_KEY = (offset: number, limit: number, search?: string, status?: string) =>
  ["customers", offset, limit, search ?? "", status ?? ""] as const;

export function useCustomers({ offset = 0, limit = LIST_PAGE_SIZE, search, status }: UseCustomersOptions = {}) {
  return useQuery({
    queryKey: CUSTOMERS_QUERY_KEY(offset, limit, search, status),
    queryFn: async (): Promise<PaginatedResult<CustomerListItem>> => {
      const params: Record<string, unknown> = { offset, limit };
      if (search?.trim()) params.search = search.trim();
      if (status) params.status = status;
      const res = await apiClient.get("/api/v1/customers/", { params });
      return res.data as PaginatedResult<CustomerListItem>;
    },
    staleTime: 60_000,
  });
}
```

### Step 2b — Update `CustomersPage.tsx`

Read the current file first. Add filter bar + replace Load More with `<PilotPaginator>`:

1. Import `LIST_PAGE_SIZE` from `@pilot/shared-api`
2. Replace `skip` state with `offset` state
3. Add `customerSearch`, `statusFilter` state for filter bar inputs
4. Add `appliedCustomerSearch`, `appliedStatusFilter` state for submitted values
5. Update `useCustomers` call to use `offset` + applied filter values
6. Add filter bar JSX above the table:
   - Text input: "Search by name, email, phone…" → `customerSearch` state
   - Status `<select>`: `""` = All / `"active"` = Active / `"inactive"` = Inactive
   - "Search" button → sets applied state, resets `offset` to 0
   - "Clear" button → resets all state + refetches
7. Remove "Load More" button pattern
8. Add `<PilotPaginator total={data.total} limit={LIST_PAGE_SIZE} offset={offset} onPageChange={setOffset} />` after the table

**Intermediate verification:**
```bash
pnpm --filter web test -- apps/web/src/features/customers 2>&1 | tail -6
```

---

## STEP 3 — Quotes

### Step 3a — Update `useQuotes.ts`

Add 4 new filter params, `skip` → `offset`, return `PaginatedResult<QuoteListItem>`:

```typescript
interface UseQuotesOptions {
  offset?: number;
  limit?: number;
  status?: string;
  customer_search?: string;
  title_search?: string;
  date_from?: string;  // ISO date string YYYY-MM-DD
  date_to?: string;
}
```

Update query key to include all new params. Update `queryFn` to append new params.

### Step 3b — Update `QuotesPage.tsx`

Read the current file first. The `STATUS_FILTERS` array currently drives filter pills — convert to a `<select>` dropdown. Add filter bar:

1. Status: `<select>` with options from STATUS_FILTER values (`""` = All, `"draft"` = Draft, etc.) — same options as current STATUS_FILTERS array
2. Customer search text input
3. Title search text input
4. Date From / Date To `<input type="date">` pair
5. "Search" + "Clear" buttons
6. Remove `STATUS_FILTERS` pills rendering (replaced by select)
7. Replace Load More with `<PilotPaginator>`

> The `STATUS_COLORS` and `STATUS_FILTERS` arrays can stay defined — remove only the pills rendering in JSX. The status column badge still uses `STATUS_COLORS`.

**Intermediate verification:**
```bash
pnpm --filter web test -- apps/web/src/features/quotes 2>&1 | tail -6
```

---

## STEP 4 — Invoices

### Step 4a — Update `useInvoices.ts`

Read the current file. Add 3 new params without changing existing structure:

```typescript
// Add to UseInvoicesOptions interface:
customer_search?: string;
issued_from?: string;  // ISO date string
issued_to?: string;
```

Update query key + queryFn to include new params. The return type stays `InvoiceListResponse` (already has `total`).

### Step 4b — Update `InvoicesPage.tsx`

Read the current file. **Keep existing status pills and Overdue toggle as-is.** Add to the existing filter bar area:

- "Customer name" text input
- "Issued From" + "Issued To" `<input type="date">` pair
- These integrate with the existing "Search" and "Clear" button pattern if it exists, or add new buttons

Add `<PilotPaginator>` after the table (invoices already has `offset`/`total` state — wire it up).

**Intermediate verification:**
```bash
pnpm --filter web test -- apps/web/src/features/invoices 2>&1 | tail -6
```

---

## STEP 5 — Jobs

### Step 5a — Update `useJobs.ts`

Read the current file. Currently has **no params** — complete rewrite of the hook signature:

```typescript
interface UseJobsOptions {
  offset?: number;
  limit?: number;
  tech_id?: string;
  scheduled_date?: string;   // keep for dispatch board compat
  status?: string;
  customer_search?: string;
  scheduled_from?: string;   // ISO date string
  scheduled_to?: string;
}

export const JOBS_QUERY_KEY = (options?: UseJobsOptions) => ["jobs", options ?? {}] as const;

export function useJobs(options: UseJobsOptions = {}) {
  return useQuery({
    queryKey: JOBS_QUERY_KEY(options),
    queryFn: async (): Promise<PaginatedResult<JobListItem>> => {
      const { offset = 0, limit = LIST_PAGE_SIZE, tech_id, scheduled_date, status, customer_search, scheduled_from, scheduled_to } = options;
      const params: Record<string, unknown> = { offset, limit };
      if (tech_id) params.tech_id = tech_id;
      if (scheduled_date) params.scheduled_date = scheduled_date;
      if (status) params.status = status;
      if (customer_search?.trim()) params.customer_search = customer_search.trim();
      if (scheduled_from) params.scheduled_from = scheduled_from;
      if (scheduled_to) params.scheduled_to = scheduled_to;
      const res = await apiClient.get("/api/v1/jobs/", { params });
      return res.data as PaginatedResult<JobListItem>;
    },
    staleTime: 30_000,
  });
}
```

> **Dispatch board compatibility**: The dispatch board may call `useJobs({ scheduled_date: "YYYY-MM-DD", tech_id: "..." })`. The new signature is backward-compatible since options is an object. Verify by `grep -rn "useJobs" frontend/apps/web/src/ --include="*.ts" --include="*.tsx"` to find all callers.

### Step 5b — Update `JobsPage.tsx`

Read the current file. Add filter bar:
- Customer search text input
- Status `<select>`: All / Draft / Scheduled / In Progress / Completed / Cancelled
- Scheduled From / Scheduled To `<input type="date">`
- "Search" + "Clear" buttons
- Remove Load More (if present)
- Add `<PilotPaginator>`

**Intermediate verification:**
```bash
pnpm --filter web test -- apps/web/src/features/jobs 2>&1 | tail -6
```

---

## STEP 6 — Catalog

### Step 6a — Update `usePricebook.ts`

Read the current file. Add `offset` (replacing `skip`), update return type to `PaginatedResult<PricebookItem>`:

```typescript
interface UsePricebookOptions {
  offset?: number;
  limit?: number;
  search?: string;
  status?: "active" | "inactive" | "";
}
```

Update queryFn — send `offset` not `skip`. For status: `is_active = status === "active" ? true : status === "inactive" ? false : undefined`.

### Step 6b — Update `CatalogPage.tsx`

Read the current file. Add filter bar:
- Search text input (name, SKU, description)
- Status `<select>`: All / Active / Inactive
- "Search" + "Clear" buttons
- Remove Load More
- Add `<PilotPaginator>`

**Intermediate verification:**
```bash
pnpm --filter web test -- apps/web/src/features/catalog 2>&1 | tail -6
```

---

## STEP 7 — Update MSW Handlers

All 5 list endpoint MSW handlers must return the new `PaginatedResult` shape instead of a raw array.

For each handler, read the file first, then update the response body:

```typescript
// Before:
return HttpResponse.json([...mockItems]);

// After:
return HttpResponse.json({
  items: [...mockItems],
  total: mockItems.length,
  limit: 25,
  offset: 0,
});
```

> Also ensure mock handlers accept and handle the new query params (e.g., `customer_search`, `status`, `offset`) gracefully — they can ignore them for the default happy-path case.

Verify all 5 handlers are still registered in `index.ts`.

---

## Test Requirements

### Required: `PilotPaginator` unit tests

**File**: `apps/web/src/components/__tests__/PilotPaginator.test.tsx`

```typescript
// Test 1: renders nothing when total <= limit
// Test 2: renders page count correctly (10 items, limit 5 = "Page 1 of 2")
// Test 3: clicking next page calls onPageChange with correct offset
// Test 4: clicking previous page calls onPageChange
// Test 5: << goes to offset 0, >> goes to last page offset
// Test 6: first/last buttons disabled at boundaries
// Test 7: typing page number + Enter jumps to that page
```

### Required: Integration tests for 2 of the 5 pages

**File**: `apps/web/src/__tests__/batch_ui_fix_1c/pagination_customers.integration.test.tsx`  
**File**: `apps/web/src/__tests__/batch_ui_fix_1c/pagination_jobs.integration.test.tsx`

Minimum per test file:
1. Page renders with paginator when `total > limit`
2. Paginator hidden when `total <= limit`
3. Search button triggers hook refetch with correct params
4. Clear button resets state

### Hook query key tests

Update existing query key tests in:
- `features/customers/hooks/__tests__/useCustomers.test.ts` — add new params to query key tests
- `features/quotes/hooks/__tests__/useQuotes.test.ts` — add new params
- `features/jobs/hooks/__tests__/useJobs.test.ts` (create if missing) — test new params

### TanStack Query setup

Always use `retry: false`:
```typescript
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
```

### Next.js mocks for web tests

```typescript
vi.mock("next/navigation", () => ({
  usePathname: () => "/customers",
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: any) => React.createElement("a", { href, ...rest }, children),
}));
```

---

## Final Verification

> ❌ **BANNED**: `npx vitest run` — use `pnpm --filter web test` only.

### Phase 1 — Targeted tests

```bash
cd <repo>/frontend

pnpm --filter web test -- apps/web/src/components 2>&1 | tail -6
pnpm --filter web test -- apps/web/src/features/customers 2>&1 | tail -6
pnpm --filter web test -- apps/web/src/features/quotes 2>&1 | tail -6
pnpm --filter web test -- apps/web/src/features/invoices 2>&1 | tail -6
pnpm --filter web test -- apps/web/src/features/jobs 2>&1 | tail -6
pnpm --filter web test -- apps/web/src/features/catalog 2>&1 | tail -6
pnpm --filter web test -- apps/web/src/__tests__/batch_ui_fix_1c 2>&1 | tail -8
```

### Phase 2 — Full verification

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — UI-FIX-1C Part B

Update `ui-fix-1-decisions.md` §Implementation Batches when complete:

- [ ] Regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — paginated types visible in `@pilot/shared-types`
- [ ] Design doc fully read (sections A–I)
- [ ] All mandatory source files read before modifying
- [ ] All endpoint URLs + new params verified in `openapi_schema_map.md`
- [ ] All `useJobs` callers audited (dispatch board, etc.) — confirm backward compat
- [ ] **Step 1a**: `LIST_PAGE_SIZE = 25` added to `packages/shared-api/src/constants.ts`
- [ ] **Step 1b**: `PilotPaginator.tsx` created — renders nothing when `total <= limit`
- [ ] **Step 2**: `useCustomers` updated (offset, status); `CustomersPage` filter bar + PilotPaginator
- [ ] **Step 3**: `useQuotes` updated (4 new filters); `QuotesPage` status pills → dropdown + filter bar + PilotPaginator
- [ ] **Step 4**: `useInvoices` updated (3 new filters); `InvoicesPage` new inputs added (pills kept)
- [ ] **Step 5**: `useJobs` updated (new option-based params); `JobsPage` filter bar + PilotPaginator
- [ ] **Step 6**: `usePricebook` updated (offset, status); `CatalogPage` filter bar + PilotPaginator
- [ ] **Step 7**: All 5 MSW handlers return `{ items, total, limit, offset }` shape
- [ ] `PilotPaginator.test.tsx` — ≥7 unit tests pass
- [ ] `pagination_customers.integration.test.tsx` — ≥4 tests pass
- [ ] `pagination_jobs.integration.test.tsx` — ≥4 tests pass
- [ ] Query key tests updated for `useCustomers`, `useQuotes`, `useJobs`
- [ ] Zero TypeScript errors (`pnpm --filter web check-types`)
- [ ] Zero ESLint warnings (`pnpm --filter web lint`)
- [ ] No regressions in pre-existing test suite
- [ ] **Phase 2 FULL verification passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`)
- [ ] `ui-fix-1-decisions.md` — UI-FIX-1C row updated to ✅ Complete

---

## Completion Summary

After all DoD items complete:

1. Add Completion Summary to `ui-fix-1-decisions.md` §Implementation Batches.
2. Add to `pilot-launch-plan.md` Appendix B.

```markdown
### UI-FIX-1C Part B — Server-Side Pagination Frontend: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (web)
**Final**: X+N passed (+N new tests)

#### What Was Accomplished

- Added LIST_PAGE_SIZE = 25 constant and PilotPaginator component
- Updated all 5 list hooks to handle PaginatedResult<T> and new filter params
- Added filter bars (search + status dropdown + date pickers) to all 5 list pages
- Replaced Load More pattern with PilotPaginator on 4 pages; added paginator to InvoicesPage
- Updated all 5 MSW handlers to return paginated response shape

#### Files Changed / Created

| File | Action |
|---|---|
| `packages/shared-api/src/constants.ts` | Updated — LIST_PAGE_SIZE = 25 |
| `apps/web/src/components/PilotPaginator.tsx` | Created |
| `apps/web/src/components/__tests__/PilotPaginator.test.tsx` | Created |
| `apps/web/src/features/customers/hooks/useCustomers.ts` | Updated |
| `apps/web/src/features/customers/components/CustomersPage.tsx` | Updated |
| `apps/web/src/features/quotes/hooks/useQuotes.ts` | Updated |
| `apps/web/src/features/quotes/components/QuotesPage.tsx` | Updated |
| `apps/web/src/features/invoices/hooks/useInvoices.ts` | Updated |
| `apps/web/src/features/invoices/components/InvoicesPage.tsx` | Updated |
| `apps/web/src/features/jobs/hooks/useJobs.ts` | Updated |
| `apps/web/src/features/jobs/components/JobsPage.tsx` | Updated |
| `apps/web/src/features/catalog/hooks/usePricebook.ts` | Updated |
| `apps/web/src/features/catalog/components/CatalogPage.tsx` | Updated |
| MSW handlers (5 files) | Updated — paginated response shape |
| `apps/web/src/__tests__/batch_ui_fix_1c/pagination_customers.integration.test.tsx` | Created |
| `apps/web/src/__tests__/batch_ui_fix_1c/pagination_jobs.integration.test.tsx` | Created |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `components/__tests__/PilotPaginator.test.tsx` | Unit | ≥7 | ✅ |
| `__tests__/batch_ui_fix_1c/pagination_customers.integration.test.tsx` | Integration | ≥4 | ✅ |
| `__tests__/batch_ui_fix_1c/pagination_jobs.integration.test.tsx` | Integration | ≥4 | ✅ |
```
