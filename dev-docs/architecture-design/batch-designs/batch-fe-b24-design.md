# Batch FE-B24 Design — CRUD Completeness: Job Create Modal, Invoice Create Rework, Invoice Customer Name Display, Quote Metadata Edit, Customer Delete

**Batch Code**: FE-B24  
**Type**: Frontend web only (`apps/web`)  
**Date**: 2026-07-10  
**Author**: Pilot Architect  
**Status**: Ready for implementation  
**Priority**: P1 — blocking demo useability (🔴 critical items) and owner workflow (🟡 important items)  
**Backend companion**: B18 must complete first (provides `customer_name` in `InvoiceSummary` + `PATCH /api/v1/jobs/{job_id}`)  
**Source Issue**: `dev-docs/testing-support/alpha-testing/ui-testing-status-2026-07-10.md`

---

## A. Input Read Summary

| Input | What Was Verified |
|---|---|
| `ui-testing-status-2026-07-10.md` | 5 frontend gaps confirmed: (1) No Job Create UI, (2) Invoice Create modal has zero fields, (3) Invoice list shows UUID not customer name, (4) No Quote metadata edit form, (5) No Customer delete button |
| `backend/api/schemas/schemas.py` | `JobCreate` schema: `customer_id`, `site_id`, `quote_id?`, `scheduled_start_at?`, `scheduled_end_at?`, `estimated_duration_minutes?`. `InvoiceCreate`: `quote_id?`, `job_id?`, `customer_notes?`, `terms_and_conditions?`, `due_at?`, `issued_at?`. `InvoiceSummary` after B18: adds `customer_name`. |
| `backend/api/routes/jobs.py` | `POST /api/v1/jobs/` exists and is functional. Create accepts `customer_id` + `site_id` and derives `status_id` from default job status. No additional BE work needed for Job Create. |
| `backend/api/routes/invoices.py` | `POST /api/v1/invoices/` exists. Does NOT require `customer_id` directly — derives it from linked `quote_id` or `job_id`. The current empty modal is a pure FE bug. |
| `backend/api/schemas/schemas.py` — Quote | `PATCH /api/v1/quotes/{id}` exists and accepts `status_id`, `expires_at`, `subtotal_cents`, `tax_cents`, `total_cents`, `currency`. |
| `backend/api/routes/customers.py` (implied) | `DELETE /api/v1/customers/{id}` exists per testing doc — needs only a confirmation modal on the FE |
| `frontend/react-engr-std-prompt-inclusions.md` | Read in full — all required prompt sections identified |
| B18 design doc | Confirms `customer_name: str \| None = None` will be on `InvoiceSummary` after B18 |

---

## B. Migration Plan

**No Alembic migration.** This is a pure frontend batch — no DB schema changes.

---

## C. Execution Order

| Step | Task | Primary File(s) |
|---|---|---|
| 1 | `pnpm sync-api-types` — pull latest openapi (must run after B18 ships) | — |
| 2 | Create `useCreateJob` hook | `features/jobs/hooks/useCreateJob.ts` |
| 3 | Create `JobFormModal` component (customer → site cascade, datetime pickers) | `features/jobs/components/JobFormModal.tsx` |
| 4 | Wire "Add Job" button in `JobsPage` → `JobFormModal` | `features/jobs/components/JobsPage.tsx` |
| 5 | Create/extend `jobHandlers.ts` MSW handler for `POST /api/v1/jobs/` | `mocks/handlers/jobHandlers.ts` |
| 6 | Create `InvoiceCreateModal` replacement (proper form replacing zero-field modal) | `features/invoices/components/InvoiceCreateModal.tsx` |
| 7 | Wire `InvoiceCreateModal` into `InvoicesPage` (replace empty modal call) | `features/invoices/components/InvoicesPage.tsx` |
| 8 | Fix `InvoiceList` / `InvoicesPage` to display `customer_name` (not UUID) | `features/invoices/components/InvoicesPage.tsx` |
| 9 | Extend `invoiceDetailHandlers.ts` MSW to return `customer_name` in list fixture | `mocks/handlers/invoiceDetailHandlers.ts` |
| 10 | Create `useUpdateQuote` hook | `features/quotes/hooks/useUpdateQuote.ts` |
| 11 | Create `QuoteMetadataEditModal` component (expires_at, currency) | `features/quotes/components/QuoteMetadataEditModal.tsx` |
| 12 | Wire "Edit" action in `QuoteDetailPage` → `QuoteMetadataEditModal` on draft quotes | `features/quote-approval/QuoteDetailPage.tsx` |
| 13 | Add Customer delete confirmation modal to `CustomersPage` or customer detail | `features/customers/components/DeleteCustomerModal.tsx` |
| 14 | Write unit + integration tests for all new components/hooks | `__tests__/batch_fe_b24/` |
| 15 | Phase 2 full verification | — |

---

## D. New API Endpoints

All backend endpoints already exist after B18 ships. No new backend work in this batch.

**Verified endpoints for this batch:**

| Hook | Endpoint | Backend Status |
|---|---|---|
| `useCreateJob` | `POST /api/v1/jobs/` | ✅ Exists (FE-B21) |
| `useCreateInvoice` (update) | `POST /api/v1/invoices/` | ✅ Exists (FE-B22) |
| `useInvoices` (update) | `GET /api/v1/invoices/` | ✅ Exists; `customer_name` added in B18 |
| `useUpdateQuote` (new) | `PATCH /api/v1/quotes/{id}` | ✅ Exists (B17) |
| `useDeleteCustomer` | `DELETE /api/v1/customers/{id}` | ✅ Exists (FE-B18) |

> **Dependency**: `customer_name` in `GET /api/v1/invoices/` response requires B18 to ship first. Run `pnpm sync-api-types` after B18 is confirmed deployed to pull the updated `InvoiceSummary` type.

---

## E. Pattern Reuse Decisions

| Pattern | Applied Where |
|---|---|
| `<LoadingState>` / `<ErrorState>` / `<EmptyState>` from `@pilot/ui` | Job form while customers loading; invoice form while customers/jobs loading |
| `<RoleGate permission="jobs.create">` | "Add Job" button — owners and office staff only |
| `<RoleGate permission="invoices.create">` | Invoice create button |
| `<RoleGate permission="customers.delete">` | Customer delete button |
| TanStack Query `useMutation` for all POST/PATCH/DELETE | `useCreateJob`, `useCreateInvoice`, `useUpdateQuote`, `useDeleteCustomer` |
| `retry: false` on QueryClient in tests | Required per react-engr inclusions §9 |
| MSW handlers for all API calls | `jobHandlers.ts`, `invoiceDetailHandlers.ts`, `quoteHandlers.ts`, `customerHandlers.ts` |
| `apiClient` from `@pilot/shared-api` — no raw `fetch()` | All hooks |
| Confirm-as-Turn pattern (mvp-arch §16) | Delete customer — show confirmation step before DELETE fires |
| Cascade-select (customer → site dropdown) | `JobFormModal` — site list filtered by selected `customer_id` |

---

## F. Shared Module Interfaces

### F1. `useCreateJob` hook

```typescript
// features/jobs/hooks/useCreateJob.ts
interface JobCreatePayload {
  customer_id: string;
  site_id: string;
  quote_id?: string;
  scheduled_start_at?: string; // ISO 8601
  scheduled_end_at?: string;   // ISO 8601
  estimated_duration_minutes?: number;
}

const useCreateJob = () => useMutation({
  mutationFn: (payload: JobCreatePayload) =>
    apiClient.post('/api/v1/jobs/', payload),
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ['jobs'] }),
});
```

### F2. `useUpdateQuote` hook

```typescript
// features/quotes/hooks/useUpdateQuote.ts
interface QuoteUpdatePayload {
  expires_at?: string;  // ISO 8601
  currency?: string;
  // status_id excluded — status transitions go through approval workflow
}

const useUpdateQuote = (quoteId: string) => useMutation({
  mutationFn: (payload: QuoteUpdatePayload) =>
    apiClient.patch(`/api/v1/quotes/${quoteId}`, payload),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['quote', quoteId] });
    queryClient.invalidateQueries({ queryKey: ['quotes'] });
  },
});
```

### F3. `JobFormModal` component contract

```typescript
interface JobFormModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess?: (job: JobResponse) => void;
}
```

- Step 1: Customer dropdown (`GET /api/v1/customers/`)
- Step 2: Site dropdown (filtered by `customer_id` from `GET /api/v1/sites/?customer_id=...`)
- Optional: `scheduled_start_at`, `scheduled_end_at` datetime pickers
- Optional: `estimated_duration_minutes` number input
- Submit calls `useCreateJob`, closes modal on success, shows toast

### F4. `InvoiceCreateModal` component contract

```typescript
interface InvoiceCreateModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess?: (invoice: InvoiceResponse) => void;
}
```

**Form fields (all optional per `InvoiceCreate` schema):**
- Customer picker → populates `customer_id` display (note: backend derives `customer_id` from linked quote/job, but we need to show the user which customer)
- Quote linkage dropdown — optional: `GET /api/v1/quotes/?status=accepted` (only show accepted quotes since those become jobs/invoices)
- Job linkage dropdown — optional: `GET /api/v1/jobs/` 
- Due date: `due_at` date picker (ISO 8601)
- Issue date: `issued_at` date picker (defaults to today)
- Customer notes: textarea
- Submit: calls `POST /api/v1/invoices/` with `{quote_id?, job_id?, customer_notes?, due_at?, issued_at?}`

**Design note**: The invoice's `customer_id` and `site_id` are set server-side based on the linked quote or job. If neither is linked, the backend creates a "standalone" invoice against a default customer. The frontend should show a warning if neither quote nor job is linked, but should not block submission.

### F5. `QuoteMetadataEditModal` component contract

```typescript
interface QuoteMetadataEditModalProps {
  quoteId: string;
  currentExpiresAt: string | null;
  currentCurrency: string;
  open: boolean;
  onClose: () => void;
}
```

- `expires_at` date picker
- `currency` dropdown (USD, CAD — only USD for MVP; keep dropdown but default USD)
- Submit: calls `useUpdateQuote`, invalidates quote detail

**Placement**: "Edit" link on draft quote detail page (already exists as link per testing doc) — replace/augment the link target to open this modal.

### F6. `DeleteCustomerModal` component contract

```typescript
interface DeleteCustomerModalProps {
  customerId: string;
  customerName: string;
  open: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}
```

- Confirmation message: "Delete [customerName]? This action cannot be undone."
- Cancel button (closes modal)
- Delete button → calls `DELETE /api/v1/customers/{id}` via `useDeleteCustomer` hook
- On success: navigate to `/customers` list

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| Does `InvoiceCreate` require `customer_id` directly? | No — backend derives it from `quote_id` or `job_id`. Standalone invoices (no linkage) are allowed by the schema. FE should show a warning but not block. |
| How does the invoice create modal know which customer to link? | User selects a Quote or Job from dropdowns. The selected quote/job has a customer. Display the customer name as read-only context once quote or job is selected. |
| Should Job Create require a quote linkage? | No — `quote_id` is optional in `JobCreate`. Jobs can be created without a quote. |
| Is "Customer Delete" safe for MVP (can it break related data)? | Backend endpoint already exists — it presumably handles soft-delete (setting `is_active=false`) or cascade. FE simply needs the confirmation modal. Tom confirmed: "backend endpoint exists". |
| Should the Quote metadata edit modal be shown on all quote statuses? | No — only draft quotes. Accepted/approved quotes should show the edit fields as read-only. The testing doc notes "The 'Edit' link on draft quotes" specifically. |
| Does `customer_name` display require FE work after B18 ships? | Yes — `InvoicesPage.tsx` must render `item.customer_name` instead of `item.customer_id.slice(0,8)…`. The `InvoiceSummary` type will have `customer_name` after B18 + `pnpm sync-api-types`. |

---

## H. Surface Mockup Reference

No dedicated UI designer pass was done for this batch — these are CRUD completion gaps, not new UX surfaces. All surfaces follow the existing design system:

| Surface | Platform | Location | Description |
|---|---|---|---|
| `JobFormModal` | Web only | `features/jobs/` | Modal dialog with customer/site cascade dropdowns + optional schedule fields |
| `InvoiceCreateModal` | Web only | `features/invoices/` | Modal with quote/job linkage dropdowns + due date + customer notes |
| Invoice list `customer_name` | Web only | `features/invoices/InvoicesPage.tsx` | Replace UUID substring with `customer_name` string |
| `QuoteMetadataEditModal` | Web only | `features/quotes/` | Small modal for `expires_at` and `currency` |
| `DeleteCustomerModal` | Web only | `features/customers/` | Confirm-as-Turn deletion dialog |

---

## I. Component Manifest

| Component | Destination Path | Type |
|---|---|---|
| `JobFormModal` | `apps/web/src/features/jobs/components/JobFormModal.tsx` | New |
| `useCreateJob` | `apps/web/src/features/jobs/hooks/useCreateJob.ts` | New |
| `InvoiceCreateModal` | `apps/web/src/features/invoices/components/InvoiceCreateModal.tsx` | Replace existing skeleton |
| `useCreateInvoice` | `apps/web/src/features/invoices/hooks/useCreateInvoice.ts` | New or extend existing |
| `QuoteMetadataEditModal` | `apps/web/src/features/quotes/components/QuoteMetadataEditModal.tsx` | New |
| `useUpdateQuote` | `apps/web/src/features/quotes/hooks/useUpdateQuote.ts` | New |
| `DeleteCustomerModal` | `apps/web/src/features/customers/components/DeleteCustomerModal.tsx` | New |
| `useDeleteCustomer` | `apps/web/src/features/customers/hooks/useDeleteCustomer.ts` | New or extend existing |
| `jobHandlers.ts` (MSW) | `apps/web/src/mocks/handlers/jobHandlers.ts` | New or extend existing |

> **Note to React Engineer**: Before creating any of these, check whether stubs already exist in the features directory — some may have been scaffolded in FE-B21/B22. Read each destination file with `read_file` before writing.
