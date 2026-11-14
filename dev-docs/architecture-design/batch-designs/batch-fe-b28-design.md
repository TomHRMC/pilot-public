# Batch Design: FE-B28 — TanStack Table Migration (All 8 Tables) + Shared Combobox Components

**Batch**: FE-B28  
**Type**: Frontend-only (no backend changes)  
**Depends on**: FE-B26 ✅ + FE-B27 ✅  
**Engineer**: Pilot React Engineer  
**Platform**: Web only (`apps/web`)  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-fe-b28-design.md`  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 — FE-B28 row  
**Source decision**: `dev-docs/testing-support/alpha-testing/ui-testing-status-2026-07-10-v2.md` — "All Data Tables → `@tanstack/react-table`" decision section

---

## A. Input Read Summary

| Input | What Was Read | Key Finding |
|---|---|---|
| `pilot-launch-plan.md` §Phase 1 FE-B28 | Batch scope | 8 tables + sortable headers + column resize + text wrap policy + shared combobox components |
| `ui-testing-status-2026-07-10-v2.md` | Full alpha testing doc | Decision: all list tables use TanStack Table v8 for column resizing + sort; combobox spec provided |
| `apps/web/package.json` | Full dependency list | ⚠️ `@tanstack/react-table` is **NOT installed** — must be added as Step 0 |
| `JobsPage.tsx` (lines 113–252) | Full table rendering | Manual `<table>` with 4 columns; client-side filter on `status_code` + `customer_name`; no sort state |
| `CustomersPage.tsx` (full) | Full table rendering | Manual `<table>` with 3 columns; server-side search via `?search=`; Load More pagination |
| `QuotesPage.tsx` (lines 190–284) | Table section | Manual `<table>` with 5 columns including Actions; server-side status filter; Load More |
| `InvoicesPage.tsx` (lines 210–295) | Table section | Manual `<table>` with 6 columns; overdue toggle filter; Load More pagination |
| `PricebookItemsPage.tsx` (lines 1–80) | Structure | Manual `<table>`; has search + create/edit modals; FE-B27 already right-aligned "Current Price" |
| `LaborRatesPage.tsx` (lines 1–60) | Structure | Manual `<table>`; FE-B27 already right-aligned monetary columns |
| `MarkupsPage.tsx` (lines 1–60) | Structure | Manual `<table>`; FE-B27 already right-aligned "Current Markup" |
| `SupplierItemsPage.tsx` (lines 1–80) | Structure | Manual `<table>` with 4 columns (SKU, Name, Description, Status); read-only; no price column yet |

---

## B. Migration Plan

**No database migrations.** This is a pure frontend batch. No new API endpoints needed — the migration is entirely about replacing manual `<table>` rendering with TanStack Table v8.

### B.1 — New Package Install (Step 0, MANDATORY FIRST)

```bash
cd <repo>/frontend
pnpm add @tanstack/react-table --filter web
```

Verify it was added to `apps/web/package.json` under `dependencies` before proceeding. The package is `@tanstack/react-table` v8 (compatible with React 19).

### B.2 — What TanStack Table Replaces

Each table migration replaces:
- Manual `<thead><tr><th>...</th></tr></thead>` markup → `useReactTable` `getHeaderGroups()` render
- Manual `<tbody>{data.map(row => ...}</tbody>` → `getRowModel().rows` render
- No sort state anywhere → `useSortBy` / `getSortedRowModel()` built-in
- No column resize anywhere → `columnResizeMode: "onChange"` + `header.getSize()` built-in

What is **NOT** replaced by this migration:
- Existing filter pills (Jobs, Invoices) — keep as-is, filter data before passing to `useReactTable`
- Server-side search inputs (Customers, SupplierItems) — keep as-is
- "Load More" pagination buttons — keep as-is (TanStack Table receives the currently-loaded rows)
- Modals (create/edit) — untouched
- `<RoleGate>` wrappers — untouched
- `<LoadingState>`, `<ErrorState>`, `<EmptyState>` — untouched

### B.3 — Global Text Wrap Policy

Per the alpha testing doc decision:

| Column Type | Class | When |
|---|---|---|
| Description / Notes / Name body text | `line-clamp-2 break-words` | Multi-word body columns that benefit from 2-line preview |
| ID columns (SKU, Invoice #, Job #, Quote #) | `whitespace-nowrap font-mono text-xs` | Never wrap identifiers |
| Date columns | `whitespace-nowrap` | Never wrap dates |
| Status badge columns | `whitespace-nowrap` | Never wrap pills |
| Numeric / monetary columns | `whitespace-nowrap tabular-nums text-right` | Right-aligned, never wrap |

Apply this policy at the column `cell` definition level in TanStack Table — not via global CSS.

---

## C. Execution Order

| # | Task | Target File(s) | Notes |
|---|---|---|---|
| 0 | Install `@tanstack/react-table` | `apps/web/package.json` | `pnpm add` before any code |
| 1 | Create `<PilotTable>` shared wrapper component | `apps/web/src/components/PilotTable.tsx` | One shared render layer used by all 8 tables |
| 2 | Migrate `JobsPage.tsx` | `apps/web/src/features/jobs/components/JobsPage.tsx` | First migration — establishes pattern |
| 3 | Migrate `CustomersPage.tsx` | `apps/web/src/features/customers/components/CustomersPage.tsx` | Server-side search preserved |
| 4 | Migrate `QuotesPage.tsx` | `apps/web/src/features/quotes/components/QuotesPage.tsx` | Status filter + Actions column preserved |
| 5 | Migrate `InvoicesPage.tsx` | `apps/web/src/features/invoices/components/InvoicesPage.tsx` | Overdue badge + Load More preserved |
| 6 | Migrate `PricebookItemsPage.tsx` | `apps/web/src/features/catalog/components/PricebookItemsPage.tsx` | Existing FE-B27 right-align preserved via column def |
| 7 | Migrate `LaborRatesPage.tsx` | `apps/web/src/features/catalog/components/LaborRatesPage.tsx` | Existing FE-B27 right-align preserved |
| 8 | Migrate `MarkupsPage.tsx` | `apps/web/src/features/catalog/components/MarkupsPage.tsx` | Existing FE-B27 right-align preserved |
| 9 | Migrate `SupplierItemsPage.tsx` | `apps/web/src/features/catalog/components/SupplierItemsPage.tsx` | Read-only; no price column yet (deferred) |
| 10 | Create `<CustomerCombobox>` shared component | `apps/web/src/components/CustomerCombobox.tsx` | Typeahead select — web-app scoped |
| 11 | Create `<SiteCombobox>` shared component | `apps/web/src/components/SiteCombobox.tsx` | Cascades from `customerId` prop |
| 12 | Wire comboboxes into `JobFormModal` + `JobEditModal` | `JobFormModal.tsx`, `JobEditModal.tsx` | Replace plain `<select>` dropdowns |
| 13 | Integration tests | `__tests__/batch_fe_b28/` | One test file per major table surface |

**Migrate tables in order 2 → 9.** Each is the same pattern. Do not skip Step 1 (`<PilotTable>`) — it prevents 8 copies of identical render boilerplate.

---

## D. Component Specifications

### D.1 — `<PilotTable>` — Shared Render Wrapper

**Location**: `apps/web/src/components/PilotTable.tsx`

This component accepts a TanStack Table instance and renders the shared markup shell (outer `<div>`, `<table>`, column resize handles, sort indicator arrows). Each page creates the table instance with `useReactTable()` and passes it to `<PilotTable>`.

```typescript
import type { Table } from "@tanstack/react-table";

interface PilotTableProps<TData> {
  table: Table<TData>;
  /** Optional: extra CSS classes on the outer container */
  className?: string;
}
```

**`<PilotTable>` renders:**
- Outer container: `overflow-x-auto rounded-lg border border-neutral-200`
- `<table className="w-full table-fixed">` — `table-fixed` enables column width enforcement
- `<thead className="bg-neutral-50 border-b border-neutral-200">` with `getHeaderGroups()` map
- Each `<th>`: `relative px-4 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide select-none` + `cursor-pointer hover:bg-neutral-100` when `header.column.getCanSort()`
- Sort indicator arrow: `▲` (asc), `▼` (desc), or `↕` (unsorted/sortable) — `text-neutral-400 ml-1`; hidden when `!header.column.getCanSort()`
- Column resize handle: `absolute right-0 top-0 h-full w-1 cursor-col-resize bg-neutral-300 opacity-0 hover:opacity-100 select-none touch-none` — rendered via `header.getResizeHandler()`
- `<tbody className="divide-y divide-neutral-100">` with `getRowModel().rows` map
- Each `<tr className="hover:bg-neutral-50 transition-colors">`
- Each `<td style={{ width: cell.column.getSize() }}>` — applies column width from resize state

**Important**: `<PilotTable>` does NOT render empty states, filter UIs, page headers, or action buttons. Those remain in the individual page components. The wrapper only renders the table itself.

### D.2 — Column Definition Pattern (Same For All 8 Tables)

Each page defines its columns using `columnHelper.accessor()`:

```typescript
import { createColumnHelper, getCoreRowModel, getSortedRowModel, useReactTable, flexRender } from "@tanstack/react-table";
import { useState } from "react";
import type { SortingState, ColumnResizingState } from "@tanstack/react-table";

// Example: Jobs table
const columnHelper = createColumnHelper<JobListItem>();

const columns = [
  columnHelper.accessor("customer_name", {
    header: "Customer",
    size: 200,
    minSize: 100,
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
    enableSorting: true,
    cell: (info) => <StatusBadge statusCode={info.getValue()} />,
  }),
  columnHelper.accessor("scheduled_start_at", {
    header: "Scheduled",
    size: 180,
    minSize: 120,
    enableSorting: true,
    cell: (info) => (
      <span className="text-sm text-neutral-600 whitespace-nowrap">
        {formatScheduledDate(info.getValue())}
      </span>
    ),
  }),
  columnHelper.display({
    id: "actions",
    header: "Actions",
    size: 140,
    minSize: 80,
    enableSorting: false,
    cell: (info) => <JobRowActions job={info.row.original} />,
  }),
];
```

**Table instance setup** (same pattern in every page):
```typescript
const [sorting, setSorting] = useState<SortingState>([]);
const [columnSizing, setColumnSizing] = useState<ColumnResizingState>({});

const table = useReactTable({
  data: filtered,            // pre-filtered array (filters stay in page component)
  columns,
  state: { sorting, columnSizing },
  onSortingChange: setSorting,
  onColumnSizingChange: setColumnSizing,
  columnResizeMode: "onChange",
  getCoreRowModel: getCoreRowModel(),
  getSortedRowModel: getSortedRowModel(),
});
```

Pass `table` to `<PilotTable table={table} />`.

### D.3 — Column Specifications Per Table

**Jobs** (4 columns):

| Column | Accessor | Sortable | Size | Text Policy |
|---|---|---|---|---|
| Customer | `customer_name` | ✅ | 200 | `line-clamp-2` |
| Status | `status_code` | ✅ | 140 | `whitespace-nowrap` (badge) |
| Scheduled | `scheduled_start_at` | ✅ | 180 | `whitespace-nowrap` |
| Actions | display | ❌ | 140 | N/A |

**Customers** (3 columns):

| Column | Accessor | Sortable | Size | Text Policy |
|---|---|---|---|---|
| Name | `display_name` | ✅ | 220 | `line-clamp-2` — link styled |
| Type | `type` | ✅ | 120 | `whitespace-nowrap capitalize` |
| Email | `email` | ✅ | 200 | `line-clamp-1` |

**Quotes** (5 columns):

| Column | Accessor | Sortable | Size | Text Policy |
|---|---|---|---|---|
| Quote # | `quote_number` | ✅ | 140 | `whitespace-nowrap` — link styled |
| Customer | `customer_name` | ✅ | 180 | `line-clamp-2` |
| Status | `status_code` | ✅ | 150 | `whitespace-nowrap` (badge) |
| Total | `total_cents` | ✅ | 110 | `whitespace-nowrap tabular-nums text-right` |
| Actions | display | ❌ | 160 | N/A |

**Invoices** (6 columns):

| Column | Accessor | Sortable | Size | Text Policy |
|---|---|---|---|---|
| Invoice # | `invoice_number` | ✅ | 140 | `whitespace-nowrap` — link styled |
| Customer | `customer_name` | ✅ | 180 | `line-clamp-2` |
| Status | `status_code` | ✅ | 170 | `whitespace-nowrap` (badge + overdue) |
| Total | `total_cents` | ✅ | 110 | `whitespace-nowrap tabular-nums text-right` |
| Issued | `issued_at` | ✅ | 130 | `whitespace-nowrap` |
| Due | `due_at` | ✅ | 130 | `whitespace-nowrap` |

**Pricebook** (5 columns):

| Column | Accessor | Sortable | Size | Text Policy |
|---|---|---|---|---|
| SKU | `sku` | ✅ | 120 | `whitespace-nowrap font-mono text-xs` |
| Name | `name` | ✅ | 200 | `line-clamp-2` |
| Description | `description` | ❌ | 240 | `line-clamp-2 text-neutral-500` |
| Current Price | computed | ✅ | 130 | `whitespace-nowrap tabular-nums text-right` |
| Status | `is_active` | ✅ | 100 | `whitespace-nowrap` (badge) |

**Labor Rates** (5 columns):

| Column | Accessor | Sortable | Size | Text Policy |
|---|---|---|---|---|
| Skill Level | `skill_level_label` | ✅ | 160 | `line-clamp-1` |
| Hourly Rate | `hourly_rate_cents` | ✅ | 120 | `whitespace-nowrap tabular-nums text-right` |
| Burden % | `burden_pct` | ✅ | 100 | `whitespace-nowrap tabular-nums` |
| Burdened Rate | computed | ✅ | 140 | `whitespace-nowrap tabular-nums text-right` |
| Effective From | `effective_from` | ✅ | 140 | `whitespace-nowrap` |

> **Note**: Read `useLaborRates` hook to confirm exact field names before defining columns.

**Markups** (3 columns + Actions):

| Column | Accessor | Sortable | Size | Text Policy |
|---|---|---|---|---|
| Category | `markup_category_label` | ✅ | 200 | `line-clamp-1` |
| Current Markup | `markup_pct` | ✅ | 150 | `whitespace-nowrap tabular-nums text-right` — "X%" format |
| Effective From | `effective_from` | ✅ | 160 | `whitespace-nowrap` |

> **Note**: Read `useMarkups` hook to confirm exact field names.

**Supplier Items** (4 columns):

| Column | Accessor | Sortable | Size | Text Policy |
|---|---|---|---|---|
| SKU | `sku` | ✅ | 120 | `whitespace-nowrap font-mono text-xs` |
| Name | `name` | ✅ | 180 | `line-clamp-2` |
| Description | `description` | ❌ | 260 | `line-clamp-2 text-neutral-500` |
| Status | `is_active` | ✅ | 100 | `whitespace-nowrap` (badge) |

### D.4 — `<CustomerCombobox>` Shared Component

**Location**: `apps/web/src/components/CustomerCombobox.tsx`

**Why `apps/web/src/components/` NOT `packages/ui/`**: This component depends on `useCustomers` (TanStack Query + `apiClient`) and must stay web-app-scoped. `packages/ui/` is platform-agnostic and cannot import API hooks.

```typescript
interface CustomerComboboxProps {
  value: string;                          // current customer_id
  onChange: (customerId: string) => void; // fires on selection
  disabled?: boolean;
  placeholder?: string;
  /** Filter customers to specific type (optional) */
  customerType?: string;
}
```

**Behavior:**
- On mount: fetches `GET /api/v1/customers/?limit=200` via `useCustomers({ limit: 200 })`
- Input field: `type="text"` — typing filters the loaded list in-memory (case-insensitive `display_name` match)
- Dropdown: shows up to 20 filtered results, sorted alphabetically by `display_name`
- Selection: sets `value` to `customer.id`; displays `customer.display_name` in the input
- Clear button: `×` icon resets selection (calls `onChange("")`)
- While loading: shows `disabled` input with "Loading customers…" placeholder
- Empty state: "No customers found" message in dropdown when filter returns 0 results

**No library needed.** Implement as a native `<input>` + dropdown `<ul>` with Tailwind. Do NOT install `@headlessui/react` — it's not in `package.json` and is not needed for this.

```typescript
// Token guidance:
// Input: `w-full border border-neutral-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-brand-400`
// Dropdown container: `absolute z-50 w-full mt-1 bg-white border border-neutral-200 rounded-md shadow-lg max-h-48 overflow-y-auto`
// Dropdown item: `px-3 py-2 text-sm text-neutral-700 hover:bg-brand-50 cursor-pointer`
// Selected item: `px-3 py-2 text-sm text-neutral-900 font-medium bg-brand-50 cursor-pointer`
```

### D.5 — `<SiteCombobox>` Shared Component

**Location**: `apps/web/src/components/SiteCombobox.tsx`

```typescript
interface SiteComboboxProps {
  customerId: string | null;              // drives fetch — null = disabled
  value: string;                          // current site_id
  onChange: (siteId: string) => void;
  disabled?: boolean;
  placeholder?: string;
}
```

**Behavior:**
- When `customerId` is null or empty: input is `disabled`, placeholder "Select a customer first"
- When `customerId` changes: re-fetches `GET /api/v1/sites/?customer_id={customerId}` via `useCustomerSites(customerId)`, resets current `value` to `""` (fires `onChange("")`)
- Typing filters in-memory by `site.name` or `site.address`
- Same dropdown UI as `<CustomerCombobox>`

### D.6 — Wire Comboboxes into Existing Modals

**`JobFormModal.tsx`** and **`JobEditModal.tsx`** both currently use plain `<select>` dropdowns for Customer and Site. Replace with `<CustomerCombobox>` and `<SiteCombobox>`:

```tsx
// Before (plain select):
<select value={customerId} onChange={e => setCustomerId(e.target.value)}>
  {customers.map(c => <option key={c.id} value={c.id}>{c.display_name}</option>)}
</select>

// After (combobox):
<CustomerCombobox
  value={customerId}
  onChange={(id) => { setCustomerId(id); setSiteId(""); }}
/>
<SiteCombobox
  customerId={customerId || null}
  value={siteId}
  onChange={setSiteId}
/>
```

These modals import `useCustomers` and `useCustomerSites` directly today — those can be removed since the combobox components own the data fetching.

---

## E. Pattern Reuse Decisions

| Pattern | Applied Where | Reference |
|---|---|---|
| TanStack Table v8 `useReactTable` | All 8 tables | `@tanstack/react-table` — new dependency |
| `columnResizeMode: "onChange"` | `<PilotTable>` | Built-in resizing — no extra library |
| `getSortedRowModel()` | All 8 tables | Built-in sort — no custom `sortField` state |
| Ephemeral resize state | `useState<ColumnResizingState>({})` | No localStorage persistence for MVP |
| Filter state stays in page component | All pages | TanStack Table receives `data` AFTER filter is applied |
| `line-clamp-2` for body text | Description columns | Global text wrap policy per alpha testing doc |
| `whitespace-nowrap` for identifiers/dates/currency | ID, date, monetary columns | Prevents wrapping on short content |
| `<RoleGate>` on Actions column cells | Jobs, Quotes, Pricebook, Labor Rates, Markups | RBAC not changed — cell renders `<RoleGate>` same as before |

---

## F. Shared Module Interfaces

### F.1 — `<PilotTable<TData>>` component

```typescript
// apps/web/src/components/PilotTable.tsx
import type { Table } from "@tanstack/react-table";
import { flexRender } from "@tanstack/react-table";

export function PilotTable<TData>({ table, className }: PilotTableProps<TData>): JSX.Element
```

### F.2 — `<CustomerCombobox>` exports

```typescript
// apps/web/src/components/CustomerCombobox.tsx
export function CustomerCombobox(props: CustomerComboboxProps): JSX.Element
```

### F.3 — `<SiteCombobox>` exports

```typescript
// apps/web/src/components/SiteCombobox.tsx
export function SiteCombobox(props: SiteComboboxProps): JSX.Element
```

**Note**: These components are NOT exported from `packages/ui/src/index.ts` — they are web-app-scoped and not available to mobile or marketing.

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| Should column resize state be persisted to `localStorage`? | No — ephemeral `useState` for MVP. Post-launch, persist via `localStorage` in a follow-up. |
| Should sort be server-side or client-side? | Client-side for all tables. Data volumes at MVP don't require server-side sort. Customers already has server-side search — sort is applied to loaded results only. |
| Should the Comms thread list (from alpha doc) be migrated? | No — the Comms page uses a card list (`<ul>`), not a data `<table>`. The alpha doc explicitly decided React Table does NOT apply to Dispatch Board Day view; the same reasoning applies to the Comms card list. Comms thread text wrap was already fixed in FE-B27 via `text-sm`. |
| Should `<CustomerCombobox>` and `<SiteCombobox>` go in `packages/ui/`? | No — these components use TanStack Query hooks (`useCustomers`, `useCustomerSites`) tied to the web app's `apiClient`. `packages/ui/` is platform-agnostic and must not import API hooks. Place in `apps/web/src/components/`. |
| Does installing `@tanstack/react-table` conflict with existing `@tanstack/react-query`? | No — they are separate packages from TanStack. `@tanstack/react-query` v5 is already installed; `@tanstack/react-table` v8 is compatible and has no shared peer dependency conflicts. |
| Should `<PilotTable>` be in `packages/ui/` or `apps/web/`? | `apps/web/src/components/PilotTable.tsx` — it imports from `@tanstack/react-table` which, while not inherently web-specific, is only used in the web app. No mobile tables use TanStack Table. Keep it web-scoped. |
| Does `SupplierItemsPage` need a price column in FE-B28? | No — the alpha testing doc flagged it as needing a price column, but noted the backend may not return `price_cents` from the current `useSupplierItems` hook. Defer to a future batch. FE-B28 migrates the 4-column table as-is. |
| Should the combobox wire into `InvoiceCreateModal`? | Yes — `InvoiceCreateModal` has Job and Quote dropdowns (not customer/site). The `<CustomerCombobox>` and `<SiteCombobox>` are specifically for customer/site cascade pickers. `InvoiceCreateModal` uses job/quote dropdowns which are separate concerns. Do NOT touch `InvoiceCreateModal` in FE-B28. |

---

## H. Surface Mockup Reference

**No new surfaces.** FE-B28 is a pure refactor + shared component addition. No UI-DS spec is needed. The visual output should be indistinguishable from the current tables except:
- Column header cells have a sort indicator arrow (▲/▼/↕)  
- Column headers have a resize drag handle on the right edge
- Description columns wrap to 2 lines instead of truncating to 1

---

## I. Component Manifest

| Component / File | Location | Action | Notes |
|---|---|---|---|
| `PilotTable.tsx` | `apps/web/src/components/PilotTable.tsx` | **Created** | Shared TanStack Table render wrapper |
| `CustomerCombobox.tsx` | `apps/web/src/components/CustomerCombobox.tsx` | **Created** | Typeahead customer picker |
| `SiteCombobox.tsx` | `apps/web/src/components/SiteCombobox.tsx` | **Created** | Typeahead site picker (cascades from customerId) |
| `JobsPage.tsx` | `apps/web/src/features/jobs/components/JobsPage.tsx` | **Modified** | TanStack Table migration |
| `CustomersPage.tsx` | `apps/web/src/features/customers/components/CustomersPage.tsx` | **Modified** | TanStack Table migration |
| `QuotesPage.tsx` | `apps/web/src/features/quotes/components/QuotesPage.tsx` | **Modified** | TanStack Table migration |
| `InvoicesPage.tsx` | `apps/web/src/features/invoices/components/InvoicesPage.tsx` | **Modified** | TanStack Table migration |
| `PricebookItemsPage.tsx` | `apps/web/src/features/catalog/components/PricebookItemsPage.tsx` | **Modified** | TanStack Table migration |
| `LaborRatesPage.tsx` | `apps/web/src/features/catalog/components/LaborRatesPage.tsx` | **Modified** | TanStack Table migration |
| `MarkupsPage.tsx` | `apps/web/src/features/catalog/components/MarkupsPage.tsx` | **Modified** | TanStack Table migration |
| `SupplierItemsPage.tsx` | `apps/web/src/features/catalog/components/SupplierItemsPage.tsx` | **Modified** | TanStack Table migration |
| `JobFormModal.tsx` | `apps/web/src/features/jobs/components/JobFormModal.tsx` | **Modified** | `<select>` → `<CustomerCombobox>` + `<SiteCombobox>` |
| `JobEditModal.tsx` | `apps/web/src/features/jobs/components/JobEditModal.tsx` | **Modified** | `<select>` → `<CustomerCombobox>` + `<SiteCombobox>` |
| `__tests__/batch_fe_b28/*.integration.test.tsx` | `apps/web/src/__tests__/batch_fe_b28/` | **Created** | One test file per major surface |

---

## ⚠️ Batch Size Advisory

This batch touches **13 files** across 8 table migrations + 3 new shared components + 2 modal wires. This is the largest FE batch to date. To prevent agent context overflow:

1. **Step 1 (`<PilotTable>`) is the critical setup step.** Once that pattern works, each subsequent table is 20–30 lines of column definitions.
2. **Migrate one table at a time.** Run targeted tests after each table (not just at the end).
3. **Combobox components are independent of the table migration.** They can be written in parallel or at the end.
4. **If running low on context**, complete all 8 table migrations first and leave combobox components + modal wiring for the end. The table migrations are the core deliverable.

---

*Design doc authored: 2026-07-11 | FE-B28 depends on FE-B26 ✅ + FE-B27 ✅ | No backend required*
