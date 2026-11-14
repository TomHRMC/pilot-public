# Implementation Prompt: FE-B18 — Customer Create/Edit + Sites + Customer Detail

**Mode**: Pilot React Engineer  
**Batch**: FE-B18  
**Source plan**: `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` §Phase 0.9 — FE-B18  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-fe-b18-design.md`  
**Estimated session**: 4–6 hours  
**Platform**: Web only (`apps/web`)  
**Backend companion**: None — all endpoints exist. Prerequisite: B17 Part A complete + `pnpm sync-api-types` run.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-fe-b18-design.md`** — every section (A–I)

**Critical rules for this batch:**

- **Rule 1.1**: Before writing ANY hook or API call, verify the endpoint exists in `backend/openapi_schema_map.md`. If it is NOT there → **STOP and ask Tom**.
- **Rule 1.2**: Do NOT invent URL patterns or parameter names. Every shape comes from `openapi.json`.
- **Rule 1.3**: Run `pnpm sync-api-types` before starting — B17 Part A added `mobile_phone` to `CustomerResponse`. Without re-running sync, the TypeScript type is stale.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any component — `<LoadingState>`, `<ErrorState>`, `<EmptyState>`, `<RoleGate>` are all available.
- **Rule 8**: No new npm dependencies without checking `package.json` first. Modal/drawer components must be built with existing tools (Tailwind + `dialog` element or existing pattern from the codebase).
- **Rule 9**: Route files in `app/(authed)/` are thin server components — no `"use client"`, no data fetching. All logic in feature components.
- **Rule 10**: If ANY test fails — even pre-existing — you must fix it before declaring done.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G:

| Decision | Outcome | Rationale |
|---|---|---|
| Edit Customer UI pattern | Inline edit toggle on Overview tab (not a separate drawer) | Simpler; sufficient for MVP |
| Sites placement | New "Sites" tab in tab bar (between Overview and Jobs) | Sites list is meaningful enough for its own tab |
| Payment method vaulting | Deferred to FE-B22 | Requires Stripe Elements — out of scope for B18 |
| Customer layout header name | `CustomerDetailHeader` client component passed `customerId` | Server component layout passes `customerId`; client component fetches name |
| Jobs/Invoices tab fallback | `CustomerTabDeferredState` if `?customer_id=` filter not supported | Verify in pre-work; never 404 or error |

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend

# Web app
pnpm --filter web test 2>&1 | tail -5

# Shared UI (touching packages/ui patterns)
pnpm --filter @pilot/ui test 2>&1 | tail -5
```

Record the exact counts. Fix any pre-existing failures before starting — or confirm with Tom.

---

## Pre-Work: Sync API Types

**This is mandatory — B17 Part A added `mobile_phone` to `CustomerResponse`.**

```bash
cd <repo>/frontend
pnpm sync-api-types
```

If this fails: B17 Part A may not be complete. Stop and confirm with Tom.

---

## Pre-Work: Verify Endpoints

For each hook in this batch, verify the endpoint exists before writing any code:

```bash
# From project root:
grep -A 8 "GET /api/v1/customers" backend/openapi_schema_map.md | head -30
grep -A 5 "POST /api/v1/customers" backend/openapi_schema_map.md | head -15
grep -A 5 "PATCH /api/v1/customers" backend/openapi_schema_map.md | head -15
grep -A 5 "/api/v1/sites" backend/openapi_schema_map.md | head -20

# Check if jobs endpoint supports customer_id filter:
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
jobs_get = spec['paths'].get('/api/v1/jobs/', {}).get('get', {})
params = [p['name'] for p in jobs_get.get('parameters', [])]
print('Jobs GET params:', params)
"

# Check if invoices endpoint supports customer_id filter:
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
inv_get = spec['paths'].get('/api/v1/invoices/', {}).get('get', {})
params = [p['name'] for p in inv_get.get('parameters', [])]
print('Invoices GET params:', params)
"
```

**Decision based on pre-work results:**
- If `customer_id` IS in jobs params: build `CustomerJobsList` with real data
- If `customer_id` is NOT in jobs params: render `<CustomerTabDeferredState message="Full job details available in the Jobs module" />` — do not error
- Same logic for invoices

| Hook | Endpoint | Verified |
|---|---|---|
| `useCustomer` | `GET /api/v1/customers/{id}` | Confirm before coding |
| `useCreateCustomer` | `POST /api/v1/customers/` | Confirm before coding |
| `useUpdateCustomer` | `PATCH /api/v1/customers/{id}` | Confirm before coding |
| `useCustomerSites` | `GET /api/v1/sites/?customer_id={id}` | Confirm `?customer_id=` param |
| `useCreateSite` | `POST /api/v1/sites/` | Confirm before coding |
| `useUpdateSite` | `PATCH /api/v1/sites/{id}` | Confirm before coding |

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

```
frontend/apps/web/src/features/customers/components/CustomersPage.tsx
  ← understand current state before adding button + modal

frontend/apps/web/src/features/customers/hooks/useCustomers.ts
  ← understand existing hook signature before adding companion hooks

frontend/apps/web/src/app/(authed)/customers/[id]/layout.tsx
  ← understand layout structure before adding Sites tab + CustomerDetailHeader

frontend/apps/web/src/app/(authed)/customers/[id]/page.tsx
  ← see the "coming soon" placeholder to replace

frontend/apps/web/src/app/(authed)/customers/[id]/comms/page.tsx
  ← reference for how a working customer sub-page is structured

frontend/apps/web/src/mocks/handlers/index.ts
  ← understand current handler registrations before adding customerHandlers

frontend/packages/ui/src/index.ts
  ← confirm LoadingState, ErrorState, EmptyState, RoleGate import paths before use
```

Also run:
```bash
# Find any existing customer-related components or hooks
find frontend/apps/web/src/features/customers -type f | sort

# Check what permissions exist for customers
grep -n "customers" frontend/packages/ui/src/role-gate/permissions.ts | head -20

# Find if a modal/dialog pattern exists in the codebase
grep -rn "dialog\|Modal\|modal" frontend/packages/ui/src/index.ts | head -10
find frontend/apps/web/src/features -name "*Modal*" -o -name "*modal*" | head -10
```

---

## Context: What This Batch Does

| Step | Task | Result |
|---|---|---|
| 1 | MSW handlers for customer + site CRUD | Tests can work without real backend |
| 2–6 | New TanStack Query hooks | `useCustomer`, `useCreateCustomer`, `useUpdateCustomer`, `useCustomerSites`, `useCreateSite`, `useUpdateSite` |
| 7–9 | `CustomerForm` + `CreateCustomerModal` + wire to list page | "Add Customer" button on `/customers` works end-to-end |
| 10–12 | `CustomerOverviewTab` + layout header name | `/customers/[id]` shows real data, not "coming soon" |
| 13–14 | `SiteListPanel` + `SiteForm` + Sites tab | `/customers/[id]/sites` works |
| 15–20 | Quotes/Jobs/Invoices sub-lists (or deferred state) | All "coming soon" strings eliminated |
| 21–22 | Tests + verification | Zero failures, zero "coming soon" in JSX |

---

## Step 1 — Create MSW Handlers for Customer + Site CRUD

**File**: `apps/web/src/mocks/handlers/customerHandlers.ts` (new)

Read `mocks/handlers/index.ts` first to understand the barrel pattern.

Create handlers for all customer and site CRUD endpoints. Use realistic fixture data based on the seed data customers (Smith Electrical, Johnson Home Services, Martinez Properties LLC from `quotesListHandlers.ts`). The fixture IDs must be consistent across handlers so GET-after-create tests work.

Key handlers to include:
```typescript
import { http, HttpResponse } from "msw";

// GET /api/v1/customers/
// GET /api/v1/customers/:customerId
// POST /api/v1/customers/
// PATCH /api/v1/customers/:customerId
// DELETE /api/v1/customers/:customerId
// GET /api/v1/sites/?customer_id=:customerId
// POST /api/v1/sites/
// PATCH /api/v1/sites/:siteId
```

**Then register in `mocks/handlers/index.ts`:**
```typescript
import { customerHandlers } from "./customerHandlers";  // ADD

export const handlers = [
  // ... existing handlers ...
  ...customerHandlers,  // ADD — FE-B18
];
```

> **Test resilience**: Fixture data is read-only — never mutate the module-level fixture arrays. Mock POST/PATCH handlers should return the input merged with a generated ID, not mutate shared state.

**Intermediate check:**
```bash
pnpm --filter web test 2>&1 | tail -5
```

---

## Step 2–6 — Create Customer + Site Hooks

**Files**: `apps/web/src/features/customers/hooks/`

Read `useCustomers.ts` first. Follow the exact same pattern for all new hooks.

### `useCustomer.ts` (single customer fetch)

```typescript
// Query key: ['customer', customerId]
// Endpoint: GET /api/v1/customers/{customerId}
// enabled: !!customerId (don't fetch if undefined)
```

### `useCreateCustomer.ts` (POST mutation)

```typescript
// Endpoint: POST /api/v1/customers/
// onSuccess: invalidate ['customers'] queries
// Return type: CustomerResponse from @pilot/shared-types
```

### `useUpdateCustomer.ts` (PATCH mutation)

```typescript
// Endpoint: PATCH /api/v1/customers/{customerId}
// onSuccess: invalidate ['customer', customerId] AND ['customers']
```

### `useCustomerSites.ts` (site list for a customer)

```typescript
// Query key: ['customer-sites', customerId]
// Endpoint: GET /api/v1/sites/?customer_id={customerId}
// enabled: !!customerId
```

### `useCreateSite.ts` and `useUpdateSite.ts`

```typescript
// useCreateSite: POST /api/v1/sites/ — invalidates ['customer-sites', customerId]
// useUpdateSite: PATCH /api/v1/sites/{siteId} — invalidates ['customer-sites', customerId]
```

> **Field names come from `openapi.json`** — do not invent request body field names. Verify `SiteCreate` schema before coding: `customer_id`, `name`, `notes`, `jurisdiction_code`, `address` (nested optional).

**Intermediate check:**
```bash
pnpm --filter web test 2>&1 | tail -5
```

---

## Step 7–9 — CustomerForm + CreateCustomerModal + Wire to List Page

### `CustomerForm.tsx` — shared form component

**File**: `apps/web/src/features/customers/components/CustomerForm.tsx`

This component is used for both create and edit. Props:

```typescript
interface CustomerFormProps {
  initialValues?: Partial<CustomerFormValues>;
  onSubmit: (values: CustomerFormValues) => void;
  onCancel: () => void;
  isSubmitting: boolean;
  submitLabel?: string; // defaults to "Save"
}
```

Fields:
- **Type**: radio or select — "Person" / "Company" (maps to `type: 'person' | 'company'`)
- **When Person**: First Name, Last Name (both optional), Display Name (required)
- **When Company**: Company Name (optional), Display Name (required)
- Email (optional)
- Mobile Phone (optional)
- Notes (optional textarea)

> Display Name is always required regardless of type — it's the primary identifier in the app.

All inputs must use `className` from Tailwind design tokens (no hardcoded hex colors). Read `CustomersPage.tsx` for the existing input className pattern to stay consistent.

### `CreateCustomerModal.tsx`

**File**: `apps/web/src/features/customers/components/CreateCustomerModal.tsx`

Look for an existing modal/dialog pattern in the codebase before creating one. Run:
```bash
find frontend/apps/web/src/features -name "*Modal*" | head -10
grep -rn "dialog\|role=\"dialog\"" frontend/apps/web/src/ --include="*.tsx" -l | head -5
```

If a modal pattern exists, follow it. If not, use a `<dialog>` element with `open` attribute and `onClose` callback, or a simple absolute-positioned overlay — keep it minimal.

```typescript
interface CreateCustomerModalProps {
  open: boolean;
  onClose: () => void;
}

export function CreateCustomerModal({ open, onClose }: CreateCustomerModalProps) {
  const { mutate, isPending } = useCreateCustomer();
  // ... form submission logic
  // On success: close modal + TanStack Query invalidation happens in hook
}
```

### Modify `CustomersPage.tsx`

Read the file first. Add:
1. State: `const [showCreate, setShowCreate] = useState(false)`
2. "Add Customer" button wrapped in `<RoleGate permission="customers.create">`:
   ```tsx
   <RoleGate permission="customers.create">
     <button onClick={() => setShowCreate(true)} className="...">
       + Add Customer
     </button>
   </RoleGate>
   ```
3. `<CreateCustomerModal open={showCreate} onClose={() => setShowCreate(false)} />`

Also check: if B17 Part A added `?search=` to `GET /api/v1/customers/` (verify in `openapi_schema_map.md`), update `useCustomers` to accept a `search` param and remove the client-side `useMemo` filter from `CustomersPage`.

**Intermediate check:**
```bash
pnpm --filter web test -- --testPathPattern="CustomersPage|CreateCustomer" 2>&1 | tail -8
```

---

## Step 10–12 — CustomerOverviewTab + Layout Header Name

### `CustomerDetailHeader.tsx` (client component)

**File**: `apps/web/src/features/customers/components/CustomerDetailHeader.tsx`

This is a `"use client"` component that takes `customerId` and renders the customer name in the layout header:

```typescript
"use client";
export function CustomerDetailHeader({ customerId }: { customerId: string }) {
  const { data: customer, isLoading } = useCustomer(customerId);
  if (isLoading) return <span className="text-neutral-400">Loading...</span>;
  return <span>{customer?.display_name ?? 'Customer'}</span>;
}
```

### Modify `customers/[id]/layout.tsx`

Read the file first. Changes:
1. Add "Sites" tab to `TABS` array (between Overview and Jobs):
   ```typescript
   { label: "Sites", href: "/sites" }
   ```
2. Replace hardcoded `<h1>Customer</h1>` with `<CustomerDetailHeader customerId={id} />`

> The layout is a server component — import `CustomerDetailHeader` as a client component and pass `id` from params.

### `CustomerOverviewTab.tsx`

**File**: `apps/web/src/features/customers/components/CustomerOverviewTab.tsx`

```typescript
"use client";
interface CustomerOverviewTabProps {
  customerId: string;
}
```

View mode shows all `CustomerResponse` fields:
- Type badge (Person / Company)
- Display Name, First/Last or Company Name
- Email (with mailto link if present)
- Mobile Phone
- Preferred Contact Channel badge
- SMS Consent status badge (opted in / opted out; show opt-out date if opted out)
- Notes

Edit mode (toggled by "Edit" button behind `<RoleGate permission="customers.edit">`):
- Renders `<CustomerForm>` pre-filled with `customer` data
- On submit: calls `useUpdateCustomer`; on success: back to view mode

Use `<LoadingState>`, `<ErrorState>` from `@pilot/ui/states` for loading/error states.

### Modify `customers/[id]/page.tsx`

Read the current file (it renders `"coming soon"`). Replace with:
```typescript
import { CustomerOverviewTab } from "@/features/customers/components/CustomerOverviewTab";

export default async function CustomerOverviewPage({ params }: ...) {
  const { id } = await params;
  return <CustomerOverviewTab customerId={id} />;
}
```

**Intermediate check:**
```bash
pnpm --filter web test -- --testPathPattern="CustomerOverview|CustomerDetail" 2>&1 | tail -8
```

---

## Step 13–14 — SiteListPanel + SiteForm + Sites Tab

### `SiteForm.tsx`

**File**: `apps/web/src/features/customers/components/SiteForm.tsx`

Fields (all optional except `name`):
- Name (required)
- Notes
- Gate Code (`gate_code`)
- Access Instructions (`access_instructions`)
- Hazard Notes (`hazard_notes`)
- Address sub-section (optional): Line 1, Line 2, City, State, Postal Code, Country

> The `SiteCreate` schema has a nested `address` field. Verify the exact field names in `openapi.json` before coding the address sub-section.

### `SiteListPanel.tsx`

**File**: `apps/web/src/features/customers/components/SiteListPanel.tsx`

```typescript
"use client";
interface SiteListPanelProps {
  customerId: string;
}
```

Shows:
- List of sites with name, address (if present), gate code, access instructions snippet
- "Add Site" button (behind `<RoleGate permission="sites.create">`)
- "Edit" button per site (behind `<RoleGate permission="sites.edit">`)
- Add/Edit opens `<SiteForm>` in a modal

Use `<EmptyState>` for empty list.

### New `customers/[id]/sites/page.tsx`

**File**: `apps/web/src/app/(authed)/customers/[id]/sites/page.tsx` (new)

```typescript
import { SiteListPanel } from "@/features/customers/components/SiteListPanel";

export default async function CustomerSitesPage({ params }) {
  const { id } = await params;
  return <div className="p-6"><SiteListPanel customerId={id} /></div>;
}
```

**Intermediate check:**
```bash
pnpm --filter web test -- --testPathPattern="SiteList|SiteForm|CustomerSites" 2>&1 | tail -8
```

---

## Step 15–20 — Quotes / Jobs / Invoices Sub-Lists

### `CustomerTabDeferredState.tsx`

**File**: `apps/web/src/features/customers/components/CustomerTabDeferredState.tsx`

Reusable placeholder for tabs not yet fully implemented:
```typescript
export function CustomerTabDeferredState({ message, batchLabel }: {
  message: string;
  batchLabel?: string;
}) {
  return (
    <div className="p-6 text-center text-neutral-500">
      <p>{message}</p>
      {batchLabel && <p className="mt-1 text-xs text-neutral-400">Coming in {batchLabel}</p>}
    </div>
  );
}
```

### `CustomerQuotesList.tsx` (Steps 15–16)

Build this unless `GET /api/v1/quotes/?customer_id=` is not supported (check pre-work). If not supported, use `<CustomerTabDeferredState>`.

If supported:
- Call existing `useQuotes` with `{ customer_id: customerId }` (add this param to the hook if not present)
- Simple table: Quote ID, Status badge, Total, Created date
- Each row links to `/quotes/[id]`

### `CustomerJobsList.tsx` (Steps 17–18)

Build if `GET /api/v1/jobs/?customer_id=` is supported. Otherwise deferred state.

If supported:
- Simple table: Status, Scheduled date, Site
- Each row links to `/jobs/[id]` (will be a 404 until FE-B21 builds the jobs module — that's acceptable; use an anchor that will work once built)

### `CustomerInvoicesList.tsx` (Steps 19–20)

Build if `GET /api/v1/invoices/?customer_id=` is supported. Otherwise deferred state.

If supported:
- Simple table: Invoice #, Status badge, Due date, Balance
- Each row links to `/invoices/[id]` (will be 404 until FE-B22)

Wire each to the corresponding `page.tsx` (replace "coming soon" strings).

---

## Test Requirements

### Platform: Web (`apps/web`)

- `"use client"` on feature components only — route files stay thin server components
- `vi.mock()` not `jest.mock()` — this is Vitest
- `toBeInTheDocument()` for assertions (not `.toBeTruthy()`)
- Mock `next/navigation` where needed:
  ```typescript
  vi.mock("next/navigation", () => ({
    usePathname: () => "/customers/customer-001",
    useRouter: () => ({ push: vi.fn() }),
  }));
  ```

### TanStack Query Setup (every test)

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

### MSW in Tests

```typescript
import { setupServer } from "msw/node";
import { customerHandlers } from "@/mocks/handlers/customerHandlers";

const server = setupServer(...customerHandlers);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

### Test Resilience Rules (per `react-engineer-rules.md` Rule 15)

- Never mutate shared fixture objects — copy before modifying
- Never assert on `toHaveLength(N)` — assert by specific content/ID
- Per-test `server.use(...)` overrides must be paired with `server.resetHandlers()` in `afterEach`

### Unit Tests to Write

**`features/customers/components/__tests__/CustomerForm.test.tsx`:**
- Renders without crashing
- Shows person fields (first/last name) when type = "person"
- Shows company fields when type = "company"
- Submit calls onSubmit with correct data shape
- Cancel calls onCancel

**`features/customers/components/__tests__/CreateCustomerModal.test.tsx`:**
- When `open=false`, modal not visible
- When `open=true`, modal visible with form
- Submit calls `useCreateCustomer` with correct payload

**`features/customers/components/__tests__/CustomerOverviewTab.test.tsx`:**
- Renders LoadingState while fetching
- Renders ErrorState on API failure
- Shows customer name and email from mock data
- Edit button visible for owner; hidden for technician

**`features/customers/components/__tests__/SiteListPanel.test.tsx`:**
- Renders EmptyState when no sites
- Renders site cards with name and address from mock data
- "Add Site" button visible for owner; hidden for tech

### Integration Tests

**`apps/web/src/__tests__/batch_fe_b18/customerList.integration.test.tsx`:**
1. `/customers` renders customer list with data from MSW
2. "Add Customer" button visible for owner; hidden for tech
3. Clicking "Add Customer" opens modal
4. Submitting form adds customer to list (optimistic + confirmed)

**`apps/web/src/__tests__/batch_fe_b18/customerDetail.integration.test.tsx`:**
1. `/customers/[id]` no longer renders "coming soon"
2. Shows customer name in header
3. Sites tab navigates to sites list
4. Edit toggles form into view

---

## Final Verification

### Phase 1 — Targeted (run after each step group)

```bash
cd <repo>/frontend

# After hooks are done:
pnpm --filter web test -- --testPathPattern="useCustomer|useSite" 2>&1 | tail -6

# After components:
pnpm --filter web test -- --testPathPattern="CustomerForm|CustomerOverview|SiteList" 2>&1 | tail -8

# After integration tests:
pnpm --filter web test -- --testPathPattern="batch_fe_b18" 2>&1 | tail -8
```

### Phase 2 — Full Verification (once at the end)

```bash
cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter @pilot/ui lint && pnpm --filter web lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && echo "=== FE-B18 FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — FE-B18

Update `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` §Phase 0.9 milestone checklist:

- [ ] Pre-modification regression baseline captured for `@pilot/ui` and `web` (zero failures or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — `mobile_phone` field available in `CustomerResponse` TypeScript type
- [ ] Design doc read in full (all sections A–I)
- [ ] All mandatory source files read before modifying (`CustomersPage.tsx`, `useCustomers.ts`, `[id]/layout.tsx`, `[id]/page.tsx`, `mocks/handlers/index.ts`, `packages/ui/src/index.ts`)
- [ ] All endpoints verified in `openapi_schema_map.md` — jobs and invoices `?customer_id=` pre-work complete
- [ ] **Step 1**: `customerHandlers.ts` created; registered in `mocks/handlers/index.ts`
- [ ] **Steps 2–6**: `useCustomer`, `useCreateCustomer`, `useUpdateCustomer`, `useCustomerSites`, `useCreateSite`, `useUpdateSite` hooks created
- [ ] **Steps 7–9**: `CustomerForm`, `CreateCustomerModal` created; "Add Customer" button wired to `/customers` page; `<RoleGate>` wrapping correct
- [ ] **Steps 10–12**: `CustomerDetailHeader` created; `[id]/layout.tsx` updated with Sites tab + customer name; `[id]/page.tsx` shows `CustomerOverviewTab` (not "coming soon")
- [ ] **Steps 13–14**: `SiteListPanel`, `SiteForm` created; `[id]/sites/page.tsx` created; Sites tab functional
- [ ] **Steps 15–20**: All four "coming soon" strings eliminated from customer sub-pages (`/quotes`, `/jobs`, `/invoices`); either real lists or `CustomerTabDeferredState`
- [ ] Zero literal "coming soon" strings visible to users in any customer route (grep confirms):
  ```bash
  grep -rn "coming soon" frontend/apps/web/src/app/\(authed\)/customers/ --include="*.tsx"
  ```
- [ ] `CustomerForm` unit tests pass (person/company type conditional fields)
- [ ] `CustomerOverviewTab` unit tests pass (RBAC edit button visibility)
- [ ] `SiteListPanel` unit tests pass (empty state, site cards)
- [ ] Integration tests in `__tests__/batch_fe_b18/` pass
- [ ] All new MSW handlers registered in `mocks/handlers/index.ts` barrel
- [ ] No fixture objects mutated in tests — all test overrides use copies or `server.use(...)` + `resetHandlers()`
- [ ] Zero TypeScript errors (`pnpm --filter web check-types`)
- [ ] Zero ESLint `no-hardcoded-design-values` warnings
- [ ] **Phase 2 FULL verification command passes** (`=== FE-B18 FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter @pilot/ui lint && pnpm --filter web lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && echo "=== FE-B18 FINAL VERIFICATION COMPLETE ==="
  ```
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to impl plan §Phase 0.9

---

## Completion Summary

After all Definition of Done items are complete, add a **Completion Summary** to `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` under Phase 0.9 — FE-B18:

```markdown
### FE-B18 — Customer Create/Edit + Sites + Customer Detail: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (ui) | X passed (web)
**Final**: X+N passed (ui) | X+N passed (web) (+N new tests)

#### What Was Accomplished

- Added "Add Customer" button + CreateCustomerModal to /customers list page
- Built CustomerOverviewTab — eliminated "coming soon" from /customers/[id]
- Built SiteListPanel + SiteForm — /customers/[id]/sites now functional
- Built CustomerQuotesList — /customers/[id]/quotes shows quotes (or deferred state)
- Built CustomerJobsList — /customers/[id]/jobs [result]
- Built CustomerInvoicesList — /customers/[id]/invoices [result]
- Customer name now shows in detail page header
- Sites tab added to customer detail tab bar

#### Files Changed / Created

| File | Action |
|---|---|
| `apps/web/src/mocks/handlers/customerHandlers.ts` | Created — MSW handlers for customer + site CRUD |
| `apps/web/src/mocks/handlers/index.ts` | Updated — registered customerHandlers |
| `apps/web/src/features/customers/hooks/useCustomer.ts` | Created |
| `apps/web/src/features/customers/hooks/useCreateCustomer.ts` | Created |
| `apps/web/src/features/customers/hooks/useUpdateCustomer.ts` | Created |
| `apps/web/src/features/customers/hooks/useCustomerSites.ts` | Created |
| `apps/web/src/features/customers/hooks/useCreateSite.ts` | Created |
| `apps/web/src/features/customers/hooks/useUpdateSite.ts` | Created |
| `apps/web/src/features/customers/components/CustomerForm.tsx` | Created |
| `apps/web/src/features/customers/components/CreateCustomerModal.tsx` | Created |
| `apps/web/src/features/customers/components/CustomersPage.tsx` | Updated — Add Customer button |
| `apps/web/src/features/customers/components/CustomerDetailHeader.tsx` | Created |
| `apps/web/src/features/customers/components/CustomerOverviewTab.tsx` | Created |
| `apps/web/src/features/customers/components/SiteListPanel.tsx` | Created |
| `apps/web/src/features/customers/components/SiteForm.tsx` | Created |
| `apps/web/src/features/customers/components/CustomerQuotesList.tsx` | Created |
| `apps/web/src/features/customers/components/CustomerJobsList.tsx` | Created |
| `apps/web/src/features/customers/components/CustomerInvoicesList.tsx` | Created |
| `apps/web/src/features/customers/components/CustomerTabDeferredState.tsx` | Created |
| `apps/web/src/app/(authed)/customers/[id]/layout.tsx` | Updated — Sites tab + customer name |
| `apps/web/src/app/(authed)/customers/[id]/page.tsx` | Updated — CustomerOverviewTab |
| `apps/web/src/app/(authed)/customers/[id]/sites/page.tsx` | Created |
| `apps/web/src/app/(authed)/customers/[id]/quotes/page.tsx` | Updated |
| `apps/web/src/app/(authed)/customers/[id]/jobs/page.tsx` | Updated |
| `apps/web/src/app/(authed)/customers/[id]/invoices/page.tsx` | Updated |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `features/customers/components/__tests__/CustomerForm.test.tsx` | Unit | N | ✅ |
| `features/customers/components/__tests__/CreateCustomerModal.test.tsx` | Unit | N | ✅ |
| `features/customers/components/__tests__/CustomerOverviewTab.test.tsx` | Unit | N | ✅ |
| `features/customers/components/__tests__/SiteListPanel.test.tsx` | Unit | N | ✅ |
| `apps/web/src/__tests__/batch_fe_b18/customerList.integration.test.tsx` | Integration | N | ✅ |
| `apps/web/src/__tests__/batch_fe_b18/customerDetail.integration.test.tsx` | Integration | N | ✅ |
```

---

## After This Batch

FE-B18 is complete. `/customers` and `/customers/[id]` are fully functional.

**Next batch**: `batch-fe-b19-react-engr-prompt.md` — Quote Builder UI. FE-B19 depends on FE-B18 being complete (the quote builder needs a customer picker that pulls from the customer list).
