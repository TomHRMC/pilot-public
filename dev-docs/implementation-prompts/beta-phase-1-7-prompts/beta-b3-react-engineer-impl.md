# Implementation Prompt: BETA-B3 — Web List/Index Pages

**Mode**: Pilot React Engineer  
**Batch**: BETA-B3  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-beta-v1-fixes-b3-design.md`  
**Source plan**: `dev-docs/analysis/pilot-app-beta-fixes-v1-impl-plan.md` §8 BETA-B3  
**Estimated session**: 4–6 hours  
**Contains companion Python Engineer backend tasks** — see §Companion Backend Tasks below

---

## ⚠️ MANDATORY STOP: Read These Rules First

Before writing a single line of code, read:
- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full

The highest-risk rules for this batch:
- **Rule 1.1**: Every endpoint path and param in the design doc was verified from `backend/openapi_schema_map.md`. Do NOT deviate from what the design doc specifies.
- **Rule 1.3**: Run `pnpm sync-api-types` before starting. Use types from `@pilot/shared-types` where available.
- **Rule 2**: All API calls use `apiClient`. Never raw `fetch()`.
- **Rule 7**: Check `packages/ui/src/index.ts` for shared components before creating anything new.

---

## Design Principle

> **This batch is PRD-driven, not API-as-built driven.** The PRD defines what the product must do. When the backend falls short of PRD requirements, the gap is called out and addressed — not silently dropped. Frontend components are designed against product requirements. Backend gaps are companion tasks executed in parallel.

---

## Context: What This Batch Does

| Route | Current State | Target State |
|---|---|---|
| `/customers` | `<h1>Customers</h1>` stub | Paginated customer list with search, name, type, email |
| `/quotes` | `<h1>Quotes</h1>` stub | Paginated quotes list with status filter pills, `<RoleGate>` for tech exclusion |
| `/invoices` | `<h1>Invoices</h1>` stub | Paginated invoices with status filter pills, Load More, `<RoleGate>` for tech exclusion |
| `/notifications` | `<h1>Notifications</h1>` stub | Notification list using existing `useInAppNotifications` hook |
| `/operations` | `<h1>Operations</h1>` stub | Next.js redirect to `/settings/operations/field-operations` |
| `/sync` | `<h1>Sync</h1>` stub | Next.js redirect to `/settings/sync-storage/background-sync` |

> **`/comms` is NOT in scope** — confirmed fully implemented (154 lines). Do not touch it.

---

## Companion Backend Tasks (Python Engineer)

Before or alongside this frontend work, a Python Engineer must complete these backend gaps. They are NOT blockers for the frontend (MSW handlers cover the gaps during development), but they MUST be completed before BETA-B3 can be marked fully done.

| # | Task | Endpoint | What's Missing |
|---|---|---|---|
| BE-1 | Add `?search=` to customer list | `GET /api/v1/customers/` | Case-insensitive search across `display_name`, `first_name`, `last_name`, `company_name`, `email` |
| BE-2 | Add `?status=` filter to quotes list | `GET /api/v1/quotes` | Status filter param for PRD §3.10 quote lifecycle |
| BE-3 | Add `status_code` to quotes list response | `GET /api/v1/quotes` | Returns `status_id` UUID only — `status_code` (string) required for display |
| BE-4 | Add `customer_name` to quotes list response | `GET /api/v1/quotes` | Returns `customer_id` UUID only — `customer_name` (denormalized) required for display |
| BE-5 | Add `require_permission("quotes.list")` to quotes endpoint | `GET /api/v1/quotes` | Server-side RBAC must match frontend `<RoleGate permission="quotes.view">` |
| BE-6 | Add `require_permission("invoices.list")` to invoices endpoint | `GET /api/v1/invoices/` | Server-side RBAC must match frontend `<RoleGate permission="invoices.view">` |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter @pilot/ui test 2>&1 | tail -5
pnpm --filter web test 2>&1 | tail -5
```

Record these counts. All must still pass at the end.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

---

## Pre-Work: Read the Full Design Doc

**Read the complete design doc before writing any code:**

```
dev-docs/architecture-design/batch-designs/batch-beta-v1-fixes-b3-design.md
```

It contains the exact TypeScript interfaces for all hooks (§F), API endpoint details (§D), RBAC spec (§C.2), and test plan (§I). Implement exactly what the design doc specifies.

---

## Pre-Work: Verify Existing Files

```bash
# Confirm feature folders don't exist yet (must not recreate if they do):
ls frontend/apps/web/src/features/customers/ 2>/dev/null || echo "DOES NOT EXIST - OK to create"
ls frontend/apps/web/src/features/quotes/ 2>/dev/null || echo "DOES NOT EXIST - OK to create"
ls frontend/apps/web/src/features/invoices/ 2>/dev/null || echo "DOES NOT EXIST - OK to create"
ls frontend/apps/web/src/features/notifications-center/components/ 2>/dev/null || echo "DOES NOT EXIST - OK to create"

# Confirm useInAppNotifications already exists (do NOT recreate):
ls frontend/packages/ui/src/hooks/useInAppNotifications.ts
```

Also read the actual `permissions.ts` file before modifying it:
```bash
cat frontend/packages/ui/src/role-gate/permissions.ts
```

---

## Implementation: Step-by-Step Execution

Follow the execution order from Design Doc §B exactly. **Step 0 must be completed before any page component is written.**

---

### STEP 0 (P0): Update `permissions.ts` — MUST DO FIRST

**File**: `frontend/packages/ui/src/role-gate/permissions.ts`

Read the file first. Then add three new permission keys and update the role-permission map.

**Add to `PermissionKey` type union** (preserve all existing keys verbatim):

```typescript
| "customers.view"   // CRM list — all authenticated roles including tech
| "quotes.view"      // Financial surface — owner, office_staff, operator only; NOT tech
| "invoices.view";   // Financial surface — owner, office_staff, operator only; NOT tech
```

**Add to `ROLE_PERMISSION_MAP`** (the exact structure depends on what the file currently uses — read it first):

| Permission | owner | office_staff | tech | operator |
|---|---|---|---|---|
| `customers.view` | ✅ | ✅ | ✅ | ✅ |
| `quotes.view` | ✅ | ✅ | ❌ | ✅ |
| `invoices.view` | ✅ | ✅ | ❌ | ✅ |

**Rationale** (from Design Doc §C.2):
- `customers.view` — tech needs customer contact details, site instructions, and hazard notes in the field (PRD §3.3). Customer data is not financial data.
- `quotes.view` / `invoices.view` — PRD §3.5 explicitly excludes technicians from financial admin permissions. Quote totals (`total_cents`) and invoice billing data are financial surfaces.

**Run tests immediately after this change:**
```bash
pnpm --filter @pilot/ui test 2>&1 | tail -5
```

Zero regressions required before proceeding.

---

### STEP 1: Create `useCustomers.ts` hook

**File**: `frontend/apps/web/src/features/customers/hooks/useCustomers.ts`

Implement exactly per Design Doc **§F.1**:

```typescript
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface CustomerListItem {
  id: string;
  tenant_id: string;
  type: string;
  display_name: string;
  first_name: string | null;
  last_name: string | null;
  company_name: string | null;
  email: string | null;
}

export interface UseCustomersOptions {
  skip?: number;
  limit?: number;
}

export const CUSTOMERS_QUERY_KEY = (skip: number, limit: number) =>
  ["customers", skip, limit] as const;

export function useCustomers({ skip = 0, limit = 100 }: UseCustomersOptions = {}) {
  return useQuery({
    queryKey: CUSTOMERS_QUERY_KEY(skip, limit),
    queryFn: async (): Promise<CustomerListItem[]> => {
      const res = await apiClient.get("/api/v1/customers/", {
        params: { skip, limit },
      });
      return res.data as CustomerListItem[];
    },
    staleTime: 60_000,
  });
}
```

> **Note on search**: The hook fetches all customers up to `limit`. `CustomersPage` performs client-side filtering. When the Python Engineer adds `?search=` (BE-1), the hook will be updated to pass it and disable client-side filtering.

---

### STEP 2: Create `CustomersPage.tsx` component

**File**: `frontend/apps/web/src/features/customers/components/CustomersPage.tsx`

Requirements:
- Search input with client-side filter across `display_name`, `first_name`, `last_name`, `company_name`, `email`
- Table: Name (link to `/customers/[id]`), Type, Email
- Load More (detect end-of-list when `data.length < PAGE_SIZE`)
- Loading, Empty, and Error states from shared catalog

```tsx
"use client";

import { useState, useMemo } from "react";
import { useCustomers, CustomerListItem } from "../hooks/useCustomers";
import { EmptyState, LoadingState, ErrorState } from "@pilot/ui/states";

const PAGE_SIZE = 100;

export function CustomersPage() {
  const [skip, setSkip] = useState(0);
  const [search, setSearch] = useState("");
  const { data, isLoading, isError, refetch } = useCustomers({ skip, limit: PAGE_SIZE });

  const customers = data ?? [];

  const filtered = useMemo(() => {
    if (!search.trim()) return customers;
    const q = search.toLowerCase();
    return customers.filter((c) =>
      [c.display_name, c.first_name, c.last_name, c.company_name, c.email]
        .some((f) => f?.toLowerCase().includes(q))
    );
  }, [customers, search]);

  if (isLoading) return <LoadingState type="inline" label="Loading customers..." />;
  if (isError) return (
    <ErrorState
      type="server"
      title="Could not load customers"
      description="Check your connection and try again."
      onRetry={() => refetch()}
    />
  );

  if (customers.length === 0 && skip === 0) {
    return (
      <EmptyState
        type="no-data"
        title="No customers yet"
        description="Customers will appear here once added."
      />
    );
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-neutral-900">Customers</h1>
        <span className="text-sm text-neutral-500">{filtered.length} of {customers.length}</span>
      </div>

      {/* Search input — client-side filter (server-side search coming via backend BE-1 task) */}
      <div className="mb-4">
        <input
          type="search"
          placeholder="Search customers..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full max-w-sm px-3 py-2 text-sm border border-neutral-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-400"
          aria-label="Search customers"
        />
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          type="no-results"
          title="No customers match your search"
          description="Try a different search term."
        />
      ) : (
        <>
          <div className="rounded-md border border-neutral-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-neutral-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-neutral-600">Name</th>
                  <th className="px-4 py-3 text-left font-medium text-neutral-600">Type</th>
                  <th className="px-4 py-3 text-left font-medium text-neutral-600">Email</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {filtered.map((c) => (
                  <tr key={c.id} className="hover:bg-neutral-50">
                    <td className="px-4 py-3">
                      <a href={`/customers/${c.id}`} className="text-brand-600 hover:underline font-medium">
                        {c.display_name}
                      </a>
                    </td>
                    <td className="px-4 py-3 text-neutral-600 capitalize">{c.type}</td>
                    <td className="px-4 py-3 text-neutral-600">{c.email ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {customers.length === PAGE_SIZE && !search && (
            <button
              onClick={() => setSkip(skip + PAGE_SIZE)}
              className="mt-4 px-4 py-2 text-sm text-brand-600 border border-brand-200 rounded-md hover:bg-brand-50"
            >
              Load More
            </button>
          )}
        </>
      )}
    </div>
  );
}
```

---

### STEP 3: Update `customers/page.tsx` route

**File**: `frontend/apps/web/src/app/(authed)/customers/page.tsx`

Replace stub entirely — no `"use client"` at route level:

```tsx
import { CustomersPage } from "@/features/customers/components/CustomersPage";

export default function CustomersIndexPage() {
  return <CustomersPage />;
}
```

---

### STEP 4: Create Quotes MSW Handler

**Before implementing `QuotesPage`**, create the MSW handler that mocks the enhanced response shape (including `status_code` and `customer_name` that the real backend is missing).

**File**: `frontend/apps/web/src/mocks/handlers/quotes-list.ts` (or add to existing `quotes.ts` if it exists — check first with `ls frontend/apps/web/src/mocks/handlers/`)

```typescript
// MSW handler for quotes list — mocks enhanced response shape
// until backend BE-2/BE-3/BE-4 companion tasks add these fields to the real API
import { http, HttpResponse } from "msw";

const MOCK_QUOTES = [
  {
    id: "q-001",
    tenant_id: "t-001",
    customer_id: "c-001",
    customer_name: "Smith Electrical",   // ← backend gap BE-4
    site_id: "s-001",
    status_id: "s-draft",
    status_code: "draft",               // ← backend gap BE-3
    subtotal_cents: 185000,
    tax_cents: 14800,
    total_cents: 199800,
  },
  {
    id: "q-002",
    tenant_id: "t-001",
    customer_id: "c-002",
    customer_name: "Johnson Home Services",
    site_id: "s-002",
    status_id: "s-sent",
    status_code: "sent",
    subtotal_cents: 320000,
    tax_cents: 25600,
    total_cents: 345600,
  },
];

export const quotesListHandlers = [
  http.get("/api/v1/quotes", ({ request }) => {
    const url = new URL(request.url);
    const status = url.searchParams.get("status");
    const items = status
      ? MOCK_QUOTES.filter((q) => q.status_code === status)
      : MOCK_QUOTES;
    return HttpResponse.json(items);
  }),
];
```

Register this handler in `frontend/apps/web/src/mocks/handlers/index.ts`. Read that file first to understand the registration pattern.

---

### STEP 5: Create `useQuotes.ts` hook

**File**: `frontend/apps/web/src/features/quotes/hooks/useQuotes.ts`

Implement exactly per Design Doc **§F.2**:

```typescript
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

/** Current backend response shape — status_code and customer_name are backend gaps */
export interface QuoteListItem {
  id: string;
  tenant_id: string;
  customer_id: string;
  site_id: string;
  status_id: string;
  // status_code?: string;   ← add when backend BE-3 delivers
  // customer_name?: string; ← add when backend BE-4 delivers
  subtotal_cents: number;
  tax_cents: number;
  total_cents: number;
}

/** Enhanced shape returned by MSW mock; will match real API once backend tasks complete */
export interface QuoteListItemEnhanced extends QuoteListItem {
  status_code: string;
  customer_name: string;
}

export interface UseQuotesOptions {
  skip?: number;
  limit?: number;
}

export const QUOTES_QUERY_KEY = (skip: number, limit: number) =>
  ["quotes", skip, limit] as const;

export function useQuotes({ skip = 0, limit = 100 }: UseQuotesOptions = {}) {
  return useQuery({
    queryKey: QUOTES_QUERY_KEY(skip, limit),
    queryFn: async (): Promise<QuoteListItem[]> => {
      const res = await apiClient.get("/api/v1/quotes", {
        params: { skip, limit },
      });
      return res.data as QuoteListItem[];
    },
    staleTime: 60_000,
  });
}
```

---

### STEP 6: Create `QuotesPage.tsx` component

**File**: `frontend/apps/web/src/features/quotes/components/QuotesPage.tsx`

Requirements:
- **`<RoleGate permission="quotes.view">`** wraps all content (tech role sees nothing)
- Status filter pills: All, Draft, Pending Approval, Sent, Expired — client-side filter
- Table: Quote (link), Customer (name if available, else truncated ID), Status pill, Total
- MSW mock provides `status_code` and `customer_name` — component treats these as optional fields

```tsx
"use client";

import { useState, useMemo } from "react";
import { RoleGate } from "@pilot/ui/role-gate";
import { EmptyState, LoadingState, ErrorState } from "@pilot/ui/states";
import { useQuotes, QuoteListItemEnhanced } from "../hooks/useQuotes";

const PAGE_SIZE = 100;

const STATUS_FILTERS = [
  { label: "All", value: undefined },
  { label: "Draft", value: "draft" },
  { label: "Pending Approval", value: "pending_approval" },
  { label: "Sent", value: "sent" },
  { label: "Expired", value: "expired" },
];

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-neutral-100 text-neutral-700",
  pending_approval: "bg-alert-100 text-alert-700",
  sent: "bg-brand-100 text-brand-700",
  approved: "bg-margin-100 text-margin-700",
  expired: "bg-neutral-100 text-neutral-500",
};

function formatCents(cents: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(cents / 100);
}

export function QuotesPage() {
  return (
    <RoleGate permission="quotes.view">
      <QuotesPageContent />
    </RoleGate>
  );
}

function QuotesPageContent() {
  const [skip, setSkip] = useState(0);
  const [activeStatus, setActiveStatus] = useState<string | undefined>(undefined);
  const { data, isLoading, isError, refetch } = useQuotes({ skip, limit: PAGE_SIZE });

  const quotes = (data ?? []) as QuoteListItemEnhanced[];

  const filtered = useMemo(() => {
    if (!activeStatus) return quotes;
    return quotes.filter((q) =>
      q.status_code === activeStatus
    );
  }, [quotes, activeStatus]);

  if (isLoading) return <LoadingState type="inline" label="Loading quotes..." />;
  if (isError) return (
    <ErrorState
      type="server"
      title="Could not load quotes"
      onRetry={() => refetch()}
    />
  );

  if (quotes.length === 0 && skip === 0) {
    return (
      <EmptyState
        type="no-data"
        title="No quotes yet"
        description="Quotes will appear here once created."
      />
    );
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold text-neutral-900 mb-6">Quotes</h1>

      {/* Status filter pills */}
      <div className="flex flex-wrap gap-2 mb-4">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.label}
            onClick={() => setActiveStatus(f.value)}
            className={`px-3 py-1 rounded-full text-sm font-medium border transition-colors ${
              activeStatus === f.value
                ? "bg-brand-600 text-white border-brand-600"
                : "bg-white text-neutral-600 border-neutral-200 hover:border-brand-400"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          type="no-results"
          title="No quotes found"
          description={activeStatus ? `No ${activeStatus.replace("_", " ")} quotes.` : "No quotes yet."}
        />
      ) : (
        <>
          <div className="rounded-md border border-neutral-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-neutral-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-neutral-600">Quote ID</th>
                  <th className="px-4 py-3 text-left font-medium text-neutral-600">Customer</th>
                  <th className="px-4 py-3 text-left font-medium text-neutral-600">Status</th>
                  <th className="px-4 py-3 text-right font-medium text-neutral-600">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {filtered.map((q) => (
                  <tr key={q.id} className="hover:bg-neutral-50">
                    <td className="px-4 py-3">
                      <a href={`/quotes/${q.id}`} className="text-brand-600 hover:underline font-mono text-xs">
                        {q.id.slice(0, 8)}…
                      </a>
                    </td>
                    <td className="px-4 py-3 text-neutral-700">
                      {q.customer_name ?? (
                        <span className="text-neutral-400 font-mono text-xs">{q.customer_id.slice(0, 8)}…</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {q.status_code ? (
                        <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium capitalize ${STATUS_COLORS[q.status_code] ?? "bg-neutral-100 text-neutral-600"}`}>
                          {q.status_code.replace(/_/g, " ")}
                        </span>
                      ) : (
                        <span className="text-neutral-400 font-mono text-xs">{q.status_id.slice(0, 8)}…</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right text-neutral-700 font-medium">
                      {formatCents(q.total_cents)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {quotes.length === PAGE_SIZE && !activeStatus && (
            <button
              onClick={() => setSkip(skip + PAGE_SIZE)}
              className="mt-4 px-4 py-2 text-sm text-brand-600 border border-brand-200 rounded-md hover:bg-brand-50"
            >
              Load More
            </button>
          )}
        </>
      )}
    </div>
  );
}
```

---

### STEP 7: Update `quotes/page.tsx` route

```tsx
import { QuotesPage } from "@/features/quotes/components/QuotesPage";

export default function QuotesIndexPage() {
  return <QuotesPage />;
}
```

---

### STEP 8: Create `useInvoices.ts` hook

**File**: `frontend/apps/web/src/features/invoices/hooks/useInvoices.ts`

Implement exactly per Design Doc **§F.3**:

```typescript
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface InvoiceListItem {
  id: string;
  invoice_number: string;
  customer_id: string;
  site_id: string;
  status_id: string;
  status_code: string;
  issued_at: string | null;
  due_at: string | null;
}

export interface InvoiceListResponse {
  items: InvoiceListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface UseInvoicesOptions {
  status?: string;
  limit?: number;
  offset?: number;
}

export const INVOICES_QUERY_KEY = (opts: UseInvoicesOptions) =>
  ["invoices", opts] as const;

export function useInvoices({ status, limit = 50, offset = 0 }: UseInvoicesOptions = {}) {
  return useQuery({
    queryKey: INVOICES_QUERY_KEY({ status, limit, offset }),
    queryFn: async (): Promise<InvoiceListResponse> => {
      const res = await apiClient.get("/api/v1/invoices/", {
        params: { ...(status ? { status } : {}), limit, offset },
      });
      return res.data as InvoiceListResponse;
    },
    staleTime: 60_000,
  });
}
```

---

### STEP 9: Create `InvoicesPage.tsx` component

**File**: `frontend/apps/web/src/features/invoices/components/InvoicesPage.tsx`

Requirements:
- **`<RoleGate permission="invoices.view">`** wraps all content
- Status filter pills send `?status=` to the backend (server-side filter — invoices endpoint supports it)
- Table: invoice_number (link), customer_id (truncated), status_code pill, due_at
- Load More: offset-based, hidden when `items.length < limit`

```tsx
"use client";

import { useState } from "react";
import { RoleGate } from "@pilot/ui/role-gate";
import { EmptyState, LoadingState, ErrorState } from "@pilot/ui/states";
import { useInvoices } from "../hooks/useInvoices";

const PAGE_SIZE = 50;

const STATUS_FILTERS = [
  { label: "All", value: undefined },
  { label: "Draft", value: "draft" },
  { label: "Sent", value: "sent" },
  { label: "Paid", value: "paid" },
  { label: "Overdue", value: "overdue" },
];

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-neutral-100 text-neutral-700",
  sent: "bg-brand-100 text-brand-700",
  viewed: "bg-brand-100 text-brand-700",
  paid: "bg-margin-100 text-margin-700",
  partially_paid: "bg-alert-100 text-alert-700",
  overdue: "bg-fault-100 text-fault-700",
  void: "bg-neutral-100 text-neutral-500",
};

export function InvoicesPage() {
  return (
    <RoleGate permission="invoices.view">
      <InvoicesPageContent />
    </RoleGate>
  );
}

function InvoicesPageContent() {
  const [activeStatus, setActiveStatus] = useState<string | undefined>(undefined);
  const [offset, setOffset] = useState(0);
  const { data, isLoading, isError, refetch } = useInvoices({
    status: activeStatus,
    limit: PAGE_SIZE,
    offset,
  });

  const handleStatusChange = (status: string | undefined) => {
    setActiveStatus(status);
    setOffset(0);
  };

  if (isLoading) return <LoadingState type="inline" label="Loading invoices..." />;
  if (isError) return (
    <ErrorState
      type="server"
      title="Could not load invoices"
      onRetry={() => refetch()}
    />
  );

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-neutral-900">Invoices</h1>
        <span className="text-sm text-neutral-500">{total} total</span>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.label}
            onClick={() => handleStatusChange(f.value)}
            className={`px-3 py-1 rounded-full text-sm font-medium border transition-colors ${
              activeStatus === f.value
                ? "bg-brand-600 text-white border-brand-600"
                : "bg-white text-neutral-600 border-neutral-200 hover:border-brand-400"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {items.length === 0 ? (
        <EmptyState
          type="no-results"
          title="No invoices found"
          description={activeStatus ? `No ${activeStatus} invoices.` : "No invoices yet."}
        />
      ) : (
        <>
          <div className="rounded-md border border-neutral-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-neutral-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-neutral-600">Invoice #</th>
                  <th className="px-4 py-3 text-left font-medium text-neutral-600">Customer</th>
                  <th className="px-4 py-3 text-left font-medium text-neutral-600">Status</th>
                  <th className="px-4 py-3 text-left font-medium text-neutral-600">Due</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {items.map((inv) => (
                  <tr key={inv.id} className="hover:bg-neutral-50">
                    <td className="px-4 py-3">
                      <a href={`/invoices/${inv.id}`} className="text-brand-600 hover:underline font-medium">
                        {inv.invoice_number}
                      </a>
                    </td>
                    <td className="px-4 py-3 text-neutral-500 font-mono text-xs">
                      {inv.customer_id.slice(0, 8)}…
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium capitalize ${STATUS_COLORS[inv.status_code] ?? "bg-neutral-100 text-neutral-600"}`}>
                        {inv.status_code.replace(/_/g, " ")}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-neutral-600">
                      {inv.due_at ? new Date(inv.due_at).toLocaleDateString() : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {items.length === PAGE_SIZE && (
            <button
              onClick={() => setOffset(offset + PAGE_SIZE)}
              className="mt-4 px-4 py-2 text-sm text-brand-600 border border-brand-200 rounded-md hover:bg-brand-50"
            >
              Load More
            </button>
          )}
        </>
      )}
    </div>
  );
}
```

---

### STEP 10: Update `invoices/page.tsx` route

```tsx
import { InvoicesPage } from "@/features/invoices/components/InvoicesPage";

export default function InvoicesIndexPage() {
  return <InvoicesPage />;
}
```

---

### STEP 11: Create `NotificationsPage.tsx`

**File**: `frontend/apps/web/src/features/notifications-center/components/NotificationsPage.tsx`

**IMPORTANT**: Verify the exact return shape of `useInAppNotifications` before wiring:
```bash
cat frontend/packages/ui/src/hooks/useInAppNotifications.ts
```

Adjust prop names below to match the actual hook signature:

```tsx
"use client";

import { useInAppNotifications } from "@pilot/ui";
import { EmptyState, LoadingState } from "@pilot/ui/states";

export function NotificationsPage() {
  // Read useInAppNotifications.ts first — verify these are the correct return values
  const { notifications, unreadCount, isLoading, markRead, markAllRead } = useInAppNotifications();

  if (isLoading) return <LoadingState type="inline" label="Loading notifications..." />;

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-neutral-900">
          Notifications
          {unreadCount > 0 && (
            <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-brand-100 text-brand-700">
              {unreadCount} unread
            </span>
          )}
        </h1>
        {unreadCount > 0 && (
          <button
            onClick={() => markAllRead()}
            className="text-sm text-brand-600 hover:text-brand-800"
          >
            Mark all read
          </button>
        )}
      </div>

      {notifications.length === 0 ? (
        <EmptyState type="no-data" title="No notifications" description="You're all caught up." />
      ) : (
        <div className="space-y-1">
          {notifications.map((n) => (
            <div
              key={n.notification_id}
              className={`flex items-start gap-3 p-4 rounded-md border cursor-pointer transition-colors ${
                n.read_at
                  ? "border-neutral-100 bg-white text-neutral-500"
                  : "border-brand-100 bg-brand-50 text-neutral-900"
              }`}
              onClick={() => markRead(n.notification_id)}
            >
              {!n.read_at && <span className="mt-1.5 h-2 w-2 rounded-full bg-brand-600 flex-shrink-0" />}
              <div className="flex-1 min-w-0">
                <p className="text-sm">{n.body}</p>
                <p className="text-xs text-neutral-400 mt-1">
                  {new Date(n.created_at).toLocaleString()}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

---

### STEP 12: Update `notifications/page.tsx`

```tsx
import { NotificationsPage } from "@/features/notifications-center/components/NotificationsPage";

export default function NotificationsIndexPage() {
  return <NotificationsPage />;
}
```

---

### STEP 13: `/operations` redirect

```tsx
// frontend/apps/web/src/app/(authed)/operations/page.tsx
import { redirect } from "next/navigation";
export default function OperationsPage() {
  redirect("/settings/operations/field-operations");
}
```

---

### STEP 14: `/sync` redirect

```tsx
// frontend/apps/web/src/app/(authed)/sync/page.tsx
import { redirect } from "next/navigation";
export default function SyncPage() {
  redirect("/settings/sync-storage/background-sync");
}
```

---

## Test Implementation

### Unit Tests

**IMPORTANT — Add this test file first for `permissions.ts` changes (Step 0):**

**File**: `frontend/packages/ui/src/role-gate/__tests__/permissions-b3.test.ts`

```typescript
import { ROLE_PERMISSION_MAP } from "../permissions";

describe("BETA-B3 permission additions", () => {
  it("tech role has customers.view", () => {
    expect(ROLE_PERMISSION_MAP.tech).toContain("customers.view");
  });

  it("tech role does NOT have quotes.view", () => {
    expect(ROLE_PERMISSION_MAP.tech).not.toContain("quotes.view");
  });

  it("tech role does NOT have invoices.view", () => {
    expect(ROLE_PERMISSION_MAP.tech).not.toContain("invoices.view");
  });

  it("owner has all three view permissions", () => {
    expect(ROLE_PERMISSION_MAP.owner).toContain("customers.view");
    expect(ROLE_PERMISSION_MAP.owner).toContain("quotes.view");
    expect(ROLE_PERMISSION_MAP.owner).toContain("invoices.view");
  });

  it("office_staff has all three view permissions", () => {
    expect(ROLE_PERMISSION_MAP.office_staff).toContain("customers.view");
    expect(ROLE_PERMISSION_MAP.office_staff).toContain("quotes.view");
    expect(ROLE_PERMISSION_MAP.office_staff).toContain("invoices.view");
  });

  it("operator has all three view permissions", () => {
    expect(ROLE_PERMISSION_MAP.operator).toContain("customers.view");
    expect(ROLE_PERMISSION_MAP.operator).toContain("quotes.view");
    expect(ROLE_PERMISSION_MAP.operator).toContain("invoices.view");
  });
});
```

Then create per Design Doc §I.1:
- `useCustomers.test.ts`, `CustomersPage.test.tsx` (includes search filter test)
- `useQuotes.test.ts`, `QuotesPage.test.tsx` (includes status filter pills test + `quotes.view` RoleGate test)
- `useInvoices.test.ts`, `InvoicesPage.test.tsx` (includes status filter + RoleGate test)
- `NotificationsPage.test.tsx`

### Integration Tests

Create folder: `apps/web/__tests__/batch_beta_v1_b3/`

Per Design Doc §I.2:
- `customers.test.tsx` — happy path, search filters rows, empty state, error state, row links
- `quotes.test.tsx` — MSW mock data renders, status pills filter, tech role `<RoleGate>` blocks access, row links
- `invoices.test.tsx` — happy path, status filter pill changes `?status=` param, Load More, tech role blocked, row links
- `notifications.test.tsx` — list renders, unread badge, mark-read
- `redirects.test.tsx` — `/operations` → `/settings/operations/field-operations`; `/sync` → `/settings/sync-storage/background-sync`

### Accessibility

Per Design Doc §I.3 — add axe-core check to each of the 4 new page components:

```typescript
import { axe } from "jest-axe";

it("has no accessibility violations", async () => {
  const { container } = render(<CustomersPage />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

---

## Final Verification

```bash
cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter mobile build && pnpm --filter @pilot/ui lint && pnpm --filter web lint && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — BETA-B3

Update the `pilot-app-beta-fixes-v1-impl-plan.md` §9 Batch Completion Tracker:

- [ ] Pre-modification regression baseline captured
- [ ] `pnpm sync-api-types` run
- [ ] Design doc fully read before writing any code
- [ ] **STEP 0**: `permissions.ts` updated with `customers.view`, `quotes.view`, `invoices.view`
- [ ] **STEP 0**: `ROLE_PERMISSION_MAP` updated — tech has `customers.view` but NOT `quotes.view`/`invoices.view`
- [ ] **STEP 0**: `permissions.ts` unit tests pass (tech excluded from financial permissions)
- [ ] `useCustomers.ts` created with `apiClient`, correct query key
- [ ] `CustomersPage.tsx` includes search input with client-side filter across all name/email fields
- [ ] `/customers` route updated
- [ ] Quotes MSW handler created with `status_code` and `customer_name` in mock data
- [ ] MSW handler registered in `handlers/index.ts`
- [ ] `useQuotes.ts` created with `QuoteListItem` and `QuoteListItemEnhanced` types
- [ ] `QuotesPage.tsx` wraps content in `<RoleGate permission="quotes.view">`
- [ ] `QuotesPage.tsx` renders status filter pills with client-side filter
- [ ] `QuotesPage.tsx` renders `customer_name` when available, falls back to truncated `customer_id`
- [ ] `/quotes` route updated
- [ ] `useInvoices.ts` created with `status`, `limit`, `offset` params and `{items, total}` response shape
- [ ] `InvoicesPage.tsx` wraps content in `<RoleGate permission="invoices.view">`
- [ ] `InvoicesPage.tsx` sends `?status=` to backend (server-side filter)
- [ ] `InvoicesPage.tsx` Load More increments offset correctly
- [ ] `/invoices` route updated
- [ ] `useInAppNotifications` NOT recreated — existing hook used as-is
- [ ] `NotificationsPage.tsx` wired to actual `useInAppNotifications` prop names (read the hook before wiring)
- [ ] `/notifications` route updated
- [ ] `/operations` redirects to `/settings/operations/field-operations`
- [ ] `/sync` redirects to `/settings/sync-storage/background-sync`
- [ ] `/comms` page NOT modified
- [ ] All unit tests pass per §I.1 (including new permissions test)
- [ ] All integration tests pass per §I.2 (5 files in `batch_beta_v1_b3/`)
- [ ] axe-core zero violations on all 4 new page components
- [ ] Zero TypeScript errors
- [ ] Zero ESLint `no-hardcoded-design-values` warnings
- [ ] No regressions in pre-existing test suite
- [ ] Full verification command passes (`=== MVP FINAL VERIFICATION COMPLETE ===`)
- [ ] Companion backend tasks (BE-1 through BE-6) documented/tracked for Python Engineer
- [ ] Update this Definition of Done list with completion checks next to each item if completed
- [ ] Final test count (before/after) documented in impl plan tracker in the source plan
- [ ] Summary of work accomplished added to new sub-section in impl plan tracker in Section 9 in the source plan after the last batch entry
