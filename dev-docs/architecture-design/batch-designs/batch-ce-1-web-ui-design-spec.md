# CE-1 Part C — Web UI Design Spec: Invoice Sign-off Card + Overpayment Review

**Batch code**: CE-1 (Part C — Web)
**Date**: 2026-08-12
**Author**: Pilot Web UI Designer
**Status**: DRAFT — pending Tom approval
**Binding design**: `batch-ce-1-design.md` — scope §H rows H2 + H3 only
**Endpoint contracts**: §D.3 (`GET /api/v1/invoices/{invoice_id}/signoff`), §D.4 (`POST /api/v1/payments/{payment_id}/resolve-variance`)
**Component manifest source**: §I "Part C — Web" (matched exactly below)
**Resolved decisions**: §G (esp. R6 — resolution is record-keeping only, no Stripe refund execution)

---

## 1. Surface Overview

This spec covers two additions to the authenticated invoice-detail surface (`InvoiceDetailPage.tsx`):

| # | Component | Route / mount point | RBAC | Data source |
|---|---|---|---|---|
| H2 | `InvoiceSignoffCard` | Invoice detail page, below payment history | `<RoleGate permission="invoices.view">` (owner, office_staff, operator — tech excluded) | `GET /api/v1/invoices/{invoice_id}/signoff` (§D.3) via `useInvoiceSignoff` |
| H3a | `OverpaymentReviewBanner` | Invoice detail page, above line items | `<RoleGate permission="invoices.view">` (banner visible); Resolve action gated `invoices.update` | Derived from `invoice.payments[]` (already fetched by `useInvoice`) |
| H3b | `ResolveVarianceModal` | Rendered by the banner | `<RoleGate permission="invoices.update">` (owner, office_staff — operator excluded from `invoices.update` per design-system §8; verify against `ROLE_PERMISSION_MAP`) | `POST /api/v1/payments/{payment_id}/resolve-variance` (§D.4) via `useResolveVariance` |

**Out of scope**: H1 (mobile — `pilot-voice-ui-designer`), H4 (public `/i/[token]` — deferred §G-R2, `pilot-marketing-ui-designer`).

**Component-existence check** (run against `packages/ui/src/index.ts` 2026-08-12): `NotificationBanner`, `EmptyState`, `LoadingState`, `ErrorState`, `RoleGate`, `PendingBadge` all exist and are composed. **Zero new `packages/ui` components.**

**Money-display convention** (mirrors `InvoicePartialPaidState.tsx` and `InvoiceDetailPage.tsx`): `new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 }).format(cents / 100)`. All amounts arrive as integer `_cents` fields — divide by 100, format USD. Never spec an "overdue" badge (derived state, not a DB code).

---

## 2. H2 — InvoiceSignoffCard

### 2.1 Placement

Mounted inside `InvoiceDetailPage.tsx` immediately **after** `<InvoicePaymentHistory>` and **before** the customer-notes block. Wrapped in `<RoleGate permission="invoices.view">` so techs never see it.

```
{/* Payment History */}
<InvoicePaymentHistory payments={invoice.payments ?? []} />

{/* NEW — Customer Sign-off */}
<RoleGate permission="invoices.view">
  <InvoiceSignoffCard invoiceId={invoiceId} />
</RoleGate>

{/* Customer notes … */}
```

### 2.2 Data hook — `useInvoiceSignoff`

- **File**: `frontend/apps/web/src/features/invoices/hooks/useInvoiceSignoff.ts` (NEW)
- **Endpoint**: `GET /api/v1/invoices/{invoice_id}/signoff` (§D.3)
- **Query key**: `["invoice", invoiceId, "signoff"]` as const (colocated under the invoice namespace; `useInvoice` uses `["invoice", invoiceId]` — sibling, not child, so invalidation of the parent does not auto-refetch signoff; the card manages its own refetch).
- **TanStack Query v5 object-form**: `{ queryKey, queryFn, enabled: !!invoiceId, retry: false, staleTime: 0 }` — `staleTime: 0` so a re-mount (tab return) always refetches a fresh presigned `signature_url` (1h TTL per §D.3).
- **`apiClient` only** (never raw fetch) — mirrors `useInvoice.ts`.
- **Types**: after `pnpm sync-api-types` (Part A regenerates the OpenAPI spec), import `InvoiceSignoffResponse` from `@pilot/shared-types`. Until then, define a local interface matching §D.3:

```typescript
export interface InvoiceSignoffResponse {
  signoff_id: string;
  invoice_id: string;
  signed_by_name: string;
  signed_at: string;            // ISO 8601 — server receipt time
  client_capture_at: string | null; // device clock (offline pattern)
  captured_by_user_id: string;
  signature_url: string;        // presigned GET, 1h TTL
  superseded_count: number;     // >0 when prior captures were superseded
}
// 200 with no active signoff → { signoff: null } — hook returns null
```

- **Signature URL expiry handling**: the presigned URL has a 1h TTL. Strategy: `staleTime: 0` + `refetchOnWindowFocus: true` (default) ensures a fresh URL on tab return. Additionally, the `<img>` `onError` handler (§2.6 error state) triggers `refetch()` to recover from a stale/expired URL without a full page reload. Note this in Implementation Notes.

### 2.3 Pixel specs — populated state

Card container (matches the visual language of the balance-due panel at `InvoiceDetailPage.tsx`):

| Element | Spec |
|---|---|
| Outer wrapper | `mt-4 rounded-md border border-neutral-200 bg-white px-4 py-4` |
| Card width | Full content width (parent is `max-w-4xl mx-auto p-6`) |
| Header row | `flex items-center justify-between mb-3` |
| Header H3 | `text-sm font-semibold text-neutral-700` — text: "Customer Sign-off" |
| Header icon | `DocumentSignatureIcon` (Heroicons 2.0, outline, `w-5 h-5 text-neutral-400`) — sits left of the H3 with `mr-2` |
| Signature image | `block rounded-md border border-neutral-200 bg-neutral-50` — `max-h-40 w-auto object-contain` (constrain height, preserve aspect ratio). `alt="Customer signature: {signed_by_name}"`. `data-testid="signoff-signature-img"` |
| Metadata grid | `mt-3 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-sm` |
| Metadata label | `text-neutral-500` — e.g. "Signed by" |
| Metadata value | `text-neutral-900 font-medium` |
| `signed_at` | Format: `new Date(signed_at).toLocaleString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" })` — label "Signed at" |
| `client_capture_at` | Shown **only when present** and **different from** `signed_at` (offline capture). Label "Captured on device". Same date-time format. Helper: a `InformationCircleIcon` (`w-4 h-4 text-neutral-400`) with `title="Device clock at capture; may differ from server time when captured offline."` |
| `captured_by_user_id` | Label "Captured by". Display: see §2.7 (user-name resolution gap). |
| Superseded history line | Shown **only when** `superseded_count > 0`. `mt-3 text-xs text-neutral-500` — text: `{superseded_count} prior signature{superseded_count > 1 ? "s" : ""} replaced.` Preceded by `ClockIcon` (`w-4 h-4 text-neutral-400 inline mr-1`). `data-testid="signoff-superseded-count"` |

### 2.4 Pixel specs — empty state

When the hook returns `null` (no active sign-off):

| Element | Spec |
|---|---|
| Outer wrapper | Same card container as §2.3 |
| Header | Same H3 "Customer Sign-off" + `DocumentSignatureIcon` |
| Body | Compose `<EmptyState>` from `@pilot/ui/states` |
| `EmptyState` props | `type="no-results"`, `title="No signature captured"`, `description="The customer's signature is captured from the mobile app at job sign-off. Once a technician completes sign-off in the field, the signature appears here."` |
| No CTA button | Empty state is informational only — capture happens on mobile (§G-R3). Do not add a "Capture" button on web. |

### 2.5 Pixel specs — loading state (skeleton)

Per standards §11 ("skeletons over spinners for content-shaped loading"):

| Element | Spec |
|---|---|
| Outer wrapper | Same card container |
| Header | Same H3 (real text, not skeleton) |
| Signature skeleton | `h-40 w-full rounded-md bg-neutral-100 animate-pulse` (`data-testid="signoff-skeleton-img"`) |
| Metadata skeleton | Two rows of `h-4 w-48 rounded bg-neutral-100 animate-pulse` with `gap-y-2` |
| Animation | `animate-pulse` (Tailwind). Reduced-motion: `@media (prefers-reduced-motion: reduce)` → remove `animate-pulse`, render static `bg-neutral-100` block (no opacity animation). State in §2.9. |

### 2.6 Pixel specs — error state

When `isError` (network failure, 403, 404):

| Element | Spec |
|---|---|
| Outer wrapper | Same card container |
| Body | Compose `<ErrorState>` from `@pilot/ui/states` |
| `ErrorState` props | `type="server"`, `title="Could not load signature"`, `description="Check your connection and try again."`, `onRetry={() => void refetch()}` |
| Image-load error (distinct) | If the hook succeeded but the `<img>` fails to load (expired/stale presigned URL): `onError` calls `refetch()` from the hook. While refetching, show `bg-neutral-100 h-40 rounded-md` with centered `ArrowPathIcon` (`w-5 h-5 text-neutral-400 animate-spin`) + `text-xs text-neutral-500` "Refreshing signature…". `data-testid="signoff-img-refreshing"`. |

### 2.7 `captured_by_user_id` display — resolution gap (flag for Implementation Notes)

The invoice detail page currently fetches the **customer** via `useCustomer(invoice?.customer_id)` (`InvoiceDetailPage.tsx`) but does **not** fetch user display names for `captured_by_user_id`. Two options, spec'd in priority order:

1. **Preferred**: if a `useUser(userId)` hook exists in `apps/web/src/features/` (engineer verifies during implementation), use it to resolve `captured_by_user_id` → display name. Label "Captured by" → value = display name.
2. **Fallback (if no user hook exists)**: display `User {captured_by_user_id.slice(0,8)}` (first 8 chars of the UUID) with a `title="Technician user ID — name resolution not yet wired."` tooltip via `InformationCircleIcon`. **Flag in Implementation Notes** so the engineer confirms whether a user-name hook is available; if not, the fallback ships and a follow-up ticket is noted.

This is flagged explicitly per the task brief.

### 2.8 Interaction spec — InvoiceSignoffCard

The card is **display-only** — no interactive elements in the populated or empty states. The only interactive affordance is the `onError` → `refetch()` recovery on the signature image (§2.6), which is automatic, not user-initiated.

| Element | Default | Hover | focus-visible | Active | Disabled |
|---|---|---|---|---|---|
| Signature `<img>` | `border-neutral-200` | n/a (non-interactive) | n/a | n/a | n/a |
| `InformationCircleIcon` tooltips | `text-neutral-400` | `text-neutral-600` (cursor `help`) | `focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1` (if implemented as a button) | n/a | n/a |

No five-state table needed beyond the above — the card has no buttons.

### 2.9 Animation spec — InvoiceSignoffCard

| Element | Transition | Reduced-motion fallback |
|---|---|---|
| Skeleton pulse | `animate-pulse` (Tailwind built-in: `opacity` 1→0.5→1, 2s linear infinite) | `@media (prefers-reduced-motion: reduce)` → static `bg-neutral-100`, no animation |
| Image-refresh spinner | `animate-spin` (Tailwind: `rotate` 360deg, 1s linear infinite) | `@media (prefers-reduced-motion: reduce)` → static `ArrowPathIcon`, no rotation |

---

## 3. H3a — OverpaymentReviewBanner

### 3.1 Visibility logic

The banner renders when **any** payment on the invoice has `amount_variance_cents > 0` **AND** `variance_resolution IS NULL`. The invoice detail page already fetches `invoice.payments[]` via `useInvoice` (`useInvoice.ts`). The `PaymentSummaryEntry` interface must be **extended** (see §5 Implementation Notes) to include `amount_variance_cents` and the four variance-resolution fields.

**Computation** (in the banner component, pure derived from props — no extra fetch):

```typescript
const unresolvedOverpayments = (payments ?? []).filter(
  (p) => p.amount_variance_cents > 0 && p.variance_resolution === null
);
// render banner iff unresolvedOverpayments.length > 0
```

If multiple payments are overpaid + unresolved, the banner lists each (see §3.3). The modal resolves **one payment at a time** (§D.4 is per-`payment_id`).

### 3.2 Placement

Mounted at the **top of the invoice detail content**, above the header — so the review call-to-action is visible without scrolling. Wrapped in `<RoleGate permission="invoices.view">`.

```
<div className="p-6 max-w-4xl mx-auto" data-testid="invoice-detail-page">
  {/* NEW — Overpayment review banner (above breadcrumb) */}
  <RoleGate permission="invoices.view">
    <OverpaymentReviewBanner
      invoiceId={invoiceId}
      payments={invoice.payments ?? []}
    />
  </RoleGate>

  {/* Breadcrumb */}
  <nav className="text-sm text-neutral-500 mb-4">…</nav>
  …
```

### 3.3 Pixel specs — unresolved (active) state

Composes the `warning` severity class per §16.6 four-class severity (`alert` tokens). Visual treatment mirrors the design-system warning palette.

| Element | Spec |
|---|---|
| Outer wrapper | `mb-4 rounded-md border border-alert-200 bg-alert-50 px-4 py-3` (`data-testid="overpayment-review-banner"`) |
| Layout | `flex items-start gap-3` |
| Icon | `ExclamationTriangleIcon` (Heroicons 2.0, solid, `w-5 h-5 text-alert-600 flex-shrink-0 mt-0.5`) |
| Body | `flex-1 space-y-1` |
| Headline | `text-sm font-medium text-alert-800` — copy (anchored on arch §18.5): `Customer paid {formatCents(amount_variance_cents)} over invoice total — review.` (money-from-cents, USD). `data-testid="overpayment-headline"` |
| Per-payment rows (when >1) | `text-sm text-alert-700` — one line per unresolved payment: `Payment of {formatCents(p.amount_cents)} on {formatDate(p.paid_at)} — over by {formatCents(p.amount_variance_cents)}.` Each row has a `data-testid="overpayment-payment-row"` |
| Customer comment | Shown **only when** `customer_payment_comment` is present. `text-xs text-alert-700 italic` — prefixed with `ChatBubbleLeftRightIcon` (`w-4 h-4 text-alert-500 inline mr-1`). Text: `"Customer note: {customer_payment_comment}"`. `data-testid="overpayment-customer-comment"` |
| Action button | `Resolve` — gated `<RoleGate permission="invoices.update">`. `mt-2 inline-flex items-center rounded-md border border-alert-300 bg-white px-3 py-1.5 text-sm font-medium text-alert-700 hover:bg-alert-100`. Icon: `CheckCircleIcon` (outline, `w-4 h-4 mr-1.5`). `data-testid="resolve-variance-btn"`. Min target 44×24px (button is `py-1.5` ≈ 32px tall + border; **engineer: bump to `py-2` if axe-core flags the 32px height** — prefer 44px). |

### 3.4 Pixel specs — resolved (collapsed) state

When **all** previously-overpaid payments now have `variance_resolution !== null`, the banner collapses to a quiet confirmation line (no longer `alert` severity — switches to `margin`/success-adjacent neutral).

| Element | Spec |
|---|---|
| Outer wrapper | `mb-4 rounded-md border border-neutral-200 bg-neutral-50 px-4 py-2` (`data-testid="overpayment-resolved-line"`) |
| Layout | `flex items-center gap-2` |
| Icon | `CheckCircleIcon` (Heroicons 2.0, outline, `w-4 h-4 text-margin-600`) |
| Text | `text-xs text-neutral-600` — per resolved payment: `Overpayment of {formatCents(p.amount_variance_cents)} resolved as {resolutionLabel} on {formatDate(p.variance_resolved_at)}.` |
| `resolutionLabel` map | `credit` → "credit forward", `refund_offline` → "offline refund", `writeoff` → "write off" |
| No action button | Resolved state has no Resolve button. |

### 3.5 Pixel specs — hidden state

When no payment has `amount_variance_cents > 0`, the banner renders **nothing** (returns `null`). No empty state needed — this is the common case.

### 3.6 Data states — OverpaymentReviewBanner

The banner is **derived from `invoice.payments[]`** (already loaded by `useInvoice`), so it has no independent loading/error/empty states of its own — it inherits the parent page's `isLoading`/`isError` gates (`InvoiceDetailPage.tsx`:91). The banner only renders once `invoice` is populated. The four states:

| State | Behavior |
|---|---|
| Parent `isLoading` | Page shows `<LoadingState>`; banner not mounted. |
| Parent `isError` | Page shows `<ErrorState>`; banner not mounted. |
| Populated, no overpayment | Banner returns `null` (hidden). |
| Populated, unresolved overpayment | Active banner (§3.3). |
| Populated, resolved overpayment | Collapsed line (§3.4). |

### 3.7 Interaction spec — OverpaymentReviewBanner

| Element | Default | Hover | focus-visible | Active | Disabled |
|---|---|---|---|---|---|
| Resolve button | `bg-white text-alert-700 border-alert-300` | `hover:bg-alert-100` | `focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1` | `active:bg-alert-200` | n/a (hidden via `<RoleGate>` when no `invoices.update` — never disabled-visible) |

### 3.8 Animation spec — OverpaymentReviewBanner

| Element | Transition | Reduced-motion fallback |
|---|---|---|
| Resolve button color | `transition-colors duration-150 ease-in-out` | `@media (prefers-reduced-motion: reduce)` → no transition (instant color swap) |
| Banner collapse (active→resolved) | `transition: opacity 200ms ease-in-out` (fade active banner out, resolved line fades in) | `@media (prefers-reduced-motion: reduce)` → instant swap, no fade |

---

## 4. H3b — ResolveVarianceModal

### 4.1 Overview

Modal opened by the banner's Resolve button (§3.3). Resolves **one** overpaid payment per submission (§D.4 is per-`payment_id`). When multiple payments are unresolved, the banner's Resolve button opens the modal seeded with the **first** unresolved payment; after a successful resolve, the modal closes and the banner re-renders (still active if more remain). The engineer may add a "Resolve next" affordance — **not specced** here; keep the MVP to one-at-a-time.

### 4.2 Data hook — `useResolveVariance`

- **File**: `frontend/apps/web/src/features/invoices/hooks/useResolveVariance.ts` (NEW)
- **Endpoint**: `POST /api/v1/payments/{payment_id}/resolve-variance` (§D.4)
- **Mutation** (TanStack Query v5 `useMutation`, object-form):
  - `mutationFn`: `apiClient.post(`/api/v1/payments/${paymentId}/resolve-variance`, payload)` — payload `{ resolution, note? }`.
  - `retry: false` (never auto-retry a financial mutation).
  - `onSuccess`: `queryClient.invalidateQueries({ queryKey: ["invoice", invoiceId] })` — refreshes the invoice + payments so the banner re-evaluates (mirrors `useRecordPayment.ts`). Also calls the caller's `onSuccess` callback to close the modal.
- **Idempotency**: §D.4 is a resolve action, not a payment creation — the backend guard is "already resolved → 409" (§D.4). No `Idempotency-Key` header required for resolve (unlike payment creation). Engineer confirms against the OpenAPI spec after `pnpm sync-api-types`.
- **Types**: `ResolveVarianceRequest` `{ resolution: "credit" | "refund_offline" | "writeoff"; note?: string }` and the extended `PaymentResponse` (adds `variance_resolution`, `variance_resolution_note`, `variance_resolved_at`, `variance_resolved_by_user_id`). Import from `@pilot/shared-types` after sync; until then, extend the local `PaymentResponse` in `useRecordPayment.ts` (which already has `amount_variance_cents`).

### 4.3 Pixel specs — modal panel

Follows design-system §7 modal pattern. Composed inline (not a new `packages/ui` component).

| Element | Spec |
|---|---|
| Overlay | `fixed inset-0 z-50 bg-neutral-900/50` (`data-testid="resolve-variance-overlay"`) |
| Modal panel | `bg-white rounded-lg shadow-xl max-w-md w-full mx-auto mt-16 p-6` (`data-testid="resolve-variance-modal"`) |
| Close button | Top-right `XMarkIcon` (Heroicons 2.0, outline, `w-5 h-5 text-neutral-400 hover:text-neutral-600`). Wrapped in a `<button>` with `p-1` (8px padding → 24×24px hit area around the 20px icon). `aria-label="Close"`. `data-testid="resolve-variance-close"` |
| Title | `text-h2 font-semibold text-neutral-900` — "Resolve overpayment" |
| Subtitle | `mt-1 text-sm text-neutral-500` — `Payment of {formatCents(payment.amount_cents)} — over by {formatCents(payment.amount_variance_cents)}.` |
| Customer comment (when present) | `mt-2 text-xs text-neutral-600 italic` — `"Customer note: {customer_payment_comment}"`. Prefixed with `ChatBubbleLeftRightIcon` (`w-4 h-4 text-neutral-400 inline mr-1`). |
| Form | `mt-4 space-y-4` |

### 4.4 Pixel specs — resolution radio group

Three options per design §B.2 CHECK constraint. Implemented as a radio group (`<fieldset>` + `<legend>` + `<input type="radio">`). **Color is never the only signal** — each option has a text label and a descriptive helper line (WCAG 1.4.1).

| Element | Spec |
|---|---|
| `<legend>` | `text-sm font-medium text-neutral-700 mb-2` — "Resolution" |
| Option container | `space-y-2` |
| Each option | `flex items-start gap-3 rounded-md border border-neutral-200 px-3 py-2.5 cursor-pointer hover:bg-neutral-50` — the `<label>` wraps the radio + text (clickable row). `data-testid="resolution-option-{value}"` |
| Radio `<input>` | `mt-0.5 h-4 w-4 text-brand-600 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1 border-neutral-300` |
| Option label | `text-sm font-medium text-neutral-900` |
| Option helper | `text-xs text-neutral-500 mt-0.5` |

**Option 1 — `credit`**:
- Label: "Credit forward"
- Helper: "Apply the overpayment as a credit toward the customer's next invoice."

**Option 2 — `refund_offline`**:
- Label: "Record offline refund"
- Helper: "Refund happened outside Pilot; this records it. No Stripe refund is issued." (verbatim from task brief / §G-R6)

**Option 3 — `writeoff`**:
- Label: "Write off / accept"
- Helper: "Accept the overpayment as-is. No refund or credit is issued."

### 4.5 Pixel specs — note field

| Element | Spec |
|---|---|
| Container | `mt-4` |
| `<label>` | `block text-sm font-medium text-neutral-700 mb-1` — "Note (optional)" — `htmlFor="resolve-variance-note"` |
| `<textarea>` | `id="resolve-variance-note"` `rows={3}` `maxLength={1000}` `className="block w-full rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:border-brand-500 resize-none"` `placeholder="Add a note about this resolution (optional)."`. `data-testid="resolve-variance-note"`. `aria-describedby="resolve-variance-note-count"` |
| Character counter | `mt-1 text-right text-xs text-neutral-500` — `{note.length} / 1000`. `id="resolve-variance-note-count"`. Turns `text-alert-600` when `note.length >= 1000`. |

### 4.6 Pixel specs — action buttons

| Element | Spec |
|---|---|
| Button row | `mt-6 flex justify-end gap-3` |
| Cancel | `inline-flex items-center rounded-md border border-neutral-300 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50`. `data-testid="resolve-variance-cancel"`. Min 44px tall (`py-2` + `text-sm` line-height ≈ 36px — **engineer: verify axe-core; bump to `py-2.5` if under 44px**). |
| Submit | `inline-flex items-center rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700`. `data-testid="resolve-variance-submit"`. Text: "Resolve". Min 44px tall (same note as Cancel). **Disabled** until a resolution is selected (`disabled` attr + `opacity-50 cursor-not-allowed` when no radio checked). |

### 4.7 Data states — ResolveVarianceModal

| State | Behavior |
|---|---|
| Open, idle | Modal panel per §4.3–4.6. Submit disabled until a radio is selected. |
| Submitting (`isPending`) | Submit button shows `ArrowPathIcon` (`w-4 h-4 mr-1.5 animate-spin`) + text "Resolving…". Submit + Cancel both `disabled`. Radio group + note field `disabled` (`aria-busy="true"` on the form). `data-testid="resolve-variance-submitting"`. |
| Success | `onSuccess` → `invalidateQueries(['invoice', invoiceId])` → modal closes → banner re-evaluates (collapses to resolved line §3.4 if no more unresolved). |
| 409 (already resolved) | Per §16.4 409-and-refresh: **compose, don't invent**. The mutation's `onError` detects HTTP 409, calls `queryClient.invalidateQueries({ queryKey: ["invoice", invoiceId] })` (refetch), closes the modal, and pushes a `<NotificationBanner>` via `useNotificationQueue` (already used in `InvoiceDetailPage.tsx`): `addNotification({ id: "variance-409-{paymentId}", severity: "info", title: "This overpayment was already resolved. The invoice has been refreshed." })`. The refetched invoice now shows the resolved line (§3.4). |
| 422 (no overpayment / validation) | Inline error: `mt-2 text-xs text-fault-600` below the radio group, `aria-describedby`-linked to the fieldset. Text from the RFC 7807 `detail`. `data-testid="resolve-variance-error"`. Modal stays open. |
| Network error | Inline error (same placement as 422): "Could not submit resolution. Check your connection and try again." Submit re-enabled. |

### 4.8 Interaction spec — ResolveVarianceModal

| Element | Default | Hover | focus-visible | Active | Disabled |
|---|---|---|---|---|---|
| Close (`XMarkIcon`) button | `text-neutral-400` | `hover:text-neutral-600 hover:bg-neutral-100` (on the `p-1` wrapper) | `focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1` | `active:text-neutral-800` | n/a |
| Radio option row | `border-neutral-200 bg-white` | `hover:bg-neutral-50` | `focus-visible:ring-2 focus-visible:ring-brand-500` on the `<input>` (ring shows on the row via `focus-within:`) | `active:bg-neutral-100` | n/a |
| Note `<textarea>` | `border-neutral-300` | n/a | `focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:border-brand-500` | n/a | `disabled:bg-neutral-50 disabled:text-neutral-400` (during submit) |
| Cancel button | `bg-white text-neutral-700 border-neutral-300` | `hover:bg-neutral-50` | `focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1` | `active:bg-neutral-100` | `disabled:opacity-50 disabled:cursor-not-allowed` (during submit) |
| Submit button | `bg-brand-600 text-white` | `hover:bg-brand-700` | `focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1` | `active:bg-brand-800` | `disabled:opacity-50 disabled:cursor-not-allowed` (no radio selected OR submitting) |

### 4.9 Animation spec — ResolveVarianceModal

| Element | Transition | Reduced-motion fallback |
|---|---|---|
| Overlay fade-in | `transition: opacity 150ms ease-out` (0→100%) | `@media (prefers-reduced-motion: reduce)` → instant (no fade) |
| Modal panel entrance | `transition: transform 150ms ease-out, opacity 150ms ease-out` (translateY(8px)→0, opacity 0→100%) | `@media (prefers-reduced-motion: reduce)` → instant (no transform/opacity) |
| Submit spinner | `animate-spin` (1s linear infinite) | `@media (prefers-reduced-motion: reduce)` → static icon |
| Button color | `transition-colors duration-150 ease-in-out` | `@media (prefers-reduced-motion: reduce)` → no transition |

---

## 5. Implementation Notes

### 5.1 Hook conventions (both hooks)

- Both `useInvoiceSignoff` and `useResolveVariance` use `apiClient` from `@pilot/shared-api` (never raw fetch) — mirrors `useInvoice.ts` and `useRecordPayment.ts`.
- TanStack Query v5 **object-form** options (not the legacy positional form).
- `retry: false` on both (signoff: a failed presigned-URL fetch shouldn't hammer; variance: never auto-retry a financial mutation).
- Query keys colocated in the hook file as `const` factories (e.g. `export const SIGNOFF_QUERY_KEY = (invoiceId: string) => ["invoice", invoiceId, "signoff"] as const`).

### 5.2 Type sync dependency

- Types (`InvoiceSignoffResponse`, `ResolveVarianceRequest`, extended `PaymentResponse`) come from `@pilot/shared-types` **after** `pnpm sync-api-types` runs — which requires Part A (backend) to have regenerated `openapi.json` first (batch design §C step 7→9). Until then, define local interfaces matching §D.3/§D.4 shapes and mark with `// TODO: replace with @pilot/shared-types after pnpm sync-api-types`.
- The four variance fields added to `PaymentResponse` (per design §B.2 / §D.4): `variance_resolution`, `variance_resolution_note`, `variance_resolved_at`, `variance_resolved_by_user_id`. The existing local `PaymentResponse` in `useRecordPayment.ts` already has `amount_variance_cents` — extend it with these four.

### 5.3 `PaymentSummaryEntry` extension

The `PaymentSummaryEntry` interface in `useInvoice.ts` (used by `InvoiceResponse.payments[]`) currently lacks `amount_variance_cents` and the four variance fields. **The engineer must extend it** so `OverpaymentReviewBanner` can read them from the already-fetched invoice data (no extra fetch). Add:

```typescript
export interface PaymentSummaryEntry {
  // …existing fields…
  amount_variance_cents: number;          // already in PaymentResponse, add here too
  variance_resolution: string | null;
  variance_resolution_note: string | null;
  variance_resolved_at: string | null;
  variance_resolved_by_user_id: string | null;
}
```

### 5.4 `captured_by_user_id` name resolution gap

See §2.7. The engineer must check whether a `useUser(userId)` hook exists in `apps/web/src/features/`. If yes, resolve the name. If no, ship the `User {id.slice(0,8)}` fallback and note a follow-up ticket. **Do not block CE-1 on user-name resolution** — the UUID fallback is acceptable for beta.

### 5.5 MSW handler pointers

The engineer should add MSW (Mock Service Worker) handlers for the two new endpoints so component tests (`__tests__/`) can exercise all four data states without a live backend:

- `GET /api/v1/invoices/:invoiceId/signoff` → return a fixture `InvoiceSignoffResponse` (populated), `{ signoff: null }` (empty), or a 500 (error).
- `POST /api/v1/payments/:paymentId/resolve-variance` → return the extended `PaymentResponse` (success), 409 (already resolved), or 422 (no overpayment).

Follow the existing MSW handler conventions in `apps/web/src/mocks/` (engineer locates the handlers directory — the invoice feature tests at `__tests__/` already use MSW for `useInvoices`/`useRecordPayment`).

### 5.6 409-and-refresh composition (§16.4)

The resolve-variance 409 path (§4.7) composes the existing `useNotificationQueue` (already imported in `InvoiceDetailPage.tsx`) + `invalidateQueries` — **do not** build a new conflict-resolution component. The `useStalenessRetry` hook from `@pilot/ui` (`packages/ui/src/index.ts`) is available if the engineer prefers a hook-based 409 handler, but the inline `onError` + `invalidateQueries` + `addNotification` approach is simpler and sufficient for this single-endpoint case.

### 5.7 Signature URL refresh strategy

The presigned `signature_url` has a 1h TTL (§D.3). The spec relies on:
1. `staleTime: 0` + `refetchOnWindowFocus: true` (TanStack default) → fresh URL on tab return.
2. `<img onError>` → `refetch()` → recovers from a stale URL mid-session.

The engineer should **not** implement a client-side timer to pre-emptively refresh — the `onError` recovery is simpler and sufficient for a detail page that is typically viewed briefly.

### 5.8 No new `packages/ui` components

Per design §I, **zero** new `packages/ui` components. The modal is composed inline in `ResolveVarianceModal.tsx` following design-system §7. If a shared `Modal` shell is later desired, that is a separate FE-B batch — not CE-1.

### 5.9 RBAC verification

The engineer must verify the `invoices.update` permission mapping in `ROLE_PERMISSION_MAP` (exported from `packages/ui/src/index.ts`). Per design-system §8, `invoices.view` = owner/office_staff/operator. The task brief specifies the Resolve action is gated `invoices.update` — confirm which roles hold `invoices.update` (likely owner/office_staff; operator may or may not — verify and use `<RoleGate permission="invoices.update">` so the mapping is authoritative, not hardcoded role lists).

### 5.10 Manual E2E (partial-pay flow — §G-R1)

Per design §I Part C, the engineer runs a manual E2E pass of the pre-built partial-pay flow on `/i/[token]` (issue invoice → partial pay → "Pay remaining" → full pay). This is **verification only** — no new code. Not part of this design spec; noted for completeness.

---

## 6. Component Manifest

Matches batch design §I "Part C — Web" exactly.

| Component / file | Path | Change |
|---|---|---|
| `InvoiceSignoffCard.tsx` | `frontend/apps/web/src/features/invoices/components/InvoiceSignoffCard.tsx` | NEW — display card per §2 (presigned GET image, refresh on `signature_url` expiry, signer/timestamps/tech/superseded history, empty + loading + error states) |
| `OverpaymentReviewBanner.tsx` | `frontend/apps/web/src/features/invoices/components/OverpaymentReviewBanner.tsx` | NEW — warning banner per §3, renders when any payment has `amount_variance_cents > 0` AND `variance_resolution IS NULL`; collapses to resolved line |
| `ResolveVarianceModal.tsx` | `frontend/apps/web/src/features/invoices/components/ResolveVarianceModal.tsx` | NEW — 3-option resolution + note per §4; composes modal pattern (design-system §7); 409 → refetch + notification |
| `useInvoiceSignoff.ts` | `frontend/apps/web/src/features/invoices/hooks/useInvoiceSignoff.ts` | NEW — D.3 hook (`apiClient` only; `retry: false`; query key `["invoice", invoiceId, "signoff"]`) |
| `useResolveVariance.ts` | `frontend/apps/web/src/features/invoices/hooks/useResolveVariance.ts` | NEW — D.4 hook (`apiClient` only; `retry: false`; invalidates `["invoice", invoiceId]` on success) |
| Invoice detail page | `frontend/apps/web/src/features/invoices/components/InvoiceDetailPage.tsx` | MODIFY — mount `OverpaymentReviewBanner` (top, `<RoleGate permission="invoices.view">`) + `InvoiceSignoffCard` (after payment history, `<RoleGate permission="invoices.view">`) |
| `useInvoice.ts` | `frontend/apps/web/src/features/invoices/hooks/useInvoice.ts` | MODIFY — extend `PaymentSummaryEntry` with `amount_variance_cents` + four variance-resolution fields (§5.3) |

**Zero new `packages/ui` components.** `NotificationBanner`, `EmptyState`, `LoadingState`, `ErrorState`, `RoleGate` composed from existing exports.

---

## 7. Accessibility Notes (WCAG 2.2 AA)

### 7.1 Color-independent status

- **Overpayment banner**: the `alert` color (`bg-alert-50`, `text-alert-800`) is paired with the `ExclamationTriangleIcon` (solid) + the text headline "Customer paid $X over invoice total — review." Color is not the only signal.
- **Resolved line**: the `margin` check icon + text "resolved as {resolution}" — color is not the only signal.
- **Resolution radio options**: each option has a text label + helper text. No color-only differentiation between the three options.
- **Character counter**: turns `text-alert-600` at the limit **and** displays the numeric count "{n} / 1000" — not color-only.

### 7.2 Target sizes

| Element | Spec'd size | Meets ≥24×24? | Notes |
|---|---|---|---|
| Banner Resolve button | `px-3 py-1.5` + `text-sm` ≈ 32px tall | ✅ (24px min) | Engineer bumps to `py-2` if axe-core flags; prefer 44px |
| Modal close (`XMarkIcon`) | `w-5 h-5` (20px) + `p-1` wrapper (8px) = 28×28px hit area | ✅ | Meets 24px min; acceptable for a secondary control |
| Radio `<input>` | `h-4 w-4` (16px) | ❌ as sole target | **Not the sole target** — the entire `<label>` row is clickable (≥44px tall via `py-2.5`). Keyboard users tab to the radio itself; the visible focus ring + the large label row satisfy SC 2.5.8. |
| Cancel / Submit buttons | `px-4 py-2` + `text-sm` ≈ 36px tall | ✅ (24px min) | Engineer bumps to `py-2.5` for 44px if flagged |
| Note `<textarea>` | `rows={3}` + `py-2` ≈ 72px tall | ✅ | Large target |

### 7.3 Focus order + focus-visible

- **Invoice detail page tab order**: OverpaymentReviewBanner (if present) → breadcrumb → header → line items → balance → payment history → **InvoiceSignoffCard** → customer notes → action bar. The new components insert into the natural DOM order; no `tabIndex` manipulation needed.
- **All interactive elements use `focus-visible`** (not `focus`): `focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1`. Keyboard users see the ring; mouse users don't get a persistent ring on click.
- **Banner Resolve button**: receives focus when tabbing through. After the modal opens, focus moves into the modal (§7.4).
- **`scroll-margin-top`**: the `h-12` sticky header could obscure anchored content. The invoice detail page does not use anchor links, but if the engineer adds any, spec `scroll-mt-16` (64px) on anchored elements to clear the header.

### 7.4 Modal focus trap + return focus

- **On open**: focus moves to the modal's first focusable element (the close `XMarkIcon` button, or the first radio if the engineer prefers). `role="dialog"`, `aria-modal="true"`, `aria-labelledby` pointing to the title.
- **Focus trap**: Tab cycles within the modal (close → radio 1 → radio 2 → radio 3 → note → cancel → submit → close). Shift+Tab reverses. Focus does not escape to the page behind the overlay.
- **On close (Cancel / X / Escape)**: focus returns to the **Resolve button** that opened the modal (the trigger). This is critical for keyboard users — without return-focus, they'd be dropped at the top of the page.
- **Escape key**: closes the modal (same as Cancel) — **unless** the mutation is submitting (`isPending`), in which case Escape is disabled (prevent accidental close mid-submit).
- **`inert` on background**: the page content behind the overlay should be marked `inert` (or `aria-hidden="true"`) so screen readers don't reach it. Engineer uses the standard React `inert` pattern or a focus-trap library already in the repo (verify).

### 7.5 Form labeling + error association

- **Radio group**: `<fieldset>` + `<legend>` "Resolution" — the legend is the accessible name for the group. Each radio has a `<label>` (wrapping the input + text). `aria-describedby` on each radio points to its helper text `id`.
- **Note field**: visible `<label>` "Note (optional)" with `htmlFor="resolve-variance-note"` (§5 form pattern — placeholder-as-label is banned). `aria-describedby="resolve-variance-note-count"` links the character counter.
- **Inline errors** (422 / network): `text-fault-600`, `id="resolve-variance-error"`, `aria-describedby`-linked to the fieldset. Announced via `role="alert"` so screen readers pick up the dynamic error.

### 7.6 Contrast

All token pairings used are pre-validated per standards §10:
- `text-neutral-900 on bg-white` (modal body) — ≥4.5:1 ✅
- `text-alert-800 on bg-alert-50` (banner headline) — ≥4.5:1 ✅
- `text-alert-700 on bg-alert-50` (banner body) — ≥4.5:1 ✅
- `text-neutral-500 on bg-white` (helper text) — verify ≥4.5:1; `text-neutral-500` is the standards-spec'd secondary-text token (§3) — if axe-core flags, bump helper text to `text-neutral-600`.
- `text-brand-600` radio accent — decorative (the radio also has a text label); not a text-contrast concern.

---

## 8. Responsive Reflow (1024px / 768px)

The invoice detail page is `max-w-4xl mx-auto p-6` — already responsive. Notes for the new components:

| Breakpoint | Behavior |
|---|---|
| 1280px+ (primary) | Full spec as above. Metadata grid is 2-column (`sm:grid-cols-2`). |
| 1024px | No change — `max-w-4xl` (896px) fits within the content area. Metadata grid stays 2-column. |
| 768px | Content area narrows. Metadata grid collapses to 1-column (`grid-cols-1` — the `sm:` breakpoint is 640px, so at 768px it's still 2-col; engineer may add a `md:grid-cols-2` if 768px feels cramped, but 2-col is acceptable). Modal `max-w-md` (448px) fits within 768px with margin. Banner + card are full-width. |

No table layouts are introduced, so no horizontal-scroll concerns.

---

## Handoff Gate

This spec is ready for Tom's review. Implementation starts only after approval. The CE-1 Part C React Engineer prompt is authored only after Tom approves this spec.
