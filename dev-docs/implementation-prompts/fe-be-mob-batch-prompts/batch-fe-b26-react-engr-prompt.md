# Implementation Prompt: FE-B26 — UUID Display Fixes, Job/Quote Number Display, Profitability Drill-Down, Job-from-Quote CTA

**Mode**: Pilot React Engineer  
**Batch**: FE-B26  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 — FE-B26 row  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-fe-b26-design.md`  
**Estimated session**: 3–4 hours  
**Platform**: Web only (`apps/web`)  
**Backend companion**: B19 ✅ (complete — all required backend fields already live)  
**Pure frontend — no backend changes needed**

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-fe-b26-design.md`** — every section (A–I)

**Critical rules for this batch:**

- **Rule 1.1**: Before writing ANY hook extension or API reference, verify the endpoint fields exist in `backend/openapi_schema_map.md` AND in `@pilot/shared-types` after `pnpm sync-api-types`. If `JobResponse` does not include `status_code`/`site_name`/`customer_name`/`job_number` after syncing → **STOP and ask Tom** (B19 fields may not be deployed yet).
- **Rule 1.2**: Do NOT invent field names. Every field name used (`job_number`, `quote_number`, `status_code`, `site_name`, `customer_name`) must appear in the synced TypeScript types or be confirmed via `grep` against `backend/openapi_schema_map.md`.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned for `/api/v1/...` calls.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new component — `<RoleGate>`, `<LoadingState>`, `<ErrorState>` are already available.
- **Rule 8**: No new npm dependencies without first checking what is already installed in `package.json`.
- **Rule 9**: Route files in `apps/web/src/app/(authed)/` MUST be thin server components — no `"use client"`, no data fetching.
- **Rule 10**: If ANY test fails during your work — even one that appears to be pre-existing — **you must fix it before declaring the batch done**. No "not my fault" exception.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| "Convert to Invoice" CTA destination | Navigate to `/invoices/new?job_id={jobId}` (Link, not mutation) | Aligned with FE-B29 full-page invoice builder spec |
| "Create Job" entry point on accepted quotes | Opens `JobFormModal` in modal (not a new route) | Consistent with FE-B24 "Add Job" pattern |
| Quote-to-job conversion status | Do NOT call `useConvertQuote` — just create the job with `quote_id` | Status update is out of scope for this CTA |
| `DrillDownPanel` customer-group rows | `job_number` will be null → render "—" in Job # column | No special case needed — graceful fallback |
| `quote.title` in Quotes list | Do NOT show — `quote_number` in column is sufficient | Keep list clean; title is better on detail page |

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend

# Web only (this batch)
pnpm --filter web test 2>&1 | tail -5
```

Record the exact pass/fail count. These numbers must still hold at the end of the batch.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed. Either confirm with Tom that the failure is a known accepted issue, or fix it before touching any batch files.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

This regenerates `packages/shared-types/src/api-schema.d.ts` from the live backend OpenAPI spec.

> **⚠️ CRITICAL GATE**: After running `pnpm sync-api-types`, verify the following fields exist in the generated types:
>
> ```bash
> grep -n "job_number\|site_name\|customer_name\|status_code" \
>   packages/shared-types/src/api-schema.d.ts | head -30
>
> grep -n "quote_number" \
>   packages/shared-types/src/api-schema.d.ts | head -10
> ```
>
> If `JobResponse` does not include `job_number`, `status_code`, `site_name`, `customer_name` → **STOP. Do not implement steps 1–2. Notify Tom that B19 fields are not in the live backend schema.** Steps 3–6 (QuotesPage, QuoteDetailPage, DrillDownPanel) may proceed independently since they use `JobListItem` and profitability rows which confirmed have these fields.

---

## Pre-Work: Verify Endpoints

All endpoints in this batch are pre-existing. Verify the B19 field additions are present:

```bash
# Confirm job_number on JobListItem (list)
grep -A 10 '"job_number"' backend/openapi_schema_map.md | head -20

# Confirm customer_name on profitability rows
grep -B 5 -A 3 '"customer_name"' backend/openapi_schema_map.md | grep -A 3 "group_key"

# Confirm quote_number on QuoteListItem
grep -A 3 '"quote_number"' backend/openapi_schema_map.md | head -15
```

**Verified endpoints for this batch** (all pre-existing from B19 + prior batches):

| Hook | Endpoint | Verified |
|---|---|---|
| `useJob(jobId)` | `GET /api/v1/jobs/{job_id}` → `JobResponse` | B19 — confirm `status_code`/`site_name`/`customer_name`/`job_number` after sync-api-types |
| `useJobs()` | `GET /api/v1/jobs/` → `JobListItem[]` | B19 — `job_number`, `status_code`, `customer_name` confirmed in schema map |
| `useQuotes()` | `GET /api/v1/quotes/` → `QuoteListItem[]` | B19 — `quote_number` confirmed in schema map |
| `useProfitability()` | `GET /api/v1/reports/profitability` | B19 — `customer_name` confirmed in schema map |
| `useCreateJob` | `POST /api/v1/jobs/` | Pre-existing (FE-B24) |

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

```
frontend/apps/web/src/features/jobs/components/JobDetailHeader.tsx
← understand the exact broken state: 3 UUID bugs (breadcrumb, StatusBadge, site)

frontend/apps/web/src/features/jobs/components/JobDetailPage.tsx
← understand line 80: isTerminalStatus(job.status_id) bug; Convert button state

frontend/apps/web/src/features/jobs/components/JobsPage.tsx (lines 76–112)
← understand the "→ Invoice" link at line 101

frontend/apps/web/src/features/quotes/components/QuotesPage.tsx (lines 120–284)
← find the exact Quote ID column render to fix

frontend/apps/web/src/features/quote-approval/QuoteDetailPage.tsx (lines 40–180)
← understand isAccepted flag and where to add the Create Job CTA

frontend/apps/web/src/features/jobs/components/JobFormModal.tsx
← check if prefilledQuoteId prop already exists; if not, plan to add it

frontend/apps/web/src/features/profitability/hooks/useProfitability.ts
← understand RawProfitabilityRow and ClosedJob interfaces to extend

frontend/apps/web/src/features/profitability/components/DrillDownPanel.tsx
← understand table columns to modify

frontend/apps/web/src/mocks/handlers/index.ts
← understand how to register new MSW handlers if needed
```

Also run these to locate related files:

```bash
# Confirm JobFormModal accepts quoteId today
grep -n "quoteId\|quote_id\|prefilledQuote" \
  frontend/apps/web/src/features/jobs/components/JobFormModal.tsx

# Confirm useJobs hook type shape (JobListItem fields)
grep -n "job_number\|JobListItem" \
  frontend/apps/web/src/features/jobs/hooks/useJobs.ts | head -20

# Confirm useQuotes hook type shape
grep -n "quote_number\|QuoteListItem" \
  frontend/apps/web/src/features/quotes/hooks/useQuotes.ts | head -20

# Find existing MSW handler files
find frontend/apps/web/src/mocks/handlers -name "*.ts" | head -20
```

---

## Context: What This Batch Does

| # | Task | File | What Changes |
|---|---|---|---|
| 1 | Fix `isTerminalStatus` bug | `JobDetailPage.tsx` | Line 80: `job.status_id` → `job.status_code ?? ""`; clean up `TERMINAL_STATUSES` set |
| 2 | Fix 3 UUID bugs in `JobDetailHeader` | `JobDetailHeader.tsx` | Breadcrumb shows `job_number`; StatusBadge uses `status_code`; Site shows `site_name`; add customer name + quote link |
| 3 | Fix broken "→ Invoice" link | `JobsPage.tsx` | Change `?action=convert` → `/invoices/new?job_id=${job.id}`; rename label |
| 4 | Render `quote_number` in Quotes list | `QuotesPage.tsx` | Column header "Quote ID" → "Quote #"; render `q.quote_number` |
| 5 | Add "Create Job" CTA on accepted quotes | `QuoteDetailPage.tsx` + `JobFormModal.tsx` | Button when `isAccepted && isOwner`; opens `JobFormModal` with `prefilledQuoteId` |
| 6 | Fix DrillDownPanel — job # + customer | `DrillDownPanel.tsx` + `useProfitability.ts` | Extend interfaces; add "Customer" column; render `job_number` |
| 7 | Integration tests | `__tests__/batch_fe_b26/` | One test file per changed surface (6 test files minimum) |

---

## STEP 1 — Fix `isTerminalStatus` bug in `JobDetailPage.tsx`

**Read the file first**: `read_file frontend/apps/web/src/features/jobs/components/JobDetailPage.tsx`

**Adjustment needed** (read file to confirm line numbers before editing):

1. Simplify `TERMINAL_STATUSES` to only valid status codes:
   ```typescript
   const TERMINAL_STATUSES = new Set(["completed", "invoice_pending"]);
   ```
   Remove the `"status-completed"`, `"status-invoice-pending"`, `"status-invoice_pending"` entries — these are not real status codes.

2. Change line 80 from:
   ```typescript
   const showConvertButton = job ? isTerminalStatus(job.status_id) : false;
   ```
   to:
   ```typescript
   const showConvertButton = job ? isTerminalStatus(job.status_code ?? "") : false;
   ```
   Requires `status_code` to exist on the type returned by `useJob(jobId)`. If it does not exist yet (B19 not in types) → skip this step and add a TODO comment.

3. Change the "Convert to Invoice" button action from calling `createInvoice()` mutation to navigating to the invoice builder:
   ```tsx
   // Before (mutation call):
   <button onClick={() => createInvoice()} ...>Convert to Invoice</button>
   
   // After (Link navigation):
   import { useRouter } from "next/navigation";
   // ...
   const router = useRouter();
   // ...
   <button
     onClick={() => router.push(`/invoices/new?job_id=${jobId}`)}
     disabled={isCreating}
     className="..."
   >
     Create Invoice
   </button>
   ```
   
   Read the file to understand what the current button looks like and where `isCreating` is used. Adjust accordingly.

**Intermediate verification**:
```bash
cd <repo>/frontend
pnpm --filter web test -- __tests__/batch_fe_b26 2>&1 | tail -10
```
(Tests won't exist yet — this is just to confirm no compilation errors in Step 1.)

---

## STEP 2 — Fix `JobDetailHeader.tsx` — 3 UUID Bugs + 2 New Display Elements

**Read the file first**: `read_file frontend/apps/web/src/features/jobs/components/JobDetailHeader.tsx`

This file is 89 lines. Read it fully before modifying.

**Changes required** (adjust to match exact file content):

### 2a — Fix `StatusBadge` component

The current `StatusBadge` accepts `statusId: string` (UUID) and tries to strip `"status-"` prefix. Refactor to accept `statusCode: string` and use the same color/label maps as `JobsPage.tsx StatusBadge`:

```typescript
function StatusBadge({ statusCode }: { statusCode: string }) {
  const colorMap: Record<string, string> = {
    draft: "bg-neutral-100 text-neutral-700",
    scheduled: "bg-blue-100 text-blue-700",
    in_progress: "bg-yellow-100 text-yellow-800",
    completed: "bg-green-100 text-green-700",
    invoice_pending: "bg-purple-100 text-purple-700",
    cancelled: "bg-red-100 text-red-700",
  };

  const labelMap: Record<string, string> = {
    draft: "Draft",
    scheduled: "Scheduled",
    in_progress: "In Progress",
    completed: "Completed",
    invoice_pending: "Invoice Pending",
    cancelled: "Cancelled",
  };

  const colorClass = colorMap[statusCode] ?? "bg-neutral-100 text-neutral-700";
  const label = labelMap[statusCode] ?? statusCode.replace(/_/g, " ");

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-sm font-medium ${colorClass}`}>
      {label}
    </span>
  );
}
```

### 2b — Fix breadcrumb (raw UUID → `job_number`)

```tsx
// Before (line 76 approximately):
<span className="text-neutral-900 font-medium">Job {jobId}</span>

// After:
<span className="text-neutral-900 font-medium">
  {job.job_number ?? `Job ${jobId.slice(0, 8)}…`}
</span>
```

### 2c — Fix StatusBadge call site

```tsx
// Before:
<StatusBadge statusId={job.status_id} />

// After:
<StatusBadge statusCode={job.status_code ?? job.status_id} />
```

### 2d — Fix site display (UUID → `site_name`)

```tsx
// Before:
<span className="text-sm text-neutral-500">Site: {job.site_id}</span>

// After (omit if null):
{job.site_name && (
  <span className="text-sm text-neutral-500">📍 {job.site_name}</span>
)}
```

### 2e — Add customer name display

Add to the same metadata row as status + dates:
```tsx
{job.customer_name && (
  <span className="text-sm font-medium text-neutral-700">{job.customer_name}</span>
)}
```

### 2f — Add linked quote reference

```tsx
{job.quote_id && (
  <Link
    href={`/quotes/${job.quote_id}`}
    className="text-sm text-brand-600 hover:text-brand-800 transition-colors"
  >
    View Quote →
  </Link>
)}
```

> **Note**: `quote_id` must be on `JobResponse`. Check the synced types. If absent, skip this element.

**Adjust prop names to match what you actually find in the file** — do not assume the exact interface shape matches these examples.

---

## STEP 3 — Fix `JobsPage.tsx` "→ Invoice" Link

**Read the relevant section first**: `read_file frontend/apps/web/src/features/jobs/components/JobsPage.tsx --offset 76 --limit 40`

Locate the "→ Invoice" link in `JobRow` (approximately line 100–106). Change:

```tsx
// Before:
<Link
  href={`/jobs/${job.id}?action=convert`}
  className="text-sm text-neutral-500 hover:text-neutral-700"
>
  → Invoice
</Link>

// After:
<Link
  href={`/invoices/new?job_id=${job.id}`}
  className="text-sm text-brand-600 hover:text-brand-800 font-medium"
>
  Create Invoice
</Link>
```

This is the only change in `JobsPage.tsx`. No other modifications needed.

---

## STEP 4 — Fix `QuotesPage.tsx` Quote Number Display

**Read the file first (lines 120–284)**: `read_file frontend/apps/web/src/features/quotes/components/QuotesPage.tsx --offset 120 --limit 164`

Find the table column that renders the Quote ID. It will look approximately like:
```tsx
<td className="...">
  {q.id.slice(0, 8)}…
</td>
```
or similar (may use `q.status_id` or `q.id`). Also find the `<th>` header for that column.

**Changes:**
1. Column header: Change `"Quote ID"` → `"Quote #"`
2. Column cell: Change UUID display → `{q.quote_number}`

The `QuoteListItem` type from `useQuotes` includes `quote_number: string` per B19. Verify via:
```bash
grep -n "quote_number" frontend/apps/web/src/features/quotes/hooks/useQuotes.ts
```
If `quote_number` is not yet in the hook's `QuoteListItem` type, add it as `quote_number: string` before using it.

---

## STEP 5 — Add "Create Job" CTA to `QuoteDetailPage.tsx`

**Read the file first**: `read_file frontend/apps/web/src/features/quote-approval/QuoteDetailPage.tsx`

**Also read `JobFormModal.tsx`**: `read_file frontend/apps/web/src/features/jobs/components/JobFormModal.tsx`

### 5a — Check if `JobFormModal` accepts `prefilledQuoteId`

```bash
grep -n "quoteId\|prefilledQuote\|quote_id" \
  frontend/apps/web/src/features/jobs/components/JobFormModal.tsx
```

If `prefilledQuoteId` prop does not exist, add it to `JobFormModalProps` and wire it into the `useCreateJob` mutation payload:

```typescript
// In JobFormModalProps:
prefilledQuoteId?: string;

// In JobFormContent props (inner component):
prefilledQuoteId?: string;

// In createJob mutation call (adjust to actual hook signature):
createJob({
  customer_id: customerId,
  site_id: siteId,
  quote_id: prefilledQuoteId ?? undefined,  // add this
  scheduled_start_at: scheduledStart || undefined,
  // ... rest
});
```

### 5b — Add "Create Job" CTA to `QuoteDetailPage`

Add imports at top of file:
```tsx
import { JobFormModal } from "../jobs/components/JobFormModal";
// import useRouter if not already imported
import { useRouter } from "next/navigation";
```

Add state:
```tsx
const [createJobOpen, setCreateJobOpen] = useState(false);
const router = useRouter();
```

Add button in the quote header section, alongside/below existing action buttons. Place it where `isAccepted && isOwner`:

```tsx
{isAccepted && isOwner && (
  <RoleGate permission="jobs.create">
    <button
      type="button"
      onClick={() => setCreateJobOpen(true)}
      className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-md hover:bg-brand-700 transition-colors"
      data-testid="create-job-from-quote-btn"
    >
      Create Job from Quote
    </button>
  </RoleGate>
)}
```

Add `JobFormModal` alongside `QuoteMetadataEditModal` (or wherever modals are rendered in the component):
```tsx
<JobFormModal
  open={createJobOpen}
  onClose={() => setCreateJobOpen(false)}
  prefilledQuoteId={quoteId}
  onSuccess={() => {
    setCreateJobOpen(false);
    router.push("/jobs");
  }}
/>
```

**Read the file to confirm**: where `isAccepted` is defined, where existing modals are placed, and what `RoleGate` imports look like. Adjust accordingly.

---

## STEP 6 — Fix `DrillDownPanel` + `useProfitability.ts`

### 6a — Extend `RawProfitabilityRow` interface

**Read the file first**: `read_file frontend/apps/web/src/features/profitability/hooks/useProfitability.ts`

In `RawProfitabilityRow` interface, add two new optional fields:
```typescript
interface RawProfitabilityRow {
  group_key: string;
  group_label: string;       // now contains job_number when group_by=job
  customer_name?: string | null;   // B19: from profitability JOIN
  job_count: number;
  quoted_total_cents: number;
  actual_labor_cost_cents: number;
  actual_material_cost_cents: number;
  actual_profit_cents: number;
  margin_pct: number | null;
  margin_bucket: string | null;
  below_margin_target: boolean;
}
```

### 6b — Extend `ClosedJob` interface

```typescript
export interface ClosedJob {
  id: string;
  title: string;                    // keep — maps from group_label for backward compat
  job_number: string | null;        // B19: human-readable job ID
  customer_name: string | null;     // B19: from profitability JOIN
  close_date: string;
  revenue_cents: number;
  margin_pct: number;
  margin_bucket: MarginBucket;
}
```

### 6c — Update the adapter in `adaptProfitabilityResponse()`

Find where closed_jobs are mapped (read the file to find the exact adapter code). Add the new fields to the mapping:

```typescript
// In the closed_jobs mapping (read file to find exact location):
const closedJob: ClosedJob = {
  id: r.group_key,
  title: r.group_label,          // unchanged
  job_number: r.group_label ?? null,  // group_label IS the job_number when group_by=job
  customer_name: r.customer_name ?? null,   // B19 addition
  close_date: /* existing */,
  revenue_cents: /* existing */,
  margin_pct: /* existing */,
  margin_bucket: /* existing */,
};
```

> **Note**: `job_number` maps to `group_label` — because B19 changed profitability `group_label` to contain `job_number` (format `JOB-000001`) when `group_by=job`. This is the correct mapping. Read the B19 completion summary for confirmation.

### 6d — Update `DrillDownPanel.tsx`

**Read the file first**: `read_file frontend/apps/web/src/features/profitability/components/DrillDownPanel.tsx`

1. Rename column header "Job" → "Job #"
2. Add new "Customer" column header after "Job #"
3. In the row rendering: render `job.job_number ?? job.title` in "Job #" column
4. Add "Customer" cell: `{job.customer_name ?? "—"}`

```tsx
// Updated thead:
<thead>
  <tr className="border-b border-neutral-100">
    <th className="py-2 pl-4 pr-2 text-left text-caption font-medium text-neutral-600">
      Job #
    </th>
    <th className="py-2 px-2 text-left text-caption font-medium text-neutral-600">
      Customer
    </th>
    <th className="py-2 px-2 text-right text-caption font-medium text-neutral-600">
      Closed
    </th>
    <th className="py-2 px-2 text-right text-caption font-medium text-neutral-600">
      Revenue
    </th>
    <th className="py-2 pl-2 pr-4 text-right text-caption font-medium text-neutral-600">
      Margin
    </th>
  </tr>
</thead>

// Updated tbody row:
<tr key={job.id} className="border-b border-neutral-50 hover:bg-neutral-50">
  <td className="py-2 pl-4 pr-2">
    <p className="text-body text-neutral-900 truncate max-w-32">
      {job.job_number ?? job.title}
    </p>
  </td>
  <td className="py-2 px-2">
    <p className="text-body text-neutral-600 truncate max-w-32">
      {job.customer_name ?? "—"}
    </p>
  </td>
  {/* ... rest of cells unchanged */}
</tr>
```

**Adjust class names and structure to match what you actually find in the file.** The above is a starting point, not gospel.

---

## Test Implementation

### Test file locations

Create in `apps/web/src/__tests__/batch_fe_b26/`:

| Test File | Surface Tested |
|---|---|
| `job_detail_header.integration.test.tsx` | `JobDetailHeader` UUID fix (job_number, status_code, site_name) |
| `job_detail_convert_button.integration.test.tsx` | `JobDetailPage` Convert button visibility + navigation |
| `jobs_page_invoice_link.integration.test.tsx` | `JobsPage` "Create Invoice" link destination |
| `quotes_page_number.integration.test.tsx` | `QuotesPage` quote_number column |
| `quote_detail_create_job.integration.test.tsx` | `QuoteDetailPage` "Create Job" CTA |
| `drilldown_panel_columns.integration.test.tsx` | `DrillDownPanel` job # + customer columns |

### TanStack Query — Required Setup

**Always use `retry: false`** on the QueryClient in tests:

```typescript
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
```

### MSW Setup

```typescript
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { handlers } from "../../mocks/handlers/index";

const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

### Mock Next.js Router

```typescript
import { vi } from "vitest";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  usePathname: () => "/jobs",
  useRouter: () => ({ push: mockPush, back: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: any) =>
    React.createElement("a", { href, ...rest }, children),
}));
```

### Minimum Test Coverage Per Surface

**`job_detail_header.integration.test.tsx`**:
1. Renders `job_number` in breadcrumb (not raw UUID)
2. Renders correct status badge label from `status_code`
3. Renders `site_name` (not site UUID)
4. Renders `customer_name`

**`job_detail_convert_button.integration.test.tsx`**:
1. "Create Invoice" button is visible when `job.status_code === "completed"`
2. "Create Invoice" button is NOT visible when `job.status_code === "draft"`
3. Clicking "Create Invoice" navigates to `/invoices/new?job_id={id}` (check `mockPush`)

**`jobs_page_invoice_link.integration.test.tsx`**:
1. "Create Invoice" link href contains `/invoices/new?job_id=` (not `?action=convert`)
2. Link only visible for completed/invoice_pending jobs

**`quotes_page_number.integration.test.tsx`**:
1. Column header reads "Quote #" (not "Quote ID")
2. Row renders `quote_number` value (e.g., "QUO-000001"), not UUID slice

**`quote_detail_create_job.integration.test.tsx`**:
1. "Create Job from Quote" button visible when `status === "accepted"` AND role is `owner`
2. Button not visible for `owner` when status is `draft`
3. Button not visible for `tech` role when status is `accepted`
4. Clicking button opens `JobFormModal` (check for modal presence)

**`drilldown_panel_columns.integration.test.tsx`**:
1. Column header "Job #" is present
2. Column header "Customer" is present
3. Renders `job_number` value in Job # column
4. Renders `customer_name` value in Customer column
5. Renders "—" when `customer_name` is null

### RBAC Testing Pattern

```typescript
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue, PilotRole } from "@pilot/ui/auth";

function makeAuthValue(role: PilotRole): AuthContextValue {
  return {
    user: { id: "u1", email: "test@example.com", role, tenantId: "t1", displayName: "Test", accessToken: "tok" },
    isAuthenticated: true,
    role,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("tok"),
  };
}

function renderAs(role: PilotRole, component: React.ReactElement) {
  return render(
    React.createElement(AuthContext.Provider, { value: makeAuthValue(role) }, component)
  );
}
```

### MSW Handler Additions

For tests in this batch, create or extend MSW handlers for the job detail and quote detail pages:

```bash
# Check if handlers exist for jobs detail + quotes detail
cat frontend/apps/web/src/mocks/handlers/index.ts
grep -l "api/v1/jobs/" frontend/apps/web/src/mocks/handlers/
```

If no handler exists for `GET /api/v1/jobs/{job_id}` with B19 fields, create a handler that returns mock data including `job_number`, `status_code`, `site_name`, `customer_name`. This only needs to be in the test file's local `server` instance — no need to register globally.

Example mock data shape (adjust field names to match synced types):
```typescript
const mockJobResponse = {
  id: "job-uuid-001",
  tenant_id: "tenant-001",
  customer_id: "cust-001",
  customer_name: "Acme Electric",
  site_id: "site-001",
  site_name: "The Smith Home",
  status_id: "status-uuid-001",
  status_code: "completed",
  job_number: "JOB-000001",
  quote_id: "quote-uuid-001",
  scheduled_start_at: "2026-07-01T08:00:00Z",
  scheduled_end_at: "2026-07-01T12:00:00Z",
  estimated_duration_minutes: 240,
};
```

---

## Final Verification

### Phase 1 — Targeted tests (run after each step during development)

```bash
cd <repo>/frontend

# Run only the new batch test files:
npx vitest run apps/web/src/__tests__/batch_fe_b26 2>&1 | tail -15

# Run all web tests (periodically during development):
pnpm --filter web test 2>&1 | tail -6
```

Fix any failure before moving to the next step — including failures that appear pre-existing.

### Phase 2 — Full verification (run once at the very end, before DoD sign-off)

```bash
cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter mobile build && pnpm --filter @pilot/ui lint && pnpm --filter web lint && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== FE-B26 FINAL VERIFICATION COMPLETE ==="
```

> **Any failure in either phase must be fixed before the batch is declared done.** There is no "pre-existing failure" exception without explicit written confirmation from Tom.

---

## Definition of Done — FE-B26

Update `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 FE-B26 row when each item is done:

- [ ] Pre-modification regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — B19 fields (`job_number`, `status_code`, `site_name`, `customer_name`, `quote_number`) present in generated types
- [ ] Design doc `batch-fe-b26-design.md` fully read before writing any code
- [ ] All mandatory source files read before modifying (see Pre-Work list above)
- [ ] All endpoint fields verified via `pnpm sync-api-types` or `grep` against schema map
- [ ] **STEP 1**: `JobDetailPage.tsx` — `isTerminalStatus` bug fixed; `TERMINAL_STATUSES` cleaned up; Convert button navigates to `/invoices/new?job_id=`
- [ ] **STEP 2**: `JobDetailHeader.tsx` — breadcrumb shows `job_number`; StatusBadge uses `status_code`; site shows `site_name`; customer name + quote link added
- [ ] **STEP 3**: `JobsPage.tsx` — "→ Invoice" link → `/invoices/new?job_id={id}`; label → "Create Invoice"
- [ ] **STEP 4**: `QuotesPage.tsx` — "Quote ID" → "Quote #" header; UUID slice → `quote_number` value
- [ ] **STEP 5**: `QuoteDetailPage.tsx` — "Create Job from Quote" button visible for `owner` + `accepted` status; `JobFormModal` opens with `prefilledQuoteId`
- [ ] **STEP 5 (if needed)**: `JobFormModal.tsx` — `prefilledQuoteId?: string` prop added if not already present
- [ ] **STEP 6**: `useProfitability.ts` — `RawProfitabilityRow` + `ClosedJob` interfaces extended with `job_number` + `customer_name`
- [ ] **STEP 6**: `DrillDownPanel.tsx` — "Job #" column header; "Customer" column added; `job_number` + `customer_name` rendered
- [ ] 6 integration test files created in `__tests__/batch_fe_b26/`
- [ ] All new MSW handlers included in test files (not required in global `index.ts` unless shared)
- [ ] Zero TypeScript errors (`pnpm --filter web check-types` passes)
- [ ] Zero ESLint errors (`pnpm --filter web lint` passes)
- [ ] No regressions in pre-existing web test suite
- [ ] **Phase 2 FULL verification command passes** (`=== FE-B26 FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter mobile build && pnpm --filter @pilot/ui lint && pnpm --filter web lint && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== FE-B26 FINAL VERIFICATION COMPLETE ==="
  ```
- [ ] Final test count (before → after) documented below in Completion Summary

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** subsection to `dev-docs/analysis/pilot-launch-plan.md` in the FE-B26 section using the format below.

```markdown
### FE-B26 — UUID Display Fixes, Job/Quote Number Display, Profitability Drill-Down, Job-from-Quote CTA: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (web)
**Final**: X+N passed (+N new tests)

#### What Was Accomplished

- [Brief description of each key fix]

#### Files Changed / Created

| File | Action |
|---|---|
| `apps/web/src/features/jobs/components/JobDetailPage.tsx` | Updated — isTerminalStatus bug fixed; Convert button navigates |
| `apps/web/src/features/jobs/components/JobDetailHeader.tsx` | Updated — breadcrumb/status/site UUID fixes; customer name + quote link |
| `apps/web/src/features/jobs/components/JobsPage.tsx` | Updated — Invoice link destination fixed |
| `apps/web/src/features/quotes/components/QuotesPage.tsx` | Updated — quote_number display |
| `apps/web/src/features/quote-approval/QuoteDetailPage.tsx` | Updated — Create Job CTA |
| `apps/web/src/features/jobs/components/JobFormModal.tsx` | Updated — prefilledQuoteId prop (if added) |
| `apps/web/src/features/profitability/hooks/useProfitability.ts` | Updated — ClosedJob + RawProfitabilityRow extended |
| `apps/web/src/features/profitability/components/DrillDownPanel.tsx` | Updated — Job # + Customer columns |
| `apps/web/src/__tests__/batch_fe_b26/*.integration.test.tsx` | Created — 6 test files |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `batch_fe_b26/job_detail_header.integration.test.tsx` | Integration | N | ✅ |
| `batch_fe_b26/job_detail_convert_button.integration.test.tsx` | Integration | N | ✅ |
| `batch_fe_b26/jobs_page_invoice_link.integration.test.tsx` | Integration | N | ✅ |
| `batch_fe_b26/quotes_page_number.integration.test.tsx` | Integration | N | ✅ |
| `batch_fe_b26/quote_detail_create_job.integration.test.tsx` | Integration | N | ✅ |
| `batch_fe_b26/drilldown_panel_columns.integration.test.tsx` | Integration | N | ✅ |
```
