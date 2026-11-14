# Batch Design: BETA-B3 — Web List/Index Pages

**Batch**: BETA-B3
**Author**: Pilot Architect
**Date**: 2026-06-04
**Output file**: `dev-docs/architecture-design/batch-designs/batch-beta-v1-fixes-b3-design.md`
**Implements**: `dev-docs/implementation-prompts/beta-b3-architect-design-session.md`
**Source issue**: `dev-docs/analysis/pilot-app-beta-fixes-v1-impl-plan.md` §8 BETA-B3
**React Engineer execution doc**: this file

> **Design Principle**: This document is PRD-driven. The PRD defines what the product must do — this is the source of truth. Current backend capabilities are measured against PRD requirements. When the backend falls short, the gap is documented as a backend spec item and called out explicitly — not silently dropped from the frontend design. Frontend components are designed against product requirements; backend gaps are surfaced as parallel Python Engineer work items.

---

## A. Input Read Summary

| Artifact | Location | Finding |
|---|---|---|
| `/customers/page.tsx` | `apps/web/src/app/(authed)/customers/page.tsx` | ✅ Pure stub — only `<h1>Customers</h1>` |
| `/quotes/page.tsx` | `apps/web/src/app/(authed)/quotes/page.tsx` | ✅ Pure stub — only `<h1>Quotes</h1>` |
| `/invoices/page.tsx` | `apps/web/src/app/(authed)/invoices/page.tsx` | ✅ Pure stub — only `<h1>Invoices</h1>` |
| `/comms/page.tsx` | `apps/web/src/app/(authed)/comms/page.tsx` | ⚠️ **NOT a stub** — full implementation exists (see §G) |
| `/notifications/page.tsx` | `apps/web/src/app/(authed)/notifications/page.tsx` | ✅ Pure stub — only `<h1>Notifications</h1>` |
| `/operations/page.tsx` | `apps/web/src/app/(authed)/operations/page.tsx` | ✅ Pure stub — only `<h1>Operations</h1>` |
| `/sync/page.tsx` | `apps/web/src/app/(authed)/sync/page.tsx` | ✅ Pure stub — only `<h1>Sync</h1>` |
| `features/` directory | `apps/web/src/features/` | No `customers/`, `quotes/`, or `invoices/` subfolders exist |
| Hooks search | `features/**/*.ts` grep for `useCustomers\|useQuotes\|useInvoices` | **0 results** — no hooks exist |
| `GET /api/v1/customers/` | `backend/openapi_schema_map.md` line 3888 | Verified — array response, `skip/limit` only, **no `?search=`** — backend gap |
| `GET /api/v1/quotes` | `backend/openapi_schema_map.md` line 11844 | Verified — array response, `skip/limit` only, **no status filter, no `status_code`, no `customer_name`** — backend gaps |
| `GET /api/v1/invoices/` | `backend/openapi_schema_map.md` line 6571 | Verified — paginated `{items, total, limit, offset}`, has `?status=` filter, `status_code` in response |
| `GET /api/v1/communications/recent` | `backend/openapi_schema_map.md` line 2584 | Verified — BETA-B1 endpoint, paginated `{items, total, page, page_size}` |
| `GET /api/v1/notifications/in-app/recent` | `backend/openapi_schema_map.md` line 9696 | Verified — `?limit=` param, returns `InAppNotification[]` |
| `packages/ui/src/index.ts` | `packages/ui/src/index.ts` | `EmptyState`, `LoadingState`, `ErrorState`, `RoleGate`, `useRequiresPermission`, `useInAppNotifications`, `NotificationCenterBell` all confirmed present |
| `permissions.ts` | `packages/ui/src/role-gate/permissions.ts` | **No `*.view` permission keys exist** — RBAC registry gap; action keys only (`customers.delete`, `invoices.approve`, etc.) — remediation required in this batch |
| Pattern reference | `features/profitability/components/ProfitabilityPage.tsx` | Pattern: page route imports feature-scoped page component; component calls hook via `apiClient` |
| Settings `/operations/` routes | `apps/web/src/app/(authed)/settings/operations/` | Has `page.tsx` + `field-operations/`, `margin-buckets/`, `profitability-rules/` sub-routes |
| Settings `/sync-storage/` routes | `apps/web/src/app/(authed)/settings/sync-storage/` | Has `page.tsx` + `background-sync/`, `offline-limits/`, `photos/`, `voice-capture/` sub-routes |
| PRD §3.3 CRM | `dev-docs/product-requirements/mvp-prd.md` | Customer list, search, and management features are core MVP CRM capability |
| PRD §3.5 RBAC | `dev-docs/product-requirements/mvp-prd.md` | Technician role explicitly excludes financial admin permissions; quotes and invoices are financial surfaces |
| PRD §3.10 Quotes | `dev-docs/product-requirements/mvp-prd.md` | Full quote lifecycle (draft → pending_approval → sent → expired) requires status-aware list filtering |

---

## B. Execution Order

| # | Surface | Component / File | Priority | Dependency Rationale |
|---|---|---|---|---|
| 0 | RBAC | `permissions.ts` — add `customers.view`, `quotes.view`, `invoices.view` | P0 | **Must complete before any page component wraps `<RoleGate>`** |
| 1 | Customers | `useCustomers.ts` hook | P1 | No dependencies — plain API list call |
| 2 | Customers | `CustomersPage.tsx` component | P1 | Depends on #0, #1 |
| 3 | Customers | `customers/page.tsx` route update | P1 | Depends on #2 |
| 4 | Invoices | `useInvoices.ts` hook | P1 | No dependencies — has richer response shape than quotes |
| 5 | Invoices | `InvoicesPage.tsx` component | P1 | Depends on #0, #4 |
| 6 | Invoices | `invoices/page.tsx` route update | P1 | Depends on #5 |
| 7 | Quotes | `useQuotes.ts` hook | P1 | No dependencies — built after invoices to leverage pattern |
| 8 | Quotes | `QuotesPage.tsx` component | P1 | Depends on #0, #7; uses MSW mock for enhanced response shape (see §D.2) |
| 9 | Quotes | `quotes/page.tsx` route update | P1 | Depends on #8 |
| 10 | Notifications | `NotificationsPage.tsx` component | P3 | Reuses existing `useInAppNotifications` hook — no new hook needed |
| 11 | Notifications | `notifications/page.tsx` route update | P3 | Depends on #10 |
| 12 | Operations | `operations/page.tsx` redirect | P3 | Pure Next.js redirect — no feature code |
| 13 | Sync | `sync/page.tsx` redirect | P3 | Pure Next.js redirect — no feature code |

> **`/comms` is excluded from this batch** — it is already fully implemented. See §G.

---

## C. New Routes

### C.1 Routes Being Updated (Stub → Real Content)

| Route | File Path | Auth Requirement | RBAC Gate |
|---|---|---|---|
| `/customers` | `apps/web/src/app/(authed)/customers/page.tsx` | Required (Cognito JWT via `(authed)` layout) | `customers.view` — all roles (owner, office_staff, tech, operator) |
| `/quotes` | `apps/web/src/app/(authed)/quotes/page.tsx` | Required | `quotes.view` — owner, office_staff, operator only; tech excluded |
| `/invoices` | `apps/web/src/app/(authed)/invoices/page.tsx` | Required | `invoices.view` — owner, office_staff, operator only; tech excluded |
| `/notifications` | `apps/web/src/app/(authed)/notifications/page.tsx` | Required | All authenticated users — notifications are personal and user-scoped |
| `/operations` | `apps/web/src/app/(authed)/operations/page.tsx` | Required | Redirect — no gate needed |
| `/sync` | `apps/web/src/app/(authed)/sync/page.tsx` | Required | Redirect — no gate needed |

### C.2 RBAC Gap — Missing View Permission Keys (Required Remediation in This Batch)

> **This is a PRD compliance gap to be resolved in BETA-B3 — not deferred to a future batch.**

**Finding**: `packages/ui/src/role-gate/permissions.ts` contains only action-level keys (`customers.delete`, `invoices.approve`, `comms.send`, etc.). It does not contain `customers.view`, `quotes.view`, or `invoices.view`.

**PRD requirement (§3.5)**: "The `technician` role has `voice.use` and `nec.calculate` permissions but explicitly excludes `integrations.manage` and **financial admin permissions**." Quotes and invoices expose pricing data (`total_cents`, `subtotal_cents`) and payment status — they are financial surfaces. The absence of `*.view` keys is an RBAC registry omission. It does **not** mean all roles should have unrestricted access; it means the registry must be updated.

**The React Engineer must add these keys to `permissions.ts` as part of BETA-B3.** This is a frontend-only change — no backend migration or Python Engineer involvement required for the frontend gate.

#### Required additions to `packages/ui/src/role-gate/permissions.ts`:

```typescript
// packages/ui/src/role-gate/permissions.ts — BETA-B3 additions required
export type PermissionKey =
  // ... all existing keys preserved verbatim ...
  | "customers.view"   // CRM list — all authenticated roles
  | "quotes.view"      // Financial surface — owner, office_staff, operator only
  | "invoices.view";   // Financial surface — owner, office_staff, operator only
```

#### Required additions to `ROLE_PERMISSION_MAP`:

| Permission | owner | office_staff | tech | operator |
|---|---|---|---|---|
| `customers.view` | ✅ | ✅ | ✅ | ✅ |
| `quotes.view` | ✅ | ✅ | ❌ | ✅ |
| `invoices.view` | ✅ | ✅ | ❌ | ✅ |

**Rationale for role assignments**:
- `customers.view` granted to `tech`: PRD §3.3 CRM — technicians access customer details for job context (contact details, site access instructions, hazard notes). Customer data is not financial data. Techs need it in the field.
- `quotes.view` / `invoices.view` denied to `tech`: PRD §3.5 explicitly excludes technicians from financial admin permissions. Quote totals and invoice billing data fall squarely within financial admin scope. The tech mobile app has no `/quotes` or `/invoices` routes — these are web-only owner/office surfaces.

**Parallel backend task**: Python Engineer must add `require_permission("quotes.list")` and `require_permission("invoices.list")` decorators to `GET /api/v1/quotes` and `GET /api/v1/invoices/` respectively to enforce the same access control server-side. This is a backend BETA-B3 companion task.

### C.3 Route Implementation Pattern

Follow the exact pattern from `reports/page.tsx`:

```tsx
// apps/web/src/app/(authed)/customers/page.tsx
import { CustomersPage } from "@/features/customers/components/CustomersPage";

export default function CustomersIndexPage() {
  return <CustomersPage />;
}
```

Page route files must remain **Server Components** (no `"use client"` at the route level). The `"use client"` directive belongs on the feature page component that uses TanStack Query hooks.

For gated surfaces (`/quotes`, `/invoices`), the feature page component wraps content in `<RoleGate>`:

```tsx
// apps/web/src/features/quotes/components/QuotesPage.tsx (excerpt)
"use client";
import { RoleGate } from "@pilot/ui/role-gate";

export function QuotesPage() {
  return (
    <RoleGate permission="quotes.view">
      {/* list content */}
    </RoleGate>
  );
}
```

---

## D. API Endpoint Consumption

### D.1 Customers

| Field | Value |
|---|---|
| **Endpoint** | `GET /api/v1/customers/` |
| **Auth** | Required |
| **Params** | `skip` (integer, default 0), `limit` (integer, default 100) |
| **Response shape** | Array: `Array<{id, tenant_id, type, display_name, first_name, last_name, company_name, email}>` |
| **Pagination type** | Offset-based (plain array — no `total` field in response) |
| **Search support** | ⚠️ **Backend gap** — `GET /api/v1/customers/` has no `?search=` param. Frontend MUST include a search input (basic CRM usability); use client-side name filter on the fetched list as interim until backend adds server-side search. |
| **Backend gap spec** | Python Engineer must add `?search=` query param to `GET /api/v1/customers/` — case-insensitive match across `display_name`, `first_name`, `last_name`, `company_name`, and `email`. Log as BETA-B3 companion task. |
| **New hook** | `useCustomers.ts` — create at `apps/web/src/features/customers/hooks/useCustomers.ts` |
| **TanStack Query key** | `["customers", skip, limit]` |
| **MSW handler required?** | No — current endpoint shape is sufficient for client-side search interim |

### D.2 Quotes

| Field | Value |
|---|---|
| **Endpoint** | `GET /api/v1/quotes` |
| **Auth** | Required |
| **Params** | `skip` (integer, default 0), `limit` (integer, default 100) |
| **Current response shape** | Array: `Array<{id, tenant_id, customer_id, site_id, status_id, subtotal_cents, tax_cents, total_cents}>` |
| **Pagination type** | Offset-based (plain array — no `total` field) |
| **Status filter support** | ⚠️ **Backend gap** — no `?status=` param. PRD §3.10 requires status-aware quote management (draft, pending_approval, sent, expired). Frontend MUST design with status filter pills; use client-side filtering as interim. |
| **Status code display** | ⚠️ **Backend gap** — list response returns `status_id` (UUID), not `status_code`. Frontend cannot display human-readable status without this field. |
| **Customer name in response** | ⚠️ **Backend gap** — only `customer_id` returned. The list page requires a customer column; frontend displays truncated customer_id as a fallback. |
| **Backend gap spec** | Python Engineer must: (1) Add `?status=` filter param to `GET /api/v1/quotes`; (2) Add `status_code` field to quotes list response schema; (3) Add `customer_name` (denormalized) to quotes list response schema. All three are required for a usable quotes list page. Log as BETA-B3 companion tasks. |
| **New hook** | `useQuotes.ts` — create at `apps/web/src/features/quotes/hooks/useQuotes.ts` |
| **TanStack Query key** | `["quotes", skip, limit]` |
| **MSW handler required?** | **Yes** — MSW handler must mock the enhanced response shape (including `status_code` and `customer_name`) so frontend development can proceed while the backend gaps are being closed. |

### D.3 Invoices

| Field | Value |
|---|---|
| **Endpoint** | `GET /api/v1/invoices/` |
| **Auth** | Required |
| **Params** | `status` (optional), `due_before` (optional), `due_after` (optional), `limit` (integer, default 50), `offset` (integer, default 0) |
| **Response shape** | `InvoiceListResponse: {items: Array<{id, invoice_number, customer_id, site_id, status_id, status_code, issued_at, due_at}>, total, limit, offset}` |
| **Pagination type** | Offset-based with `total` — supports proper Load More |
| **Status filter support** | ✅ `?status=` param exists — implement status filter pills |
| **Status code display** | ✅ `status_code` is available in list item — use for human-readable pill |
| **New hook** | `useInvoices.ts` — create at `apps/web/src/features/invoices/hooks/useInvoices.ts` |
| **TanStack Query key** | `["invoices", { status, limit, offset }]` |
| **MSW handler required?** | No — endpoint is complete and stable |

### D.4 Communications (comms)

**Status**: `/comms/page.tsx` is **already fully implemented** — no action required. See §G.

### D.5 Notifications

| Field | Value |
|---|---|
| **Endpoint** | `GET /api/v1/notifications/in-app/recent` |
| **Auth** | Required |
| **Params** | `limit` (integer, default 50) |
| **Response shape** | `InAppNotification[]` where `InAppNotification = {notification_id, category_id, body, deep_link_target, priority, created_at, read_at}` |
| **Existing hook** | `useInAppNotifications()` — **already exists** at `packages/ui/src/hooks/useInAppNotifications.ts`. **Do not create a duplicate.** |
| **TanStack Query key** | Managed internally by `useInAppNotifications` hook |
| **MSW handler required?** | No — endpoint is stable |
| **Reuse** | Import `useInAppNotifications` from `@pilot/ui` and `NotificationCenterBell` from `@pilot/ui` |

---

## E. Pattern Reuse Decisions

| Shared Component | Import Path | Surface | Props to Pass |
|---|---|---|---|
| `EmptyState` | `@pilot/ui/states` | Customers, Quotes, Invoices, Notifications | `type="list"`, `title`, `description` |
| `LoadingState` | `@pilot/ui/states` | Customers, Quotes, Invoices, Notifications | `type="inline"`, `label` |
| `ErrorState` | `@pilot/ui/states` | Customers, Quotes, Invoices, Notifications | `type="server"`, `title`, `description`, `onRetry` |
| `RoleGate` | `@pilot/ui/role-gate` | Quotes, Invoices | `permission="quotes.view"` / `permission="invoices.view"` |
| `useInAppNotifications` | `@pilot/ui` | Notifications | Called as hook — provides `notifications`, `unreadCount`, `markRead`, `markAllRead` |
| `NotificationCenterBell` | `@pilot/ui` | Notifications | `notifications`, `unreadCount`, `isConnected`, `onMarkRead`, `onMarkAllRead`, `onNotificationNavigate` |

> **No new shared components are being added to `packages/ui/`** in this batch. All new code lives in `apps/web/src/features/{surface}/` or `packages/ui/src/role-gate/permissions.ts`.

---

## F. Shared Module Interfaces

### F.1 `useCustomers()`

**Location**: `apps/web/src/features/customers/hooks/useCustomers.ts`

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
    staleTime: 60_000, // 1 minute
  });
}
```

**Note on search**: The hook fetches all customers up to `limit`. The `CustomersPage` component performs client-side filtering on `display_name`, `first_name`, `last_name`, `company_name`, and `email` fields using a controlled search input. When the backend adds `?search=` support (BETA-B3 companion task), the hook will be updated to pass the search param and disable client-side filtering.

**Example call**:
```typescript
const { data, isLoading, isError, refetch } = useCustomers();
```

---

### F.2 `useQuotes()`

**Location**: `apps/web/src/features/quotes/hooks/useQuotes.ts`

```typescript
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

/**
 * Current backend response shape — missing status_code and customer_name.
 * MSW mock must use QuoteListItemEnhanced shape until backend gaps are closed.
 */
export interface QuoteListItem {
  id: string;
  tenant_id: string;
  customer_id: string;
  site_id: string;
  status_id: string;
  // status_code: string;   ← backend gap — add when backend delivers
  // customer_name: string; ← backend gap — add when backend delivers
  subtotal_cents: number;
  tax_cents: number;
  total_cents: number;
}

/** Enhanced shape used by MSW mock and component until backend delivers */
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

**Example call**:
```typescript
const { data, isLoading, isError, refetch } = useQuotes();
```

---

### F.3 `useInvoices()`

**Location**: `apps/web/src/features/invoices/hooks/useInvoices.ts`

```typescript
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export type InvoiceStatusCode =
  | "draft"
  | "sent"
  | "viewed"
  | "partially_paid"
  | "paid"
  | "overdue"
  | "void";

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

**Example call**:
```typescript
const { data, isLoading, isError, refetch } = useInvoices({ status: "sent", limit: 50 });
```

---

## G. Open Questions Resolved

| Question | Decision |
|---|---|
| **Is `/comms/page.tsx` a stub?** | **NO.** Confirmed via direct file read — `/comms/page.tsx` has a complete implementation (154 lines) including `useQuery` with `GET /api/v1/communications/recent`, a full table UI, channel pills, status pills, customer links, and error/loading/empty states. This surface is **complete and excluded from BETA-B3**. The session prompt incorrectly listed it as a stub. |
| **Does `/comms` depend on BETA-B1?** | Yes — the endpoint `GET /api/v1/communications/recent` is flagged as a BETA-B1 addition in `openapi_schema_map.md`. The existing implementation in `comms/page.tsx` already calls it. No action needed. |
| **Should `/operations` get its own page or redirect?** | **Redirect** to `/settings/operations/field-operations`. Settings pages exist at `apps/web/src/app/(authed)/settings/operations/` with full sub-routes (`field-operations/`, `margin-buckets/`, `profitability-rules/`). A top-level `/operations` redirect is cleanest for MVP. |
| **Should `/sync` get its own page or redirect?** | **Redirect** to `/settings/sync-storage/background-sync`. Settings pages exist at `apps/web/src/app/(authed)/settings/sync-storage/` with full sub-routes. Same rationale as `/operations`. |
| **Are `*.view` permission keys needed?** | **Yes — required in this batch.** `permissions.ts` is missing `customers.view`, `quotes.view`, and `invoices.view`. PRD §3.5 explicitly excludes technicians from financial admin permissions. Adding these keys to `permissions.ts` is a **required deliverable of BETA-B3**, not a future enhancement. See §C.2 for full spec. |
| **Does `/notifications` need a new hook?** | **No.** `useInAppNotifications()` already exists at `packages/ui/src/hooks/useInAppNotifications.ts` and hits `GET /api/v1/notifications/in-app/recent`. The `NotificationsPage` component should call this hook directly. |
| **Pagination strategy?** | **Load More** (offset-based) for all three P1 surfaces. Invoices has a proper `{items, total, limit, offset}` shape — Load More is straightforward. Customers and Quotes return plain arrays without `total` — detect end-of-list by checking `items.length < limit`. Do not implement infinite scroll (requires more complex intersection observer logic not needed for beta). |
| **Search/filter for Customers?** | **Design with search; use client-side filter as interim.** `GET /api/v1/customers/` has no `?search=` param — this is a backend gap, not a product decision to omit search. The `CustomersPage` must render a search input and perform client-side filter on the fetched list. Python Engineer must add server-side `?search=` in the BETA-B3 companion backend task. |
| **Status filter for Quotes?** | **Design with status filter pills; use client-side filtering as interim.** `GET /api/v1/quotes` has no `?status=` param and returns no `status_code` — both are backend gaps. PRD §3.10 requires status-aware quote management. `QuotesPage` must render status pills (All, Draft, Pending Approval, Sent, Expired); use client-side filter against the fetched list. MSW handler must mock `status_code` and `customer_name`. Python Engineer must add `?status=`, `status_code`, and `customer_name` to the quotes list endpoint. |
| **Customer name on quotes list?** | **Design with customer column; use truncated ID as fallback.** The quotes list API only returns `customer_id` — this is a backend gap. The `QuotesPage` renders a "Customer" column; when backend delivers `customer_name` it will display naturally; until then it displays `customer_id` first 8 chars. Python Engineer must add `customer_name` to the quotes list response in the BETA-B3 companion backend task. |
| **Status filter for Invoices?** | **Implement server-side filter.** `GET /api/v1/invoices/` has `?status=` param and `status_code` in list response — no backend gap here. Build status filter pills: All, Draft, Sent, Paid, Overdue. |

---

## H. External Dependency Status

| Surface | Dependency | Status |
|---|---|---|
| `/customers` | `GET /api/v1/customers/` | ✅ Stable — WS1 backend complete; search is client-side interim |
| `/quotes` | `GET /api/v1/quotes` — **enhanced shape** | ⚠️ Companion backend task required: add `?status=`, `status_code`, `customer_name`; MSW handler covers gap |
| `/invoices` | `GET /api/v1/invoices/` | ✅ Stable — WS1 backend complete |
| `/comms` | DONE — excluded from batch | N/A |
| `/notifications` | `GET /api/v1/notifications/in-app/recent` | ✅ Stable — WS1 backend complete |
| `/operations` | Next.js redirect only | No backend dependency |
| `/sync` | Next.js redirect only | No backend dependency |
| `permissions.ts` update | Frontend-only change | ✅ No backend dependency — React Engineer can complete this independently |
| Backend RBAC decorators | `require_permission()` on quotes/invoices list endpoints | ⚠️ Python Engineer companion task — must be consistent with frontend `<RoleGate>` |
| All P1 surfaces | `pnpm sync-api-types` currency | Must be run before implementation to ensure `@pilot/shared-types` reflects current backend types |
| All surfaces | `@pilot/shared-api` `apiClient` | Already used by `useProfitability` — no new setup required |

---

## I. Test Plan

### I.1 Unit Tests

| Surface | Test File | Coverage |
|---|---|---|
| `useCustomers` | `apps/web/src/features/customers/hooks/__tests__/useCustomers.test.ts` | Returns data on success; throws on API error; query key is stable |
| `useQuotes` | `apps/web/src/features/quotes/hooks/__tests__/useQuotes.test.ts` | Returns data on success; throws on API error; query key is stable |
| `useInvoices` | `apps/web/src/features/invoices/hooks/__tests__/useInvoices.test.ts` | Returns paginated shape; status filter passed as param; detects end-of-list |
| `CustomersPage` | `apps/web/src/features/customers/components/__tests__/CustomersPage.test.tsx` | Renders loading state; renders list; renders empty state; renders error state; search input filters list client-side |
| `QuotesPage` | `apps/web/src/features/quotes/components/__tests__/QuotesPage.test.tsx` | Renders loading state; renders list with MSW mock data; renders empty state; renders error state; status pills filter list client-side; `quotes.view` gate hides content from `tech` role |
| `InvoicesPage` | `apps/web/src/features/invoices/components/__tests__/InvoicesPage.test.tsx` | Renders loading state; renders list; renders empty state; renders error state; status filter pills toggle; `invoices.view` gate hides content from `tech` role |
| `NotificationsPage` | `apps/web/src/features/notifications-center/components/__tests__/NotificationsPage.test.tsx` | Renders unread count; renders notification list; mark-read interaction |
| `permissions.ts` additions | `packages/ui/src/role-gate/__tests__/permissions.test.ts` | `tech` role does NOT have `quotes.view` or `invoices.view`; `tech` role DOES have `customers.view`; owner/office_staff/operator have all three |

### I.2 Integration Tests

**Location**: `apps/web/__tests__/batch_beta_v1_b3/`

| File | Surface | Coverage |
|---|---|---|
| `customers.test.tsx` | `/customers` | Primary flow (list renders); search input filters visible rows; empty state when API returns `[]`; error state when API returns 500; row links to `/customers/[id]` |
| `quotes.test.tsx` | `/quotes` | Primary flow (list renders with MSW mock); status filter pill filters displayed rows; empty state; error state; row links to `/quotes/[id]`; tech role sees empty/redirect (RoleGate) |
| `invoices.test.tsx` | `/invoices` | Primary flow (list renders); status filter pill sends `?status=` param; "Load More" increments offset; row links to `/invoices/[id]`; empty state; error state; tech role sees empty/redirect (RoleGate) |
| `notifications.test.tsx` | `/notifications` | List renders with unread count badge; mark-read updates list; empty state when no notifications |
| `redirects.test.tsx` | `/operations`, `/sync` | `/operations` redirects to `/settings/operations/field-operations`; `/sync` redirects to `/settings/sync-storage/background-sync` |

### I.3 Accessibility

**Requirement**: Every new surface in this batch must pass an axe-core accessibility check as part of the integration test suite.

```typescript
import { axe } from "jest-axe";

it("has no accessibility violations", async () => {
  const { container } = render(<CustomersPage />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

Apply this pattern to: `CustomersPage`, `QuotesPage`, `InvoicesPage`, `NotificationsPage`.

---

## Appendix: Component File Tree

The following files are **new** (confirmed absent via directory listing and hook grep):

```
packages/ui/src/role-gate/
└── permissions.ts                      ← UPDATE — add customers.view, quotes.view, invoices.view

apps/web/src/features/
├── customers/                          ← NEW directory
│   ├── hooks/
│   │   └── useCustomers.ts             ← NEW
│   └── components/
│       └── CustomersPage.tsx           ← NEW
├── quotes/                             ← NEW directory
│   ├── hooks/
│   │   └── useQuotes.ts                ← NEW
│   └── components/
│       └── QuotesPage.tsx              ← NEW
├── invoices/                           ← NEW directory
│   ├── hooks/
│   │   └── useInvoices.ts              ← NEW
│   └── components/
│       └── InvoicesPage.tsx            ← NEW
└── notifications-center/               ← EXISTS (has types.ts)
    └── components/
        └── NotificationsPage.tsx       ← NEW (components/ dir does not exist yet)

apps/web/src/app/(authed)/
├── customers/page.tsx                  ← UPDATE (replace stub with feature import)
├── quotes/page.tsx                     ← UPDATE (replace stub with feature import)
├── invoices/page.tsx                   ← UPDATE (replace stub with feature import)
├── notifications/page.tsx              ← UPDATE (replace stub with feature import)
├── operations/page.tsx                 ← UPDATE (replace stub with Next.js redirect)
└── sync/page.tsx                       ← UPDATE (replace stub with Next.js redirect)

apps/web/__tests__/batch_beta_v1_b3/   ← NEW directory
├── customers.test.tsx
├── quotes.test.tsx
├── invoices.test.tsx
├── notifications.test.tsx
└── redirects.test.tsx
```

**The following file is confirmed complete and requires NO changes:**
- `apps/web/src/app/(authed)/comms/page.tsx` — fully implemented (154 lines)

---

## Pre-Implementation Quality Gates

- [x] Every component listed as "new" was confirmed absent via `list_files` and `search_files` grep
- [x] Every API endpoint path verified from `openapi_schema_map.md` — no invented paths
- [x] Backend gaps for customers search, quotes status filter, quotes status_code, and quotes customer_name are explicitly called out as companion backend tasks — NOT silently dropped from frontend design
- [x] Permission keys `customers.view`, `quotes.view`, `invoices.view` are specified additions to `permissions.ts` — required deliverable of this batch, not future enhancement
- [x] RBAC role assignments grounded in PRD §3.5 — technician exclusion from financial surfaces is PRD-mandated
- [x] Every shared component import resolves to a confirmed export in `packages/ui/src/index.ts`
- [x] P3 surfaces (`/notifications`, `/operations`, `/sync`) have clear decisions — not TBD
- [x] `/comms` correctly identified as **already complete** — excluded from scope
- [x] `/operations` and `/sync` redirect targets verified by checking actual settings route directories
- [x] `useInAppNotifications` confirmed to already exist — no duplicate hook will be created
- [x] MSW handler requirement called out for quotes — frontend development can proceed before backend gaps are closed
- [x] Implementation order (§B) is feasible: permission keys (step 0) must be done first; P1 surfaces are then independent of each other; P3 notifications reuses an existing hook and can be built any time
