# Implementation Prompt: UI-FIX-1B — Quote Approved Flow + AR Widget Links + Payment History

**Mode**: Pilot React Engineer  
**Batch**: UI-FIX-1B  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §UI Fix — Batch 1  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-ui-fix-1b-design.md`  
**Estimated session**: 3–4 hours  
**Platform**: Web only (`apps/web`)  
**Backend companion**: UI-FIX-1A ✅ complete — `pnpm sync-api-types` **REQUIRED** before starting

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-ui-fix-1b-design.md`** — every section (A–I)

**Critical rules for this batch:**

- **Rule 1.1**: Before writing ANY hook or API call, verify the endpoint exists in `backend/openapi_schema_map.md`. If it is NOT there → **STOP and ask Tom**.
- **Rule 1.2**: Do NOT invent URL patterns or parameter names. Every shape comes from `openapi.json` or the design doc.
- **Rule 1.3**: Run `pnpm sync-api-types` before starting — all TypeScript types for backend payloads come from `@pilot/shared-types`. The UI-FIX-1A Python Engineer batch added `PaymentSummaryResponse` to `InvoiceResponse` — these types are now live in the backend OpenAPI spec.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned for `/api/v1/...` calls.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new component — `<LoadingState>`, `<ErrorState>`, `<EmptyState>`, `<RoleGate>` are available.
- **Rule 8**: No new npm dependencies without first checking what is already installed in `package.json`.
- **Rule 9**: Route files in `apps/web/src/app/(authed)/` MUST be thin server components — no `"use client"`, no data fetching.
- **Rule 10**: If ANY test fails during your work — even pre-existing — you must fix it before declaring the batch done.

**Invoice status "overdue" rule (FIX-010b):**  
`invoice_status` table has NO "overdue" code. Overdue is a derived display state: `due_at < TODAY AND status NOT IN ('paid', 'void', 'writeoff')`. The `isOverdue()` helper in `InvoicesPage.tsx` implements this correctly — use it. Never send `?status=overdue` to the API.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| `approved` list action | Navigate to `/quotes/{id}` detail page — not direct public-link generation | Matches UX pattern; preview modal on detail page handles confirmation |
| AR bucket link `Current` | Links to `/invoices` with no filter | "Current" means not overdue — all overdue filters use `?overdue=true` |
| `PaymentEntry.idempotency_key` removal | Replaced by `customer_payment_comment` + `psp_provider` fallback | `idempotency_key` not in `PaymentSummaryResponse` from backend |
| `status_id` in `PaymentSummaryEntry` | Included in interface, NOT rendered | Forward-compatibility; no payment status badge in this batch |
| Aging column sorting | Client-side only (sort by bucket string) | Server-side sort is FIX-014 / UI-FIX-1C — not this batch |

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend

# Web tests only — this batch is web-only
pnpm --filter web test 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**.

> **If any tests are already failing before you start**: Do NOT treat them as "pre-existing" and proceed. Either confirm with Tom (with documented reason) OR fix the failure before touching any batch files.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

This regenerates `packages/shared-types/src/api-schema.d.ts`. The UI-FIX-1A Python Engineer batch added `PaymentSummaryResponse` to `InvoiceResponse` — these types are now live. Verify:

```bash
grep -n "payments\|PaymentSummary" frontend/packages/shared-types/src/api-schema.d.ts | head -10
```

> **If `pnpm sync-api-types` fails** (backend not running locally): use the local interface stubs in design doc §D (marked with `// TODO: replace with @pilot/shared-types when stable`). Do not block work.

---

## Pre-Work: Verify Endpoints

All endpoints used in this batch are already live — no new endpoints needed.

```bash
# Verify quote public-link endpoint
grep -A 5 "versions.*public-link" backend/openapi_schema_map.md | head -10

# Verify invoices list accepts due_before
grep -A 5 "GET /api/v1/invoices/" backend/openapi_schema_map.md | head -10

# Verify invoice detail returns payments
grep -A 20 "GET /api/v1/invoices/{invoice_id}" backend/openapi_schema_map.md | head -25
```

**Verified endpoints for this batch:**

| Hook | Endpoint | Status |
|---|---|---|
| `useGeneratePublicLink` | `POST /api/v1/quotes/{id}/versions/{versionId}/public-link` | ✅ Confirmed live |
| `useInvoice` | `GET /api/v1/invoices/{invoiceId}` | ✅ Confirmed live; `payments` field added by UI-FIX-1A |
| `useInvoices` | `GET /api/v1/invoices/` | ✅ Confirmed live; `?due_before=` param already live |

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

```
frontend/apps/web/src/features/quotes/components/QuotesPage.tsx
  ← understand STATUS_FILTERS array and actions column cell structure

frontend/apps/web/src/features/quotes/components/QuoteActionBar.tsx
  ← understand isDraft/isSent/isAccepted guards and existing Send button

frontend/apps/web/src/features/quote-approval/QuoteDetailPage.tsx
  ← understand QuoteActionBar mount condition (isDraft || isAccepted)

frontend/apps/web/src/features/invoices/hooks/useInvoice.ts
  ← understand InvoiceResponse interface before adding payments field

frontend/apps/web/src/features/invoices/components/InvoiceDetailPage.tsx
  ← find exact line 218 <InvoicePaymentHistory /> call

frontend/apps/web/src/features/invoices/components/InvoicePaymentHistory.tsx
  ← understand PaymentEntry interface before updating it

frontend/apps/web/src/features/dashboard/components/ArSummaryWidget.tsx
  ← understand bucket map structure before adding Link wrappers

frontend/apps/web/src/features/invoices/components/InvoicesPage.tsx
  ← understand column definition structure and isOverdue() helper location

frontend/apps/web/src/features/invoices/hooks/useInvoices.ts
  ← verify whether due_before param is already supported

frontend/apps/web/src/mocks/handlers/invoiceDetailHandlers.ts
  ← understand existing mock structure before adding payments to mock response

frontend/apps/web/src/mocks/handlers/index.ts
  ← confirm all handler registrations before adding any new ones
```

Also run:

```bash
# Find QuoteActionBar tests
find frontend/apps/web/src -name "QuoteActionBar.test.tsx" | head -5

# Find InvoicePaymentHistory tests (if any)
find frontend/apps/web/src -name "InvoicePaymentHistory.test*" | head -5

# Find ArSummaryWidget tests
find frontend/apps/web/src -name "ArSummaryWidget.test.tsx" | head -5

# Confirm useInvoices due_before support
grep -n "due_before" frontend/apps/web/src/features/invoices/hooks/useInvoices.ts
```

---

## Context: What This Batch Does

Three UI defects discovered during hands-on testing (2026-07-16):

| Fix | Surface | Issue | Change |
|---|---|---|---|
| FIX-001 | Quotes list + Quote detail | `approved` status is invisible — no filter pill, no action, action bar hidden | 4 targeted code changes across 3 files |
| FIX-010 | Dashboard AR widget + Invoices list | AR widget buckets are not clickable; no aging column on invoices list | Link wrappers + new computed column |
| FIX-013-FE | Invoice detail page | Payment history always empty — `<InvoicePaymentHistory />` called with no props | Pass `invoice.payments` from `useInvoice` |

No new components. No new routes. No new permissions. No new npm packages.

---

## STEP 1 — FIX-001: Quote Approved Flow (3 files, 4 changes)

### Step 1a — QuotesPage.tsx: Add `approved` filter pill

**File**: `apps/web/src/features/quotes/components/QuotesPage.tsx`

Read the file first. In the `STATUS_FILTERS` array (line 31), add `approved` **after** `pending_approval`:

```tsx
const STATUS_FILTERS = [
  { label: "All", value: undefined },
  { label: "Draft", value: "draft" },
  { label: "Pending Approval", value: "pending_approval" },
  { label: "Approved", value: "approved" },   // ← ADD
  { label: "Sent", value: "sent" },
  { label: "Accepted", value: "accepted" },
  { label: "Expired", value: "expired" },
] as const;
```

> `STATUS_COLORS` at line 45 already has `approved: "bg-margin-100 text-margin-700"` — no change needed there.

### Step 1b — QuotesPage.tsx: Add `approved` action in the table

In the actions column `cell`, after the `pending_approval` case (around line 233), add the `approved` case:

```tsx
{/* Approved: navigate to detail to send to customer */}
{q.status_code === "approved" && (
  <RoleGate permission="quotes.edit">
    <a
      href={`/quotes/${q.id}`}
      className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border border-brand-200 bg-brand-50 text-brand-600 hover:bg-brand-100 transition-colors"
    >
      Send to Customer
    </a>
  </RoleGate>
)}
```

> Adjust prop names and class names to match what you find in the file — copy the exact pattern from the `pending_approval` case.

**Intermediate verification:**

```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/features/quotes 2>&1 | tail -8
```

### Step 1c — QuoteActionBar.tsx: Add `isApproved` guard + button

**File**: `apps/web/src/features/quotes/components/QuoteActionBar.tsx`

Read the file first. After line 51 (`const isAccepted = Boolean(customerAcceptedAt);`):

```tsx
const isApproved = status === "approved";  // ← ADD
```

Update the early return guard on line 53:

```tsx
if (!isDraft && !isApproved && !(isSent && isAccepted)) return null;
```

Add the `isApproved` action block inside the JSX, between the draft block and the sent+accepted block:

```tsx
{/* Approved: owner/operator sends to customer */}
{isApproved && (
  <RoleGate permission="quotes.edit">
    <button
      type="button"
      onClick={() => setShowPreviewModal(true)}
      disabled={publicLinkMutation.isPending}
      className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-md hover:bg-brand-700 transition-colors disabled:opacity-50"
      data-testid="send-to-customer-approved-btn"
    >
      Send to Customer
    </button>
  </RoleGate>
)}
```

> The `SendQuotePreviewModal`, `setShowPreviewModal`, and `publicLinkMutation` are already wired — this reuses the identical pattern as the draft "Send to Customer" button. No new hooks or state needed.

### Step 1d — QuoteDetailPage.tsx: Add `isApproved` to mount condition

**File**: `apps/web/src/features/quote-approval/QuoteDetailPage.tsx`

Read the file first. After line 57 (`const isAccepted = quote?.status === "accepted";`):

```tsx
const isApproved = quote?.status === "approved";  // ← ADD
```

Update the `QuoteActionBar` mount condition (around line 274):

```tsx
{/* FE-B19 + UI-FIX-1B: Draft + Approved + Accepted action bar */}
{(isDraft || isApproved || isAccepted) && (
  <QuoteActionBar
    quoteId={quoteId}
    status={quote.status ?? "draft"}
    customerAcceptedAt={isAccepted ? "accepted" : null}
    customerEmail={null}
    customerName={quote.customer_name ?? "Customer"}
    quoteVersionId={quote.quote_version_id ?? ""}
    testID="quote-action-bar"
  />
)}
```

**Intermediate verification:**

```bash
pnpm --filter web test -- apps/web/src/features/quotes 2>&1 | tail -8
pnpm --filter web test -- apps/web/src/features/quote-approval 2>&1 | tail -8
```

---

## STEP 2 — FIX-013-FE: Invoice Payment History

### Step 2a — useInvoice.ts: Add payments to InvoiceResponse

**File**: `apps/web/src/features/invoices/hooks/useInvoice.ts`

Read the file first. Add `PaymentSummaryEntry` interface before `InvoiceResponse`:

```tsx
// TODO: replace with @pilot/shared-types InvoiceResponse when pnpm sync-api-types delivers this type
export interface PaymentSummaryEntry {
  id: string;
  amount_cents: number;
  paid_at: string | null;
  paid_via: string | null;
  psp_provider: string | null;
  customer_payment_comment: string | null;
  status_id: string;
}
```

Add `payments` to `InvoiceResponse` **after** `lines`:

```tsx
lines: InvoiceLineResponse[];
payments: PaymentSummaryEntry[];   // ← ADD
```

### Step 2b — InvoicePaymentHistory.tsx: Update PaymentEntry interface

**File**: `apps/web/src/features/invoices/components/InvoicePaymentHistory.tsx`

Read the file first. Replace the existing `PaymentEntry` interface with:

```tsx
interface PaymentEntry {
  id: string;
  amount_cents: number;
  paid_via: string | null;
  paid_at: string | null;
  psp_provider: string | null;
  customer_payment_comment: string | null;
}
```

Update the `InvoicePaymentHistoryProps`:

```tsx
interface InvoicePaymentHistoryProps {
  payments?: PaymentEntry[];
}
```

Update the "Reference" column cell (currently uses `idempotency_key`):

```tsx
<td className="px-4 py-3 text-neutral-500 text-xs">
  {p.customer_payment_comment ?? p.psp_provider ?? "—"}
</td>
```

Update the table body `map` call — adjust `p.paid_via` for nullable:

```tsx
<td className="px-4 py-3 text-neutral-600 capitalize">
  {p.paid_via ? p.paid_via.replace(/_/g, " ") : "—"}
</td>
```

### Step 2c — InvoiceDetailPage.tsx: Pass payments prop

**File**: `apps/web/src/features/invoices/components/InvoiceDetailPage.tsx`

Read the file first. Locate line 218:

```tsx
<InvoicePaymentHistory />
```

Replace with:

```tsx
<InvoicePaymentHistory payments={invoice.payments ?? []} />
```

> `invoice` comes from `useInvoice(invoiceId)` — its type is `InvoiceResponse` which now includes `payments: PaymentSummaryEntry[]`.

**Intermediate verification:**

```bash
pnpm --filter web test -- apps/web/src/features/invoices 2>&1 | tail -8
```

---

## STEP 3 — FIX-010: AR Widget Links + Aging Column

### Step 3a — useInvoices.ts: Verify `due_before` param

**File**: `apps/web/src/features/invoices/hooks/useInvoices.ts`

Read the file. Run `grep -n "due_before" frontend/apps/web/src/features/invoices/hooks/useInvoices.ts`.

If `due_before` is NOT already a param, add it to the params interface and append to the query string:

```tsx
// In the params interface:
due_before?: string;

// In queryFn, before the fetch:
if (params.due_before) searchParams.append("due_before", params.due_before);
```

If it IS already there — no change needed.

### Step 3b — ArSummaryWidget.tsx: Make bucket rows clickable

**File**: `apps/web/src/features/dashboard/components/ArSummaryWidget.tsx`

Read the file first. Add `import Link from "next/link"` at the top.

Add date computation helpers before the return (inside the component, after `const total`):

```tsx
const today = new Date();
function subtractDays(d: Date, days: number): string {
  const copy = new Date(d);
  copy.setDate(d.getDate() - days);
  return copy.toISOString().split("T")[0]; // YYYY-MM-DD for query param
}
```

Update the `buckets` array to include an `href` field:

```tsx
const buckets = [
  {
    label: "Current",
    key: "current",
    cents: summary.current_cents,
    colorClass: "text-margin-700",
    href: "/invoices",
  },
  {
    label: "30+ days",
    key: "30d",
    cents: summary.bucket_31_60_cents,
    colorClass: "text-alert-600",
    href: `/invoices?overdue=true&due_before=${subtractDays(today, 30)}`,
  },
  {
    label: "60+ days",
    key: "60d",
    cents: summary.bucket_61_90_cents,
    colorClass: "text-alert-700",
    href: `/invoices?overdue=true&due_before=${subtractDays(today, 60)}`,
  },
  {
    label: "90+ days",
    key: "90d",
    cents: summary.bucket_91_plus_cents,
    colorClass: "text-fault-700",
    href: `/invoices?overdue=true&due_before=${subtractDays(today, 90)}`,
  },
];
```

Wrap each bucket row in `<Link>` (replace the existing `<div>` wrapper):

```tsx
{buckets.map((bucket) => (
  <Link
    key={bucket.key}
    href={bucket.href}
    className="flex items-center justify-between hover:bg-neutral-50 rounded px-1 -mx-1 transition-colors"
    data-testid={`ar-bucket-${bucket.key}`}
  >
    <span className="text-sm text-neutral-600">{bucket.label}</span>
    <span className={`text-sm font-medium ${bucket.colorClass}`}>
      {formatCents(bucket.cents)}
    </span>
  </Link>
))}
```

Also wrap the "Total Outstanding" row in a `<Link href="/invoices?overdue=true">`.

> Adjust exact class names to match what you find in the existing file.

### Step 3c — InvoicesPage.tsx: Add Aging column

**File**: `apps/web/src/features/invoices/components/InvoicesPage.tsx`

Read the file first. Add helper functions near the top (after the existing `isOverdue` helper):

```tsx
function getAgingBucket(invoice: { due_at: string | null; status_code: string }): string {
  if (!isOverdue(invoice)) return "Current";
  const daysOverdue = Math.floor(
    (Date.now() - new Date(invoice.due_at!).getTime()) / 86_400_000
  );
  if (daysOverdue <= 60) return "30+";
  if (daysOverdue <= 90) return "60+";
  return "90+";
}

const AGING_BADGE: Record<string, string> = {
  Current: "bg-margin-100 text-margin-700",
  "30+":    "bg-alert-100 text-alert-600",
  "60+":    "bg-alert-100 text-alert-700",
  "90+":    "bg-fault-100 text-fault-700",
};
```

Add the Aging column **after** the `due_at` column (after the closing `}),` of the `due_at` column around line 252):

```tsx
columnHelper.display({
  id: "aging",
  header: "Aging",
  size: 90,
  minSize: 70,
  enableResizing: false,
  enableSorting: false,
  cell: (info) => {
    const inv = info.row.original;
    if (["paid", "void", "writeoff"].includes(inv.status_code)) {
      return <span className="text-neutral-400 text-xs">—</span>;
    }
    const bucket = getAgingBucket(inv);
    return (
      <span
        className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${AGING_BADGE[bucket]}`}
      >
        {bucket}
      </span>
    );
  },
}),
```

**Intermediate verification:**

```bash
pnpm --filter web test -- apps/web/src/features/invoices 2>&1 | tail -8
pnpm --filter web test -- apps/web/src/features/dashboard 2>&1 | tail -8
```

---

## STEP 4 — Update MSW Handlers for Invoice Detail

**File**: `apps/web/src/mocks/handlers/invoiceDetailHandlers.ts`

Read the file first. Find the handler for `GET /api/v1/invoices/:invoiceId`. Update its mock response to include a `payments` array.

Add at least one payment entry to the mock invoice response (for tests that check payment history rendering):

```typescript
payments: [
  {
    id: "pay-mock-001",
    amount_cents: 80000,
    paid_at: "2026-07-01T00:00:00Z",
    paid_via: "check",
    psp_provider: null,
    customer_payment_comment: "July partial payment",
    status_id: "ps-mock-001",
  },
],
```

Also add a separate mock handler variant or ensure the existing handler's mock data has `payments: []` for the empty state test.

> Do NOT add new handler files unless the invoice detail mock doesn't already exist. Check `index.ts` before creating anything.

---

## Test Requirements

### TanStack Query — Required Setup for All Tests

Always use `retry: false` on the QueryClient in tests:

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

### Required Test: QuoteActionBar — `status="approved"` renders Send button

**File**: `apps/web/src/features/quotes/components/__tests__/QuoteActionBar.test.tsx`

Read the existing test file first. Add a new test case (do not overwrite existing tests):

```typescript
it("approved status: renders Send to Customer button for owner (quotes.edit role)", () => {
  // Render with status="approved" and owner role
  // Assert "Send to Customer" button is visible
  // Assert the early-return guard did NOT fire (container is not null/empty)
});

it("approved status: renders nothing for tech role (no quotes.edit permission)", () => {
  // Render with status="approved" and tech role
  // Assert container is empty (RoleGate blocks the button)
});
```

Adjust to match the exact test setup pattern you find in the existing test file (AuthContext mock pattern, render approach, etc.).

### Required Test: InvoiceDetailPage — payments prop passed

Locate or create `apps/web/src/__tests__/batch_ui_fix_1b/invoice_payment_history.integration.test.tsx`:

```typescript
// Test 1: InvoicePaymentHistory renders payment rows when invoice.payments is populated
// - Mock useInvoice to return an invoice with payments: [{ id, amount_cents, paid_at, paid_via, ... }]
// - Render InvoiceDetailPage (or InvoicePaymentHistory directly with props)
// - Assert payment row is visible with correct amount

// Test 2: InvoicePaymentHistory shows empty state when invoice.payments is []
// - Mock useInvoice to return invoice with payments: []
// - Assert "No payments recorded" empty state text is visible
```

### Required Test: ArSummaryWidget — bucket rows are Links

Update the existing test in `apps/web/src/features/dashboard/components/__tests__/ArSummaryWidget.test.tsx`:

```typescript
it("bucket rows are clickable links to invoices page", () => {
  // Render ArSummaryWidget with non-zero AR data
  // Assert the "30+ days" bucket row renders as a link (<a> or Link)
  // Assert href contains "/invoices?overdue=true&due_before="
  // (Next.js Link renders as <a> in jsdom)
});
```

### MSW in Tests

```typescript
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

### Next.js mocks required for web tests

```typescript
vi.mock("next/navigation", () => ({ usePathname: () => "/dashboard", useRouter: () => ({ push: vi.fn(), back: vi.fn() }), useSearchParams: () => new URLSearchParams() }));
vi.mock("next/link", () => ({ default: ({ href, children, ...rest }: any) => React.createElement("a", { href, ...rest }, children) }));
```

---

## Final Verification

> ❌ **BANNED COMMAND**: `npx vitest run` — **NEVER use this**. The ONLY correct test runner is `pnpm --filter web test`.

### Phase 1 — Targeted tests (run after each step group)

```bash
cd <repo>/frontend

pnpm --filter web test -- apps/web/src/features/quotes 2>&1 | tail -6
pnpm --filter web test -- apps/web/src/features/quote-approval 2>&1 | tail -6
pnpm --filter web test -- apps/web/src/features/invoices 2>&1 | tail -6
pnpm --filter web test -- apps/web/src/features/dashboard 2>&1 | tail -6
pnpm --filter web test -- apps/web/src/__tests__/batch_ui_fix_1b 2>&1 | tail -8
```

Fix any failure before moving to the next step — including failures that appear pre-existing.

### Phase 2 — Full verification (run once at the very end)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

> Any failure in either phase must be fixed before the batch is declared done.

---

## Definition of Done — UI-FIX-1B

Update `dev-docs/architecture-design/batch-designs/ui-fix-1-decisions.md` §Implementation Batches when complete:

- [ ] Pre-modification regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — `payments` field visible in `packages/shared-types/src/api-schema.d.ts`
- [ ] Design doc fully read before writing any code (sections A–I)
- [ ] All mandatory source files read before modifying
- [ ] All endpoint URLs verified in `openapi_schema_map.md`
- [ ] **Step 1a**: `approved` added to `STATUS_FILTERS` in `QuotesPage.tsx`
- [ ] **Step 1b**: `approved` action ("Send to Customer" link to `/quotes/{id}`) added in actions column
- [ ] **Step 1c**: `isApproved` guard added to `QuoteActionBar.tsx`; Send to Customer button renders for `approved`
- [ ] **Step 1d**: `isApproved` added to `QuoteDetailPage.tsx` mount condition
- [ ] **Step 2a**: `PaymentSummaryEntry` interface + `payments` field added to `useInvoice.ts` `InvoiceResponse`
- [ ] **Step 2b**: `InvoicePaymentHistory.tsx` `PaymentEntry` interface updated; Reference column uses `customer_payment_comment`
- [ ] **Step 2c**: `InvoiceDetailPage.tsx` passes `invoice.payments ?? []` to `<InvoicePaymentHistory>`
- [ ] **Step 3a**: `useInvoices.ts` accepts `due_before` param (added if missing)
- [ ] **Step 3b**: `ArSummaryWidget.tsx` bucket rows wrapped in `<Link>` with `?due_before=` params
- [ ] **Step 3c**: `InvoicesPage.tsx` `getAgingBucket()` helper + Aging column added after Due column
- [ ] **Step 4**: `invoiceDetailHandlers.ts` updated to include `payments` array in mock invoice response
- [ ] No `"use client"` on route files in `app/(authed)/`
- [ ] All new `<Link>` uses Next.js `<Link>` (not `<a>`) for internal navigation
- [ ] `QuoteActionBar.test.tsx` — new test cases for `status="approved"` pass
- [ ] `invoice_payment_history.integration.test.tsx` — 2 test cases pass (populated + empty state)
- [ ] `ArSummaryWidget.test.tsx` — bucket links test passes
- [ ] Zero TypeScript errors (`pnpm --filter web check-types` passes)
- [ ] Zero ESLint warnings (`pnpm --filter web lint` passes)
- [ ] No regressions in pre-existing test suite
- [ ] **Phase 2 FULL verification command passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`)
- [ ] `ui-fix-1-decisions.md` — UI-FIX-1B row updated to ✅ Complete

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** to `ui-fix-1-decisions.md` §Implementation Batches.
2. Update the `UI-FIX-1B` row in the Batch Overview table to ✅ Complete.

```markdown
### UI-FIX-1B — Quote Approved Flow + AR Widget Links + Payment History: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed, Y failed (web)
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished

- FIX-001: approved status now has filter pill, list action, action bar visibility, and Send to Customer flow
- FIX-010: AR widget bucket rows are clickable Links; invoice list has computed Aging column
- FIX-013-FE: InvoiceDetailPage now passes invoice.payments to InvoicePaymentHistory; payment history visible

#### Files Changed / Created

| File | Action |
|---|---|
| `apps/web/src/features/quotes/components/QuotesPage.tsx` | Updated — approved filter pill + action |
| `apps/web/src/features/quotes/components/QuoteActionBar.tsx` | Updated — isApproved guard + Send button |
| `apps/web/src/features/quote-approval/QuoteDetailPage.tsx` | Updated — isApproved mount condition |
| `apps/web/src/features/invoices/hooks/useInvoice.ts` | Updated — PaymentSummaryEntry + payments field |
| `apps/web/src/features/invoices/components/InvoicePaymentHistory.tsx` | Updated — PaymentEntry interface + Reference column |
| `apps/web/src/features/invoices/components/InvoiceDetailPage.tsx` | Updated — pass payments prop |
| `apps/web/src/features/dashboard/components/ArSummaryWidget.tsx` | Updated — Link wrappers on buckets |
| `apps/web/src/features/invoices/components/InvoicesPage.tsx` | Updated — getAgingBucket + Aging column |
| `apps/web/src/features/invoices/hooks/useInvoices.ts` | Updated (if needed) — due_before param |
| `apps/web/src/mocks/handlers/invoiceDetailHandlers.ts` | Updated — payments in mock response |
| `apps/web/src/__tests__/batch_ui_fix_1b/invoice_payment_history.integration.test.tsx` | Created — 2 tests |

#### Tests Added

| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `features/quotes/components/__tests__/QuoteActionBar.test.tsx` | Unit | +2 | ✅ |
| `__tests__/batch_ui_fix_1b/invoice_payment_history.integration.test.tsx` | Integration | 2 | ✅ |
| `features/dashboard/components/__tests__/ArSummaryWidget.test.tsx` | Unit | +1 | ✅ |
```
