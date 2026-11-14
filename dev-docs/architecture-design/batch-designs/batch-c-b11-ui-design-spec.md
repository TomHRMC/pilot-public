# C-B11 — Operator Cohort Dashboard UI Design Spec

**Batch**: C-B11 (Part B prerequisite — UI design spec)
**Surface**: Operator Cohort Dashboard — `/operator/cohort`
**Platform**: Web only (`apps/web`)
**Designer**: pilot-web-ui-designer
**Date**: August 7, 2026
**Source design doc**: `batch-c-b11-design.md` §H (Surface Mockup Reference), §I (Component Manifest), §D (API contracts)
**Platform patterns**: `mvp-arch.md` §16.6 (Four-Class Severity), §16.7 (Always-Preview-Before-Send), §16.8 (Optimistic UI with Pending Badges)

---

## 1. Surface Overview

### 1.1 What this is

A **platform-level operator tool** — the first operator-only page in the Pilot web app. It shows all Charter members in a single table with tripwire alerts and provides two operator actions: **Silent Extension** (per-row) and **Cohort Close** (top-level, destructive).

### 1.2 Route & layout scope

- **Route**: `/operator/cohort` — a **standalone route**, NOT under the `(authed)` route group. It has its own minimal layout: no tenant shell, no `AppSidebar`, no tenant-scoped data, no impersonation. The platform shell + impersonation is deferred to C-B15.
- **Layout**: A simple page-level header (title + cohort close button) followed by the cohort table. No sidebar, no tenant selector.
- **Login routing**: After Cognito auth, the frontend calls `GET /api/v1/auth/me`. If `user_type === "platform"`, redirect to `/operator/cohort`. If `user_type === "tenant"`, existing redirect to `/dashboard` applies. This is the only routing change in C-B11.

### 1.3 Who sees it (RBAC)

This surface is **platform-level**, not tenant-scoped. The backend `get_platform_user()` dependency gates all three endpoints. The frontend does NOT use `<RoleGate>` (which is tenant-scoped). Instead:

| Surface element | Backend permission | Platform roles that see it |
|---|---|---|
| Cohort dashboard (read) | `platform_role.permissions.read_all === true` | `owner`, `accountant`, `support` |
| Silent Extension action | `permissions.write` contains `"tenants"` OR `"billing"` | `owner`, `support` |
| Cohort Close action | `permissions.write` contains `"billing"` | `owner` only |

**Frontend visibility rule**: The `Extend` row action and the `Close Cohort` button are conditionally rendered based on the platform user's permissions, fetched from `GET /api/v1/auth/me` (which returns `platform_role_code`). The frontend maps `platform_role_code` → permission set. **Hide-not-disable** for unauthorized actions (per §11 of web-app-design-standards — `disabled` is reserved for genuinely-unavailable-but-visible, not permissions). An `accountant` sees the table read-only with no action buttons. A `support` user sees the table + Extend action but no Close Cohort button.

### 1.4 When it's used

Tom (platform `owner`) uses this daily during the Charter cohort period to monitor activation tripwires (members not creating jobs) and proactively extend free periods before they expire. Cohort Close is a one-time action taken when the Charter cohort is finalized.

---

## 2. Layout — Standalone Page Structure

### 2.1 Page shell

The page is a full-viewport flex column. No `(authed)` layout wrapper — this route renders its own minimal chrome.

```
┌─────────────────────────────────────────────────────────────┐
│ PAGE HEADER (h-16, bg-white, border-b border-neutral-200)   │
│  [logo-icon] Pilot Operator — Charter Cohort   [Close Cohort]│
├─────────────────────────────────────────────────────────────┤
│ CONTENT AREA (flex-1, overflow-auto, bg-neutral-50, p-6)    │
│                                                             │
│  ┌─ Cohort summary strip ─────────────────────────────┐    │
│  │ Charter · 8 / 12 members · Cohort open             │    │
│  └────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─ Cohort table (PilotTable) ───────────────────────┐     │
│  │ Member | Days | Stripe | PM | 10DLC | Cust | Inv │     │
│  │ ...up to 12 rows...                               │     │
│  └───────────────────────────────────────────────────┘     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Page header

- **Container**: `h-16 bg-white border-b border-neutral-200 px-6 flex items-center justify-between sticky top-0 z-30`
- **Left side**: `logo-icon.svg` (24×24, from `apps/web/public/brand/`) + title text "Pilot Operator — Charter Cohort" — `text-h2 font-semibold text-neutral-900`
- **Right side**: `<CloseCohortButton>` (only rendered for `owner` platform role). When cohort is already closed (`cohort_is_active === false`), the button is replaced with a static badge: `bg-neutral-100 text-neutral-500 rounded-md px-3 py-2 text-sm font-medium` with text "Cohort closed" and a `LockClosedIcon` (`w-4 h-4`, outline).

### 2.3 Cohort summary strip

A thin info bar directly below the header, inside the content area padding:

- **Container**: `bg-white rounded-lg border border-neutral-200 px-4 py-3 mb-4 flex items-center gap-6`
- **Content** (left to right):
  - Cohort tier name: `text-sm font-medium text-neutral-900` — e.g., "Charter"
  - Member count: `text-sm text-neutral-500` — e.g., "8 / 12 members" (uses `members.length` / `signup_cap`)
  - Cohort status badge:
    - Open (`cohort_is_active === true`): `bg-margin-50 text-margin-700 rounded-full px-2.5 py-0.5 text-caption font-medium` + `CheckCircleIcon` (`w-4 h-4`, outline) + text "Cohort open"
    - Closed (`cohort_is_active === false`): `bg-neutral-100 text-neutral-500 rounded-full px-2.5 py-0.5 text-caption font-medium` + `LockClosedIcon` (`w-4 h-4`, outline) + text "Cohort closed"

### 2.4 Content area

- **Container**: `flex-1 overflow-auto bg-neutral-50 p-6`
- **Table wrapper**: full width (no `max-w` constraint — this is a table page, per §4 of web-app-design-standards)

### 2.5 Responsive notes

- **1280px+** (primary): Table renders with all 10 columns visible. Column widths sum to ~1100px, comfortable in the content area.
- **1024px**: Table enters horizontal scroll (`overflow-x-auto` is built into `PilotTable`). Summary strip wraps to two lines if needed.
- **768px**: Not a target viewport for this operator tool (operators use desktop). Table scrolls horizontally; no mobile spec.

---

## 3. Table Columns

The table uses `PilotTable` (TanStack Table wrapper). 10 columns. Column sizes are TanStack `columnDef.size` values (treated as proportional flex-weights by PilotTable).

| # | Column header | Data field | Type | Format | Size (px) | Sortable |
|---|---|---|---|---|---|---|
| 1 | Member | `charter_member_number` + `business_name` | string | "#1 — Acme Electric" | 220 | Yes (by member number) |
| 2 | Days left | `days_remaining` | integer | "90" or "—" if null | 90 | Yes |
| 3 | Stripe | `stripe_status` | enum badge | `trialing` / `active` / `paused` | 110 | Yes |
| 4 | Card | `has_payment_method` | boolean | `CreditCardIcon` (yes, `text-neutral-400`) / `MinusCircleIcon` (no, `text-neutral-300`) | 70 | No |
| 5 | 10DLC | `messaging_status` | enum badge | `not_started` / `active` / `pending` / `failed` | 120 | Yes |
| 6 | Customers | `customer_count` | integer | "3" | 100 | Yes |
| 7 | Invoices | `invoice_count` | integer | "2" | 100 | Yes |
| 8 | Last job | `days_since_last_job` | integer\|null | "5d" or "Never" (null) | 100 | Yes |
| 9 | Alert | `alert_level` | enum (red/amber/none) | Icon + text label (color-independent) | 140 | Yes |
| 10 | Actions | — | button | "Extend" link button (per-row) | 100 | No |

### 3.1 Column detail

**Column 1 — Member** (`charter_member_number` + `business_name`):
- Cell: `text-sm text-neutral-900`
- Format: `<span className="font-medium">#{charter_member_number}</span>` + ` — ` + `<span>{business_name}</span>`
- The member number is `font-medium text-neutral-900`; the business name is `text-neutral-700`.

**Column 2 — Days left** (`days_remaining`):
- Cell: `text-sm text-neutral-900 tabular-nums`
- If `days_remaining <= 14`: `text-alert-700 font-medium` (amber text signals the extension window — but paired with the Alert column icon+text, so color is not the only signal)
- If `days_remaining === null`: render "—" in `text-neutral-400`

**Column 3 — Stripe** (`stripe_status`):
- Badge: `inline-flex items-center rounded-full px-2.5 py-0.5 text-caption font-medium`
- `trialing` → `bg-blue-100 text-blue-700` + text "Trialing"
- `active` → `bg-margin-100 text-margin-700` + text "Active"
- `paused` → `bg-neutral-100 text-neutral-500` + text "Paused"
- Unknown/other → `bg-neutral-100 text-neutral-500` + text capitalized status

**Column 4 — Card** (`has_payment_method`):
- `true` → `CreditCardIcon` (`w-4 h-4`, outline, `text-neutral-400`) with `aria-label="Payment method on file"`
- `false` → `MinusCircleIcon` (`w-4 h-4`, outline, `text-neutral-300`) with `aria-label="No payment method"`
- Cell: `text-center` — icon centered in cell. **Hit area**: the icon is decorative (not clickable); no padding needed beyond cell padding.

**Column 5 — 10DLC** (`messaging_status`):
- Badge: `inline-flex items-center rounded-full px-2.5 py-0.5 text-caption font-medium`
- `not_started` → `bg-neutral-100 text-neutral-500` + text "Not started"
- `active` → `bg-margin-100 text-margin-700` + text "Active"
- `pending` → `bg-alert-100 text-alert-700` + text "Pending"
- `failed` → `bg-fault-100 text-fault-600` + text "Failed"

**Column 6 — Customers** (`customer_count`):
- Cell: `text-sm text-neutral-900 tabular-nums text-center`

**Column 7 — Invoices** (`invoice_count`):
- Cell: `text-sm text-neutral-900 tabular-nums text-center`

**Column 8 — Last job** (`days_since_last_job`):
- Cell: `text-sm tabular-nums`
- If integer: `"{n}d"` in `text-neutral-700`
- If `null` (never created a job): "Never" in `text-fault-600 font-medium` (this is the activation tripwire — red text paired with the Alert column, color-independent)
- If `> 7`: `text-fault-600 font-medium` (red text, paired with Alert column icon+text)

**Column 9 — Alert** (`alert_level`):
- See §4 below for full spec. Color-independent: icon + text label + row styling.

**Column 10 — Actions**:
- "Extend" link button — only rendered if the platform user has `write` permission for `"tenants"` or `"billing"` (i.e., `owner` or `support`).
- If the member's `stripe_status !== "trialing"`: the Extend action is **disabled** (genuinely-unavailable — the backend will reject with 409). Disabled state: `text-neutral-400 cursor-not-allowed` with `title="Cannot extend — subscription is not trialing"`.
- If the user lacks permission: the action is **hidden** (hide-not-disable per §11).
- See §5 for the Extend action interaction.

### 3.2 Table header styling

Per `PilotTable`: `bg-neutral-50 border-b border-neutral-200`, header cells `px-4 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide`. Sortable columns show `↕` / `▲` / `▼` indicators.

### 3.3 Row styling

Base row (per PilotTable): `hover:bg-neutral-50 transition-colors`, cells `px-4 py-3`. Alert-level row overrides are applied via a conditional class on the `<tr>` (see §4.3 — the React Engineer passes a `getRowClassName` or wraps rows; PilotTable's current API doesn't expose per-row class, so the engineer will either extend PilotTable with an optional `getRowClassName?: (row: TData) => string` prop or render the table manually for this surface. **Implementation note**: prefer extending PilotTable with `getRowClassName` to keep the shared component as the render path).

---

## 4. Alert-Level Styling (Color-Independent)

The `alert_level` field from the API drives row styling. **Red takes precedence over amber** if both conditions are true. This is the four-class severity pattern (§16.6) reduced to three visible classes (red / amber / none) for this surface.

### 4.1 Alert computation (backend — for reference)

- `"red"` — `days_since_last_job > 7` OR `days_since_last_job === null` (no jobs ever = highest concern)
- `"amber"` — `free_period_ends_at` within 14 days (and not red)
- `"none"` — neither condition

### 4.2 Alert column cell (Column 9)

Each alert level renders an **icon + text label** (color-independent — WCAG 1.4.1):

| Level | Icon (Heroicons 2.0, outline) | Text label | Cell classes |
|---|---|---|---|
| `red` | `ExclamationTriangleIcon` (`w-4 h-4`) | "Activation risk" | `inline-flex items-center gap-1.5 text-fault-600 text-sm font-medium` |
| `amber` | `ClockIcon` (`w-4 h-4`) | "Expiring soon" | `inline-flex items-center gap-1.5 text-alert-700 text-sm font-medium` |
| `none` | `CheckCircleIcon` (`w-4 h-4`) | "Healthy" | `inline-flex items-center gap-1.5 text-margin-600 text-sm` |

The icon has `aria-hidden="true"`; the text label is the accessible name. The cell also has an `aria-label` on the `<td>` for screen readers: e.g., `aria-label="Alert: activation risk"`.

### 4.3 Row-level styling

The `<tr>` gets a left border accent + subtle background tint to make the alert scannable at a glance. This is **redundant** with the icon+text (not color-only):

| Level | Row classes (applied to `<tr>`) |
|---|---|
| `red` | `bg-fault-50 border-l-4 border-fault-500` (overrides `hover:bg-neutral-50` → `hover:bg-fault-100`) |
| `amber` | `bg-alert-50 border-l-4 border-alert-500` (overrides `hover:bg-neutral-50` → `hover:bg-alert-100`) |
| `none` | (default PilotTable row — no override) |

**Note on hover**: The alert-tinted rows keep their tint on hover (slightly darker). The React Engineer implements this by conditionally setting the hover class.

---

## 5. Silent Extension Modal (`ExtendFreePeriodModal`)

### 5.1 Trigger

The "Extend" link button in Column 10 (Actions). Opens a modal for that specific member.

### 5.2 Pattern: Always-Preview-Before-Send (§16.7)

The extension is a one-way-door action (modifies Stripe trial end + writes an override record). Per §16.7, the operator sees a **preview** of the new date + reason before confirming. This surface does NOT use `<MessagePreviewModal>` — that component is locked to communication previews (SMS/email). The extension preview is a **domain-specific modal** that follows the same *preview-then-confirm* philosophy but renders date/reason content, not message content. **Do not attempt to repurpose `MessagePreviewModal`** — its props (`previewData`, `onConfirm`, channel pills) don't fit. Build `ExtendFreePeriodModal` as a new feature-specific component.

### 5.3 Modal layout

```
┌─────────────────────────────────────────────────┐
│ Extend free period — #1 Acme Electric    [X]    │
├─────────────────────────────────────────────────┤
│                                                 │
│  Current free period ends                       │
│  November 4, 2026                               │
│                                                 │
│  New end date *                                 │
│  [ date picker input                  ] 📅      │
│  Must be after the current end date.            │
│                                                 │
│  Reason *                                       │
│  [ textarea                              ]      │
│  [                                       ]      │
│  Required — this is logged to the audit trail.  │
│                                                 │
│  ── Preview ──────────────────────────────────  │
│  ┌───────────────────────────────────────────┐  │
│  │ Preview                                    │  │
│  │ Member:        #1 Acme Electric            │  │
│  │ Current end:   Nov 4, 2026                 │  │
│  │ New end:       Dec 4, 2026 (+30 days)      │  │
│  │ Reason:        Customer needs more time... │  │
│  │ Notification:  None (silent extension)     │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│              [Cancel]  [Extend free period]     │
│                                                 │
└─────────────────────────────────────────────────┘
```

### 5.4 Modal panel specs

- **Overlay**: `fixed inset-0 bg-neutral-900/50 z-50` (per §7 of design-system-reference)
- **Panel**: `bg-white rounded-lg shadow-xl max-w-lg w-full mx-auto mt-16 p-6` (wider than the default `max-w-md` to fit the preview block)
- **Close button**: top-right `XMarkIcon` (`w-5 h-5`, outline) in a 44×44px hit area (`p-2.5 rounded-md hover:bg-neutral-100 focus-visible:ring-2 focus-visible:ring-brand-500`)
- **Title**: `text-h2 font-semibold text-neutral-900` — "Extend free period — #{n} {business_name}"
- **z-index**: `z-50` (modal), overlay `z-50`

### 5.5 Form fields

**Current free period end date** (read-only display):
- Label: `text-sm font-medium text-neutral-700 mb-1` — "Current free period ends"
- Value: `text-sm text-neutral-900` — formatted as "MMMM D, YYYY" (e.g., "November 4, 2026"). Uses `free_period_ends_at` from the member row data.

**New end date** (required):
- Label: `text-sm font-medium text-neutral-700 mb-1` — "New end date" + `*` in `text-fault-600`
- Input: native date picker — `rounded-md border border-neutral-300 px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:border-brand-500 w-full`
- Helper text: `text-xs text-neutral-500 mt-1` — "Must be after the current end date."
- Validation: if the selected date is on or before the current end date, show error text `text-xs text-fault-600 mt-1` — "New date must be after the current end date." and disable the confirm button. (Mirrors backend 422.)
- `aria-describedby` links the helper/error text to the input.

**Reason** (required):
- Label: `text-sm font-medium text-neutral-700 mb-1` — "Reason" + `*` in `text-fault-600`
- Input: `<textarea>` — `rounded-md border border-neutral-300 px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:border-brand-500 w-full min-h-[80px] resize-y`
- Helper text: `text-xs text-neutral-500 mt-1` — "Required — this is logged to the audit trail."
- Validation: if empty on confirm attempt, show error text `text-xs text-fault-600 mt-1` — "Reason is required." and disable confirm.
- `aria-describedby` links helper/error.

### 5.6 Preview block

A bordered panel that updates live as the operator fills in the date + reason. This is the **always-preview-before-send** safeguard — the operator reviews the exact change before committing.

- **Container**: `bg-neutral-50 border border-neutral-200 rounded-md p-4 mt-4`
- **Title**: `text-sm font-medium text-neutral-700 mb-2` — "Preview"
- **Rows** (label-value pairs, `flex justify-between text-sm py-1`):
  - "Member" → `text-neutral-900` — "#1 Acme Electric"
  - "Current end" → `text-neutral-900` — "Nov 4, 2026"
  - "New end" → `text-neutral-900 font-medium` — "Dec 4, 2026 (+30 days)" (the `+N days` delta is computed client-side from the two dates)
  - "Reason" → `text-neutral-700` — the reason text (truncated with `truncate` if long, `title` attribute for full text)
  - "Notification" → `text-neutral-500` — "None (silent extension)" with `BellSlashIcon` (`w-4 h-4`, outline) inline. This reinforces D16 — no customer notification.

### 5.7 Action buttons

- **Container**: `flex justify-end gap-3 mt-6`
- **Cancel** (secondary, safe default): `border border-neutral-300 text-neutral-700 rounded-md px-4 py-2 text-sm font-medium hover:bg-neutral-50 focus-visible:ring-2 focus-visible:ring-brand-500` — closes modal, discards input.
- **Extend free period** (primary CTA): `bg-brand-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-brand-700 focus-visible:ring-2 focus-visible:ring-brand-500 disabled:bg-neutral-300 disabled:cursor-not-allowed` — disabled until both fields are valid.
- **Button order**: Cancel (left), Extend (right). Cancel is the default safe action (per §7 destructive confirm pattern — though this isn't destructive, the cancel-left convention holds).

### 5.8 Optimistic UI (§16.8)

On confirm:
1. The modal closes immediately.
2. The row's `days_remaining` and `free_period_ends_at` are **optimistically updated** in the TanStack Query cache (the new `free_period_ends_at` → recompute `days_remaining`).
3. A `<PendingBadge>` appears next to the member name in Column 1 — `variant="optimistic"` — text "Extending…" for ~2 seconds or until the mutation settles.
4. On success: badge clears, `alert_level` is recomputed client-side (amber may clear if the new date is >14 days out).
5. On error (409 not-trialing, 422 past date, network): badge transitions to `variant="error"`, a `<NotificationBanner>` (severity `error`) appears at the top of the content area with the RFC 7807 detail message, and the row reverts to its previous state. A "Retry" link in the banner re-opens the modal with the previous input.

### 5.9 409 handling (not-trialing)

If the backend returns 409 (subscription not `trialing`), the modal stays open, a `text-fault-600` error message appears below the preview block: "This member's subscription is no longer trialing and cannot be extended." The confirm button is disabled. The operator must close the modal. (This is an edge case — the Extend action is already disabled in the table when `stripe_status !== "trialing"`, but the race condition is handled here.)

---

## 6. Cohort Close Modal (`CloseCohortButton`)

### 6.1 Trigger

The "Close Cohort" button in the page header (right side). Only rendered for platform `owner` role.

### 6.2 Button (header)

- **Classes**: `inline-flex items-center gap-2 bg-fault-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-fault-700 focus-visible:ring-2 focus-visible:ring-fault-500 disabled:bg-neutral-300 disabled:cursor-not-allowed`
- **Icon**: `LockClosedIcon` (`w-4 h-4`, outline) + text "Close Cohort"
- **Disabled state**: disabled when `cohort_is_active === false` (already closed) or when the close mutation is in-flight. `title="Cohort is already closed"` when disabled.
- **Hit area**: the button is 44px tall (py-2 + text + border = ~36px; bump to `py-2.5` if needed to hit 44px min target).

### 6.3 Confirmation modal

Destructive confirm pattern (per §7 of design-system-reference):

```
┌─────────────────────────────────────────────────┐
│ Close Charter cohort?                       [X] │
├─────────────────────────────────────────────────┤
│                                                 │
│  This will archive the Charter price and close  │
│  the cohort to new signups. Existing members    │
│  keep their locked rate.                        │
│                                                 │
│  This cannot be undone.                         │
│                                                 │
│              [Cancel]  [Close Cohort]           │
│                                                 │
└─────────────────────────────────────────────────┘
```

- **Overlay**: `fixed inset-0 bg-neutral-900/50 z-50`
- **Panel**: `bg-white rounded-lg shadow-xl max-w-md w-full mx-auto mt-16 p-6`
- **Title**: `text-h2 font-semibold text-neutral-900` — "Close Charter cohort?"
- **Body**: `text-sm text-neutral-700 mt-2` — "This will archive the Charter price and close the cohort to new signups. Existing members keep their locked rate."
- **Warning line**: `text-sm text-fault-600 font-medium mt-2` — "This cannot be undone." with `ExclamationTriangleIcon` (`w-4 h-4`, outline) inline.
- **Close button**: `XMarkIcon` top-right, 44×44px hit area.
- **Action buttons** (`flex justify-end gap-3 mt-6`):
  - **Cancel** (default, safe): `border border-neutral-300 text-neutral-700 rounded-md px-4 py-2 text-sm font-medium hover:bg-neutral-50 focus-visible:ring-2 focus-visible:ring-brand-500`
  - **Close Cohort** (destructive): `bg-fault-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-fault-700 focus-visible:ring-2 focus-visible:ring-fault-500 disabled:bg-neutral-300 disabled:cursor-not-allowed` — disabled while mutation is in-flight.

### 6.4 Post-close behavior

On success:
1. Modal closes.
2. The cohort summary strip updates: status badge → "Cohort closed" (`bg-neutral-100 text-neutral-500` + `LockClosedIcon`).
3. The "Close Cohort" button in the header is replaced with the static "Cohort closed" badge (§2.2).
4. A `<NotificationBanner>` (severity `success`) appears: "Charter cohort closed. {N} members retain their locked rate."
5. The table remains visible (existing members keep their rate — the table still shows them). No rows are removed.

### 6.5 409 handling (already closed)

If the backend returns 409 (cohort already closed), the modal closes and a `warning` severity `NotificationBanner` appears: "The cohort was already closed." The UI state syncs to closed.

---

## 7. Empty / Loading / Error States

### 7.1 Loading state (`isPending`)

While `GET /api/v1/operator/cohort` is in-flight (initial load):

- The content area renders a **skeleton** matching the table layout (per §11 of web-app-design-standards — skeletons over spinners for content-shaped loading).
- Skeleton: `PilotTable` container with 12 placeholder rows. Each row is `h-12 bg-neutral-100 animate-pulse rounded`. The header row renders normally (column labels are known).
- The cohort summary strip renders as a skeleton: `h-12 bg-neutral-100 animate-pulse rounded-lg`.
- The page header renders normally (title + Close Cohort button — the button is disabled until data loads, since `cohort_is_active` is unknown).
- **Reduced motion**: `@media (prefers-reduced-motion: reduce)` → `animate-pulse` becomes `bg-neutral-100` (static, no pulse).

### 7.2 Empty state (no Charter members)

When `members.length === 0`:

- Use `<EmptyState>` from `@pilot/ui/states` with `type="no-data"`.
- Override `title`: "No Charter members yet"
- Override `description`: "Members will appear here when they sign up."
- No CTA (this is a monitoring page — the operator doesn't create members here).
- The cohort summary strip still renders: "Charter · 0 / 12 members · Cohort open".
- The Close Cohort button remains visible (owner can close an empty cohort, though unlikely).

### 7.3 Error state (`isError`)

When the GET fails:

- Use `<ErrorState>` from `@pilot/ui/states` with `type="server"`.
- `onRetry`: calls `queryClient.invalidateQueries({ queryKey: ['cohort-overview'] })`.
- The page header + summary strip render normally (the error is in the table area only).

### 7.4 Mutation error states

- **Extension failure**: see §5.8 — `NotificationBanner` (error) + row revert + retry link.
- **Close failure**: `NotificationBanner` (error) — "Failed to close cohort. Please try again." with retry.

---

## 8. Interaction States & Motion

### 8.1 Extend link button (Column 10)

| State | Classes |
|---|---|
| Default | `text-brand-600 text-sm font-medium hover:text-brand-700 focus-visible:ring-2 focus-visible:ring-brand-500 rounded-md px-1 py-0.5` |
| Hover | `text-brand-700 underline` |
| Focus-visible | `ring-2 ring-brand-500` |
| Active | `text-brand-800` |
| Disabled (not trialing) | `text-neutral-400 cursor-not-allowed` + `title="Cannot extend — subscription is not trialing"` |
| Hidden (no permission) | not rendered |

**Hit area**: The link text alone is too small. Wrap in a `px-1 py-0.5` padded area → ~24px tall. Acceptable (meets WCAG 2.5.8 minimum).

### 8.2 Close Cohort button (header)

| State | Classes |
|---|---|
| Default | `bg-fault-600 text-white hover:bg-fault-700 focus-visible:ring-2 focus-visible:ring-fault-500` |
| Hover | `bg-fault-700` |
| Focus-visible | `ring-2 ring-fault-500 ring-offset-2` |
| Active | `bg-fault-800` |
| Disabled (already closed / in-flight) | `bg-neutral-300 text-neutral-500 cursor-not-allowed` |

### 8.3 Modal close button (`XMarkIcon`)

| State | Classes |
|---|---|
| Default | `text-neutral-400 hover:text-neutral-600` |
| Hover | `text-neutral-600 bg-neutral-100` |
| Focus-visible | `ring-2 ring-brand-500` |
| Active | `text-neutral-900` |

Hit area: `p-2.5 rounded-md` → 44×44px.

### 8.4 Row hover

- Default rows: `hover:bg-neutral-50 transition-colors` (built into PilotTable)
- Red alert rows: `hover:bg-fault-100 transition-colors`
- Amber alert rows: `hover:bg-alert-100 transition-colors`

### 8.5 Animation spec

| Element | Transition | Reduced motion |
|---|---|---|
| Row hover | `transition-colors 150ms ease-in-out` | no transition (instant) |
| Modal open/close | `opacity 200ms ease-out` (overlay fade) + `transform 200ms ease-out` (panel scale from 0.95→1.0) | instant (no fade/scale) |
| Skeleton pulse | `animate-pulse` (Tailwind default 2s) | static `bg-neutral-100` |
| PendingBadge | `animate-pulse` while pending | static |
| Optimistic row update | no animation (instant value swap) | n/a |

All transitions: `@media (prefers-reduced-motion: reduce) → transition: none`.

---

## 9. Accessibility Notes (WCAG 2.2 AA)

### 9.1 Color-independent status

- **Alert column** (§4.2): every alert level pairs a color token with an icon (`ExclamationTriangleIcon` / `ClockIcon` / `CheckCircleIcon`) AND a text label ("Activation risk" / "Expiring soon" / "Healthy"). Color is never the only signal. Passes WCAG 1.4.1.
- **Row tinting** (§4.3): the left-border accent + background tint is **redundant** with the icon+text in Column 9. A user who cannot perceive color still reads the alert from the icon+text. Passes WCAG 1.4.1.
- **Days left column** (§3.1 col 2): amber text for `<=14` days is paired with the Alert column. Not color-only.
- **Last job column** (§3.1 col 8): red text for `>7` or "Never" is paired with the Alert column. Not color-only.
- **Stripe / 10DLC badges**: all badges include text labels (not color-only).

### 9.2 Contrast ratios

All token pairings used are pre-validated per §10 of web-app-design-standards:
- `text-neutral-900 on bg-white` — ≥ 4.5:1 ✅
- `text-fault-600 on bg-fault-50` — ≥ 4.5:1 ✅
- `text-alert-700 on bg-alert-50` — ≥ 4.5:1 ✅
- `text-margin-600 on bg-white` — ≥ 4.5:1 ✅
- `text-brand-600 on bg-white` (Extend link) — ≥ 4.5:1 ✅
- Badge text on badge bg (e.g., `text-blue-700 on bg-blue-100`) — ≥ 4.5:1 ✅

### 9.3 Target sizes

| Element | Target size | Meets SC 2.5.8 (≥24×24)? |
|---|---|---|
| Extend link button | ~24×24px (padded) | ✅ (minimum) |
| Close Cohort button | ~44×36px | ✅ |
| Modal close `XMarkIcon` | 44×44px (`p-2.5`) | ✅ (preferred) |
| Sort indicator (header) | full `<th>` cell (clickable) | ✅ |
| Cancel / Confirm buttons | ~44×36px | ✅ |

### 9.4 Focus order & focus-visible

- **Page load**: focus moves to the page header (H1). The content area is next in tab order.
- **Table**: the table is not interactive row-by-row (no row click). The only interactive elements in the table are the Extend link buttons. Tab order: header → summary strip → first Extend button → second → ... → Close Cohort button.
- **`focus-visible`** (not `focus`): all interactive elements use `focus-visible:ring-2 focus-visible:ring-brand-500` (or `ring-fault-500` for destructive). Keyboard users get a ring; mouse users don't see a persistent ring on click.
- **Modal focus trap**: when a modal opens, focus moves to the first focusable element (the date input for Extend; the Cancel button for Close). Focus is trapped within the modal (Tab cycles through modal elements only). On close, focus returns to the triggering element (the Extend link or the Close Cohort button). The engineer uses a focus-trap utility (e.g., `focus-trap-react` or the pattern from existing modals).
- **Focus not obscured** (SC 2.4.11): the page header is `sticky top-0 z-30`. When a modal opens, the overlay is `z-50` — above the header. Modal content is scrolled into view if needed. No `scroll-margin-top` issue since the header is only `h-16` and modals are centered with `mt-16`.

### 9.5 Form fields (Extend modal)

- Every field has a visible `<label>` above it (§5 form pattern). Placeholder-as-label is banned.
- Error text is `text-fault-600` AND linked via `aria-describedby` to the input.
- The date picker is a native `<input type="date">` — accessible, supports keyboard entry, paste allowed.
- The reason textarea has a visible label, helper text, and error text all `aria-describedby`-linked.

### 9.6 Screen reader announcements

- The alert column `<td>` has `aria-label="Alert: {level label}"` (e.g., "Alert: activation risk").
- The card column icon has `aria-label` ("Payment method on file" / "No payment method").
- The PendingBadge (§5.8) uses `aria-live="polite"` to announce "Extending…" and then "Extended" or "Extension failed".
- The NotificationBanner uses `role="alert"` (error) or `role="status"` (success) per its existing implementation.

### 9.7 Modal dismiss

- `Escape` key closes the modal (same as Cancel).
- Clicking the overlay closes the modal (same as Cancel).
- For the Close Cohort modal: dismissing via Escape/overlay click is safe (no data lost — it's a confirmation, not an in-progress action).

---

## 10. Token Manifest (Zero Hex Codes)

Every color in this spec uses `pilotPreset` token names. The React Engineer must not hardcode any hex value.

| Token | Used for |
|---|---|
| `bg-neutral-50` | Page background, table header bg, skeleton base |
| `bg-white` | Header, summary strip, modal panel, table container |
| `bg-neutral-100` | Badges (void/paused/not-started), skeleton static, disabled button |
| `bg-neutral-900/50` | Modal overlay |
| `bg-brand-600` | Primary CTA (Extend confirm) |
| `bg-brand-700` | Primary CTA hover |
| `bg-fault-50` | Red alert row background |
| `bg-fault-100` | Red alert row hover |
| `bg-fault-600` | Destructive CTA (Close Cohort), red alert border |
| `bg-fault-700` | Destructive CTA hover |
| `bg-alert-50` | Amber alert row background |
| `bg-alert-100` | Amber alert row hover, pending badge bg, alert badge bg |
| `bg-alert-500` | Amber alert border |
| `bg-margin-50` | Success banner bg, cohort-open badge bg |
| `bg-margin-100` | Active badge bg (Stripe/10DLC) |
| `bg-blue-100` | Trialing badge bg |
| `text-neutral-900` | Primary text, member name, modal title |
| `text-neutral-700` | Secondary text, labels, body text |
| `text-neutral-600` | Modal close hover |
| `text-neutral-500` | Tertiary text, helper text, header labels, disabled text |
| `text-neutral-400` | Sort indicator, card icon (yes), modal close default, disabled link |
| `text-neutral-300` | Card icon (no) |
| `text-brand-600` | Extend link |
| `text-brand-700` | Extend link hover |
| `text-brand-800` | Extend link active |
| `text-fault-600` | Error text, red alert text, "Never" text, destructive warning |
| `text-alert-700` | Amber alert text, days-left amber text |
| `text-margin-600` | Healthy alert text |
| `text-margin-700` | Active badge text, cohort-open badge text |
| `text-blue-700` | Trialing badge text |
| `text-white` | Button text (on brand/fault bg) |
| `border-neutral-200` | Table border, summary strip border, modal preview border |
| `border-neutral-300` | Input borders, secondary button border |
| `border-neutral-100` | Table row divider |
| `border-fault-500` | Red alert left border |
| `border-alert-500` | Amber alert left border |
| `ring-brand-500` | Focus-visible ring (primary actions, inputs) |
| `ring-fault-500` | Focus-visible ring (destructive actions) |
| `shadow-sm` | Summary strip |
| `shadow-xl` | Modal panel |

---

## 11. Icon Inventory (Heroicons 2.0)

All icons are [Heroicons 2.0](https://heroicons.com/). Outline variant unless noted.

| Icon | Variant | Size | Used in |
|---|---|---|---|
| `ExclamationTriangleIcon` | outline | `w-4 h-4` | Alert column (red), Close modal warning |
| `ClockIcon` | outline | `w-4 h-4` | Alert column (amber) |
| `CheckCircleIcon` | outline | `w-4 h-4` | Alert column (none), cohort-open badge |
| `LockClosedIcon` | outline | `w-4 h-4` | Cohort-closed badge, Close Cohort button |
| `XMarkIcon` | outline | `w-5 h-5` | Modal close button |
| `CreditCardIcon` | outline | `w-4 h-4` | Card column (has payment method) |
| `MinusCircleIcon` | outline | `w-4 h-4` | Card column (no payment method) |
| `BellSlashIcon` | outline | `w-4 h-4` | Extend modal preview (silent extension) |

No emoji. No custom SVG required.

---

## 12. Component Manifest

Reconciled with design doc §I. No orphan components. All new components are feature-specific (operator domain) → placed in `apps/web/src/components/operator/cohort/`.

| Component | Path | Status | Description |
|---|---|---|---|
| `CohortDashboardPage` | `apps/web/src/app/operator/cohort/page.tsx` | NEW | Thin route — server component that renders `<CohortDashboardClient>`. Route is NOT under `(authed)`. |
| `CohortDashboardClient` | `apps/web/src/components/operator/cohort/CohortDashboardClient.tsx` | NEW | Orchestrator — calls `useCohortOverview`, renders header + summary strip + table + modals. Manages modal open state. |
| `CohortMemberRow` | `apps/web/src/components/operator/cohort/CohortMemberRow.tsx` | NEW | Not a separate component — the row is rendered via TanStack Table `columnDef.cell` functions. **Reconciled**: the design doc lists this as a component, but since we use `PilotTable` (TanStack), rows are cell renderers, not a row component. The engineer may extract a `CohortMemberRow` helper for cell rendering if it improves readability, but it is not a separate rendered component. |
| `ExtendFreePeriodModal` | `apps/web/src/components/operator/cohort/ExtendFreePeriodModal.tsx` | NEW | Date picker + reason + preview block + confirm/cancel. Follows always-preview-before-send (§16.7). Does NOT use `MessagePreviewModal` (domain-specific). |
| `CloseCohortButton` | `apps/web/src/components/operator/cohort/CloseCohortButton.tsx` | NEW | Header button + confirmation modal. Destructive confirm pattern. |
| `useCohortOverview` | `apps/web/src/features/operator/hooks/useCohortOverview.ts` | NEW | TQ v5 query hook — `GET /api/v1/operator/cohort`. Query key: `['cohort-overview']`. |
| `useExtendFreePeriod` | `apps/web/src/features/operator/hooks/useExtendFreePeriod.ts` | NEW | TQ v5 mutation — `POST /api/v1/operator/cohort/{tenant_id}/extend`. Optimistic update (§16.8) on `['cohort-overview']` cache. |
| `useCloseCohort` | `apps/web/src/features/operator/hooks/useCloseCohort.ts` | NEW | TQ v5 mutation — `POST /api/v1/operator/cohort/close`. Invalidates `['cohort-overview']` on success. |
| `cohortDashboardHandlers` | `apps/web/src/mocks/handlers/cohortDashboardHandlers.ts` | NEW | MSW handlers for 3 endpoints (GET cohort, POST extend, POST close). |
| `PilotTable` | `apps/web/src/components/PilotTable.tsx` | MODIFIED | Add optional `getRowClassName?: (row: TData) => string` prop to support alert-level row styling. Backward-compatible (optional prop). |

### 12.1 Shared components consumed (no changes)

| Component | Import | Used for |
|---|---|---|
| `PilotTable` | `@/components/PilotTable` | Table rendering |
| `EmptyState` | `@pilot/ui/states` | Empty state (no members) |
| `ErrorState` | `@pilot/ui/states` | Error state (GET failure) |
| `LoadingState` | `@pilot/ui/states` | Not used directly — skeleton is custom (§7.1). Available if engineer prefers. |
| `NotificationBanner` | `@pilot/ui` | Mutation success/error banners |
| `PendingBadge` | `@pilot/ui` | Optimistic "Extending…" badge (§5.8) |

### 12.2 Components NOT used (and why)

| Component | Why not |
|---|---|
| `MessagePreviewModal` | Locked to communication previews (SMS/email). Extension preview is date/reason content — domain-specific modal built instead. |
| `RoleGate` | Tenant-scoped RBAC. This is a platform-level surface — visibility is determined by `platform_role_code` from `GET /api/v1/auth/me`, not `<RoleGate>`. |
| `PilotPaginator` | Max 12 rows — no pagination needed. |
| `HelpAnchor` | Operator-only internal tool. Help system is for tenant users. Not in scope. |

---

## 13. Implementation Notes

### 13.1 Route placement

The route is at `apps/web/src/app/operator/cohort/page.tsx` — a **new top-level route segment** `operator/`, NOT under `(authed)/`. This is critical: the `(authed)` layout renders `AppSidebar` + tenant shell, which this surface must not have. The `operator/` segment has no layout file (or a minimal one if needed for auth gating).

**Auth gating**: The page must still require authentication. Since it's not under `(authed)`, the engineer wraps the page content in `<RequireAuth>` (from `@pilot/ui/auth`) directly, or creates a minimal `operator/layout.tsx` that does so. The `usePostLoginRedirect` hook (`hooks/usePostLoginRedirect.ts`) handles the `GET /api/v1/auth/me` → redirect logic.

### 13.2 Platform user permission check

The frontend needs to know the platform user's permissions to show/hide the Extend and Close Cohort actions. Source: `GET /api/v1/auth/me` returns `platform_role_code`. The frontend maps:

| `platform_role_code` | `read_all` | `write` | Sees |
|---|---|---|---|
| `owner` | true | `["tenants","users","suppliers","billing","jwks","plans","notifications"]` | Table + Extend + Close Cohort |
| `support` | true | `["tenants","users","billing","notifications"]` | Table + Extend (no Close) |
| `accountant` | true | `[]` | Table only (read-only) |

The engineer should fetch this once (via `useAuth` or a dedicated `useAuthMe` hook) and pass the permission flags down to `CohortDashboardClient`. **Hide-not-disable** for unauthorized actions.

### 13.3 TanStack Query keys

- `useCohortOverview`: `queryKey: ['cohort-overview']`, `queryFn: () => api.get('/api/v1/operator/cohort')`
- `useExtendFreePeriod`: `mutationFn: ({ tenantId, newEnd, reason }) => api.post(...)`, `onMutate` optimistically updates `['cohort-overview']` cache (§16.8), `onError` rolls back, `onSuccess` invalidates.
- `useCloseCohort`: `mutationFn: () => api.post('/api/v1/operator/cohort/close')`, `onSuccess` invalidates `['cohort-overview']`.

### 13.4 Date formatting

- `free_period_ends_at` is an ISO 8601 UTC timestamp. Display as "MMMM D, YYYY" (e.g., "November 4, 2026") using `Intl.DateTimeFormat('en-US', { month: 'long', day: 'numeric', year: 'numeric' })`.
- `days_remaining` is an integer from the backend (computed server-side via `safe_now_utc()`). Display as-is.
- The date picker (`<input type="date">`) works with `YYYY-MM-DD` values. Convert the ISO timestamp to `YYYY-MM-DD` for the `min` attribute (the current end date) and for the value.

### 13.5 Optimistic update detail (§16.8)

In `useExtendFreePeriod`'s `onMutate`:
1. Cancel outgoing queries for `['cohort-overview']`.
2. Snapshot the current cache (previous data).
3. Update the cache: find the member by `tenant_id`, set `free_period_ends_at = newEnd`, recompute `days_remaining` = `ceil((newEnd - now) / 86400000)`, recompute `alert_level` (amber if `days_remaining <= 14`, else none — red can't be cleared by extension since it's about jobs, not dates).
4. Return `{ previousData }` for rollback.

`onError`: rollback to `previousData`. Show `NotificationBanner` (error).

`onSuccess`: invalidate `['cohort-overview']` to get the server-confirmed state.

### 13.6 MSW handlers

The `cohortDashboardHandlers.ts` file should mock:
- `GET /api/v1/operator/cohort` → returns a `CohortOverviewResponse` with 8-12 fixture members (mix of alert levels, stripe statuses, messaging statuses).
- `POST /api/v1/operator/cohort/:tenantId/extend` → returns `ExtendFreePeriodResponse` (success) or 409/422 for edge cases.
- `POST /api/v1/operator/cohort/close` → returns `CloseCohortResponse` or 409.

### 13.7 PilotTable extension

Add `getRowClassName?: (row: TData) => string` to `PilotTableProps`. In the `<tr>` render, merge the returned class with the existing `hover:bg-neutral-50 transition-colors`. The alert-level row classes (§4.3) override the default hover. The engineer must ensure the override works (Tailwind class order — later classes win for same-property; use `!` important if needed, or structure the conditional to not include `hover:bg-neutral-50` when an alert class is present).

---

## 14. Handoff Gate

**This spec is ready for Tom's review. Implementation starts only after approval.**

The React Engineer prompt for C-B11 Part B will NOT be authored until this spec is Tom-approved. Per the batch prompt: "STOP after producing the spec."
