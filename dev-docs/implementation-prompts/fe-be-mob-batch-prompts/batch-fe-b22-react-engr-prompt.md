# Implementation Prompt: FE-B22 — Invoice Detail + Create + Record Payment + Tax Setup

**Mode**: Pilot React Engineer  
**Batch**: FE-B22  
**Source plan**: `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` §Phase 0.9 — FE-B22  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-fe-b22-design.md`  
**Estimated session**: 4–6 hours  
**Platform**: Web only (`apps/web`)  
**Backend companion**: None — all endpoints exist. Prerequisites: FE-B21 complete, B17 Part A complete + `pnpm sync-api-types`.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-fe-b22-design.md`** — every section (A–I)

**Critical rules for this batch:**

- **Rule 1.1**: Before ANY hook, verify exact endpoint path and response schema in `backend/openapi_schema_map.md`. `PaymentRecordRequest` requires `payment_method_id` and `payment_status_id` UUIDs — verify how to obtain these.
- **Rule 1.3**: Run `pnpm sync-api-types` before starting.
- **Rule 2**: All API calls use `apiClient`. `fetch()` banned.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating components.
- **Rule 9**: Route files are thin server components.
- **Rule 10**: Fix any test failure before declaring done.
- **always-preview-before-send is non-negotiable**: `SendInvoicePreviewModal` must render before `useSendInvoice` fires. The hook must NEVER be called outside the "Confirm Send" button handler.
- **412 must be caught, not swallowed**: `useCreateInvoice` must catch HTTP 412 and open `TaxSetupSubFlowModal`. A generic error toast for 412 is a product defect.
- **Check existing invoice handlers before creating new ones**: Run `find frontend/apps/web/src/mocks/handlers -name "*[Ii]nvoice*"` before creating a new handler file. Extend if it exists; create if it doesn't.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G:

| Decision | Outcome | Rationale |
|---|---|---|
| `payment_method_id` for record-payment | Use simplified 'other' paid_via + find a usable UUID in pre-work | Do not block the feature; MVP can use manual payment recording |
| AR aging widget | Client-side computation from invoices list | Dashboard aggregate endpoint not confirmed to exist |
| Tax setup sub-flow | If 412 is returned: `TaxSetupSubFlowModal`; if tax endpoint doesn't exist: user-friendly error with link to Settings | Never silently ignore the 412 |
| "Create Invoice" button | Secondary action — minimal create form (customer + job/quote reference) | Primary creation path is job/quote conversion from FE-B21/B19 |
| `always-preview-before-send` | `SendInvoicePreviewModal` required on all send paths | Platform pattern — matches FE-B19 quote send |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
pnpm --filter @pilot/ui test 2>&1 | tail -5
```

Record exact counts. Fix pre-existing failures or confirm with Tom.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

---

## Pre-Work: Verify Endpoints

Run ALL of these before writing any code:

```bash
# 1. Verify invoice detail endpoint + response shape
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
inv_detail = spec['paths'].get('/api/v1/invoices/{invoice_id}', {}).get('get', {})
resp = inv_detail.get('responses', {}).get('200', {}).get('content', {}).get('application/json', {}).get('schema', {})
ref = resp.get('\$ref', '')
if ref:
    name = ref.split('/')[-1]
    s = spec['components']['schemas'][name]
    print('InvoiceResponse fields:', list(s.get('properties', {}).keys()))
"

# 2. Verify send endpoint response shape
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
send = spec['paths'].get('/api/v1/invoices/{invoice_id}/send', {}).get('post', {})
resp = send.get('responses', {}).get('201', send.get('responses', {}).get('200', {}))
print('Send response:', resp.get('content', {}).get('application/json', {}).get('schema', {}))
"

# 3. Check PaymentRecordRequest required fields
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
prr = spec['components']['schemas'].get('PaymentRecordRequest', {})
print('PaymentRecordRequest:', list(prr.get('properties', {}).keys()))
print('Required:', prr.get('required', []))
"

# 4. Check if payment_status lookup endpoint exists
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
ps_paths = [p for p in spec['paths'] if 'payment-status' in p or 'payment_status' in p]
print('Payment status paths:', ps_paths)
"

# 5. Check if AR summary dashboard endpoint exists
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
ar_paths = [p for p in spec['paths'] if 'ar-summary' in p or 'aging' in p]
print('AR summary paths:', ar_paths)
"

# 6. Check tax jurisdiction endpoint
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
tax_paths = [p for p in spec['paths'] if 'tax' in p.lower()]
print('Tax paths:', tax_paths)
"

# 7. Check if customer_id filter exists on invoices
python3 -c "
import json
spec = json.load(open('backend/openapi.json'))
inv_list = spec['paths'].get('/api/v1/invoices/', {}).get('get', {})
params = [p['name'] for p in inv_list.get('parameters', [])]
print('Invoice list params:', params)
"

# 8. Find existing invoice MSW handlers
find frontend/apps/web/src/mocks/handlers -name "*[Ii]nvoice*" 2>/dev/null

# 9. Check payment_method seeded data (for record-payment form)
grep -A 5 "payment_method\|payment_type" backend/migrations/scripts/seed_test_tenant.py | head -20
```

**Critical decisions from pre-work:**
- If `payment_method_id` is required (NOT NULL): use the payment_method from seed data or find a workaround (e.g., create a "manual" payment method record). Do NOT make the Record Payment feature unavailable.
- If tax endpoint doesn't exist: `TaxSetupSubFlowModal` shows "Tax rates must be configured before creating invoices. Go to Settings → Tax." with a link.
- If AR summary endpoint doesn't exist: compute client-side from `useInvoices` data.

---

## Pre-Work: Read These Source Files

```
frontend/apps/web/src/features/invoices/components/InvoicesPage.tsx
  ← understand current state before modifying

frontend/apps/web/src/features/invoices/hooks/useInvoices.ts
  ← understand existing hook before adding companions

frontend/apps/web/src/app/(authed)/dashboard/page.tsx
  ← understand dashboard layout before adding AR widget

frontend/apps/web/src/features/customers/components/CustomerInvoicesList.tsx
  ← check if still deferred state — update if customer_id filter confirmed

frontend/apps/web/src/features/quotes/components/SendQuotePreviewModal.tsx
  ← reference implementation for always-preview-before-send pattern (FE-B19)

frontend/apps/web/src/mocks/handlers/index.ts
  ← understand barrel before adding invoice handlers

frontend/packages/ui/src/index.ts
  ← confirm component imports before use
```

---

## Step 1 — Invoice MSW Handlers

**Check existing first**: `find frontend/apps/web/src/mocks/handlers -name "*[Ii]nvoice*"`

If an invoice handler file exists: extend it. If not: create `mocks/handlers/invoiceDetailHandlers.ts`.

Add handlers for:
```typescript
// GET /api/v1/invoices/:invoiceId — full invoice with lines
// POST /api/v1/invoices/:invoiceId/send — returns { public_url, token }
// POST /api/v1/invoices/:invoiceId/record-payment — returns PaymentResponse
// POST /api/v1/invoices/ — create invoice (returns InvoiceResponse)
```

Use fixture data consistent with `quotesListHandlers.ts` customers.

**Register in `mocks/handlers/index.ts`:**
```typescript
import { invoiceDetailHandlers } from "./invoiceDetailHandlers";  // ADD
export const handlers = [
  // ... existing ...
  ...invoiceDetailHandlers,  // ADD — FE-B22
];
```

> **Test resilience**: Never mutate fixture arrays. POST handlers return merged data with generated IDs.

---

## Steps 2–6 — Create Hooks

**Directory**: `apps/web/src/features/invoices/hooks/` (add to existing)

### `useInvoice.ts`

```typescript
// Query key: ['invoice', invoiceId]
// GET /api/v1/invoices/{invoiceId}
// Returns: InvoiceResponse (includes lines[])
// enabled: !!invoiceId
// staleTime: 60_000
```

### `useCreateInvoice.ts`

```typescript
// POST /api/v1/invoices/
// Body: { quote_id?, job_id?, due_at?, issued_at?, customer_notes?, idempotency_key }
// MUST handle 412 differently from other errors:
//   try { ... } catch (err) {
//     if (axios.isAxiosError(err) && err.response?.status === 412) {
//       setTaxSetupRequired(true);  // triggers TaxSetupSubFlowModal
//     } else {
//       throw err;  // let TanStack Query handle other errors
//     }
//   }
// Pass setTaxSetupRequired as a callback from the component using this hook
// Or: use a Zustand/useState approach to open the modal
```

### `useSendInvoice.ts`

```typescript
// POST /api/v1/invoices/{invoiceId}/send
// Returns { public_url, token }
// Only called from SendInvoicePreviewModal confirm button
// onSuccess: copy public_url to clipboard + show success toast
```

### `useRecordPayment.ts`

```typescript
// POST /api/v1/invoices/{invoiceId}/record-payment
// Body: { amount_cents, paid_via, payment_method_id, payment_status_id, paid_at?, reference? }
// payment_method_id + payment_status_id: from pre-work findings
// onSuccess: invalidate ['invoice', invoiceId]
```

### `useArSummary.ts`

```typescript
// If AR summary endpoint confirmed: GET it
// If not: compute from useInvoices with no status filter:
//   - Fetch all unpaid invoices (status not 'paid' or 'void')
//   - Group by due_at into buckets:
//     current: due_at > today OR due_at is null
//     30d: due_at between 30 days ago and today
//     60d: due_at between 60 and 31 days ago
//     90d: due_at between 90 and 61 days ago
//   - Sum balance_due_cents per bucket
```

---

## Step 7–11 — Invoice Detail Components

### `InvoiceLineItemsTable.tsx`

```typescript
// Props: lines: InvoiceLineResponse[]
// Table columns: Description, Qty, Unit Price, Subtotal, Tax, Total
// Footer row: Subtotal | Tax | Grand Total
// No edit actions — invoice lines are immutable after creation
```

### `InvoicePaymentHistory.tsx`

```typescript
// Props: invoiceId: string (re-use useRecordPayment invalidation to refresh)
// May need a separate usePayments hook or payment data may come from InvoiceResponse
// Check pre-work: does InvoiceResponse include payments[]? If not: fetch separately
// Shows: Date, Amount, Method, Reference — EmptyState if no payments
```

### `RecordPaymentModal.tsx`

```typescript
interface RecordPaymentModalProps {
  open: boolean;
  invoiceId: string;
  balanceDueCents: number;  // pre-fill amount field
  onClose: () => void;
}

// Fields:
// - Amount: defaults to balance_due_cents (allow partial)
// - Payment Method: from pre-work — if payment_method_id can be looked up, show dropdown
//   If no lookup: use 'other' paid_via with a reference text field
// - Date: defaults to today
// - Reference: optional text

// On submit: calls useRecordPayment
// On success: close modal + show "Payment recorded" toast
```

### `SendInvoicePreviewModal.tsx`

Read `SendQuotePreviewModal.tsx` from FE-B19 as the reference. Apply the same pattern:

```typescript
interface SendInvoicePreviewModalProps {
  open: boolean;
  invoiceId: string;
  invoiceNumber: string;
  customerEmail: string | null;
  onClose: () => void;
  onConfirm: () => void;
  isConfirming: boolean;
}

// Shows: "Send Invoice [INV-XX] to [customer email]"
// "Confirm Send" → calls onConfirm (which calls useSendInvoice)
// always-preview-before-send: useSendInvoice must NOT be called until confirm
```

### `TaxSetupSubFlowModal.tsx`

```typescript
// Opens when useCreateInvoice receives a 412 response
// Content depends on pre-work:
//   If tax jurisdiction endpoint exists:
//     Show auto-detected zip, default rate suggestion, confirm/override
//     On submit: POST to tax endpoint → then retry invoice creation
//   If tax endpoint NOT available:
//     Show: "Tax rates must be configured before creating invoices."
//     Link to Settings (tax settings page if it exists)
//     "Configure Tax" button
// Either path: clear the 412 state and close when done
```

### `InvoiceDetailPage.tsx`

```typescript
"use client";
interface InvoiceDetailPageProps {
  invoiceId: string;
}

// Layout:
// 1. Header: Invoice number, status badge, customer name, site, issued/due dates
// 2. <InvoiceLineItemsTable lines={invoice.lines} />
// 3. Totals: subtotal, tax, total, balance due
// 4. <InvoicePaymentHistory invoiceId={invoiceId} />
// 5. Action bar:
//    - [Send Invoice] → opens SendInvoicePreviewModal (shown when status is draft)
//    - [Record Payment] → opens RecordPaymentModal (hidden when balance = 0)
//    - [Copy Public Link] → if public link generated, copy URL; otherwise generate first
// 6. Both modals rendered with open/close state
```

---

## Steps 14, 15–16 — InvoicesPage + Dashboard

### Modify `InvoicesPage.tsx`

Read the file first. Add:
- "+" button behind `<RoleGate permission="invoices.create">` → opens minimal create invoice modal (customer picker + optional job/quote reference)
- Note: `customer_name` may not be in `InvoiceSummary` — check `useInvoices` hook response

### `ArSummaryWidget.tsx`

```typescript
"use client";
// Shows 4 AR aging buckets as a compact summary card
// Data from useArSummary (computed or fetched)
// Clicking a bucket could eventually filter invoices list — for MVP: read-only display
// EmptyState: "No outstanding invoices"
```

### Add to `dashboard/page.tsx`

Read the file first. Add `<ArSummaryWidget className="w-full" />` below existing widgets.

---

## Step 13 — Route File

```typescript
// app/(authed)/invoices/[id]/page.tsx
import { InvoiceDetailPage } from "@/features/invoices/components/InvoiceDetailPage";

interface Props { params: Promise<{ id: string }> }

export default async function InvoiceDetailRoute({ params }: Props) {
  const { id } = await params;
  return <InvoiceDetailPage invoiceId={id} />;
}

export const metadata = { title: "Invoice | Pilot" };
```

---

## Test Requirements

### Platform: Web (`apps/web`) — Vitest

- `vi.mock()`, `toBeInTheDocument()`, mock `next/navigation`
- `createWrapper()` with `retry: false`

### Test Resilience (per `react-engineer-rules.md` Rule 15)

- Never mutate fixture arrays
- Per-test `server.use(...)` + `server.resetHandlers()` in `afterEach`
- Never `toHaveLength(N)` on invoice lists

### Unit Tests

**`features/invoices/components/__tests__/SendInvoicePreviewModal.test.tsx`:**
- When `open=false`: modal not visible
- Renders customer email in preview
- "Cancel" calls `onClose` WITHOUT calling `onConfirm`
- "Confirm Send" calls `onConfirm` — verifying the always-preview-before-send invariant

**`features/invoices/components/__tests__/RecordPaymentModal.test.tsx`:**
- Renders with balance amount pre-filled
- Submit fires `useRecordPayment` with correct amount
- Cancel closes without firing mutation

**`features/invoices/components/__tests__/TaxSetupSubFlowModal.test.tsx`:**
- Renders when `open=true` with appropriate message
- Shows link to settings if tax endpoint unavailable

**`features/invoices/components/__tests__/InvoiceLineItemsTable.test.tsx`:**
- Renders all line items with description, qty, price
- Footer shows correct totals

**`features/dashboard/components/__tests__/ArSummaryWidget.test.tsx`:**
- Renders AR buckets: current, 30d, 60d, 90d
- Shows EmptyState when no outstanding invoices

### Integration Tests

**`apps/web/src/__tests__/batch_fe_b22/invoiceDetail.integration.test.tsx`:**
1. `/invoices/[id]` renders invoice detail with line items (no longer 404)
2. "Send Invoice" button opens `SendInvoicePreviewModal`
3. "Cancel" in modal does NOT fire `useSendInvoice`
4. "Record Payment" button opens `RecordPaymentModal`
5. "Record Payment" button hidden when balance_due_cents = 0

**`apps/web/src/__tests__/batch_fe_b22/invoiceTaxSetup.integration.test.tsx`:**
1. When `POST /api/v1/invoices/` returns 412: `TaxSetupSubFlowModal` opens (not a generic error)
2. Modal shows appropriate messaging

---

## Final Verification

### Phase 1 — Targeted

```bash
cd <repo>/frontend

# After hooks:
pnpm --filter web test -- --testPathPattern="useInvoice|useSendInvoice|useRecordPayment" 2>&1 | tail -6

# After components:
pnpm --filter web test -- --testPathPattern="SendInvoice|RecordPayment|TaxSetup|InvoiceLine|ArSummary" 2>&1 | tail -8

# After integration:
pnpm --filter web test -- --testPathPattern="batch_fe_b22" 2>&1 | tail -8
```

### Phase 2 — Full Verification

```bash
cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter @pilot/ui lint && pnpm --filter web lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && echo "=== FE-B22 FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — FE-B22

Update `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` §Phase 0.9:

- [ ] Regression baseline captured (zero pre-existing failures or confirmed with Tom)
- [ ] `pnpm sync-api-types` run
- [ ] Design doc read in full (A–I)
- [ ] All mandatory source files read (InvoicesPage, useInvoices, dashboard/page, CustomerInvoicesList, SendQuotePreviewModal as reference, mocks/handlers/index.ts)
- [ ] Pre-work complete: send response shape confirmed, PaymentRecordRequest required fields confirmed, payment_method_id strategy decided, tax endpoint existence confirmed, AR summary endpoint existence confirmed
- [ ] **Step 1**: Invoice MSW handlers added/extended; registered in barrel
- [ ] **Steps 2–6**: `useInvoice`, `useCreateInvoice`, `useSendInvoice`, `useRecordPayment`, `useArSummary` created
- [ ] **Steps 7–11**: `InvoiceLineItemsTable`, `InvoicePaymentHistory`, `RecordPaymentModal`, `SendInvoicePreviewModal`, `TaxSetupSubFlowModal`, `InvoiceDetailPage` created
- [ ] **Step 13**: `invoices/[id]/page.tsx` created — `/invoices/[id]` no longer 404
- [ ] **Step 14**: `InvoicesPage` has "+" Create Invoice button behind RoleGate
- [ ] **Step 15–16**: `ArSummaryWidget` created + added to dashboard page
- [ ] `SendInvoicePreviewModal` unit test: "Cancel" does NOT call `onConfirm` — always-preview-before-send enforced
- [ ] `TaxSetupSubFlowModal` opens on 412 — NOT a generic error state
- [ ] `RecordPaymentModal` unit tests pass
- [ ] `InvoiceLineItemsTable` unit tests pass
- [ ] `ArSummaryWidget` unit tests pass
- [ ] Integration tests in `__tests__/batch_fe_b22/` pass
- [ ] All new MSW handlers registered in `mocks/handlers/index.ts`
- [ ] Zero TypeScript errors
- [ ] Zero ESLint `no-hardcoded-design-values` warnings
- [ ] **Phase 2 FULL verification passes** (`=== FE-B22 FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter @pilot/ui lint && pnpm --filter web lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && echo "=== FE-B22 FINAL VERIFICATION COMPLETE ==="
  ```
- [ ] Final test count documented
- [ ] Completion Summary added to impl plan §Phase 0.9

---

## Completion Summary

After all DoD items, add a **Completion Summary** to `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` under Phase 0.9 — FE-B22:

```markdown
### FE-B22 — Invoice Detail + Create + Record Payment + Tax Setup: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (ui) | X passed (web)
**Final**: X+N passed (+N new tests)

#### What Was Accomplished

- Built /invoices/[id] detail page (no longer 404) with line items, tax, payment history
- Always-preview-before-send enforced for invoice send flow
- Record Payment modal with balance pre-fill
- Tax setup sub-flow modal intercepts 412 response
- AR aging widget added to dashboard
- "+" Create Invoice button on invoices list
- CustomerInvoicesList updated with real data (if customer_id filter confirmed)

#### Files Changed / Created

| File | Action |
|---|---|
| `apps/web/src/mocks/handlers/invoiceDetailHandlers.ts` | Created |
| `apps/web/src/mocks/handlers/index.ts` | Updated |
| `apps/web/src/features/invoices/hooks/useInvoice.ts` | Created |
| `apps/web/src/features/invoices/hooks/useCreateInvoice.ts` | Created |
| `apps/web/src/features/invoices/hooks/useSendInvoice.ts` | Created |
| `apps/web/src/features/invoices/hooks/useRecordPayment.ts` | Created |
| `apps/web/src/features/dashboard/hooks/useArSummary.ts` | Created |
| `apps/web/src/features/invoices/components/InvoiceDetailPage.tsx` | Created |
| `apps/web/src/features/invoices/components/InvoiceLineItemsTable.tsx` | Created |
| `apps/web/src/features/invoices/components/InvoicePaymentHistory.tsx` | Created |
| `apps/web/src/features/invoices/components/RecordPaymentModal.tsx` | Created |
| `apps/web/src/features/invoices/components/SendInvoicePreviewModal.tsx` | Created |
| `apps/web/src/features/invoices/components/TaxSetupSubFlowModal.tsx` | Created |
| `apps/web/src/features/dashboard/components/ArSummaryWidget.tsx` | Created |
| `apps/web/src/features/invoices/components/InvoicesPage.tsx` | Updated |
| `apps/web/src/app/(authed)/dashboard/page.tsx` | Updated |
| `apps/web/src/app/(authed)/invoices/[id]/page.tsx` | Created |
| `apps/web/src/features/customers/components/CustomerInvoicesList.tsx` | Updated |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `features/invoices/components/__tests__/SendInvoicePreviewModal.test.tsx` | Unit | N | ✅ |
| `features/invoices/components/__tests__/RecordPaymentModal.test.tsx` | Unit | N | ✅ |
| `features/invoices/components/__tests__/TaxSetupSubFlowModal.test.tsx` | Unit | N | ✅ |
| `features/invoices/components/__tests__/InvoiceLineItemsTable.test.tsx` | Unit | N | ✅ |
| `features/dashboard/components/__tests__/ArSummaryWidget.test.tsx` | Unit | N | ✅ |
| `apps/web/src/__tests__/batch_fe_b22/invoiceDetail.integration.test.tsx` | Integration | N | ✅ |
| `apps/web/src/__tests__/batch_fe_b22/invoiceTaxSetup.integration.test.tsx` | Integration | N | ✅ |
```

---

## After This Batch

FE-B22 is complete. The core product loop on web is now fully operational:

**Catalog → Customer → Quote → Send → Accept → Convert to Job → Job Detail → Convert to Invoice → Invoice Detail → Record Payment**

**Next batch**: `batch-fe-b23-design.md` — Dashboard Business Intelligence + Notification Bell + Voice on Web. This is a mixed batch (Python Engr + React Engr).
