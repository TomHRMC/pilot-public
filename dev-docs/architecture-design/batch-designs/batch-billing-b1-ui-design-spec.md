# UI Design Spec: BILLING-B1 (Part B) — Payment Schedule Builder

**Batch**: BILLING-B1 (Part B — Design Phase)
**Surface**: Payment Schedule Builder (contractor-facing draw editor + reconciliation + activate + per-draw invoice generation)
**Platform**: Web (`apps/web`) — authenticated internal surface
**Mode**: Pilot Web UI Designer
**Author**: Pilot Web UI Designer
**Date**: 2026-07-28
**Status**: Ready for Tom review
**Source prompt**: `dev-docs/implementation-prompts/fe-be-mob-batch-prompts/batch-billing-b1-web-ui-designer-prompt.md`
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-billing-b1-design.md` (§D endpoints, §F integrity rules, §G resolved decisions, §H frontend scope)
**Backend status**: Part A (Python) **COMPLETE 2026-07-28** — migration `2dba31137096`; 9 endpoints + `/test` twins live under `/api/v1/payment-schedules`; contract frozen in `backend/openapi_schema_map.md`.

> **Design rule**: All colors use `pilotPreset` token names — zero hex codes. All icons are exact Heroicons 2.0 names. No emoji in production UI. Money is integer cents (÷100, USD). Reconciliation math is backend-owned — the UI **displays** `scheduled_total_cents` / `residual_cents` / `resolved_amount_cents`; it never recomputes them.

---

## 1. Surface Overview

### 1.1 What this is

The **Payment Schedule Builder** is the contractor-facing surface where an owner/office user structures the draws (deposit + progress + final) against a locked `contract_total_cents`, watches live reconciliation, activates the schedule, and generates each draw's `progress` invoice when its milestone is reached. A deposit is modeled as the `sequence=1` draw — **no separate deposit component** (§G).

### 1.2 Placement

New feature domain: **`apps/web/src/features/billing/`**.

Rationale: payment schedules are a distinct billing domain (parent `payment_schedule` + child `payment_schedule_line` tables, their own 9 endpoints, their own hooks). Keeping them in `features/billing/` isolates the new batch's files and avoids bloating `features/invoices/`. The builder **cross-imports** the feature-local `SendInvoicePreviewModal` sibling and links to `InvoiceDetailPage` — cross-feature imports are permitted (both are app-feature, not shared).

### 1.3 Routes (thin server components — Rule 9)

| Route | File | Purpose |
|---|---|---|
| `/billing/payment-schedules/new` | `apps/web/src/app/(authed)/billing/payment-schedules/new/page.tsx` | Create a new schedule. Reads `?quote_id=` or `?job_id=` query param, seeds `contract_total_cents` from the quote/job total. |
| `/billing/payment-schedules/[id]` | `apps/web/src/app/(authed)/billing/payment-schedules/[id]/page.tsx` | Edit (draft) / view (active/completed/cancelled) an existing schedule. |

Each route is a thin server component: `return <PaymentScheduleBuilder scheduleId={params.id} />` (detail) or `<PaymentScheduleBuilder mode="new" quoteId={...} jobId={...} />` (new). No `"use client"`, no data fetching in the route.

### 1.4 Entry & return navigation

- **Entry**: a **"Set up payment schedule"** action button on the quote detail page and job detail page (owner/office only — `<RoleGate permission="invoices.create">`; techs hidden). When a quote/job has no schedule, the action links to `/billing/payment-schedules/new?quote_id={id}` (or `?job_id={id}`). When a schedule already exists, the action links to `/billing/payment-schedules/[id]`.
- **Return**: the builder breadcrumb links back to the originating quote (`/quotes/{quote_id}`) or job (`/jobs/{job_id}`). The top-left Cancel button calls `router.back()`.
- **Draw invoice exit**: a generated draw's `invoice_id` links to `/invoices/{invoice_id}` (the existing `InvoiceDetailPage`).

### 1.5 RBAC

| Surface / action | Permission | Roles | Treatment |
|---|---|---|---|
| See the builder at all | `invoices.create` | owner, office_staff | `<RoleGate permission="invoices.create">` — **hide-not-disable**; techs never see the builder or the "Set up payment schedule" entry action |
| Create schedule + generate draw invoice | `invoices.create` | owner, office_staff | `<RoleGate>` |
| **Edit/activate/delete draws (draft only)** | `invoices.update` | **owner only** | `<RoleGate permission="invoices.update">` around the draft editor + Activate |

> ✅ **PERMISSIONS RESOLVED (Tom, 2026-07-28; ADR-0010).** Invoice **editing** (`invoices.update`) is **owner-only** by policy — office_staff is read-mostly (support/CRM: create + view, no editing), the future `accountant` role is read-only, techs are excluded. This **already matches the live backend seed exactly** (verified via `postgres-local` MCP): `owner` = `["*"]` (grants `invoices.update`), `office_staff` = `invoices.create` + `invoices.view` (**no** update), `technician` = none. **Therefore no backend change, no migration, and no separate batch are needed.** The only real gap was the **frontend** registry: `permissions.ts` defines `invoices.create` (line 49) but not `invoices.update`, so `<RoleGate permission="invoices.update">` denied everyone including owner. **This one-line frontend fix is folded into the BILLING-B1 Part B React prompt** (not deferred): add `"invoices.update"` to the `PermissionKey` union and to the **`owner`** role set only (NOT office_staff, NOT tech). The React Engineer then gates edit/activate with `<RoleGate permission="invoices.update">` directly — no temporary `invoices.create` gate, no `// TODO`. Do **not** design a disabled-for-techs/office state — non-owners are hidden via `<RoleGate>`. Note: `backend/api/schemas/roles.py` is request/response schemas only — its permission arrays are Swagger examples with zero runtime effect, so it needs no edit. The FE `operator`↔BE `accountant` and FE `tech`↔BE `technician` role-vocabulary reconciliation is a separate P2 RBAC-hardening item (ADR-0010), out of scope here.

### 1.6 Shell layout

Matches the `InvoiceBuilderPage` sibling shell exactly:

```
┌─────────────────────────────────────────────────────────────┐
│ AuthedLayout (h-12 header + 256px sidebar — unchanged)      │
├──────────────────────────────────────────────────────────────┤
│ CONTENT AREA (bg-neutral-50, overflow-auto, px-6 py-6)      │
│                                                              │
│  ┌─ max-w-5xl mx-auto ──────────────────────────────────┐   │
│  │ Breadcrumb  [Quote/Job] / Payment Schedule           │   │
│  │                                  [Cancel] [Activate →]│   │
│  │ H1: Payment Schedule                                  │   │
│  │ Schedule status badge · Contract total · Basis default│   │
│  │                                                        │   │
│  │ ┌─ Draw editor card (bg-white …) ──────────────────┐ │   │
│  │ │ DrawRow × N  (table)                              │ │   │
│  │ │ + Add draw                                        │ │   │
│  │ └────────────────────────────────────────────────────┘ │   │
│  │ ┌─ ReconciliationBar ────────────────────────────────┐ │   │
│  │ │ scheduled vs contract · residual banner (3 states) │ │   │
│  │ └────────────────────────────────────────────────────┘ │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                │
│  Fixed action footer (bg-white border-t, z-40)               │
│  [Cancel]  [Save draft]  [Activate schedule →]                │
└──────────────────────────────────────────────────────────────┘
```

- Container: `max-w-5xl mx-auto p-6 pb-24` (wider than the `max-w-4xl` invoice builder because the draw table has more columns).
- Card sections: `bg-white border border-neutral-200 rounded-lg shadow-sm p-6 mb-4`.
- Section H2: `text-base font-semibold text-neutral-800 mb-3`.
- Page H1: `text-h1 font-semibold text-neutral-900 mb-1` (per typography scale §7; the sibling uses `text-2xl font-semibold` — prefer the token class).
- Breadcrumb: `text-sm text-neutral-500`, active crumb `text-neutral-900 font-medium`.
- Fixed action footer: `fixed bottom-0 left-0 right-0 bg-white border-t border-neutral-200 px-6 py-4 flex items-center justify-end gap-3 z-40`.

---

## 2. State A — Empty (no schedule yet)

### 2.1 When

The quote/job is billed line-item today; `GET /api/v1/payment-schedules?quote_id=` / `?job_id=` returns an empty list (no schedule exists). Rendered inside the builder route when `mode="new"` and no schedule is found, OR as an inline panel on the quote/job detail page.

### 2.2 Component

Compose `<FirstTimeUserState>` from `@pilot/ui/states` (FE-B1 export, confirmed in `index.ts`). Do **not** build a new empty-state component.

### 2.3 Pixel spec

- Container: `bg-white border border-neutral-200 rounded-lg shadow-sm p-10 text-center`, centered in the `max-w-5xl` shell.
- Illustration slot: `<FirstTimeUserState>` `illustration` prop — use the `CurrencyDollarIcon` (Heroicons outline, `w-12 h-12 text-brand-500`) as the leading visual (custom SVG not required; Heroicons suffices).
- Title: `text-h2 font-semibold text-neutral-900 mt-4` — "Set up a payment schedule".
- Body: `text-body text-neutral-500 mt-2 max-w-md mx-auto` — "Break this job into draws — a deposit, progress payments, and a final payment. Each draw becomes its own invoice when its milestone is reached. The draws must sum to the contract total before you can activate the schedule."
- Primary CTA: solid button `bg-brand-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-brand-700` with `PlusIcon` (Heroicons solid, `w-4 h-4`) + label "Set up payment schedule". Min target 44×44px (the `px-4 py-2` button exceeds this).
- Secondary info row below CTA: `text-caption text-neutral-500 mt-3` — "Contract total will be seeded from the {quote/job} total: **{formatCents(total)}**." (the seeded `contract_total_cents` preview).

### 2.4 Interaction states (CTA)

| State | Spec |
|---|---|
| default | `bg-brand-600 text-white` |
| hover | `hover:bg-brand-700` |
| focus-visible | `focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2` |
| active | `active:bg-brand-800` |
| disabled | n/a — RBAC hides, not disables |

### 2.5 Data state

Empty = State A. The `isPending` skeleton (§6) precedes it; `isError` (§6) replaces it on fetch failure.

---

## 3. State B — Draft Builder (fully editable)

The builder proper. All structural editing lives here; once activated the structure locks (§G). This section specs the draw editor table, the reconciliation bar, add-draw, per-row remove, and the Activate action.

### 3.1 Schedule header card

A read-mostly summary card above the draw table:

- Card: `bg-white border border-neutral-200 rounded-lg shadow-sm p-6 mb-4`.
- Row 1 (flex, `items-center justify-between`):
  - Left: H2 `text-base font-semibold text-neutral-800` "Payment Schedule" + schedule status badge (see §3.2).
  - Right: contract total readout — `text-sm text-neutral-500` "Contract total" + `text-h3 font-semibold text-neutral-900` `{formatCents(contract_total_cents)}`.
- Row 2 (flex, `items-center gap-6 mt-3 text-sm`):
  - Basis default label: `text-neutral-500` "Default basis:" + `text-neutral-900 font-medium` `{basis_default === 'percent' ? 'Percent' : 'Fixed amount'}`. Editable inline via a small segmented control while `status='draft'` (see §3.3).
  - Origin: `text-neutral-500` "From:" + link `text-brand-600 hover:text-brand-700 hover:underline` to the quote/job.
  - Customer/Site: `text-neutral-500` "{customer_name} · {site_label}".

### 3.2 Schedule status badge (text + token, never color-only)

| `status` | Label | Token classes |
|---|---|---|
| `draft` | Draft | `bg-neutral-100 text-neutral-700` |
| `active` | Active | `bg-blue-100 text-blue-700` |
| `completed` | Completed | `bg-margin-100 text-margin-700` |
| `cancelled` | Cancelled | `bg-fault-100 text-fault-500` |

Badge shell: `inline-flex items-center rounded-full px-2.5 py-0.5 text-caption font-medium`. Each badge pairs its color with the text label above (WCAG 1.4.1).

### 3.3 Basis-default segmented control (draft only)

Mirrors the `InvoiceBuilderPage` billing-mode toggle exactly:

- Shell: `bg-neutral-100 rounded-md p-1 inline-flex`.
- Active segment: `bg-white shadow-sm rounded px-3 py-1 text-sm font-medium text-neutral-900`.
- Inactive segment: `px-3 py-1 text-sm font-medium text-neutral-500 hover:text-neutral-700`.
- Segments: "Percent" (`basis_default='percent'`) | "Fixed amount" (`basis_default='fixed_amount'`).
- On change → `useUpdateSchedule` (PATCH schedule header, draft only). A 409 (schedule no longer draft) routes to `useStalenessRetry` + `<StalenessRefreshDialog>` (§16.3).
- Hidden when `status !== 'draft'` (read-only shows the label only).

### 3.4 Draw editor table

A `<table>` mirroring `InvoiceLineItemsTable` rhythm: `rounded-md border border-neutral-200 overflow-hidden`, `thead bg-neutral-50`, `divide-y divide-neutral-100`, cells `px-4 py-3 text-sm`.

**Columns** (left → right):

| # | Column | Width | Content |
|---|---|---|---|
| 1 | Reorder | `w-10` | drag handle (`Bars3Icon`, outline, `w-5 h-5 text-neutral-400`) — 24×24px hit area (`p-1` around the 20px icon) |
| 2 | # | `w-10` | `sequence` integer, `text-neutral-500 text-center` |
| 3 | Label | `w-40` | text input — see §3.5 |
| 4 | Basis | `w-44` | segmented toggle (Percent / Fixed) — see §3.6 |
| 5 | Value | `w-32` | conditional % or $ input — see §3.7 |
| 6 | Trigger | `w-48` | trigger_type select + conditional detail — see §3.8 |
| 7 | Resolved | `w-28` | `resolved_amount_cents` readout (right-aligned, `font-medium text-neutral-900`) — **display only** |
| 8 | Actions | `w-12` | remove button (draft) / status badge + invoice link (active) — see §3.9 / §4 |

**Row height**: min `h-14` (56px) to fit the inline inputs comfortably; `py-3` vertical padding.

**Header row**: `bg-neutral-50 border-b border-neutral-200`, cells `px-4 py-3 text-sm font-medium text-neutral-700` (per design-system §6).

**Body rows**: `border-b border-neutral-100 hover:bg-neutral-50` (draft); active/completed rows drop the hover (read-only).

#### 3.4.1 Deposit row convention

The `sequence=1` row is the deposit **by convention only** — it is a normal `DrawRow`. The only special treatment: when a new schedule is created, the first draw is pre-seeded with `label="Deposit"`, `sequence=1`. No special styling, no separate component (§G). The label is freely editable like any other draw.

### 3.5 Label input (col 3)

- `<input type="text">`, `w-full border border-neutral-300 rounded-md px-3 py-2 text-sm text-neutral-900 focus:border-brand-500 focus:ring-2 focus:ring-brand-500`.
- Placeholder: "Draw label (e.g. Rough-in)".
- `<label>` above is omitted in-table (column header serves as label); for a11y each input carries `aria-label="Draw label for sequence {sequence}"` and `aria-describedby` pointing to its error region.
- Validation: non-empty (Zod `z.string().min(1)`). Error text below input: `text-xs text-fault-600 mt-1`, `aria-invalid` set when erroring.

### 3.6 Basis toggle (col 4)

Segmented control (same shell as §3.3, smaller): `bg-neutral-100 rounded-md p-0.5 inline-flex text-xs`.
- Active: `bg-white shadow-sm rounded px-2 py-1 text-xs font-medium text-neutral-900`.
- Inactive: `px-2 py-1 text-xs font-medium text-neutral-500 hover:text-neutral-700`.
- Segments: "Percent" / "Fixed".
- On change → `useUpdateScheduleLine` (PATCH line, draft only). Toggling basis clears the now-irrelevant value field client-side before the PATCH (the backend CHECK enforces `percent` XOR `amount_cents`).
- 409 → `<StalenessRefreshDialog>`.

### 3.7 Value input (col 5) — conditional on `basis`

- **`basis='percent'`**: `<input type="number" step="0.01" min="0" max="100">`, `w-24 border border-neutral-300 rounded-md px-2 py-2 text-sm text-right text-neutral-900 focus:border-brand-500 focus:ring-2 focus:ring-brand-500`, trailing `%` glyph in a `text-neutral-500` span. `percent` is `numeric(5,2)` arriving as a string — display 2-decimal precision. `aria-label="Percent of contract total for sequence {sequence}"`.
- **`basis='fixed_amount'`**: `<input type="number" step="0.01" min="0">`, same shell, trailing `$` glyph. On blur, convert dollars → cents (`Math.round(parseFloat(value) * 100)`) before the PATCH sends `amount_cents`. `aria-label="Fixed dollar amount for sequence {sequence}"`.
- **Resolved readout (col 7)** is the backend-computed `resolved_amount_cents` — the UI never re-derives percent math (§F). The value input is the user's intent; the resolved column is the truth.
- Validation (Zod v4, mirrors backend CHECK): percent branch requires `percent` present & `amount_cents` null; fixed branch requires `amount_cents` present & `percent` null. Non-color-only error: `aria-invalid` + `aria-describedby` + `text-xs text-fault-600` message "Enter a percent" / "Enter a dollar amount".

### 3.8 Trigger control (col 6)

- `<select>` for `trigger_type`: options `manual` ("Manual"), `date` ("On date"), `milestone` ("On milestone"). Shell: `border border-neutral-300 rounded-md px-2 py-2 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-500`.
- **Conditional detail** (renders inline to the right of the select, `ml-2`):
  - `trigger_type='date'` → `<input type="date">`, `w-40` same input shell. `aria-label="Trigger date for sequence {sequence}"`.
  - `trigger_type='milestone'` → `<input type="text">` placeholder "Milestone (e.g. Rough-in complete)", `w-48`. `aria-label="Milestone label for sequence {sequence}"`.
  - `trigger_type='manual'` → no detail; show a muted hint `text-caption text-neutral-400` "Invoiced manually".
- Validation (Zod, mirrors `psl_trigger_detail_chk`): `date` requires `trigger_date`; `milestone` requires `milestone_label`; `manual` requires neither.
- Leading icon (inline `w-4 h-4 text-neutral-400` before the select, `mr-1`): `HandRaisedIcon` (manual) / `CalendarDaysIcon` (date) / `FlagIcon` (milestone) — swaps with the select value.

### 3.9 Per-row remove (col 8, draft only)

- Icon button: `TrashIcon` (Heroicons outline, `w-4 h-4`) inside a `p-1.5 rounded-md` hit area (≥24×24px; the `p-1.5` + 16px icon = 36px).
- Tokens: `text-neutral-400 hover:text-fault-600 hover:bg-fault-50 focus-visible:ring-2 focus-visible:ring-brand-500`.
- `aria-label="Remove draw {sequence}: {label}"`.
- On click → confirm via the standard destructive confirm modal (design-system §7): overlay `fixed inset-0 bg-neutral-900/50 z-50`, panel `bg-white rounded-lg shadow-xl max-w-md w-full mx-auto mt-16 p-6`, confirm button `bg-fault-600 text-white`, cancel `border border-neutral-300 text-neutral-700`. Then `useDeleteScheduleLine` (DELETE line, draft only). 409 → `<StalenessRefreshDialog>`.
- Optimistic: the row is removed from the list immediately via `useOptimisticMutation`; a `<PendingBadge>` (§16.8) appears in col 8 position until the mutation settles. On error the row reappears and a `<NotificationBanner>` (fault severity) shows the RFC 7807 message.

### 3.10 Add-draw action

- Below the table, a text button: `PlusIcon` (Heroicons outline, `w-4 h-4`) + "Add draw", `mt-3 text-sm text-brand-600 hover:text-brand-700 font-medium`.
- On click → `useAddScheduleLine` (POST line, draft only) with optimistic insert: a new `DrawRow` appears at the bottom with `sequence = max(existing)+1`, empty fields, `<PendingBadge>` in col 8 until settled. 409 → `<StalenessRefreshDialog>`.
- Target ≥24×24px (`p-1` around the icon + text).

### 3.11 Reconciliation bar

Always visible directly below the draw editor card. Composes **no new component** beyond `ReconciliationBar` (a feature-local presentational component — see manifest). It displays three backend-computed values from `PaymentScheduleResponse`: `scheduled_total_cents`, `contract_total_cents`, `residual_cents`.

**Layout** (`bg-white border border-neutral-200 rounded-lg shadow-sm p-6 mb-4`):

- Row 1 (flex `items-center justify-between`):
  - Left: `text-sm text-neutral-500` "Scheduled" + `text-h3 font-semibold text-neutral-900 ml-2` `{formatCents(scheduled_total_cents)}`.
  - Center: a thin progress bar — `flex-1 mx-6 h-2 rounded-full bg-neutral-100 overflow-hidden` with an inner `<div>` `h-full rounded-full` whose width = `min(100, scheduled/contract*100)%` and whose color tracks the residual state (see below). The bar is a **secondary** signal — the text banner is primary (WCAG 1.4.1).
  - Right: `text-sm text-neutral-500` "Contract" + `text-h3 font-semibold text-neutral-900 ml-2` `{formatCents(contract_total_cents)}`.
- Row 2 (the residual banner — `mt-4 rounded-md border px-4 py-3 flex items-center gap-2`): an icon + text. **Three states, each color + text + icon** (never color-only):

| State | Condition | Token classes | Icon (Heroicons solid, `w-5 h-5`) | Text |
|---|---|---|---|---|
| Balanced | `residual_cents === 0` | `bg-margin-50 border-margin-200 text-margin-700` | `CheckCircleIcon` | "$0 remaining — ready to activate" |
| Under-allocated | `residual_cents > 0` | `bg-alert-50 border-alert-200 text-alert-700` | `ExclamationTriangleIcon` | "{formatCents(residual_cents)} under-allocated — add draws to reach the contract total" |
| Over-allocated | `residual_cents < 0` | `bg-fault-50 border-fault-200 text-fault-600` | `ExclamationCircleIcon` | "{formatCents(abs(residual_cents))} over-allocated — reduce draws to match the contract total" |

Progress-bar inner color: balanced → `bg-margin-500`; under → `bg-alert-500`; over → `bg-fault-500`.

### 3.12 Activate action

- Primary CTA in the fixed action footer (rightmost): solid button `bg-brand-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-brand-700` with `BoltIcon` (Heroicons solid, `w-4 h-4`) + "Activate schedule".
- **Disabled (genuine state, not RBAC)** until `residual_cents === 0`: `disabled:opacity-50 disabled:cursor-not-allowed`. The disabled reason is surfaced via:
  - The reconciliation banner text (under/over states explicitly say draws must sum to the total), AND
  - a `title`/`aria-describedby` on the disabled button: "Draws must sum to the contract total before activating. {formatCents(abs(residual_cents))} {over/under}-allocated." (non-color-only — WCAG 1.4.1).
- On click → `useActivateSchedule` (POST activate). On 422 (residual ≠ 0 — defense in depth; the client already gates this) → `<NotificationBanner>` fault severity with the RFC 7807 `detail`. On success → the schedule transitions to `status='active'` (State C) via cache invalidation; the editor locks.
- While the POST is in flight: button shows "Activating…" and is disabled (`isPending`).

### 3.13 Save-draft action (footer, secondary)

- `border border-neutral-300 text-neutral-700 rounded-md px-4 py-2 text-sm font-medium hover:bg-neutral-50`.
- Persists any in-flight header/line edits. In practice, draft edits PATCH immediately on blur (optimistic) — this button is a belt-and-suspenders "flush + leave" that navigates back to the origin quote/job after the last mutation settles.

### 3.14 Optimistic UI placement (§16.8)

- Add-draw and reorder use `useOptimisticMutation` from `@pilot/ui` (FE-B7 export, `index.ts`).
- `<PendingBadge>` (FE-B7, `index.ts`) renders in col 8 (replacing the remove button) while an add/reorder mutation is in flight, and in the row's sequence cell while a reorder is pending.
- On settle, `onSettled` invalidates `paymentScheduleKeys.detail(id)` — no hand-patching except the optimistic insert/reorder.

---

## 4. State C — Active (structure locked; draw lifecycle)

Editing is blocked — a PATCH/POST/DELETE on a line returns **409** (§G). The table becomes read-mostly; each draw exposes its lifecycle.

### 4.1 Table changes (active)

- All inputs (label, basis, value, trigger) become **read-only displays**: replace inputs with `text-sm text-neutral-900` spans. The basis toggle becomes a static label. The trigger detail becomes a static label (`CalendarDaysIcon` + formatted date, or `FlagIcon` + milestone text, or "Manual").
- Reorder handle (col 1) and remove button (col 8 draft) are **removed** (not disabled — hidden).
- Col 8 becomes the **draw lifecycle cell**: status badge + action/link (see §4.2).
- Row hover (`hover:bg-neutral-50`) is dropped (read-only).

### 4.2 Per-draw status badge + lifecycle (col 8, active)

Draw `status` badge (text + token, never color-only — design-system §3 style):

| `status` | Label | Token classes |
|---|---|---|
| `pending` | Pending | `bg-neutral-100 text-neutral-700` |
| `invoiced` | Invoiced | `bg-blue-100 text-blue-700` |
| `paid` | Paid | `bg-margin-100 text-margin-700` |
| `void` | Void | `bg-neutral-100 text-neutral-500` |

Badge shell: `inline-flex items-center rounded-full px-2.5 py-0.5 text-caption font-medium`.

Below/next to the badge, the lifecycle action:

| `status` | Trigger arrived? | Action |
|---|---|---|
| `pending` | yes (trigger_date ≤ today, or milestone — manual is always "arrived" on user discretion) | **Generate invoice** button (§4.3) |
| `pending` | no | muted `text-caption text-neutral-400` "Trigger not yet reached" (with the date/milestone hint) |
| `invoiced` / `paid` | — | link to invoice: `ArrowTopRightOnSquareIcon` (outline, `w-4 h-4`) + `text-brand-600 hover:text-brand-700 hover:underline text-sm`, href `/invoices/{invoice_id}` |
| `void` | — | muted `text-caption text-neutral-500` "Invoice voided — re-invoiceable" + a secondary "Generate invoice" link (voiding the prior invoice returns the line to `pending`, re-invoiceable — §G) |

### 4.3 Generate-invoice action (§16.7 always-preview-before-send)

Composes the **existing** `<MessagePreviewModal>` from `@pilot/ui` (FE-B6 export, `index.ts`). **Do NOT design a new preview modal.** The feature-local `SendInvoicePreviewModal` is the sibling that wraps `<MessagePreviewModal>` for the send flow; the draw-invoice generation preview reuses the same shared component.

- Button: `DocumentPlusIcon` (Heroicons outline, `w-4 h-4`) + "Generate invoice", `inline-flex items-center gap-1.5 text-sm text-brand-600 hover:text-brand-700 font-medium px-2 py-1 rounded-md hover:bg-brand-50 focus-visible:ring-2 focus-visible:ring-brand-500`. Target ≥24×24px.
- On click → open `<MessagePreviewModal>` with the draw's preview payload (draw label, `resolved_amount_cents` formatted USD, customer, site, the originating quote/job). The modal's confirm handler fires `useGenerateDrawInvoice` (POST `…/lines/{line_id}/generate-invoice`) with an **`Idempotency-Key`** header (mirror `useCreateInvoice`'s pattern — `draw-gen-{schedule_id}-{line_id}-{Date.now()}` is acceptable; a stable key per line is better for retry safety).
- On success → `line.invoice_id` is set, `line.status='invoiced'`; the row's col 8 swaps to the invoice link. Cache invalidation re-fetches the schedule.
- On **409** (draw already invoiced — Integrity rule 4) → `<NotificationBanner>` fault severity: "This draw already has an invoice. Void the existing invoice before re-generating." (§16.3 409-and-refresh is not the right fit here — this is a rule-4 conflict, surfaced as a banner, not a staleness refresh.)
- While generating: button shows "Generating…" + `<PendingBadge>`; the modal's confirm button is disabled (`isConfirming`).
- Modal focus-trap + return focus to the trigger button on close (§10).

### 4.4 409-and-refresh on a blocked edit (§16.3)

If a user somehow attempts a structural edit while `status='active'` (e.g. a stale tab where the schedule was activated elsewhere), the PATCH/POST/DELETE returns 409. Wrap all draft-only mutations in `useStalenessRetry` (FE-B4 export, `index.ts`); a 409 routes to `<StalenessRefreshDialog>` (FE-B4, `index.ts`) which explains the schedule is now active and offers "Refresh" — on refresh, the builder re-renders in State C (read-only). Do **not** design a new conflict dialog.

---

## 5. State D — Completed / Cancelled (read-only summary)

### 5.1 Completed (`status='completed'`)

All draws are invoiced (and typically paid). The table is fully read-only (same as State C active, but no generate-invoice actions — every draw is `invoiced`/`paid`/`void` with invoice links). The reconciliation bar shows balanced (residual 0) in a muted "Completed" treatment: replace the residual banner with `bg-margin-50 border-margin-200 text-margin-700` + `CheckCircleIcon` + "Schedule completed — all draws invoiced". The action footer hides Activate/Save-draft; shows only `[Back to {quote/job}]`.

### 5.2 Cancelled (`status='cancelled'`)

Read-only summary with a cancelled banner at the top of the card: `bg-fault-50 border border-fault-200 text-fault-600 rounded-md px-4 py-3` + `ExclamationCircleIcon` + "This payment schedule was cancelled." Draw rows show their last-known status badges + invoice links (where `invoice_id` exists). No actions except `[Back to {quote/job}]`.

---

## 6. Data States (design-standards §12 — all four, always)

| TQ state | Condition | Rendered |
|---|---|---|
| `isPending` (initial load) | `usePaymentSchedule`/`usePaymentSchedules` fetching, no cached data | **Skeleton matching the table shape**: the schedule header card skeleton (`bg-white border … p-6` with `animate-pulse bg-neutral-100` blocks for title/total), then a `rounded-md border border-neutral-200` table shell with 4 skeleton rows (`h-14` each, `animate-pulse bg-neutral-100`), then a skeleton reconciliation bar (`h-16`). Skeletons over spinners (§11) — reduces layout shift. |
| `isError` | fetch failed | `<ErrorState>` from `@pilot/ui/states` (FE-B1, `index.ts`) with `type="server"`, title "Could not load payment schedule", description "Check your connection and try again.", `onRetry={() => refetch()}`. |
| empty | no schedule for this quote/job | State A (`<FirstTimeUserState>` + start CTA, §2). |
| populated | schedule present | State B / C / D per `status`. |

> **"Overdue" is not a status** (design-standards §12): never spec an "overdue" draw badge. Draw `status` is `pending`/`invoiced`/`paid`/`void` only. Invoice aging is a separate concern on the InvoiceDetailPage, not here.

---

## 7. §16 Pattern Composition Table (compose, never reinvent)

| Need | Locked pattern (§16) | Existing component (barrel ref) | Prop/slot used |
|---|---|---|---|
| Preview the draw invoice before generating | Always-preview-before-send (§16.7) | `<MessagePreviewModal>` (`index.ts`) | `open`, preview-data payload (draw label, resolved amount, customer/site), `onConfirm` → `useGenerateDrawInvoice` |
| Add / reorder draws responsively | Optimistic UI (§16.8) | `<PendingBadge>` (`index.ts`) + `useOptimisticMutation` (`index.ts`) | `PendingBadge` in col 8 / sequence cell during in-flight add/reorder |
| Editing a locked (active) schedule | 409-and-refresh (§16.3) | `useStalenessRetry` (`index.ts`) + `<StalenessRefreshDialog>` (`index.ts`) | wraps draft-only line mutations; 409 → dialog → refresh → re-render State C |
| Surface a 422 reconciliation / 409 re-invoice error | Four-class severity banner | `<NotificationBanner>` / `useNotificationQueue` (`index.ts`) | RFC 7807 `detail` → fault severity on 422 activate + 409 re-invoice |
| Loading / error / empty | Data-state components | `<LoadingState>` / `<ErrorState>` / `<EmptyState>` / `<FirstTimeUserState>` (`index.ts`) | skeleton (custom, table-shaped) for `isPending`; `<ErrorState>` for `isError`; `<FirstTimeUserState>` for State A |
| Builder access + owner-only editing | RBAC hide-not-disable | `<RoleGate>` (`index.ts`) | `permission="invoices.create"` (builder + generate — owner/office), `permission="invoices.update"` (edit/activate — **owner only**, per §1.5 / ADR-0010) |
| Track-changes diff (§16.2) | `<DiffView>` (`index.ts`) | **Not composed** — inline edit is sufficient for draft draws; no review-before-save gate is required for this surface. Listed here to prove the option was considered and intentionally declined. |

> No new diff UI, preview modal, optimistic marker, or conflict/refresh dialog is proposed. If a pattern doesn't fit, the spec says "extend `<Component>` with optional prop X" — never "build new." None required here.

---

## 8. Interaction States (design-standards §11 — all five, every interactive element)

`focus-visible` (not `focus`) everywhere: `focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2`. `disabled` reserved for genuine states (Activate before balanced, Save while saving) — **never** for RBAC (techs are hidden via `<RoleGate>`).

| Element | default | hover | focus-visible | active | disabled |
|---|---|---|---|---|---|
| Set-up-CTA (State A) | `bg-brand-600 text-white` | `hover:bg-brand-700` | ring | `active:bg-brand-800` | n/a (RBAC-hidden) |
| Basis segmented (active seg) | `bg-white shadow-sm text-neutral-900` | n/a (active) | ring | n/a | n/a |
| Basis segmented (inactive seg) | `text-neutral-500` | `hover:text-neutral-700` | ring | `bg-neutral-100` | n/a |
| Label / value / trigger inputs | `border-neutral-300 text-neutral-900` | n/a | `focus:border-brand-500 focus:ring-2 focus:ring-brand-500` | n/a | n/a (active state swaps to read-only spans, not disabled inputs) |
| Add-draw | `text-brand-600` | `hover:text-brand-700` | ring | `active:text-brand-800` | n/a |
| Remove (TrashIcon) | `text-neutral-400` | `hover:text-fault-600 hover:bg-fault-50` | ring | `active:bg-fault-100` | n/a |
| Reorder handle | `text-neutral-400 cursor-grab` | `hover:text-neutral-700 cursor-grab` | ring | `cursor-grabbing` | n/a |
| Activate | `bg-brand-600 text-white` | `hover:bg-brand-700` | ring | `active:bg-brand-800` | `disabled:opacity-50 disabled:cursor-not-allowed` (until `residual_cents===0`) |
| Save draft | `border-neutral-300 text-neutral-700` | `hover:bg-neutral-50` | ring | `active:bg-neutral-100` | `disabled:opacity-50` while `isPending` |
| Generate-invoice | `text-brand-600` | `hover:text-brand-700 hover:bg-brand-50` | ring | `active:bg-brand-100` | `disabled:opacity-50` while `isConfirming` |
| Invoice link | `text-brand-600` | `hover:text-brand-700 hover:underline` | ring | n/a | n/a |
| Cancel (footer) | `border-neutral-300 text-neutral-700` | `hover:bg-neutral-50` | ring | `active:bg-neutral-100` | n/a |

---

## 9. Animation Spec (with `prefers-reduced-motion` fallback)

| Element | Transition | Reduced-motion |
|---|---|---|
| Reconciliation bar banner (state change) | `transition-colors duration-200 ease-in-out` on the banner + progress-bar inner | no transition (instant color swap) |
| Progress-bar inner width | `transition: width 300ms ease-in-out` | no transition |
| DrawRow add (optimistic insert) | `transition-opacity duration-150 ease-out` (row fades in from `opacity-0` to `opacity-100`) | no transition (instant appear) |
| DrawRow remove (optimistic) | `transition-opacity duration-150 ease-out` (fades out, then unmounts) | no transition (instant unmount) |
| Basis segmented active slide | `transition-colors duration-150` (no position slide — the active segment re-renders in place) | no transition |
| Button hover/active | `transition-colors duration-150` | no transition |
| Skeleton pulse | `animate-pulse` (Tailwind default) | `animate-none` — show a static `bg-neutral-100` block instead |

All transitions respect `@media (prefers-reduced-motion: reduce)` → instant/opacity-only. State this in the component JSDoc for the engineer.

---

## 10. Accessibility Notes (design-standards §10 — WCAG 2.2 AA)

- **Color is never the only signal.**
  - Reconciliation bar: each of the three states pairs its color token with a text label AND a distinct Heroicon (`CheckCircleIcon` / `ExclamationTriangleIcon` / `ExclamationCircleIcon`) — three independent signals (WCAG 1.4.1).
  - Every draw status badge and schedule status badge pairs its color with the text label from §3.2/§4.2.
  - The disabled Activate button carries a `title`/`aria-describedby` stating the residual reason in text.
- **Contrast ≥ 4.5:1 body / 3:1 UI borders.** All token pairings used (`text-neutral-900 on bg-white`, `text-brand-700 on bg-brand-50`, `text-fault-600 on bg-fault-50`, `text-alert-700 on bg-alert-50`, `text-margin-700 on bg-margin-50`) are pre-validated by the design system. No new pairings invented.
- **Target size ≥24×24px (WCAG 2.2 SC 2.5.8).**
  - Reorder handle: `Bars3Icon` `w-5 h-5` (20px) inside `p-1` → 28px hit area. ✓
  - Remove button: `TrashIcon` `w-4 h-4` (16px) inside `p-1.5` → 36px. ✓
  - Generate-invoice: `px-2 py-1` around `w-4 h-4` → ≥28px. ✓
  - Add-draw, Activate, Save: `px-4 py-2` buttons → ≥44px. ✓
  - Modal close `XMarkIcon`: `w-5 h-5` inside `p-1` → 28px. ✓
- **Focus not obscured (WCAG 2.2 SC 2.4.11).** The `h-12` sticky header + any `<NotificationBanner>` portal must not hide focused content. Spec `scroll-margin-top: 4rem` (`scroll-mt-16`) on the draw editor card and reconciliation bar so keyboard-anchored content scrolls below the sticky header. The fixed action footer (`z-40`) must not overlap the last table row — `pb-24` on the container reserves footer space.
- **Every form field has a visible label / accessible label.** In-table inputs use `aria-label="… for sequence {sequence}"` (the column header is visual-only); the basis/trigger segmented controls have `role="group"` + `aria-label`. Error text is `text-fault-600` AND linked via `aria-describedby` to the input; `aria-invalid` set on error. Placeholder-as-label is banned (§10).
- **Modal focus-trap + return.** `<MessagePreviewModal>` and `<StalenessRefreshDialog>` must trap focus while open and return focus to the triggering button (Generate-invoice / the edit control) on close. The destructive remove-confirm modal likewise. Spec `role="dialog" aria-modal="true" aria-labelledby=…`.
- **Accessible authentication (WCAG 2.2 SC 3.3.8).** N/A — no auth on this surface. (Noted for completeness.)
- **Consistent help (WCAG 2.2 SC 3.2.6).** A `<HelpAnchor>` "?" (FE-B16, `index.ts`) sits in the schedule header card's top-right, in the same relative position as other surfaces, with context payload `surface: "payment-schedule-builder"`.
- **Keyboard order** through the draw table: reorder handle → label → basis → value → trigger select → trigger detail → remove/generate. Tab order follows DOM order (left-to-right, top-to-bottom). Reorder via keyboard: the handle is `role="button"` with `aria-keyshortcuts` / arrow-key reorder (spec the handle as a focusable button; arrow-up/down reorders, Enter confirms).

---

## 11. Icon Inventory (exact Heroicons 2.0 names; no emoji)

| Icon | Variant | Size | Use |
|---|---|---|---|
| `CurrencyDollarIcon` | outline | `w-12 h-12` | State A empty-state leading visual |
| `PlusIcon` | outline | `w-4 h-4` | Add-draw action |
| `PlusIcon` | solid | `w-4 h-4` | State A "Set up payment schedule" CTA |
| `Bars3Icon` | outline | `w-5 h-5` | Reorder/drag handle |
| `TrashIcon` | outline | `w-4 h-4` | Per-row remove (draft) |
| `BoltIcon` | solid | `w-4 h-4` | Activate schedule CTA |
| `DocumentPlusIcon` | outline | `w-4 h-4` | Generate-invoice action |
| `ArrowTopRightOnSquareIcon` | outline | `w-4 h-4` | Invoice link (invoiced/paid draw) |
| `HandRaisedIcon` | outline | `w-4 h-4` | Trigger type = manual |
| `CalendarDaysIcon` | outline | `w-4 h-4` | Trigger type = date |
| `FlagIcon` | outline | `w-4 h-4` | Trigger type = milestone |
| `CheckCircleIcon` | solid | `w-5 h-5` | Reconciliation: balanced |
| `ExclamationTriangleIcon` | solid | `w-5 h-5` | Reconciliation: under-allocated |
| `ExclamationCircleIcon` | solid | `w-5 h-5` | Reconciliation: over-allocated + cancelled banner |
| `XMarkIcon` | outline | `w-5 h-5` | Modal close (preview / refresh / confirm) |
| `ArrowLeftIcon` | outline | `w-4 h-4` | Cancel / back-to-origin breadcrumb |

All outline for secondary/nav/inline; solid for primary CTAs and active emphasis (design-standards §5). No custom SVG required.

---

## 12. Component Manifest

Every file the React Engineer creates/modifies. Feature-local components live in `apps/web/src/features/billing/` (new domain). No new shared components are added to `packages/ui` (locked §16 patterns are composed, not rebuilt).

| File | Action | Description |
|---|---|---|
| `apps/web/src/features/billing/components/PaymentScheduleBuilder.tsx` | **new** | Container orchestrating all 4 product states (A/B/C/D) + 4 data states; wraps in `<RoleGate permission="invoices.create">`; renders header card, draw table, reconciliation bar, action footer. |
| `apps/web/src/features/billing/components/DrawRow.tsx` | **new** | One draw row: reorder handle, sequence, label, basis toggle, conditional value input, trigger control + conditional detail, resolved readout, lifecycle cell (remove in draft / status badge + generate-invoice or invoice link in active). Deposit = `sequence=1` row, no special component. |
| `apps/web/src/features/billing/components/ReconciliationBar.tsx` | **new** | Presentational: `scheduled_total_cents` vs `contract_total_cents` + `residual_cents` banner in 3 color-independent states (balanced/under/over) with text + icon. Display-only — no math. |
| `apps/web/src/features/billing/components/GenerateDrawInvoiceButton.tsx` | **new** | Per-pending-draw button → opens `<MessagePreviewModal>` (§16.7) → `useGenerateDrawInvoice` with Idempotency-Key → invoice link on success; 409 → `<NotificationBanner>`. |
| `apps/web/src/features/billing/components/__tests__/PaymentScheduleBuilder.test.tsx` | **new** | Integration: route renders, RBAC (owner sees / tech hidden), State A/B/C, reconciliation 3 states w/ text asserts, Activate disabled until residual 0 + 422 banner, 409 → refresh dialog, generate-invoice opens modal + fires POST w/ Idempotency-Key. |
| `apps/web/src/features/billing/components/__tests__/ReconciliationBar.test.tsx` | **new** | Unit: 3 states assert on text labels (not color). |
| `apps/web/src/features/billing/components/__tests__/DrawRow.test.tsx` | **new** | Unit: basis toggle swaps %/$ input; trigger select swaps detail; Zod validation errors are non-color-only (`aria-invalid`). |
| `apps/web/src/features/billing/hooks/usePaymentSchedule.ts` | **new** | `GET /api/v1/payment-schedules/{id}` — TQ v5, query-key factory `paymentScheduleKeys.detail(id)`. |
| `apps/web/src/features/billing/hooks/usePaymentSchedules.ts` | **new** | `GET /api/v1/payment-schedules?quote_id=&job_id=` — `placeholderData: keepPreviousData`. |
| `apps/web/src/features/billing/hooks/useCreatePaymentSchedule.ts` | **new** | `POST /api/v1/payment-schedules` — Idempotency-Key header; invalidates detail+list. |
| `apps/web/src/features/billing/hooks/useUpdateSchedule.ts` | **new** | `PATCH /api/v1/payment-schedules/{id}` (draft only) — wrapped in `useStalenessRetry` (409 → refresh). |
| `apps/web/src/features/billing/hooks/useAddScheduleLine.ts` | **new** | `POST /api/v1/payment-schedules/{id}/lines` — optimistic via `useOptimisticMutation` + `<PendingBadge>`. |
| `apps/web/src/features/billing/hooks/useUpdateScheduleLine.ts` | **new** | `PATCH /api/v1/payment-schedules/{id}/lines/{line_id}` (draft only) — `useStalenessRetry`. |
| `apps/web/src/features/billing/hooks/useDeleteScheduleLine.ts` | **new** | `DELETE /api/v1/payment-schedules/{id}/lines/{line_id}` (draft only) — optimistic + `useStalenessRetry`. |
| `apps/web/src/features/billing/hooks/useActivateSchedule.ts` | **new** | `POST /api/v1/payment-schedules/{id}/activate` — 422 (residual ≠ 0) → `<NotificationBanner>` fault. |
| `apps/web/src/features/billing/hooks/useGenerateDrawInvoice.ts` | **new** | `POST /api/v1/payment-schedules/{id}/lines/{line_id}/generate-invoice` — Idempotency-Key; 409 (already invoiced) → banner. |
| `apps/web/src/features/billing/hooks/__tests__/*.test.ts` | **new** | Per-hook unit tests (shape, error, query keys, Idempotency-Key header assert). |
| `apps/web/src/app/(authed)/billing/payment-schedules/new/page.tsx` | **new** | Thin server component (Rule 9): reads `?quote_id=`/`?job_id=`, renders `<PaymentScheduleBuilder mode="new" … />`. |
| `apps/web/src/app/(authed)/billing/payment-schedules/[id]/page.tsx` | **new** | Thin server component: `<PaymentScheduleBuilder scheduleId={params.id} />`. |
| `apps/web/src/mocks/handlers/paymentScheduleHandlers.ts` | **new** | MSW handlers for all 9 endpoints: a draft schedule (deposit + 2 draws, residual drivable to 0) + an active schedule (1 invoiced + 1 pending draw); per-test overrides for 422-residual + 409-lock/re-invoice. |
| `apps/web/src/mocks/handlers/index.ts` | **modify** | Register `paymentScheduleHandlers` in the `handlers` array (do not duplicate existing paths). |
| `frontend/packages/ui/src/role-gate/permissions.ts` | **modify** | Add `"invoices.update"` to the `PermissionKey` union AND to the **`owner`** role set **only** (mirror `invoices.create` at line 49 — but owner-set only; do **NOT** add to office_staff, tech, or operator). This is the one real change resolving the gap (§1.5 / ADR-0010). No backend change is required — the live seed already grants owner `invoices.update` via `"*"`. |
| `apps/web/src/features/quotes/components/QuoteDetailPage.tsx` (or job detail) | **modify** | Add the "Set up payment schedule" entry action (link to `/billing/payment-schedules/new?quote_id={id}` or existing `[id]`), wrapped in `<RoleGate permission="invoices.create">`. (Exact file confirmed by the React Engineer against the live codebase.) |

> **No orphan/duplicate components.** `PaymentScheduleBuilder`, `DrawRow`, `ReconciliationBar`, `GenerateDrawInvoiceButton` match design doc §H exactly. None exist in the `packages/ui` barrel (confirmed) — they are app-feature, correctly placed in `features/billing/`.

---

## 13. Implementation Notes (for the React Engineer)

### 13.1 Hooks & query keys

- Query-key factory (colocated in `usePaymentSchedule.ts`):
  ```typescript
  export const paymentScheduleKeys = {
    all: ["payment-schedules"] as const,
    list: (params: { quote_id?: string; job_id?: string }) =>
      [...paymentScheduleKeys.all, "list", params] as const,
    detail: (id: string) => [...paymentScheduleKeys.all, "detail", id] as const,
  };
  ```
- All 9 hooks via `apiClient` from `@pilot/shared-api` (Rule 2 — `fetch()` banned). Types from `@pilot/shared-types` after `pnpm sync-api-types` (Rule 1.3) — `components["schemas"]["PaymentScheduleResponse"]`, `["PaymentScheduleLineResponse"]`, `["PaymentScheduleCreate"]`, `["PaymentScheduleLineCreate"]`, `["PaymentScheduleLineUpdate"]`.
- TQ v5 object-form (Rule 12): `gcTime`/`isPending`; `placeholderData: keepPreviousData` on the list hook; invalidate (don't hand-patch) in `onSettled` — except the optimistic add/reorder which uses `useOptimisticMutation`.

### 13.2 Idempotency-Key

- `useCreatePaymentSchedule` and `useGenerateDrawInvoice` **must** send an `Idempotency-Key` header (mirror `useCreateInvoice`). A stable per-line key (e.g. `draw-gen-{schedule_id}-{line_id}`) is preferred over a timestamp for retry safety — a retried generation returns the same invoice.

### 13.3 Entry query params

- `/billing/payment-schedules/new?quote_id={id}` or `?job_id={id}`. The builder seeds `contract_total_cents` from the quote/job total at create time (POST body). The schedule locks its own `contract_total_cents` — it is **not** a live FK to `quote.total_cents` (§G); the quote may change post-schedule.

### 13.4 Display-only fields (never recompute)

- `scheduled_total_cents`, `residual_cents`, `resolved_amount_cents` are **backend-computed** (§F). The UI displays them verbatim. The reconciliation bar's progress-bar width is the only client-derived value (`scheduled/contract*100`, clamped 0–100) — and it is a secondary signal; the text banner is primary.
- Mixed-basis reconciliation (fixed-first, then percent across the remainder) is backend-owned — never reimplement in the UI.

### 13.5 Money formatting

- All `_cents` fields are integer cents → `formatCents(cents)` = `Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(cents / 100)` (mirror `InvoiceBuilderPage.formatCents`). Never render raw cents.
- `percent` is `numeric(5,2)` arriving as a string — display 2-decimal precision in the percent input (`step="0.01"`).

### 13.6 Zod v4 validation (Rule 13)

- Draw form validation mirrors the backend CHECKs:
  - `basis='percent'` → `percent` required (`z.string().regex(/^\d+(\.\d{1,2})?$/).min(0).max(100)`), `amount_cents` null.
  - `basis='fixed_amount'` → `amount_cents` required (positive int), `percent` null.
  - `trigger_type='date'` → `trigger_date` required; `='milestone'` → `milestone_label` required; `='manual'` → neither.
- `zodResolver`; errors surfaced via `aria-invalid` + `aria-describedby` + `text-xs text-fault-600` (non-color-only).

### 13.7 409 / 422 routing

- 409 on a draft-only line mutation (schedule no longer draft) → `useStalenessRetry` → `<StalenessRefreshDialog>` (§16.3).
- 422 on activate (residual ≠ 0) → `<NotificationBanner>` fault severity (RFC 7807 `detail`).
- 409 on generate-invoice (draw already invoiced — rule 4) → `<NotificationBanner>` fault severity (NOT the staleness dialog — this is a rule-4 conflict, not a staleness conflict).

### 13.8 React Compiler (Rule 11)

- React 19.2 + compiler enabled. Do **not** hand-write `useMemo`/`useCallback`/`React.memo` for render-perf. Keep `DrawRow`/`ReconciliationBar` pure.

### 13.9 SSE / real-time

- The schedule detail is **not** a live SSE surface (unlike the dispatch board). It uses standard TanStack Query refetch-on-invalidate. The notification bell is unaffected.

### 13.10 "Overdue" reminder

- Never send `?status=overdue` (no such code). Draw `status` is `pending`/`invoiced`/`paid`/`void` only. Invoice aging lives on InvoiceDetailPage.

---

## 14. Handoff Gate

This spec is ready for **Tom's review**. Implementation starts only after approval. The React Engineer's implementation prompt (`batch-billing-b1-react-engr-prompt.md`) is gated on this approval (Architect Rule §1.5).

**Resolved item (Tom's decision, 2026-07-28; ADR-0010)**: the `invoices.update` key was missing from `permissions.ts` (§1.5). Investigation (live `postgres-local` MCP) confirmed the **backend already enforces `invoices.update` correctly** — `owner` = `["*"]` grants it, `office_staff` intentionally does not, `technician` is denied — so **no backend change, no migration, and no separate batch are required**. Invoice editing is **owner-only** by policy. The React Engineer, **in this BILLING-B1 Part B batch**, adds `"invoices.update"` to the `PermissionKey` union and the **`owner`** role set only, then gates edit/activate with `<RoleGate permission="invoices.update">` directly (no temporary `invoices.create` gate, no `// TODO`). `roles.py` needs no edit (Swagger examples only). The FE `operator`→`accountant` + FE `tech`→`technician` role-vocabulary alignment is parked as a P2 RBAC-hardening item.
