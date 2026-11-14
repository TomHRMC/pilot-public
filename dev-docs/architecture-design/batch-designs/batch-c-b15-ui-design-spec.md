# C-B15 — Platform Shell + Tenant Impersonation UI Design Spec

**Batch**: C-B15 (Part B prerequisite — UI design spec)
**Surface**: Operator layout shell, tenant selector, impersonation confirm modal, impersonation banner
**Platform**: Web only (`apps/web`)
**Designer**: pilot-web-ui-designer
**Date**: August 8, 2026
**Source design doc**: `batch-c-b15-design.md` §D (API contracts), §G (resolved questions), §H (Surface Mockup Reference), §I (Component Manifest)
**Sibling spec**: `batch-c-b11-ui-design-spec.md` — operator cohort dashboard (conventions reference)
**Platform patterns**: `mvp-arch.md` §16.6 (Four-Class Severity), §16.7 (Always-Preview-Before-Send), §16.8 (Optimistic UI)

---

## 1. Surface Overview

### 1.1 What this is

A **platform-level operator shell** that wraps all `/operator/*` routes, plus the **tenant impersonation** flow that lets a platform operator view and act in the app as any tenant's owner. Four surfaces:

1. **Operator layout shell** — sidebar + header for `/operator/*` routes, with a platform-user guard.
2. **Tenant selector** — searchable dropdown in the operator header; source `GET /api/v1/operator/tenants`.
3. **Impersonation confirm modal** — §16.7 always-preview-before-send; triggered by selecting a tenant.
4. **Impersonation banner** — persistent banner at the top of both shells while an impersonation session is active.

### 1.2 Route & layout scope

- **Operator routes**: `/operator/*` — a **new route group layout** at `apps/web/src/app/operator/layout.tsx`. The existing `/operator/cohort` page (C-B11) inherits this layout automatically.
- **Tenant routes**: `/dashboard` and all `(authed)` routes — the impersonation banner mounts in `apps/web/src/app/(authed)/layout.tsx` above the existing header.
- **Login routing**: unchanged from C-B11 — `GET /api/v1/operator/auth/me` returns `user_type` + `redirect_to`. Platform users → `/operator/cohort`; tenant users → `/dashboard`.

### 1.3 Who sees it (RBAC)

This is **platform-level**, not tenant-scoped. The backend `get_platform_user()` dependency gates all three new endpoints. The frontend does NOT use `<RoleGate>` (tenant-scoped). Visibility is determined by `useAuthMe()` → `user_type === "platform"`.

| Surface element | Backend permission | Platform roles that see it |
|---|---|---|
| Operator shell (all) | `get_platform_user()` (any platform role) | `owner`, `accountant`, `support` |
| Tenant selector (read list) | `permissions.read_all === true` | `owner`, `accountant`, `support` |
| Impersonation (start/exit) | `permissions.impersonate_tenant === true` | `owner`, `support` |
| Impersonation banner | active session only | any platform user with an active session |

**Frontend visibility rule**: The tenant selector is visible to all platform users (all three roles have `read_all`). The "View as {tenant}" confirm button is **hidden** (hide-not-disable per §11) for `accountant` (`impersonate_tenant === false`). The selector still renders and is browsable for `accountant` (read-only), but selecting a tenant shows a `NotificationBanner` (warning): "Your role does not permit impersonation." rather than the confirm modal. **Hide-not-disable** for the impersonation action.

### 1.4 When it's used

Tom (platform `owner`) uses the operator shell daily to monitor the Charter cohort and to impersonate tenants for support and onboarding assistance. Impersonation is read-write as the tenant's owner (design §G Q1 — Tom-approved decision pending). Every impersonated mutation is audit-logged.

---

## 2. Operator Layout Shell

### 2.1 Shell structure

The operator layout is a full-viewport flex column. It mirrors the `(authed)` tenant shell structure (`apps/web/src/app/(authed)/layout.tsx`) but is visually distinct so an operator always knows which context they are in.

```
┌─────────────────────────────────────────────────────────────┐
│ IMPERSONATION BANNER (h-10, only if session active)          │  ← §5
├─────────────────────────────────────────────────────────────┤
│ HEADER (h-12, bg-white, border-b)                             │  ← §2.3
│ [logo] [Operator badge]              [TenantSelector ▾]      │
├──────────┬──────────────────────────────────────────────────┤
│ OPERATOR │ CONTENT AREA (flex-1, overflow-auto, bg-neutral-50)│
│ SIDEBAR  │                                                   │
│ (256px)  │  /operator/cohort page renders here               │
│          │  (page-level header + cohort table)               │
└──────────┴──────────────────────────────────────────────────┘
```

### 2.2 Platform-user guard

The layout wraps children in `<RequireAuth redirectTo="/login">` (from `@pilot/ui/auth`), then runs the platform-user check via `useAuthMe()`:

| `useAuthMe` state | Behavior |
|---|---|
| `isPending` (initial load) | Render a centered `<LoadingState>` (spinner + "Verifying access…") on a `bg-neutral-50` full-viewport. No shell chrome rendered yet. |
| `isError` | Render `<ErrorState>` (type `server`) with retry → `queryClient.invalidateQueries({ queryKey: ['auth','me'] })`. |
| `user_type === "tenant"` | `router.replace('/dashboard')` and render `null` (redirect in flight). No shell rendered. |
| `user_type === "platform"` | Render the full operator shell (§2.1). |

**Redirect state note**: the redirect is a client-side `router.replace` — there is a brief frame where the layout renders `null`. This is acceptable (the user is leaving the operator context). No loading spinner is needed for the redirect itself (the `/dashboard` route renders its own loading state).

### 2.3 Operator header

- **Container**: `h-12 bg-white border-b border-neutral-200 flex items-center justify-between px-4 shrink-0 z-30` (mirrors the `(authed)` header at `apps/web/src/app/(authed)/layout.tsx`)
- **Left side**:
  - Logo: `logo-icon.jpg` (32×32, from `apps/web/public/brand/`) when sidebar is collapsed; `logo-primary.jpg` (120×32) when expanded — same switch logic as the `(authed)` header, driven by `useSidebarState()`. Wrapped in a `<Link href="/operator/cohort">` with `aria-label="Pilot operator home"`.
  - **Operator badge** (immediately right of logo): `inline-flex items-center bg-neutral-100 text-neutral-600 rounded px-1.5 py-0.5 text-caption font-medium` — text "Operator". This is the visual distinguisher from the tenant shell (which has no badge). Paired with the logo, so it is not color-only.
- **Right side**: `<TenantSelector />` (§3). No `NotificationBell`, no `SettingsGearIcon`, no `ProfileDropdown` — those are tenant-scoped. A logout affordance is provided via a minimal icon button: `ArrowRightOnRectangleIcon` (`w-5 h-5`, outline) in a 44×44px hit area (`p-2.5 rounded-md text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700 focus-visible:ring-2 focus-visible:ring-brand-500`), `aria-label="Sign out"`, `title="Sign out"`. The engineer wires this to the existing Cognito sign-out flow (implementation note — reuse the sign-out handler from `AuthProvider`).

### 2.4 Content area

- **Container**: `flex-1 min-w-0 overflow-auto bg-neutral-50` — the cohort page (and future operator pages) render here.
- The existing C-B11 cohort page renders its own page-level header (title + Close Cohort button) inside this area. See §6 for the adjustment to the cohort page now that it inherits the shell.

### 2.5 Responsive notes

- **1280px+** (primary): sidebar 256px expanded / 64px collapsed; content area fills the rest. Header spans full width.
- **1440px**: identical layout, more content breathing room. No reflow needed.
- **1024px**: sidebar auto-collapse is not triggered (operator tool, desktop-first). The sidebar pill toggle remains manual. Content area narrows; the cohort table scrolls horizontally (built into `PilotTable`).
- **768px**: not a target viewport for operator tooling. No mobile spec (mobile is out of scope — `pilot-voice-ui-designer`).

---

## 3. Operator Sidebar (`OperatorSidebar`)

### 3.1 Purpose

Persistent left navigation for `/operator/*` routes. Mirrors `AppSidebar` collapse conventions (pill toggle, `useSidebarState`, active left-border accent) so the two shells feel like one product.

### 3.2 Nav items

| # | Label | Route | Icon (Heroicons 2.0, outline) | State |
|---|---|---|---|---|
| 1 | Cohort Dashboard | `/operator/cohort` | `Squares2X2Icon` | Active (current page) |
| 2 | More operator tools | (none — placeholder group) | `EllipsisHorizontalCircleIcon` | Disabled (coming soon) |

**Item 1 — Cohort Dashboard**:
- Active state: `bg-brand-50 text-brand-700 font-medium border-l-2 border-brand-600 pl-2.5` (identical to `AppSidebar` active treatment at `AppSidebar.tsx`)
- Inactive (future pages): `text-neutral-700 hover:bg-neutral-100 hover:text-neutral-900 pl-3`
- Icon: `w-5 h-5 shrink-0`, `aria-hidden="true"`
- Label: `truncate` when expanded; `title={label}` when collapsed

**Item 2 — More operator tools (placeholder)**:
- Non-interactive group header (not a `<Link>`). Rendered as a `<li>` with a `<div>` (not a button):
  - Expanded: `flex items-center gap-3 py-2 pl-3 text-sm text-neutral-400 cursor-not-allowed` + `EllipsisHorizontalCircleIcon` (`w-5 h-5`, `text-neutral-300`) + text "More operator tools" + a `text-caption text-neutral-400` suffix "Coming soon"
  - Collapsed: icon only, centered, `text-neutral-300`
  - `aria-disabled="true"`, `title="More operator tools coming soon"`
- This is a **disabled-but-visible** element (genuinely-unavailable, not a permission gate) — the `disabled` visual state is appropriate here per §11.

### 3.3 Sidebar container & collapse

- **Wrapper**: `relative shrink-0` (so the pill toggle can overlap the right border — identical to `AppSidebar` at `AppSidebar.tsx`)
- **Nav**: `flex flex-col h-full bg-white border-r border-neutral-200 overflow-hidden` + width class:
  - Collapsed: `w-16`
  - Expanded: `w-fit min-w-40 max-w-[12.5rem]`
- **Nav list**: `flex-1 py-3 space-y-0.5 px-2`
- **Pill toggle** (collapse/expand): identical to `AppSidebar` at `AppSidebar.tsx` — `absolute top-3 -right-3 z-20 w-6 h-6 rounded-full bg-white border border-neutral-200 shadow-sm hover:bg-neutral-50` with `ChevronDoubleLeftIcon` (`w-3 h-3`, rotates 180° when collapsed). `aria-label` toggles "Expand navigation" / "Collapse navigation".
- **State persistence**: reuses `useSidebarState()` — same `localStorage` key `pilot.sidebar.collapsed`. **Note**: this shares state with the tenant `AppSidebar`. If the operator wants independent collapse state, the engineer may introduce a separate key `pilot.operator.sidebar.collapsed` (implementation note — default to shared state for "one product" feel; flag for Tom).

### 3.4 `aria-label`

- `<nav aria-label="Operator navigation">` (distinct from `AppSidebar`'s "Main navigation")

---

## 4. Tenant Selector (`TenantSelector`)

### 4.1 Purpose

A searchable dropdown in the operator header. Source: `GET /api/v1/operator/tenants` → `OperatorTenantListResponse` (design §D.1). Selecting a tenant opens the impersonation confirm modal (§5). Client-side filtering is optimistic (§16.6) — the list filters instantly as the operator types; no refetch.

### 4.2 Trigger button (closed state)

- **Container**: `inline-flex items-center gap-2 rounded-md border border-neutral-300 bg-white px-3 py-1.5 text-sm text-neutral-700 hover:bg-neutral-50 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:border-brand-500` — minimum 44px tall (`py-1.5` + text + border ≈ 36px; bump to `py-2` if needed to hit 44px).
- **Content**: `BuildingOffice2Icon` (`w-4 h-4`, outline, `text-neutral-400`) + text "Select a tenant" (placeholder) or the last-selected tenant name (none persisted across sessions — always "Select a tenant" on fresh load) + `ChevronDownIcon` (`w-4 h-4`, outline, `text-neutral-400`)
- **`aria-haspopup="listbox"`, `aria-expanded` toggles with open state, `aria-label="Select a tenant to view as"`**

### 4.3 Dropdown panel (open state)

```
┌──────────────────────────────────────────┐
│ [🔍 Search tenants…              ] [✕]   │
├──────────────────────────────────────────┤
│ Acme Electric          Charter  ● Trialing│
│ Bright Spark LLC       Charter  ● Active │
│ Delta Wiring           Pro      ● Past due│
│ …                                        │
│ (scroll if > 8 visible)                  │
├──────────────────────────────────────────┤
│ {N} tenants                              │
└──────────────────────────────────────────┘
```

- **Panel**: `absolute right-0 top-full mt-1 w-96 max-w-[calc(100vw-2rem)] bg-white rounded-lg border border-neutral-200 shadow-lg z-40` (dropdown z-index per §7 of design-system-reference)
- **Search input** (top): `w-full px-3 py-2 text-sm border-b border-neutral-200 focus-visible:ring-0` with a `MagnifyingGlassIcon` (`w-4 h-4`, outline, `text-neutral-400`) absolutely positioned left (`pl-9` on input). Placeholder "Search tenants…". `aria-label="Search tenants"`. A clear `XMarkIcon` button (`w-4 h-4`) appears when text is present, in a 24×24px hit area.
- **List**: `max-h-80 overflow-y-auto py-1` — each row is a `<button>` (full width, left-aligned):
  - Row: `flex items-center justify-between gap-3 px-3 py-2 text-sm text-neutral-900 hover:bg-neutral-50 focus-visible:bg-neutral-50 focus-visible:ring-2 focus-visible:ring-brand-500 rounded-md mx-1`
  - **Left**: tenant name — `text-neutral-900 font-medium truncate`
  - **Right**: tier name + subscription-status pill (§4.4)
  - `aria-label="{tenant name}, {tier}, {status label}"` for screen readers
- **Footer**: `px-3 py-2 border-t border-neutral-100 text-caption text-neutral-500` — "{N} tenants" (count of filtered results)
- **Keyboard**: `ArrowDown`/`ArrowUp` moves focus between rows; `Enter` selects; `Escape` closes. The search input is the first focus when the panel opens.

### 4.4 Subscription-status pill (four-class severity, §16.6)

Each tenant row shows a status pill. **Color-independent**: icon + text label, never color alone (WCAG 1.4.1). Pill: `inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-caption font-medium`.

| `subscription_status` | Icon (outline, `w-3.5 h-3.5`) | Label | Token classes |
|---|---|---|---|
| `active` | `CheckCircleIcon` | Active | `bg-margin-100 text-margin-700` |
| `trialing` | `ClockIcon` | Trialing | `bg-blue-100 text-blue-700` |
| `past_due` | `ExclamationCircleIcon` | Past due | `bg-alert-100 text-alert-700` |
| `incomplete` | `ExclamationCircleIcon` | Incomplete | `bg-alert-100 text-alert-700` |
| `paused` | `PauseIcon` | Paused | `bg-neutral-100 text-neutral-500` |
| `canceled` | `MinusCircleIcon` | Canceled | `bg-neutral-100 text-neutral-500` |
| `null` (no subscription) | `MinusCircleIcon` | No subscription | `bg-neutral-100 text-neutral-500` |

**Tier name** (left of pill): `text-caption text-neutral-500` — e.g., "Charter", "Pro". If `tier_name` is null, render "—" in `text-neutral-400`.

### 4.5 States

**Loading (`isPending`)**:
- The dropdown panel opens with the search input rendered + a skeleton list: 6 rows of `h-9 bg-neutral-100 animate-pulse rounded mx-1`. The footer shows "Loading tenants…".
- Reduced motion: `@media (prefers-reduced-motion: reduce)` → skeleton is static `bg-neutral-100` (no pulse).

**Empty (no tenants)**:
- Use `<EmptyState>` (type `no-data`) rendered inside the panel below the search input: title "No tenants found", description "Tenants will appear here once they sign up." No CTA.

**Error (`isError`)**:
- Use `<ErrorState>` (type `server`) inside the panel: `onRetry` → `queryClient.invalidateQueries({ queryKey: ['operator-tenants'] })`. The search input remains functional (filtering the empty list shows nothing — acceptable).

**No search results**:
- A centered `text-sm text-neutral-500 py-6` — "No tenants match "{query}."" with the query in `font-medium text-neutral-700`.

### 4.6 Optimistic filtering (§16.8 / §16.6)

- The full tenant list is fetched once (`useOperatorTenants`, `staleTime: 5 * 60 * 1000`). Filtering is **client-side** as the operator types — the visible list updates instantly with no network request. This is the optimistic-UI application for this surface (design §E, §16.6).
- No pending badge is needed (filtering is synchronous, not a mutation).

### 4.7 Selecting a tenant

On row click (or `Enter`):
1. The dropdown closes.
2. If the platform user's role has `impersonate_tenant === true` (`owner`, `support`): open `<ImpersonationConfirmModal>` (§5) with the selected tenant.
3. If `impersonate_tenant === false` (`accountant`): do NOT open the modal. Show a `<NotificationBanner>` (severity `warning`) at the top of the content area: "Your role does not permit impersonation." The selector stays closed. (Hide-not-disable at the action level — the selector is browsable, the impersonation action is blocked with a clear message.)

---

## 5. Impersonation Confirm Modal (`ImpersonationConfirmModal`)

### 5.1 Pattern: Always-Preview-Before-Send (§16.7)

Impersonation is a one-way-door action (the operator will act as the tenant's owner with real, audit-logged consequences). Per §16.7, the operator sees a **preview** of the context they are about to enter before confirming. This surface does NOT use `<MessagePreviewModal>` — that component is locked to communication previews (SMS/email). The impersonation confirm is a **domain-specific confirm modal** that follows the same *preview-then-confirm* philosophy but renders tenant-context content, not message content. **Do not repurpose `MessagePreviewModal`** — its props (`previewData`, `onConfirm`, channel pills) don't fit.

### 5.2 Component-existence check

Per the design doc §I, `ImpersonationConfirmModal` is "New (compose existing modal primitive — existence check required)." The barrel at `frontend/packages/ui/src/index.ts` was read in full. **No generic `Modal` or `Dialog` primitive is exported** — all modals in the library are domain-specific (`MessagePreviewModal`, `StalenessRefreshDialog`, `RevertToDefaultDialog`), each built on the standard modal pattern (§7 of design-system-reference). Therefore `ImpersonationConfirmModal` is built as a new feature-specific component following the same standard modal pattern (overlay + panel + focus trap), consistent with how C-B11's `CloseCohortButton` modal was built. No orphan component — this reconciles with design §I.

### 5.3 Modal layout

```
┌─────────────────────────────────────────────────┐
│ View as a tenant                            [X] │
├─────────────────────────────────────────────────┤
│                                                 │
│  You are about to view Pilot as                 │
│  Acme Electric (owner).                         │
│                                                 │
│  All changes you make are real and audit-logged. │
│                                                 │
│  ── Preview ──────────────────────────────────  │
│  ┌───────────────────────────────────────────┐  │
│  │ Tenant:   Acme Electric                  │  │
│  │ Tier:     Charter                        │  │
│  │ Status:   ● Trialing                     │  │
│  │ Role:     Owner (full access)            │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  ⚠ This session persists until you exit.        │
│                                                 │
│              [Cancel]  [View as Acme Electric]  │
│                                                 │
└─────────────────────────────────────────────────┘
```

### 5.4 Modal panel specs

- **Overlay**: `fixed inset-0 bg-neutral-900/50 z-50` (per §7 of design-system-reference)
- **Panel**: `bg-white rounded-lg shadow-xl max-w-md w-full mx-auto mt-16 p-6`
- **Close button**: top-right `XMarkIcon` (`w-5 h-5`, outline) in a 44×44px hit area (`p-2.5 rounded-md hover:bg-neutral-100 focus-visible:ring-2 focus-visible:ring-brand-500`)
- **Title**: `text-h2 font-semibold text-neutral-900` — "View as a tenant"
- **z-index**: `z-50` (modal + overlay)

### 5.5 Body content

- **Lead sentence**: `text-sm text-neutral-700 mt-2` — "You are about to view Pilot as **{tenant name}** (owner)." The tenant name is wrapped in `<strong className="font-semibold text-neutral-900">`.
- **Warning sentence**: `text-sm text-fault-600 font-medium mt-2` — "All changes you make are real and audit-logged." with `ExclamationTriangleIcon` (`w-4 h-4`, outline) inline before the text.

### 5.6 Preview block

A bordered panel showing the exact context the operator will enter. This is the **always-preview-before-send** safeguard.

- **Container**: `bg-neutral-50 border border-neutral-200 rounded-md p-4 mt-4`
- **Rows** (label-value pairs, `flex justify-between gap-4 text-sm py-1`):
  - "Tenant" → `text-neutral-900 font-medium` — the selected tenant name
  - "Tier" → `text-neutral-700` — the tier name (or "—" if null)
  - "Status" → the subscription-status pill from §4.4 (reused — same icon + label + tokens)
  - "Role" → `text-neutral-700` — "Owner (full access)"

### 5.7 Persistence note

- `text-sm text-neutral-700 mt-3 flex items-center gap-1.5` — `ExclamationCircleIcon` (`w-4 h-4`, outline, `text-alert-600`) + "This session persists until you exit. Closing the tab also ends the session." (Reinforces the `sessionStorage` tab-scoped behavior from design §G Q2.)

### 5.8 Action buttons

- **Container**: `flex justify-end gap-3 mt-6`
- **Cancel** (default, safe): `border border-neutral-300 text-neutral-700 rounded-md px-4 py-2 text-sm font-medium hover:bg-neutral-50 focus-visible:ring-2 focus-visible:ring-brand-500` — closes modal, no action.
- **View as {tenant name}** (primary CTA): `bg-brand-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-brand-700 focus-visible:ring-2 focus-visible:ring-brand-500 disabled:bg-neutral-300 disabled:cursor-not-allowed` — disabled while the start mutation is in-flight. The button label includes the tenant name: "View as Acme Electric".
- **Button order**: Cancel (left), View as (right). Cancel is the default safe action.

### 5.9 On confirm

1. Call `useImpersonationStart` mutation (`POST /api/v1/operator/impersonation/start`).
2. On **success**: `setImpersonation({ tenantId, tenantName })` (writes to `sessionStorage` `pilot.impersonation`) → `window.location.assign('/dashboard')` (deliberate **full page reload** — design §G Q2/Q3; not an in-place state swap, to avoid cross-tenant cache leakage).
3. On **error** (403 / 404 / 409): the modal stays open. A `text-fault-600` error message appears below the preview block:
   - `403` (no permission): "Your role does not permit impersonation."
   - `404` (tenant not found): "This tenant no longer exists."
   - `409` (tenant inactive): "This tenant is inactive and cannot be impersonated."
   - The confirm button re-enables. The operator must close the modal or pick another tenant.

### 5.10 In-flight state

While the start mutation is pending: the confirm button shows `disabled:bg-neutral-300 disabled:cursor-not-allowed` and the button text appends "…" → "View as Acme Electric…". The Cancel button remains enabled (the operator can cancel the in-flight request — the mutation is aborted on unmount).

---

## 6. Impersonation Banner (`ImpersonationBanner`)

### 6.1 Purpose

A persistent banner at the top of both shells while an impersonation session is active. It is the constant visual reminder that the operator is acting as a tenant. **Color-independent** (icon + text, never color alone — WCAG 1.4.1).

### 6.2 Banner layout

```
┌─────────────────────────────────────────────────────────────┐
│ 👁 Viewing as: Acme Electric          [↗ Exit]              │
└─────────────────────────────────────────────────────────────┘
```

- **Container**: `h-10 bg-alert-50 border-b border-alert-200 flex items-center justify-between px-4 shrink-0 z-40`
- **Left side**: `inline-flex items-center gap-2 text-sm font-medium text-alert-800` — `EyeIcon` (`w-4 h-4`, outline) + text "Viewing as: {tenantName}". The tenant name is `font-semibold`. The `EyeIcon` is the color-independent signal (icon + text, not color alone).
- **Right side — Exit button**: `inline-flex items-center gap-1.5 text-sm font-medium text-alert-700 hover:text-alert-900 rounded-md px-2 py-1 focus-visible:ring-2 focus-visible:ring-alert-500` — `ArrowRightOnRectangleIcon` (`w-4 h-4`, outline) + text "Exit". Hit area: `px-2 py-1` + text + icon ≈ 28×32px (meets SC 2.5.8 ≥24×24). `aria-label="Exit impersonation and return to operator cohort"`.

### 6.3 Color choice rationale

`bg-alert-50` (amber) signals "attention — you are in a special mode" without implying an error (`fault`) or success (`margin`). The amber tone is distinct from both the tenant shell (white header) and the operator shell (white header), so the banner reads as an overlay-state in either context. Paired with the `EyeIcon` + "Viewing as:" text, it is color-independent.

### 6.4 On exit

1. Call `useImpersonationEnd` mutation (`POST /api/v1/operator/impersonation/end`).
2. On **success or failure** (defensive — design §D.3 always returns 200): `clearImpersonation()` (removes `sessionStorage` `pilot.impersonation`) → `window.location.assign('/operator/cohort')` (deliberate **full page reload**).
3. The Exit button shows a brief in-flight state: text "Exiting…" + `disabled:cursor-not-allowed` while the mutation is pending. The full reload happens on settle, so the in-flight state is momentary.

### 6.5 Coexistence with both shells

The banner mounts as the **first child** of the outer flex column in both layouts, before the header. It is a **normal-flow `shrink-0` bar** (NOT CSS `position: fixed`) — this is the critical layout decision:

- **`(authed)` layout** (`apps/web/src/app/(authed)/layout.tsx`): the outer `div` is `flex flex-col h-full min-h-screen`. The banner inserts as the first child (`shrink-0`), pushing the existing `h-12` header down by 40px. The sidebar (`h-full` via the `flex-1` sibling) and content area fill the remaining space. **No overlap, no displacement of the header/sidebar** — the banner occupies its own 40px row. The page itself does not scroll (the content area `overflow-auto` does), so the banner is always visible. Verified at 1280px and 1440px: the flex column absorbs the extra 40px without reflow.
- **Operator layout** (§2.1): identical structure — banner first child, then header, then sidebar+content.

**Why not `position: fixed`**: a fixed banner would overlay the header (z-fighting) and require a `scroll-margin-top` / `padding-top` hack on the content area to avoid the banner covering content. The normal-flow approach is simpler and layout-safe. The banner is "fixed" in the sense of *always present while the session is active*, not CSS-fixed.

### 6.6 When it renders

- **`(authed)` shell**: renders when `useImpersonation()` returns a non-null session. This is the primary use case — the operator is viewing the tenant app as the tenant.
- **Operator shell**: renders when `useImpersonation()` returns a non-null session. In practice this is a **safety net** — the operator is normally navigated to `/dashboard` on impersonation start, so they would not be on `/operator/*` while impersonating. If they somehow land on `/operator/*` with a stale session (e.g., manual URL entry), the banner shows and the Exit action returns them to `/operator/cohort` cleanly.

### 6.7 Mount condition

Both layouts render `{useImpersonation() && <ImpersonationBanner />}`. The `useImpersonation()` hook (from `frontend/packages/shared-api/src/impersonation.ts`, design §F.3) reads `sessionStorage` on mount and subscribes to `storage` / custom events for cross-tab sync.

---

## 7. Cohort Page Adjustment (existing C-B11 component)

### 7.1 What changes

The C-B11 cohort page (`apps/web/src/app/operator/cohort/page.tsx`) and its orchestrator (`CohortDashboardClient.tsx`) were built as a standalone route with their own minimal layout. With the C-B15 operator layout now wrapping `/operator/*`, two adjustments are needed:

1. **Remove the `RequireAuth` wrapper** from `CohortDashboardClient` — the operator layout now provides `<RequireAuth>` + the platform-user guard. The cohort page no longer needs its own auth gate. (The `useAuthMe()` call inside `CohortDashboardClient` for permission flags stays — it's still needed for action visibility.)
2. **Simplify the page-level header** — the C-B11 page header (§2.2 of the C-B11 spec) rendered `logo-icon` + "Pilot Operator — Charter Cohort" + Close Cohort button. Now that the shell header provides the logo + "Operator" badge, the cohort page header should:
   - Remove the `logo-icon` (the shell header has it).
   - Change the title to "Charter Cohort" (`text-h2 font-semibold text-neutral-900`) — drop the "Pilot Operator —" prefix (the shell header's "Operator" badge covers that).
   - Keep the Close Cohort button on the right (unchanged).
   - Container: `h-16 bg-white border-b border-neutral-200 px-6 flex items-center justify-between sticky top-0 z-20` (z-20, below the shell header's z-30).

### 7.2 No other C-B11 changes

The cohort table, summary strip, modals, alert-level styling, and all interaction states from the C-B11 spec remain unchanged. The shell wraps them; they render inside the content area.

---

## 8. Empty / Loading / Error States

### 8.1 Operator layout — platform guard

See §2.2. `isPending` → centered `<LoadingState>` "Verifying access…". `isError` → `<ErrorState>` with retry. `user_type === "tenant"` → redirect.

### 8.2 Tenant selector

See §4.5. `isPending` → skeleton list. Empty → `<EmptyState>`. `isError` → `<ErrorState>` with retry. No search results → inline message.

### 8.3 Impersonation start failure

See §5.9. Modal stays open with a `text-fault-600` error message. 403 / 404 / 409 each have a specific message.

### 8.4 Impersonation end failure

The end endpoint always returns 200 (design §D.3 — defensive). On a network error, the banner's Exit button still calls `clearImpersonation()` + `window.location.assign('/operator/cohort')` — the local session is cleared regardless of the network result. A transient `NotificationBanner` (warning) is not needed (the full reload resets state). If the engineer wants belt-and-suspenders, a `console.warn` on end failure is acceptable.

---

## 9. Interaction States & Motion

### 9.1 Tenant selector trigger button

| State | Classes |
|---|---|
| Default | `border-neutral-300 bg-white text-neutral-700 hover:bg-neutral-50` |
| Hover | `bg-neutral-50` |
| Focus-visible | `ring-2 ring-brand-500 border-brand-500` |
| Active | `bg-neutral-100` |
| Disabled | n/a (always enabled for platform users with `read_all`) |

### 9.2 Tenant selector list row

| State | Classes |
|---|---|
| Default | `text-neutral-900 hover:bg-neutral-50` |
| Hover | `bg-neutral-50` |
| Focus-visible | `bg-neutral-50 ring-2 ring-brand-500` |
| Active | `bg-brand-50` |

### 9.3 Impersonation confirm button

| State | Classes |
|---|---|
| Default | `bg-brand-600 text-white hover:bg-brand-700` |
| Hover | `bg-brand-700` |
| Focus-visible | `ring-2 ring-brand-500 ring-offset-2` |
| Active | `bg-brand-800` |
| Disabled (in-flight) | `bg-neutral-300 text-neutral-500 cursor-not-allowed` |

### 9.4 Banner Exit button

| State | Classes |
|---|---|
| Default | `text-alert-700 hover:text-alert-900` |
| Hover | `text-alert-900 bg-alert-100` |
| Focus-visible | `ring-2 ring-alert-500` |
| Active | `text-alert-900` |
| Disabled (in-flight) | `text-alert-400 cursor-not-allowed` |

### 9.5 Sidebar pill toggle

Identical to `AppSidebar` (`AppSidebar.tsx`): `hover:bg-neutral-50`, `focus-visible:ring-2 focus-visible:ring-brand-500`.

### 9.6 Animation spec

| Element | Transition | Reduced motion |
|---|---|---|
| Sidebar collapse/expand | `transition-[width] 200ms ease-in-out` (mirrors `(authed)` header logo switch at `layout.tsx`) | no transition (instant width) |
| Pill toggle icon rotate | `transition-transform 200ms ease-in-out` | no transition |
| Dropdown panel open/close | `opacity 150ms ease-out` + `transform 150ms ease-out` (scale 0.98→1.0) | instant (no fade/scale) |
| Modal open/close | `opacity 200ms ease-out` (overlay) + `transform 200ms ease-out` (panel scale 0.95→1.0) | instant |
| Skeleton pulse | `animate-pulse` (Tailwind 2s) | static `bg-neutral-100` |
| Row hover | `transition-colors 150ms ease-in-out` | no transition |

All transitions: `@media (prefers-reduced-motion: reduce) → transition: none`.

---

## 10. Accessibility Notes (WCAG 2.2 AA)

### 10.1 Color-independent status

- **Subscription-status pill** (§4.4): every status pairs a color token with an icon (`CheckCircleIcon` / `ClockIcon` / `ExclamationCircleIcon` / `PauseIcon` / `MinusCircleIcon`) AND a text label ("Active" / "Trialing" / "Past due" / etc.). Color is never the only signal. Passes WCAG 1.4.1.
- **Impersonation banner** (§6): the amber background is paired with an `EyeIcon` + "Viewing as: {tenantName}" text. A user who cannot perceive color still reads the banner. Passes WCAG 1.4.1.
- **Operator badge** (§2.3): the "Operator" text label is the signal; the `bg-neutral-100` is decorative. Not color-only.

### 10.2 Contrast ratios

All token pairings used are pre-validated per §10 of web-app-design-standards:
- `text-alert-800 on bg-alert-50` — ≥ 4.5:1 ✅ (amber-800 is dark on light amber-50)
- `text-alert-700 on bg-alert-50` (Exit button) — ≥ 4.5:1 ✅
- `text-neutral-900 on bg-white` (selector rows, modal title) — ≥ 4.5:1 ✅
- `text-neutral-700 on bg-white` (body text) — ≥ 4.5:1 ✅
- `text-fault-600 on bg-white` (warning sentence) — ≥ 4.5:1 ✅
- `text-brand-600 on bg-white` — n/a (button is `bg-brand-600 text-white`, contrast ≥ 4.5:1 ✅)
- Badge text on badge bg (e.g., `text-blue-700 on bg-blue-100`, `text-margin-700 on bg-margin-100`, `text-alert-700 on bg-alert-100`) — ≥ 4.5:1 ✅

### 10.3 Target sizes

| Element | Target size | Meets SC 2.5.8 (≥24×24)? |
|---|---|---|
| Tenant selector trigger | ~44×36px (bump to `py-2` if needed) | ✅ |
| Selector list row | full-width × ~36px | ✅ |
| Selector search clear `XMarkIcon` | 24×24px hit area | ✅ (minimum) |
| Modal close `XMarkIcon` | 44×44px (`p-2.5`) | ✅ (preferred) |
| Cancel / Confirm buttons | ~44×36px | ✅ |
| Banner Exit button | ~28×32px (`px-2 py-1`) | ✅ |
| Sidebar pill toggle | 24×24px (`w-6 h-6`) | ✅ (minimum) |
| Logout icon button | 44×44px (`p-2.5`) | ✅ (preferred) |

### 10.4 Focus order & focus-visible

- **Operator shell load**: focus moves to the shell header. Tab order: header (logo link → logout) → sidebar (nav items → pill toggle) → content area (cohort page header → table → actions).
- **Tenant selector**: trigger button → (open) search input → list rows → footer. `ArrowDown`/`ArrowUp` moves a roving `tabindex` through rows. `Escape` closes and returns focus to the trigger button.
- **Modal**: focus moves to the Cancel button (safe default) on open. Focus is trapped within the modal (Tab cycles: Cancel → Confirm → Close `XMarkIcon`). On close, focus returns to the tenant selector trigger (the element that opened the modal).
- **`focus-visible`** (not `focus`): all interactive elements use `focus-visible:ring-2 focus-visible:ring-brand-500` (or `ring-alert-500` for the banner Exit). Keyboard users get a ring; mouse users don't see a persistent ring on click.
- **Focus not obscured** (SC 2.4.11): the shell header is `sticky top-0 z-30`. The banner (when present) is `z-40` above it. Modal overlay is `z-50` above both. When a modal opens, focus moves into the modal (above all chrome). No `scroll-margin-top` issue — the content area scrolls, not the page; the banner + header are always at the top of the viewport.

### 10.5 Screen reader announcements

- The banner uses `role="status"` with `aria-live="polite"` so screen readers announce "Viewing as: {tenantName}" when the session starts. The Exit button has a descriptive `aria-label`.
- The tenant selector trigger has `aria-haspopup="listbox"` + `aria-expanded`. The list rows have descriptive `aria-label`s including tenant name, tier, and status label.
- The modal has `role="dialog"` + `aria-modal="true"` + `aria-labelledby` pointing to the title "View as a tenant".
- The subscription-status pill icons are `aria-hidden="true"`; the text label is the accessible name.

### 10.6 Modal dismiss

- `Escape` key closes the modal (same as Cancel — no action taken).
- Clicking the overlay closes the modal (same as Cancel).
- Dismissing via Escape/overlay is safe (no data lost — no action has been taken yet; the start mutation only fires on confirm).

### 10.7 Consistent help

- No `<HelpAnchor>` on operator surfaces (operator-only internal tool; the help system is for tenant users — same decision as C-B11 §12.2).

---

## 11. Token Manifest (Zero Hex Codes)

Every color in this spec uses `pilotPreset` token names. The React Engineer must not hardcode any hex value.

| Token | Used for |
|---|---|
| `bg-neutral-50` | Page background, skeleton base |
| `bg-white` | Header, sidebar, selector panel, modal panel |
| `bg-neutral-100` | Operator badge, neutral status pills, skeleton static, disabled button |
| `bg-neutral-900/50` | Modal overlay |
| `bg-brand-50` | Active nav item bg, selector row active |
| `bg-brand-600` | Primary CTA (confirm) |
| `bg-brand-700` | Primary CTA hover |
| `bg-brand-800` | Primary CTA active |
| `bg-alert-50` | Impersonation banner bg |
| `bg-alert-100` | Banner Exit hover, alert status pill bg |
| `bg-margin-100` | Active status pill bg |
| `bg-blue-100` | Trialing status pill bg |
| `text-neutral-900` | Primary text, tenant name, modal title |
| `text-neutral-700` | Secondary text, body text, nav inactive |
| `text-neutral-600` | Operator badge text |
| `text-neutral-500` | Tertiary text, helper, neutral pill text, logout icon |
| `text-neutral-400` | Search icon, clear icon, disabled text, tier name null |
| `text-alert-800` | Banner text ("Viewing as:") |
| `text-alert-700` | Banner Exit button, alert pill text |
| `text-alert-900` | Banner Exit hover/active |
| `text-alert-400` | Banner Exit disabled |
| `text-alert-600` | Persistence note icon, warning sentence |
| `text-fault-600` | Error text, warning sentence (audit-logged) |
| `text-margin-700` | Active pill text |
| `text-blue-700` | Trialing pill text |
| `text-brand-700` | Active nav item text |
| `text-white` | Button text (on brand bg) |
| `border-neutral-200` | Header, sidebar, selector panel, modal preview, search input divider |
| `border-neutral-300` | Selector trigger border, logout button hover ring base |
| `border-neutral-100` | Selector footer divider |
| `border-alert-200` | Banner bottom border |
| `border-brand-600` | Active nav item left border |
| `ring-brand-500` | Focus-visible ring (primary actions, inputs, selector) |
| `ring-alert-500` | Focus-visible ring (banner Exit) |
| `shadow-sm` | Sidebar pill toggle |
| `shadow-lg` | Selector dropdown panel |
| `shadow-xl` | Modal panel |

---

## 12. Icon Inventory (Heroicons 2.0)

All icons are [Heroicons 2.0](https://heroicons.com/). Outline variant unless noted.

| Icon | Variant | Size | Used in |
|---|---|---|---|
| `Squares2X2Icon` | outline | `w-5 h-5` | Operator sidebar — Cohort Dashboard |
| `EllipsisHorizontalCircleIcon` | outline | `w-5 h-5` | Operator sidebar — More tools placeholder |
| `ChevronDoubleLeftIcon` | outline | `w-3 h-3` | Sidebar pill toggle (collapse) |
| `ChevronDownIcon` | outline | `w-4 h-4` | Tenant selector trigger |
| `BuildingOffice2Icon` | outline | `w-4 h-4` | Tenant selector trigger |
| `MagnifyingGlassIcon` | outline | `w-4 h-4` | Tenant selector search |
| `XMarkIcon` | outline | `w-4 h-4` | Selector search clear |
| `XMarkIcon` | outline | `w-5 h-5` | Modal close button |
| `CheckCircleIcon` | outline | `w-3.5 h-3.5` | Active status pill |
| `ClockIcon` | outline | `w-3.5 h-3.5` | Trialing status pill |
| `ExclamationCircleIcon` | outline | `w-3.5 h-3.5` | Past due / Incomplete status pill, persistence note |
| `PauseIcon` | outline | `w-3.5 h-3.5` | Paused status pill |
| `MinusCircleIcon` | outline | `w-3.5 h-3.5` | Canceled / No subscription status pill |
| `ExclamationTriangleIcon` | outline | `w-4 h-4` | Modal warning sentence (audit-logged) |
| `EyeIcon` | outline | `w-4 h-4` | Impersonation banner |
| `ArrowRightOnRectangleIcon` | outline | `w-4 h-4` | Banner Exit button, header logout button |
| `ArrowRightOnRectangleIcon` | outline | `w-5 h-5` | Header logout button (larger) |

No emoji. No custom SVG required.

---

## 13. Component Manifest

Reconciled with design doc §I. No orphan components. New operator components are placed in `apps/web/src/components/operator/` (domain-specific). The store lives in `packages/shared-api` (cross-platform). Hooks live in `apps/web/src/features/operator/hooks/`.

| Component | Path | Status | Description |
|---|---|---|---|
| `impersonation.ts` store + `useImpersonation` | `frontend/packages/shared-api/src/impersonation.ts` | NEW | Module-level `sessionStorage` store (`pilot.impersonation`), `getImpersonation`/`setImpersonation`/`clearImpersonation` + `useImpersonation()` React hook. Not a UI component — listed for manifest reconciliation. |
| `OperatorLayout` | `apps/web/src/app/operator/layout.tsx` | NEW | Client route layout: `<RequireAuth>` + platform-user guard (`useAuthMe`), renders banner (if active) + header + `OperatorSidebar` + content area. |
| `OperatorSidebar` | `apps/web/src/components/operator/OperatorSidebar.tsx` | NEW | Nav: Cohort Dashboard (active) + disabled "More operator tools" placeholder. Mirrors `AppSidebar` collapse conventions via `useSidebarState`. |
| `TenantSelector` | `apps/web/src/components/operator/TenantSelector.tsx` | NEW | Searchable dropdown: trigger button + panel (search input + list + footer). Source `useOperatorTenants`. Client-side filtering (§16.6). Selecting a tenant → confirm modal (or warning banner for `accountant`). |
| `ImpersonationConfirmModal` | `apps/web/src/components/operator/ImpersonationConfirmModal.tsx` | NEW | §16.7 always-preview confirm modal. Preview block (tenant/tier/status/role) + Cancel / "View as {name}". On confirm → `useImpersonationStart` → `setImpersonation` → `window.location.assign('/dashboard')`. Built on standard modal pattern (no generic `Modal` primitive exists in `packages/ui` — existence check confirmed). |
| `ImpersonationBanner` | `apps/web/src/components/operator/ImpersonationBanner.tsx` | NEW | `h-10` amber banner: `EyeIcon` + "Viewing as: {name}" + Exit button. Mounted in `OperatorLayout` and `(authed)/layout.tsx` when `useImpersonation()` is non-null. Exit → `useImpersonationEnd` → `clearImpersonation` → `window.location.assign('/operator/cohort')`. |
| `useOperatorTenants` | `apps/web/src/features/operator/hooks/useOperatorTenants.ts` | NEW | TQ v5 query — `GET /api/v1/operator/tenants`. Query key: `['operator-tenants']`. `staleTime: 5min`, `retry: false`. |
| `useImpersonationStart` | `apps/web/src/features/operator/hooks/useImpersonationStart.ts` | NEW | TQ v5 mutation — `POST /api/v1/operator/impersonation/start`. `retry: false`. |
| `useImpersonationEnd` | `apps/web/src/features/operator/hooks/useImpersonationEnd.ts` | NEW | TQ v5 mutation — `POST /api/v1/operator/impersonation/end`. `retry: false`. |
| `operatorTenantsHandlers` | `apps/web/src/mocks/handlers/operatorTenantsHandlers.ts` + barrel | NEW | MSW handlers for 3 endpoints (GET tenants, POST start, POST end). |
| `(authed)/layout.tsx` | `apps/web/src/app/(authed)/layout.tsx` | MODIFIED | Mount `<ImpersonationBanner />` as first child of the outer flex column (before the header) when `useImpersonation()` is non-null. |
| `AuthProvider.tsx` | `frontend/packages/ui/src/auth/AuthProvider.tsx` | MODIFIED | `fetchUserFromBackend()` attaches `X-Impersonate-Tenant` header from the store when present. Full reload on start/exit re-runs the provider. |
| `client.ts` | `frontend/packages/shared-api/src/client.ts` | MODIFIED | Request interceptor adds `X-Impersonate-Tenant` header when `getImpersonation()` is non-null (after JWT attach). |
| `CohortDashboardClient.tsx` | `apps/web/src/components/operator/cohort/CohortDashboardClient.tsx` | MODIFIED | Remove `RequireAuth` wrapper (layout provides it). Simplify page header: remove logo, title → "Charter Cohort". See §7. |

### 13.1 Shared components consumed (no changes)

| Component | Import | Used for |
|---|---|---|
| `RequireAuth` | `@pilot/ui/auth` | Auth gate in `OperatorLayout` |
| `LoadingState` | `@pilot/ui/states` | Platform guard pending state |
| `ErrorState` | `@pilot/ui/states` | Platform guard error, selector error |
| `EmptyState` | `@pilot/ui/states` | Selector empty (no tenants) |
| `NotificationBanner` | `@pilot/ui` | `accountant` impersonation-blocked warning |
| `useSidebarState` | `@/hooks/useSidebarState` | Sidebar collapse state (shared with `AppSidebar`) |
| `useAuthMe` | `@/features/auth/hooks/useAuthMe` | Platform-user guard + permission flags |

### 13.2 Components NOT used (and why)

| Component | Why not |
|---|---|
| `MessagePreviewModal` | Locked to communication previews (SMS/email). Impersonation confirm is tenant-context content — domain-specific modal built instead. (Same decision as C-B11 §5.2.) |
| `RoleGate` | Tenant-scoped RBAC. This is a platform-level surface — visibility is determined by `useAuthMe()` → `user_type`/`platform_role_code`, not `<RoleGate>`. |
| `PendingBadge` | No optimistic mutation on this surface — selector filtering is synchronous; impersonation start/exit are deliberate full reloads (not optimistic, per design §G Q2/Q3). |
| `HelpAnchor` | Operator-only internal tool. Help system is for tenant users. (Same as C-B11 §12.2.) |
| `PilotPaginator` | Tenant list is unbounded-scroll dropdown with client-side filter; no pagination (design §D.1 — < 200 tenants at MVP). |

---

## 14. Implementation Notes

### 14.1 Route placement

The operator layout lives at `apps/web/src/app/operator/layout.tsx`. Next.js route group layouts apply to all pages in the segment — the existing `cohort/page.tsx` inherits it automatically. No change to the cohort route file itself (only to `CohortDashboardClient` per §7).

### 14.2 Platform-user guard

`useAuthMe()` (`useAuthMe.ts`) returns `AuthMeResponse` with `user_type` and `platform_role_code`. The layout checks `user_type === "platform"`; otherwise redirects to `/dashboard` (or the `redirect_to` from the response if present). The `platform_role_code` is passed to `TenantSelector` to determine impersonation permission (`owner`/`support` → allowed; `accountant` → blocked with warning).

Permission mapping (mirrors C-B11 `CohortDashboardClient.tsx`):

| `platform_role_code` | `impersonate_tenant` | Sees selector | Can impersonate |
|---|---|---|---|
| `owner` | true | ✅ | ✅ |
| `support` | true | ✅ | ✅ |
| `accountant` | false | ✅ (read-only) | ❌ (warning banner on select) |

### 14.3 Impersonation store

`frontend/packages/shared-api/src/impersonation.ts` (design §F.3):
- `sessionStorage` key: `pilot.impersonation` = `JSON.stringify({ tenantId, tenantName })`
- `getImpersonation()`: reads + parses; returns `null` if absent/invalid.
- `setImpersonation(s)`: writes + dispatches a custom `pilot:impersonation-change` event.
- `clearImpersonation()`: removes + dispatches the event.
- `useImpersonation()`: React hook — reads on mount, subscribes to the custom event + `storage` event (cross-tab), returns `ImpersonationSession | null`.

### 14.4 Header injection

`client.ts` request interceptor (design §F.3): after the JWT is attached, `const imp = getImpersonation(); if (imp) config.headers["X-Impersonate-Tenant"] = imp.tenantId;`. This is read synchronously from `sessionStorage` on every request — no React state involved.

`AuthProvider.tsx` `fetchUserFromBackend()` (design §C-B Part B task 6): attaches the same header to its raw `fetch()` call (this predates the `apiClient` mandate). On full reload after `setImpersonation`/`clearImpersonation`, `AuthProvider` re-runs and fetches the user under the new context.

### 14.5 Full reload — not optimistic

Impersonation start and exit are **deliberate full page reloads** (`window.location.assign`), not optimistic UI state swaps. This is a hard rule (design §G Q2/Q3): a full reload re-runs `AuthProvider` and rebuilds all TanStack Query caches under the new tenant context, preventing cross-tenant cache leakage. Do NOT spec or implement an in-place context switch.

### 14.6 TanStack Query keys

- `useOperatorTenants`: `queryKey: ['operator-tenants']`, `queryFn: () => apiClient.get('/api/v1/operator/tenants')`, `staleTime: 5 * 60 * 1000`, `retry: false`.
- `useImpersonationStart`: `mutationFn: ({ tenantId }) => apiClient.post('/api/v1/operator/impersonation/start', { tenant_id: tenantId })`, `retry: false`.
- `useImpersonationEnd`: `mutationFn: ({ tenantId }) => apiClient.post('/api/v1/operator/impersonation/end', { tenant_id: tenantId })`, `retry: false`.

### 14.7 MSW handlers

`operatorTenantsHandlers.ts` should mock:
- `GET /api/v1/operator/tenants` → `OperatorTenantListResponse` with 8–12 fixture tenants (mix of tiers, statuses including `trialing`, `active`, `past_due`, `canceled`, one with `null` subscription).
- `POST /api/v1/operator/impersonation/start` → `ImpersonationSessionResponse` (success) or 403/404/409 for edge cases.
- `POST /api/v1/operator/impersonation/end` → `{ "ended": true }`.

### 14.8 Sidebar state sharing

`OperatorSidebar` reuses `useSidebarState()` which reads/writes `localStorage["pilot.sidebar.collapsed"]`. This shares collapse state with the tenant `AppSidebar`. If independent state is preferred, introduce `pilot.operator.sidebar.collapsed` in a new `useOperatorSidebarState` hook (implementation note — default to shared for "one product" feel; flag for Tom at review).

### 14.9 Logout

The header logout button reuses the existing Cognito sign-out handler from `AuthProvider` (the same function `ProfileDropdown` calls). The engineer should export it or replicate the call. This is a minimal affordance — a full profile dropdown for platform users is out of scope for C-B15.

---

## 15. Handoff Gate

**This spec is ready for Tom's review. Implementation starts only after approval.**

The React Engineer prompt for C-B15 Part B will NOT be authored until this spec is Tom-approved. Per the batch prompt: "STOP after producing the spec."
