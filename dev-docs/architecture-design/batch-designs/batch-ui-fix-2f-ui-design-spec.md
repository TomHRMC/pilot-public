# UI Design Spec — Batch UI-FIX-2F
## Payment Method Screen + Stripe Connect Flow

**Spec file**: `dev-docs/architecture-design/batch-designs/batch-ui-fix-2f-ui-design-spec.md`  
**Batch**: UI-FIX-2F  
**Fix**: FIX-020  
**Designer**: Pilot Web UI Designer  
**Date**: 2026-07-20  
**Status**: 🟡 Awaiting Tom's review — implementation blocked until approved

---

## Pre-Work Findings Summary

| Source file | Key finding |
|---|---|
| `BillingSettingsPage.tsx` | Has a "Payment Methods Placeholder" card at bottom with "coming soon" text — this is what gets replaced |
| `SettingsSidebar.tsx` | `Billing` is a top-level sidebar item at `/settings/billing` with no sub-items — Payment Method is a sibling route, not a child nav item |
| `packages/ui/src/index.ts` | `NotificationBanner`, `useNotificationQueue`, `LoadingState`, `ErrorState`, `RoleGate` are all available — use these before designing new components |
| `batch-ui-fix-2f-design.md` | 4 new backend endpoints; callback is a full browser redirect (not AJAX); `STRIPE_CONNECT_CLIENT_ID` is new env var Tom must add |
| `ui-fix-2-decisions.md § FIX-020` | Page accessed from Profile dropdown → "Payment Method" → `/settings/billing/payment-method` |
| `ui-fix-1-decisions.md § FIX-004` | Manual payment fallback is confirmed behavior — not a failure state, show it positively |

---

## 1. Surface Overview

| Field | Value |
|---|---|
| **Route** | `/settings/billing/payment-method` |
| **New Next.js route file** | `apps/web/src/app/(authed)/settings/billing/payment-method/page.tsx` |
| **Component** | `PaymentMethodSettingsPage` |
| **Shell** | Settings shell (`SettingsShell`) — App sidebar (256px) + Settings sidebar (224px) + content area (flex-1) |
| **Access paths** | Profile dropdown → "Payment Method" (per FIX-019) |
| **RBAC** | `settings.tenant.write` — owner and operator only; `RoleGate` wraps the entire page content |
| **Who sees this** | `owner`, `operator` — NOT `tech`, NOT `office_staff` |
| **Page context** | The contractor visits this page to connect their Stripe account before they can take card payments from customers. This is a critical MVP onboarding step. |

**Layout shell at 1280px viewport:**
```
┌─────────────────────────────────────────────────────────────────┐
│ HEADER  h-12  bg-white border-b border-neutral-200              │
│ [Logo]                    [Bell] [Settings⚙] [Avatar ▾]        │
├────────────────┬──────────────────────────────────────────────  │
│ APP SIDEBAR    │ SETTINGS SIDEBAR │ CONTENT AREA               │
│ 256px          │ 224px (w-56)     │ flex-1  overflow-auto       │
│                │                  │                             │
│                │ My Account       │  px-6 py-6                 │
│                │ Operations       │  max-w-2xl                 │
│                │ Notifications    │                             │
│                │ Sync & Storage   │  [Page H1]                 │
│                │ Integrations     │  [Content sections]        │
│                │ Communications   │                             │
│                │ Team             │                             │
│                │ Billing ←active  │                             │
│                │ Security & MFA   │                             │
│                │ Voice & AI       │                             │
│                │ Data & Privacy   │                             │
│                │                  │                             │
└────────────────┴──────────────────┴─────────────────────────────┘
```

> **Sidebar active state note**: The Settings sidebar does not have a `payment-method` sub-item. The `Billing` top-level item (`/settings/billing`) will be highlighted as the active ancestor when on `/settings/billing/payment-method` because `pathname.startsWith("/settings/billing")` is `true`. This requires no sidebar change — the existing `isAncestor()` logic in `SettingsSidebar.tsx` handles this correctly.

---

## 2. Connection Status Card — Disconnected State

This is the primary card at the top of the page. It is shown when `GET /api/v1/settings/billing/stripe-connect/status` returns `{ connected: false }`.

### Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  [LinkIcon w-5 h-5 text-neutral-400]  Stripe Account            │
│                                                                   │
│  No Stripe account connected                                      │
│                                                                   │
│  Connect your Stripe account to accept card payments from         │
│  your customers directly on invoice payment pages.               │
│                                                                   │
│  ┌────────────────────────────────────────┐                      │
│  │  →  Connect Stripe Account             │  ← Primary CTA      │
│  └────────────────────────────────────────┘                      │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  [InformationCircleIcon w-4 h-4]  You'll be redirected  │   │
│  │  to Stripe's website to complete the connection.         │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### Pixel Spec

| Property | Value |
|---|---|
| Card container | `bg-white border border-neutral-200 rounded-lg p-6` |
| Card width | `max-w-2xl` (inherits from page container) |
| Card shadow | `shadow-sm` |
| Gap between card header and body | `mt-1` |
| Gap between card body and CTA | `mt-5` |
| Gap between CTA and info note | `mt-4` |

### Card Header Row

| Element | Spec |
|---|---|
| Icon | `LinkIcon` (Heroicons 2.0 outline) `w-5 h-5 text-neutral-400 mr-2` |
| Section title text | `"Stripe Account"` — `text-h3 font-medium text-neutral-900` |
| Layout | `flex items-center` |

### Card Body Text

| Element | Spec |
|---|---|
| Primary status line | `"No Stripe account connected"` — `text-body font-medium text-neutral-900 mt-4` |
| Description | `"Connect your Stripe account to accept card payments from your customers directly on invoice payment pages."` — `text-body text-neutral-600 mt-1` |

### Connect Stripe Account CTA Button

| Property | Value |
|---|---|
| Label | `"Connect Stripe Account"` |
| Trailing icon | `ArrowRightIcon` (Heroicons 2.0 outline) `w-4 h-4 ml-2` |
| Base classes | `inline-flex items-center rounded-md bg-brand-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm` |
| Hover | `hover:bg-brand-700` |
| Focus | `focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2` |
| Disabled (loading) | `disabled:opacity-60 disabled:cursor-not-allowed` |
| Button width | `w-full` — full width of card for visual emphasis |
| Height | `py-2.5` — 40px effective height |

**Interaction**: Clicking this button:
1. Fires `GET /api/v1/settings/billing/stripe-connect/authorize` to retrieve the Stripe OAuth URL
2. While the request is in-flight: shows loading spinner state (see Section 9)
3. On success: `window.location.href = response.oauth_url` — full page navigation to Stripe's OAuth page
4. On fetch error: shows inline error text below the button (see Section 8)

### Redirect Info Note (below the CTA)

| Property | Value |
|---|---|
| Container | `rounded-md bg-neutral-50 border border-neutral-200 px-4 py-3` |
| Icon | `InformationCircleIcon` (Heroicons 2.0 outline) `w-4 h-4 text-neutral-500 mr-2 mt-0.5 shrink-0` |
| Layout | `flex items-start` |
| Text | `"You'll be redirected to Stripe's website to complete the connection. You'll return to Pilot after."` |
| Text style | `text-caption text-neutral-600` |

---

## 3. Connection Status Card — Connected State

Shown when `GET /api/v1/settings/billing/stripe-connect/status` returns `{ connected: true, account_name: "Acme Electric LLC", ... }`.

### Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  [CheckCircleIcon w-5 h-5 text-margin-600]  Stripe Account       │
│                                              ─ Connected         │
│                                                                   │
│  Acme Electric LLC                                               │
│  Customers can now pay by card on invoice payment pages.         │
│                                                                   │
│  [Disconnect]                                                     │
└──────────────────────────────────────────────────────────────────┘
```

### Card Header Row (Connected)

| Element | Spec |
|---|---|
| Icon | `CheckCircleIcon` (Heroicons 2.0 **solid**) `w-5 h-5 text-margin-600 mr-2` |
| Title | `"Stripe Account"` — `text-h3 font-medium text-neutral-900` |
| Connected badge | Inline next to title: `"Connected"` — `ml-2 inline-flex items-center rounded-full bg-margin-100 px-2.5 py-0.5 text-caption font-medium text-margin-700` |
| Header layout | `flex items-center` |

### Account Display

| Element | Spec |
|---|---|
| Account name | `{account_name}` — `text-body font-medium text-neutral-900 mt-4` |
| Fallback (if account_name null) | Show `account_id` masked: `"Stripe account (...{last 6 of account_id})"` |
| Description | `"Customers can now pay by card on invoice payment pages."` — `text-body text-neutral-600 mt-1` |

### Disconnect Button

| Property | Value |
|---|---|
| Label | `"Disconnect"` |
| Variant | Outlined destructive |
| Base classes | `inline-flex items-center rounded-md border border-fault-300 bg-white px-4 py-2 text-sm font-medium text-fault-700 shadow-sm` |
| Hover | `hover:bg-fault-50` |
| Focus | `focus:outline-none focus:ring-2 focus:ring-fault-500 focus:ring-offset-2` |
| Icon | `XCircleIcon` (Heroicons 2.0 outline) `w-4 h-4 mr-1.5 text-fault-600` |
| Position | `mt-5` below the account description, left-aligned |
| Width | `auto` (not full-width — this is a secondary destructive action) |

**Interaction**: Clicking "Disconnect" opens the confirmation modal (Section 5). Does NOT immediately disconnect.

---

## 4. Manual Payment Info Section

Always visible below the Connection Status Card, regardless of Stripe connection state. This is informational content shown with a positive framing — "always available" not "fallback option."

### Layout

```
Manual Payment Options
──────────────────────────────────────────────────────────────

Even without Stripe, your customers can pay by:

  ✓  Check — mail to your business address
  ✓  Cash — in person at time of service
  ✓  Zelle / Venmo — your contact details on the invoice
  ✓  Wire transfer — for commercial clients

When a payment is received, record it in Pilot from the
invoice detail page → "Record Payment".
```

### Pixel Spec

| Property | Value |
|---|---|
| Container margin-top | `mt-6` |
| Container style | Not a card — plain section with a top border separator |
| Section separator | `border-t border-neutral-200 pt-6` |
| Section title | `"Manual Payment Options"` — `text-h3 font-medium text-neutral-900 mb-3` |
| Intro text | `"Even without Stripe, your customers can pay by:"` — `text-body text-neutral-600 mb-4` |

### Bullet List

| Property | Value |
|---|---|
| List container | `space-y-2` |
| Each item layout | `flex items-start` |
| Bullet icon | `CheckIcon` (Heroicons 2.0 solid) `w-4 h-4 text-margin-600 mr-2 mt-0.5 shrink-0` |
| Item text | `text-body text-neutral-700` |
| Items | `"Check — mail to your business address"` / `"Cash — in person at time of service"` / `"Zelle / Venmo — your contact details on the invoice"` / `"Wire transfer — for commercial clients"` |

### Record Payment Note

| Property | Value |
|---|---|
| Container | `mt-4 rounded-md bg-neutral-50 border border-neutral-200 px-4 py-3` |
| Icon | `DocumentTextIcon` (Heroicons 2.0 outline) `w-4 h-4 text-neutral-500 mr-2 mt-0.5 shrink-0` |
| Layout | `flex items-start` |
| Text | `"When a payment is received, record it in Pilot from the invoice detail page → \"Record Payment\"."` |
| Text style | `text-caption text-neutral-600` |

**Collapsible or always expanded**: **Always expanded.** This information is brief, important for onboarding, and does not warrant a collapse interaction.

---

## 5. Disconnect Confirmation Modal

Shown when the contractor clicks "Disconnect" in the connected state card.

### Layout

```
┌─────────────────────────────────────────────────────────┐
│  Disconnect Stripe?                          [✕ close]  │
│  ─────────────────────────────────────────────────────  │
│                                                         │
│  Disconnecting your Stripe account will:                │
│                                                         │
│  •  Prevent new card payments on invoice payment pages  │
│  •  Customers will see manual payment instructions      │
│     instead of a payment form                           │
│  •  Existing recorded payments are not affected         │
│                                                         │
│  ─────────────────────────────────────────────────────  │
│                             [Cancel]  [Disconnect Stripe]│
└─────────────────────────────────────────────────────────┘
```

### Modal Pixel Spec

| Property | Value |
|---|---|
| Overlay | `fixed inset-0 bg-neutral-900/50 z-50` |
| Modal panel | `bg-white rounded-lg shadow-xl max-w-md w-full mx-auto mt-16 p-6` |
| z-index | `z-50` (per design system modal pattern) |
| Animation | `transition: opacity 150ms ease-in` on overlay; panel enters with `transform: scale(0.95) → scale(1.0) 150ms ease-out` |

### Modal Header

| Element | Spec |
|---|---|
| Title | `"Disconnect Stripe?"` — `text-h2 font-semibold text-neutral-900` |
| Close button | `XMarkIcon` (Heroicons 2.0 outline) `w-5 h-5 text-neutral-400` — `absolute top-4 right-4 hover:text-neutral-600 p-1 rounded` |
| Divider below title | `border-t border-neutral-200 mt-4 mb-4` |

### Modal Body

| Element | Spec |
|---|---|
| Intro text | `"Disconnecting your Stripe account will:"` — `text-body text-neutral-700 mb-3` |
| List container | `space-y-2` |
| Each bullet layout | `flex items-start` |
| Bullet marker | `ExclamationTriangleIcon` (Heroicons 2.0 outline) `w-4 h-4 text-fault-500 mr-2 mt-0.5 shrink-0` — use on first two items only |
| Bullet marker (safe item) | `CheckIcon` (Heroicons 2.0 outline) `w-4 h-4 text-margin-600 mr-2 mt-0.5 shrink-0` — for "Existing payments not affected" |
| Item text | `text-body text-neutral-700` |

**Bullet items:**
1. (⚠ `ExclamationTriangleIcon`) `"Prevent new card payments on invoice payment pages"`
2. (⚠ `ExclamationTriangleIcon`) `"Customers will see manual payment instructions instead of a payment form"`
3. (✓ `CheckIcon`) `"Existing recorded payments are not affected"`

### Modal Footer

| Element | Spec |
|---|---|
| Divider | `border-t border-neutral-200 mt-6 pt-4` |
| Footer layout | `flex justify-end gap-3` |
| Cancel button | `border border-neutral-300 text-neutral-700 rounded-md px-4 py-2 text-sm font-medium hover:bg-neutral-50` |
| Disconnect confirm button | `rounded-md bg-fault-600 px-4 py-2 text-sm font-medium text-white hover:bg-fault-700 focus:outline-none focus:ring-2 focus:ring-fault-500 focus:ring-offset-2` |
| Disconnect confirm label | `"Disconnect Stripe"` |
| Confirm button disabled state | `disabled:opacity-60 disabled:cursor-not-allowed` — shown while DELETE mutation is in-flight |

**Interaction**: Clicking "Disconnect Stripe" fires `DELETE /api/v1/settings/billing/stripe-connect`. While the mutation is pending, the confirm button shows a spinner (see Section 9 loading patterns). On success: modal closes; page re-fetches status (now disconnected); shows a brief `NotificationBanner` success toast: `"Stripe account disconnected."`.

---

## 6. Loading State (Page Load)

While `useStripeConnectStatus()` is fetching on page mount (before the first response arrives).

### Loading State for Connection Status Card

| Property | Value |
|---|---|
| Strategy | **Skeleton** inside the status card — not `<LoadingState>` from `@pilot/ui` (which is a full-page spinner). The card frame itself renders; its interior is replaced by skeleton lines. |
| Card container | Same dimensions as the real card — `bg-white border border-neutral-200 rounded-lg p-6 shadow-sm` |
| Skeleton animate | `animate-pulse` |
| Header skeleton | `h-5 w-40 bg-neutral-200 rounded` |
| Status line skeleton | `mt-4 h-4 w-48 bg-neutral-200 rounded` |
| Description skeleton | `mt-2 h-4 w-full bg-neutral-200 rounded` + `mt-1 h-4 w-3/4 bg-neutral-200 rounded` |
| Button skeleton | `mt-5 h-10 w-full bg-neutral-200 rounded-md` |
| Note skeleton | `mt-4 h-12 bg-neutral-100 rounded-md` |

The Manual Payment section below the card is **not** skeletonized — it is static informational content and renders immediately.

---

## 7. Post-Connect Success Banner

Shown when the page loads with `?connected=true` in the URL query string (the backend callback redirects here after successful OAuth exchange).

### Spec

| Property | Value |
|---|---|
| Component | Use `NotificationBanner` from `@pilot/ui` — the project already has this |
| Position | Top of page content area, above the page H1, below the Settings shell header |
| Style | `bg-margin-50 border border-margin-200 text-margin-800 rounded-md px-4 py-3` |
| Icon | `CheckCircleIcon` (Heroicons 2.0 solid) `w-5 h-5 text-margin-600 mr-3 shrink-0` |
| Message | `"Your Stripe account has been connected. Customers can now pay by card on invoice payment pages."` |
| Dismissible | **Yes** — show `XMarkIcon` button on right. Auto-dismiss after **8 seconds** (`setTimeout`). |
| Animation in | `transition: opacity 200ms ease-in` — fade in on mount |
| Animation out | `transition: opacity 200ms ease-out` — fade out on dismiss or auto-dismiss |
| Margin | `mb-6` below banner, above page H1 |

**Implementation note**: On page mount, check `searchParams.get("connected")` === `"true"`. If true, show the banner and immediately replace the URL with `window.history.replaceState({}, "", "/settings/billing/payment-method")` so refreshing the page does not re-trigger the banner.

---

## 8. Post-Connect Error Banner

Shown when the page loads with `?error=connect_failed` in the URL query string (the backend callback redirects here after a failed OAuth exchange).

### Spec

| Property | Value |
|---|---|
| Component | Use `NotificationBanner` from `@pilot/ui` |
| Position | Same as success banner — top of page content, above page H1 |
| Style | `bg-fault-50 border border-fault-200 text-fault-800 rounded-md px-4 py-3` |
| Icon | `ExclamationCircleIcon` (Heroicons 2.0 solid) `w-5 h-5 text-fault-600 mr-3 shrink-0` |
| Message | `"Could not connect your Stripe account. Please try again or contact support@pilotfortrades.com if the issue continues."` |
| `support@pilotfortrades.com` | Rendered as `<a href="mailto:support@pilotfortrades.com" class="underline">` |
| Dismissible | **Yes** — `XMarkIcon` dismiss button. **No auto-dismiss** (errors require intentional dismissal). |
| Animation | Same as success banner |
| Margin | `mb-6` below banner |

**Implementation note**: Check `searchParams.get("error")` === `"connect_failed"`. Same URL cleanup as success banner via `history.replaceState`.

---

## 9. Connect Button Loading State (Redirect In-Flight)

When the contractor clicks "Connect Stripe Account," the frontend must:
1. Call `GET /api/v1/settings/billing/stripe-connect/authorize` to get the OAuth URL
2. This is a network call that may take 300–800ms before the redirect fires

During this window, the button must communicate activity to prevent double-clicks.

### Button Loading State Spec

| Property | Value |
|---|---|
| Button disabled | `disabled` attribute set — prevents re-click |
| Button label | Replace `"Connect Stripe Account"` with `"Connecting..."` |
| Leading spinner | Replace the `ArrowRightIcon` trailing icon with a spinner: `<span class="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />` |
| Button colors | Same as default — `bg-brand-600 text-white` — do NOT change to neutral/muted (spinner communicates loading, not disabled) |
| Cursor | `cursor-wait` (set via `disabled:cursor-wait` override) |

**Error during authorize fetch**: If the `GET /authorize` call fails (network error, 5xx):
- Button returns to default state (label + arrow icon, not disabled)
- Show inline error text below the button: `"Could not initiate Stripe connection. Please try again."` — `text-caption text-fault-600 mt-2`
- This is a different error path than the post-OAuth `?error=connect_failed` URL param

### Disconnect Confirm Button Loading State (same pattern)

During the `DELETE /stripe-connect` mutation:
- Confirm button: `disabled`, replace label with `"Disconnecting..."` + leading spinner (border-white)
- Cancel button: `disabled` — prevents closing the modal mid-mutation

---

## 10. Interaction States — Complete Reference

### Connect Stripe Account Button

| State | Visual |
|---|---|
| Default | `bg-brand-600 text-white` |
| Hover | `bg-brand-700` |
| Focus | `ring-2 ring-brand-500 ring-offset-2` |
| Active (pressed) | `bg-brand-700` (same as hover) |
| Loading | `bg-brand-600 text-white disabled opacity-60 cursor-wait` + spinner + `"Connecting..."` |

### Disconnect Button (card, outline)

| State | Visual |
|---|---|
| Default | `border border-fault-300 text-fault-700 bg-white` |
| Hover | `bg-fault-50` |
| Focus | `ring-2 ring-fault-500 ring-offset-2` |
| Active | `bg-fault-50` |

### Cancel Button (modal)

| State | Visual |
|---|---|
| Default | `border border-neutral-300 text-neutral-700` |
| Hover | `bg-neutral-50` |
| Disabled (during disconnect) | `opacity-50 cursor-not-allowed` |

### Disconnect Stripe (modal confirm)

| State | Visual |
|---|---|
| Default | `bg-fault-600 text-white` |
| Hover | `bg-fault-700` |
| Focus | `ring-2 ring-fault-500 ring-offset-2` |
| Loading | Same color + spinner + `"Disconnecting..."` |

---

## 11. Transitions and Animations

| Element | Property | Duration | Easing |
|---|---|---|---|
| Success / Error banner fade-in | `opacity: 0 → 1` | `200ms` | `ease-in` |
| Success / Error banner fade-out | `opacity: 1 → 0` | `200ms` | `ease-out` |
| Disconnect confirmation modal overlay | `opacity: 0 → 1` | `150ms` | `ease-in` |
| Disconnect confirmation modal panel scale | `scale(0.95) → scale(1)` | `150ms` | `ease-out` |
| Connection status card state transition (disconnected → connected after reconnect) | Handled by React Query cache invalidation — `useStripeConnectStatus()` refetches and re-renders; no CSS transition needed |
| Skeleton to real content | `transition: opacity 200ms ease` — apply `opacity-0` on skeleton, `opacity-100` on real content (both rendered, skeleton hidden when data arrives) |

---

## 12. Page-Level Layout Spec

The full page assembled, for 1280px viewport in the Settings shell:

```
┌─────────────────────────────────────────────────────────────────┐  (content area starts)
│  [success/error banner — conditional, mb-6]                     │
│                                                                   │
│  Payment Method                                [page H1]         │
│  Manage how your customers can pay their invoices.  [subtitle]   │
│                                                                   │
│  ┌───────────────────────────────────────────────────────┐       │
│  │  SECTION: Connection Status Card                      │       │
│  │  (Disconnected OR Connected state — mutually exclusive)│       │
│  └───────────────────────────────────────────────────────┘       │
│                                                                   │
│  ─────────────────────── (border-t separator)                    │
│                                                                   │
│  SECTION: Manual Payment Options (always visible)                 │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Page Header Spec

| Element | Spec |
|---|---|
| Page title | `"Payment Method"` — `text-h1 font-semibold text-neutral-900` |
| Subtitle | `"Manage how your customers can pay their invoices."` — `text-body text-neutral-500 mt-1` |
| Title-to-first-card gap | `mt-6` |
| Content area padding | `px-6 py-6` (standard) |
| Content max-width | `max-w-2xl` |

---

## 13. Full Page Wireframe Annotation (1280px)

### State A — Disconnected, No Banner

```
px-6 py-6 max-w-2xl
│
├── [H1] Payment Method
│   [p]  Manage how your customers can pay their invoices.
│
├── mt-6
│   ┌── bg-white border border-neutral-200 rounded-lg p-6 shadow-sm ──────────┐
│   │   [LinkIcon w-5 h-5 text-neutral-400]  "Stripe Account"                  │
│   │                                                                           │
│   │   mt-4 [p text-body font-medium] "No Stripe account connected"           │
│   │   mt-1 [p text-body text-neutral-600]                                    │
│   │         "Connect your Stripe account to accept card payments from         │
│   │          your customers directly on invoice payment pages."               │
│   │                                                                           │
│   │   mt-5                                                                    │
│   │   [button w-full bg-brand-600 text-white py-2.5 rounded-md]              │
│   │   [ArrowRightIcon]  Connect Stripe Account                                │
│   │                                                                           │
│   │   mt-4                                                                    │
│   │   [div bg-neutral-50 border-neutral-200 rounded-md px-4 py-3]            │
│   │   [InformationCircleIcon] "You'll be redirected to Stripe's website…"    │
│   └───────────────────────────────────────────────────────────────────────────┘
│
├── border-t border-neutral-200 mt-6 pt-6
│
└── MANUAL PAYMENT SECTION
    [h3] "Manual Payment Options"
    [p]  "Even without Stripe, your customers can pay by:"
    [ul space-y-2]
    ├── [CheckIcon text-margin-600] "Check — mail to your business address"
    ├── [CheckIcon text-margin-600] "Cash — in person at time of service"
    ├── [CheckIcon text-margin-600] "Zelle / Venmo — your contact details on the invoice"
    └── [CheckIcon text-margin-600] "Wire transfer — for commercial clients"
    [div bg-neutral-50 border-neutral-200 mt-4 px-4 py-3 rounded-md]
    [DocumentTextIcon] "When a payment is received, record it in Pilot…"
```

### State B — Connected

```
[same page header]
├── mt-6
│   ┌── bg-white border border-neutral-200 rounded-lg p-6 shadow-sm ──────────┐
│   │   [CheckCircleIcon solid w-5 h-5 text-margin-600]  "Stripe Account"       │
│   │   [badge bg-margin-100 text-margin-700] "Connected"                       │
│   │                                                                           │
│   │   mt-4 [p text-body font-medium] "Acme Electric LLC"                     │
│   │   mt-1 [p text-body text-neutral-600]                                    │
│   │         "Customers can now pay by card on invoice payment pages."         │
│   │                                                                           │
│   │   mt-5                                                                    │
│   │   [button border-fault-300 text-fault-700 hover:bg-fault-50 rounded-md]  │
│   │   [XCircleIcon] Disconnect                                                 │
│   └───────────────────────────────────────────────────────────────────────────┘
[same manual payment section below]
```

---

## 14. Component Manifest

Every file the React Engineer creates or modifies:

| File | Action | Description |
|---|---|---|
| `apps/web/src/app/(authed)/settings/billing/payment-method/page.tsx` | **Create** | New Next.js route file; imports and renders `<PaymentMethodSettingsPage />` |
| `apps/web/src/features/settings/components/PaymentMethodSettingsPage.tsx` | **Create** | Main page component; reads `?connected=true` / `?error=connect_failed` query params; renders page header, Connection Status Card, Manual Payment section; wraps in `<RoleGate permission="settings.tenant.write">` |
| `apps/web/src/features/settings/hooks/useStripeConnectStatus.ts` | **Create** | `useQuery` calling `GET /api/v1/settings/billing/stripe-connect/status`; returns `{ connected, account_name, account_id, account_last4, isLoading, isError }` |
| `apps/web/src/features/settings/hooks/useStripeConnectAuthorize.ts` | **Create** | `useMutation` (or plain async fn) calling `GET /api/v1/settings/billing/stripe-connect/authorize`; returns `{ oauth_url }`; caller sets `window.location.href = oauth_url` |
| `apps/web/src/features/settings/hooks/useStripeConnectDisconnect.ts` | **Create** | `useMutation` calling `DELETE /api/v1/settings/billing/stripe-connect`; on success invalidates the status query cache |
| `apps/web/src/features/settings/components/StripeConnectionCard.tsx` | **Create** | Presentational card component; accepts `status: StripeConnectStatusResponse | null`, `isLoading: boolean`, `isError: boolean`, `onConnect: () => void`, `isConnecting: boolean`, `onDisconnect: () => void`; renders the two states + skeleton |
| `apps/web/src/features/settings/components/DisconnectStripeModal.tsx` | **Create** | Confirmation modal component; accepts `isOpen: boolean`, `onClose: () => void`, `onConfirm: () => void`, `isDisconnecting: boolean` |
| `apps/web/src/features/settings/components/BillingSettingsPage.tsx` | **Update** | Remove the "Payment Methods Placeholder" card (lines 184–199); add a link/button `→ Payment Method settings` pointing to `/settings/billing/payment-method` in its place |
| `apps/web/src/mocks/handlers/stripeConnectHandlers.ts` | **Create** | MSW mock handlers for all 3 Stripe Connect endpoints: `GET /status`, `GET /authorize` (returns `{ oauth_url: "https://connect.stripe.com/oauth/authorize?..." }`), `DELETE /stripe-connect`; register in the MSW handler index barrel |

---

## 15. Implementation Notes for React Engineer

1. **Query param detection on mount**: In `PaymentMethodSettingsPage`, read query params using Next.js `useSearchParams()`. Check for `searchParams.get("connected") === "true"` → show success banner; `searchParams.get("error") === "connect_failed"` → show error banner. After reading, call `window.history.replaceState({}, "", "/settings/billing/payment-method")` to clean the URL so a page refresh doesn't re-show the banner.

2. **The authorize endpoint is a GET, not a POST**: `GET /api/v1/settings/billing/stripe-connect/authorize` — this returns the Stripe OAuth URL. The React hook can use either `useQuery` with `enabled: false` + manual `refetch()`, OR a plain `async function` (not wrapped in `useMutation`). A plain async function called from the button `onClick` is simpler and preferred — avoids query caching of a one-shot redirect flow.

3. **The callback endpoint is handled by the backend**: The React Engineer does NOT implement a `/settings/billing/payment-method/callback` Next.js route. The backend callback at `GET /api/v1/settings/billing/stripe-connect/callback` handles the OAuth code exchange and then issues a `302` redirect to `/settings/billing/payment-method?connected=true`. The Next.js page receives the redirect automatically.

4. **React Query invalidation after disconnect**: In `useStripeConnectDisconnect`, the `onSuccess` handler must call `queryClient.invalidateQueries({ queryKey: ["stripe-connect-status"] })`. This causes `useStripeConnectStatus` to re-fetch and the UI transitions from Connected state to Disconnected state.

5. **`RoleGate` wraps page content, not the route**: The route itself (`page.tsx`) does not need RBAC — the Settings shell layout already requires authentication. The `<RoleGate permission="settings.tenant.write">` wraps the `<StripeConnectionCard>` and Disconnect button, but the Manual Payment section is visible to all authenticated roles (it's purely informational). The page H1 and subtitle are also outside the RoleGate.

6. **MSW mock for authorize endpoint**: Return `{ oauth_url: "https://connect.stripe.com/oauth/authorize?response_type=code&client_id=ca_test&scope=read_write&redirect_uri=..." }`. Do NOT redirect in the MSW handler — the mock only needs to return the URL object. The `onClick` handler in the real component fires `window.location.href = data.oauth_url`. In tests, mock `window.location.href` assignment with `Object.defineProperty(window, 'location', ...)`.

7. **Stripe account name fallback**: `account_name` may be null if Stripe doesn't return a display name for the connected account. If null, render the `account_id` masked as `"Stripe account (acct_…${last6})"`. If `account_id` is also null (which shouldn't happen if `connected: true`, but guard anyway), render `"Stripe account"`.

8. **SettingsSidebar active state**: The `Billing` sidebar item at `/settings/billing` will automatically highlight as an ancestor when the user is on `/settings/billing/payment-method` because the existing `isAncestor()` function in `SettingsSidebar.tsx` uses `pathname.startsWith(href)`. No sidebar changes required for this batch.

9. **BillingSettingsPage update**: The "Payment Methods Placeholder" block (lines 184–199 in `BillingSettingsPage.tsx`) should be replaced with a simple referral row:
   ```
   [CreditCardIcon]  Payment Method
   Manage how your customers pay invoices, including Stripe Connect.
   [→ Payment Method settings]  (Next.js Link)
   ```
   This is a `<Link href="/settings/billing/payment-method">` styled as `text-brand-600 hover:underline text-sm font-medium`.

10. **Loading state implementation**: Do NOT use `<LoadingState>` from `@pilot/ui` for the connection card — that component is designed for full-section empty/error states, not for in-card skeletons. Implement the skeleton inline in `StripeConnectionCard.tsx` using `animate-pulse` divs as specified in Section 6.

---

## 16. Token Quick Reference (this page only)

| Use | Token |
|---|---|
| Page background | `bg-neutral-50` |
| Card/panel | `bg-white border border-neutral-200 rounded-lg shadow-sm` |
| Connect CTA button | `bg-brand-600 text-white hover:bg-brand-700` |
| Connect CTA focus ring | `ring-brand-500` |
| Loading spinner | `border-white border-t-transparent` (on dark bg button) |
| Disconnect outline button | `border-fault-300 text-fault-700 hover:bg-fault-50` |
| Disconnect confirm (modal) | `bg-fault-600 text-white hover:bg-fault-700` |
| Connected status icon | `text-margin-600` |
| Connected badge | `bg-margin-100 text-margin-700` |
| Success banner | `bg-margin-50 border-margin-200 text-margin-800` |
| Error banner | `bg-fault-50 border-fault-200 text-fault-800` |
| Info note background | `bg-neutral-50 border-neutral-200` |
| Check icons (manual payment) | `text-margin-600` |
| Warning icons (modal bullets) | `text-fault-500` |
| Section divider | `border-neutral-200` |
| Secondary text | `text-neutral-600` |
| Body text | `text-neutral-900` |
| Caption text | `text-neutral-500` / `text-neutral-600` |

---

## 17. Icon Inventory

| Icon name (Heroicons 2.0) | Variant | Size | Color token | Used for |
|---|---|---|---|---|
| `LinkIcon` | outline | `w-5 h-5` | `text-neutral-400` | Card header — disconnected state |
| `CheckCircleIcon` | **solid** | `w-5 h-5` | `text-margin-600` | Card header — connected state |
| `ArrowRightIcon` | outline | `w-4 h-4` | `text-white` | Connect button trailing icon |
| `XCircleIcon` | outline | `w-4 h-4` | `text-fault-600` | Disconnect button leading icon |
| `InformationCircleIcon` | outline | `w-4 h-4` | `text-neutral-500` | Redirect info note |
| `CheckIcon` | **solid** | `w-4 h-4` | `text-margin-600` | Manual payment list bullets; modal "safe" bullet |
| `DocumentTextIcon` | outline | `w-4 h-4` | `text-neutral-500` | Record Payment note |
| `XMarkIcon` | outline | `w-5 h-5` | `text-neutral-400` | Modal close button |
| `ExclamationTriangleIcon` | outline | `w-4 h-4` | `text-fault-500` | Modal warning bullets |
| `ExclamationCircleIcon` | **solid** | `w-5 h-5` | `text-fault-600` | Error banner icon |
| `CreditCardIcon` | outline | `w-4 h-4` | `text-neutral-500` | BillingSettingsPage referral row |

---

## Handoff Gate

This spec is ready for Tom's review. **Implementation starts only after Tom approves this design spec.** Once approved:

1. **Python Engineer** runs first: DB migration (`stripe_connect_account_id` column) + 4 Stripe Connect endpoints + update `stripe_payment_intents.py` + regenerate `openapi.json`
2. **React Engineer** runs second: `pnpm sync-api-types` → implement hooks + page component + update `BillingSettingsPage` + MSW handlers

No code is written until Tom confirms approval.
