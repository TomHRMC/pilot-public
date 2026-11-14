# Implementation Prompt: FE-B28 — TanStack Table Migration (All 8 Tables) + Shared Combobox Components

**Mode**: Pilot React Engineer  
**Batch**: FE-B28  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 — FE-B28 row  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-fe-b28-design.md`  
**Estimated session**: 4–6 hours  
**Platform**: Web only (`apps/web`)  
**Backend companion**: None  
**Pure frontend — no backend changes needed**

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-fe-b28-design.md`** — every section (A–I)

**Critical rules for this batch:**

- **Rule 8**: `@tanstack/react-table` is NOT in `package.json`. You MUST run `pnpm add @tanstack/react-table --filter web` as Step 0 before any code. Do not attempt to import it before installing.
- **Rule 7**: `<PilotTable>` and the combobox components go in `apps/web/src/components/` — NOT in `packages/ui/`. They use web-app-specific API hooks and cannot be platform-agnostic.
- **Rule 10**: This batch touches 13 files. Run targeted tests after each table migration — not just at the end. If any test breaks, fix it before moving to the next table.
- **Rule 1.2**: Every column accessor name must be verified against the actual hook return type. Do NOT assume field names — `grep` the hook file first.
- **Rule 9**: Route files remain thin server components — only the feature components change.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Column resize state persistence | Ephemeral `useState` only — no `localStorage` for MVP | Simpler for beta; persistence can be added post-launch |
| Sort | Client-side `getSortedRowModel()` on all tables | Data volumes at MVP don't need server-side sort |
| Comms thread list | NOT migrated to TanStack Table | It's a card list `<ul>`, not a data table |
| `<CustomerCombobox>` / `<SiteCombobox>` location | `apps/web/src/components/` — NOT `packages/ui/` | Uses `useCustomers` + `useCustomerSites` (web-app hooks) |
| `<PilotTable>` location | `apps/web/src/components/PilotTable.tsx` | TanStack Table is web-app-only |
| `InvoiceCreateModal` comboboxes | NOT touched in FE-B28 | That modal has job/quote dropdowns, not customer/site |
| SupplierItems price column | Deferred — not in this batch | Backend may not return `price_cents` yet |

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend

pnpm --filter web test 2>&1 | tail -5
```

Record the exact pass/fail count. All tests must still pass at the end of the batch.

> **If any tests are already failing before you start**: Confirm with Tom before proceeding. Do NOT treat them as "pre-existing" and proceed.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

Verify the command completes without error before starting.

---

## Pre-Work: Verify Column Field Names

Before defining columns for each table, verify the exact field names returned by the hook:

```bash
# Jobs — confirm job_number, status_code, customer_name on JobListItem
grep -n "job_number\|status_code\|customer_name\|JobListItem" \
  frontend/apps/web/src/features/jobs/hooks/useJobs.ts | head -20

# Customers — confirm display_name, type, email
grep -n "display_name\|CustomerListItem\|interface" \
  frontend/apps/web/src/features/customers/hooks/useCustomers.ts | head -15

# Quotes — confirm quote_number, total_cents, status_code
grep -n "quote_number\|total_cents\|QuoteListItem" \
  frontend/apps/web/src/features/quotes/hooks/useQuotes.ts | head -15

# Invoices — confirm invoice_number, customer_name, total_cents, issued_at, due_at
grep -n "invoice_number\|customer_name\|total_cents\|InvoiceListItem" \
  frontend/apps/web/src/features/invoices/hooks/useInvoices.ts | head -20

# Pricebook — confirm field names
grep -n "interface\|PricebookItem\|sku\|is_active" \
  frontend/apps/web/src/features/catalog/hooks/usePricebook.ts | head -20

# Labor Rates — confirm field names
grep -n "interface\|LaborRate\|hourly_rate\|burden" \
  frontend/apps/web/src/features/catalog/hooks/useLaborRates.ts | head -20

# Markups — confirm field names
grep -n "interface\|Markup\|markup_pct\|category" \
  frontend/apps/web/src/features/catalog/hooks/useMarkups.ts | head -20

# Supplier Items — confirm field names
grep -n "interface\|SupplierItem\|sku\|is_active" \
  frontend/apps/web/src/features/catalog/hooks/useSupplierItems.ts | head -20
```

**If any field name in the design doc does not match what you find in the hook**: use the actual hook field name. The design doc uses representative names that must be verified against real code.

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

```
frontend/apps/web/src/features/jobs/components/JobsPage.tsx
← understand current table structure before replacing it

frontend/apps/web/src/features/customers/components/CustomersPage.tsx
← understand server-side search pattern to preserve

frontend/apps/web/src/features/quotes/components/QuotesPage.tsx
← understand Actions column logic to preserve

frontend/apps/web/src/features/invoices/components/InvoicesPage.tsx
← understand overdue badge + Load More pagination to preserve

frontend/apps/web/src/features/jobs/components/JobFormModal.tsx
← understand current customer/site <select> structure before replacing

frontend/apps/web/src/features/jobs/components/JobEditModal.tsx
← understand current customer/site <select> structure before replacing

frontend/apps/web/src/features/customers/hooks/useCustomers.ts
← verify available fields; needed by <CustomerCombobox>

frontend/apps/web/src/features/customers/hooks/useCustomerSites.ts
← verify signature; needed by <SiteCombobox>

frontend/apps/web/src/mocks/handlers/index.ts
← understand handler registration before adding new handlers
```

---

## STEP 0 — Install `@tanstack/react-table` (MANDATORY FIRST)

```bash
cd <repo>/frontend
pnpm add @tanstack/react-table --filter web
```

Verify `apps/web/package.json` now shows `"@tanstack/react-table": "..."` in `dependencies` before proceeding.

---

## STEP 1 — Create `<PilotTable>` Shared Component

**Create**: `frontend/apps/web/src/components/PilotTable.tsx`

This is the shared render shell used by all 8 tables. It accepts a TanStack `Table<TData>` instance and renders the complete `<table>` markup including resize handles and sort indicators.

```tsx
"use client";

import {
  flexRender,
  type Table,
} from "@tanstack/react-table";

interface PilotTableProps<TData> {
  table: Table<TData>;
  className?: string;
}

export function PilotTable<TData>({
  table,
  className = "",
}: PilotTableProps<TData>): JSX.Element {
  return (
    <div className={`overflow-x-auto rounded-lg border border-neutral-200 bg-white ${className}`}>
      <table
        className="w-full table-fixed"
        style={{ width: table.getTotalSize() }}
      >
        <thead className="bg-neutral-50 border-b border-neutral-200">
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <th
                  key={header.id}
                  style={{ width: header.getSize(), position: "relative" }}
                  className={`px-4 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide select-none ${
                    header.column.getCanSort()
                      ? "cursor-pointer hover:bg-neutral-100 transition-colors"
                      : ""
                  }`}
                  onClick={header.column.getToggleSortingHandler()}
                >
                  <span className="flex items-center gap-1">
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )}
                    {header.column.getCanSort() && (
                      <span className="text-neutral-400">
                        {header.column.getIsSorted() === "asc"
                          ? "▲"
                          : header.column.getIsSorted() === "desc"
                            ? "▼"
                            : "↕"}
                      </span>
                    )}
                  </span>
                  {/* Column resize handle */}
                  {header.column.getCanResize() && (
                    <div
                      onMouseDown={header.getResizeHandler()}
                      onTouchStart={header.getResizeHandler()}
                      className={`absolute right-0 top-0 h-full w-1 cursor-col-resize select-none touch-none transition-opacity ${
                        header.column.getIsResizing()
                          ? "bg-brand-400 opacity-100"
                          : "bg-neutral-300 opacity-0 hover:opacity-100"
                      }`}
                    />
                  )}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody className="divide-y divide-neutral-100">
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id} className="hover:bg-neutral-50 transition-colors">
              {row.getVisibleCells().map((cell) => (
                <td
                  key={cell.id}
                  style={{ width: cell.column.getSize() }}
                  className="px-4 py-3"
                >
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

**Intermediate verification** after creating this file:
```bash
cd <repo>/frontend
pnpm --filter web check-types 2>&1 | tail -10
```
Fix any type errors before proceeding.

---

## STEP 2 — Migrate `JobsPage.tsx`

**Read the file first**: `read_file frontend/apps/web/src/features/jobs/components/JobsPage.tsx`

This is the template migration. Get this right — the other 7 tables follow the same pattern.

### Pattern to apply:

```tsx
import {
  createColumnHelper,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import type { SortingState, ColumnResizingState } from "@tanstack/react-table";
import { PilotTable } from "../../../../components/PilotTable";

// 1. Define columnHelper outside the component
const columnHelper = createColumnHelper<JobListItem>();

// 2. Define columns outside the component (or inside if cell renderer needs component state)
const columns = [
  columnHelper.accessor("customer_name", {
    header: "Customer",
    size: 200,
    minSize: 100,
    enableResizing: true,
    enableSorting: true,
    cell: (info) => (
      <span className="text-sm font-medium text-neutral-900 line-clamp-2">
        {info.getValue()}
      </span>
    ),
  }),
  columnHelper.accessor("status_code", {
    header: "Status",
    size: 140,
    minSize: 100,
    enableResizing: true,
    enableSorting: true,
    cell: (info) => <StatusBadge statusCode={info.getValue() ?? ""} />,
  }),
  columnHelper.accessor("scheduled_start_at", {
    header: "Scheduled",
    size: 180,
    minSize: 120,
    enableResizing: true,
    enableSorting: true,
    cell: (info) => (
      <span className="text-sm text-neutral-600 whitespace-nowrap">
        {formatScheduledDate(info.getValue())}
      </span>
    ),
  }),
  // Actions column needs access to component state (addJobOpen, etc.)
  // Use columnHelper.display for non-data columns
  columnHelper.display({
    id: "actions",
    header: "Actions",
    size: 140,
    minSize: 80,
    enableResizing: false,
    enableSorting: false,
    cell: (info) => {
      const job = info.row.original;
      const isTerminal = TERMINAL_STATUSES.has(job.status_code);
      return (
        <div className="flex items-center gap-2">
          <Link href={`/jobs/${job.id}`} className="text-sm text-brand-600 hover:text-brand-800 font-medium">
            View
          </Link>
          {isTerminal && (
            <RoleGate role={["owner", "office_staff", "operator"]}>
              <Link href={`/invoices/new?job_id=${job.id}`} className="text-sm text-brand-600 hover:text-brand-800 font-medium">
                Create Invoice
              </Link>
            </RoleGate>
          )}
        </div>
      );
    },
  }),
];

// 3. Inside the component:
const [sorting, setSorting] = useState<SortingState>([]);
const [columnSizing, setColumnSizing] = useState<ColumnResizingState>({});

const table = useReactTable({
  data: filtered,   // pass the already-filtered array (filter logic stays in component)
  columns,
  state: { sorting, columnSizing },
  onSortingChange: setSorting,
  onColumnSizingChange: setColumnSizing,
  columnResizeMode: "onChange",
  getCoreRowModel: getCoreRowModel(),
  getSortedRowModel: getSortedRowModel(),
});

// 4. Replace the manual <table> render with:
// (if filtered.length === 0 → keep existing EmptyState)
<PilotTable table={table} />
```

**What to preserve** (do NOT remove these):
- `JobFormModal` + "Add Job" button + `RoleGate`
- Status filter pills
- Customer search input
- `EmptyState` when filtered.length === 0
- All existing imports that are still needed

**What to remove**:
- The entire manual `<div className="overflow-hidden rounded-lg border..."><table>...</table></div>` block
- Individual `<th>` + `<td>` markup (replaced by `<PilotTable>`)
- Manual `filtered.map((job) => <JobRow .../>)` (replaced by TanStack row model)
- The `JobRow` sub-component (inline into column def or keep as helper — your choice)

**Run tests after this step**:
```bash
cd <repo>/frontend
pnpm --filter web test -- __tests__/batch_fe_b28 2>&1 | tail -10
npx vitest run apps/web/src/features/jobs 2>&1 | tail -10
```

---

## STEPS 3–9 — Migrate Remaining 7 Tables

**Same pattern as Step 2.** For each table:
1. Read the file
2. Verify exact field names via `grep` against the hook
3. Define `columnHelper` + `columns` + `useReactTable`
4. Replace manual `<table>` block with `<PilotTable table={table} />`
5. Preserve ALL existing filter UI, search inputs, modals, buttons, EmptyState, LoadMore

### Step 3 — `CustomersPage.tsx`

Columns: Name (link, `display_name`), Type (`type`), Email (`email`)
- **Server-side search is preserved** — `useCustomers({ search })` stays unchanged
- **Load More pagination** stays unchanged — TanStack receives the currently loaded page
- Name column: `<a href={/customers/${c.id}} className="text-brand-600 hover:underline font-medium">{c.display_name}</a>`
- Verify actual field names: `grep -n "display_name\|interface" frontend/apps/web/src/features/customers/hooks/useCustomers.ts`

### Step 4 — `QuotesPage.tsx`

Columns: Quote # (link, `quote_number`), Customer (`customer_name`), Status (`status_code`), Total (`total_cents`, right-aligned), Actions (display)
- **Status filter** + **Load More** preserved in component
- Actions column renders `ConvertToJobButton`, edit link, review link — preserve these exactly as they are
- Quote # column: `<a href={/quotes/${q.id}} className="text-brand-600 hover:underline font-medium text-sm">{q.quote_number ?? ${q.id.slice(0, 8)}…}</a>`
- Total column: right-aligned `text-right tabular-nums whitespace-nowrap`

### Step 5 — `InvoicesPage.tsx`

Columns: Invoice # (link, `invoice_number`), Customer (`customer_name`), Status + Overdue badge, Total (right-aligned, `total_cents`), Issued (`issued_at`), Due (`due_at`)
- **Overdue toggle** + **filter pills** + **Load More** preserved in component
- Status cell: render both the status pill AND the overdue badge (use `info.row.original` to access full invoice object for `isOverdue(inv)`)
- Read file fully to understand the overdue badge render and `isOverdue()` function before migrating

### Step 6 — `PricebookItemsPage.tsx`

Columns: SKU, Name, Description, Current Price (right-aligned), Status
- **Modals** (create, edit, update-price) + "Add Item" button preserved
- Read the file to understand what `PricebookItem` looks like (especially the price field name)
- Verify: `grep -n "price\|PricebookItem\|is_active" frontend/apps/web/src/features/catalog/hooks/usePricebook.ts`

### Step 7 — `LaborRatesPage.tsx`

Columns: Skill Level, Hourly Rate (right-aligned), Burden %, Burdened Rate (right-aligned, computed), Effective From
- Read the file to understand how burdened rate is computed (it may be computed in a cell from base fields)
- Verify: `grep -n "interface\|LaborRate\|hourly\|burden" frontend/apps/web/src/features/catalog/hooks/useLaborRates.ts`

### Step 8 — `MarkupsPage.tsx`

Columns: Category, Current Markup (right-aligned, "X%"), Effective From
- Read the file and hook to verify markup field names
- Verify: `grep -n "interface\|Markup\|markup_pct\|category" frontend/apps/web/src/features/catalog/hooks/useMarkups.ts`

### Step 9 — `SupplierItemsPage.tsx`

Columns: SKU, Name, Description, Status
- Read-only table — no create/edit actions
- No price column in this batch (deferred — verify `useSupplierItems` doesn't already return price_cents; if it does, don't block — add it)
- Verify: `grep -n "interface\|SupplierItem" frontend/apps/web/src/features/catalog/hooks/useSupplierItems.ts`

---

## STEP 10 — Create `<CustomerCombobox>` Component

**Create**: `frontend/apps/web/src/components/CustomerCombobox.tsx`

**Read the hook first**: `read_file frontend/apps/web/src/features/customers/hooks/useCustomers.ts`

This is a typeahead input — NOT a `<select>`. No new library needed. Native `<input>` + dropdown `<ul>`.

```tsx
"use client";

import { useState, useRef, useEffect } from "react";
import { useCustomers } from "../features/customers/hooks/useCustomers";
// Adjust import path based on actual structure

interface CustomerComboboxProps {
  value: string;          // current customer_id (empty string = no selection)
  onChange: (customerId: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function CustomerCombobox({
  value,
  onChange,
  disabled,
  placeholder = "Search customers…",
}: CustomerComboboxProps) {
  const [inputText, setInputText] = useState("");
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const { data: customers, isLoading } = useCustomers({ limit: 200 });

  // Sync inputText with selected value display_name
  const selectedCustomer = customers?.find((c) => c.id === value);
  useEffect(() => {
    if (selectedCustomer) {
      setInputText(selectedCustomer.display_name);
    } else {
      setInputText("");
    }
  }, [selectedCustomer]);

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filtered = (customers ?? [])
    .filter((c) => c.display_name.toLowerCase().includes(inputText.toLowerCase()))
    .slice(0, 20);

  function handleSelect(customerId: string, displayName: string) {
    onChange(customerId);
    setInputText(displayName);
    setOpen(false);
  }

  function handleClear() {
    onChange("");
    setInputText("");
    setOpen(false);
  }

  return (
    <div ref={containerRef} className="relative">
      <div className="flex items-center">
        <input
          type="text"
          value={inputText}
          onChange={(e) => { setInputText(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
          disabled={disabled || isLoading}
          placeholder={isLoading ? "Loading customers…" : placeholder}
          className="w-full border border-neutral-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-brand-400 disabled:bg-neutral-50 disabled:text-neutral-400"
          role="combobox"
          aria-expanded={open}
          aria-autocomplete="list"
        />
        {value && !disabled && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute right-2 text-neutral-400 hover:text-neutral-600 text-lg leading-none"
            aria-label="Clear selection"
          >
            ×
          </button>
        )}
      </div>
      {open && filtered.length > 0 && (
        <ul
          className="absolute z-50 w-full mt-1 bg-white border border-neutral-200 rounded-md shadow-lg max-h-48 overflow-y-auto"
          role="listbox"
        >
          {filtered.map((c) => (
            <li
              key={c.id}
              role="option"
              aria-selected={c.id === value}
              onClick={() => handleSelect(c.id, c.display_name)}
              className={`px-3 py-2 text-sm cursor-pointer ${
                c.id === value
                  ? "bg-brand-50 text-brand-700 font-medium"
                  : "text-neutral-700 hover:bg-brand-50"
              }`}
            >
              {c.display_name}
            </li>
          ))}
        </ul>
      )}
      {open && !isLoading && filtered.length === 0 && inputText && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-neutral-200 rounded-md shadow-lg px-3 py-2 text-sm text-neutral-500">
          No customers found
        </div>
      )}
    </div>
  );
}
```

**Adjust import paths** to match the actual directory structure. The `useCustomers` import path from `apps/web/src/components/` to `apps/web/src/features/customers/hooks/useCustomers.ts` will be a relative path like `../features/customers/hooks/useCustomers`.

---

## STEP 11 — Create `<SiteCombobox>` Component

**Create**: `frontend/apps/web/src/components/SiteCombobox.tsx`

**Read the hook first**: `read_file frontend/apps/web/src/features/customers/hooks/useCustomerSites.ts`

Same pattern as `<CustomerCombobox>`, but:
- Disabled when `customerId` is null/empty
- Re-fetches when `customerId` changes
- Calls `useCustomerSites(customerId)` from `apps/web/src/features/customers/hooks/useCustomerSites.ts`
- Resets selection when `customerId` changes (call `onChange("")` via `useEffect` on `customerId` change)
- Site display: use `site.name` or `site.address` — check the hook to see which field exists

```typescript
interface SiteComboboxProps {
  customerId: string | null;
  value: string;
  onChange: (siteId: string) => void;
  disabled?: boolean;
  placeholder?: string;
}
```

---

## STEP 12 — Wire Comboboxes into `JobFormModal` + `JobEditModal`

**Read both files first**:
- `read_file frontend/apps/web/src/features/jobs/components/JobFormModal.tsx`
- `read_file frontend/apps/web/src/features/jobs/components/JobEditModal.tsx`

In each modal, find the customer `<select>` and site `<select>`. Replace them:

```tsx
// Add imports at top:
import { CustomerCombobox } from "../../../../components/CustomerCombobox";
import { SiteCombobox } from "../../../../components/SiteCombobox";

// Replace customer <select>:
<CustomerCombobox
  value={customerId}
  onChange={(id) => {
    setCustomerId(id);
    setSiteId("");  // reset site when customer changes
  }}
/>

// Replace site <select>:
<SiteCombobox
  customerId={customerId || null}
  value={siteId}
  onChange={setSiteId}
/>
```

**Also remove**: the `useCustomers` and `useCustomerSites` imports that are now handled inside the combobox components (if they were imported directly in the modal).

**Verify the existing `useCreateJob` / `useUpdateJob` mutation payload still gets `customer_id` and `site_id` correctly** — the state variables (`customerId`, `siteId`) don't change, only the input components change.

---

## Test Implementation

### Test file locations

Create in `apps/web/src/__tests__/batch_fe_b28/`:

| Test File | Surface Tested |
|---|---|
| `pilot_table.test.tsx` | `<PilotTable>` component renders, sort indicators, resize handle |
| `jobs_table_migration.integration.test.tsx` | `JobsPage` TanStack Table renders correct rows + sortable header |
| `customers_table_migration.integration.test.tsx` | `CustomersPage` TanStack Table renders rows |
| `quotes_table_migration.integration.test.tsx` | `QuotesPage` quote_number column + Actions column |
| `invoices_table_migration.integration.test.tsx` | `InvoicesPage` columns + overdue badge preserved |
| `catalog_tables_migration.integration.test.tsx` | Pricebook + LaborRates + Markups + SupplierItems (can be one file) |
| `customer_combobox.test.tsx` | `<CustomerCombobox>` filter, select, clear |
| `site_combobox.test.tsx` | `<SiteCombobox>` disabled when no customer, re-fetches on change |

### TanStack Query — Required Setup

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

### Mock Next.js

```typescript
import { vi } from "vitest";
import React from "react";

vi.mock("next/navigation", () => ({
  usePathname: () => "/jobs",
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: any) =>
    React.createElement("a", { href, ...rest }, children),
}));
```

### MSW Setup

```typescript
import { setupServer } from "msw/node";
import { handlers } from "../../mocks/handlers/index";

const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

### Minimum Test Coverage

**`<PilotTable>` unit tests**:
1. Renders table with correct number of rows
2. Sort indicator shows "↕" for sortable column headers
3. Sort changes to "▲" after clicking a sortable header
4. Sort changes to "▼" on second click (desc)
5. Non-sortable columns show no indicator

**Per table migration integration test** (minimum):
1. Table renders without crashing
2. Correct columns are present (check header text)
3. Correct data appears in rows (from MSW fixture)
4. Clicking a sortable column header sorts the rows

**`<CustomerCombobox>` unit tests**:
1. Renders with disabled state when `isLoading`
2. Filters list when user types
3. Calls `onChange` with customer_id on selection
4. Clears selection on `×` click
5. Shows "No customers found" when filter returns 0 results

**`<SiteCombobox>` unit tests**:
1. Renders as disabled when `customerId` is null
2. Enables and fetches when `customerId` provided
3. Calls `onChange("")` when `customerId` changes (reset)
4. Calls `onChange(siteId)` on selection

---

## Final Verification

### Phase 1 — Targeted tests (run after each step during development)

```bash
cd <repo>/frontend

# Run only batch_fe_b28 tests:
npx vitest run apps/web/src/__tests__/batch_fe_b28 2>&1 | tail -15

# Run all web tests periodically:
pnpm --filter web test 2>&1 | tail -6
```

Fix any failure before moving to the next step.

### Phase 2 — Full verification (run once at the very end)

```bash
cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter mobile build && pnpm --filter @pilot/ui lint && pnpm --filter web lint && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== FE-B28 FINAL VERIFICATION COMPLETE ==="
```

> **Any failure must be fixed before declaring the batch done.**

---

## Definition of Done — FE-B28

Update `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 FE-B28 section when each item is done:

- [ ] Pre-modification regression baseline captured
- [ ] `pnpm sync-api-types` run — no new type errors
- [ ] Design doc `batch-fe-b28-design.md` fully read before writing any code
- [ ] All hook field names verified via `grep` before writing column definitions
- [ ] **STEP 0**: `@tanstack/react-table` installed in `apps/web/package.json`
- [ ] **STEP 1**: `apps/web/src/components/PilotTable.tsx` created — renders TanStack Table with sort indicators + resize handles
- [ ] **STEP 2**: `JobsPage.tsx` migrated — manual `<table>` replaced; filter/search/modals preserved
- [ ] **STEP 3**: `CustomersPage.tsx` migrated — server-side search + Load More preserved
- [ ] **STEP 4**: `QuotesPage.tsx` migrated — Actions column preserved
- [ ] **STEP 5**: `InvoicesPage.tsx` migrated — overdue badge + Load More preserved
- [ ] **STEP 6**: `PricebookItemsPage.tsx` migrated — FE-B27 right-aligned price preserved
- [ ] **STEP 7**: `LaborRatesPage.tsx` migrated — FE-B27 right-aligned rates preserved
- [ ] **STEP 8**: `MarkupsPage.tsx` migrated — FE-B27 right-aligned markup preserved
- [ ] **STEP 9**: `SupplierItemsPage.tsx` migrated — 4 columns preserved
- [ ] **STEP 10**: `apps/web/src/components/CustomerCombobox.tsx` created — typeahead filter, select, clear
- [ ] **STEP 11**: `apps/web/src/components/SiteCombobox.tsx` created — disabled when no customer, resets on customer change
- [ ] **STEP 12**: `JobFormModal.tsx` + `JobEditModal.tsx` — `<select>` replaced with comboboxes
- [ ] All 8 integration test files created in `__tests__/batch_fe_b28/`
- [ ] `<PilotTable>` unit test file created
- [ ] `<CustomerCombobox>` + `<SiteCombobox>` unit test files created
- [ ] Column sort works on at least 3 columns per table (click header → rows reorder)
- [ ] Column resize drag handle visible on hover
- [ ] Global text wrap policy applied: description columns `line-clamp-2`; identifiers/dates/currency `whitespace-nowrap`
- [ ] Zero TypeScript errors (`pnpm --filter web check-types` passes)
- [ ] Zero ESLint errors
- [ ] No regressions in pre-existing test suite
- [ ] **Phase 2 FULL verification command passes** (`=== FE-B28 FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter mobile build && pnpm --filter @pilot/ui lint && pnpm --filter web lint && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== FE-B28 FINAL VERIFICATION COMPLETE ==="
  ```
- [ ] Final test count (before → after) documented in Completion Summary below

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** subsection to `dev-docs/analysis/pilot-launch-plan.md` in the FE-B28 section.

```markdown
### FE-B28 — TanStack Table Migration + Shared Combobox Components: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (web)
**Final**: X+N passed (+N new tests)

#### What Was Accomplished

- Installed `@tanstack/react-table` v8 in `apps/web`
- Created `<PilotTable>` shared wrapper with sort indicators + column resize handles
- Migrated all 8 data tables (Jobs, Customers, Quotes, Invoices, Pricebook, Labor Rates, Markups, Supplier Items) from manual `<table>` to TanStack Table
- Applied global text wrap policy: `line-clamp-2` on description/name columns; `whitespace-nowrap` on identifiers/dates/currency
- Created `<CustomerCombobox>` + `<SiteCombobox>` typeahead select components
- Wired comboboxes into `JobFormModal` + `JobEditModal` (replaced plain `<select>`)

#### Files Changed / Created

| File | Action |
|---|---|
| `apps/web/package.json` | Updated — `@tanstack/react-table` added |
| `apps/web/src/components/PilotTable.tsx` | Created |
| `apps/web/src/components/CustomerCombobox.tsx` | Created |
| `apps/web/src/components/SiteCombobox.tsx` | Created |
| `apps/web/src/features/jobs/components/JobsPage.tsx` | Updated — TanStack Table migration |
| `apps/web/src/features/customers/components/CustomersPage.tsx` | Updated — TanStack Table migration |
| `apps/web/src/features/quotes/components/QuotesPage.tsx` | Updated — TanStack Table migration |
| `apps/web/src/features/invoices/components/InvoicesPage.tsx` | Updated — TanStack Table migration |
| `apps/web/src/features/catalog/components/PricebookItemsPage.tsx` | Updated — TanStack Table migration |
| `apps/web/src/features/catalog/components/LaborRatesPage.tsx` | Updated — TanStack Table migration |
| `apps/web/src/features/catalog/components/MarkupsPage.tsx` | Updated — TanStack Table migration |
| `apps/web/src/features/catalog/components/SupplierItemsPage.tsx` | Updated — TanStack Table migration |
| `apps/web/src/features/jobs/components/JobFormModal.tsx` | Updated — CustomerCombobox + SiteCombobox |
| `apps/web/src/features/jobs/components/JobEditModal.tsx` | Updated — CustomerCombobox + SiteCombobox |
| `apps/web/src/__tests__/batch_fe_b28/*.test.tsx` | Created — N test files |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `batch_fe_b28/pilot_table.test.tsx` | Unit | N | ✅ |
| `batch_fe_b28/jobs_table_migration.integration.test.tsx` | Integration | N | ✅ |
| `batch_fe_b28/customers_table_migration.integration.test.tsx` | Integration | N | ✅ |
| `batch_fe_b28/quotes_table_migration.integration.test.tsx` | Integration | N | ✅ |
| `batch_fe_b28/invoices_table_migration.integration.test.tsx` | Integration | N | ✅ |
| `batch_fe_b28/catalog_tables_migration.integration.test.tsx` | Integration | N | ✅ |
| `batch_fe_b28/customer_combobox.test.tsx` | Unit | N | ✅ |
| `batch_fe_b28/site_combobox.test.tsx` | Unit | N | ✅ |
```
