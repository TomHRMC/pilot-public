# TEAM-INVITE-1 — UI Design Spec (Part B Gate)

**Batch code**: TEAM-INVITE-1
**Version**: 1.0 · **Date**: 2026-09-03 · **Author**: Pilot Web UI Designer
**Status**: DESIGN SPEC — for Tom approval → then Architect authors the Part B React prompt
**Commissioned by**: `batch-team-invite-1-design.md` §H (commission brief) + §I (Component Manifest — reconciled below) + §D (API contracts)
**Scope**: Web only, desktop-first 1280px. 3 surfaces.

---

## 0. Pre-Design Audit Summary

| Input read | Key findings informing this spec |
|---|---|
| `TeamSettingsPage.tsx` | P0 placeholder `InviteDialog` (lines 46–67) renders literal "coming soon" — replaced by [`InviteMemberDialog`](#1-invite-dialog). `ROLE_OPTIONS` already in BE vocabulary (owner/office_staff/technician/accountant). `RoleBadge` component (lines 24–44) uses hardcoded color map — **flagged for token reconciliation** (see §1.6). `useRequiresPermission("settings.manage")` gates the page — **changed to `users.manage`** per design §I.5/G.10. |
| `packages/ui/src/index.ts` | No shared Dialog/Modal primitive exists in the barrel. `CharterUpgradeModal` (feature-local) is the focus-trap precedent — [`InviteMemberDialog`](#1-invite-dialog) mirrors its pattern (feature-local, not promoted to `packages/ui`). `EmptyState`, `LoadingState`, `ErrorState` from `@pilot/ui/states` — composed for [`PendingInvitesSection`](#2-pending-invites-section). `RoleGate` / `useRequiresPermission` from `@pilot/ui/role-gate` — gates the invite button. `NotificationBanner` from `@pilot/ui` — used for in-modal errors. `PendingBadge` from `@pilot/ui` — used for optimistic mutation markers. |
| `SettingsSidebar.tsx` | Team is the first sidebar item (line 38), no `roleRequired` — all authenticated roles see it. No change needed. |
| `permissions.ts` | **No `users.manage` key exists** — this spec adds it (owner-only). `PilotRole` union (line 17 of `auth/types.ts`) = `"owner" | "tech" | "office_staff" | "operator"` — ADR-0010 reconciliation (`tech`→`technician`, `operator`→`accountant`) is Part B scope (§I.5) but **does not block this spec's visual design**; the role *select* uses BE vocabulary codes directly. |
| `CharterUpgradeModal.tsx` | Focus-trap pattern (lines 78–105): `useEffect` keydown listener, Tab cycling, Escape-to-close (suppressed during loading), overlay click suppressed during loading, `triggerRef` focus restore. [`InviteMemberDialog`](#1-invite-dialog) and the Revoke confirm modal both mirror this pattern. |
| `PublicInvoicePage.tsx` | Public-page state machine pattern (lines 38–43): `loading` → `error-invalid` → `error-generic` → `ready`. Uses raw `fetch` (not `apiClient`) per Rule 35 exception — no auth context. [`InviteLandingPage`](#3-invite-landing-page) mirrors this. `PoweredByPilotFooter` from `public-quote` — reused on the landing page. |
| `useCognitoSignUp.ts` | Cognito `signUp` via dynamic import (line 78). The landing page CTA hands off into `/signup/account?email=...` — the existing account page pre-fills from query param (engineer adds `searchParams.get("email")` to `defaultValues`). |
| `useTeamUsers.ts` | Query key `["team-users"]`. New hooks use `["team-invites"]` query key. On invite acceptance (Lambda Path 2), the `team-users` query is invalidated by the `useCreateInvite` / `useResendInvite` / `useRevokeInvite` `onSuccess` handlers (409-and-refresh pattern). |
| `client.ts` | `apiClient` is an Axios instance. `Idempotency-Key` header is passed via the `headers` config option on individual `.post()` calls (not a global interceptor) — mirrors the pattern in `InvoicePaymentModal.tsx`. |
| `problem.ts` | `getApiProblem(err)` normalizes RFC 7807 errors into `{ status, detail, code }`. The `code` field (line 34) carries the machine-readable error code (e.g., `invite_pending_exists`, `invite_user_exists`) — used by [`InviteMemberDialog`](#1-invite-dialog) to branch 409 states. |

---

## Design Token Reference (all colors are `pilotPreset` names — zero hex)

| Purpose | Token |
|---|---|
| Primary brand (CTA) | `bg-brand-600`, `hover:bg-brand-700`, `text-white` |
| Active/selected | `bg-brand-50`, `text-brand-700`, `border-brand-500` |
| Borders | `border-neutral-200`, `border-neutral-300` |
| Body text | `text-neutral-900` |
| Secondary text | `text-neutral-500`, `text-neutral-600` |
| Error / destructive | `text-fault-600`, `bg-fault-50`, `border-fault-200`, `hover:bg-fault-700` |
| Success / positive | `text-margin-700`, `bg-margin-50` |
| Warning / pending | `text-alert-700`, `bg-alert-50`, `border-alert-200` |
| Page background | `bg-neutral-50` |
| Card/panel | `bg-white` |
| Overlay | `bg-neutral-900/50` |
| Shadow | `shadow-sm`, `shadow-xl` |

---

## Icon Inventory (all Heroicons 2.0, outline variant unless noted)

| Icon | Where used | Size |
|---|---|---|
| `UserPlusIcon` | Invite button (header CTA) | `w-5 h-5` |
| `XMarkIcon` | Modal close button | `w-5 h-5` |
| `PaperAirplaneIcon` | Send invite submit button (in-flight spinner replaces) | `w-4 h-4` |
| `CheckCircleIcon` | Success confirmation state | `w-8 h-8` |
| `ExclamationCircleIcon` | 409 `invite_user_exists` explainer, error states | `w-5 h-5` |
| `ArrowPathIcon` | Resend action, in-flight spinner | `w-4 h-4` |
| `ClockIcon` | Expiry countdown, pending status chip | `w-4 h-4` |
| `EnvelopeIcon` | Email field, invite landing email display | `w-5 h-5` |
| `ShieldCheckIcon` | Role descriptions (owner), landing page role display | `w-5 h-5` |
| `Cog6ToothIcon` | Role descriptions (office_staff) | `w-5 h-5` |
| `WrenchScrewdriverIcon` | Role descriptions (technician) | `w-5 h-5` |
| `CalculatorIcon` | Role descriptions (accountant) | `w-5 h-5` |
| `TrashIcon` | Revoke action | `w-4 h-4` |
| `ArrowRightIcon` | Landing page SignUp CTA | `w-4 h-4` |
| `ExclamationTriangleIcon` | Revoke confirm modal warning, invalid landing state | `w-6 h-6` |

---

## 1. Invite Dialog

### 1.1 Surface Overview

| Attribute | Value |
|---|---|
| **Component** | `InviteMemberDialog` |
| **Route** | `/settings/team` (modal overlay on the team page) |
| **Replaces** | Placeholder `InviteDialog` in `TeamSettingsPage.tsx` (P0 "coming soon" — Rule 9.4) |
| **RBAC** | `<RoleGate permission="users.manage">` — owner only. The "Invite team member" button is hidden (not disabled) for non-owners per hide-not-disable rule. |
| **API** | `POST /api/v1/users/invites` (D1) — `Idempotency-Key` header required |
| **Pattern** | Optimistic UI (§16.8) on submit; 409-and-refresh (§16) on duplicate states |

### 1.2 Layout — Modal Panel

```
┌─────────────────────────────────────────────┐  max-w-lg (512px)
│  [UserPlusIcon]  Invite Team Member    [X]   │  h-auto, p-6
│                                               │
│  ─────────────────────────────────────────── │  border-b border-neutral-100
│                                               │
│  Email address *                              │  <label> text-sm font-medium
│  ┌─────────────────────────────────────────┐ │
│  │ [EnvelopeIcon]  colleague@example.com   │ │  input w-full, pl-10
│  └─────────────────────────────────────────┘ │
│  We'll send them an invitation email.         │  helper text-xs text-neutral-500
│                                               │
│  Role *                                       │  <label> text-sm font-medium
│  ┌─────────────────────────────────────────┐ │
│  │  ○ Owner                                │ │  radio card (selected)
│  │    Full access — manage team, billing,   │ │
│  │    settings, and all operations.         │ │
│  ├─────────────────────────────────────────┤ │
│  │  ○ Office Staff                         │ │  radio card
│  │    Dispatch, quotes, invoices, jobs,    │ │
│  │    customers. No billing or settings.   │ │
│  ├─────────────────────────────────────────┤ │
│  │  ○ Technician                           │ │  radio card
│  │    Field jobs, schedule, catalog,       │ │
│  │    customer info. No financial data.    │ │
│  ├─────────────────────────────────────────┤ │
│  │  ○ Accountant                          │ │  radio card
│  │    Read-only financials, reports,      │ │
│  │    invoices. No settings or dispatch.   │ │
│  └─────────────────────────────────────────┘ │
│                                               │
│  ┌─────────────────────────────────────────┐ │  409 error banner (conditional)
│  │ [ExclamationCircleIcon]                 │ │  bg-alert-50 border-alert-200
│  │ A pending invite already exists for      │ │
│  │ this email. [Resend invite]              │ │
│  └─────────────────────────────────────────┘ │
│                                               │
│              [Cancel]  [Send invite →]        │  justify-end, gap-3
└─────────────────────────────────────────────┘
```

### 1.3 Pixel Specs — Modal Shell

| Element | Spec |
|---|---|
| Overlay | `fixed inset-0 bg-neutral-900/50 z-50 flex items-start justify-center` |
| Panel | `bg-white rounded-lg shadow-xl max-w-lg w-full mx-auto mt-16 p-6` |
| Header row | `flex items-center justify-between mb-4` |
| Title icon | `UserPlusIcon` `w-5 h-5 text-brand-600` (left of title) |
| Title text | `text-h2 font-semibold text-neutral-900` — "Invite Team Member" |
| Close button | `XMarkIcon` `w-5 h-5`, wrapper `p-2.5 rounded-md text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 focus-visible:ring-2 focus-visible:ring-brand-500` — target 40×40px (padded) |
| Divider | `border-b border-neutral-100 mb-4` |
| Body | `flex flex-col gap-4` |
| Button bar | `flex justify-end gap-3 mt-6` |

### 1.4 Pixel Specs — Email Field

| Element | Spec |
|---|---|
| Label | `<label>` `text-sm font-medium text-neutral-700 mb-1` — "Email address *" |
| Input wrapper | `relative` |
| Input | `w-full rounded-md border pl-10 pr-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1` |
| Default border | `border-neutral-300` |
| Error border | `border-fault-600 bg-fault-50` (when `aria-invalid`) |
| Leading icon | `EnvelopeIcon` `w-5 h-5 text-neutral-400` at `absolute left-3 top-1/2 -translate-y-1/2` |
| Helper text | `text-xs text-neutral-500 mt-1` — "We'll send them an invitation email." |
| Error text | `text-xs text-fault-600 mt-1 role="alert"` — linked via `aria-describedby` |
| `autoComplete` | `email` |
| `inputMode` | `email` |

### 1.5 Pixel Specs — Role Select (Radio Card Group)

| Element | Spec |
|---|---|
| Group label | `<span>` `text-sm font-medium text-neutral-700 mb-2` — "Role *" |
| Container | `role="radiogroup" aria-label="Role"` `flex flex-col gap-2` |
| Card (default) | `role="radio" aria-checked={false}` `px-4 py-3 rounded-md border border-neutral-200 bg-white text-left cursor-pointer motion-safe:transition-colors focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1` |
| Card (selected) | `border-brand-500 bg-brand-50` + `aria-checked={true}` |
| Card (hover) | `hover:border-brand-400` |
| Role name | `block text-sm font-medium text-neutral-900` |
| Role description | `block text-caption text-neutral-500 mt-0.5` |
| Target size | Each card min-height 44px (WCAG 2.5.8) |

**Role options data** (plain-language descriptions — these are the exact copy strings):

| `value` | Label | Description |
|---|---|---|
| `owner` | Owner | Full access — manage team, billing, settings, and all operations. |
| `office_staff` | Office Staff | Dispatch, quotes, invoices, jobs, customers. No billing or settings. |
| `technician` | Technician | Field jobs, schedule, catalog, customer info. No financial data. |
| `accountant` | Accountant | Read-only financials, reports, invoices. No settings or dispatch. |

> **Note**: The `value` codes match the backend `tenant_user_role.code` vocabulary exactly. The ADR-0010 FE rename (`tech`→`technician`, `operator`→`accountant` in `PilotRole`) is Part B implementation scope (§I.5) — the select uses BE codes directly, so the visual design is unaffected.

### 1.6 Pixel Specs — 409 Error Banners (conditional, below role select)

**409 `invite_pending_exists`** (offer Resend inline):

| Element | Spec |
|---|---|
| Container | `rounded-md bg-alert-50 border border-alert-200 p-3 flex items-start gap-2` |
| Icon | `ExclamationCircleIcon` `w-5 h-5 text-alert-600 mt-0.5 shrink-0` |
| Text | `text-sm text-alert-700` — "A pending invite already exists for this email." |
| Resend link | `text-sm text-brand-700 font-medium underline hover:text-brand-800 focus-visible:ring-2 focus-visible:ring-brand-500 rounded` — "Resend invite" — fires `useResendInvite` with the invite `id` from the 409 response detail |

**409 `invite_user_exists`** (explainer — person already has a Pilot account):

| Element | Spec |
|---|---|
| Container | `rounded-md bg-neutral-50 border border-neutral-200 p-3 flex items-start gap-2` |
| Icon | `ExclamationCircleIcon` `w-5 h-5 text-neutral-500 mt-0.5 shrink-0` |
| Text | `text-sm text-neutral-700` — "This person already has a Pilot account. They may already be on your team — check the members list above." |

**422 validation error** (inline email field error — no banner):

| Element | Spec |
|---|---|
| Error text | `text-xs text-fault-600 mt-1 role="alert"` — "Enter a valid email address." |
| Input border | `border-fault-600 bg-fault-50` |
| `aria-invalid` | `true` on the input |
| `aria-describedby` | `"invite-email-error"` |

### 1.7 Pixel Specs — Buttons

| Button | Spec |
|---|---|
| Cancel (secondary) | `border border-neutral-300 text-neutral-700 rounded-md px-4 py-2.5 min-h-11 text-sm font-medium hover:bg-neutral-50 focus-visible:ring-2 focus-visible:ring-brand-500` |
| Send invite (primary) | `bg-brand-600 text-white rounded-md px-4 py-2.5 min-h-11 text-sm font-medium hover:bg-brand-700 focus-visible:ring-2 focus-visible:ring-brand-500 disabled:bg-neutral-300 disabled:cursor-not-allowed inline-flex items-center justify-center` |
| Send invite (in-flight) | `disabled` + `ArrowPathIcon` `w-4 h-4 mr-2 animate-spin motion-reduce:hidden` + text "Sending…" |
| Send invite (default text) | "Send invite →" with `ArrowRightIcon` `w-4 h-4 ml-1` (inline) — actually use text "Send invite" without icon to keep it simple; the arrow is optional. **Decision**: text "Send invite" only, no trailing icon (keeps the button clean; the `PaperAirplaneIcon` is not used on the button to avoid clutter). |

### 1.8 State Coverage

| State | Visual |
|---|---|
| **Default (form)** | Empty email, role defaults to `technician` (most common invite), no errors |
| **Email format error (422)** | Inline `text-fault-600` error below email field, `border-fault-600` on input, `aria-invalid` |
| **409 `invite_pending_exists`** | Alert banner below role select with "Resend invite" link. Form stays interactive. Email field not cleared. |
| **409 `invite_user_exists`** | Neutral banner below role select. Form stays interactive. |
| **Send in-flight** | Submit button disabled + spinner, overlay click suppressed, Escape suppressed (mirrors `CharterUpgradeModal` lines 82–84, 108–111) |
| **Success** | Modal body replaced with success state: `CheckCircleIcon` `w-8 h-8 text-margin-600` centered, "Invite sent!" `text-h2 font-semibold text-neutral-900`, "We've sent an invitation to {email}. They'll appear in your team list once they accept." `text-sm text-neutral-600`, single "Done" button (`bg-brand-600 text-white rounded-md px-4 py-2.5 min-h-11 text-sm font-medium hover:bg-brand-700`). Auto-closes after 3s via `setTimeout` (cleared on unmount). |
| **Network error** | `NotificationBanner` severity `error` inside modal above button bar (mirrors `CharterUpgradeModal` lines 244–258) — "Could not send invite. Check your connection and try again." Modal stays open for retry. |

### 1.9 Interaction States — All Interactive Elements

**Email input:**
| State | Spec |
|---|---|
| Default | `border-neutral-300 bg-white` |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1` |
| Error | `border-fault-600 bg-fault-50` |
| Disabled | N/A (never disabled) |

**Role radio cards:**
| State | Spec |
|---|---|
| Default | `border-neutral-200 bg-white` |
| Hover | `hover:border-brand-400` |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1` |
| Selected | `border-brand-500 bg-brand-50` + `aria-checked=true` |
| Active (mouse down) | `active:scale-[0.99]` (subtle, `motion-safe:transition-transform`) |

**Send invite button:**
| State | Spec |
|---|---|
| Default | `bg-brand-600 text-white` |
| Hover | `hover:bg-brand-700` |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-brand-500` |
| Active | `active:bg-brand-800` |
| Disabled (in-flight) | `disabled:bg-neutral-300 disabled:cursor-not-allowed` + spinner |

**Cancel button:**
| State | Spec |
|---|---|
| Default | `border-neutral-300 text-neutral-700 bg-white` |
| Hover | `hover:bg-neutral-50` |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-brand-500` |
| Active | `active:bg-neutral-100` |
| Disabled | N/A (never disabled — but suppressed during in-flight via overlay click suppression; the button itself remains clickable to allow cancel-during-send) |

**Close (X) button:**
| State | Spec |
|---|---|
| Default | `text-neutral-400` |
| Hover | `hover:text-neutral-600 hover:bg-neutral-100` |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-brand-500` |
| Disabled (in-flight) | `opacity-50 pointer-events-none` (suppressed during send) |

**Resend invite link (409 `invite_pending_exists`):**
| State | Spec |
|---|---|
| Default | `text-brand-700 underline` |
| Hover | `hover:text-brand-800` |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-brand-500 rounded` |
| Active | `active:text-brand-900` |
| In-flight | `opacity-50 pointer-events-none` + inline `ArrowPathIcon` spinner `w-3 h-3 animate-spin` |

### 1.10 Animation Spec

| Element | Transition | Reduced-motion |
|---|---|---|
| Role card select | `transition: background-color 150ms ease-in-out, border-color 150ms ease-in-out` | `@media (prefers-reduced-motion: reduce)` → no transition |
| Role card active | `transition: transform 100ms ease-in-out` (scale 0.99) | No transition |
| Submit spinner | `animation: spin 600ms linear infinite` | `motion-reduce:hidden` (spinner hidden; text "Sending…" remains) |
| Success auto-close | `setTimeout(3000)` → `onClose()` | No animation; the 3s delay remains (it's a timer, not motion) |
| Modal open/close | `motion-safe:transition-opacity` on overlay, `motion-safe:transition-transform` on panel | No transition (instant appear/disappear) |

### 1.11 Accessibility Notes — Invite Dialog

- **Focus trap**: On open, focus moves to the email input. Tab cycles within the modal (mirrors `CharterUpgradeModal` lines 87–101). On close, focus returns to the "Invite team member" trigger button (`triggerRef` pattern).
- **Escape to close**: `Escape` key closes the modal — suppressed during send-in-flight (prevents accidental close mid-mutation).
- **Overlay click**: Clicking the overlay closes the modal — suppressed during send-in-flight.
- **`role="dialog"` + `aria-modal="true"`** on the overlay div. `aria-labelledby` points to the title heading `id`.
- **Email field**: Visible `<label>` above input (not placeholder-as-label). `aria-invalid` set on validation error. `aria-describedby` links to error text `id`.
- **Role select**: `role="radiogroup"` with `aria-label="Role"`. Each card is `role="radio"` with `aria-checked`. Keyboard: Arrow keys move between options (standard radiogroup pattern), Space/Enter selects.
- **Target sizes**: Close button 40×40px (padded `p-2.5`), submit/cancel buttons `min-h-11` (44px), role cards min-height 44px. All ≥ 24×24px.
- **Color-independent status**: 409 errors use icon + text, not color alone. The alert banner has `ExclamationCircleIcon` + text. The neutral banner has `ExclamationCircleIcon` + text. The 422 error has text message + `role="alert"`.
- **Focus not obscured**: Modal is `z-50`, above the `h-12` sticky header (`z-30`). No `NotificationBanner` portal competes (the in-modal banner is inline, not portaled).
- **Reduced motion**: All transitions have `motion-safe:` prefix; spinner hidden via `motion-reduce:hidden`.

### 1.12 RoleBadge Token Reconciliation (flagged deviation)

The existing `RoleBadge` in `TeamSettingsPage.tsx` uses `bg-success-100 text-success-700` for technician — **`success` is not a valid pilotPreset token** (the design system uses `margin` for positive/success). This spec flags this as a **token reconciliation fix** to be applied in the same PR:

| Role | Current (invalid) | Corrected (token-only) |
|---|---|---|
| owner | `bg-brand-100 text-brand-700` | `bg-brand-100 text-brand-700` (no change) |
| office_staff | `bg-neutral-100 text-neutral-700` | `bg-neutral-100 text-neutral-700` (no change) |
| technician | `bg-success-100 text-success-700` | `bg-blue-100 text-blue-700` |
| accountant | `bg-alert-100 text-alert-700` | `bg-alert-100 text-alert-700` (no change) |

> **Rationale**: `technician` is a field role, not a "success" state. `blue-100/blue-700` is a neutral informational token that doesn't conflict with the `margin` (positive/financial) or `alert` (warning) semantics. This also aligns with the `scheduled` job status badge (`bg-blue-100 text-blue-700`) which is the closest semantic cousin.

---

## 2. Pending Invites Section

### 2.1 Surface Overview

| Attribute | Value |
|---|---|
| **Component** | `PendingInvitesSection` |
| **Route** | `/settings/team` — rendered below the members table, inside `TeamContent` |
| **RBAC** | Visible to all roles who can view `/settings/team` (no `roleRequired` on the sidebar item). The Resend/Revoke action buttons are `<RoleGate permission="users.manage">` — owner only (hide-not-disable). |
| **API** | `GET /api/v1/users/invites` (D2) for list; `POST .../resend` (D3); `POST .../revoke` (D4) |
| **Pattern** | Optimistic UI (§16.8) on Resend/Revoke; 409-and-refresh on `invite_already_accepted` / `invite_revoked` |

### 2.2 Layout — Section

```
┌──────────────────────────────────────────────────────────┐  max-w-4xl
│  Pending Invites                                          │  text-h2 font-semibold
│  Invitations waiting for acceptance.                      │  text-sm text-neutral-500
│                                                           │
│  ┌──────────────────────────────────────────────────────┐ │  rounded-md border
│  │  Email          Role        Sent    Expires   Status  │ │  border-neutral-200
│  │───────────────────────────────────────────────────────│ │  overflow-hidden
│  │  jane@acme.example.com  [Office]   Sep 1   4 days  [Pending] │ │  table header
│  │                 [Resend]  [Revoke]                     │ │  row actions
│  │───────────────────────────────────────────────────────│ │
│  │  bob@acme.example.com   [Tech]      Aug 28  Expired  [Expired]│ │
│  │                 [Resend]  [Revoke]                     │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                           │
│  (empty state when no invites)                            │
└──────────────────────────────────────────────────────────┘
```

### 2.3 Pixel Specs — Section Header

| Element | Spec |
|---|---|
| Container | `mt-8` (below members table) |
| Title | `text-h2 font-semibold text-neutral-900` — "Pending Invites" |
| Subtitle | `text-sm text-neutral-500 mt-1` — "Invitations waiting for acceptance." |

### 2.4 Pixel Specs — Table

| Element | Spec |
|---|---|
| Table wrapper | `rounded-md border border-neutral-200 overflow-hidden mt-4` |
| Header row | `bg-neutral-50 border-b border-neutral-200` |
| Header cell | `px-4 py-3 text-sm font-medium text-neutral-700 text-left` |
| Body row | `border-b border-neutral-100 hover:bg-neutral-50` |
| Body cell | `px-4 py-3 text-sm text-neutral-900` |
| Row actions cell | `px-4 py-3` — inline buttons, `flex items-center gap-2` |

**Columns:**

| Column | Content | Width |
|---|---|---|
| Email | `text-sm text-neutral-900` | flex-1 (widest) |
| Role | `RoleBadge` component (reused from TeamSettingsPage, token-corrected per §1.12) | `w-32` |
| Sent | `text-sm text-neutral-500` — formatted date `MMM d` | `w-24` |
| Expires | `text-sm` — countdown ("4 days", "Expired", "Today") | `w-28` |
| Status | Status chip (see §2.5) | `w-28` |
| Actions | Resend + Revoke buttons (owner only) | `w-40` |

### 2.5 Status Chips

| Status | Label | Token classes | Icon |
|---|---|---|---|
| `pending` | Pending | `bg-alert-50 text-alert-700 border border-alert-200` | `ClockIcon` `w-3.5 h-3.5` |
| `expired` | Expired | `bg-neutral-100 text-neutral-500 border border-neutral-200` | `ClockIcon` `w-3.5 h-3.5` |
| `accepted` | Accepted | `bg-margin-50 text-margin-700 border border-margin-200` | `CheckCircleIcon` `w-3.5 h-3.5` |
| `revoked` | Revoked | `bg-neutral-100 text-neutral-500 border border-neutral-200` | `XMarkIcon` `w-3.5 h-3.5` |

> **Note**: `accepted` and `revoked` invites appear in the list per D2 (all states returned). However, accepted invites "disappear into the members list" — the design decision is: **accepted invites are filtered out of the pending section** (they're now members). The `accepted` and `revoked` chips exist for the brief window before the query refetches. The engineer filters `status !== "accepted"` from the D2 response for the pending section display. Revoked invites remain visible (so the owner sees the revoke took effect) until the next page load.

**Chip spec:**
| Element | Spec |
|---|---|
| Container | `inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium` |
| Icon | `w-3.5 h-3.5` (inline, before text) |

### 2.6 Expiry Countdown Display

The `expires_at` field is an ISO timestamp. The countdown is computed client-side:

| Condition | Display | Token |
|---|---|---|
| > 1 day remaining | "{n} days" | `text-neutral-500` |
| ≤ 1 day, > 0 | "Today" | `text-alert-600 font-medium` |
| ≤ 0 (expired) | "Expired" | `text-neutral-400` |

> **Color-independent**: The "Today" state uses `text-alert-600` + the word "Today" (not just color). The "Expired" state uses the word "Expired" + the `expired` status chip. No color-only signal.

### 2.7 Pixel Specs — Row Action Buttons

| Button | Spec |
|---|---|
| Resend | `inline-flex items-center gap-1 text-xs font-medium text-brand-700 hover:text-brand-800 hover:bg-brand-50 rounded-md px-2 py-1 focus-visible:ring-2 focus-visible:ring-brand-500` — `ArrowPathIcon` `w-3.5 h-3.5` + "Resend" |
| Revoke | `inline-flex items-center gap-1 text-xs font-medium text-fault-600 hover:text-fault-700 hover:bg-fault-50 rounded-md px-2 py-1 focus-visible:ring-2 focus-visible:ring-fault-500` — `TrashIcon` `w-3.5 h-3.5` + "Revoke" |
| Target size | Both buttons: padded to min 24×24px (`px-2 py-1` + icon = ~28px height) |

### 2.8 Revoke Confirm Modal

A confirm step is required before revoking (destructive action). This is a small modal mirroring the `CharterUpgradeModal` focus-trap pattern.

```
┌──────────────────────────────────────────┐  max-w-sm (384px)
│  [ExclamationTriangleIcon]  Revoke invite │
│                                            │
│  Are you sure you want to revoke the      │
│  invitation to jane@acme.example.com? They'll     │
│  no longer be able to accept it.           │
│                                            │
│              [Cancel]  [Revoke invite]     │
└──────────────────────────────────────────┘
```

| Element | Spec |
|---|---|
| Overlay | `fixed inset-0 bg-neutral-900/50 z-50 flex items-start justify-center` |
| Panel | `bg-white rounded-lg shadow-xl max-w-sm w-full mx-auto mt-16 p-6` |
| Warning icon | `ExclamationTriangleIcon` `w-6 h-6 text-fault-600` |
| Title | `text-h2 font-semibold text-neutral-900` — "Revoke invite" |
| Body | `text-sm text-neutral-600 mt-2` — "Are you sure you want to revoke the invitation to {email}? They'll no longer be able to accept it." |
| Cancel | `border border-neutral-300 text-neutral-700 rounded-md px-4 py-2.5 min-h-11 text-sm font-medium hover:bg-neutral-50 focus-visible:ring-2 focus-visible:ring-brand-500` |
| Confirm (destructive) | `bg-fault-600 text-white rounded-md px-4 py-2.5 min-h-11 text-sm font-medium hover:bg-fault-700 focus-visible:ring-2 focus-visible:ring-fault-500 disabled:bg-neutral-300 disabled:cursor-not-allowed inline-flex items-center justify-center` |
| In-flight | Confirm button disabled + `ArrowPathIcon` `w-4 h-4 mr-2 animate-spin motion-reduce:hidden` + "Revoking…" |
| Focus trap | Same pattern as `CharterUpgradeModal` (§1.11). Focus moves to Cancel (safe default) on open. |
| Escape | Closes modal (suppressed during in-flight). |
| Overlay click | Closes modal (suppressed during in-flight). |

### 2.9 State Coverage — Four Data States

| State | Visual |
|---|---|
| **Loading (initial)** | Skeleton: 3 placeholder rows matching the table layout. Each row: `animate-pulse` bars — email column `w-48 h-4 bg-neutral-200 rounded`, role `w-20 h-5 bg-neutral-200 rounded-full`, sent `w-16 h-4 bg-neutral-200 rounded`, expires `w-16 h-4 bg-neutral-200 rounded`, status `w-20 h-5 bg-neutral-200 rounded-full`. Header row visible (static). `data-testid="pending-invites-skeleton"`. |
| **Error** | `<ErrorState>` from `@pilot/ui/states` — "Could not load pending invites." with a "Try again" button that re-fetches. Rendered inside the section container (below the header). |
| **Empty** | `<EmptyState>` from `@pilot/ui/states` — "No pending invites" with subtitle "Invite team members and they'll appear here until they accept." No CTA button (the invite button is already in the page header). |
| **Populated** | Table with rows per §2.4. |

### 2.10 Interaction States — Row Action Buttons

**Resend button:**
| State | Spec |
|---|---|
| Default | `text-brand-700` |
| Hover | `hover:text-brand-800 hover:bg-brand-50` |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-brand-500` |
| Active | `active:bg-brand-100` |
| In-flight | `opacity-50 pointer-events-none` + `ArrowPathIcon` spinner `w-3.5 h-3.5 animate-spin motion-reduce:hidden` |
| Disabled (accepted/revoked) | Hidden — Resend only shows for `pending` and `expired` statuses |

**Revoke button:**
| State | Spec |
|---|---|
| Default | `text-fault-600` |
| Hover | `hover:text-fault-700 hover:bg-fault-50` |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-fault-500` |
| Active | `active:bg-fault-100` |
| In-flight | `opacity-50 pointer-events-none` |
| Disabled (accepted) | Hidden — Revoke only shows for `pending` and `expired` statuses |

### 2.11 Optimistic UI Behavior

**Resend (optimistic):**
1. On click, the row's Resend button shows spinner immediately (no network wait).
2. The `expires_at` cell updates optimistically to "7 days" (the new window).
3. The status chip stays `pending`.
4. On success (200): the `team-invites` query is invalidated → refetch confirms the new `expires_at`.
5. On 409 `invite_already_accepted`: the `team-invites` + `team-users` queries are invalidated (409-and-refresh) → the invite disappears from pending, the user appears in members. A `NotificationBanner` (severity `info`) shows "This invite was already accepted — {email} is now in your team list."
6. On 409 `invite_revoked`: query invalidated → row shows `revoked` status. `NotificationBanner` (severity `info`) shows "This invite was already revoked."
7. On network error: `NotificationBanner` (severity `error`) shows "Could not resend invite. Please try again." Row reverts to pre-optimistic state.

**Revoke (optimistic):**
1. On confirm, the Revoke button shows spinner.
2. The row's status chip optimistically changes to `revoked`.
3. On success (200): `team-invites` query invalidated → refetch confirms.
4. On 409 `invite_already_accepted`: `team-invites` + `team-users` invalidated → invite disappears from pending, user appears in members. `NotificationBanner` (severity `info`).
5. On network error: `NotificationBanner` (severity `error`). Row reverts.

### 2.12 Animation Spec

| Element | Transition | Reduced-motion |
|---|---|---|
| Skeleton pulse | `animation: pulse 1.5s ease-in-out infinite` | `motion-reduce:animate-none` (skeleton bars become static `bg-neutral-200`) |
| Row hover | `transition: background-color 100ms ease-in-out` | No transition |
| Status chip change (optimistic) | `transition: background-color 150ms ease-in-out, color 150ms ease-in-out` | No transition |
| Confirm modal open/close | `motion-safe:transition-opacity` on overlay | No transition |

### 2.13 Accessibility Notes — Pending Invites Section

- **Color-independent status**: Every status chip has an icon + text label. The expiry countdown uses words ("4 days", "Today", "Expired"), not color alone.
- **Target sizes**: Resend/Revoke buttons are `px-2 py-1` + icon = ~28×28px (≥ 24×24px). The confirm modal buttons are `min-h-11` (44px).
- **Focus-visible**: All buttons have `focus-visible:ring-2`. The table rows are not focusable (actions are in cells).
- **Screen reader**: The table uses semantic `<table>`, `<thead>`, `<tbody>`, `<th>` (with `scope="col"`), `<td>`. Status chips have `aria-label` combining icon + text (e.g., "Status: Pending").
- **Revoke confirm modal**: `role="dialog"`, `aria-modal="true"`, `aria-labelledby` pointing to "Revoke invite" heading. Focus trap + Escape + overlay click (all suppressed during in-flight). Focus returns to the Revoke trigger button on close.
- **Skeleton**: `aria-busy="true"` on the table body during loading. `aria-live="polite"` on the section container so screen readers announce when data loads.
- **Reduced motion**: Skeleton pulse disabled, all transitions disabled.

---

## 3. Invite Landing Page

### 3.1 Surface Overview

| Attribute | Value |
|---|---|
| **Component** | `InviteLandingPage` (client component) + `app/invite/[token]/page.tsx` (server component — metadata + token passthrough) |
| **Route** | `/invite/[token]` — **new public route**, sibling to `q/[token]` and `i/[token]` |
| **RBAC** | **None** — public, unauthenticated. MUST NEVER import `useAuth()`, `RequireAuth`, or `RoleGate` (mirrors `i/[token]/page.tsx` RULE 1). |
| **API** | `GET /api/v1/invites/{token}` (D5) — public, uniform 404 for all failure modes |
| **Pattern** | Public-page state machine (mirrors `PublicInvoicePage.tsx` lines 38–43). Uses raw `fetch` (not `apiClient`) per Rule 35 exception — no auth context. |

### 3.2 Route File — `app/invite/[token]/page.tsx`

Mirrors the `i/[token]` and `q/[token]` server-component pattern:

- `generateMetadata()`: fetches `GET /api/v1/invites/{token}` with `next: { revalidate: 0 }`. On success: `title: "Join {tenant_name} on Pilot for Trades"`, `robots: "noindex, nofollow"`. On any failure: `title: "Pilot for Trades Invite"`, `robots: "noindex, nofollow"`.
- Default export: `async function InvitePage({ params })` → `const { token } = await params; return <InviteLandingPage token={token} />`
- **CRITICAL**: No auth imports. Lives outside the `(authed)` route group.

### 3.3 Layout — Valid State

```
┌──────────────────────────────────────────────────────────┐  min-h-screen bg-neutral-50
│  [Pilot Logo]                                             │  header (same as signup layout)
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │  max-w-lg
│  │                                                       │ │  bg-white rounded-xl
│  │            [EnvelopeIcon]                             │ │  border-neutral-200
│  │                                                       │ │  shadow-sm p-8
│  │       Join {tenant_name}                               │ │  text-center
│  │       on Pilot for Trades                              │ │  text-h1 font-bold
│  │                                                       │ │
│  │  ─────────────────────────────────────────────────── │ │  border-b border-neutral-100
│  │                                                       │ │
│  │  You've been invited as:                               │ │  text-sm text-neutral-500
│  │  [ShieldCheckIcon] Field Technician                    │ │  role display
│  │                                                       │ │
│  │  Invited email:                                        │ │
│  │  jane@acme.example.com                                         │ │  text-sm text-neutral-900
│  │                                                       │ │
│  │  Expires: Sep 10, 2026                                 │ │  text-sm text-neutral-500
│  │                                                       │ │
│  │  ┌─────────────────────────────────────────────────┐ │ │
│  │  │  Accept Invite & Sign Up           [ArrowRight] │ │ │  CTA button
│  │  └─────────────────────────────────────────────────┘ │ │
│  │                                                       │ │
│  │  Already have an account? Sign in                     │ │  text-xs text-neutral-500
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  © 2026 Pilot for Trades · Privacy · Terms                │  PoweredByPilotFooter
└──────────────────────────────────────────────────────────┘
```

### 3.4 Pixel Specs — Valid State

| Element | Spec |
|---|---|
| Page container | `min-h-screen bg-neutral-50 flex flex-col` |
| Header | `w-full px-6 py-4 flex items-center justify-center border-b border-neutral-100 bg-white` — Pilot logo (reuse the SVG from `signup/layout.tsx` lines 33–48) |
| Main | `flex-1 flex flex-col items-center justify-start px-4 py-8 sm:py-12` |
| Card | `w-full max-w-lg bg-white rounded-xl border border-neutral-200 shadow-sm p-8 flex flex-col items-center text-center` |
| Envelope icon | `EnvelopeIcon` `w-12 h-12 text-brand-600` (centered, above title) |
| Title | `text-h1 font-bold text-neutral-900` — "Join {tenant_name}" |
| Subtitle | `text-h1 font-bold text-neutral-900` (same line, or below) — "on Pilot for Trades" |
| Divider | `w-full border-b border-neutral-100 my-6` |
| Role label | `text-sm text-neutral-500` — "You've been invited as:" |
| Role display | `flex items-center justify-center gap-2 mt-1` — role icon (`w-5 h-5 text-brand-600`) + `text-sm font-medium text-neutral-900` (role display name) |
| Invited email label | `text-sm text-neutral-500 mt-4` — "Invited email:" |
| Invited email value | `text-sm text-neutral-900` — the email from D5 response |
| Expiry label | `text-sm text-neutral-500 mt-2` — "Expires:" |
| Expiry value | `text-sm text-neutral-500` — formatted date `MMM d, yyyy` |
| CTA button | `w-full mt-6 bg-brand-600 text-white rounded-lg py-3.5 px-6 text-sm font-semibold hover:bg-brand-700 focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2 inline-flex items-center justify-center gap-2` — "Accept Invite & Sign Up" + `ArrowRightIcon` `w-4 h-4` |
| Sign in link | `text-xs text-neutral-500 mt-4` — "Already have an account? " + `<a href="/login" class="text-brand-600 hover:text-brand-800 underline">Sign in</a>` |
| Footer | `PoweredByPilotFooter` from `features/public-quote` (reused) |

**Role display name + icon mapping** (from D5 `role_code`):

| `role_code` | Display name | Icon |
|---|---|---|
| `owner` | Owner | `ShieldCheckIcon` |
| `office_staff` | Office Staff | `Cog6ToothIcon` |
| `technician` | Field Technician | `WrenchScrewdriverIcon` |
| `accountant` | Accountant | `CalculatorIcon` |

> **Note**: The display name for `technician` is "Field Technician" (the `tenant_user_role.name` from the DB, per design §F.4). The others use the `tenant_user_role.name` directly.

### 3.5 CTA Handoff — SignUp Flow

The "Accept Invite & Sign Up" button navigates to:

```
/signup/account?email={encodeURIComponent(email)}&invite_token={token}
```

- The `email` query param pre-fills the email field on `signup/account/page.tsx` (engineer adds `searchParams.get("email")` to `defaultValues.owner_email` and makes the field `readOnly` when pre-filled from an invite).
- The `invite_token` query param is stored in `sessionStorage` (key: `invite_token`) by the account page on mount, so the Post-Confirmation Lambda (Path 2) can look up the pending invite by token hash after Cognito email verification.
- The existing Cognito `SignUp` flow proceeds normally (password → verify email → Lambda Path 2 attach → login → dashboard).
- **The landing page does NOT call Cognito itself** — it only hands off to the signup wizard. ADR-0011: the backend never takes Cognito admin IAM; the invitee self-registers.

### 3.6 Layout — Invalid/Expired/Accepted/Revoked State

Per design §D5: the backend returns a **uniform 404** for every failure mode (unknown token, expired, accepted, revoked). The landing page renders **ONE neutral state** — no distinguishable failure modes (no enumeration oracle).

```
┌──────────────────────────────────────────────────────────┐  min-h-screen bg-neutral-50
│  [Pilot Logo]                                             │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │  max-w-md
│  │                                                       │ │  bg-white rounded-xl
│  │            [ExclamationTriangleIcon]                   │ │  border-neutral-200
│  │                                                       │ │  shadow-sm p-8
│  │       This link is no longer valid                     │ │  text-center
│  │                                                       │ │
│  │  This invitation may have expired, already been       │ │  text-sm text-neutral-600
│  │  accepted, or been revoked. Please contact the         │ │
│  │  business owner who invited you and ask them to        │ │
│  │  send a new invitation.                                │ │
│  │                                                       │ │
│  │  ┌─────────────────────────────────────────────────┐ │ │
│  │  │  Go to Pilot for Trades                           │ │ │  secondary link
│  │  └─────────────────────────────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  © 2026 Pilot for Trades · Privacy · Terms                │
└──────────────────────────────────────────────────────────┘
```

### 3.7 Pixel Specs — Invalid State

| Element | Spec |
|---|---|
| Card | `w-full max-w-md bg-white rounded-xl border border-neutral-200 shadow-sm p-8 flex flex-col items-center text-center` |
| Warning icon | `ExclamationTriangleIcon` `w-12 h-12 text-neutral-400` (centered) |
| Title | `text-h1 font-bold text-neutral-900` — "This link is no longer valid" |
| Body | `text-sm text-neutral-600 mt-2` — "This invitation may have expired, already been accepted, or been revoked. Please contact the business owner who invited you and ask them to send a new invitation." |
| Link | `mt-6 inline-flex items-center justify-center border border-neutral-300 text-neutral-700 rounded-lg px-4 py-2.5 text-sm font-medium hover:bg-neutral-50 focus-visible:ring-2 focus-visible:ring-brand-500` — "Go to Pilot for Trades" → `href="/"` |

### 3.8 State Coverage — Full State Machine

| State | Phase | Visual |
|---|---|---|
| **Loading** | `loading` | Centered spinner: `h-8 w-8 rounded-full border-2 border-neutral-300 border-t-neutral-700 animate-spin` + `text-sm text-neutral-500` "Loading invite…" |
| **Valid** | `ready` | Card per §3.3/§3.4 with tenant name, email, role, expiry, CTA |
| **Invalid (404)** | `error-invalid` | Card per §3.6/§3.7 — uniform neutral state |
| **Network error** | `error-generic` | Card: `ExclamationTriangleIcon` + "Something went wrong" + `text-sm text-neutral-500` "Could not load this invitation. Check your connection and try again." + "Try again" button (`border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50`) that re-fetches. |

> **No `error-expired` phase** — unlike `PublicInvoicePage` (which has a 410 expired state with tenant contact info), the invite endpoint returns a uniform 404. There is no distinguishable expired state. This is by design (§D5: no enumeration oracle).

### 3.9 Interaction States — CTA Button

| State | Spec |
|---|---|
| Default | `bg-brand-600 text-white` |
| Hover | `hover:bg-brand-700` |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2` |
| Active | `active:bg-brand-800` |
| Disabled | N/A (never disabled — it's a navigation link) |

### 3.10 Animation Spec

| Element | Transition | Reduced-motion |
|---|---|---|
| Loading spinner | `animation: spin 600ms linear infinite` | `motion-reduce:animate-none` (spinner hidden; text "Loading invite…" remains) |
| CTA hover | `transition: background-color 150ms ease-in-out` | No transition |
| Card appear | None (instant render) | N/A |

### 3.11 Accessibility Notes — Invite Landing Page

- **No auth imports**: The route file and `InviteLandingPage` MUST NEVER import `useAuth()`, `RequireAuth`, `RoleGate`, or any auth hook (mirrors `i/[token]` RULE 1). The token in the URL is the only authentication.
- **Color-independent status**: The invalid state uses `ExclamationTriangleIcon` + text "This link is no longer valid" + explanatory body — not color alone. The valid state uses `EnvelopeIcon` + text.
- **Target sizes**: CTA button `py-3.5 px-6` = ~48px height (≥ 44px). "Go to Pilot for Trades" link `px-4 py-2.5` = ~40px (≥ 24px). "Sign in" link is inline text (keyboard-focusable, `focus-visible:underline`).
- **Focus-visible**: CTA button has `focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2`. Links have `focus-visible:underline`.
- **Semantic HTML**: The card uses `<main>` for the content area. The title is `<h1>`. The role/email/expiry are `<dl>` / `<dt>` / `<dd>` (description list — semantic for label/value pairs).
- **`noindex, nofollow`**: Set in `generateMetadata()` — invite links are private, must not be indexed.
- **Reduced motion**: Spinner hidden via `motion-reduce:animate-none`. All transitions disabled.
- **Keyboard navigation**: The CTA is a link (`<a>` or `next/link`), focusable via Tab. The "Sign in" link is also Tab-focusable. No focus trap needed (full page, not a modal).

---

## 4. Component Manifest

Reconciled against design §I. Every file from §I is accounted for. Additions/deviations are flagged explicitly.

| # | Component / module | Destination path | Action | Reconciliation with §I |
|---|---|---|---|---|
| 1 | `InviteMemberDialog` | `apps/web/src/features/settings/components/InviteMemberDialog.tsx` | **New** (replaces placeholder `InviteDialog` in `TeamSettingsPage.tsx`) | §I.1 — ✅ match. Replaces the P0 "coming soon" placeholder (Rule 9.4). |
| 2 | `PendingInvitesSection` | `apps/web/src/features/settings/components/PendingInvitesSection.tsx` | **New** | §I.2 — ✅ match. Includes row actions (Resend + Revoke) and the Revoke confirm modal (inline sub-component `RevokeConfirmModal`). |
| 3 | `RevokeConfirmModal` | `apps/web/src/features/settings/components/RevokeConfirmModal.tsx` | **New** | **Addition** (not separately listed in §I.2, but implied by "Revoke needs a confirm step"). Extracted as its own component for reusability and testability. **Flagged deviation**: §I.2 bundles the confirm modal into `PendingInvitesSection`; this spec separates it for cleaner focus-trap logic. |
| 4 | `InviteLandingPage` | `apps/web/src/features/users/components/InviteLandingPage.tsx` | **New** | §I.3 — ✅ match. Client component with the state machine. Placed in `features/users/` per §I.3 (design says `features/users/components/InviteLanding*.tsx`). |
| 5 | Invite landing route | `apps/web/src/app/invite/[token]/page.tsx` | **New** | §I.3 — ✅ match. Server component (metadata + token passthrough), sibling to `q/[token]` and `i/[token]`. |
| 6 | `useTeamInvites` | `apps/web/src/features/settings/hooks/useTeamInvites.ts` | **New** | §I.4 — ✅ match. Query hook for D2 (`GET /api/v1/users/invites`). Query key: `["team-invites"]`. |
| 7 | `useCreateInvite` | `apps/web/src/features/settings/hooks/useCreateInvite.ts` | **New** | §I.4 — ✅ match. Mutation hook for D1 (`POST /api/v1/users/invites`). Sends `Idempotency-Key` header. On success: invalidates `["team-invites"]`. On 409: returns structured error code for the dialog to branch. |
| 8 | `useResendInvite` | `apps/web/src/features/settings/hooks/useResendInvite.ts` | **New** | §I.4 — ✅ match. Mutation hook for D3 (`POST /api/v1/users/invites/{id}/resend`). Sends `Idempotency-Key`. On success: invalidates `["team-invites"]`. On 409: invalidates `["team-invites"]` + `["team-users"]` (409-and-refresh). |
| 9 | `useRevokeInvite` | `apps/web/src/features/settings/hooks/useRevokeInvite.ts` | **New** | §I.4 — ✅ match. Mutation hook for D4 (`POST /api/v1/users/invites/{id}/revoke`). Sends `Idempotency-Key`. On success: invalidates `["team-invites"]`. On 409: invalidates `["team-invites"]` + `["team-users"]`. |
| 10 | `useInviteToken` | `apps/web/src/features/users/hooks/useInviteToken.ts` | **New** | §I.6 — ✅ match. Public token lookup hook for D5 (`GET /api/v1/invites/{token}`). Uses raw `fetch` (not `apiClient`) per Rule 35 exception — no auth context. Placed in `features/users/hooks/` (not `features/settings/`) since it's a public-route hook. |
| 11 | `TeamSettingsPage` (modified) | `apps/web/src/features/settings/components/TeamSettingsPage.tsx` | **Modify** | Replaces placeholder `InviteDialog` with `InviteMemberDialog`. Adds `PendingInvitesSection` below the members table. Changes `useRequiresPermission("settings.manage")` → `useRequiresPermission("users.manage")` on the invite button. Fixes `RoleBadge` token (`success` → `blue`). |
| 12 | RBAC registry (modified) | `packages/ui/src/role-gate/permissions.ts` | **Modify** | §I.5 — Adds `"users.manage"` to `PermissionKey` union + `owner` set only. **Note**: The ADR-0010 full rename (`tech`→`technician`, `operator`→`accountant`) is Part B implementation scope — this spec's visual design is unaffected (role select uses BE codes). |
| 13 | `PilotRole` type (modified) | `packages/ui/src/auth/types.ts` | **Modify** | §I.5 — ADR-0010 rename. **Note**: This is implementation scope; the spec's visual design uses BE vocabulary codes directly and is not blocked by this. |
| 14 | `help-anchor/types.ts` (modified) | `packages/ui/src/help-anchor/types.ts` | **Modify** | §I.5 — Update the duplicated `PilotRole` union at line 36. |

**No orphans**: Every component in §I is accounted for. The only addition is `RevokeConfirmModal` (#3), which is a sub-component of `PendingInvitesSection` extracted for focus-trap isolation — flagged as a deviation.

**No new `packages/ui` components**: All new components are feature-local (`apps/web/src/features/...`). No shared component is promoted to the barrel. The existing `EmptyState`, `LoadingState`, `ErrorState`, `RoleGate`, `useRequiresPermission`, `NotificationBanner`, `PendingBadge` are composed, not duplicated.

---

## 5. Implementation Notes

### 5.1 Hook Names and Query Keys

| Hook | File | Query key | API endpoint | `retry` |
|---|---|---|---|---|
| `useTeamInvites` | `features/settings/hooks/useTeamInvites.ts` | `["team-invites"]` | `GET /api/v1/users/invites` (D2) | `false` |
| `useCreateInvite` | `features/settings/hooks/useCreateInvite.ts` | mutation (invalidates `["team-invites"]`) | `POST /api/v1/users/invites` (D1) | `false` |
| `useResendInvite` | `features/settings/hooks/useResendInvite.ts` | mutation (invalidates `["team-invites"]`, `["team-users"]` on 409) | `POST /api/v1/users/invites/{id}/resend` (D3) | `false` |
| `useRevokeInvite` | `features/settings/hooks/useRevokeInvite.ts` | mutation (invalidates `["team-invites"]`, `["team-users"]` on 409) | `POST /api/v1/users/invites/{id}/revoke` (D4) | `false` |
| `useInviteToken` | `features/users/hooks/useInviteToken.ts` | `["invite-token", token]` | `GET /api/v1/invites/{token}` (D5, public) | `false` |

All TanStack Query hooks use `retry: false` per design §I.4. The `useInviteToken` hook uses raw `fetch` (not `apiClient`) because it's a public endpoint with no auth context — mirrors `PublicInvoicePage.tsx` line 55.

### 5.2 Idempotency-Key on Mutations

All three mutation hooks (`useCreateInvite`, `useResendInvite`, `useRevokeInvite`) send an `Idempotency-Key` header via the `apiClient.post()` config:

```typescript
apiClient.post("/api/v1/users/invites", { email, role_code }, {
  headers: { "Idempotency-Key": crypto.randomUUID() }
});
```

This mirrors the pattern in `InvoicePaymentModal.tsx` line 97. The key is generated per mutation attempt (not stable across retries) — the backend's 24h TTL store + `uq_tenant_user_invite_tenant_id_email` natural-key fallback handles dedup (design §D / §E).

### 5.3 RFC 7807 Error Handling

The `useCreateInvite` hook catches errors via `getApiProblem(err)` from `@pilot/shared-api`. The `code` field on the `ApiProblem` carries the machine-readable error code:

| HTTP | `code` | Dialog behavior |
|---|---|---|
| 422 | (validation) | Inline email field error (`setError("email", ...)`) |
| 409 | `invite_pending_exists` | Alert banner with "Resend invite" link (uses `invite_id` from response detail) |
| 409 | `invite_user_exists` | Neutral banner explainer |
| 400 | `invalid_role` | `NotificationBanner` error (shouldn't happen — select only offers valid roles) |
| 0 | (network) | `NotificationBanner` error "Could not send invite. Check your connection." |

The `useResendInvite` / `useRevokeInvite` hooks handle:
| HTTP | `code` | Behavior |
|---|---|---|
| 409 | `invite_already_accepted` | Invalidate `["team-invites"]` + `["team-users"]` → invite disappears, user appears in members. `NotificationBanner` info. |
| 409 | `invite_revoked` (resend only) | Invalidate `["team-invites"]` → row shows `revoked`. `NotificationBanner` info. |
| 404 | `invite_not_found` | Invalidate `["team-invites"]` → row disappears. `NotificationBanner` info "This invite no longer exists." |

### 5.4 `users.manage` Permission Key

**New permission key** added to `permissions.ts`:

```typescript
// TEAM-INVITE-1 additions — invite management
| "users.manage" // Invite, resend, revoke team members — owner only
```

Added to the `owner` set only. The invite button, Resend, and Revoke actions are gated by `<RoleGate permission="users.manage">` (hide-not-disable). Non-owners never see these controls.

The existing `useRequiresPermission("settings.manage")` on the `TeamContent` page wrapper stays (it gates the whole page view). The invite button specifically uses `useRequiresPermission("users.manage")` — a stricter subset (owner only).

### 5.5 Invite Landing Page — SignUp Handoff

The CTA navigates to `/signup/account?email={email}&invite_token={token}`:

- **`email` param**: The account page reads `searchParams.get("email")` and pre-fills `defaultValues.owner_email`. The field is made `readOnly` when pre-filled from an invite (the invitee's email is fixed by the invitation).
- **`invite_token` param**: Stored in `sessionStorage` under key `"invite_token"` by the account page on mount. The Post-Confirmation Lambda (Path 2) looks up the pending invite by `sha256(token)` = `token_hash` after Cognito email verification. The Lambda's `_find_pending_invite` function already handles this (design §F.3).
- **No Cognito call from the landing page**: The landing page only navigates. The existing Cognito `SignUp` flow in `useCognitoSignUp.ts` handles account creation. ADR-0011: self-serve `SignUp`, never `AdminCreateUser`.

### 5.6 `TeamSettingsPage` Modifications

The existing `TeamSettingsPage.tsx` is modified:

1. **Remove** the placeholder `InviteDialog` function (lines 46–67).
2. **Import** `InviteMemberDialog` and render it when `showInviteDialog` is true.
3. **Import** `PendingInvitesSection` and render it below the members table (inside `TeamContent`, after the closing `</div>` of the table wrapper at line 173).
4. **Change** the invite button's permission gate from `useRequiresPermission("settings.manage")` to `useRequiresPermission("users.manage")`.
5. **Fix** `RoleBadge` token: `bg-success-100 text-success-700` → `bg-blue-100 text-blue-700` for technician (§1.12).
6. **Add** `UserPlusIcon` to the invite button (left of text): `inline-flex items-center gap-2`.

### 5.7 MSW Handlers

New MSW handlers for D1–D5 should be added to the existing MSW setup. The hooks' `__tests__` directories should include:
- `useTeamInvites.test.ts` — query shape + query-key factory
- `useCreateInvite.test.ts` — Idempotency-Key header + 409 code branching
- `useResendInvite.test.ts` — Idempotency-Key + 409 `invite_already_accepted` invalidation
- `useRevokeInvite.test.ts` — Idempotency-Key + 409 invalidation
- `useInviteToken.test.ts` — public fetch + uniform 404 handling

### 5.8 Responsive Notes (1024px / 768px)

| Surface | 1280px (primary) | 1024px | 768px |
|---|---|---|---|
| Invite dialog | `max-w-lg` (512px) centered | Same (modal is overlay, not constrained by sidebar) | Same |
| Pending invites table | Full width within `max-w-4xl` | Table scrolls horizontally if needed (`overflow-x-auto` on wrapper) | Table scrolls horizontally; row actions wrap to second line |
| Invite landing | `max-w-lg` card centered | Same | `max-w-md` card, `px-4` |

> Mobile app UI is out of scope (React Native → `pilot-voice-ui-designer`). These are tablet/narrow-desktop reflow notes only.

### 5.9 Dev Token for Landing Page Testing

Per design §B.3 (Layer 2 seed data), the dev test tenant has a pending invite with raw token `dev-invite-token-0001` (token_hash = `sha256('dev-invite-token-0001')`). The landing page can be tested at `/invite/dev-invite-token-0001` in local dev.

---

## 6. Accessibility Notes (Consolidated — WCAG 2.2 AA)

### 6.1 Color-Independent Status (WCAG 1.4.1)

- Every status chip (pending/expired/accepted/revoked) pairs a color token with an icon + text label.
- 409 error banners use `ExclamationCircleIcon` + text, not color alone.
- The expiry countdown uses words ("4 days", "Today", "Expired"), not color.
- The invalid landing state uses `ExclamationTriangleIcon` + text "This link is no longer valid".

### 6.2 Target Sizes (WCAG 2.5.8)

- All modal buttons: `min-h-11` (44px) — primary actions.
- Close (X) button: padded `p-2.5` = 40×40px.
- Resend/Revoke row buttons: `px-2 py-1` + icon = ~28×28px (≥ 24×24px).
- Role radio cards: min-height 44px.
- CTA on landing page: `py-3.5` = ~48px.

### 6.3 Focus-Visible Rings (WCAG 2.4.7)

- All interactive elements use `focus-visible:ring-2 focus-visible:ring-brand-500` (or `ring-fault-500` for destructive).
- `focus-visible`, not `focus` — keyboard users get the ring, mouse users don't see a persistent ring on click.

### 6.4 Focus Not Obscured (WCAG 2.4.11)

- Modals are `z-50`, above the `h-12` sticky header (`z-30`). No `NotificationBanner` portal competes (in-modal banners are inline).
- The pending invites section is below the members table — no sticky element obscures focus when scrolling to it. `scroll-margin-top: 4rem` on the section container to account for the sticky header if anchored.

### 6.5 Modal Focus Trap + Return (WCAG 2.4.3, 2.4.11)

- Both `InviteMemberDialog` and `RevokeConfirmModal` implement the focus-trap pattern from `CharterUpgradeModal`:
  - On open: focus moves to the first focusable element (email input / Cancel button).
  - Tab cycles within the modal (first ↔ last).
  - Escape closes (suppressed during in-flight).
  - Overlay click closes (suppressed during in-flight).
  - On close: focus returns to the trigger element (`triggerRef`).

### 6.6 Visible Labels (WCAG 3.3.2)

- Every form field has a visible `<label>` above it (not placeholder-as-label).
- Error text is `text-fault-600` + `role="alert"` + linked via `aria-describedby`.

### 6.7 Reduced Motion (WCAG 2.3.3)

- All transitions use `motion-safe:` prefix.
- Spinner uses `motion-reduce:hidden` (text label remains).
- Skeleton pulse uses `motion-reduce:animate-none` (bars become static).

### 6.8 Accessible Authentication (WCAG 3.3.8)

- The invite landing page CTA hands off to the existing Cognito `SignUp` flow, which allows paste in all fields and requires no memorization puzzles. The email field is pre-filled (not re-asked) — WCAG 3.3.7 (Redundant Entry).

---

## 7. Handoff Gate

**This spec is ready for Tom's review. Implementation starts only after approval.**

The Architect then authors the Part B React prompt (`batch-team-invite-1-react-engr-prompt.md`) against this approved spec, per Rule 1.5.

**Spec completeness checklist:**
- [x] Surface overview (3 surfaces, routes, RBAC)
- [x] Pixel specs (dimensions, padding, gap, border-radius for every component)
- [x] Token-only colors (zero hex codes — `RoleBadge` `success` token flagged + corrected)
- [x] Icon inventory (exact Heroicons 2.0 names)
- [x] State coverage (loading/empty/error/populated for all 3 surfaces + all API-driven 409/422 states)
- [x] Interaction spec (all 5 states on every interactive element)
- [x] Animation spec (transitions + reduced-motion fallbacks)
- [x] Component manifest (reconciled against §I, no orphans, 1 flagged deviation)
- [x] Implementation notes (hooks, Idempotency-Key, RFC 7807 codes, `users.manage` key, SignUp handoff, dev token)
- [x] Accessibility notes (WCAG 2.2 AA: color-independent, target sizes, focus-visible, focus trap, visible labels, reduced motion)
- [x] Handoff gate stated explicitly
