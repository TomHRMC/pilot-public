# Batch FE-B22 Design — Invoice Detail + Create + Record Payment + Tax Setup

**Batch**: FE-B22 (Frontend — React Engineer only)  
**Date**: June 16, 2026  
**Author**: Pilot Architect  
**Status**: DESIGN COMPLETE — Ready for implementation  
**Reference gap analysis**: `dev-docs/analysis/pilot-app-pre-wkstm-3-mvp-ui-api-gap-analysis.md` §1.4, §1.7, §1.15, §4.2  
**Prerequisites**: FE-B21 complete (job → invoice conversion exists), B17 Part A complete + `pnpm sync-api-types`

---

## Overview

FE-B22 builds the complete invoice management surface on the web app. Currently:
- `/invoices/[id]` is a 404 (route doesn't exist) — links from the invoices list go nowhere
- There's no way to create a standalone invoice (outside of job conversion)
- Recording a payment has no UI
- Tax setup has no UI (412 errors on invoice create are unhandled)

FE-B22 delivers:
1. **Invoice detail** at `/invoices/[id]` — line items, tax breakdown, payment history, balance
2. **"Generate Public Link"** action on the invoice detail → `POST /api/v1/invoices/{id}/send`
3. **"Record Payment"** modal on unpaid/partial invoices
4. **AR aging widget** on the dashboard
5. **Tax setup just-in-time sub-flow** — intercepts 412 when invoice creation fails due to missing tax config
6. **"Send Invoice"** action with `always-preview-before-send` pattern
7. **Update `CustomerInvoicesList`** from FE-B18 deferred state to real data

No backend changes needed — all endpoints exist.

---

## A. Input Read Summary

| Input | What was read | Key finding |
|---|---|---|
| PRD §3.6 Invoicing & Billing | Full feature list | One-click quote/job → invoice, AR aging, ACH/card, public payment links, dunning, Stripe payment, variance payment accounting |
| `backend/api/routes/invoices.py` (endpoints search) | 10 route decorators | `GET /`, `POST /`, `GET /{id}`, `POST /{id}/send`, `POST /{id}/record-payment` — all exist |
| `backend/api/schemas/schemas.py` lines 432–569 | `InvoiceSummary`, `InvoiceListResponse`, `InvoiceLineResponse`, `InvoiceResponse`, `InvoiceCreate`, `PaymentRecordRequest`, `PaymentResponse` | `InvoiceCreate` accepts `quote_id`, `job_id`, `due_at`, `issued_at`, `customer_notes`, `idempotency_key`; `PaymentRecordRequest` requires `payment_method_id` and `payment_status_id` (UUIDs — need lookup tables) |
| Live DB `invoice` table | 24 columns confirmed | Has `quote_id`, `job_id`, `balance_due_cents`, `status_code` (via join), `lines` (nested in response) |
| Live DB `invoice_line` table | Columns confirmed | `source_type`, `source_id`, `description`, `quantity`, `unit_price_cents`, `subtotal_cents`, `tax_amount_cents`, `total_cents` |
| `features/invoices/hooks/useInvoices.ts` | Existing hook | Already exists; has `InvoiceListItem` type; `status_code` present; `customer_id` missing from list item |
| `features/invoices/components/InvoicesPage.tsx` | Existing page | Read-only list with status filter; links to `/invoices/${inv.id}` (currently 404) |
| Gap analysis §1.15 | Tax setup | 412 Precondition Required when no tax jurisdiction configured; no frontend intercept exists |
| PRD §3.12, §4.7.6 | Tax setup sub-flow | "Tax Setup Just-In-Time Sub-Flow": 412 → contextual sub-flow → configure tax → resume invoice creation |

---

## B. Migration Plan

**No Alembic migrations. No backend changes.** FE-B22 is purely frontend.

All required endpoints confirmed:

| Endpoint | Description |
|---|---|
| `GET /api/v1/invoices/` | List invoices (exists, used by `InvoicesPage`) |
| `POST /api/v1/invoices/` | Create invoice (requires quote_id or job_id) |
| `GET /api/v1/invoices/{id}` | Invoice detail with nested lines |
| `POST /api/v1/invoices/{id}/send` | Generate public link + trigger send notification |
| `POST /api/v1/invoices/{id}/record-payment` | Record payment against invoice |

**Pre-work verification needed**:
- What does `POST /api/v1/invoices/{id}/send` return? Verify if it returns a `public_url`.
- `PaymentRecordRequest` requires `payment_method_id` (UUID) and `payment_status_id` (UUID). Do lookup endpoints exist for these? If not, the Record Payment form needs to handle this differently.
- Does `GET /api/v1/invoices/?customer_id=` filter exist? Check for FE-B18 `CustomerInvoicesList` update.
- Verify the 412 response structure when tax is not configured — what does the response body look like?
- Check if tax jurisdiction configuration endpoint exists: `POST /api/v1/settings/tax-jurisdiction` or similar.

---

## C. Execution Order

| # | Task | Files | Dependency |
|---|---|---|---|
| 1 | Extend existing invoice MSW handlers | `mocks/handlers/` (check for existing invoice handler) | None |
| 2 | Create `useInvoice` hook (single invoice detail) | `features/invoices/hooks/useInvoice.ts` | 1 |
| 3 | Create `useCreateInvoice` mutation + 412 intercept | `features/invoices/hooks/useCreateInvoice.ts` | 1 |
| 4 | Create `useSendInvoice` mutation | `features/invoices/hooks/useSendInvoice.ts` | 1 |
| 5 | Create `useRecordPayment` mutation | `features/invoices/hooks/useRecordPayment.ts` | 1 |
| 6 | Create `useArSummary` hook (dashboard widget data) | `features/dashboard/hooks/useArSummary.ts` | 1 |
| 7 | Create `InvoiceDetailPage` — header + line items + payment history | `features/invoices/components/InvoiceDetailPage.tsx` | 2, 4, 5 |
| 8 | Create `InvoiceLineItemsTable` component | `features/invoices/components/InvoiceLineItemsTable.tsx` | None |
| 9 | Create `InvoicePaymentHistory` component | `features/invoices/components/InvoicePaymentHistory.tsx` | None |
| 10 | Create `RecordPaymentModal` | `features/invoices/components/RecordPaymentModal.tsx` | 5 |
| 11 | Create `SendInvoicePreviewModal` (always-preview-before-send) | `features/invoices/components/SendInvoicePreviewModal.tsx` | 4 |
| 12 | Create `TaxSetupSubFlowModal` (412 intercept) | `features/invoices/components/TaxSetupSubFlowModal.tsx` | 3 |
| 13 | Create `/invoices/[id]/page.tsx` route | `app/(authed)/invoices/[id]/page.tsx` | 7 |
| 14 | Update `InvoicesPage` — add "+" Create Invoice button, fix customer name display | `features/invoices/components/InvoicesPage.tsx` | 3 |
| 15 | Create `ArSummaryWidget` for dashboard | `features/dashboard/components/ArSummaryWidget.tsx` | 6 |
| 16 | Add `ArSummaryWidget` to dashboard page | `app/(authed)/dashboard/page.tsx` | 15 |
| 17 | Update `CustomerInvoicesList` from deferred state (if `?customer_id=` confirmed) | `features/customers/components/CustomerInvoicesList.tsx` | 1 |
| 18 | Write unit + integration tests | `__tests__/batch_fe_b22/` | All |
| 19 | Full verification | — | 18 |

---

## D. API Endpoints Consumed

| Hook | Endpoint | Method |
|---|---|---|
| `useInvoice` | `GET /api/v1/invoices/{id}` | GET |
| `useCreateInvoice` | `POST /api/v1/invoices/` | POST |
| `useSendInvoice` | `POST /api/v1/invoices/{id}/send` | POST |
| `useRecordPayment` | `POST /api/v1/invoices/{id}/record-payment` | POST |
| `useInvoices` (existing) | `GET /api/v1/invoices/` | GET |
| `useArSummary` | Dashboard aggregate endpoint (if exists — verify) | GET |

---

## E. Pattern Reuse Decisions

| Pattern | Applied in FE-B22 |
|---|---|
| **`always-preview-before-send`** (mvp-arch §16.7) | `SendInvoicePreviewModal` — must confirm before `useSendInvoice` fires |
| **Tax Setup JIT sub-flow** (PRD §4.7.6) | `TaxSetupSubFlowModal` intercepts 412 from `useCreateInvoice` |
| `<RoleGate>` | "Record Payment" / "Send Invoice" / "Create Invoice" all gated to `invoices.create` / `invoices.edit` |
| `<LoadingState>`, `<ErrorState>` | Invoice detail page loading/error states |
| `apiClient` | All hooks |
| `retry: false` | All test QueryClient wrappers |
| `always-preview-before-send` | Mandatory for invoice send — same as quote send in FE-B19 |

---

## F. Shared Module Interfaces

### F.1 `useInvoice`

```typescript
// Query key: ['invoice', invoiceId]
// GET /api/v1/invoices/{invoiceId}
// Returns: InvoiceResponse (includes nested lines[])
// enabled: !!invoiceId
```

### F.2 `useCreateInvoice`

```typescript
// POST /api/v1/invoices/
// Request: { quote_id?, job_id?, due_at?, issued_at?, customer_notes?, idempotency_key }
// On 201: navigate to /invoices/{response.id}
// On 412: open TaxSetupSubFlowModal with the 412 response payload
// The 412 must be caught and handled — NOT surfaced as a generic error
```

### F.3 `useSendInvoice`

```typescript
// POST /api/v1/invoices/{invoiceId}/send
// Returns: { public_url, token } (verify response shape in pre-work)
// Only called from SendInvoicePreviewModal confirm button — never pre-emptively
```

### F.4 `useRecordPayment`

```typescript
// POST /api/v1/invoices/{invoiceId}/record-payment
// Request: { amount_cents, paid_via, payment_method_id, payment_status_id, paid_at?, reference?, comment? }
// Note: payment_method_id + payment_status_id are UUIDs — need lookup values
// Verify in pre-work: how does the UI get these IDs? 
//   Option A: GET /api/v1/payment-methods (customer's vaulted methods)
//   Option B: Hardcode "record manual payment" flow with 'other' paid_via
// onSuccess: invalidate ['invoice', invoiceId]
```

### F.5 `useArSummary`

```typescript
// Verify if GET /api/v1/dashboard/ar-summary exists (not yet built)
// If endpoint doesn't exist: use GET /api/v1/invoices/ to compute AR buckets client-side
// AR buckets: current (not overdue), 30d, 60d, 90d
// Compute from balance_due_cents + due_at on each invoice
```

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| **`payment_method_id` requirement for record-payment** | For MVP web: use a simplified "Record Manual Payment" form with `paid_via: 'other'` and a placeholder `payment_method_id`. Check pre-work if a lookup endpoint exists. If `payment_method_id` is required (NOT NULL), find the default system payment method ID or add a minimal payment method selector. Do NOT block the feature. |
| **`payment_status_id` for record-payment** | Same resolution. Check if `payment_status` table lookup endpoint exists. If not, query MCP for the seeded `payment_status` UUIDs and hardcode the `succeeded` status UUID in the MSW mock. |
| **Tax setup sub-flow — does the tax endpoint exist?** | Verify in pre-work. If `POST /api/v1/settings/tax-jurisdiction` exists: build the full sub-flow. If not: show the 412 as a user-friendly error ("Tax setup required — go to Settings → Tax") with a link. Do NOT silently swallow the 412. |
| **AR aging widget — should it be server-side or client-side computed?** | Client-side computation from the invoices list for MVP. Fetch all unpaid invoices, group by `due_at` into buckets (current / 30d / 60d / 90d overdue). If `/dashboard/ar-summary` endpoint exists: use it instead. |
| **"Create Invoice" on list page — when is it used?** | For creating standalone invoices not from a job. Should have customer picker + site picker + optional quote/job reference. This is a secondary flow (most invoices come from job conversion in FE-B21 or quote conversion in FE-B19). Keep the create form minimal. |
| **`InvoicesPage` customer name display** | `InvoiceListItem` in `useInvoices.ts` has `customer_id` but NOT `customer_name`. After B17 and `pnpm sync-api-types`, verify if `InvoiceSummary` now includes a `customer_name` field. If not: show `customer_id.slice(0,8)` (as currently done) — not worth an N+1 query. |
| **Should `InvoicesPage` have a "Create Invoice" button?** | Yes, but secondary (most invoice creation happens via job/quote conversion). Add a "+" button behind `<RoleGate permission="invoices.create">`. |

---

## H. Surface Mockup Reference

**Platform**: Web only (`apps/web`)

### H.1 `/invoices/[id]` — Invoice Detail

```
┌─────────────────────────────────────────────────────────────┐
│  Invoices / INV-20260616-A4B2                               │
│  Status: Sent  •  Johnson Electrical  •  Due Jun 30         │
│  ─────────────────────────────────────────────────────────  │
│  200A Service Panel      1    $450.00   $450.00            │
│  Wire, 12 AWG 100ft     100   $0.85     $85.00             │
│  ────────────────────────────────────────                   │
│  Subtotal: $535.00   Tax (8.25%): $44.14   Total: $579.14   │
│  Balance Due: $579.14                                       │
│  ─────────────────────────────────────────────────────────  │
│  Payments                                                   │
│  [No payments yet]                                          │
│  ─────────────────────────────────────────────────────────  │
│  [Send Invoice]  [Record Payment]  [Copy Public Link]       │
└─────────────────────────────────────────────────────────────┘
```

- "Send Invoice": opens `SendInvoicePreviewModal` → on confirm calls `useSendInvoice`
- "Record Payment": opens `RecordPaymentModal` (hidden if balance = 0)
- "Copy Public Link": copies the public URL if already generated (if not: generates first)

### H.2 Dashboard — AR Aging Widget

```
┌───────────────────────────────────┐
│  Accounts Receivable              │
│  Current: $2,450   (5 invoices)   │
│  30+ days: $1,200  (2 invoices)   │
│  60+ days: $800    (1 invoice)    │
│  90+ days: $350    (1 invoice)    │
│  Total Outstanding: $4,800        │
└───────────────────────────────────┘
```

---

## I. Component Manifest

| Component | Path | New or Modify | Notes |
|---|---|---|---|
| `InvoiceDetailPage` | `features/invoices/components/InvoiceDetailPage.tsx` | **New** | Full invoice detail with actions |
| `InvoiceLineItemsTable` | `features/invoices/components/InvoiceLineItemsTable.tsx` | **New** | Renders `InvoiceLineResponse[]` |
| `InvoicePaymentHistory` | `features/invoices/components/InvoicePaymentHistory.tsx` | **New** | Shows recorded payments |
| `RecordPaymentModal` | `features/invoices/components/RecordPaymentModal.tsx` | **New** | Record manual payment |
| `SendInvoicePreviewModal` | `features/invoices/components/SendInvoicePreviewModal.tsx` | **New** | always-preview-before-send |
| `TaxSetupSubFlowModal` | `features/invoices/components/TaxSetupSubFlowModal.tsx` | **New** | 412 intercept with tax config flow |
| `ArSummaryWidget` | `features/dashboard/components/ArSummaryWidget.tsx` | **New** | AR aging buckets |
| `useInvoice` | `features/invoices/hooks/useInvoice.ts` | **New** | Single invoice detail |
| `useCreateInvoice` | `features/invoices/hooks/useCreateInvoice.ts` | **New** | POST mutation with 412 handling |
| `useSendInvoice` | `features/invoices/hooks/useSendInvoice.ts` | **New** | POST send/public-link |
| `useRecordPayment` | `features/invoices/hooks/useRecordPayment.ts` | **New** | POST record-payment |
| `useArSummary` | `features/dashboard/hooks/useArSummary.ts` | **New** | AR aging data |
| `InvoicesPage` | `features/invoices/components/InvoicesPage.tsx` | **Modify** | Add "+" Create Invoice button |
| `invoices/[id]/page.tsx` | `app/(authed)/invoices/[id]/page.tsx` | **New** | Thin route: `<InvoiceDetailPage>` |
| `dashboard/page.tsx` | `app/(authed)/dashboard/page.tsx` | **Modify** | Add `<ArSummaryWidget>` |
| `CustomerInvoicesList.tsx` | `features/customers/components/CustomerInvoicesList.tsx` | **Modify** | Replace deferred state if `?customer_id=` confirmed |
| Invoice MSW handlers | `mocks/handlers/invoiceHandlers.ts` (new or extend existing) | **New/Extend** | Add invoice detail + send + record-payment handlers |
| `mocks/handlers/index.ts` | `mocks/handlers/index.ts` | **Modify** | Register new invoice handlers |
