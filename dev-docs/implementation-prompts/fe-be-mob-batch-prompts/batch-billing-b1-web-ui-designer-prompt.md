# Design Prompt: BILLING-B1 (Part B — Design Phase) — Payment Schedule Builder

**Mode**: Pilot Web UI Designer
**Batch**: BILLING-B1 (Part B — Design Phase; the Payment Schedule builder)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md §2.3` → BILLING-B1 (row 7)
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-billing-b1-design.md §H` (Part B — Frontend Scope)
**Backend status**: Part A (Python) **COMPLETE 2026-07-28** — migration `2dba31137096`; 9 endpoints + 9 `/test` twins live under `/api/v1/payment-schedules`; contract frozen in `backend/openapi_schema_map.md`.
**Estimated session**: 2–3 hours
**Platform**: Web (`apps/web`) — a builder surface inside the authed invoice/quote flow (NOT the public invoice payment page)
**Output**: A design spec at `dev-docs/architecture-design/batch-designs/batch-billing-b1-ui-design-spec.md`
**Next step**: Tom reviews and approves. Then the React Engineer implements Part B against the approved spec + the frozen API contract.

---

## ⚠️ MANDATORY STOP: Read These First

Before producing any design, read:

- **`dev-docs/architecture-design/batch-designs/batch-billing-b1-design.md`** — all sections, but especially **§D (endpoints)**, **§F (integrity rules + reconciliation math)**, **§G (resolved decisions)**, and **§H (Part B frontend scope + component manifest)**. This is the technical scope you are designing on top of.
- **Your two rule files** (they govern this spec's format and quality bar):
  - `.roo/rules-pilot-web-ui-designer/web-app-design-standards.md` — §3 token rules, §5 icons (Heroicons, **never emoji in production UI**), §6 component hierarchy (compose locked §16 patterns), §8 output format, §10 WCAG 2.2 AA, §11 five interaction states + reduced motion, §12 data-state awareness (money is integer cents; four data states).
  - `.roo/rules-pilot-web-ui-designer/pilot-design-system-reference.md` — status badge patterns, token pairings, currency formatting.

Also read these source files (per design-standards §2 Mandatory Pre-Work):

```
frontend/packages/ui/src/index.ts
  ← the authoritative barrel of every shared component. A component does not exist until it is here.
    You will compose: <DiffView> (§16.2 track-changes), <MessagePreviewModal> (§16.7 preview-before-send),
    <PendingBadge> + useOptimisticMutation (§16.8 optimistic UI), <NotificationBanner> (RFC 7807 → severity),
    <LoadingState>/<ErrorState>/<EmptyState> (§16 data states), <RoleGate> (RBAC).

frontend/apps/web/src/features/invoices/components/InvoiceBuilderPage.tsx
  ← the closest existing sibling surface (a builder with a line-items table). Match its shell, spacing, and header rhythm.

frontend/apps/web/src/features/invoices/components/InvoiceLineItemsTable.tsx
  ← the existing editable line-item table pattern. The draw editor is a close cousin — reuse the row/column rhythm.

frontend/apps/web/src/features/invoices/components/SendInvoicePreviewModal.tsx
  ← how the invoices feature already composes the always-preview-before-send pattern. The per-draw
    "Generate invoice" action reuses this pattern — do NOT design a new preview modal.

frontend/apps/web/src/features/invoices/components/InvoiceDetailPage.tsx
  ← where a generated draw invoice lands; understand the entry/exit navigation between a schedule and its draw invoices.
```

If a file you expect does not exist, note that in the spec rather than assuming.

---

## Background: Why This Surface Matters

Deposit + progress/milestone billing is table-stakes across every SMB field-service competitor (HCP, Jobber, Workiz, Service Fusion, FieldEdge). Part A shipped the backend orchestration: a **payment schedule** (parent, with a locked `contract_total_cents` the draws must sum to) and its **draws** (`payment_schedule_line` rows). A deposit is simply the draw with `sequence=1` — there is no separate "deposit" concept to design.

This design phase produces the **Payment Schedule builder** — the contractor-facing surface where an owner/office user structures the draws (deposit + progress + final), watches live reconciliation against the contract total, activates the schedule, and generates each draw's invoice when its milestone is reached.

---

## The Frozen API Contract (Do Not Invent Fields)

Every field below is confirmed live in `backend/openapi_schema_map.md`. Design only against these — the React Engineer will bind to exactly these names via `pnpm sync-api-types`.

**`PaymentScheduleResponse`** (the schedule + its draws):
`id`, `tenant_id`, `quote_id` (nullable), `job_id` (nullable), `customer_id`, `site_id`, `contract_total_cents` (integer cents), `status` (`draft` | `active` | `completed` | `cancelled`), `basis_default` (`percent` | `fixed_amount`), `is_active`, `lines: PaymentScheduleLineResponse[]`, **`scheduled_total_cents`** (integer — sum of resolved draws), **`residual_cents`** (integer — `contract_total_cents − scheduled_total_cents`; **must be 0 to activate**).

**`PaymentScheduleLineResponse`** (one draw):
`id`, `payment_schedule_id`, `sequence` (integer — `sequence=1` is the deposit **by convention only**, no special flag), `label` (free text: "Deposit", "Rough-in", "Final"), `basis` (`percent` | `fixed_amount`), `percent` (nullable, `numeric(5,2)` — string in JSON), `amount_cents` (nullable integer), **`resolved_amount_cents`** (integer — the computed dollar value of this draw, always present), `trigger_type` (`manual` | `date` | `milestone`), `trigger_date` (nullable), `milestone_label` (nullable), `invoice_id` (nullable — set once the draw is invoiced), `status` (`pending` | `invoiced` | `paid` | `void`), `is_active`.

**The 9 endpoints** (§D): create schedule (POST), get (GET), list (GET `?quote_id=`/`?job_id=`), patch header (PATCH — draft only), add draw (POST lines), edit/reorder draw (PATCH line — draft only), soft-delete draw (DELETE line — draft only), **activate** (POST — 422 if `residual_cents ≠ 0`), **generate-invoice** (POST line/generate-invoice — Idempotency-Key; 409 if the draw is already invoiced).

---

## Product States You Must Design (this is the core of the spec)

### State A — Empty (no schedule yet on this quote/job)
The quote/job is billed line-item today; no schedule exists. Show a `<FirstTimeUserState>`/`<EmptyState>` with a single primary CTA to start a payment schedule (seed `contract_total_cents` from the quote/job total). Explain in one line what progress billing does.

### State B — Draft schedule (fully editable)
The builder proper. The owner adds/edits/reorders/removes draws. This is where **all editing lives** — once activated, the structure locks (§G). Must contain:
- **Draw editor table** — one row per draw: drag-handle/reorder, `sequence`, `label`, `basis` toggle (percent vs fixed), the value input (a % field when `basis=percent`, a $ field when `basis=fixed_amount`), `trigger_type` (manual/date/milestone) with its conditional detail (a date picker for `date`, a text field for `milestone`), and a resolved-amount readout (`resolved_amount_cents` → USD). Deposit is just the `sequence=1` row with label "Deposit" — spec it as a normal row, not a special component.
- **Reconciliation bar** — always visible: `scheduled_total_cents` vs `contract_total_cents`, and the **`residual_cents`** banner. Three visual states: **balanced** (residual = 0 → positive/`margin`), **under-allocated** (residual > 0 → `alert`), **over-allocated** (residual < 0 → `fault`). This is what tells the user whether Activate is allowed. Color must NOT be the only signal — pair each with text (e.g., "$0 remaining — ready to activate").
- **Add-draw** action and per-row **remove** (soft-delete).
- **Activate** primary action — disabled (visibly, with reason) until `residual_cents = 0`. On click it hits POST activate; a 422 (residual ≠ 0) routes to `<NotificationBanner>`.
- Editing draft rows uses the **optimistic UI** pattern (`<PendingBadge>` + `useOptimisticMutation`) for add/reorder — spec where the pending marker appears.

### State C — Active schedule (structure locked; draw lifecycle)
Editing is blocked (a PATCH/POST/DELETE on a line returns **409**). The table becomes read-mostly, and each draw exposes its lifecycle:
- Per-draw **status** (`pending` / `invoiced` / `paid` / `void`) — as a status badge with a text label (design-system §3; never color-only).
- For a `pending` draw whose trigger has arrived: a per-row **"Generate invoice"** action. This composes the existing **always-preview-before-send** pattern via `<MessagePreviewModal>` / `SendInvoicePreviewModal` — the user previews the draw invoice before it's created/sent. Spec the entry into that existing modal; do NOT design a new preview UI.
- For an `invoiced`/`paid` draw: a link to the generated invoice (`invoice_id` → InvoiceDetailPage).
- Because active edits 409, spec how the **409-and-refresh** pattern surfaces (the platform `useStalenessRetry`/`StalenessRefreshDialog` already exists — reference it; if the user tries to edit a locked schedule, the refresh dialog explains it's active).

### State D — Completed / Cancelled
All draws invoiced (completed) or the schedule was cancelled. Read-only summary; no actions except viewing the draw invoices.

### Cross-cutting data states (design-standards §12 — all four, always)
`isPending` (skeleton matching the table shape), `isError` (`<ErrorState>` with retry), empty (State A), populated (B/C/D). Spec each.

---

## §16 Pattern Composition — Compose, Never Reinvent (design-standards §6)

You are **composing locked platform patterns**, not inventing UX. Map each to the existing component in the barrel and state it explicitly in the spec:

| Need | Locked pattern (§16) | Existing component to compose |
|---|---|---|
| Edit a draft draw / show what changed | Track-changes diff (§16.2) | `<DiffView>` — only if the spec calls for a review-before-save of draft edits; otherwise inline edit is fine |
| Preview the draw invoice before generating | Always-preview-before-send (§16.7) | `<MessagePreviewModal>` / feature's `SendInvoicePreviewModal` |
| Add / reorder draws responsively | Optimistic UI (§16.8) | `<PendingBadge>` + `useOptimisticMutation` |
| Editing a locked (active) schedule | 409-and-refresh (§16.3) | `useStalenessRetry` + `<StalenessRefreshDialog>` |
| Surface a 422 reconciliation / 409 lock error | Four-class severity banner | `<NotificationBanner>` (RFC 7807 → severity) |
| Loading / error / empty | Data-state components | `<LoadingState>` / `<ErrorState>` / `<EmptyState>` / `<FirstTimeUserState>` |
| Owner/office-only builder | RBAC hide-not-disable | `<RoleGate permission="invoices.create" />` (and `invoices.update`) |

> Proposing a **new** diff UI, a new preview modal, a new optimistic marker, or a new conflict/refresh dialog is a design-review failure. If a pattern doesn't fit, spec "extend `<Component>` with optional prop X" — never "build new."

---

## RBAC

The builder is gated to users with `invoices.create` (create schedule + generate invoice) and `invoices.update` (edit/activate). These are existing permission keys — confirm both exist in `frontend/packages/ui/src/role-gate/permissions.ts`. Techs must not see the builder. Use `<RoleGate>` (hide-not-disable) — do NOT design a disabled-for-techs state.

---

## Where This Surface Lives (placement)

Per design doc §H, the builder is a surface on the **invoice/quote flow** in `apps/web/src/features/invoices/` (or a new `features/billing/` — call the placement in the spec and reconcile it with the React Engineer's Component Manifest). It is reached from a quote or job that is being billed in draws. It is **not** the public `/i/[token]` payment page (that's marketing-ui-designer's surface, out of scope here). Spec the entry point (e.g., a "Set up payment schedule" action on the quote/job or invoice builder) and the return navigation.

---

## Money & Formatting Rules (design-standards §12)

- All `_cents` fields are **integer cents** — spec currency as "divide by 100, format as USD" (e.g., `contract_total_cents: 500000` → "$5,000.00"). Never render raw cents.
- `percent` is `numeric(5,2)` (arrives as a string) — spec it as a percent input with 2-decimal precision; the resolved dollar amount comes from `resolved_amount_cents` (the backend already computed it — never re-derive percent math in the UI display; show the backend value).
- The reconciliation math (fixed-first, then percent across the remainder) is **backend-owned** (§F). The UI displays `scheduled_total_cents` / `residual_cents` from the response — it does not recompute them.

---

## Output: Design Spec Document

Produce the spec at:

**`dev-docs/architecture-design/batch-designs/batch-billing-b1-ui-design-spec.md`**

It MUST include (design-standards §8 + §10 Accessibility Notes):

1. **Surface overview** — route/entry point, placement (`features/invoices` vs new `features/billing`), who sees it (RBAC: `invoices.create`/`invoices.update`; techs hidden).
2. **State A — Empty** — the empty/first-time state + start CTA (pixel specs, tokens, Heroicon).
3. **State B — Draft builder** — full pixel specs for: the draw editor table (columns, row height, drag handle, the basis toggle, the conditional % vs $ input, the trigger_type control + its conditional detail, resolved-amount readout), the reconciliation bar (all three residual states, color-independent), add-draw, per-row remove, and the Activate action (enabled/disabled states with the disabled reason).
4. **State C — Active** — read-mostly table, per-draw status badges (text + token), the per-draw Generate-invoice action → preview modal composition, invoice link, and the 409-and-refresh treatment on a blocked edit.
5. **State D — Completed / Cancelled** — read-only summary.
6. **Data states** — `isPending` skeleton (table-shaped), `isError` (`<ErrorState>` + retry), populated. (Empty is State A.)
7. **§16 Pattern Composition table** — the table above, filled in with exact component names + the prop/slot each row uses (proving reuse, not reinvention).
8. **Interaction states** — for every interactive element: default, hover, `focus-visible` (visible ring), active, disabled (design-standards §11). Reserve `disabled` for genuine states (Activate before balanced), NOT for RBAC.
9. **Animation spec** — any transition (e.g., reconciliation bar color change, row add/remove) with property + duration + easing AND a `prefers-reduced-motion` fallback.
10. **Icon inventory** — exact Heroicons names (outline for secondary/nav, solid for primary CTAs; 20px nav / 16px inline). No emoji.
11. **Component Manifest** — a table of every file the React Engineer creates/modifies with exact path + one-line description. Reconcile with design doc §H (`PaymentScheduleBuilder`, `DrawRow`, `ReconciliationBar`, `GenerateDrawInvoiceButton`) — confirm each against the barrel so there are no orphan/duplicate components.
12. **Implementation notes** — hook names (`usePaymentSchedule`, `useCreatePaymentSchedule`, `useUpdateScheduleLine`, `useActivateSchedule`, `useGenerateDrawInvoice`), query-param entry (`?quote_id=`/`?job_id=`), the Idempotency-Key requirement on generate-invoice, and the fact that `scheduled_total_cents`/`residual_cents`/`resolved_amount_cents` are backend-computed (display only).
13. **Accessibility Notes** (design-standards §10) — color-independent status for the reconciliation bar AND every draw status badge; target sizes ≥24×24px for the reorder handle, remove button, and row actions; focus order through the draw table; modal focus-trap/return for the preview + refresh dialogs; non-color-only validation on the % / $ inputs.

---

## Handoff Gate

After producing the design spec, **STOP**. Do NOT write any code. The spec goes to Tom for approval; the React Engineer's implementation prompt is gated on that approval (Architect Rule §1.5). State this explicitly at the end of the spec.
