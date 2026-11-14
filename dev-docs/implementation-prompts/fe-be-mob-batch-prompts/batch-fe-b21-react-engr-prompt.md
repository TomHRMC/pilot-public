# Implementation Prompt: FE-B21 — Jobs Web Module

**Mode**: Pilot React Engineer  
**Batch**: FE-B21  
**Source plan**: `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` §Phase 0.9 — FE-B21  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-fe-b21-design.md`  
**Estimated session**: 5–7 hours  
**Platform**: Web only (`apps/web`)  
**Backend companion**: None — all endpoints exist. Prerequisites: FE-B19 complete, B17 Part A complete + `pnpm sync-api-types`.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-fe-b21-design.md`** — every section (A–I)

**Critical rules for this batch:**

- **Rule 1.1**: Before writing ANY hook, verify the exact endpoint path + params in `backend/openapi_schema_map.md`. The `projected-margin` response shape must be verified — do not invent field names.
- **Rule 1.2**: `POST /api/v1/invoices/` may require more fields than just `job_id`. Verify `InvoiceCreate` schema before building the "Convert to Invoice" button.
- **Rule 1.3**: Run `pnpm sync-api-types` before starting.
- **Rule 2**: All API calls use `apiClient`. `fetch()` banned.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any component.
- **Rule 8**: No new npm packages without checking `package.json` first.
- **Rule 9**: Route files are thin server components — no `"use client"`, no data fetching.
- **Rule 10**: Any test failure must be fixed before declaring done.
- **Extend `mocks/handlers/jobs.ts`, do NOT replace it**: The existing `jobs.ts` handler file has dispatch board job fixtures. Extend it with new endpoints — do not overwrite existing handlers.
- **Notes save-on-blur**: The `JobNotesTab` saves on textarea blur. Do NOT add a submit button. Do NOT auto-save on every keystroke. Only save when user leaves the textarea.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G:

| Decision | Outcome | Rationale |
|---|---|---|
| Layout | Tabs: Profitability / Time Entries / Expenses / Change Orders / Notes | Clean separation of concerns |
| Profitability | Persistent widget above tabs; `useProjectedMargin` provides live data | Always visible regardless of active tab |
| Notes | Save on blur (not submit button) | Avoids accidental partial saves |
| Photo section | Deferred — show read-only grid of existing; no upload in FE-B21 | Multipart S3 upload is complex |
| "Convert to Invoice" | Shown only for completed/terminal job statuses | Guard against premature invoicing |
| Dispatch board wiring | `onJobSelect` → `router.push('/jobs/${jobId}')` | Closes a key navigation gap |
| jobs.ts MSW | Extend, don't replace | Existing dispatch board fixtures must not break |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
pnpm --filter @pilot/ui test 2>&1 | tail -5
```

Record exact counts. Fix pre-existing failures or confirm with Tom.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

---

## Pre-Work: Verify Endpoints

Run ALL of these before coding:

```bash
# 1. Confirm job list endpoint and params
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
jobs_get = spec['paths'].get('/api/v1/jobs/', {}).get('get', {})
params = [(p['name'], p.get('required', False)) for p in jobs_get.get('parameters', [])]
print('Jobs GET params:', params)
"

# 2. Check projected-margin response schema
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
pm = spec['paths'].get('/api/v1/jobs/{job_id}/projected-margin', {}).get('get', {})
resp_schema = pm.get('responses', {}).get('200', {}).get('content', {}).get('application/json', {}).get('schema', {})
print('Projected margin response:', resp_schema)
# Follow \$ref if present:
ref = resp_schema.get('\$ref', '')
if ref:
    schema_name = ref.split('/')[-1]
    schema = spec.get('components', {}).get('schemas', {}).get(schema_name, {})
    print('Schema fields:', list(schema.get('properties', {}).keys()))
"

# 3. Check InvoiceCreate schema — what fields does it require?
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
ic = spec.get('components', {}).get('schemas', {}).get('InvoiceCreate', {})
props = ic.get('properties', {})
required = ic.get('required', [])
print('InvoiceCreate fields:', list(props.keys()))
print('Required:', required)
"

# 4. Verify job status codes from seeded data
# (run via MCP or check seed_scenario_dispatch.py)
grep -A 5 "job_status" backend/migrations/scripts/seed_core.py | head -20

# 5. Check if customer_id filter supported on jobs
# Already checked above via params — confirm 'customer_id' in list

# 6. Verify existing jobs.ts handler to avoid overwriting
cat frontend/apps/web/src/mocks/handlers/jobs.ts | head -50
```

Record findings before coding.

| Hook | Endpoint | Verified |
|---|---|---|
| `useJobs` | `GET /api/v1/jobs/` | Confirm `?status=` + `?customer_id=` params |
| `useJob` | `GET /api/v1/jobs/{id}` | Confirm response includes profitability fields |
| `useProjectedMargin` | `GET /api/v1/jobs/{id}/projected-margin` | Confirm response field names |
| `useCreateInvoiceFromJob` | `POST /api/v1/invoices/` | Confirm `job_id` field + all required fields |

---

## Pre-Work: Read These Source Files

```
frontend/apps/web/src/mocks/handlers/jobs.ts
  ← read fully before extending — understand existing fixtures

frontend/apps/web/src/features/dispatch-board/components/DispatchBoardPage.tsx
  ← find onJobSelect; understand how to wire navigation

frontend/apps/web/src/components/AppSidebar.tsx
  ← understand current nav before adding Jobs

frontend/apps/web/src/features/customers/components/CustomerJobsList.tsx
  ← check if deferred state — update if customer_id filter confirmed

frontend/packages/ui/src/index.ts
  ← confirm LoadingState, ErrorState, EmptyState, RoleGate imports
```

Also run:
```bash
# Find if any jobs-related feature components already exist
find frontend/apps/web/src/features/jobs -type f 2>/dev/null | sort

# Check dispatch board JobBlock for click handler
grep -n "onClick\|onSelect\|href" frontend/apps/web/src/features/dispatch-board/components/JobBlock.tsx | head -15

# Find invoice create in existing hooks/mocks
find frontend/apps/web/src -name "*[Ii]nvoice*" | head -10
```

---

## Step 1 — Extend `mocks/handlers/jobs.ts` with New Endpoints

**File**: `apps/web/src/mocks/handlers/jobs.ts` (EXTEND, do not replace)

Read the file first. Add handlers for the endpoints that don't already exist:

```typescript
// NEW handlers to add (only if not already in the file):
// GET /api/v1/jobs/:jobId — job detail
// GET /api/v1/jobs/:jobId/time-entries
// POST /api/v1/jobs/:jobId/time-entries
// GET /api/v1/jobs/:jobId/expenses
// POST /api/v1/jobs/:jobId/expenses
// GET /api/v1/jobs/:jobId/notes
// PUT /api/v1/jobs/:jobId/notes
// GET /api/v1/jobs/:jobId/change-orders
// POST /api/v1/jobs/:jobId/change-orders
// PATCH /api/v1/jobs/:jobId/change-orders/:coId
// DELETE /api/v1/jobs/:jobId/change-orders/:coId
// GET /api/v1/jobs/:jobId/projected-margin
```

Use realistic fixture data matching the dispatch board job IDs already in the file.

> **Test resilience**: Never mutate module-level fixture arrays. POST handlers return new items with generated IDs.

Verify no existing handler is overridden by checking the file first.

**Intermediate check:**
```bash
pnpm --filter web test 2>&1 | tail -5
```

---

## Steps 2–8 — Create All Hooks

**Directory**: `apps/web/src/features/jobs/hooks/`

Read existing hooks (e.g., `features/customers/hooks/useCustomers.ts`) for the pattern. All hooks follow the same structure.

### `useJobs.ts`
```typescript
// Query key: ['jobs', status, customerId]
// GET /api/v1/jobs/?status={status}&customer_id={customerId}&skip={skip}&limit={limit}
// Returns: JobListItem[] (has status_code + customer_name)
// staleTime: 30_000
```

### `useJob.ts`
```typescript
// Query key: ['job', jobId]
// GET /api/v1/jobs/{jobId}
// Returns: JobResponse (has actual_labor_cost_cents, actual_material_cost_cents, actual_profit_cents)
// enabled: !!jobId
```

### `useJobTimeEntries.ts` + `useAddTimeEntry.ts`
```typescript
// useJobTimeEntries: GET /api/v1/jobs/{jobId}/time-entries → JobTimeEntryResponse[]
// useAddTimeEntry: POST /api/v1/jobs/{jobId}/time-entries
//   - Request body field names from verified pre-work (started_at, ended_at, hours, notes, hourly_rate_cents?)
//   - onSuccess: invalidate ['job-time-entries', jobId]
```

### `useJobExpenses.ts` + `useAddExpense.ts`
```typescript
// useJobExpenses: GET /api/v1/jobs/{jobId}/expenses → JobExpenseResponse[]
// useAddExpense: POST /api/v1/jobs/{jobId}/expenses
//   - Request: job_expense_category_code, description, vendor_name?, incurred_at, cost_cents, is_billable
//   - onSuccess: invalidate ['job-expenses', jobId]
```

### `useJobChangeOrders.ts` + mutations
```typescript
// useJobChangeOrders: GET /api/v1/jobs/{jobId}/change-orders → ChangeOrderResponse[]
// useCreateChangeOrder: POST /api/v1/jobs/{jobId}/change-orders
// useUpdateChangeOrder: PATCH /api/v1/jobs/{jobId}/change-orders/{coId}
// useDeleteChangeOrder: DELETE /api/v1/jobs/{jobId}/change-orders/{coId}
// All onSuccess: invalidate ['job-change-orders', jobId]
```

### `useJobNotes.ts` + `useUpdateJobNotes.ts`
```typescript
// useJobNotes: GET /api/v1/jobs/{jobId}/notes → { notes_text: string }
// useUpdateJobNotes: PUT /api/v1/jobs/{jobId}/notes (note: PUT not PATCH)
//   - Request: { notes_text: string }
//   - onSuccess: invalidate ['job-notes', jobId]
```

### `useProjectedMargin.ts`
```typescript
// Query key: ['job-projected-margin', jobId]
// GET /api/v1/jobs/{jobId}/projected-margin
// Response field names from verified pre-work
// staleTime: 15_000 (refresh more often than list)
```

### `useCreateInvoiceFromJob.ts`
```typescript
// POST /api/v1/invoices/ with job_id + any required fields from verified InvoiceCreate schema
// onSuccess: navigate to /invoices/{response.id}
// Required: invoices.create permission
```

**Intermediate check:**
```bash
pnpm --filter web test -- --testPathPattern="useJob|useProjected" 2>&1 | tail -6
```

---

## Steps 9 — `JobsPage`

**File**: `apps/web/src/features/jobs/components/JobsPage.tsx`

```typescript
"use client";
// Status filter pills: All, Draft, Scheduled, In Progress, Completed
// Customer search: text input → useJobs({ customerSearch }) with client-side filter
//   (or server-side if ?customer_id= filter confirmed — use server-side if confirmed)
// Table columns: Customer, Status badge, Scheduled date, Actions (View link)
// "Convert to Invoice" action shown for completed jobs (visible for owner/accountant)
// EmptyState, LoadingState, ErrorState
// RoleGate not needed on page itself — all roles can view jobs
```

---

## Steps 10–15 — Job Detail Components

### `JobDetailHeader.tsx`

```typescript
"use client";
// Shows: breadcrumb (Jobs > [customer name]), status badge, scheduled window, site name
// useJob hook provides the data
// Does NOT include tabs or profitability — that's JobDetailPage's responsibility
```

### `JobProfitabilityWidget.tsx`

```typescript
"use client";
// Persistent section above tabs
// Shows:
//   Actual Labor: $X / Est. $Y
//   Actual Materials: $X / Est. $Y
//   Projected Margin: Z%  (from useProjectedMargin)
//   Margin status indicator: ✅ (above target) / ⚠️ (below target)
// Target margin from tenant setting or hardcoded 20%
// Loading skeleton while data loads
```

### `JobTimeEntriesTab.tsx`

```typescript
"use client";
// List: start time, end time, hours, tech name, hourly rate, total cost
// "+ Add Time Entry" button (RoleGate: jobs.edit) → inline form or modal
// AddTimeEntryForm: started_at (date+time), ended_at (date+time), notes
//   hours auto-calculated from start/end; show as hint
// EmptyState for no entries
```

### `JobExpensesTab.tsx`

```typescript
"use client";
// List: category badge, description, vendor, cost, markup, billable amount
// "+ Add Expense" button (RoleGate: jobs.edit) → AddExpenseForm
// AddExpenseForm:
//   - category: dropdown from GET /api/v1/job-expense-categories (from B17)
//   - description: text
//   - vendor_name: optional text
//   - cost_cents: dollar input
//   - incurred_at: date
```

### `JobChangeOrdersTab.tsx`

```typescript
"use client";
// List: description, total, status (active/inactive)
// "+ Add Change Order" button (RoleGate: jobs.edit)
// Edit / Delete actions per row (RoleGate: jobs.edit)
// Change order form: description only (MVP) — total is computed from lines
```

### `JobNotesTab.tsx`

```typescript
"use client";
// Large textarea showing current job notes
// Save on blur (onBlur event) — NOT a submit button
// Show "Saving..." while mutation pending
// Show "Saved ✓" for 2 seconds after successful save
// If save fails: show inline error with retry option
```

### `JobDetailPage.tsx`

**File**: `apps/web/src/features/jobs/components/JobDetailPage.tsx`

```typescript
"use client";
interface JobDetailPageProps {
  jobId: string;
}

// Layout:
// 1. <JobDetailHeader jobId={jobId} />
// 2. <JobProfitabilityWidget jobId={jobId} />
// 3. Tab bar: [Profitability] [Time Entries] [Expenses] [Change Orders] [Notes]
//    (Profitability tab shows a summary card; main profitability is always-visible above)
// 4. Active tab content
// 5. "Convert to Invoice" button — shown when job status is terminal (completed)
//    Behind RoleGate permission="invoices.create"

// "Convert to Invoice" handler:
const { mutate: createInvoice, isPending } = useCreateInvoiceFromJob(jobId);
// On click: call createInvoice(); on success: navigated to /invoices/{id} by the hook
```

---

## Steps 17 — Route Files

All thin server components:

```typescript
// app/(authed)/jobs/page.tsx
import { JobsPage } from "@/features/jobs/components/JobsPage";
export default function JobsRoute() { return <JobsPage />; }
export const metadata = { title: "Jobs | Pilot" };

// app/(authed)/jobs/[id]/page.tsx
import { JobDetailPage } from "@/features/jobs/components/JobDetailPage";
interface Props { params: Promise<{ id: string }> }
export default async function JobDetailRoute({ params }: Props) {
  const { id } = await params;
  return <JobDetailPage jobId={id} />;
}
export const metadata = { title: "Job Detail | Pilot" };
```

---

## Step 18 — Add "Jobs" to AppSidebar

Read `AppSidebar.tsx` first. Add `{ label: "Jobs", href: "/jobs", icon: "🔧" }` — position between "Schedule" and "Customers".

---

## Step 19 — Wire Dispatch Board Click to `/jobs/[id]`

Read `DispatchBoardPage.tsx` (or `JobBlock.tsx`). Find where `onJobSelect` is defined or where clicking a job card currently does nothing.

```typescript
// In DispatchBoardPage.tsx or wherever job card click is handled:
const router = useRouter();
const handleJobSelect = (jobId: string) => {
  router.push(`/jobs/${jobId}`);
};
// Pass handleJobSelect as onJobSelect prop to the grid
```

Also update `CustomerJobsList.tsx` from FE-B18 if `?customer_id=` is confirmed in pre-work:
```typescript
// Replace deferred state with:
const { data: jobs } = useJobs({ customerId });
// Render jobs table
```

---

## Test Requirements

### Platform: Web (`apps/web`) — Vitest

- `vi.mock()`, `toBeInTheDocument()`, mock `next/navigation`
- `createWrapper()` with `retry: false`

### Test Resilience (per `react-engineer-rules.md` Rule 15)

- Never mutate module-level fixture arrays in `jobs.ts`
- Per-test `server.use(...)` + `server.resetHandlers()` in `afterEach`
- Never `toHaveLength(N)` on job lists

### Unit Tests

**`features/jobs/components/__tests__/JobProfitabilityWidget.test.tsx`:**
- Renders labor + material actual vs estimated
- Shows "above target" indicator when margin > 20%
- Shows "below target" indicator when margin < 20%
- LoadingState while fetching

**`features/jobs/components/__tests__/JobNotesTab.test.tsx`:**
- Renders textarea with notes content from MSW
- Does NOT have a Submit button
- Blur event triggers `useUpdateJobNotes` mutation
- Shows "Saving..." during mutation; "Saved ✓" on success

**`features/jobs/components/__tests__/JobTimeEntriesTab.test.tsx`:**
- Renders empty state when no entries
- Renders time entries list with hours + cost
- "+ Add Time Entry" button visible for owner; hidden for tech (RoleGate)

### Integration Tests

**`apps/web/src/__tests__/batch_fe_b21/jobsList.integration.test.tsx`:**
1. `/jobs` renders job list from MSW
2. Status filter pills filter correctly (server-side param sent)
3. Each job row has a "View" link to `/jobs/[id]`

**`apps/web/src/__tests__/batch_fe_b21/jobDetail.integration.test.tsx`:**
1. `/jobs/[id]` renders job header with customer name
2. Profitability widget shows from MSW projected-margin data
3. Tabs navigate to correct sub-sections
4. "Convert to Invoice" button visible for owner on completed job; hidden for tech
5. Dispatch board "job card click" navigates to `/jobs/[id]` (mock router.push)

---

## Final Verification

### Phase 1 — Targeted

```bash
cd <repo>/frontend

# After hooks:
pnpm --filter web test -- --testPathPattern="useJob|useProjected|useTimeEntry|useExpense" 2>&1 | tail -6

# After components:
pnpm --filter web test -- --testPathPattern="JobDetail|JobProfitability|JobNotes|JobTime" 2>&1 | tail -8

# After integration:
pnpm --filter web test -- --testPathPattern="batch_fe_b21" 2>&1 | tail -8
```

### Phase 2 — Full Verification

```bash
cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter @pilot/ui lint && pnpm --filter web lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && echo "=== FE-B21 FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — FE-B21

Update `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` §Phase 0.9:

- [ ] Regression baseline captured (zero pre-existing failures or confirmed with Tom)
- [ ] `pnpm sync-api-types` run
- [ ] Design doc read in full (A–I)
- [ ] All mandatory source files read (jobs.ts, DispatchBoardPage.tsx, AppSidebar.tsx, CustomerJobsList.tsx)
- [ ] All endpoints verified: projected-margin response shape, InvoiceCreate required fields, customer_id filter on jobs
- [ ] **Step 1**: `mocks/handlers/jobs.ts` EXTENDED (not replaced); all new endpoint handlers added
- [ ] **Steps 2–8**: All 14 hooks created
- [ ] **Step 9**: `JobsPage` with status filter pills + job list
- [ ] **Steps 10–15**: `JobDetailHeader`, `JobProfitabilityWidget`, `JobTimeEntriesTab`, `JobExpensesTab`, `JobChangeOrdersTab`, `JobNotesTab`, `JobDetailPage` all created
- [ ] **Step 17**: `jobs/page.tsx` + `jobs/[id]/page.tsx` created
- [ ] **Step 18**: "Jobs" added to AppSidebar
- [ ] **Step 19**: Dispatch board job card click navigates to `/jobs/[id]`
- [ ] `CustomerJobsList.tsx` updated (deferred state replaced if `?customer_id=` confirmed)
- [ ] Notes save on blur — no submit button; "Saving..." + "Saved ✓" UX correct
- [ ] "Convert to Invoice" visible only for terminal job statuses; hidden for non-terminal
- [ ] `JobProfitabilityWidget` unit tests pass (above/below margin target)
- [ ] `JobNotesTab` unit tests pass (no submit button; blur triggers save)
- [ ] `JobTimeEntriesTab` unit tests pass (RoleGate on add button)
- [ ] Integration tests in `__tests__/batch_fe_b21/` pass
- [ ] Existing dispatch board tests still pass (jobs.ts extension didn't break them)
- [ ] Zero TypeScript errors
- [ ] Zero ESLint `no-hardcoded-design-values` warnings
- [ ] **Phase 2 FULL verification passes** (`=== FE-B21 FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter @pilot/ui lint && pnpm --filter web lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && echo "=== FE-B21 FINAL VERIFICATION COMPLETE ==="
  ```
- [ ] Final test count documented
- [ ] Completion Summary added to impl plan §Phase 0.9

---

## Completion Summary

After all DoD items, add a **Completion Summary** to `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` under Phase 0.9 — FE-B21:

```markdown
### FE-B21 — Jobs Web Module: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (ui) | X passed (web)
**Final**: X+N passed (+N new tests)

#### What Was Accomplished

- Built /jobs list with status filter pills and customer search
- Built /jobs/[id] detail page with 5 tabs
- Persistent profitability widget (actuals + projected margin) above tabs
- Time entries, expenses, change orders management with add forms
- Notes tab with save-on-blur behavior
- "Convert to Invoice" button on completed jobs
- Wired dispatch board job card → /jobs/[id] navigation
- Added "Jobs" to AppSidebar nav
- Updated CustomerJobsList to show real data (if customer_id filter confirmed)

#### Files Changed / Created

| File | Action |
|---|---|
| `apps/web/src/mocks/handlers/jobs.ts` | Extended — added 12 new endpoint handlers |
| `apps/web/src/features/jobs/hooks/*.ts` | Created — 14 new hooks |
| `apps/web/src/features/jobs/components/JobsPage.tsx` | Created |
| `apps/web/src/features/jobs/components/JobDetailHeader.tsx` | Created |
| `apps/web/src/features/jobs/components/JobProfitabilityWidget.tsx` | Created |
| `apps/web/src/features/jobs/components/JobTimeEntriesTab.tsx` | Created |
| `apps/web/src/features/jobs/components/JobExpensesTab.tsx` | Created |
| `apps/web/src/features/jobs/components/JobChangeOrdersTab.tsx` | Created |
| `apps/web/src/features/jobs/components/JobNotesTab.tsx` | Created |
| `apps/web/src/features/jobs/components/JobDetailPage.tsx` | Created |
| `apps/web/src/app/(authed)/jobs/page.tsx` | Created |
| `apps/web/src/app/(authed)/jobs/[id]/page.tsx` | Created |
| `apps/web/src/components/AppSidebar.tsx` | Updated — Jobs nav |
| `apps/web/src/features/dispatch-board/components/DispatchBoardPage.tsx` | Updated — job click wired |
| `apps/web/src/features/customers/components/CustomerJobsList.tsx` | Updated — real data |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `features/jobs/components/__tests__/JobProfitabilityWidget.test.tsx` | Unit | N | ✅ |
| `features/jobs/components/__tests__/JobNotesTab.test.tsx` | Unit | N | ✅ |
| `features/jobs/components/__tests__/JobTimeEntriesTab.test.tsx` | Unit | N | ✅ |
| `apps/web/src/__tests__/batch_fe_b21/jobsList.integration.test.tsx` | Integration | N | ✅ |
| `apps/web/src/__tests__/batch_fe_b21/jobDetail.integration.test.tsx` | Integration | N | ✅ |
```

---

## After This Batch

FE-B21 is complete. The full job management workflow is live on web, and the dispatch board now navigates to job detail.

**Next batch**: `batch-fe-b22-react-engr-prompt.md` — Invoice Detail + Create + Record Payment + Tax Setup.
