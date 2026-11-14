# Implementation Prompt: FE-B24 — CRUD Completeness: Job Create, Invoice Create Rework, Customer Name Display, Quote Edit, Customer Delete

**Mode**: Pilot React Engineer  
**Batch**: FE-B24  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §Integration & UI Hardening  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-fe-b24-design.md`  
**Estimated session**: 4–6 hours  
**Platform**: Web only (`apps/web`)  
**Backend companion**: B18 must complete first — `PATCH /api/v1/jobs/{job_id}` + `customer_name` in `InvoiceSummary`

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-fe-b24-design.md`** — every section (A–I)

**Critical rules for this batch:**

- **Rule 1.1**: Before writing ANY hook or API call, verify the endpoint exists in `backend/openapi_schema_map.md`. If NOT there → **STOP and ask Tom**.
- **Rule 1.2**: Do NOT invent URL patterns or parameter names. Every shape comes from `openapi.json` or the design doc.
- **Rule 1.3**: Run `pnpm sync-api-types` before starting — all TypeScript types for backend payloads come from `@pilot/shared-types`, never hand-written interfaces.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned for `/api/v1/...` calls.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new component — `<LoadingState>`, `<ErrorState>`, `<EmptyState>`, `<RoleGate>` are all available.
- **Rule 8**: No new npm dependencies without first checking what is already installed in `package.json`.
- **Rule 9**: Route files in `apps/web/src/app/(authed)/` MUST be thin server components — no `"use client"`, no data fetching.
- **Rule 10**: If ANY test fails during your work — fix it before declaring the batch done.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Invoice Create — customer_id | NOT required in FE form; derived server-side from quote/job linkage | Backend derives `customer_id` from linked quote or job |
| Invoice Create — standalone warning | Show warning if neither quote nor job selected, but don't block submit | Standalone invoices are valid per `InvoiceCreate` schema |
| Customer delete — pattern | Confirm-as-Turn modal before DELETE fires | Prevents accidental deletion |
| Quote edit — which statuses | Only draft quotes show the edit modal link | Accepted/approved quotes are locked |
| Job Create — quote linkage | Optional | `quote_id` is optional in `JobCreate` |
| `status_id` in Job forms | Not in Create or Edit forms | Status transitions go through dispatch board |

---

## Companion Backend Tasks — Already Complete (B18)

B18 must be verified complete before starting this batch. Confirm:

```bash
grep -A 3 "customer_name" backend/openapi_schema_map.md
grep "PATCH.*jobs" backend/openapi_schema_map.md
```

Both must return results. If not → **STOP and wait for B18 to complete**.

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend

# Web baseline
pnpm --filter web test 2>&1 | tail -5
```

Record exact count. Fix any pre-existing failures before starting.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

After syncing, verify:
```bash
grep "customer_name" frontend/packages/shared-types/src/api-schema.d.ts
grep "JobUpdate\|job_update" frontend/packages/shared-types/src/api-schema.d.ts
```

> **If `pnpm sync-api-types` fails** because B18 is not yet deployed → STOP and wait for B18.

---

## Pre-Work: Verify Endpoints

```bash
grep -A 5 "POST.*jobs" backend/openapi_schema_map.md
grep -A 5 "POST.*invoices" backend/openapi_schema_map.md
grep -A 5 "PATCH.*quotes" backend/openapi_schema_map.md
grep -A 5 "DELETE.*customers" backend/openapi_schema_map.md
grep "customer_name" backend/openapi_schema_map.md
```

**Verified endpoints for this batch:**

| Hook | Endpoint | Verified |
|---|---|---|
| `useCreateJob` | `POST /api/v1/jobs/` | Must confirm in openapi_schema_map.md |
| `useCreateInvoice` | `POST /api/v1/invoices/` | Must confirm in openapi_schema_map.md |
| `useInvoices` (display fix) | `GET /api/v1/invoices/` | Must confirm `customer_name` field |
| `useUpdateQuote` | `PATCH /api/v1/quotes/{id}` | Must confirm in openapi_schema_map.md |
| `useDeleteCustomer` | `DELETE /api/v1/customers/{id}` | Must confirm in openapi_schema_map.md |

**If any endpoint is NOT found → STOP. Do not invent a URL. Ask Tom.**

---

## Pre-Work: Read These Source Files

Read each with `read_file` before writing any code:

```
frontend/apps/web/src/features/jobs/components/JobsPage.tsx         ← understand existing "Add Job" button state; find where to add button
frontend/apps/web/src/features/jobs/hooks/                           ← find existing job hooks (use find command)
frontend/apps/web/src/features/invoices/components/InvoicesPage.tsx  ← find the empty modal + customer_id display to fix
frontend/apps/web/src/features/invoices/hooks/useInvoices.ts         ← understand invoice list hook shape
frontend/apps/web/src/features/quotes/components/QuoteActionBar.tsx  ← understand existing quote action patterns
frontend/apps/web/src/features/quote-approval/QuoteDetailPage.tsx    ← find where to wire "Edit metadata" link
frontend/apps/web/src/features/customers/components/CustomersPage.tsx ← or CustomerOverviewTab.tsx — find where to add delete button
frontend/packages/ui/src/index.ts                                    ← confirm shared component import paths
frontend/apps/web/src/mocks/handlers/index.ts                        ← understand handler registration pattern
```

Also run:
```bash
find frontend/apps/web/src/features/jobs/hooks -name "*.ts" | head -10
find frontend/apps/web/src/features/invoices -name "*.ts" | head -10
find frontend/apps/web/src/features/quotes/hooks -name "*.ts" | head -10
find frontend/apps/web/src/features/customers/hooks -name "*.ts" | head -10
find frontend/apps/web/src/mocks/handlers -name "*.ts" | head -20
```

---

## Context: What This Batch Does

| Step | Description | New Files |
|---|---|---|
| 1 | `useCreateJob` hook | `features/jobs/hooks/useCreateJob.ts` |
| 2 | `JobFormModal` — customer → site cascade, schedule pickers | `features/jobs/components/JobFormModal.tsx` |
| 3 | Wire "Add Job" button in `JobsPage.tsx` | modify `features/jobs/components/JobsPage.tsx` |
| 4 | MSW handler for `POST /api/v1/jobs/` | `mocks/handlers/jobHandlers.ts` (new or extend) |
| 5 | Rework `InvoiceCreateModal` with proper form fields | modify `features/invoices/components/InvoiceCreateModal.tsx` |
| 6 | Fix invoice list `customer_name` display | modify `features/invoices/components/InvoicesPage.tsx` |
| 7 | Update invoice MSW handler with `customer_name` | modify `mocks/handlers/invoiceDetailHandlers.ts` |
| 8 | `useUpdateQuote` hook | `features/quotes/hooks/useUpdateQuote.ts` |
| 9 | `QuoteMetadataEditModal` — expires_at, currency | `features/quotes/components/QuoteMetadataEditModal.tsx` |
| 10 | Wire edit action in `QuoteDetailPage` for draft quotes | modify `features/quote-approval/QuoteDetailPage.tsx` |
| 11 | `DeleteCustomerModal` with confirm pattern | `features/customers/components/DeleteCustomerModal.tsx` |
| 12 | Wire delete button in customer detail/overview | modify customers feature |
| 13 | Tests | `__tests__/batch_fe_b24/` |

---

## STEP 1 — Create `useCreateJob` hook

**File**: `frontend/apps/web/src/features/jobs/hooks/useCreateJob.ts`

Read existing job hooks first (use `find` command above to locate them).

```typescript
// Adjust imports to match what you find in the codebase
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

interface JobCreatePayload {
  customer_id: string;
  site_id: string;
  quote_id?: string;
  scheduled_start_at?: string; // ISO 8601
  scheduled_end_at?: string;
  estimated_duration_minutes?: number;
}

export function useCreateJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: JobCreatePayload) =>
      apiClient.post("/api/v1/jobs/", payload).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}
```

> **Adjust the import path for `apiClient`** — verify the exact import path by reading `packages/shared-api/src/index.ts`.

---

## STEP 2 — Create `JobFormModal` component

**File**: `frontend/apps/web/src/features/jobs/components/JobFormModal.tsx`

Read the design doc §F3 for the component contract. Read existing form modal components (e.g., `CreateCustomerModal.tsx`) for the established modal pattern in this codebase before writing.

Key behaviors:
- Customer dropdown: calls `GET /api/v1/customers/` to populate options
- Site dropdown: calls `GET /api/v1/sites/?customer_id={id}` — re-fetches when customer changes
- When customer changes → reset site selection
- Optional fields: `scheduled_start_at` (datetime-local input), `scheduled_end_at` (datetime-local input), `estimated_duration_minutes` (number input)
- Submit: calls `useCreateJob`, closes modal on success
- Error: displays API error message in form
- `<LoadingState>` while customers load
- `<RoleGate permission="jobs.create">` wraps the submit button (or the whole modal trigger)

---

## STEP 3 — Wire "Add Job" button in `JobsPage.tsx`

Read `JobsPage.tsx` before modifying. The current empty state says "Jobs appear from dispatch board". Replace or augment:

- Add "Add Job" button in the page header (consistent with "Add Customer" button pattern in `CustomersPage.tsx`)
- Button opens `JobFormModal`
- Wrap button in `<RoleGate permission="jobs.create">` so only owner/office_staff see it

Run targeted test after this step:
```bash
pnpm --filter web test -- features/jobs 2>&1 | tail -8
```

---

## STEP 4 — MSW handler for `POST /api/v1/jobs/`

**File**: `frontend/apps/web/src/mocks/handlers/jobHandlers.ts`

Check if this file already exists:
```bash
find frontend/apps/web/src/mocks/handlers -name "job*" | head -5
```

If it exists, read it first. If not, create it:

```typescript
import { http, HttpResponse } from "msw";

export const jobHandlers = [
  http.post("/api/v1/jobs/", async ({ request }) => {
    const body = (await request.json()) as any;
    return HttpResponse.json({
      id: "mock-job-id-001",
      tenant_id: "mock-tenant-id",
      customer_id: body.customer_id,
      site_id: body.site_id,
      status_id: "mock-status-id",
      scheduled_start_at: body.scheduled_start_at ?? null,
      scheduled_end_at: body.scheduled_end_at ?? null,
      estimated_duration_minutes: body.estimated_duration_minutes ?? null,
      actual_labor_cost_cents: 0,
      actual_material_cost_cents: 0,
      actual_profit_cents: 0,
      is_active: true,
    }, { status: 201 });
  }),
];
```

**Register in barrel** — read `mocks/handlers/index.ts` first, then add:
```typescript
import { jobHandlers } from "./jobHandlers";
// ...
export const handlers = [
  ...existingHandlers,
  ...jobHandlers,
];
```

> **This registration step is mandatory.** Without it the handler is never loaded.

---

## STEP 5 — Rework `InvoiceCreateModal`

Read `InvoiceCreateModal.tsx` first. The current implementation fires with zero form fields. Replace the modal body with a proper form.

**Form fields** (all optional per `InvoiceCreate` schema):
- Job linkage dropdown: `GET /api/v1/jobs/` — show job ID + customer name; selecting a job populates context
- Quote linkage dropdown: `GET /api/v1/quotes/` filtered to status=accepted — optional  
- Due date: `<input type="date">` for `due_at`
- Issue date: `<input type="date">` for `issued_at` (default: today)
- Customer notes: `<textarea>` for `customer_notes`
- Warning if neither job nor quote selected: "Creating a standalone invoice. Consider linking to a job or quote."
- Submit: calls `POST /api/v1/invoices/` with `{quote_id?, job_id?, customer_notes?, due_at?, issued_at?}`

Check if `useCreateInvoice` hook already exists:
```bash
find frontend/apps/web/src/features/invoices/hooks -name "useCreate*" | head -5
```

If it doesn't exist, create `features/invoices/hooks/useCreateInvoice.ts`.

---

## STEP 6 — Fix Invoice List `customer_name` Display

Read `InvoicesPage.tsx` to find where `customer_id` is currently displayed as a truncated UUID.

After `pnpm sync-api-types`, the `InvoiceSummary` type will have `customer_name: string | null`.

Replace the truncated UUID display with:
```typescript
// Before: item.customer_id.slice(0, 8) + "..."
// After:
{item.customer_name ?? `${item.customer_id.slice(0, 8)}…`}
```

Use the `customer_name` when available, fall back to UUID slice only if null.

---

## STEP 7 — Update Invoice MSW Handler with `customer_name`

Read `mocks/handlers/invoiceDetailHandlers.ts`. Find the `GET /api/v1/invoices/` list handler and add `customer_name` to the fixture items:

```typescript
// In invoice list fixture:
{
  id: "mock-invoice-id",
  customer_id: "mock-customer-id",
  customer_name: "Smith Electric LLC",  // ADD THIS
  // ... rest of fields
}
```

---

## STEP 8 — Create `useUpdateQuote` hook

**File**: `frontend/apps/web/src/features/quotes/hooks/useUpdateQuote.ts`

Read existing quote hooks first:
```bash
find frontend/apps/web/src/features/quotes/hooks -name "*.ts" | head -10
```

```typescript
interface QuoteUpdatePayload {
  expires_at?: string; // ISO 8601
  currency?: string;
}

export function useUpdateQuote(quoteId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: QuoteUpdatePayload) =>
      apiClient.patch(`/api/v1/quotes/${quoteId}`, payload).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["quote", quoteId] });
      queryClient.invalidateQueries({ queryKey: ["quotes"] });
    },
  });
}
```

---

## STEP 9 — Create `QuoteMetadataEditModal`

**File**: `frontend/apps/web/src/features/quotes/components/QuoteMetadataEditModal.tsx`

Form fields:
- `expires_at`: `<input type="date">` — pre-populated from `currentExpiresAt`
- `currency`: `<select>` with options `["USD", "CAD"]` — pre-selected from `currentCurrency`; default USD
- Submit: calls `useUpdateQuote`, closes modal on success
- Only render on draft quotes — the caller (`QuoteDetailPage`) controls the `open` prop

---

## STEP 10 — Wire `QuoteMetadataEditModal` in `QuoteDetailPage`

Read `features/quote-approval/QuoteDetailPage.tsx` before modifying.

Find the "Edit" link that currently navigates away. For **draft** quotes:
- Add state: `const [editOpen, setEditOpen] = useState(false)`
- Replace or augment the Edit link: `onClick={() => setEditOpen(true)}`
- Render `<QuoteMetadataEditModal open={editOpen} onClose={() => setEditOpen(false)} ... />`
- Only show the edit trigger when `quote.status === 'draft'`

---

## STEP 11 — Create `DeleteCustomerModal`

**File**: `frontend/apps/web/src/features/customers/components/DeleteCustomerModal.tsx`

```typescript
interface DeleteCustomerModalProps {
  customerId: string;
  customerName: string;
  open: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}
```

- Confirmation message: "Delete **{customerName}**? This action cannot be undone."
- Cancel button (closes modal)
- Delete button: calls `DELETE /api/v1/customers/{customerId}` via mutation
- On success: call `onSuccess()` (caller navigates to `/customers`)
- `<RoleGate permission="customers.delete">` wraps the delete button

Check if `useDeleteCustomer` hook already exists:
```bash
find frontend/apps/web/src/features/customers/hooks -name "useDelete*" | head -5
```

If not, create it.

---

## STEP 12 — Wire Delete Button in Customer Detail

Read `CustomerOverviewTab.tsx` or `CustomersPage.tsx` — find where customer actions are displayed.

Add "Delete Customer" button (visually destructive — red/danger styling):
- `<RoleGate permission="customers.delete">` wrapper
- Opens `DeleteCustomerModal` with the current customer's `id` and `display_name`
- On success: navigate to `/customers`

---

## Test Implementation

### TanStack Query Setup for Tests

```typescript
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
import { handlers } from "../../mocks/handlers";

const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

### Minimum Test Coverage

**Integration tests** in `apps/web/src/__tests__/batch_fe_b24/`:

1. `job_create_modal.integration.test.tsx`:
   - "Add Job" button renders for `owner` role
   - "Add Job" button NOT visible for `tech` role (`<RoleGate>`)
   - `JobFormModal` renders when button clicked
   - Submitting form with customer + site fires `POST /api/v1/jobs/`

2. `invoice_create_modal.integration.test.tsx`:
   - Invoice create modal renders with form fields (not empty)
   - `due_at` date input visible
   - Customer notes textarea visible
   - Submit fires `POST /api/v1/invoices/`

3. `invoice_customer_name.integration.test.tsx`:
   - Invoice list renders `customer_name` not UUID string
   - `customer_name` from MSW fixture appears in table

4. `quote_metadata_edit.integration.test.tsx`:
   - Edit link on draft quote opens `QuoteMetadataEditModal`
   - `expires_at` and `currency` inputs visible
   - Submit fires `PATCH /api/v1/quotes/{id}`

5. `delete_customer.integration.test.tsx`:
   - Delete button renders for `owner`
   - Delete button NOT visible for `tech`
   - Clicking delete opens confirmation modal
   - Confirming fires `DELETE /api/v1/customers/{id}`

---

## Final Verification

### Phase 1 — Targeted tests (run after each step)

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -6
```

### Phase 2 — Full verification (run once at the end)

```bash
cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter mobile build && pnpm --filter @pilot/ui lint && pnpm --filter web lint && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — FE-B24

Update `dev-docs/analysis/pilot-launch-plan.md` when each item is done:

- [ ] Pre-modification regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [ ] B18 confirmed complete — `PATCH /api/v1/jobs/{job_id}` and `customer_name` visible in `openapi_schema_map.md`
- [ ] `pnpm sync-api-types` run — `customer_name` visible in shared types
- [ ] Design doc §A–I read before writing any code
- [ ] All mandatory source files read before modifying
- [ ] All endpoint URLs verified in `openapi_schema_map.md`
- [ ] **STEP 1**: `useCreateJob.ts` hook created
- [ ] **STEP 2**: `JobFormModal.tsx` created (customer→site cascade, schedule fields)
- [ ] **STEP 3**: "Add Job" button wired in `JobsPage.tsx` with `<RoleGate permission="jobs.create">`
- [ ] **STEP 4**: `jobHandlers.ts` MSW handler created and registered in `index.ts`
- [ ] **STEP 5**: `InvoiceCreateModal.tsx` reworked — job/quote dropdowns, due_at, customer notes
- [ ] **STEP 6**: `InvoicesPage.tsx` displays `customer_name` instead of truncated UUID
- [ ] **STEP 7**: Invoice MSW fixture updated with `customer_name` field
- [ ] **STEP 8**: `useUpdateQuote.ts` hook created
- [ ] **STEP 9**: `QuoteMetadataEditModal.tsx` created (expires_at, currency)
- [ ] **STEP 10**: QuoteDetailPage wired to open `QuoteMetadataEditModal` on draft quotes
- [ ] **STEP 11**: `DeleteCustomerModal.tsx` created with confirm-as-turn pattern
- [ ] **STEP 12**: Delete button wired in customer detail with `<RoleGate permission="customers.delete">`
- [ ] All new MSW handler files registered in `mocks/handlers/index.ts`
- [ ] Integration tests created in `__tests__/batch_fe_b24/` (5 test files, min 1 test each)
- [ ] Zero TypeScript errors (`pnpm --filter web check-types`)
- [ ] Zero ESLint warnings
- [ ] No regressions in pre-existing web test suite
- [ ] **Phase 2 FULL verification command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter mobile build && pnpm --filter @pilot/ui lint && pnpm --filter web lint && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
  ```
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to pilot-launch-plan.md

---

## Completion Summary

After all Definition of Done items are complete, add to `dev-docs/analysis/pilot-launch-plan.md`:

```markdown
### FE-B24 — CRUD Completeness (Job Create, Invoice Rework, Customer Name, Quote Edit, Customer Delete): Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (web)
**Final**: X+N passed (+N new tests)
**Build**: ✅ Pass — TypeScript errors: 0, ESLint warnings: 0

#### What Was Accomplished

- `useCreateJob` hook + `JobFormModal` (customer→site cascade) + "Add Job" button in `JobsPage`
- `InvoiceCreateModal` reworked — job/quote dropdowns, due_at, issued_at, customer_notes
- Invoice list now shows `customer_name` (not truncated UUID) — requires B18 `customer_name` field
- `useUpdateQuote` hook + `QuoteMetadataEditModal` (expires_at, currency) wired on draft quotes
- `DeleteCustomerModal` (confirm-as-turn) + delete button wired in customer detail

#### Files Changed / Created

| File | Action |
|---|---|
| `features/jobs/hooks/useCreateJob.ts` | Created |
| `features/jobs/components/JobFormModal.tsx` | Created |
| `features/jobs/components/JobsPage.tsx` | Updated — "Add Job" button |
| `mocks/handlers/jobHandlers.ts` | Created |
| `mocks/handlers/index.ts` | Updated — jobHandlers registered |
| `features/invoices/components/InvoiceCreateModal.tsx` | Updated — full form |
| `features/invoices/components/InvoicesPage.tsx` | Updated — customer_name display |
| `mocks/handlers/invoiceDetailHandlers.ts` | Updated — customer_name in fixture |
| `features/quotes/hooks/useUpdateQuote.ts` | Created |
| `features/quotes/components/QuoteMetadataEditModal.tsx` | Created |
| `features/quote-approval/QuoteDetailPage.tsx` | Updated — edit modal wired |
| `features/customers/components/DeleteCustomerModal.tsx` | Created |
| `features/customers/hooks/useDeleteCustomer.ts` | Created (if new) |
| `features/customers/components/CustomerOverviewTab.tsx` | Updated — delete button |
| `__tests__/batch_fe_b24/*.integration.test.tsx` | Created — 5 test files |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `batch_fe_b24/job_create_modal.integration.test.tsx` | Integration | N | ✅ |
| `batch_fe_b24/invoice_create_modal.integration.test.tsx` | Integration | N | ✅ |
| `batch_fe_b24/invoice_customer_name.integration.test.tsx` | Integration | N | ✅ |
| `batch_fe_b24/quote_metadata_edit.integration.test.tsx` | Integration | N | ✅ |
| `batch_fe_b24/delete_customer.integration.test.tsx` | Integration | N | ✅ |
```

## After This Batch — Next Step

FE-B25 (Job Edit UI — `useUpdateJob` + `JobEditModal`) can start once this batch is complete and `PATCH /api/v1/jobs/{job_id}` is confirmed in `openapi_schema_map.md`. FE-B25 will extend the `jobHandlers.ts` MSW file created in this batch.
