# MFA-WIRE-1 — Web MFA Method Cards + Remove Flow UI Design Spec

**Batch**: MFA-WIRE-1 (Part B prerequisite — Tom-approved before the React Engineer prompt is authored)
**Mode**: Pilot Web UI Designer (`pilot-web-ui-designer`)
**Source design doc**: `batch-mfa-wire-1-design.md` v1.2 ✅ APPROVED 2026-08-16 — §C step 3, §D.3/D.4, §F.3, §G-Q1/Q2/Q7, §H, §I, DoD
**Source prompt**: `batch-mfa-wire-1-web-ui-designer-prompt.md`
**Platform**: Web only (`apps/web`) — internal authenticated settings surfaces
**Status**: Draft for Tom's review

---

## 1. Surface Overview

### 1.1 Surface 1 — Method cards + Remove flow

| | |
|---|---|
| Route | `/settings/my-account/security/mfa` |
| File | `frontend/apps/web/src/app/(authed)/settings/my-account/security/mfa/page.tsx` |
| Shell | `SettingsShell` — app sidebar (256px) + settings sidebar (224px) + content (`max-w-2xl`, `px-6 py-6`) |
| RBAC | Self-service — every authenticated user manages their own MFA. **No `<RoleGate>`** on cards or the Add button. Permissions in play: `mfa.enroll_self`, `mfa.reset_self` (already enforced backend-side on the routes). |
| Data source | `GET /api/v1/users/me/mfa-status` — consumes the **new additive `methods[]` array** (design §D.4). The legacy `enrolled_methods: string[]` is kept for mobile backward-compat but is **not** the source for the card list. |
| Mutation | `DELETE /api/v1/users/me/mfa/methods/{method_id}` — requires `X-Cognito-Access-Token` header (design §D.3). |
| §16 patterns consumed | **Optimistic UI** (§16.8) for Remove — optimistic remove + rollback on non-204, composed via `<PendingBadge>` from `@pilot/ui`. **409-and-refresh** for the last-method guard — `<NotificationBanner>` + `query.invalidate`. |

**What changes**: the raw text block `Enrolled: totp, sms` (current `page.tsx`) is replaced by a **method-card list** rendering one card per entry in `methods[]`. The Add button is hidden (not disabled) when both `totp` and `sms` are enrolled. `ALL_MFA_METHODS` drops `"email"` → `["totp","sms"]`. The wizard receives `allowedPaths={["totp","sms"]}`.

### 1.2 Surface 2 — Force-flow enrollment page

| | |
|---|---|
| Route | `/settings/my-account/security/mfa/enroll` |
| File | `frontend/apps/web/src/app/(authed)/settings/my-account/security/mfa/enroll/page.tsx` |
| Shell | Full-page (no settings sidebar) — `min-h-screen bg-neutral-50`, centered `max-w-lg` |
| RBAC | Self-service; reached via FE-B2 auth-interceptor redirect (`?mfa_required=1&grace_days=N&return_to=…`) |
| What changes | `allowedPaths={["totp","sms"]}` prop added to the embedded `<MFAEnrollmentWizard>`. Force-flow context copy is added above the wizard. `forceFlow={true}` already removes Cancel (unchanged). |

### 1.3 Surface 3 — Wizard internal error states (copy + placement table)

The wizard steps themselves are **not visually redesigned** (interface LOCKED per FE-B12). The deliverable is a copy + presentation table for each §F.3 RFC 7807 error code, mapping it to inline field error vs. top-of-wizard banner per four-class severity. The React Engineer wires the backend's RFC 7807 `code` field to the correct copy/placement inside the existing wizard error slots (`MFAEnrollmentWizard.tsx` for the top-of-wizard error, `VerifyStep` for the inline verify error).

---

## 2. Pixel Specs

### 2.1 Page container (Surface 1) — unchanged from existing

| Property | Value |
|---|---|
| Container | `flex flex-col gap-6 max-w-2xl` (existing `page.tsx`) |
| Page padding | `px-6 py-6` (via SettingsShell) |
| H1 | `text-h2 font-semibold text-neutral-900` — "Two-factor authentication" (preserved from existing; not escalated to `text-h1` to avoid scope creep) |
| Subtitle | `mt-1 text-sm text-neutral-500` — "Add an extra layer of security to your account." |

### 2.2 Tenant-policy context banner (new — above the card list)

Rendered only when `tenant_policy_required === true` (and/or `grace_period_active === true`). Color is never the only signal — an icon + text label accompany the token background.

| Property | Value |
|---|---|
| Container | `rounded-md border px-4 py-3 flex items-start gap-3` |
| Tokens (grace active, >3 days) | `bg-alert-50 border-alert-200` |
| Tokens (grace active, 1–3 days) | `bg-alert-50 border-alert-200` (same; urgency conveyed by copy) |
| Tokens (grace active, 0 days / expired) | `bg-fault-50 border-fault-200` |
| Tokens (policy required, no grace) | `bg-alert-50 border-alert-200` |
| Icon | `ShieldExclamationIcon` (Heroicons outline, `w-5 h-5`, `text-alert-600` / `text-fault-600` when 0-day) |
| Text | `text-sm text-alert-700` / `text-fault-700` |
| Copy (policy required, no grace) | "Your organization requires multi-factor authentication. Add at least one method to keep your account secure." |
| Copy (grace active, N>3) | "Your organization requires MFA. You have **{N} days** left to enroll before access is restricted." |
| Copy (grace active, 1–3) | "Your organization requires MFA. **{N} days** left to enroll — add a method now." |
| Copy (grace expired, 0) | "MFA enrollment is required today to continue using Pilot." |
| `role` | `alert` |
| `data-testid` | `mfa-tenant-policy-banner` |

### 2.3 Method card (new)

One card per entry in `methods[]`. Cards stack vertically inside a `flex flex-col gap-3` list container (`data-testid="mfa-method-card-list"`).

| Property | Value |
|---|---|
| Card container | `rounded-lg border border-neutral-200 bg-white px-4 py-3 flex items-center gap-3` |
| Card width | full-width of the `max-w-2xl` content column |
| Card min-height | `min-h-[64px]` (ensures ≥44px hit area for the Remove action with padding) |
| Leading icon container | `flex-shrink-0 w-10 h-10 rounded-full bg-brand-50 flex items-center justify-center` |
| Leading icon (TOTP) | `ShieldCheckIcon` (Heroicons outline, `w-5 h-5`, `text-brand-600`) |
| Leading icon (SMS) | `DevicePhoneMobileIcon` (Heroicons outline, `w-5 h-5`, `text-brand-600`) |
| Label (primary line) | `text-sm font-medium text-neutral-900` — "Authenticator app" (TOTP) / "Text message" (SMS) |
| Secondary line | `text-xs text-neutral-500 mt-0.5` — SMS: `{destination_masked} · Enrolled {date}`; TOTP: `Enrolled {date}` |
| Date format | `MMM d, yyyy` via `Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' })` — e.g. "Enrolled Aug 17, 2026" |
| `last_used_at` | **Omitted from the card.** The field ships in the API contract (design §D.4) but is always `null` this batch (Cognito owns challenge telemetry). Showing "Never used" on every card adds noise without value. State this choice explicitly to the engineer — the field is reserved for a future batch that surfaces Cognito challenge telemetry. |
| Trailing Remove action | text button, `text-sm font-medium text-fault-600 hover:text-fault-700`, `px-2 py-2` (gives a 44×44px hit area with the text), `rounded-md`, `focus-visible:ring-2 focus-visible:ring-fault-500 focus-visible:ring-offset-2` |
| Remove icon | `TrashIcon` (Heroicons outline, `w-4 h-4`) inline before the label "Remove" — `flex items-center gap-1.5` |
| `data-testid` | `mfa-method-card-{method_type}` (e.g. `mfa-method-card-totp`); Remove button: `mfa-method-remove-{method_type}` |
| `aria-label` (Remove) | `Remove {method label} method` (e.g. "Remove Authenticator app method") |

### 2.4 Method card — optimistic pending state (§16.8)

When the user confirms Remove, the card immediately enters the pending state (optimistic remove is **not** a full disappearance — the card stays visible but dimmed + badged, so the user sees their action was received and can perceive rollback if it fails). On 204 the card is removed from the list. On non-204 the pending treatment is cleared and the card returns to default.

| Property | Value |
|---|---|
| Card container (pending) | adds `opacity-60` and `pointer-events-none` |
| Pending marker | `<PendingBadge>` from `@pilot/ui` — placed inline after the label, `ml-2` |
| Remove button (pending) | hidden (replaced by the badge) |
| `data-testid` | `mfa-method-card-{method_type}-pending` on the card container |
| `aria-busy` | `true` on the card container |

> **Rationale for "dim + badge" over "disappear":** the design doc §E says "optimistic remove + rollback on non-204." A full disappearance followed by reappearance is a jarring layout shift and makes rollback ambiguous (did a new card appear, or did the old one come back?). Dim + badge keeps the row stable; the 204 transition to "removed" is a single clean collapse. This is the §16.8 optimistic-UI pattern composed with `<PendingBadge>` — no new pattern introduced.

### 2.5 Remove confirm modal (new — design-system §7)

| Property | Value |
|---|---|
| Overlay | `fixed inset-0 bg-neutral-900/50 z-50` |
| Modal panel | `bg-white rounded-lg shadow-xl max-w-md w-full mx-auto mt-16 p-6` |
| Focus trap | Yes — focus moves to the **"Keep method"** button on open (safe default); Tab cycles within the modal; Escape activates "Keep method" (cancel). |
| Focus return | On close, focus returns to the **Remove button** that opened the modal (`mfa-method-remove-{method_type}`). |
| Title | `text-h3 font-semibold text-neutral-900` — "Remove {method label}?" |
| Body | `mt-2 text-sm text-neutral-600` — "You'll no longer be able to sign in with {method label}. If this is your only method, you may be locked out of your account." |
| Icon | `ExclamationTriangleIcon` (Heroicons outline, `w-6 h-6`, `text-fault-600`) — `flex items-start gap-3` layout with the text block |
| Cancel button (safe default, focused) | `border border-neutral-300 text-neutral-700 rounded-md px-4 py-2 text-sm font-medium hover:bg-neutral-50 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2` — label "Keep method" |
| Confirm button (destructive) | `bg-fault-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-fault-700 focus-visible:ring-2 focus-visible:ring-fault-500 focus-visible:ring-offset-2` — label "Remove method" |
| Button row | `mt-6 flex items-center justify-end gap-3` |
| Close `XMarkIcon` | top-right, `w-5 h-5 text-neutral-400 hover:text-neutral-600`, 44×44px padded hit area (`p-2 -mr-2 -mt-2`), `focus-visible:ring-2 focus-visible:ring-brand-500` |
| `data-testid` | overlay `mfa-remove-modal-overlay`; panel `mfa-remove-modal`; cancel `mfa-remove-modal-cancel`; confirm `mfa-remove-modal-confirm` |
| `aria-modal` | `true`; `aria-labelledby` → modal title id |

### 2.6 Add-method button (modified)

| Property | Value |
|---|---|
| Container | `self-start` (existing) |
| Button | `rounded-lg px-4 py-2.5 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 transition-colors` (existing tokens preserved; `hover:bg-brand-800` corrected to `hover:bg-brand-700` per token table) |
| Label | `enrolledCount === 0 ? "Add a method" : "Add another method"` (existing logic preserved) |
| Visibility | **Hidden** (not disabled) when both `totp` and `sms` are present in `methods[]`. The existing `disabled` + `title` tooltip for "all methods enrolled" is removed — with only two methods, "both enrolled" is a clean hide, not a disabled tease. |
| `data-testid` | `add-mfa-method-btn` (preserved) |

### 2.6.1 Add-method chooser (wizard method-select step)

The wizard's `MethodSelectStep` (`MFAEnrollmentWizard.tsx`) already renders only `allowedPaths`. With `allowedPaths={["totp","sms"]}` it shows exactly two options — "Authenticator app" and "Text message (SMS)". **No visual change to the step itself.** The email option is simply absent — never disabled, never teased (Rule 9.4).

### 2.7 Empty state (zero methods)

| Property | Value |
|---|---|
| Container | `rounded-lg border border-neutral-200 bg-white p-6 flex flex-col items-center gap-3 text-center` |
| Icon | `ShieldExclamationIcon` (Heroicons outline, `w-8 h-8 text-neutral-400`) |
| Title | `text-sm font-medium text-neutral-900` — "No authentication methods enrolled" |
| Body | `text-sm text-neutral-500` — "Add an authenticator app or text-message verification to protect your account." |
| CTA | the Add-method button (§2.6) renders below the empty card as normal |
| DLC-2 SMS disclosure | **Preserved.** The disclosure block (`data-testid="sms-consent-disclosure"`) lives inside the wizard's `SmsSetupStep` (`MFAEnrollmentWizard.tsx`) and appears when the user picks SMS in the wizard. It is not duplicated on the page. The existing disclosure test (`MfaMethodsPage.disclosure.test.tsx`) continues to pass. |
| `data-testid` | `mfa-empty-state` |

> **Note on `<EmptyState>` from `@pilot/ui/states`:** the shared `<EmptyState>` component is available, but the existing page uses a bespoke inline block. To minimize scope creep and preserve the existing disclosure test structure, this spec keeps the inline empty block. The engineer may swap to `<EmptyState>` if it accepts the same slots without test breakage — optional, not required.

### 2.8 Loading state (skeleton — §12)

Replace the existing bare centered spinner (`page.tsx`) with a skeleton matching the card layout (reduces layout shift per §11).

| Property | Value |
|---|---|
| Skeleton card | `rounded-lg border border-neutral-200 bg-white px-4 py-3 flex items-center gap-3` |
| Skeleton icon circle | `w-10 h-10 rounded-full bg-neutral-100 animate-pulse` |
| Skeleton line 1 | `h-4 w-32 rounded bg-neutral-100 animate-pulse` |
| Skeleton line 2 | `h-3 w-48 rounded bg-neutral-100 animate-pulse mt-1` |
| Count | 2 skeleton cards stacked in `flex flex-col gap-3` |
| `data-testid` | `mfa-method-card-skeleton` |
| `aria-busy` | `true` on the list container |
| `prefers-reduced-motion` | `animate-pulse` → static `bg-neutral-100` (no pulse). Engineer: wrap with `motion-reduce:animate-none` utility. |

### 2.9 Error state (initial load failure)

| Property | Value |
|---|---|
| Component | `<ErrorState>` from `@pilot/ui/states` |
| Message | "We couldn't load your MFA methods." |
| Retry | "Try again" button → `refetch()` the status query |
| `data-testid` | `mfa-status-error` |

### 2.10 Force-flow page (Surface 2) — context copy (new)

Added above the embedded wizard, inside the existing `max-w-lg` container.

| Property | Value |
|---|---|
| Container | `rounded-md bg-alert-50 border border-alert-200 px-4 py-3 flex items-start gap-3 mb-4` |
| Icon | `ShieldExclamationIcon` (Heroicons outline, `w-5 h-5 text-alert-600`) |
| Text | `text-sm text-alert-700` — "Your organization requires multi-factor authentication. Enrollment is not optional — set up a method to continue." |
| `role` | `alert` |
| `data-testid` | `mfa-force-flow-context-banner` |

The wizard itself receives `allowedPaths={["totp","sms"]}` (one-line prop add). `forceFlow={true}` already hides Cancel. No other wizard visual change.

---

## 3. Token-Only Colors

All colors reference `pilotPreset` token names. Zero hex codes.

| Surface | Token |
|---|---|
| Page background | `bg-neutral-50` (via shell) |
| Card / modal / empty panel | `bg-white` |
| Card border | `border-neutral-200` |
| Body text | `text-neutral-900` |
| Secondary text | `text-neutral-500`, `text-neutral-600` |
| Brand icon circle | `bg-brand-50`, icon `text-brand-600` |
| Add button | `bg-brand-600`, `hover:bg-brand-700`, text `text-white` |
| Remove action | `text-fault-600`, `hover:text-fault-700` |
| Remove confirm (destructive) | `bg-fault-600`, `hover:bg-fault-700`, text `text-white` |
| Modal overlay | `bg-neutral-900/50` |
| Tenant-policy banner (grace) | `bg-alert-50 border-alert-200 text-alert-700`, icon `text-alert-600` |
| Tenant-policy banner (0-day) | `bg-fault-50 border-fault-200 text-fault-700`, icon `text-fault-600` |
| Force-flow context banner | `bg-alert-50 border-alert-200 text-alert-700`, icon `text-alert-600` |
| Error banner (502 cognito_unavailable) | `bg-fault-50 border-fault-200 text-fault-700` |
| 409 last_method_required banner | `bg-alert-50 border-alert-200 text-alert-700` |
| Skeleton | `bg-neutral-100` |
| Focus-visible ring (brand) | `focus-visible:ring-brand-500` |
| Focus-visible ring (destructive) | `focus-visible:ring-fault-500` |

> **Contrast note:** all pairings above are pre-validated per §10 (e.g., `text-neutral-900 on bg-white` ≥ 4.5:1; `text-fault-600 on bg-white` ≥ 4.5:1; `text-alert-700 on bg-alert-50` ≥ 4.5:1). No novel pairings introduced.

---

## 4. Icon Inventory

All icons are [Heroicons 2.0](https://heroicons.com/), outline variant unless noted.

| Icon | Where | Size |
|---|---|---|
| `ShieldCheckIcon` (outline) | Method card leading — TOTP | `w-5 h-5` |
| `DevicePhoneMobileIcon` (outline) | Method card leading — SMS | `w-5 h-5` |
| `TrashIcon` (outline) | Method card Remove action | `w-4 h-4` |
| `ExclamationTriangleIcon` (outline) | Remove confirm modal | `w-6 h-6` |
| `XMarkIcon` (outline) | Remove confirm modal close | `w-5 h-5` |
| `ShieldExclamationIcon` (outline) | Tenant-policy banner; force-flow context banner; empty state | `w-5 h-5` (banner) / `w-8 h-8` (empty) |

No emoji. No custom SVG required for this batch.

---

## 5. State Coverage

### 5.1 Surface 1 — four data states (§12)

| State | Trigger | Render |
|---|---|---|
| `isPending` (initial load) | `useQuery` `isLoading` | Skeleton — 2 skeleton cards (§2.8) |
| `isError` (load failure) | `useQuery` `isError` | `<ErrorState>` with retry (§2.9) |
| Empty | `methods.length === 0` | Empty card + Add button (§2.7) |
| Populated | `methods.length >= 1` | Method-card list (§2.3) + Add button (hidden if both enrolled) |

### 5.2 Remove flow states

| State | Trigger | Render |
|---|---|---|
| Idle | default | Card default (§2.3) |
| Confirm modal open | Remove clicked | Modal (§2.5); card underneath unchanged |
| Pending (optimistic) | Confirm clicked | Card dim + `<PendingBadge>` (§2.4) |
| Success (204) | DELETE 204 | Card collapses out of list; `query.invalidate` refreshes `methods[]` |
| Rollback (non-204) | DELETE 4xx/5xx | Card returns to default; error banner rendered above the card list |
| 409 `last_method_required` | DELETE 409, `tenant_policy_required` true | `<NotificationBanner>` severity=warning: "Your organization requires MFA. Add another method before removing this one." + `query.invalidate` (409-and-refresh). Card returns to default. |
| 502 `cognito_unavailable` | DELETE 502 | `<NotificationBanner>` severity=error: "We couldn't reach the authentication service — your method was NOT removed. Try again." Card stays. |
| 401 `mfa_access_token_invalid` | DELETE 401 (stale session) | `<NotificationBanner>` severity=error: "Your session has expired. Please sign in again to manage MFA." No automatic redirect (the engineer may wire a re-sign-in nudge; do not force-redirect from a settings page). |
| 400 `mfa_access_token_required` | DELETE 400 (header missing) | Treated as a client bug, not user-facing. Log to console in dev; surface the generic 502 banner copy in prod (should never reach a real user). |

### 5.3 Tenant-policy banner states

| `tenant_policy_required` | `grace_period_active` | `grace_ends_at` | Banner |
|---|---|---|---|
| false | false | null | none |
| true | false | null | policy-required copy (§2.2) |
| true | true | future | grace copy with days remaining (§2.2) |
| true | true | today/past | 0-day copy, `bg-fault-50` (§2.2) |

---

## 6. Interaction Spec — All Five States

### 6.1 Method card Remove button

| State | Spec |
|---|---|
| Default | `text-fault-600` |
| Hover | `hover:text-fault-700`; `TrashIcon` no fill change (outline stays outline) |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-fault-500 focus-visible:ring-offset-2` |
| Active | `active:text-fault-800` (transient) |
| Disabled | N/A — Remove is always available on an enrolled card. The last-method guard is a **server-side 409**, not a client-side disable (the card cannot know tenant policy + other-methods state reliably enough to pre-disable; the 409-and-refresh pattern handles it). |

### 6.2 Add-method button

| State | Spec |
|---|---|
| Default | `bg-brand-600 text-white` |
| Hover | `hover:bg-brand-700` |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2` |
| Active | `active:bg-brand-800` (transient) |
| Disabled | Removed — button is hidden when both methods enrolled (§2.6). |

### 6.3 Remove confirm modal — Cancel ("Keep method")

| State | Spec |
|---|---|
| Default | `border border-neutral-300 text-neutral-700 bg-white` |
| Hover | `hover:bg-neutral-50` |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2` (receives initial focus on modal open) |
| Active | `active:bg-neutral-100` |

### 6.4 Remove confirm modal — Confirm ("Remove method")

| State | Spec |
|---|---|
| Default | `bg-fault-600 text-white` |
| Hover | `hover:bg-fault-700` |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-fault-500 focus-visible:ring-offset-2` |
| Active | `active:bg-fault-800` |
| Disabled | N/A — always enabled once modal is open. |

### 6.5 Modal close `XMarkIcon`

| State | Spec |
|---|---|
| Default | `text-neutral-400` |
| Hover | `hover:text-neutral-600` |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-brand-500` |
| Active | `active:text-neutral-800` |
| Hit area | 44×44px via `p-2 -mr-2 -mt-2` padding wrapper |

---

## 7. Animation Spec

| Element | Transition | Reduced-motion fallback |
|---|---|---|
| Add button color | `transition-colors duration-150 ease-in-out` | `motion-reduce:transition-none` |
| Remove button color | `transition-colors duration-150 ease-in-out` | `motion-reduce:transition-none` |
| Modal buttons color | `transition-colors duration-150 ease-in-out` | `motion-reduce:transition-none` |
| Card pending opacity | `transition-opacity duration-150 ease-in-out` (to `opacity-60`) | `motion-reduce:transition-none` — opacity applied instantly |
| Card collapse on 204 | `transition-all duration-200 ease-in-out` (height → 0, opacity → 0, margin → 0) then unmount | `motion-reduce:transition-none` — unmount immediately |
| Skeleton pulse | `animate-pulse` | `motion-reduce:animate-none` — static `bg-neutral-100` |
| Modal overlay fade-in | `transition-opacity duration-150 ease-in-out` (overlay only) | `motion-reduce:transition-none` |
| Modal panel scale-in | `transition-transform duration-150 ease-out` (`scale-95` → `scale-100`) | `motion-reduce:transition-none` — no scale |

> **No slide-in for cards on data refresh.** The status query is not an SSE live surface (§12) — it is a TanStack Query refetch. New cards appear in their sorted position without entrance animation to avoid distracting motion on a settings page.

---

## 8. Component Manifest

Reconciliation with design §I: the method-card list is **surface-scoped** inside `apps/web/src/features/account-settings/components/` — **not** a new `packages/ui` export. No orphan components. No new shared exports. The wizard is composed unchanged (locked interface); only its caller passes a different `allowedPaths` prop.

| # | File | Status | Description |
|---|---|---|---|
| 1 | `frontend/apps/web/src/app/(authed)/settings/my-account/security/mfa/page.tsx` | **Modify** | Replace raw "Enrolled: …" text block with `<MfaMethodCardList>`; add tenant-policy banner; swap bare spinner for skeleton; change `ALL_MFA_METHODS` to `["totp","sms"]`; hide (not disable) Add button when both enrolled; pass `allowedPaths={["totp","sms"]}` to the wizard; extend `MfaStatusResponse` type with `methods[]` + `tenant_policy_required` + `grace_period_active` + `grace_ends_at` + `enforcement_activated`. |
| 2 | `frontend/apps/web/src/app/(authed)/settings/my-account/security/mfa/enroll/page.tsx` | **Modify** | Add `allowedPaths={["totp","sms"]}` to the embedded wizard; add force-flow context banner above the wizard. |
| 3 | `frontend/apps/web/src/features/account-settings/components/MfaMethodCardList.tsx` | **New** | Surface-scoped list component: maps `methods[]` → `<MfaMethodCard>`; renders tenant-policy banner; manages Remove modal open state + optimistic mutation via `useOptimisticMutation` from `@pilot/ui`; renders `<NotificationBanner>` for 409/502/401. |
| 4 | `frontend/apps/web/src/features/account-settings/components/MfaMethodCard.tsx` | **New** | Surface-scoped single card: icon, label, secondary line, Remove button, pending state. Props: `method` (the `methods[]` item), `onRemove`, `isPending`. |
| 5 | `frontend/apps/web/src/features/account-settings/components/RemoveMethodConfirmModal.tsx` | **New** | Surface-scoped destructive confirm modal per §7 design-system pattern. Props: `methodLabel`, `onConfirm`, `onCancel`, `open`. Focus-trap + focus-return. |
| 6 | `frontend/apps/web/src/features/account-settings/hooks/useRemoveMfaMethod.ts` | **New** | TanStack Query `useMutation` wrapping `DELETE /me/mfa/methods/{method_id}`. Sends `X-Cognito-Access-Token` header (fetched via `aws-amplify/auth` `fetchAuthSession().tokens?.accessToken`). On 204 → invalidate `["users","me","mfa-status"]`. Exposes the RFC 7807 `code` from the error response for the banner-routing logic. |
| 7 | `frontend/packages/ui/src/mfa-enrollment-wizard/web/MFAEnrollmentWizard.tsx` | **Modify (minimal)** | Local `getAuthHeaders()` helper (`:39`) adds `X-Cognito-Access-Token` from `session.tokens?.accessToken` alongside the existing `Authorization` bearer (ID token). **No prop changes. No visual changes.** `fetch`→`apiClient` migration stays PLAT-DEBT (§G-Q7). |
| 8 | `frontend/apps/web/src/mocks/handlers/accountSecurityHandlers.ts` | **Modify** | Extend the `GET /me/mfa-status` MSW handler to return the new `methods[]` shape (with `method_id`, `method_type`, `enrolled_at`, `last_used_at: null`, `destination_masked`); extend the `DELETE` handler to return 502 `cognito_unavailable` for a test sentinel (e.g. `method_id="cognito-fail"`) so the rollback path is testable. |
| 9 | `frontend/apps/web/src/app/(authed)/settings/my-account/security/mfa/__tests__/MfaMethodsPage.disclosure.test.tsx` | **Modify** | Update the "Enrolled: totp" assertion (line 138) to the new card label "Authenticator app"; add assertions for the card list `data-testid` and the `allowedPaths`-constrained wizard. |

**Not modified (confirmed by reading):**
- `frontend/packages/ui/src/index.ts` — no new exports (method-card list is surface-scoped).
- `frontend/packages/ui/src/mfa-enrollment-wizard/types.ts` — interface LOCKED; no changes.
- `frontend/apps/web/src/features/account-settings/components/SecurityIndexPage.tsx` — upstream nav card; unchanged. Its `useMfaStatus` hook (`useMfaStatus.ts`) has a **different `MfaStatusResponse` shape** than the page's local one — the engineer should reconcile these two type definitions (the hook's shape is the older BETA-B4 one with `method_count`/`totp_enabled` etc.; the page's is the B13 one). This reconciliation is noted for the engineer but is **not a design decision** — both consume the same endpoint; the additive `methods[]` field is backward-compatible.
- `frontend/apps/web/src/features/login/components/MfaChallengeStep.tsx` — login-time challenge; copy reference only; not redesigned.

---

## 9. Wizard Internal Error States — Copy + Placement Table (Surface 3)

The wizard has two error presentation slots:
- **Top-of-wizard error** — `MFAEnrollmentWizard.tsx` (`data-testid="wizard-error"`, `role="alert"`, `text-fault-600`)
- **Inline verify error** — `VerifyStep` (`id="verify-error"`, `aria-describedby`, `text-fault-600`)

The engineer maps each RFC 7807 `code` (design §F.3) to the correct slot + copy. Four-class severity routing: `error` (fault), `warning` (alert), `info` (brand/neutral), `success` (margin).

| HTTP | `code` | Severity | Slot | Copy | Affordance |
|---|---|---|---|---|---|
| 400 | `mfa_access_token_required` | error | top-of-wizard | "Your session needs a fresh authentication token. Please sign out and sign back in, then try again." | None (client bug in prod; this is a dev guard) |
| 401 | `mfa_access_token_invalid` | error | top-of-wizard | "Your session has expired. Please sign in again to manage your MFA methods." | None — do not force-redirect from the wizard; the user can sign out via the header |
| 400 | `mfa_code_invalid` | error | inline verify | "That code doesn't match. Check your {authenticator app / phone} and try again." | Input re-focuses; "Resend code" available for SMS |
| 400 | `mfa_code_expired` | error | inline verify | "That code has expired. {Tap 'Resend code' / Request a new code} and try again." | Pairs with the existing resend path (`handleResendCode`); for TOTP there is no resend — the user re-scans/re-enters the secret, so copy becomes "That code has expired. Restart authenticator setup." with a "Restart setup" affordance that calls `handleStartEnrollment(selectedPath)` again |
| 400 | `email_mfa_not_available` | — | — | **No copy needed.** Email is unreachable in UI (`allowedPaths` hides it). The code exists only as a backend guard. |
| 400 | `phone_number_required` | error | top-of-wizard (SMS setup step) | "We need a phone number on your profile to send text-message codes. Add one at **Account → Profile**, then come back." | Link to `/settings/my-account/profile` (the profile page at `(profile-pages)/settings/my-account/profile/page.tsx` where `phone` is editable via `ProfileSettingsForm`). Render as a `<Link>` inside the error text. |
| 400 | `phone_number_invalid` | error | top-of-wizard (SMS setup step) | "That phone number doesn't look right. Update it at **Account → Profile** using the format +1 (555) 555-1234, then try again." | Same `<Link>` to profile |
| 503 | `sms_delivery_not_configured` | warning | top-of-wizard (SMS setup step) | "Text-message setup is temporarily unavailable — use an authenticator app instead." | Dignified inline notice (not a silent failure, not a fake success — DoD 2). Render with `bg-alert-50 border-alert-200 text-alert-700` + `ShieldExclamationIcon`. Below the notice, a "Set up authenticator app" button that calls `handleSelectPath("totp")` (nudge to TOTP). |
| 502 | `cognito_unavailable` | error | top-of-wizard | "We couldn't reach the authentication service. Your {enrollment / change} was not completed. Please try again in a moment." | "Try again" button re-invokes the last action |

**Verify-step code input — WCAG 2.2 SC 3.3.8 (Accessible Authentication):**
- The existing `<input>` at `MFAEnrollmentWizard.tsx` already allows paste (no `onPaste` blocker; `inputMode="numeric"`). **Explicitly note "paste allowed"** in the spec — the engineer must not add any paste-blocking logic. The input must accept a pasted 6-digit code.
- No memorization puzzle is introduced. The code is delivered out-of-band (authenticator app / SMS).
- `autoComplete="one-time-code"` is already present on the login challenge input (`MfaChallengeStep.tsx`); the wizard's verify input does **not** set `autoComplete="one-time-code"` today — the engineer should add it so iOS/OS-level OTP autofill works on web. This is an additive enhancement, not a visual change.

---

## 10. Accessibility Notes (§10)

### 10.1 Color-independent status
- Every status signal pairs color with a text label + icon. The tenant-policy banner uses `ShieldExclamationIcon` + text (not just `bg-alert-50`). The 409 banner uses text "Your organization requires MFA…" (not just a yellow flash). The 502 banner uses text "We couldn't reach the authentication service…" (not just a red flash). No status is conveyed by color alone (WCAG 1.4.1).

### 10.2 Target sizes
- Remove button: 44×44px hit area (text + `px-2 py-2` padding + icon). ✅
- Add button: `px-4 py-2.5` → ~40px tall; acceptable for a primary CTA but the engineer may bump to `py-3` if axe flags it. ✅ (≥24×24 minimum met)
- Modal close `XMarkIcon`: 44×44px via `p-2 -mr-2 -mt-2` wrapper. ✅
- Modal buttons: `px-4 py-2` → ~36px tall; meets ≥24×24 minimum. ✅
- Modal Cancel/Confirm: both ≥44px wide easily; height is the constraint — `py-2` = 36px. Acceptable per SC 2.5.8 (≥24×24). If Tom prefers 44×44 for primary modal actions, bump Confirm to `py-2.5`.

### 10.3 Focus order + focus-visible
- **Page focus order**: H1 → tenant-policy banner (if present, `role="alert"` — announced but not focusable) → method cards (Remove buttons, in DOM order) → Add button → wizard (when opened). Cards themselves are not focusable; only the Remove button inside each card is.
- **focus-visible, not focus**: all interactive elements spec `focus-visible:ring-2` (not `focus:ring-2`) so mouse users don't see a persistent ring after click (§11).
- **Modal focus**: on open, focus moves to the "Keep method" (Cancel) button — the safe default. Tab cycles: Cancel → Confirm → XMarkIcon → back to Cancel. Shift+Tab reverses. Escape = Cancel. On close, focus returns to the Remove button that opened the modal (`mfa-method-remove-{method_type}`).
- **Focus not obscured (SC 2.4.11)**: the `h-12` sticky header is `z-30`; the modal is `z-50` and overlays everything — modal focus is never obscured. For the page-level banners, anchored content beneath the sticky header needs `scroll-margin-top: 4rem` (engineer: add `scroll-mt-16` to the card list container if anchor navigation is ever added; not required this batch since there are no in-page anchors).

### 10.4 Modal focus-trap / return
- The `RemoveMethodConfirmModal` must implement a focus trap (the engineer can use `react-focus-lock` if already a dependency, or a lightweight `useEffect` Tab/Shift+Tab handler). On unmount, `document.getElementById('mfa-method-remove-{method_type}')?.focus()` restores focus. This is explicit in the spec because the design-system §7 modal pattern does not mandate a specific trap implementation — the engineer owns it, but the **behavior** is required here.

### 10.5 Form fields (wizard)
- The wizard's verify input has a visible heading (`<h2>`) above it (`MFAEnrollmentWizard.tsx`) and `aria-label="6-digit verification code"` (`:431`). Placeholder-as-label is not used. Error text is `aria-describedby="verify-error"` (`:433`). All preserved.

### 10.6 Accessible Authentication (SC 3.3.8)
- Verify-step code input: **paste allowed** (§9). No paste-blocking. `autoComplete="one-time-code"` added (additive). No memorization puzzle.

### 10.7 Reduced motion
- All transitions in §7 have `motion-reduce:` / `@media (prefers-reduced-motion: reduce)` fallbacks. Skeleton pulse becomes static. Modal scale-in becomes instant. Card collapse becomes instant unmount.

---

## 11. Implementation Notes

1. **`allowedPaths` prop — one-line change on both pages.** Surface 1 (`page.tsx`) and Surface 2 (`enroll/page.tsx`) add `allowedPaths={["totp","sms"]}` to the embedded `<MFAEnrollmentWizard>`. The prop already exists on the locked interface (`types.ts`). No wizard code changes for this.

2. **`ALL_MFA_METHODS` constant** (`page.tsx`) changes from `["totp","sms","email"]` to `["totp","sms"]`. This drives the "both enrolled → hide Add button" logic.

3. **`MfaStatusResponse` type** (local to `page.tsx`) is extended additively:
   ```ts
   interface MfaStatusResponse {
     enrolled_methods: MFAEnrollmentPath[];      // kept (deprecated; mobile uses it)
     methods: MfaMethod[];                        // NEW
     tenant_policy_required: boolean;
     grace_period_active: boolean;
     grace_ends_at: string | null;
     enforcement_activated: boolean;
   }
   interface MfaMethod {
     method_id: string;
     method_type: "totp" | "sms";
     enrolled_at: string;
     last_used_at: string | null;                 // always null this batch
     destination_masked: string | null;           // SMS only; TOTP = null
   }
   ```
   After `pnpm sync-api-types` (design §C step 2), the engineer should prefer the generated type if one exists; the local interface is a fallback until the OpenAPI regen lands.

4. **`useRemoveMfaMethod` hook** sends the `X-Cognito-Access-Token` header. The access token is fetched via `aws-amplify/auth` `fetchAuthSession()` — the same pattern the wizard's `getAuthHeaders()` uses (`MFAEnrollmentWizard.tsx`). The token is **in-memory only** — never logged, never persisted (design §E security pattern). The engineer should extract a shared `getCognitoAccessToken()` helper to avoid duplicating the Amplify import across the hook and the wizard; place it in `apps/web/src/lib/cognito-token.ts` (web-app-specific, not `packages/ui`).

5. **Optimistic Remove via `useOptimisticMutation`** (§16.8, from `@pilot/ui`):
   - `onMutate`: snapshot the current `methods[]` from the query cache; remove the target method from the cached `methods[]` (or mark it pending — see §2.4 rationale); return the snapshot as context.
   - `onError`: rollback the cache to the snapshot; parse the RFC 7807 `code` from the error response; route to the correct `<NotificationBanner>` severity + copy (§5.2).
   - `onSuccess` (204): `queryClient.invalidateQueries(["users","me","mfa-status"])` — the refetch confirms the server state.
   - The `<PendingBadge>` from `@pilot/ui` is rendered on the card during the pending window.

6. **409-and-refresh** (§16 pattern): on 409 `last_method_required`, render the warning banner AND `query.invalidate` the status query — the 409 means the server's view of "last method" is authoritative and the client should refresh rather than assume.

7. **`last_used_at` decision**: omitted from the card (§2.3). The field is in the type and the API response; it is simply not rendered. A future batch that surfaces Cognito challenge telemetry will add a "Last used {date}" tertiary line.

8. **Date formatting**: use `Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' })` on the `enrolled_at` ISO string. Do not use a date library for this single format. Timezone: display in the user's local timezone (the browser's default for `Intl`).

9. **MSW handler updates** (§8 row 8): the `GET /me/mfa-status` handler must return the new `methods[]` shape so the page renders cards in the mock environment. The `DELETE` handler gains a `cognito-fail` sentinel `method_id` that returns 502 `cognito_unavailable` so the rollback + banner path is testable. The existing `last_method_required` 409 path (`accountSecurityHandlers.ts`) is preserved.

10. **Disclosure test update** (§8 row 9): the existing test asserts `screen.getByText("Enrolled: totp")` (`MfaMethodsPage.disclosure.test.tsx`). This assertion breaks when the raw text block is replaced by cards. Update it to assert `screen.getByText("Authenticator app")` (the card label) and `screen.getByTestId("mfa-method-card-totp")`. The disclosure test's MSW fixture must also return the new `methods[]` shape.

11. **`hover:bg-brand-800` → `hover:bg-brand-700`**: the existing Add button (`page.tsx`) and wizard buttons use `hover:bg-brand-800`, which is not in the token table (§3 lists `brand-700` as the hover). The engineer should correct these to `hover:bg-brand-700` where touched. (Out of scope to audit every button in the wizard — only the ones this batch modifies.)

12. **No "coming soon" strings (Rule 9.4)**: email is absent from `allowedPaths` and from `ALL_MFA_METHODS`. No disabled email card. No "Email coming soon" tooltip. The method simply does not exist in the chooser.

13. **`SecurityIndexPage` consistency** (`SecurityIndexPage.tsx`): the upstream nav card shows `{method_count} methods enrolled`. This is unchanged. The page's card list and the index card both derive from the same endpoint; the index uses the older `useMfaStatus` hook shape. No visual inconsistency is introduced because the index shows a count, not labels.

14. **Responsive reflow (§12)**: at 1280px+ the `max-w-2xl` column is ~672px — cards render single-column comfortably. At 1024px the settings sidebar (224px) + app sidebar (256px) leave ~544px for content — cards still single-column, no reflow needed. At 768px the settings sidebar collapses (engineer: verify the shell's 768px behavior); cards remain single-column. No multi-column layout is introduced, so no table-style reflow concerns.

---

## Handoff Gate

This spec is ready for Tom's review. Implementation starts only after approval. Part B (React Engineer prompt) is authored only after Tom approves this spec (Architect Rule §1.5.5).
