# Implementation Prompt: FE-B29 — Full-Page Invoice Builder

**Mode**: Pilot React Engineer  
**Batch**: FE-B29  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 — FE-B29 row  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-fe-b29-design.md`  
**UI Spec**: `dev-docs/architecture-design/batch-designs/batch-ui-ds-b1-design-spec.md` §Surface 1  
**Estimated session**: 4–6 hours  
**Platform**: Web only (`apps/web`)  
**Backend companion**: B20 ✅ Complete — all backend fields and the billable-items endpoint are live

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-fe-b29-design.md`** — every section (A–J)
- **`dev-docs/architecture-design/batch-designs/batch-ui-ds-b1-design-spec.md` §Surface 1** — the approved visual spec you are implementing

**Critical rules for this batch:**

- **Rule 1.1**: Before writing any hook or API call, verify each endpoint in `backend/openapi_schema_map.md`. If NOT there → **STOP and ask Tom**.
- **Rule 1.2**: During pre-work, open `backend/openapi.json` and check the `InvoiceCreate` schema for the exact field names accepted by `POST /api/v1/invoices/`. The design doc lists the B20 additions — verify every field name against the actual OpenAPI spec before coding.
- **Rule 1.3**: Run `pnpm sync-api-types` first — all backend payload types come from `@pilot/shared-types`.
- **Rule 2**: All `/api/v1/...` calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any component — `<LoadingState>`, `<ErrorState>`, `<EmptyState>`, `<RoleGate>` are available.
- **Rule 8**: No new npm dependencies without confirming `package.json` first.
- **Rule 9**: `app/(authed)/invoices/new/page.tsx` is a thin server component — NO `"use client"`, NO data fetching, one line only.
- **Rule 10**: Fix any failing test before declaring done — no "pre-existing" exceptions.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| `InvoiceCreateModal` fate | **Not deleted** — `InvoicesPage.tsx` button now navigates to `/invoices/new` instead of opening the modal. The modal file stays. | Minimize diff risk; modal still used in some test paths |
| Preview Invoice button | **Deferred** — button is visible per spec but renders as disabled with `title="Coming in Phase 1.5"`. No preview flow implemented in FE-B29. | UI-DS-B1 §Interaction Annotations explicitly deferred |
| Customer + Site comboboxes | **Reuse FE-B28** `<CustomerCombobox>` and `<SiteCombobox>` from `apps/web/src/components/` | Already built and tested |
| `quote_id` entry point | **Not implemented** — FE-B29 scope is `?job_id=` only. `?quote_id=` is Phase 2.0. | UI-DS-B1 entry points table |
| Custom line items | Implement the UI (inline expand row). If `POST /api/v1/invoices/` does NOT accept `line_items[]` in `InvoiceCreate` schema → show UI but disable "Add" button with `// TODO: FE-B29-1 — awaiting line items endpoint` comment | Verify in pre-work; do NOT invent an endpoint |
| `square_integration_enabled` | Flag-only — if the tenant has Square enabled, show an info badge near customer header. No Square SDK. | B20 added the platform setting; FE-B29 reads it for display only |
| `?job_id=` pre-fill | Both `useJob(jobId)` (for `customer_id`/`site_id` IDs) AND `useBillableItems(jobId)` (for line items) run in parallel. `BillableItemsResponse.customer_name` is display-only. | Design doc §G — two parallel queries |

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```

Record the exact test count. Fix any pre-existing failures or confirm with Tom before proceeding.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

This regenerates `packages/shared-types/src/api-schema.d.ts` from the live B20 backend. The B20 fields (`payment_terms`, `billing_mode`, `progress_pct`, `internal_memo`, `card_required`) must now be present in the generated types.

---

## Pre-Work: Verify Endpoints

```bash
# Confirm billable-items endpoint
grep -A 8 "billable-items" backend/openapi_schema_map.md

# Confirm POST /api/v1/invoices/ exists
grep -A 3 "POST /api/v1/invoices/" backend/openapi_schema_map.md

# Check InvoiceCreate schema for exact field names (CRITICAL — do this before coding)
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
create = spec['components']['schemas'].get('InvoiceCreate', {})
print('InvoiceCreate fields:')
for k, v in create.get('properties', {}).items():
    print(f'  {k}: {v.get(\"type\", v.get(\"\$ref\", \"?\"))}')
"
```

**Verified endpoints for this batch:**

| Hook | Endpoint | Verified |
|---|---|---|
| `useBillableItems` | `GET /api/v1/jobs/{job_id}/billable-items` | ✅ Confirmed in openapi_schema_map.md |
| `useCreateInvoice` | `POST /api/v1/invoices/` | ✅ Confirmed in openapi_schema_map.md |
| `useJob` (existing) | `GET /api/v1/jobs/{job_id}` | ✅ Already in use by `JobDetailPage` |

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

```
# Invoice hooks to extend:
frontend/apps/web/src/features/invoices/hooks/useCreateInvoice.ts
frontend/apps/web/src/features/invoices/hooks/useInvoice.ts

# Existing invoice components (to understand patterns + SendInvoicePreviewModal):
frontend/apps/web/src/features/invoices/components/InvoiceDetailPage.tsx
frontend/apps/web/src/features/invoices/components/SendInvoicePreviewModal.tsx
frontend/apps/web/src/features/invoices/components/InvoicesPage.tsx

# FE-B28 comboboxes to reuse:
frontend/apps/web/src/components/CustomerCombobox.tsx
frontend/apps/web/src/components/SiteCombobox.tsx

# Existing job hook (for customer_id/site_id pre-fill):
frontend/apps/web/src/features/jobs/hooks/useJob.ts

# MSW handler to extend:
frontend/apps/web/src/mocks/handlers/invoiceDetailHandlers.ts
frontend/apps/web/src/mocks/handlers/index.ts

# Route structure reference:
frontend/apps/web/src/app/(authed)/invoices/page.tsx
```

Also run:

```bash
# Confirm existing combobox paths
ls frontend/apps/web/src/components/
find frontend/apps/web/src/features/invoices -name "*.tsx" | head -15
find frontend/apps/web/src/__tests__ -type d | head -10
```

---

## MSW Handlers — New Billable Items Handler

Add to `invoiceDetailHandlers.ts` (in the `invoiceDetailHandlers` array):

```typescript
// GET /api/v1/jobs/:job_id/billable-items — B20 endpoint
http.get("/api/v1/jobs/:job_id/billable-items", ({ params }) => {
  const { job_id } = params as { job_id: string };
  return HttpResponse.json({
    job_id,
    job_number: "JOB-000001",
    customer_name: "Acme Electric",
    time_entries: [
      {
        id: "te-00000001-0000-0000-0000-000000000001",
        user_id: "u-00000001-0000-0000-0000-000000000001",
        tech_name: "Jake Rodriguez",
        started_at: "2026-07-01T08:00:00Z",
        ended_at: "2026-07-01T12:00:00Z",
        hours: "4.00",
        hourly_rate_cents: 8500,
        total_cost_cents: 34000,
        notes: "Panel upgrade labor",
        is_already_invoiced: false,
      },
    ],
    expenses: [
      {
        id: "exp-00000001-0000-0000-0000-000000000001",
        description: "Wire 12AWG 50ft",
        cost_cents: 4800,
        billable_cents: 5280,
        is_billable: true,
        is_already_invoiced: false,
        incurred_at: "2026-07-01T09:30:00Z",
      },
    ],
  });
}),
```

> **Check first**: Open `invoiceDetailHandlers.ts` and confirm there is no existing `/api/v1/jobs/:job_id/billable-items` handler. Also check `jobs.ts` MSW file — it has a duplicate `POST /api/v1/invoices/` handler registered separately. Do NOT add a conflicting GET billable-items handler in `jobs.ts`.

---

## Context: What This Batch Does

FE-B29 builds the **full-page invoice builder** at `/invoices/new`. This replaces the `InvoiceCreateModal` as the primary creation path.

| Step | What Changes |
|---|---|
| New hook `useBillableItems` | Fetches `GET /api/v1/jobs/{job_id}/billable-items` for pre-filling line items |
| Extend `useCreateInvoice` | Add B20 payload fields: `payment_terms`, `billing_mode`, `progress_pct`, `internal_memo`, `customer_id`, `site_id` |
| New `InvoiceBuilderPage.tsx` | 5-section full-page builder per UI-DS-B1 §Surface 1 |
| New route `invoices/new/page.tsx` | Thin server component wrapper |
| Modify `InvoicesPage.tsx` | "+ Create Invoice" navigates to `/invoices/new` instead of opening modal |
| Extend MSW handlers | Add billable-items GET handler |
| 4 integration test files | Minimum 16 tests |

---

## STEP 1 — Create `useBillableItems` Hook

**File**: `frontend/apps/web/src/features/invoices/hooks/useBillableItems.ts`

**Read first**: `useCreateInvoice.ts` and `useInvoice.ts` to understand the hook pattern used in this feature folder.

Create a new TanStack Query hook:

```typescript
// Adjust field names to match what pnpm sync-api-types delivers from openapi.json
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface BillableTimeEntry {
  id: string;
  user_id: string;
  tech_name: string | null;
  started_at: string;
  ended_at: string | null;
  hours: string | null;
  hourly_rate_cents: number;
  total_cost_cents: number;
  notes: string | null;
  is_already_invoiced: boolean;
}

export interface BillableExpense {
  id: string;
  description: string;
  cost_cents: number;
  billable_cents: number;
  is_billable: boolean;
  is_already_invoiced: boolean;
  incurred_at: string;
}

export interface BillableItemsResponse {
  job_id: string;
  job_number: string | null;
  customer_name: string | null;
  time_entries: BillableTimeEntry[];
  expenses: BillableExpense[];
}

export const BILLABLE_ITEMS_QUERY_KEY = (jobId: string) =>
  ["billable-items", jobId] as const;

export function useBillableItems(jobId: string | null | undefined) {
  return useQuery({
    queryKey: BILLABLE_ITEMS_QUERY_KEY(jobId ?? ""),
    queryFn: async (): Promise<BillableItemsResponse> => {
      const res = await apiClient.get(
        `/api/v1/jobs/${jobId}/billable-items`,
      );
      return res.data as BillableItemsResponse;
    },
    enabled: !!jobId,
    staleTime: 60_000,
  });
}
```

> **Verify field names**: After running `pnpm sync-api-types`, check if `BillableTimeEntry` and `BillableExpense` are now in `packages/shared-types/src/api-schema.d.ts`. Use the generated types if available — remove the inline interfaces and import from `@pilot/shared-types` instead.

---

## STEP 2 — Extend `useCreateInvoice` with B20 Fields

**File**: `frontend/apps/web/src/features/invoices/hooks/useCreateInvoice.ts`

**Read first**: The existing file — understand `InvoiceCreatePayload` exactly before modifying.

Extend `InvoiceCreatePayload` with B20 fields. The existing payload only has: `quote_id`, `job_id`, `customer_notes`, `terms_and_conditions`, `due_at`, `issued_at`, `idempotency_key`.

**Add to `InvoiceCreatePayload`:**

```typescript
// Additions — verify these exact names in InvoiceCreate from openapi.json
customer_id?: string | null;
site_id?: string | null;
payment_terms?: string | null;     // 'due_on_receipt' | 'net_15' | 'net_30' | 'custom_date'
billing_mode?: string;             // 'line_item' | 'progress'
progress_pct?: number | null;      // 0–100 when billing_mode='progress'
internal_memo?: string | null;
```

The `mutationFn` already passes the full payload to `apiClient.post("/api/v1/invoices/", payload)` — no change to the mutation logic needed, only the interface.

**After this step**, run targeted tests to confirm no regressions:

```bash
cd <repo>/frontend
npx vitest run apps/web/src/features/invoices 2>&1 | tail -10
```

---

## STEP 3 — Create `InvoiceBuilderPage.tsx`

**File**: `frontend/apps/web/src/features/invoices/components/InvoiceBuilderPage.tsx`

**Read first**: `QuoteCreatePage.tsx` for the shell pattern; `CustomerCombobox.tsx` and `SiteCombobox.tsx` for the combobox API; `SendInvoicePreviewModal.tsx` to understand the always-preview-before-send pattern.

This is the main work of the batch. Implement per **UI-DS-B1 §Surface 1** exactly. Do not deviate from the approved spec — if something is unclear, implement the spec as written and add a `// NOTE:` comment.

### Page-level interface

```typescript
interface InvoiceBuilderPageProps {
  jobId?: string | null;   // From URL ?job_id= param (passed by route page.tsx)
}
```

### Section 1: Header Panel

- `<CustomerCombobox>` + `<SiteCombobox>` (cascading)
- When `jobId` is set: run `useJob(jobId)` and `useBillableItems(jobId)` in parallel
- Pre-fill `customerId` + `siteId` from `job.customer_id` / `job.site_id` once `useJob` resolves
- Show linked job amber pill badge when `jobId` present: `"Linked Job: {job.job_number}"` with `[×]` dismiss button
- Amber pill classes: `inline-flex items-center gap-1.5 bg-alert-50 border border-alert-200 text-alert-700 text-caption font-medium rounded-full px-2.5 py-1 mt-3`
- Dismissing via `[×]`: clear `jobId` from local state (not URL), reset line items to empty state
- 2-col layout for Customer + Site on `md+`: `grid grid-cols-1 md:grid-cols-2 gap-4`

### Section 2: Billing Mode Toggle

- 2-option pill switcher: "Select line items" | "Progress billing (%)"
- Outer: `bg-neutral-100 rounded-md p-1 inline-flex`
- Active pill: `bg-white shadow-sm rounded px-3 py-1 text-sm font-medium text-neutral-900`
- Inactive: `px-3 py-1 text-sm font-medium text-neutral-500 hover:text-neutral-700`
- Toggle updates `billingMode` state (`'line_item' | 'progress'`)

### Section 3: Line Items Panel

**When `billingMode === 'line_item'`:**

- **Empty state** (no jobId or job loading): `"Link a job above to pre-fill billable items, or add custom line items manually"` — `text-neutral-500 text-sm text-center py-8`
- **Loading** (`useBillableItems` in-flight): 3 pulse skeleton rows — `animate-pulse bg-neutral-100 rounded h-8`
- **Error**: `<ErrorState type="server" title="..." description="..." onRetry={...} />` from `@pilot/ui/states`
- **Populated**: Checklist rows per spec; all items default to checked (`selectedItemIds` starts with all IDs)
  - Checked row: `text-sm text-neutral-800`, amount `text-sm font-medium text-neutral-900`
  - Unchecked row: `text-sm text-neutral-400 line-through`, amount `text-sm text-neutral-400`
  - Checkbox: `w-4 h-4 rounded border-neutral-300 text-brand-600 focus:ring-brand-500`
- **"+ Add custom line item"**: inline expand row at bottom — description `<input>` + amount `<input>` + "Add" button

**When `billingMode === 'progress'`:**

- Large centered `%` input: `text-3xl font-semibold text-neutral-900 w-24 text-center border-b-2 border-brand-500 focus:outline-none bg-transparent`
- Below input: `"= ${formatCents(computedAmountCents)}"` in `text-neutral-500 text-sm mt-1`
- The `computedAmountCents` is the total of all checked items × progressPct/100

### Section 4: Payment Terms Panel

- Dropdown: `due_on_receipt` | `net_15` | `net_30` | `custom_date`
- Due date label next to dropdown: computed from selected terms — e.g., "Due: Aug 11, 2026" in `text-sm text-neutral-500 ml-3`
- When `custom_date` selected: date picker `<input type="date">` appears below dropdown: `mt-2 border border-neutral-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-brand-400 w-44`

**Due date computation (client-side for display):**

```typescript
const PAYMENT_TERMS_DAYS: Record<string, number> = {
  due_on_receipt: 0,
  net_15: 15,
  net_30: 30,
};

function computeDueDate(terms: string, issuedAt: Date = new Date()): string | null {
  if (terms === "custom_date") return null; // User picks via date picker
  const days = PAYMENT_TERMS_DAYS[terms];
  if (days === undefined) return null;
  const due = new Date(issuedAt);
  due.setDate(due.getDate() + days);
  return due.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}
```

### Section 5: Notes Panel

- Customer-facing note textarea (shown on PDF): `placeholder="Add a note for the customer (shown on invoice PDF)…"`
- Divider: `border-t border-neutral-100 my-4`
- Internal memo textarea (NOT on PDF): `placeholder="Add internal memo (not visible to customer)…"`
- Sub-labels: `text-xs text-neutral-400 mt-0.5 mb-1` — "(shown on invoice PDF)" / "(not shown on PDF)"
- Textarea classes: `w-full rounded border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 resize-y min-h-[80px] focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 placeholder:text-neutral-400`

### Top action row (breadcrumb + buttons)

```
Invoices / New Invoice        [Cancel] [Save as Draft] [Send Invoice →]
```

- Breadcrumb: `text-sm text-neutral-500` — `<Link href="/invoices">Invoices</Link>` + `/ New Invoice`
- Cancel: `router.back()`
- Save as Draft: calls `handleSave("draft")` → POST → navigate to `/invoices/{id}`
- Send Invoice: calls `handleSave("draft")` → POST success → open `<SendInvoicePreviewModal>`

### Action Footer (bottom of page)

```
[Preview Invoice]    [Save as Draft]    [Send Invoice →]
```

- Preview Invoice: **disabled** in FE-B29 — `disabled title="Invoice preview coming soon"` with `disabled:opacity-50 disabled:cursor-not-allowed`
- Save as Draft: same as top row
- Send Invoice: same as top row

### Validation before save

Client-side block (do NOT call API) when:
1. `customerId` is null (no customer selected)
2. `siteId` is null (no site selected)
3. `billingMode === 'progress'` AND (`progressPct <= 0` or `progressPct > 100` or not a number)
4. `paymentTerms === 'custom_date'` AND `customDueDate` is empty

Show inline error message above action footer: `text-sm text-alert-700 bg-alert-50 border border-alert-200 rounded px-3 py-2`

### POST payload construction

```typescript
// Read the InvoiceCreate schema from openapi.json first — verify exact field names
const payload = {
  customer_id: customerId,
  site_id: siteId,
  job_id: jobId ?? null,
  payment_terms: paymentTerms,
  billing_mode: billingMode,
  progress_pct: billingMode === 'progress' ? Number(progressPct) : null,
  internal_memo: internalMemo || null,
  customer_notes: customerNotes || null,
  issued_at: new Date().toISOString(),
  due_at: paymentTerms === 'custom_date' ? customDueDate : null,
  idempotency_key: `inv-create-${customerId}-${Date.now()}`,
  // line_items: IF InvoiceCreate accepts this — check openapi.json first
};
```

**`useCreateInvoice` wiring:**

```typescript
const { mutate: createInvoice, isPending: isSaving } = useCreateInvoice({
  onTaxSetupRequired: (detail) => {
    setTaxSetupDetail(detail);
    setTaxSetupOpen(true);
  },
  onSuccess: (invoice) => {
    if (pendingAction === "send") {
      // Open SendInvoicePreviewModal with new invoice
      setCreatedInvoiceId(invoice.id);
      setSendModalOpen(true);
    } else {
      router.push(`/invoices/${invoice.id}`);
    }
  },
});
```

Keep `<TaxSetupSubFlowModal>` wiring — the 412 flow already exists in `useCreateInvoice` and must be preserved.

---

## STEP 4 — Create Route: `invoices/new/page.tsx`

**File**: `frontend/apps/web/src/app/(authed)/invoices/new/page.tsx`

This is a **thin server component** — no `"use client"`, no logic.

```typescript
import { InvoiceBuilderPage } from "@/features/invoices/components/InvoiceBuilderPage";

interface PageProps {
  searchParams: { job_id?: string };
}

export default function InvoicesNewPage({ searchParams }: PageProps) {
  return <InvoiceBuilderPage jobId={searchParams.job_id ?? null} />;
}
```

> Read `frontend/apps/web/src/app/(authed)/invoices/page.tsx` first to confirm the import alias pattern (`@/features/...`).

---

## STEP 5 — Modify `InvoicesPage.tsx`

**File**: `frontend/apps/web/src/features/invoices/components/InvoicesPage.tsx`

**Read first**: The existing file in full.

Change the "+ Create Invoice" button from opening `InvoiceCreateModal` to navigating:

```typescript
// ADD at the top of InvoicesPage (if not already present):
import { useRouter } from "next/navigation";

// Inside the component:
const router = useRouter();

// Change the button handler:
// OLD: onClick={() => setCreateModalOpen(true)}
// NEW: onClick={() => router.push("/invoices/new")}
```

**Do NOT remove** the `InvoiceCreateModal` import or the `<InvoiceCreateModal>` JSX — only change the button handler. This avoids breaking any tests that reference the modal import.

> **Alternative**: If removing the modal JSX doesn't break tests, you may clean it up. Run targeted tests first to verify.

---

## STEP 6 — Extend MSW Handler

**File**: `frontend/apps/web/src/mocks/handlers/invoiceDetailHandlers.ts`

Add the billable-items handler as specified in the MSW Handlers section above. Place it within the `invoiceDetailHandlers` array.

> **Check for conflicts**: Search `jobs.ts` MSW file — confirm it has no `GET /api/v1/jobs/:job_id/billable-items` handler. If it does, do NOT add a duplicate.

No changes to `mocks/handlers/index.ts` needed — `invoiceDetailHandlers` is already registered.

---

## STEP 7 — Integration Tests

**Folder**: `frontend/apps/web/src/__tests__/batch_fe_b29/`

Create 4 test files. Minimum 16 tests total (4 per file). Use `setupServer` from `msw/node`, `retry: false` on QueryClient, and `vi.mock("next/navigation", ...)` in all files.

### File 1: `invoice_builder_render.integration.test.tsx`

```typescript
// Tests:
// 1. Page renders without crashing — "New Invoice" heading visible
// 2. Section cards visible: Customer, Billing Mode, Line Items, Payment Terms, Notes
// 3. RoleGate: tech role should NOT see the invoice builder (invoices.create permission)
// 4. Cancel button triggers router.back()
```

### File 2: `invoice_builder_job_prefill.integration.test.tsx`

```typescript
// Tests:
// 1. When jobId prop passed, useBillableItems is called and line items render
// 2. Linked job amber badge shows "JOB-000001"
// 3. Line item rows show tech entry ("Jake Rodriguez") and expense ("Wire 12AWG 50ft")
// 4. Dismissing [×] on amber badge hides the linked job badge and clears line items
```

Mock handlers for this test:
- `GET /api/v1/jobs/:job_id/billable-items` → fixture from `invoiceDetailHandlers.ts`
- `GET /api/v1/jobs/:job_id` → existing job fixture (use from `jobs.ts` handlers or define inline)

### File 3: `invoice_builder_billing_toggle.integration.test.tsx`

```typescript
// Tests:
// 1. Default mode is "Select line items" — checklist section visible
// 2. Clicking "Progress billing (%)" toggle — % input appears, checklist hides
// 3. In progress mode, typed % updates the computed amount display
// 4. Switching back to "Select line items" — checklist re-appears
```

### File 4: `invoice_builder_save.integration.test.tsx`

```typescript
// Tests:
// 1. Save as Draft fires POST /api/v1/invoices/ with billing_mode='line_item'
// 2. POST payload includes customer_id, site_id, payment_terms, internal_memo
// 3. On POST success, router.push fires with /invoices/{id}
// 4. On POST 412, TaxSetupSubFlowModal appears
```

**QueryClient wrapper pattern:**

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

**Navigation mock (required in all 4 files):**

```typescript
const mockPush = vi.fn();
const mockBack = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, back: mockBack }),
  usePathname: () => "/invoices/new",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: any) =>
    React.createElement("a", { href, ...rest }, children),
}));
beforeEach(() => { mockPush.mockClear(); mockBack.mockClear(); });
```

**RBAC test pattern (for test 3 in File 1):**

```typescript
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue, PilotRole } from "@pilot/ui/auth";
// Use makeAuthValue() + renderAs() pattern from inclusions file §9
```

---

## Final Verification

### Phase 1 — Targeted tests (run after each step)

```bash
cd <repo>/frontend

# After STEP 1 (useBillableItems):
npx vitest run apps/web/src/features/invoices/hooks 2>&1 | tail -8

# After STEP 3 (InvoiceBuilderPage + tests):
npx vitest run apps/web/src/__tests__/batch_fe_b29 2>&1 | tail -10

# Full web suite:
pnpm --filter web test 2>&1 | tail -6
```

Fix any failure before moving to the next step.

### Phase 2 — Full verification (run once at the very end)

```bash
cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter mobile build && pnpm --filter @pilot/ui lint && pnpm --filter web lint && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== FE-B29 FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — FE-B29

Update `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 — FE-B29 row when done:

- [ ] Pre-modification regression baseline captured (zero pre-existing failures)
- [ ] `pnpm sync-api-types` run — B20 fields visible in generated types
- [ ] Design doc fully read (batch-fe-b29-design.md all sections A–J)
- [ ] UI-DS-B1 §Surface 1 spec fully read before writing any JSX
- [ ] All mandatory source files read before modifying
- [ ] `GET /api/v1/jobs/{job_id}/billable-items` confirmed in `openapi_schema_map.md`
- [ ] `InvoiceCreate` schema verified in `openapi.json` — all B20 field names confirmed
- [ ] **STEP 1**: `useBillableItems.ts` created — enabled when `jobId` set, `retry: false` in tests
- [ ] **STEP 2**: `useCreateInvoice.ts` extended — B20 fields + `customer_id`/`site_id` in `InvoiceCreatePayload`
- [ ] **STEP 3**: `InvoiceBuilderPage.tsx` created — all 5 sections per UI-DS-B1 §Surface 1
- [ ] **STEP 4**: `invoices/new/page.tsx` created — thin server component, no `"use client"`
- [ ] **STEP 5**: `InvoicesPage.tsx` modified — "+ Create Invoice" navigates to `/invoices/new`
- [ ] **STEP 6**: MSW billable-items handler added to `invoiceDetailHandlers.ts`
- [ ] `InvoicesPage.tsx` "+ Create Invoice" navigates to `/invoices/new` (not modal)
- [ ] Linked job amber badge displays when `?job_id=` present; `[×]` dismiss works
- [ ] Billing mode toggle switches between checklist and % input views
- [ ] Payment Terms dropdown + due date label compute and display correctly
- [ ] "Custom date" reveals date picker
- [ ] Save as Draft fires POST with all B20 fields in payload
- [ ] Post-save navigation to `/invoices/{id}` works
- [ ] 412 response opens `TaxSetupSubFlowModal`
- [ ] Preview Invoice button is disabled (deferred per design doc §G)
- [ ] All integration tests in `__tests__/batch_fe_b29/` pass (minimum 16 tests)
- [ ] No TypeScript errors (`pnpm --filter web check-types` passes)
- [ ] No ESLint errors (`pnpm --filter web lint` passes)
- [ ] No regressions in pre-existing web test suite
- [ ] **Phase 2 FULL verification command passes** (`=== FE-B29 FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter mobile build && pnpm --filter @pilot/ui lint && pnpm --filter web lint && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== FE-B29 FINAL VERIFICATION COMPLETE ==="
  ```

---

## Completion Summary

After all Definition of Done items are complete, you must do **both** of the following:

1. **Update the Phase 1 batch sequence table** in `dev-docs/analysis/pilot-launch-plan.md`:
   - Find the `| 7 | **FE-B29** |` row
   - Change `| ☐ |` to `| ✅ |`
   - Append `— **Completed YYYY-MM-DD**` to the end of the "What" cell

2. **Add a Completion Summary section** immediately after the `### B20 — Invoice Builder Backend: Completion Summary` section in the same file, using the format below.

```markdown
### FE-B29 — Full-Page Invoice Builder: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (web)
**Final**: X+N passed (+N new tests, Y test files)

#### What Was Accomplished

- Created `useBillableItems` hook — `GET /api/v1/jobs/{job_id}/billable-items`
- Extended `useCreateInvoice` `InvoiceCreatePayload` with B20 fields
- Created `InvoiceBuilderPage.tsx` — 5-section full-page builder per UI-DS-B1
- Created `/invoices/new/page.tsx` route (thin server component)
- Updated `InvoicesPage.tsx` — "+ Create Invoice" now navigates to `/invoices/new`
- Added billable-items MSW handler to `invoiceDetailHandlers.ts`

#### Files Changed / Created

| File | Action |
|---|---|
| `features/invoices/hooks/useBillableItems.ts` | Created |
| `features/invoices/hooks/useCreateInvoice.ts` | Updated — B20 fields + customer_id/site_id |
| `features/invoices/components/InvoiceBuilderPage.tsx` | Created |
| `app/(authed)/invoices/new/page.tsx` | Created |
| `features/invoices/components/InvoicesPage.tsx` | Updated — nav to /invoices/new |
| `mocks/handlers/invoiceDetailHandlers.ts` | Updated — billable-items GET handler |
| `__tests__/batch_fe_b29/invoice_builder_render.integration.test.tsx` | Created |
| `__tests__/batch_fe_b29/invoice_builder_job_prefill.integration.test.tsx` | Created |
| `__tests__/batch_fe_b29/invoice_builder_billing_toggle.integration.test.tsx` | Created |
| `__tests__/batch_fe_b29/invoice_builder_save.integration.test.tsx` | Created |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `batch_fe_b29/invoice_builder_render.integration.test.tsx` | Integration | 4 | ✅ |
| `batch_fe_b29/invoice_builder_job_prefill.integration.test.tsx` | Integration | 4 | ✅ |
| `batch_fe_b29/invoice_builder_billing_toggle.integration.test.tsx` | Integration | 4 | ✅ |
| `batch_fe_b29/invoice_builder_save.integration.test.tsx` | Integration | 4 | ✅ |
```
