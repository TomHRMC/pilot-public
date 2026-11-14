# Batch UI-FIX-1B — Quote Approved Flow + AR Widget Links + Payment History

**Type**: Frontend — Web only (`apps/web`)  
**Status**: 🟡 Ready for implementation  
**Designed**: 2026-07-17  
**Source findings**: `dev-docs/architecture-design/batch-designs/ui-fix-1-decisions.md`  
**Fixes addressed**: FIX-001, FIX-010, FIX-013-FE  
**Estimated effort**: 3–4 hours  
**Backend prerequisite**: UI-FIX-1A ✅ complete — React Engineer must run `pnpm sync-api-types` before starting  

---

## Table of Contents

- [A. Input Read Summary](#a-input-read-summary)
- [B. Migration Plan](#b-migration-plan)
- [C. Execution Order](#c-execution-order)
- [D. Component Changes](#d-component-changes)
- [E. Pattern Reuse Decisions](#e-pattern-reuse-decisions)
- [F. Shared Module Interfaces](#f-shared-module-interfaces)
- [G. Open Questions Resolved](#g-open-questions-resolved)
- [H. Surface Mockup Reference](#h-surface-mockup-reference)
- [I. Component Manifest](#i-component-manifest)

---

## A. Input Read Summary

| Input | Key finding |
|---|---|
| `QuotesPage.tsx` | `STATUS_FILTERS` has `draft`, `pending_approval`, `sent`, `accepted`, `expired` — **missing `approved`** |
| `QuotesPage.tsx–250` | Actions column has cases for `draft`, `pending_approval`, `accepted` — **no `approved` case** |
| `QuoteActionBar.tsx` | Guard `if (!isDraft && !(isSent && isAccepted)) return null` — **`approved` excluded** |
| `QuoteDetailPage.tsx` | `{(isDraft \|\| isAccepted) && <QuoteActionBar ...>}` — **`approved` excluded** |
| `QuoteActionBar.tsx` | `useGeneratePublicLink` already imported and used for the "Send to Customer" button in draft flow — **no new hook needed** |
| `openapi_schema_map.md` | `POST /api/v1/quotes/{quote_id}/versions/{version_id}/public-link` ✅ confirmed — accepts calls from non-terminal statuses |
| `ArSummaryWidget.tsx–115` | 4 bucket rows are plain `<div>` elements with no `<Link>` wrapper — **not clickable** |
| `openapi_schema_map.md` | `GET /api/v1/invoices/` already accepts `?due_before=` (confirmed live ✅) — no backend change needed |
| `InvoicesPage.tsx` | `isOverdue()` helper already exists and is exported from `InvoicesPage.tsx` |
| `InvoicesPage.tsx–252` | Last column is `due_at` (header "Due") — Aging column goes **after** this column |
| `InvoiceDetailPage.tsx` | `<InvoicePaymentHistory />` called with **no props** — always renders empty |
| `InvoicePaymentHistory.tsx–24` | `PaymentEntry` interface has `id`, `amount_cents`, `paid_via`, `paid_at`, `idempotency_key` — mismatch with backend's `PaymentSummaryResponse` |
| `useInvoice.ts–57` | `InvoiceResponse` interface is **hand-written** — no `payments` field; backend `PaymentSummaryResponse` returns `id`, `amount_cents`, `paid_at`, `paid_via`, `psp_provider`, `customer_payment_comment`, `status_id` |
| `openapi_schema_map.md` | Invoice detail endpoint returns `PaymentSummaryResponse` after UI-FIX-1A — confirmed via `pnpm sync-api-types` |

---

## B. Migration Plan

**No DB migrations.** This is a pure frontend batch. No new API endpoints. No backend changes.

The `payments` field on `InvoiceResponse` is added by UI-FIX-1A (Python Engineer). After `pnpm sync-api-types`, `@pilot/shared-types` will include the updated type. The hand-written `InvoiceResponse` interface in `useInvoice.ts` must be updated to include `payments` locally (until full migration to `@pilot/shared-types` is done).

---

## C. Execution Order

| # | Task | Files | Fix |
|---|---|---|---|
| 1 | Run `pnpm sync-api-types` — confirm `payments` field visible in shared types | `packages/shared-types/src/api-schema.d.ts` | Prerequisite |
| 2 | Add `approved` to `STATUS_FILTERS` in `QuotesPage.tsx` | `QuotesPage.tsx` | FIX-001a |
| 3 | Add `approved` action ("Send to Customer" link) in actions column | `QuotesPage.tsx` | FIX-001b |
| 4 | Add `isApproved` guard to `QuoteActionBar.tsx` | `QuoteActionBar.tsx` | FIX-001c |
| 5 | Add `isApproved` to `QuoteDetailPage.tsx` mount condition | `QuoteDetailPage.tsx` | FIX-001d |
| 6 | Add `PaymentSummaryEntry` interface + `payments` to `useInvoice.ts` | `useInvoice.ts` | FIX-013a |
| 7 | Update `InvoicePaymentHistory.tsx` — align `PaymentEntry` interface with backend, update Reference column | `InvoicePaymentHistory.tsx` | FIX-013b |
| 8 | Fix `InvoiceDetailPage.tsx` — pass `invoice.payments` to `<InvoicePaymentHistory>` | `InvoiceDetailPage.tsx` | FIX-013c |
| 9 | Make AR bucket rows clickable in `ArSummaryWidget.tsx` | `ArSummaryWidget.tsx` | FIX-010a |
| 10 | Add computed "Aging" column to `InvoicesPage.tsx` | `InvoicesPage.tsx` | FIX-010b |
| 11 | Update MSW handlers for invoice detail to include `payments` array | `invoiceDetailHandlers.ts` | Test support |
| 12 | Write/update tests | `QuoteActionBar.test.tsx`, `ArSummaryWidget.test.tsx`, new `InvoiceDetailPage` test | All |

---

## D. Component Changes

### FIX-001a — Add `approved` to STATUS_FILTERS (QuotesPage.tsx)

After `{ label: "Pending Approval", value: "pending_approval" }`, add:

```tsx
{ label: "Approved", value: "approved" },
```

The `STATUS_COLORS` map already has `approved: "bg-margin-100 text-margin-700"` (line 45) — no change needed there.

---

### FIX-001b — Add `approved` action in actions column (QuotesPage.tsx)

In the actions column `cell` (around line 220), after the `pending_approval` case, add:

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

> Note: This navigates to the detail page — the `QuoteActionBar` on the detail page handles the actual public-link generation. We do NOT generate the public link directly from the list row action.

---

### FIX-001c — Add `isApproved` guard to QuoteActionBar.tsx

In `QuoteActionBar.tsx`, after line 51:

```tsx
const isDraft = status === "draft";
const isSent = status === "sent";
const isAccepted = Boolean(customerAcceptedAt);
const isApproved = status === "approved";  // ← ADD

if (!isDraft && !isApproved && !(isSent && isAccepted)) return null;  // ← UPDATE
```

Add the `approved` action block inside the JSX, after the draft block and before the sent+accepted block:

```tsx
{/* Approved: owner/operator sends to customer */}
{isApproved && (
  <RoleGate permission="quotes.edit">
    <button
      type="button"
      onClick={() => setShowPreviewModal(true)}
      disabled={publicLinkMutation.isPending}
      className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-md hover:bg-brand-700 transition-colors disabled:opacity-50"
    >
      Send to Customer
    </button>
  </RoleGate>
)}
```

The `SendQuotePreviewModal` and `publicLinkMutation` are already wired — this reuses the exact same pattern as the draft "Send to Customer" button. The modal and `onConfirm` callback require no changes.

---

### FIX-001d — Add `isApproved` to QuoteDetailPage.tsx mount condition

In `QuoteDetailPage.tsx`, around line 54-58, add:

```tsx
const isApproved = quote?.status === "approved";  // ← ADD
```

Around line 274, update:

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

---

### FIX-013a — Add `payments` to useInvoice.ts

Add `PaymentSummaryEntry` interface and extend `InvoiceResponse`:

```tsx
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

Add to `InvoiceResponse` after `lines`:

```tsx
payments: PaymentSummaryEntry[];
```

> **Note**: This is a local interface update. The canonical type after `pnpm sync-api-types` comes from `@pilot/shared-types`. Mark this with a comment: `// TODO: replace with @pilot/shared-types InvoiceResponse when sync-api-types is stable`

---

### FIX-013b — Update InvoicePaymentHistory.tsx interface

Update `PaymentEntry` to match `PaymentSummaryEntry`:

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

Update the "Reference" column cell to use `customer_payment_comment`:

```tsx
<td className="px-4 py-3 text-neutral-500 text-xs">
  {p.customer_payment_comment ?? p.psp_provider ?? "—"}
</td>
```

> **Design decision**: `idempotency_key` is not in `PaymentSummaryResponse` — replaced by `customer_payment_comment` as the "Reference" display field. `psp_provider` shown as fallback for Stripe payments.

---

### FIX-013c — Fix InvoiceDetailPage.tsx to pass payments

Line 218 currently:

```tsx
<InvoicePaymentHistory />
```

Replace with:

```tsx
<InvoicePaymentHistory payments={invoice.payments ?? []} />
```

`invoice` comes from `useInvoice(invoiceId)` — its type is `InvoiceResponse` which now includes `payments: PaymentSummaryEntry[]`.

---

### FIX-010a — Make AR bucket rows clickable (ArSummaryWidget.tsx)

Add `import Link from "next/link"` at the top of the file.

Compute the `due_before` dates at render time (before the bucket map):

```tsx
const today = new Date();
const date30dAgo = new Date(today);
date30dAgo.setDate(today.getDate() - 30);
const date60dAgo = new Date(today);
date60dAgo.setDate(today.getDate() - 60);
const date90dAgo = new Date(today);
date90dAgo.setDate(today.getDate() - 90);

function toISODateParam(d: Date): string {
  return d.toISOString().split("T")[0]; // YYYY-MM-DD
}
```

Update the `buckets` array to include an `href`:

```tsx
const buckets = [
  {
    label: "Current",
    key: "current",
    cents: summary.current_cents,
    colorClass: "text-margin-700",
    href: "/invoices",  // current = not overdue; no filter needed
  },
  {
    label: "30+ days",
    key: "30d",
    cents: summary.bucket_31_60_cents,
    colorClass: "text-alert-600",
    href: `/invoices?overdue=true&due_before=${toISODateParam(date30dAgo)}`,
  },
  {
    label: "60+ days",
    key: "60d",
    cents: summary.bucket_61_90_cents,
    colorClass: "text-alert-700",
    href: `/invoices?overdue=true&due_before=${toISODateParam(date60dAgo)}`,
  },
  {
    label: "90+ days",
    key: "90d",
    cents: summary.bucket_91_plus_cents,
    colorClass: "text-fault-700",
    href: `/invoices?overdue=true&due_before=${toISODateParam(date90dAgo)}`,
  },
];
```

Wrap each bucket row in a `<Link>`:

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

Also wrap "Total Outstanding" row in a Link to `/invoices?overdue=true`.

> **`useInvoices` hook compatibility**: The `useInvoices` hook must accept `due_before` as a param. Verify `useInvoices.ts` accepts this — if not, add it. The API already supports `?due_before=` ✅.

---

### FIX-010b — Add "Aging" column to InvoicesPage.tsx

The `isOverdue()` helper is already defined and exported from `InvoicesPage.tsx`. Add a helper that computes the aging bucket:

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

Add a new column **after** the `due_at` column (after line 252):

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
    const isPaidOrVoid = ["paid", "void", "writeoff"].includes(inv.status_code);
    if (isPaidOrVoid) {
      return <span className="text-neutral-400">—</span>;
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

---

## E. Pattern Reuse Decisions

| Pattern | Decision |
|---|---|
| `§16 always-preview-before-send` | FIX-001: `approved` status reuses the existing `SendQuotePreviewModal` + `useGeneratePublicLink` flow — same as draft. No new modal needed. |
| `§16 RBAC gating with RoleGate` | FIX-001: `approved` action in list and action bar both gated with `permission="quotes.edit"` — only owner/operator can send. |
| `apiClient` only | No raw `fetch()` anywhere. All API interaction via existing hooks (`useGeneratePublicLink`, `useInvoice`, `useInvoices`). |
| Next.js `<Link>` for navigation | FIX-010a: AR widget uses Next.js `<Link>` (not `<a>`) for client-side navigation. |
| Computed columns at render time | FIX-010b: Aging column is entirely client-side computed — no backend change, no new hook. |

---

## F. Shared Module Interfaces

No new shared components. No `packages/ui/` changes. No new `PermissionKey` additions needed — `quotes.edit` already covers the approved send action.

### useInvoices.ts — verify `due_before` param support

Before Task 9, verify `useInvoices.ts` accepts `due_before?: string`. If it doesn't have this param, add it:

```tsx
// In useInvoices params interface and queryFn:
due_before?: string;
// ...
if (due_before) params.append("due_before", due_before);
```

The `ArSummaryWidget` does not call `useInvoices` directly — it just builds navigation URLs. But the `InvoicesPage` must correctly read `due_before` from URL query params and pass to `useInvoices`. Verify how `InvoicesPage` reads URL params (likely `useSearchParams`) and ensure `due_before` is threaded through.

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| Does `QuoteActionBar` for `approved` need a different `onConfirm` flow? | No — `publicLinkMutation.mutateAsync({ versionId: quoteVersionId })` works identically for `approved` status. The backend `POST /api/v1/quotes/{quote_id}/versions/{version_id}/public-link` accepts non-terminal statuses. |
| Should `approved` quotes show the "Submit for Approval" tech button? | No — `approved` is an owner-only action (send to customer). The `quote.submit_for_approval` RoleGate wraps the Submit button; since `isApproved` skips the `isDraft` check that was guarding it, the Submit button must be explicitly excluded from `isApproved` render. The existing `{isDraft && (...Submit button...)}` guard already handles this — Submit only renders when `isDraft`. |
| Does `InvoicesPage` read URL params to pre-fill the overdue filter from AR widget links? | Verify via `useSearchParams` in `InvoicesPage.tsx`. If it doesn't currently read URL params, add it as part of FIX-010b. The `due_before` param passed from AR widget links must be consumed. |
| `PaymentSummaryEntry` — should `status_id` be used in the UI? | No — `InvoicePaymentHistory` does not display a payment status badge (out of scope for this batch). The `status_id` field is included in the interface for forward-compatibility but not rendered. |
| `idempotency_key` removed from `PaymentEntry` — will this break existing tests? | The existing `InvoicePaymentHistory` component has no test file in the scanned results. If one exists, it will need to be updated to use `customer_payment_comment` instead of `idempotency_key`. Engineer must grep for tests. |

---

## H. Surface Mockup Reference

No new surfaces. All three fixes are modifications to existing surfaces:

| Surface | Platform | Fix | Change Type |
|---|---|---|---|
| Quotes list page (`/quotes`) | Web only | FIX-001 | Add filter pill + inline action |
| Quote detail page (`/quotes/[id]`) | Web only | FIX-001 | Extend action bar mount condition |
| Quote action bar (component) | Web only | FIX-001 | Add `isApproved` guard + button |
| Dashboard AR widget | Web only | FIX-010 | Wrap bucket rows in `<Link>` |
| Invoices list page (`/invoices`) | Web only | FIX-010 | Add computed Aging column |
| Invoice detail page (`/invoices/[id]`) | Web only | FIX-013 | Pass payments to existing component |

---

## I. Component Manifest

No new components. All changes modify existing files.

| File | Change | Batch |
|---|---|---|
| `apps/web/src/features/quotes/components/QuotesPage.tsx` | Add `approved` to STATUS_FILTERS + actions column | UI-FIX-1B |
| `apps/web/src/features/quotes/components/QuoteActionBar.tsx` | Add `isApproved` guard + Send button | UI-FIX-1B |
| `apps/web/src/features/quote-approval/QuoteDetailPage.tsx` | Add `isApproved` to mount condition | UI-FIX-1B |
| `apps/web/src/features/invoices/hooks/useInvoice.ts` | Add `PaymentSummaryEntry` + `payments` to `InvoiceResponse` | UI-FIX-1B |
| `apps/web/src/features/invoices/components/InvoicePaymentHistory.tsx` | Update `PaymentEntry` interface + Reference column | UI-FIX-1B |
| `apps/web/src/features/invoices/components/InvoiceDetailPage.tsx` | Pass `invoice.payments` to `<InvoicePaymentHistory>` | UI-FIX-1B |
| `apps/web/src/features/dashboard/components/ArSummaryWidget.tsx` | Wrap bucket rows in `<Link>` with `due_before` params | UI-FIX-1B |
| `apps/web/src/features/invoices/components/InvoicesPage.tsx` | Add `getAgingBucket()` helper + Aging column | UI-FIX-1B |
| `apps/web/src/features/invoices/hooks/useInvoices.ts` | Add `due_before` param (if not already present) | UI-FIX-1B |
| `apps/web/src/mocks/handlers/invoiceDetailHandlers.ts` | Update mock to include `payments` array | UI-FIX-1B |
