# Batch FE-B18 Design — Customer Create/Edit + Site Management + Customer Detail

**Batch**: FE-B18 (Frontend — React Engineer only)  
**Date**: June 16, 2026  
**Author**: Pilot Architect  
**Status**: DESIGN COMPLETE — Ready for implementation  
**Reference gap analysis**: `dev-docs/analysis/pilot-app-pre-wkstm-3-mvp-ui-api-gap-analysis.md` §1.1, §1.3, §1.18  
**Prerequisite**: B17 Part A complete + `pnpm sync-api-types` run (adds `mobile_phone` to `CustomerResponse`)

---

## Overview

FE-B18 builds out the complete customer management surface on the web app:
1. **"Add Customer" button + create modal** on the `/customers` list page
2. **Customer Overview tab** — full detail display of all CustomerResponse fields
3. **Customer Sites tab** — site list with add/edit site form
4. **Customer Quotes sub-list** — read-only quotes for this customer
5. **Customer Jobs sub-list** — read-only jobs for this customer (basic)
6. **Customer Invoices sub-list** — read-only invoices for this customer (basic)
7. **Edit Customer drawer** on the Overview tab
8. **Customer name in layout header** (replace hardcoded "Customer" with actual name)

No backend changes are needed — all required CRUD endpoints already exist.

---

## A. Input Read Summary

| Input | What was read | Key finding |
|---|---|---|
| PRD §3.3 CRM features | Customer create/edit, multi-site, payment methods, lifecycle | Payment method vaulting deferred to FE-B22; sites are MVP |
| `mvp-arch.md` §16 patterns | `<LoadingState>`, `<ErrorState>`, `<EmptyState>`, `<RoleGate>`, optimistic UI | Use existing shared components — do not recreate |
| `gap-analysis.md` §1.1, §1.3, §1.18 | No create form, "coming soon" detail, no site management | All three gaps must be closed in this batch |
| `backend/api/routes/customers.py` | `_create_customer_impl`, `_update_customer_impl`, `_list_customers_impl`, `_get_customer_impl`, payment method endpoints | All CRUD exists; PATCH uses `CustomerCreate` schema (not a separate `CustomerUpdate`) |
| `backend/api/routes/sites.py` | `_create_site_impl`, `_list_sites_impl`, `_get_site_impl`, `_update_site_impl` | Site list supports `?customer_id=` filter |
| `backend/api/schemas/schemas.py` lines 34–142 | `CustomerCreate`, `CustomerResponse`, `SiteCreate`, `SiteResponse`, `PaymentMethodResponse` | `CustomerResponse` has `mobile_phone` (after B17); `SiteResponse` has nested `address` |
| Live DB `customer` table | 27 columns confirmed | `type` defaults to `'person'`, `preferred_contact_channel` defaults to `'sms'`, SMS consent fields present |
| Live DB `site` table | 15 columns confirmed | `gate_code`, `access_instructions`, `hazard_notes` are PRD §3.3 structured access fields |
| `customers/[id]/layout.tsx` | Tab bar: Overview, Jobs, Quotes, Comms, Invoices — shell only, "Customer" hardcoded | Need to fetch customer name and pass to layout |
| `features/customers/hooks/useCustomers.ts` | TanStack Query hook exists; `CustomerListItem` lacks `mobile_phone` (updated after sync-api-types) | Query key: `["customers", skip, limit]` |
| `mocks/handlers/index.ts` | No dedicated customer CRUD MSW handler file exists | Must create `customerHandlers.ts` and register in barrel |
| `openapi_schema_map.md` (verified) | `GET/POST /api/v1/customers/`, `GET/PATCH/DELETE /api/v1/customers/{id}`, `GET /api/v1/jobs/`, `GET /api/v1/invoices/` | Jobs endpoint needs verification: check if `?customer_id=` filter is supported (Pre-Work step in prompt) |

---

## B. Migration Plan

**No Alembic migrations required.** No DB schema changes — all columns exist on the live `customer` and `site` tables. No new backend code needed.

**No new backend endpoints required.** All CRUD endpoints exist:
- `POST /api/v1/customers/` ✅
- `GET /api/v1/customers/` ✅
- `GET /api/v1/customers/{id}` ✅
- `PATCH /api/v1/customers/{id}` ✅
- `DELETE /api/v1/customers/{id}` ✅
- `POST /api/v1/sites/` ✅
- `GET /api/v1/sites/?customer_id={id}` ✅
- `PATCH /api/v1/sites/{id}` ✅

**Open pre-work verification needed** (React Engineer must run before coding):
```bash
# Verify jobs endpoint supports customer_id filter
python3 -c "
import json
spec = json.load(open('openapi.json'))
jobs_get = spec['paths'].get('/api/v1/jobs/', {}).get('get', {})
params = [p['name'] for p in jobs_get.get('parameters', [])]
print('Jobs GET params:', params)
"

# Verify invoices endpoint supports customer_id filter
python3 -c "
import json
spec = json.load(open('openapi.json'))
inv_get = spec['paths'].get('/api/v1/invoices/', {}).get('get', {})
params = [p['name'] for p in inv_get.get('parameters', [])]
print('Invoices GET params:', params)
"
```

If `customer_id` is not in the jobs params: the Jobs tab renders a deferred placeholder ("Full job management available in the Jobs module — coming in FE-B21") rather than breaking.  
If `customer_id` is not in the invoices params: same deferred placeholder approach for Invoices tab.

---

## C. Execution Order

| # | Task | Files | Dependency |
|---|---|---|---|
| 1 | Create `customerHandlers.ts` MSW mock + register in `index.ts` | `mocks/handlers/customerHandlers.ts`, `mocks/handlers/index.ts` | None — first step unblocks all tests |
| 2 | Create `useCustomer` (single customer fetch) hook | `features/customers/hooks/useCustomer.ts` | 1 |
| 3 | Create `useCreateCustomer` mutation hook | `features/customers/hooks/useCreateCustomer.ts` | 1 |
| 4 | Create `useUpdateCustomer` mutation hook | `features/customers/hooks/useUpdateCustomer.ts` | 1 |
| 5 | Create `useCustomerSites` hook | `features/customers/hooks/useCustomerSites.ts` | 1 |
| 6 | Create `useCreateSite` + `useUpdateSite` mutation hooks | `features/customers/hooks/useCreateSite.ts`, `useUpdateSite.ts` | 1 |
| 7 | Create `CustomerForm` shared form component | `features/customers/components/CustomerForm.tsx` | 3, 4 |
| 8 | Create `CreateCustomerModal` | `features/customers/components/CreateCustomerModal.tsx` | 7 |
| 9 | Add "Add Customer" button to `CustomersPage` + wire modal | `features/customers/components/CustomersPage.tsx` | 8 |
| 10 | Create `CustomerOverviewTab` | `features/customers/components/CustomerOverviewTab.tsx` | 2, 4 |
| 11 | Wire `customers/[id]/page.tsx` to `CustomerOverviewTab` | `app/(authed)/customers/[id]/page.tsx` | 10 |
| 12 | Update `customers/[id]/layout.tsx` to show customer name | `app/(authed)/customers/[id]/layout.tsx` | 2 |
| 13 | Create `SiteForm` + `SiteListPanel` | `features/customers/components/SiteListPanel.tsx`, `SiteForm.tsx` | 5, 6 |
| 14 | Wire `customers/[id]/sites` to `SiteListPanel` (new sub-route) | `app/(authed)/customers/[id]/sites/page.tsx` — add "Sites" to tab bar | 13 |
| 15 | Build `CustomerQuotesList` (read-only, per-customer) | `features/customers/components/CustomerQuotesList.tsx` | 1 |
| 16 | Wire `customers/[id]/quotes/page.tsx` | `app/(authed)/customers/[id]/quotes/page.tsx` | 15 |
| 17 | Build `CustomerJobsList` (read-only, per-customer) or deferred placeholder | `features/customers/components/CustomerJobsList.tsx` | Pre-work verification |
| 18 | Wire `customers/[id]/jobs/page.tsx` | `app/(authed)/customers/[id]/jobs/page.tsx` | 17 |
| 19 | Build `CustomerInvoicesList` (read-only, per-customer) or deferred placeholder | `features/customers/components/CustomerInvoicesList.tsx` | Pre-work verification |
| 20 | Wire `customers/[id]/invoices/page.tsx` | `app/(authed)/customers/[id]/invoices/page.tsx` | 19 |
| 21 | Write unit + integration tests | `features/customers/__tests__/`, `__tests__/batch_fe_b18/` | All above |
| 22 | `pnpm build` + `pnpm test` full verification | — | 21 |

---

## D. New API Endpoints

**None required.** All endpoints already exist. The React Engineer will consume:

| Hook | Endpoint | Method | Auth / RBAC |
|---|---|---|---|
| `useCustomer` | `GET /api/v1/customers/{id}` | GET | JWT, `customers.view` |
| `useCreateCustomer` | `POST /api/v1/customers/` | POST | JWT, `customers.create` |
| `useUpdateCustomer` | `PATCH /api/v1/customers/{id}` | PATCH | JWT, `customers.edit` |
| `useCustomerSites` | `GET /api/v1/sites/?customer_id={id}` | GET | JWT, `sites.view` |
| `useCreateSite` | `POST /api/v1/sites/` | POST | JWT, `sites.create` |
| `useUpdateSite` | `PATCH /api/v1/sites/{id}` | PATCH | JWT, `sites.edit` |
| `useQuotes` (existing) | `GET /api/v1/quotes/?customer_id={id}` | GET | JWT, `quotes.view` |
| `useJobs` (new or existing) | `GET /api/v1/jobs/?customer_id={id}` | GET | JWT, `jobs.view` |
| `useInvoices` (existing) | `GET /api/v1/invoices/?customer_id={id}` | GET | JWT, `invoices.view` |

---

## E. Pattern Reuse Decisions

| Pattern (per `mvp-arch.md` §16) | Applied in FE-B18 |
|---|---|
| `<LoadingState>`, `<ErrorState>`, `<EmptyState>` from `@pilot/ui/states` | All data-driven tabs and modals use these for loading/error/empty states |
| `<RoleGate permission="...">` from `@pilot/ui/role-gate` | "Add Customer" button and "Edit" actions gated to `customers.create`/`customers.edit` |
| Optimistic UI with pending badges | `useCreateCustomer` / `useUpdateCustomer` mutations use TanStack Query `onMutate` for optimistic list updates |
| `apiClient` (never raw `fetch()`) | All hooks use `apiClient` from `@pilot/shared-api` |
| `retry: false` on QueryClient | All test wrappers use `retry: false` |

---

## F. Shared Module Interfaces

### F.1 `useCustomer` Hook

```typescript
// apps/web/src/features/customers/hooks/useCustomer.ts
export function useCustomer(customerId: string | undefined) {
  return useQuery({
    queryKey: ['customer', customerId],
    queryFn: async (): Promise<CustomerResponse> => {
      const res = await apiClient.get(`/api/v1/customers/${customerId}`);
      return res.data as CustomerResponse;
    },
    enabled: !!customerId,
    staleTime: 60_000,
  });
}
```

### F.2 `useCreateCustomer` Mutation

```typescript
// apps/web/src/features/customers/hooks/useCreateCustomer.ts
export function useCreateCustomer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: CustomerCreateRequest): Promise<CustomerResponse> => {
      const res = await apiClient.post('/api/v1/customers/', data);
      return res.data as CustomerResponse;
    },
    onSuccess: () => {
      // Invalidate customer list queries — exact key depends on active skip/limit
      void queryClient.invalidateQueries({ queryKey: ['customers'] });
    },
  });
}
```

### F.3 `useUpdateCustomer` Mutation

```typescript
// apps/web/src/features/customers/hooks/useUpdateCustomer.ts
export function useUpdateCustomer(customerId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: CustomerUpdateRequest): Promise<CustomerResponse> => {
      const res = await apiClient.patch(`/api/v1/customers/${customerId}`, data);
      return res.data as CustomerResponse;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['customer', customerId] });
      void queryClient.invalidateQueries({ queryKey: ['customers'] });
    },
  });
}
```

### F.4 `useCustomerSites` Hook

```typescript
// apps/web/src/features/customers/hooks/useCustomerSites.ts
export function useCustomerSites(customerId: string | undefined) {
  return useQuery({
    queryKey: ['customer-sites', customerId],
    queryFn: async (): Promise<SiteResponse[]> => {
      const res = await apiClient.get('/api/v1/sites/', {
        params: { customer_id: customerId },
      });
      return res.data as SiteResponse[];
    },
    enabled: !!customerId,
    staleTime: 60_000,
  });
}
```

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| **Does the customer detail layout need to fetch the customer?** | Yes — currently hardcodes "Customer" as the heading. The layout is a server component; it should receive `customerId` from params and either (a) fetch customer name server-side, OR (b) pass `customerId` to `CustomerOverviewTab` which fetches client-side and updates the title via a `useEffect`. Given Next.js App Router, the cleanest approach is to pass `customerId` to a `CustomerDetailHeader` client component that uses `useCustomer` and renders the name. The layout itself stays a server component. |
| **Should "Edit Customer" be an inline form on Overview or a slide-out drawer?** | Inline edit toggle on the Overview tab — simpler to implement, sufficient for MVP. No separate drawer needed. The Overview tab shows view mode by default; an "Edit" button (RBAC: `customers.edit`) toggles into an inline edit form using the same `CustomerForm` component. |
| **Should Sites be its own tab or part of Overview?** | Its own tab. The existing layout has Overview/Jobs/Quotes/Comms/Invoices — add "Sites" between Overview and Jobs. The layout already supports adding more tabs. |
| **Payment method vaulting — in scope for B18?** | No. Payment method vaulting requires Stripe Elements (PCI-compliant card collection). Deferred to FE-B22 alongside the full invoice payment flow. The Overview tab will show existing vaulted methods (read-only) if the `PaymentMethodResponse` list can be fetched, but no add/delete UI in B18. |
| **Customer Jobs tab — if `?customer_id=` not supported?** | If `GET /api/v1/jobs/` does not support `?customer_id=` filtering (verify in pre-work), render a `<CustomerTabDeferredState>` with message "Full job details available in the Jobs module" + link to `/schedule`. Do not 404 or error — the route exists, it shows a helpful deferred state. |
| **Customer Invoices tab — if `?customer_id=` not supported?** | Same deferred-state approach. The Invoices tab will become fully functional in FE-B22 when `POST /api/v1/invoices/` and the invoice detail surface are built. |
| **Should `CustomersPage` use server-side search now that BE-1 (search param) was added in B17?** | If B17 Part A added `?search=` to `GET /api/v1/customers/`, update `useCustomers` to accept a `search` param and pass it. Remove the client-side `useMemo` filter from `CustomersPage`. If not added in B17, leave client-side filter as-is — the comment in the hook already documents this. Pre-work: check `openapi_schema_map.md`. |

---

## H. Surface Mockup Reference

**Platform**: Web only (`apps/web`)  
**No mobile changes in this batch.**

### H.1 `/customers` List Page

```
┌─────────────────────────────────────────────────────────────┐
│  Customers                            [+ Add Customer]      │
│  ─────────────────────────────────────────────────────────  │
│  [Search customers...]                          42 of 42    │
│                                                             │
│  Name             Type        Email                         │
│  Johnson Elec.    Company     —                            │
│  Smith, Tom       Person      tom@smith.example.com                 │
└─────────────────────────────────────────────────────────────┘
```

- "Add Customer" button: `<RoleGate permission="customers.create">` wrapper; opens `<CreateCustomerModal>`
- `CreateCustomerModal` has type selector (Person vs Company), then conditional name fields (first/last for person; company name for company), email, mobile phone, optional notes

### H.2 Customer Detail — Overview Tab

```
┌─────────────────────────────────────────────────────────────┐
│  Customers / Johnson Electrical Co.                         │
│  Overview | Sites | Jobs | Quotes | Comms | Invoices        │
│  ─────────────────────────────────────────────────────────  │
│  [Edit Customer]                                            │
│                                                             │
│  Type: Company                                              │
│  Display Name: Johnson Electrical Co.                       │
│  Email: johnson@example.com                                 │
│  Phone: (555) 123-4567                                      │
│  SMS: Opted in                                              │
│  Preferred channel: SMS                                     │
└─────────────────────────────────────────────────────────────┘
```

- Edit Customer button: `<RoleGate permission="customers.edit">` — toggles Overview into edit mode using `CustomerForm`
- SMS status shown as badge (opted in / opted out)

### H.3 Customer Detail — Sites Tab

```
┌─────────────────────────────────────────────────────────────┐
│  Sites                                    [+ Add Site]      │
│  ─────────────────────────────────────────────────────────  │
│  Main Office                                                │
│  123 Main St, Austin TX                                     │
│  Gate: #1234  [Edit]                                        │
│                                                             │
│  Warehouse                                                  │
│  456 Industrial Dr                                          │
│  Access: Ring bell at north entrance  [Edit]                │
└─────────────────────────────────────────────────────────────┘
```

- Each site card shows: name, address (from nested `SiteResponse.address`), `gate_code`, first 80 chars of `access_instructions`
- "Add Site" button: opens `SiteForm` modal (inline or drawer)
- "Edit" button per site: opens same `SiteForm` pre-filled

### H.4 Customer Detail — Jobs / Quotes / Invoices Tabs (read-only lists)

All three follow the same pattern:
- Show a simple table of items for this customer
- Each row links to the relevant detail page (`/quotes/[id]`, `/jobs/[id]` when built)
- If `?customer_id=` filter not supported: deferred-state component with helpful message

---

## I. Component Manifest

| Component | Path | New or Modify | Notes |
|---|---|---|---|
| `CreateCustomerModal` | `features/customers/components/CreateCustomerModal.tsx` | **New** | Modal shell + CustomerForm |
| `CustomerForm` | `features/customers/components/CustomerForm.tsx` | **New** | Shared form for create + edit; type selector conditionally shows person vs company fields |
| `CustomerOverviewTab` | `features/customers/components/CustomerOverviewTab.tsx` | **New** | View/edit toggle; uses useCustomer + useUpdateCustomer |
| `CustomerDetailHeader` | `features/customers/components/CustomerDetailHeader.tsx` | **New** | Client component — renders customer name in layout header |
| `SiteListPanel` | `features/customers/components/SiteListPanel.tsx` | **New** | List of sites + AddSiteButton; uses useCustomerSites |
| `SiteForm` | `features/customers/components/SiteForm.tsx` | **New** | Add/edit site form modal; uses useCreateSite + useUpdateSite |
| `CustomerQuotesList` | `features/customers/components/CustomerQuotesList.tsx` | **New** | Read-only quotes filtered by customer_id |
| `CustomerJobsList` | `features/customers/components/CustomerJobsList.tsx` | **New** | Read-only jobs filtered by customer_id (or DeferredState) |
| `CustomerInvoicesList` | `features/customers/components/CustomerInvoicesList.tsx` | **New** | Read-only invoices filtered by customer_id (or DeferredState) |
| `CustomerTabDeferredState` | `features/customers/components/CustomerTabDeferredState.tsx` | **New** | Reusable "coming in FE-B{N}" placeholder for unbuilt tabs |
| `CustomersPage` | `features/customers/components/CustomersPage.tsx` | **Modify** | Add "Add Customer" button + CreateCustomerModal; add ?search= server-side if B17 added it |
| `customers/[id]/layout.tsx` | `app/(authed)/customers/[id]/layout.tsx` | **Modify** | Add "Sites" tab; render `CustomerDetailHeader` with customerId |
| `customers/[id]/page.tsx` | `app/(authed)/customers/[id]/page.tsx` | **Modify** | Replace "coming soon" with `<CustomerOverviewTab>` |
| `customers/[id]/sites/page.tsx` | `app/(authed)/customers/[id]/sites/page.tsx` | **New** | Render `<SiteListPanel>` |
| `customers/[id]/quotes/page.tsx` | `app/(authed)/customers/[id]/quotes/page.tsx` | **Modify** | Replace "coming soon" with `<CustomerQuotesList>` |
| `customers/[id]/jobs/page.tsx` | `app/(authed)/customers/[id]/jobs/page.tsx` | **Modify** | Replace "coming soon" with `<CustomerJobsList>` or deferred |
| `customers/[id]/invoices/page.tsx` | `app/(authed)/customers/[id]/invoices/page.tsx` | **Modify** | Replace "coming soon" with `<CustomerInvoicesList>` or deferred |
| `useCustomer` | `features/customers/hooks/useCustomer.ts` | **New** | Single customer fetch |
| `useCreateCustomer` | `features/customers/hooks/useCreateCustomer.ts` | **New** | POST mutation |
| `useUpdateCustomer` | `features/customers/hooks/useUpdateCustomer.ts` | **New** | PATCH mutation |
| `useCustomerSites` | `features/customers/hooks/useCustomerSites.ts` | **New** | Sites list for a customer |
| `useCreateSite` | `features/customers/hooks/useCreateSite.ts` | **New** | POST site mutation |
| `useUpdateSite` | `features/customers/hooks/useUpdateSite.ts` | **New** | PATCH site mutation |
| `customerHandlers.ts` | `mocks/handlers/customerHandlers.ts` | **New** | MSW handlers for all customer + site CRUD endpoints |
| `mocks/handlers/index.ts` | `mocks/handlers/index.ts` | **Modify** | Register `...customerHandlers` |
