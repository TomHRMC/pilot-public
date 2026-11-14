# Implementation Prompt: BILLING-B1 (Part B) — Payment Schedule Builder

**Mode**: Pilot React Engineer
**Batch**: BILLING-B1 (Part B — Web Frontend)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md §2.3` → BILLING-B1 (row 7)
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-billing-b1-design.md §H` (Part B — Frontend Scope)
**UI design spec**: `dev-docs/architecture-design/batch-designs/batch-billing-b1-ui-design-spec.md` — **the pixel/state/token authority. Build to this spec.**
**Estimated session**: 4–5 hours
**Platform**: Web only (`apps/web`)
**Backend companion**: **None — Part A (Python) is COMPLETE** (migration `2dba31137096`; 18 endpoints live under `/api/v1/payment-schedules`; contract frozen in `backend/openapi_schema_map.md`). Your first Pre-Work step is `pnpm sync-api-types`.

> ⛔ **GATING PRECONDITION**: This prompt may only be executed **after Tom approves** `batch-billing-b1-ui-design-spec.md` (Architect Rule §1.5). If that spec does not yet exist or is unapproved → STOP and ask Tom. Do not build against an unapproved design.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full. The hard rules are non-negotiable STOPs.
- **`dev-docs/architecture-design/batch-designs/batch-billing-b1-ui-design-spec.md`** — every section. This is your visual + state contract.
- **`dev-docs/architecture-design/batch-designs/batch-billing-b1-design.md`** — §D (endpoints), §F (integrity rules), §G (resolved decisions), §H (frontend scope).

**Before rendering any invoice or payment UI**, read `dev-docs/pilot-operations.md` — the `is_billing_active` paywall and the invoice status rules. **Design decision (§G): progress billing is NOT tier-gated** — no entitlement/402 handling is needed on this surface beyond the existing global paywall.

**Invoice status "overdue" rule**: the `invoice_status` table has NO "overdue" code. Overdue is a derived display state (`due_at < TODAY AND status NOT IN ('paid','void','writeoff')`). Never send `?status=overdue`. This batch generates `progress` invoices in a draft-equivalent status — you display the draw's own `status` (`pending`/`invoiced`/`paid`/`void`), not a derived invoice-aging state.

Critical rules for this batch:

- **Rule 1.1 / 1.2**: Every endpoint you call is already in `backend/openapi_schema_map.md` under `payment-schedules`. Verify each before writing its hook. Do NOT invent URLs or field names.
- **Rule 1.3**: Run `pnpm sync-api-types` first. All payload types come from `@pilot/shared-types` (`components["schemas"]["PaymentScheduleResponse"]`, `["PaymentScheduleLineResponse"]`, etc.) — never hand-written interfaces.
- **Rule 2**: All `/api/v1/...` calls use `apiClient` from `@pilot/shared-api`. `fetch()` is banned. Never import from `@/lib/api-client` (does not exist).
- **Rule 7**: Compose existing `packages/ui` components — check `frontend/packages/ui/src/index.ts` before creating anything. You WILL reuse: `<MessagePreviewModal>` (preview-before-send), `<PendingBadge>` + `useOptimisticMutation` (optimistic add/reorder), `useStalenessRetry` + `<StalenessRefreshDialog>` (409-and-refresh), `<NotificationBanner>` (RFC 7807 severity), `<LoadingState>`/`<ErrorState>`/`<EmptyState>`/`<FirstTimeUserState>`, `<RoleGate>`. Do NOT build a new diff/preview/optimistic/conflict pattern — they are locked §16 patterns.
- **Rule 9**: Route files in `apps/web/src/app/(authed)/` are thin server components — no `"use client"`, no data fetching. All logic in feature components.
- **Rule 10**: Any test that fails during your work — even one that looks pre-existing — you fix before declaring done. If you can't find the root cause → STOP and ask Tom.
- **Rule 11 (React Compiler, §32)**: React 19.2 + compiler enabled. Do NOT hand-write `useMemo`/`useCallback`/`React.memo` for render-perf. Keep components pure.
- **Rule 12 (TanStack Query v5, §33)**: Object-form only; `gcTime`/`isPending`; colocated query keys including every variable; `placeholderData: keepPreviousData` for the paginated list; invalidate (don't hand-patch) after mutations.
- **Rule 13 (Zod v4 + RHF, §34)**: Draw form validation is Zod v4 via `zodResolver`; top-level `z.uuid()`/`z.email()`; unified `error` param. Infer API types from `@pilot/shared-types` — never re-derive a backend shape as Zod.
- **Rule 14 (§35)**: Authenticated data fetching stays client-side (`apiClient` + TanStack Query in `"use client"`). Never fetch tenant data in a Server Component/Route Handler.
- **Rule 15 (WCAG 2.2 AA, §36)**: Color-independent status on the reconciliation bar + every draw badge; ≥24×24px targets on reorder/remove/row actions; `focus-visible` rings; modal focus-trap on the preview + refresh dialogs; non-color-only validation on the % / $ inputs. Backs the axe-core DoD gate.

---

## Design Decisions (Do Not Re-Litigate)

From design doc §G + §H and the UI spec — these are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Deposit representation | A normal draw with `sequence=1`, label "Deposit" | No special field/component (§G) — do NOT build a separate deposit widget |
| Reconciliation math | Backend-owned; UI **displays** `scheduled_total_cents` / `residual_cents` / `resolved_amount_cents` | Never recompute percent/fixed math in the UI (§F) |
| All structural editing | Draft status only; active/completed/cancelled are read-mostly | Editing a non-draft schedule returns 409 (§G) — route to 409-and-refresh |
| Activate gate | Client disables Activate until `residual_cents === 0`; backend backstops with 422 | Defense in depth (§F rule 1) |
| Generate-invoice | Composes `<MessagePreviewModal>` (preview-before-send) + Idempotency-Key | Locked §16.7 pattern; retried POST returns the same invoice |
| Tier gating | None — not entitlement-gated for MVP (§G) | Normal invoice create under the existing paywall |
| Surface placement | Per the approved UI spec Component Manifest (`features/invoices` or new `features/billing`) | Reconcile your file paths to the spec exactly |

Do NOT change these without asking Tom.

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```

Record the exact count (`X passed, Y failed`). These must still pass at the end.

> If any test is already failing: do NOT treat it as "pre-existing" and proceed. Either confirm with Tom it's a known accepted failure, or fix it first. You may not start while tests are in an unexplained failed state.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

This re-exports the live backend OpenAPI spec, then regenerates `packages/shared-types/src/api-schema.d.ts`. Consume types via the `components` root:

```typescript
import type { components } from "@pilot/shared-types";
type PaymentScheduleResponse = components["schemas"]["PaymentScheduleResponse"];
type PaymentScheduleLineResponse = components["schemas"]["PaymentScheduleLineResponse"];
type PaymentScheduleCreate = components["schemas"]["PaymentScheduleCreate"];
type PaymentScheduleLineCreate = components["schemas"]["PaymentScheduleLineCreate"];
type PaymentScheduleLineUpdate = components["schemas"]["PaymentScheduleLineUpdate"];
```

> If `pnpm sync-api-types` produces new type errors in unrelated files → STOP and ask Tom (Part A changed the shared spec; unexpected drift must be understood, not worked around).

---

## Pre-Work: Verify Endpoints

All 9 endpoints (+ `/test` twins) are live. Confirm before writing hooks:

```bash
grep -A 3 "payment-schedules" backend/openapi_schema_map.md | head -60
```

Verified endpoints for this batch:

| Hook | Endpoint | Verified |
|---|---|---|
| `usePaymentSchedule(id)` | `GET /api/v1/payment-schedules/{schedule_id}` | ✅ line 12455 |
| `usePaymentSchedules({quote_id?,job_id?})` | `GET /api/v1/payment-schedules` | ✅ line 12241 |
| `useCreatePaymentSchedule()` | `POST /api/v1/payment-schedules` (Idempotency-Key) | ✅ line 12289 |
| `useUpdateSchedule()` | `PATCH /api/v1/payment-schedules/{schedule_id}` (draft only) | ✅ line 12493 |
| `useAddScheduleLine()` | `POST /api/v1/payment-schedules/{schedule_id}/lines` | ✅ line 12624 |
| `useUpdateScheduleLine()` | `PATCH /api/v1/payment-schedules/{schedule_id}/lines/{line_id}` | ✅ line 12727 |
| `useDeleteScheduleLine()` | `DELETE /api/v1/payment-schedules/{schedule_id}/lines/{line_id}` | ✅ line 12780 |
| `useActivateSchedule()` | `POST /api/v1/payment-schedules/{schedule_id}/activate` (422 on residual) | ✅ line 12539 |
| `useGenerateDrawInvoice()` | `POST /api/v1/payment-schedules/{schedule_id}/lines/{line_id}/generate-invoice` (Idempotency-Key; 409 if invoiced) | ✅ line 12807 |

**If any endpoint is missing from `openapi_schema_map.md` → STOP. Do not invent a URL. Ask Tom.**

**Contract field names (bind exactly — from `openapi.json`):**
- `PaymentScheduleResponse`: `id, tenant_id, quote_id?, job_id?, customer_id, site_id, contract_total_cents, status, basis_default, is_active, lines[], scheduled_total_cents, residual_cents`
- `PaymentScheduleLineResponse`: `id, payment_schedule_id, sequence, label, basis, percent?, amount_cents?, resolved_amount_cents, trigger_type, trigger_date?, milestone_label?, invoice_id?, status, is_active`

---

## Pre-Work: Read These Source Files

Read each with `read_file` before writing any code:

```
frontend/apps/web/src/features/invoices/components/InvoiceBuilderPage.tsx
  ← closest sibling builder shell — match header/spacing/section rhythm
frontend/apps/web/src/features/invoices/components/InvoiceLineItemsTable.tsx
  ← editable line-item table pattern the draw editor mirrors
frontend/apps/web/src/features/invoices/components/SendInvoicePreviewModal.tsx
  ← how the feature already composes preview-before-send — reuse, do not rebuild
frontend/apps/web/src/features/invoices/components/InvoiceDetailPage.tsx
  ← where a generated draw invoice lands (invoice_id navigation target)
frontend/apps/web/src/features/invoices/hooks/useInvoices.ts
  ← existing TanStack Query v5 hook pattern + query-key factory in this feature
frontend/apps/web/src/features/invoices/hooks/useCreateInvoice.ts
  ← existing mutation + Idempotency-Key pattern (mirror for create-schedule + generate-invoice)
frontend/packages/ui/src/index.ts
  ← confirm import paths for MessagePreviewModal, PendingBadge, useOptimisticMutation,
    useStalenessRetry, StalenessRefreshDialog, NotificationBanner, RoleGate, states
frontend/packages/ui/src/role-gate/permissions.ts
  ← `invoices.create` exists (line 49); `invoices.update` does NOT — you ADD it this batch
    (union + owner set ONLY — see the RBAC step below and design-spec §1.5 / ADR-0010)
frontend/apps/web/src/mocks/handlers/index.ts
  ← the barrel where new MSW handlers register
```

Also run:

```bash
find frontend/apps/web/src/features/invoices -name "use*.ts"
grep -n "MessagePreviewModal\|useOptimisticMutation\|useStalenessRetry\|StalenessRefreshDialog" frontend/packages/ui/src/index.ts
find frontend/apps/web/src/mocks/handlers -name "*.ts" | head -20
```

> Code examples in this prompt are starting points. Read each file first and adjust prop names, import paths, and logic to what you actually find.

---

## Context: What This Batch Does

| Change | Detail |
|---|---|
| New hooks | 9 TanStack Query hooks (1 detail, 1 list, 7 mutations) via `apiClient` |
| New feature surface | `PaymentScheduleBuilder`, `DrawRow`, `ReconciliationBar`, `GenerateDrawInvoiceButton` (per UI-spec manifest) |
| New route | Thin server-component route wiring the builder into the invoice/quote flow (per UI-spec placement) |
| Composed §16 patterns | preview-before-send, optimistic UI, 409-and-refresh, RFC 7807 banner |
| MSW handlers | `paymentScheduleHandlers.ts` covering all 9 endpoints + a 422-residual + 409-lock override |
| RBAC | Builder + generate: `<RoleGate permission="invoices.create">` (owner/office). Edit/activate/delete: `<RoleGate permission="invoices.update">` (**owner only**). Add the `invoices.update` key this batch (union + **owner set only**) — see the RBAC note below. |

---

## STEP 1 — Hooks (`features/[invoices|billing]/hooks/`)

Create the 9 hooks. Follow the existing `useInvoices.ts` / `useCreateInvoice.ts` patterns (query-key factory, `apiClient`, TQ v5 object-form). Place per the UI-spec manifest.

- **Query keys** — colocate a factory that includes every variable:
  ```typescript
  export const paymentScheduleKeys = {
    all: ["payment-schedules"] as const,
    list: (params: { quote_id?: string; job_id?: string }) =>
      [...paymentScheduleKeys.all, "list", params] as const,
    detail: (id: string) => [...paymentScheduleKeys.all, "detail", id] as const,
  };
  ```
- **List** (`usePaymentSchedules`) — `placeholderData: keepPreviousData` (paginated: `limit`/`offset`).
- **Mutations** — `useCreatePaymentSchedule` + `useGenerateDrawInvoice` must send an **`Idempotency-Key`** header (mirror how `useCreateInvoice` does it). After every mutation, **invalidate** `paymentScheduleKeys.detail(id)` (and `list`) in `onSettled` — do NOT hand-patch cache (except via the shared `useOptimisticMutation` pattern for add/reorder).
- **Activate + edit-when-active** — surface backend errors through the RFC 7807 → `<NotificationBanner>` path; wrap edit/reorder/delete in `useStalenessRetry` so a 409 (schedule no longer draft) routes to `<StalenessRefreshDialog>`.

Intermediate check after the hooks exist: `pnpm --filter web test 2>&1 | tail -6` (should be green — no consumers yet).

---

## STEP 2 — `ReconciliationBar` + `DrawRow` (draft editing)

Per the UI spec §3 (State B):

- **`ReconciliationBar`** — displays `scheduled_total_cents` vs `contract_total_cents` and the `residual_cents` banner in three color-independent states (balanced/`margin`, under/`alert`, over/`fault`) — each paired with **text** ("$0 remaining — ready to activate" / "$X under-allocated" / "$X over-allocated"). Money = cents/100 formatted USD. Never color-only (§36).
- **`DrawRow`** — one draw: reorder handle, `sequence`, `label`, basis toggle (`percent`|`fixed_amount`), the conditional value input (% field vs $ field), `trigger_type` control + conditional detail (date picker for `date`, text for `milestone`), and the `resolved_amount_cents` readout (display the backend value — do not compute). Deposit is the `sequence=1` row labeled "Deposit" — no special component.
- Draw form validation: Zod v4 (`zodResolver`) mirroring the backend CHECKs (percent requires `percent` & no `amount_cents`; fixed requires `amount_cents` & no `percent`; date requires `trigger_date`; milestone requires `milestone_label`). Non-color-only errors (`aria-invalid` + `aria-describedby`).
- Add/reorder use `useOptimisticMutation` + `<PendingBadge>` (§16.8). Targets ≥24×24px.

---

## STEP 3 — `PaymentScheduleBuilder` + `GenerateDrawInvoiceButton` + route

- **`PaymentScheduleBuilder`** — the container orchestrating all four states from the UI spec: State A empty (`<FirstTimeUserState>`/`<EmptyState>` + start CTA), State B draft (the `DrawRow` table + `ReconciliationBar` + add-draw + **Activate** disabled until `residual_cents === 0`), State C active (read-mostly, per-draw status badges + lifecycle), State D completed/cancelled (read-only). Cover all four TQ data states: `isPending` skeleton, `isError` `<ErrorState>`, empty (State A), populated.
- **`GenerateDrawInvoiceButton`** — per `pending` draw whose trigger has arrived. Composes `<MessagePreviewModal>` (preview the draw invoice before generating), fires `useGenerateDrawInvoice` with an Idempotency-Key, and on success links the row to `invoice_id` → InvoiceDetailPage. A 409 (already invoiced) → `<NotificationBanner>`.
- **Route** — thin server component per Rule 9 (`return <PaymentScheduleBuilder .../>;`), wired at the entry point defined in the UI spec. Wrap in `<RoleGate permission="invoices.create">` (builder — owner/office) and gate edit/activate/delete actions with `<RoleGate permission="invoices.update">` (**owner only**). Non-owners hidden (hide-not-disable).

### RBAC — add the `invoices.update` key (this batch; owner set only)

`invoices.update` is enforced by the backend (design doc §D) but is **missing** from the frontend registry, so `<RoleGate permission="invoices.update">` currently denies everyone. Add it now — this is the ONE new key this batch is authorized to add (per design-spec §1.5 / ADR-0010):

- In `frontend/packages/ui/src/role-gate/permissions.ts`: add `"invoices.update"` to the `PermissionKey` union AND to the **`owner`** `Set<PermissionKey>` **only** (mirror `invoices.create` at line 49).
- **Do NOT** add it to `office_staff`, `tech`, or `operator` — invoice editing is **owner-only** by policy (office_staff is read-mostly; techs excluded). This matches the live backend seed (`owner` = `["*"]` grants it; `office_staff` = create+view only).
- No backend change, migration, or `roles.py` edit is needed. Gate edit/activate with `<RoleGate permission="invoices.update">` directly — no temporary `invoices.create` gate and no `// TODO`.

Intermediate check after this step: `pnpm --filter web test 2>&1 | tail -6`.

---

## MSW Handlers for the New Endpoints

Create `apps/web/src/mocks/handlers/paymentScheduleHandlers.ts` covering all 9 endpoints with a varied fixture (a draft schedule with a deposit + 2 draws whose `residual_cents` you can drive to 0, and an active schedule with one `invoiced` and one `pending` draw). Include per-test-overridable responses for the **422 residual** (activate) and **409 lock/re-invoice** cases.

**Register in the barrel** — without this the handler is never loaded:

```typescript
// apps/web/src/mocks/handlers/index.ts
import { paymentScheduleHandlers } from "./paymentScheduleHandlers";
export const handlers = [
  ...existingHandlers,
  ...paymentScheduleHandlers, // ← ADD THIS
];
```

Check `index.ts` first — never duplicate a path that already has a handler.

---

## Test Requirements

Domain: web. Unit tests co-located in `features/[invoices|billing]/components/__tests__/` and `.../hooks/__tests__/`; integration tests in `apps/web/src/__tests__/batch_billing_b1/`.

### TanStack Query — required test setup
Fresh `QueryClient` per test with `retry: false` on both `queries` and `mutations` (default retry=3 causes timeouts). Never share a client across tests.

### MSW — required setup
`setupServer` from `msw/node`; `server.resetHandlers()` in `afterEach`; per-test `server.use(...)` for the 422/409 cases. **Never mock `apiClient` directly** — MSW intercepts at the HTTP level.

### RBAC — `AuthContext.Provider` pattern
Verify a `tech` role does NOT see the builder; `owner`/`office` do (use the `renderAs(role)` pattern from the inclusion spec §9). Additionally assert **owner-only editing**: `owner` sees the draft editor + Activate (gated on `invoices.update`); `office_staff` sees the builder (create/view) but **NOT** the edit/activate controls; `tech` sees nothing.

### Required coverage
**Hooks** — each returns the expected shape with a mock response and an error state; query keys include their variables; `useCreatePaymentSchedule` + `useGenerateDrawInvoice` send an Idempotency-Key header.
**Components / integration**:
1. Route does NOT 404 — builder renders.
2. RBAC: owner sees builder; tech does not.
3. State A empty → start CTA visible; State B draft → draw table + reconciliation bar render with MSW data.
4. `ReconciliationBar` shows all three states with **text** (assert on the label, not color) — balanced/under/over.
5. Activate is disabled while `residual_cents !== 0`; enabled at 0; a 422 response routes to `<NotificationBanner>` (assert `role="alert"`).
6. Editing a draw while `status='active'` → 409 → `<StalenessRefreshDialog>` appears.
7. Generate-invoice opens `<MessagePreviewModal>`; confirming fires POST to the correct URL with an Idempotency-Key; success links to the invoice.
8. Re-generating an already-invoiced draw → 409 → banner.

**Resilience**: assert by specific IDs/labels/content from the MSW fixture — never `toHaveLength(N)`. Web assertions use `toBeInTheDocument()` (not `.toBeTruthy()`). Mock `next/navigation`/`next/link` where used.

---

## Final Verification

> ❌ **BANNED**: `npx vitest run` — bypasses the workspace and breaks module resolution. The only correct runner for `apps/web` is `pnpm --filter web test`.

### Phase 1 — Targeted (during development)
```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -6
pnpm --filter web test -- apps/web/src/__tests__/batch_billing_b1/ 2>&1 | tail -10
```
Fix any failure before moving on — including any that look pre-existing.

### Phase 2 — Full (once, at the end)
```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

> Any failure in either phase must be fixed before done — no "pre-existing" exception without Tom's written OK. If you can't find the root cause → STOP and ask Tom.

---

## Definition of Done — BILLING-B1 (Part B)

- [ ] Design spec approved by Tom before any code (gating precondition)
- [ ] Pre-modification regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — no new type errors; all types from `@pilot/shared-types`
- [ ] UI design spec + design doc §D/§F/§G/§H fully read before coding
- [ ] All mandatory source files read; all 9 endpoint URLs re-verified in `openapi_schema_map.md`
- [ ] **STEP 1**: 9 hooks (query-key factory; `keepPreviousData` on list; Idempotency-Key on create + generate-invoice; invalidate on `onSettled`; 409 via `useStalenessRetry`)
- [ ] **STEP 2**: `ReconciliationBar` (three color-independent states w/ text) + `DrawRow` (basis/trigger conditional inputs; Zod v4 mirror of CHECKs; optimistic add/reorder via `useOptimisticMutation` + `<PendingBadge>`)
- [ ] **STEP 3**: `PaymentScheduleBuilder` (4 product states + 4 data states), `GenerateDrawInvoiceButton` (`<MessagePreviewModal>` + Idempotency-Key), thin route, `<RoleGate>`
- [ ] `resolved_amount_cents`/`scheduled_total_cents`/`residual_cents` are display-only (no UI recompute of §F math)
- [ ] Money rendered from integer cents (÷100 USD); `percent` shown 2-decimal
- [ ] Activate disabled until `residual_cents === 0`; 422 + 409 route to `<NotificationBanner>` / `<StalenessRefreshDialog>`
- [ ] No hand-written `useMemo`/`useCallback`/`React.memo` for render-perf; components pure (§32)
- [ ] All hooks TQ v5 object-form + colocated keys (§33); Zod v4 (§34); client-side fetching only (§35)
- [ ] axe-core zero violations + WCAG 2.2 AA spot-checks: color-independent status, ≥24px targets (reorder/remove/actions), focus-visible, modal focus-trap on preview + refresh dialogs, non-color-only input errors (§36)
- [ ] No new shared components added to `packages/ui` (this is app-feature work) — locked §16 patterns composed, not rebuilt
- [ ] `invoices.update` added to `permissions.ts` — `PermissionKey` union + **`owner` set only** (NOT office_staff/tech/operator); edit/activate gated with `<RoleGate permission="invoices.update">` directly (no temp `invoices.create` gate, no `// TODO`); no other new keys added
- [ ] RBAC tests assert owner-only editing: owner sees edit/Activate; office_staff sees builder but not edit/Activate; tech sees nothing
- [ ] `paymentScheduleHandlers.ts` created AND registered in `mocks/handlers/index.ts`
- [ ] Unit tests pass (hooks + components); integration tests pass in `__tests__/batch_billing_b1/`
- [ ] Zero TS errors (`check-types`); zero ESLint `no-hardcoded-design-values` warnings
- [ ] No regressions in pre-existing suite (targeted run confirms)
- [ ] **Phase 2 FULL verification passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`):

  ```bash
  cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
  ```

- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to launch plan Appendix B + Appendix A row + BILLING-B1 marked ✅ Part B complete in §2.3

---

## Completion Summary

After all DoD items:

1. Add a **Completion Summary** to `pilot-launch-plan.md` Appendix B (template below), add a one-row Appendix A entry, and mark **BILLING-B1 Part B ✅** in the §2.3 row 7 status cell (BILLING-B1 is then fully complete — Part A + Part B).

```markdown
### BILLING-B1 (Part B — React Engineer) — Payment Schedule Builder: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed, Y failed (web)
**Final**: X+N passed (+N new tests)

#### What Was Accomplished
- <bullets>

#### Files Changed / Created
| File | Action |
|---|---|

#### Tests Added
| Test File | Type | Tests | All Pass |
|---|---|---|---|
```
