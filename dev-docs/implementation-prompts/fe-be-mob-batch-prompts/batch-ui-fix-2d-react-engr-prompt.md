# Implementation Prompt: UI-FIX-2D — Customer Detail Tabs: Frontend (React Engineer)

**Mode**: Pilot React Engineer  
**Batch**: UI-FIX-2D (Frontend half)  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` — UI-FIX-2D row  
**Source decisions**: `dev-docs/architecture-design/batch-designs/ui-fix-2-decisions.md § FIX-018`  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-ui-fix-2d-design.md`  
**Estimated session**: 4–5 hours  
**Platform**: Web only (`apps/web`)  
**Backend companion**: UI-FIX-2D Python Engineer — **must be complete and committed before starting this prompt**

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-ui-fix-2d-design.md`** — every section (A–I)
- **`dev-docs/architecture-design/batch-designs/ui-fix-2-decisions.md § FIX-018`** — the full FIX-018 section including the UX wireframe

**Critical rules for this batch:**

- **Rule 1.1**: Before writing any hook or modifying existing hooks, verify the new `?customer_id=` param exists on all 3 endpoints in `backend/openapi_schema_map.md`. If NOT there → **STOP. The Python Engineer batch is not yet committed.**
- **Rule 1.3**: Run `pnpm sync-api-types` FIRST — the Python Engineer batch added `customer_id` query params to 3 endpoints.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any component. `<PilotPaginator>`, `<LoadingState>`, `<ErrorState>`, `<EmptyState>` are all available.
- **Rule 8**: No new npm dependencies without checking `package.json` first.
- **Rule 9**: Route files are thin server components — no `"use client"`, no data fetching.
- **Rule 10**: If ANY test fails — even pre-existing — fix it before declaring done.

**Invoice status warning**: `invoice_status` has NO "overdue" code. Overdue is a derived display state: `due_at < TODAY AND status NOT IN ('paid', 'void', 'writeoff')`. Never send `?status=overdue` to the API.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Customer search input | **Hidden** in all 3 tab components | Redundant on customer detail page; UUID filter already locks to this customer |
| Other filters (status, dates, title search) | **Visible and functional** | Useful within a single customer's records |
| Pagination | **`PilotPaginator` preserved** | Already built and shared; reuse it |
| Customer column in tables | **Omitted** | Redundant when on customer detail page |
| `+ New [Entity]` buttons | **Yes, with `?customer_id=` pre-seeded** | Allows creating entities scoped to this customer |
| `CustomerTabDeferredState.tsx` | **Delete** | Placeholder no longer needed |
| `customer_id` in count query | **Mandatory** — filter must apply to BOTH data and count queries | Without this, paginator shows wrong page counts |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```

Record exact count. Fix any unexplained failures before proceeding.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

If this fails because the backend `openapi.json` is not updated → the Python Engineer batch is not committed. Do not proceed.

---

## Pre-Work: Verify Endpoints

```bash
grep -A 3 "customer_id" backend/openapi_schema_map.md | grep -B 1 "jobs\|quotes\|invoices" | head -20

# Or verify all three at once:
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
for path in ['/api/v1/jobs/', '/api/v1/quotes/', '/api/v1/invoices/']:
    get_op = spec['paths'].get(path, {}).get('get', {})
    params = [p['name'] for p in get_op.get('parameters', [])]
    print(path, 'customer_id' in params)
"
# Expected: True True True
```

Verified endpoints for this batch:

| Hook | Endpoint | New Param |
|---|---|---|
| `useJobs` (update) | `GET /api/v1/jobs/` | `?customer_id=uuid` |
| `useQuotes` (update) | `GET /api/v1/quotes/` | `?customer_id=uuid` |
| `useInvoices` (update) | `GET /api/v1/invoices/` | `?customer_id=uuid` |

If `customer_id` is NOT confirmed in `openapi.json` → **STOP and ask Tom before proceeding**.

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

```
frontend/apps/web/src/features/jobs/hooks/useJobs.ts
  ← understand current UseJobsOptions interface and query param construction

frontend/apps/web/src/features/quotes/hooks/useQuotes.ts
  ← understand current UseQuotesOptions interface and query param construction

frontend/apps/web/src/features/invoices/hooks/useInvoices.ts
  ← understand current UseInvoicesOptions interface and query param construction

frontend/apps/web/src/features/customers/components/CustomerJobsList.tsx
  ← understand current placeholder; what to replace

frontend/apps/web/src/features/customers/components/CustomerQuotesList.tsx
  ← understand current placeholder

frontend/apps/web/src/features/customers/components/CustomerInvoicesList.tsx
  ← understand current placeholder

frontend/apps/web/src/features/jobs/components/JobsPage.tsx
  ← use as reference for filter bar + column pattern to mirror in CustomerJobsList

frontend/apps/web/src/features/invoices/components/InvoicesPage.tsx
  ← reference for InvoicesPage filter/column pattern

frontend/apps/web/src/app/(authed)/customers/[id]/layout.tsx
  ← confirm how customerId flows from route params to tab components

frontend/apps/web/src/mocks/handlers/index.ts
  ← barrel structure before adding handler updates

frontend/packages/ui/src/index.ts
  ← confirm PilotPaginator, LoadingState, ErrorState, EmptyState import paths
```

Also run:
```bash
find frontend/apps/web/src/features/customers -name "*.tsx" | head -20
grep -n "customer_id\|customerId\|customer_search" \
  frontend/apps/web/src/features/jobs/hooks/useJobs.ts | head -10
```

---

## Step 1 — Update `useJobs` Hook

**File**: `apps/web/src/features/jobs/hooks/useJobs.ts`

Read the file first. Add `customer_id?: string` to `UseJobsOptions` (or equivalent options interface):

```typescript
// In UseJobsOptions interface — add:
customer_id?: string; // When set, scopes results to this customer UUID

// In queryFn / params construction — add:
if (options.customer_id) {
  params.customer_id = options.customer_id;
}
```

> The exact param construction pattern depends on how existing params (like `status`, `customer_search`) are already being built. Read the file and match the existing pattern.

> When `customer_id` is set, the consumer (CustomerJobsList) will NOT show the `customer_search` input. The hook itself is neutral — it just passes the param if provided.

**Intermediate check:**
```bash
pnpm --filter web test -- --testPathPattern="useJobs" 2>&1 | tail -5
```

---

## Step 2 — Update `useQuotes` Hook

**File**: `apps/web/src/features/quotes/hooks/useQuotes.ts`

Same pattern as Step 1. Add `customer_id?: string` to the options interface and param construction.

**Intermediate check:**
```bash
pnpm --filter web test -- --testPathPattern="useQuotes" 2>&1 | tail -5
```

---

## Step 3 — Update `useInvoices` Hook

**File**: `apps/web/src/features/invoices/hooks/useInvoices.ts`

Same pattern. Add `customer_id?: string`.

**Intermediate check:**
```bash
pnpm --filter web test -- --testPathPattern="useInvoices" 2>&1 | tail -5
```

---

## Step 4 — Rewrite `CustomerJobsList.tsx`

**File**: `apps/web/src/features/customers/components/CustomerJobsList.tsx`

Read the current file first (it renders `<CustomerTabDeferredState>`). Read `JobsPage.tsx` as the reference implementation.

Rewrite it to a real customer-scoped jobs list:

```typescript
"use client";
// Read and adjust imports to match what's actually available
import { PilotPaginator, LoadingState, ErrorState, EmptyState } from "@pilot/ui";
import { useJobs } from "../../jobs/hooks/useJobs";
import { LIST_PAGE_SIZE } from "@pilot/shared-api";
import { useState } from "react";

interface CustomerJobsListProps {
  customerId: string;
}

export function CustomerJobsList({ customerId }: CustomerJobsListProps) {
  // Filter state (customer search input NOT included — locked to customerId)
  const [status, setStatus] = useState("");
  const [scheduledFrom, setScheduledFrom] = useState("");
  const [scheduledTo, setScheduledTo] = useState("");
  const [pendingStatus, setPendingStatus] = useState("");
  const [pendingFrom, setPendingFrom] = useState("");
  const [pendingTo, setPendingTo] = useState("");
  const [offset, setOffset] = useState(0);

  const { data, isLoading, isError } = useJobs({
    customer_id: customerId,   // ← locked to this customer
    status: status || undefined,
    scheduled_from: scheduledFrom || undefined,
    scheduled_to: scheduledTo || undefined,
    offset,
    limit: LIST_PAGE_SIZE,
  });

  const jobs = data?.items ?? [];
  const total = data?.total ?? 0;

  const handleSearch = () => {
    setStatus(pendingStatus);
    setScheduledFrom(pendingFrom);
    setScheduledTo(pendingTo);
    setOffset(0);
  };

  const handleClear = () => {
    setPendingStatus(""); setPendingFrom(""); setPendingTo("");
    setStatus(""); setScheduledFrom(""); setScheduledTo("");
    setOffset(0);
  };

  if (isLoading) return <LoadingState />;
  if (isError) return <ErrorState message="Failed to load jobs" />;

  return (
    <div className="space-y-4">
      {/* Filter bar — NO customer search input */}
      <div className="flex flex-wrap gap-2 items-end">
        <div>
          <label className="text-xs text-neutral-500">Status</label>
          <select
            value={pendingStatus}
            onChange={(e) => setPendingStatus(e.target.value)}
            className="block text-sm border border-neutral-200 rounded px-2 py-1"
          >
            <option value="">All</option>
            <option value="draft">Draft</option>
            <option value="scheduled">Scheduled</option>
            <option value="in_progress">In Progress</option>
            <option value="completed">Completed</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
        <div>
          <label className="text-xs text-neutral-500">From</label>
          <input type="date" value={pendingFrom}
            onChange={(e) => setPendingFrom(e.target.value)}
            className="block text-sm border border-neutral-200 rounded px-2 py-1" />
        </div>
        <div>
          <label className="text-xs text-neutral-500">To</label>
          <input type="date" value={pendingTo}
            onChange={(e) => setPendingTo(e.target.value)}
            className="block text-sm border border-neutral-200 rounded px-2 py-1" />
        </div>
        <button onClick={handleSearch}
          className="text-sm bg-brand-600 text-white px-3 py-1 rounded">
          Search
        </button>
        <button onClick={handleClear}
          className="text-sm border border-neutral-200 text-neutral-600 px-3 py-1 rounded">
          Clear
        </button>
        <a href={`/jobs/new?customer_id=${customerId}`}
          className="ml-auto text-sm bg-brand-50 text-brand-700 border border-brand-200 px-3 py-1 rounded">
          + New Job
        </a>
      </div>

      {/* Jobs table — Customer column omitted */}
      {jobs.length === 0 ? (
        <EmptyState message="No jobs for this customer yet." />
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-neutral-100 text-neutral-500 text-left">
              <th className="py-2 pr-4">Job #</th>
              <th className="py-2 pr-4">Status</th>
              <th className="py-2 pr-4">Scheduled</th>
              <th className="py-2">Duration</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job: any) => (
              <tr key={job.id} className="border-b border-neutral-50 hover:bg-neutral-50">
                <td className="py-2 pr-4">
                  <a href={`/jobs/${job.id}`} className="text-brand-600 hover:underline">
                    {job.job_number}
                  </a>
                </td>
                <td className="py-2 pr-4">{job.status_code}</td>
                <td className="py-2 pr-4">
                  {job.scheduled_start_at
                    ? new Date(job.scheduled_start_at).toLocaleString()
                    : "—"}
                </td>
                <td className="py-2">{job.estimated_duration_hours ? `${job.estimated_duration_hours}h` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <PilotPaginator
        total={total}
        limit={LIST_PAGE_SIZE}
        offset={offset}
        onOffsetChange={setOffset}
      />
    </div>
  );
}
```

> **Read `JobsPage.tsx` first** to confirm the exact field names on the job response object (e.g., `job_number`, `status_code`, `scheduled_start_at`). Adjust column values to match the actual response shape. Use `pnpm sync-api-types` output as the authoritative source for field names.

> **Read the `PilotPaginator` component** to confirm its exact prop interface before using it.

**Intermediate check:**
```bash
pnpm --filter web test -- --testPathPattern="CustomerJobsList" 2>&1 | tail -5
```

---

## Step 5 — Rewrite `CustomerQuotesList.tsx`

**File**: `apps/web/src/features/customers/components/CustomerQuotesList.tsx`

Same pattern as `CustomerJobsList`. Read `QuotesPage.tsx` as reference. Use `useQuotes({ customer_id: customerId, ... })`.

Columns: Quote #, Title, Status, Total, Created (omit Customer).

Filter bar: title search input, status dropdown, date range pickers (on `created_at`), Search/Clear buttons, `+ New Quote` link to `/quotes/new?customer_id=${customerId}`.

**Intermediate check:**
```bash
pnpm --filter web test -- --testPathPattern="CustomerQuotesList" 2>&1 | tail -5
```

---

## Step 6 — Rewrite `CustomerInvoicesList.tsx`

**File**: `apps/web/src/features/customers/components/CustomerInvoicesList.tsx`

Same pattern. Read `InvoicesPage.tsx` as reference. Use `useInvoices({ customer_id: customerId, ... })`.

Columns: Invoice #, Status, Aging, Total, Balance Due, Due Date (omit Customer). Aging column: computed from `due_at` — use the same `getAgingBucket()` helper pattern that was added to `InvoicesPage.tsx` in UI-FIX-1B. Check if it's already exported from a shared location; if not, copy the helper inline.

Filter bar: status pills (keep existing pattern from `InvoicesPage`), date range pickers (on `issued_at`), Overdue Only toggle, Search/Clear buttons, `+ New Invoice` link to `/invoices/new?customer_id=${customerId}`.

**Important**: Do NOT add `?status=overdue` — use `?overdue=true` for the Overdue Only toggle. "overdue" is a derived display state, not a DB code.

---

## Step 7 — Delete `CustomerTabDeferredState.tsx`

**File**: `apps/web/src/features/customers/components/CustomerTabDeferredState.tsx`

Before deleting: confirm zero remaining imports:
```bash
grep -rn "CustomerTabDeferredState" frontend/apps/web/src/ | head -10
```

If it shows only the file itself and the 3 components you've just replaced → delete the file. If other components still import it → update them first.

---

## Step 8 — Update MSW Handlers

The existing jobs, quotes, and invoices MSW handlers need to support filtering by `?customer_id=` so that tests pass.

Read the existing handler files:
```bash
find frontend/apps/web/src/mocks/handlers -name "*.ts" | head -20
cat frontend/apps/web/src/mocks/handlers/index.ts
```

For each of the 3 handler files (jobs, quotes, invoices list handlers):
- Find the `GET` handler for the list endpoint
- Add `customer_id` filter support: if `request.url` has a `customer_id` param, filter the mock data array to only return items matching that `customer_id`

Example pattern for MSW handler update:
```typescript
http.get("/api/v1/jobs/", ({ request }) => {
  const url = new URL(request.url);
  const customerId = url.searchParams.get("customer_id");
  const filtered = customerId
    ? MOCK_JOBS.filter((j) => j.customer_id === customerId)
    : MOCK_JOBS;
  return HttpResponse.json({
    items: filtered,
    total: filtered.length,
    limit: 25,
    offset: 0,
  });
}),
```

> Make sure mock data fixtures include a `customer_id` field on each job/quote/invoice so filtering works in tests.

---

## Step 9 — Write Tests

### Unit tests (co-located)

**`features/jobs/hooks/__tests__/useJobs.test.ts`** — add test for `customer_id` param:
- When `customer_id` is set, `?customer_id=` appears in the request URL

**`features/quotes/hooks/__tests__/useQuotes.test.ts`** — same

**`features/invoices/hooks/__tests__/useInvoices.test.ts`** — same

**`features/customers/components/__tests__/CustomerJobsList.test.tsx`** — min 4 tests:
- Renders job rows from MSW fixture
- Customer search input is NOT rendered
- Status filter dropdown renders
- `+ New Job` link includes `?customer_id=`

**`features/customers/components/__tests__/CustomerQuotesList.test.tsx`** — min 4 tests (same pattern)

**`features/customers/components/__tests__/CustomerInvoicesList.test.tsx`** — min 4 tests (same pattern)

### Integration tests

**`apps/web/src/__tests__/batch_ui_fix_2d/customer_detail_tabs.integration.test.tsx`** — min 6 tests:
1. Jobs tab renders jobs from MSW (no placeholder)
2. Jobs tab does NOT render customer search input
3. Quotes tab renders quotes from MSW (no placeholder)
4. Quotes tab does NOT render customer search input
5. Invoices tab renders invoices from MSW (no placeholder)
6. `+ New Job` link contains correct `?customer_id=` param

Use TanStack Query `retry: false`. Use `vi.mock("next/navigation", ...)`. Use MSW at HTTP level only.

---

## Final Verification

### Phase 1 — Targeted tests

```bash
cd <repo>/frontend
pnpm --filter web test -- --testPathPattern="CustomerJobsList|CustomerQuotesList|CustomerInvoicesList|useJobs|useQuotes|useInvoices|batch_ui_fix_2d" 2>&1 | tail -10
```

Fix any failures before Phase 2.

### Phase 2 — Full verification

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — UI-FIX-2D React Engineer

- [ ] Pre-modification regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — no new type errors
- [ ] Design doc fully read before writing any code
- [ ] All mandatory source files read (`useJobs.ts`, `useQuotes.ts`, `useInvoices.ts`, `CustomerJobsList.tsx`, `CustomerQuotesList.tsx`, `CustomerInvoicesList.tsx`, `JobsPage.tsx`, `InvoicesPage.tsx`, `mocks/handlers/index.ts`)
- [ ] All 3 endpoints verified in `openapi_schema_map.md` to have `customer_id` param
- [ ] **STEP 1**: `useJobs.ts` updated — `customer_id?` param added to options + query construction
- [ ] **STEP 2**: `useQuotes.ts` updated — `customer_id?` param added
- [ ] **STEP 3**: `useInvoices.ts` updated — `customer_id?` param added
- [ ] **STEP 4**: `CustomerJobsList.tsx` rewritten — real data, customer search hidden, filter bar, `PilotPaginator`, `+ New Job` with `?customer_id=`
- [ ] **STEP 5**: `CustomerQuotesList.tsx` rewritten — real data, customer search hidden, filter bar, `PilotPaginator`, `+ New Quote` with `?customer_id=`
- [ ] **STEP 6**: `CustomerInvoicesList.tsx` rewritten — real data, customer search hidden, filter bar, Aging column, `PilotPaginator`, `+ New Invoice` with `?customer_id=`
- [ ] **STEP 7**: `CustomerTabDeferredState.tsx` deleted — zero remaining imports confirmed
- [ ] **STEP 8**: MSW handlers for jobs/quotes/invoices updated to filter by `customer_id` when present
- [ ] No `?status=overdue` in any new code — use `?overdue=true` or client-side derivation
- [ ] All new MSW handler changes registered correctly (no new handler files needed — updates to existing)
- [ ] Unit tests pass for all 3 updated hooks (targeted run)
- [ ] Unit tests pass for all 3 new list components
- [ ] Integration tests pass in `__tests__/batch_ui_fix_2d/`
- [ ] Zero TypeScript errors (`check-types` passes)
- [ ] Zero ESLint `no-hardcoded-design-values` warnings
- [ ] **Phase 2 FULL verification command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
  ```
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `ui-fix-2-decisions.md` under UI-FIX-2D React Engineer row

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** to `dev-docs/architecture-design/batch-designs/ui-fix-2-decisions.md` under the UI-FIX-2D batch section (React Engineer row):

```markdown
### UI-FIX-2D (React Engineer) — Customer Detail Jobs/Quotes/Invoices Real Data: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (web)
**Final**: X+N passed (+N new tests)

#### What Was Accomplished

- Updated useJobs, useQuotes, useInvoices hooks to accept customer_id param
- Rewrote CustomerJobsList, CustomerQuotesList, CustomerInvoicesList — all 3 now show real data scoped to the customer
- Customer search input hidden in all 3 tab views; all other filters visible
- PilotPaginator preserved; + New [Entity] buttons pre-seeded with customer_id
- CustomerTabDeferredState.tsx deleted
- MSW handlers updated to support ?customer_id= filtering

#### Files Changed / Created

| File | Action |
|---|---|
| `apps/web/src/features/jobs/hooks/useJobs.ts` | Updated — customer_id param |
| `apps/web/src/features/quotes/hooks/useQuotes.ts` | Updated — customer_id param |
| `apps/web/src/features/invoices/hooks/useInvoices.ts` | Updated — customer_id param |
| `apps/web/src/features/customers/components/CustomerJobsList.tsx` | Rewritten — real data |
| `apps/web/src/features/customers/components/CustomerQuotesList.tsx` | Rewritten — real data |
| `apps/web/src/features/customers/components/CustomerInvoicesList.tsx` | Rewritten — real data |
| `apps/web/src/features/customers/components/CustomerTabDeferredState.tsx` | Deleted |
| MSW handler files (jobs, quotes, invoices) | Updated — customer_id filter support |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `features/customers/components/__tests__/CustomerJobsList.test.tsx` | Unit | N | ✅ |
| `features/customers/components/__tests__/CustomerQuotesList.test.tsx` | Unit | N | ✅ |
| `features/customers/components/__tests__/CustomerInvoicesList.test.tsx` | Unit | N | ✅ |
| `__tests__/batch_ui_fix_2d/customer_detail_tabs.integration.test.tsx` | Integration | N | ✅ |
```

2. Update `dev-docs/analysis/pilot-launch-plan.md` — UI-FIX-2D row: change Status to `✅ Complete — YYYY-MM-DD`.
