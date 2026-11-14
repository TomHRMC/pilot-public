# Implementation Prompt: CE-1 (Part C) — Web Invoice Detail: Sign-Off Card + Overpayment Review

**Mode**: Pilot React Engineer
**Batch**: CE-1 — Part C (Web)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 CE-1 (Beta Execution Order 1)
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-ce-1-design.md` — §D.3/§D.4 (endpoint contracts), §G (resolved decisions), §I Part C (component manifest)
**UI design spec (Tom-approved)**: `dev-docs/architecture-design/batch-designs/batch-ce-1-web-ui-design-spec.md` — **the pixel/state authority.** H2 card = its §2, banner = §3, modal = §4, implementation notes = §5, accessibility = §7 (mandatory), responsive = §8
**Estimated session**: 2–2.5 hours (+ ~30 min manual E2E, Step 9)
**Platform**: Web only (`apps/web/`) — zero `packages/ui` changes
**Backend companion**: **CE-1 Part A (Python) MUST be merged first** (`batch-ce-1-python-engr-prompt.md`). Your first Pre-Work step (`pnpm sync-api-types`) verifies it — if `InvoiceSignoffResponse` / `resolve-variance` are absent from the generated types → **STOP; Part A is not merged.**

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`batch-ce-1-web-ui-design-spec.md`** — every section; you implement against its pixel specs, state tables, testIDs, and §7 accessibility requirements **verbatim**
- **`batch-ce-1-design.md`** — §D/§G/§I

Critical rules for this batch:

- **Rule 1.1/1.2**: Verify both endpoints in `backend/openapi_schema_map.md` before writing any hook. Never invent URLs or param names.
- **Rule 1.3**: Run `pnpm sync-api-types` before starting — payload types come from `@pilot/shared-types`, never hand-written interfaces (the only grandfathered local interface is `PaymentSummaryEntry` — see Step 1).
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is banned for `/api/v1/...`.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any component — this batch adds **zero** shared components; compose `EmptyState`, `ErrorState`, `RoleGate`, `NotificationBanner` (spec §1 component-existence check).
- **Rule 10**: Any test failure — even apparently pre-existing — must be fixed before done. Root cause unreachable → STOP and ask Tom.
- **Rule 11 (React Compiler, §32)**: No hand-written `useMemo`/`useCallback`/`React.memo` for render-perf. Keep components pure (the banner's `unresolvedOverpayments` filter is a plain derived value — spec §3.1 shows the shape; do not memoize it).
- **Rule 12 (TanStack Query v5, §33)**: Object-form only; colocated query-key factories; `retry: false` on both hooks (spec §5.1); invalidate `["invoice", invoiceId]` after the resolve mutation — never hand-patch the cache.
- **Rule 14 (§35)**: Data fetching stays client-side in feature components. No Server Component fetching.
- **Rule 15 (WCAG 2.2 AA, §36)**: The spec's §7 accessibility requirements are binding — focus trap + return focus in the modal, `focus-visible` rings, target sizes, non-color-only status. axe-core zero violations is part of done.

**Invoice status "overdue" rule:** no `overdue` code exists; never send `?status=overdue`. Not directly needed here — included as standing awareness.

---

## Design Decisions (Do Not Re-Litigate)

From design doc §G + spec §5 — final:

| Decision | Outcome | Rationale |
|---|---|---|
| Variance resolution | **Record-keeping only** — no Stripe refund call, no QB credit memo, no new payment rows | Stripe Connect decision open (INT-H1); SD-2 refund model untouched (R6) |
| Banner data source | **Derived from `invoice.payments[]`** already fetched by `useInvoice` — no extra fetch | Simplicity; `PaymentSummaryEntry` extension carries the fields (spec §5.3) |
| Modal scope | **One payment per submission**; no "resolve next" affordance | MVP discipline (spec §4.1) |
| 409 already-resolved | Compose §16.4: `invalidateQueries` + close modal + `useNotificationQueue` info banner | Locked platform pattern — do not invent a conflict UI (spec §4.7/§5.6) |
| Presigned `signature_url` (1h TTL) | `staleTime: 0` + `<img onError>` → `refetch()`; **no client-side timer** | Spec §5.7 |
| `captured_by_user_id` display | Use a `useUser` hook **if one exists**; otherwise ship `User {id.slice(0,8)}` fallback + note a follow-up | Do not block on user-name resolution (spec §2.7/§5.4) |
| Public `/i/[token]` signature display | **Deferred** (CE-1-FU) — do not touch the public page | Two-spec gate (R2) |
| Web "Capture" button | **None** — capture happens on mobile only; web card is display-only | R3 / spec §2.4 |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```

Record the exact count. Any pre-existing failure → fix or confirm with Tom before starting.

## Pre-Work: Sync API Types (Part A handoff signal — Rule 9.3)

```bash
cd <repo>/frontend
pnpm sync-api-types
grep -n "InvoiceSignoffResponse\|ResolveVarianceRequest\|variance_resolution" packages/shared-types/src/api-schema.d.ts
```

All three must appear. Missing → STOP (Part A not merged). Consume via `components["schemas"][...]` — the spec's local-interface sketches (§2.2/§4.2) are fallback-only; **generated types win**.

## Pre-Work: Verify Endpoints

```bash
grep -A 5 "signoff" backend/openapi_schema_map.md
grep -A 5 "resolve-variance" backend/openapi_schema_map.md
```

| Hook | Endpoint | Verified |
|---|---|---|
| `useInvoiceSignoff` | `GET /api/v1/invoices/{invoice_id}/signoff` | ☐ confirm |
| `useResolveVariance` | `POST /api/v1/payments/{payment_id}/resolve-variance` | ☐ confirm |

## Pre-Work: Read These Source Files

```
dev-docs/architecture-design/batch-designs/batch-ce-1-web-ui-design-spec.md   ← build authority
frontend/apps/web/src/features/invoices/components/InvoiceDetailPage.tsx      ← mount points (spec §2.1 after InvoicePaymentHistory; §3.2 above breadcrumb) + useNotificationQueue usage
frontend/apps/web/src/features/invoices/hooks/useInvoice.ts                   ← PaymentSummaryEntry (extend, Step 1) + query-key convention
frontend/apps/web/src/features/invoices/hooks/useRecordPayment.ts             ← mutation conventions + local PaymentResponse (has amount_variance_cents)
frontend/apps/web/src/features/public-invoice/InvoicePartialPaidState.tsx     ← money-formatting language to mirror
frontend/packages/ui/src/index.ts                                             ← confirm EmptyState/ErrorState/RoleGate/NotificationBanner export paths
frontend/apps/web/src/mocks/handlers/index.ts                                 ← MSW barrel (registration pattern)
frontend/apps/web/src/features/invoices/components/__tests__/                 ← existing MSW/test patterns for this feature
```

Also: `find frontend/apps/web/src/mocks/handlers -name "*.ts" | head -20`, `grep -rn "useUser" frontend/apps/web/src/features --include="*.ts" -l | head -5` (resolves the spec §5.4 name-resolution question), `grep -n "invoices.update\|invoices.view" frontend/packages/ui/src/role-gate/permissions.ts` (spec §5.9 RBAC verification — the map is authoritative; never hardcode role lists).

---

## Context: What This Batch Does

| # | Change | Spec section |
|---|---|---|
| 1 | Extend `PaymentSummaryEntry` with `amount_variance_cents` + 4 resolution fields | §5.3 |
| 2 | `useInvoiceSignoff` hook (D.3) | §2.2 |
| 3 | `useResolveVariance` mutation (D.4) | §4.2 |
| 4 | `InvoiceSignoffCard` (populated/empty/loading/error) | §2 |
| 5 | `OverpaymentReviewBanner` (active/resolved/hidden) | §3 |
| 6 | `ResolveVarianceModal` (3 options + note + 409 path) | §4 |
| 7 | Mount both in `InvoiceDetailPage` behind `<RoleGate permission="invoices.view">` | §2.1/§3.2 |
| 8 | MSW handlers + unit/integration tests | §5.5 |
| 9 | Manual E2E of the pre-built partial-pay flow (verification only) | §5.10 / design §G-R1 |

---

## Step 1 — Extend `PaymentSummaryEntry` (`useInvoice.ts`)

Per spec §5.3: add `amount_variance_cents: number`, `variance_resolution: string | null`, `variance_resolution_note: string | null`, `variance_resolved_at: string | null`, `variance_resolved_by_user_id: string | null`. If Part A's OpenAPI regen already flows these into the generated `InvoiceResponse` payments shape and the file can switch to the generated type cleanly, do that; otherwise extend the local interface (it is the file's existing pattern). Read the file first — adjust to what you find.

Intermediate: `pnpm --filter web check-types`.

## Step 2 — `useInvoiceSignoff.ts`

`features/invoices/hooks/useInvoiceSignoff.ts` per spec §2.2/§5.1: `SIGNOFF_QUERY_KEY = (invoiceId: string) => ["invoice", invoiceId, "signoff"] as const`; `useQuery({ queryKey, queryFn, enabled: !!invoiceId, retry: false, staleTime: 0 })`; `apiClient.get` to D.3; 200-with-no-signoff (`{ signoff: null }`) → return `null`. Type from `@pilot/shared-types`.

## Step 3 — `useResolveVariance.ts`

`features/invoices/hooks/useResolveVariance.ts` per spec §4.2: `useMutation` object-form; `apiClient.post` to D.4 with `{ resolution, note? }`; `retry: false`; `onSuccess` → `queryClient.invalidateQueries({ queryKey: ["invoice", invoiceId] })` + caller's close-modal callback; `onError` → 409 handling per spec §4.7 (invalidate + close + `useNotificationQueue` info notification) — 422/network errors surface inline in the modal instead.

## Step 4 — `InvoiceSignoffCard.tsx`

`features/invoices/components/InvoiceSignoffCard.tsx` per spec §2 **verbatim**: populated grid (signature `<img>` with `onError`→`refetch` recovery §2.6, signer, "Signed at", conditional "Captured on device" + info tooltip, "Captured by" per the §5.4 resolution, conditional superseded-history line), empty state (composed `<EmptyState>`, no CTA — spec §2.4), skeleton loading (§2.5 with reduced-motion fallback), error state (composed `<ErrorState>` with retry). Exact testIDs from the spec. Money/date formats per spec §1 conventions.

## Step 5 — `OverpaymentReviewBanner.tsx`

`features/invoices/components/OverpaymentReviewBanner.tsx` per spec §3: pure derived filter (§3.1 — no memoization, Rule 11), hidden→`null`, active state (§3.3 alert tokens, headline copy anchored "Customer paid {…} over invoice total — review.", per-payment rows, conditional customer comment, Resolve button behind `<RoleGate permission="invoices.update">`), resolved collapsed line (§3.4 with the `resolutionLabel` map), interactions §3.7, animations §3.8.

## Step 6 — `ResolveVarianceModal.tsx`

`features/invoices/components/ResolveVarianceModal.tsx` per spec §4: overlay + panel (design-system §7 tokens), close button, title/subtitle, radio `<fieldset>` with the three verbatim options + helpers (§4.4), note textarea + counter (§4.5), Cancel/Submit (§4.6, submit disabled until a radio is selected), all data states §4.7 (submitting/success/409/422/network), interactions §4.8, animations §4.9. **Accessibility is binding (spec §7.4/§7.5)**: `role="dialog"` + `aria-modal="true"` + `aria-labelledby`; focus trap with return-focus to the Resolve trigger; Escape closes except while `isPending`; background `inert`; labeled controls with `aria-describedby`; errors via `role="alert"`.

## Step 7 — Mount in `InvoiceDetailPage.tsx`

Per spec §2.1 + §3.2: banner at the top of the content wrapper (above breadcrumb) inside `<RoleGate permission="invoices.view">`, passing `invoiceId` + `payments={invoice.payments ?? []}`; card immediately after `<InvoicePaymentHistory>` inside `<RoleGate permission="invoices.view">`. Read the file first; match its actual prop names/structure.

Intermediate: `pnpm --filter web test 2>&1 | tail -6`

## Step 8 — MSW handlers + Tests

**MSW** (spec §5.5): new handler file (follow the existing naming convention from your `find`) covering `GET /api/v1/invoices/:invoiceId/signoff` (populated / `{ signoff: null }` / 500 variants) and `POST /api/v1/payments/:paymentId/resolve-variance` (success extended-PaymentResponse / 409 / 422 variants). Register in `apps/web/src/mocks/handlers/index.ts` — **mandatory barrel step**.

**Seed-data awareness (inclusions §18)**: Part A seeds an overpaid unresolved payment + a signoff row. MSW fixtures must carry varied states: invoice with unresolved overpayment (+customer comment), invoice with resolved overpayment, invoice with no variance, populated signoff, null signoff. Assert by specific content/ID, never counts.

**Unit tests** (co-located `__tests__/`, Vitest — `vi.mock`, `toBeInTheDocument()`, fresh `QueryClient` per test with `retry: false`, MSW `setupServer` + `resetHandlers` in `afterEach`, never mock `apiClient`; mock `next/navigation` where used):
- `InvoiceSignoffCard.test.tsx` — populated render (signer, date, image `alt`), empty (`{signoff:null}` → "No signature captured"), loading skeleton, error + retry, superseded line only when count>0.
- `OverpaymentReviewBanner.test.tsx` — hidden with no variance; active with unresolved (headline copy, comment line); resolved collapsed line with correct label; **RBAC via `AuthContext.Provider`**: owner sees Resolve; a role without `invoices.update` does not; tech (`invoices.view` absent) sees neither banner nor card (RoleGate at the page mount — test at the page level in integration).
- `ResolveVarianceModal.test.tsx` — submit disabled until selection; note counter; success closes + invalidates; 409 → notification + close + invalidate; 422 → inline error stays open; Escape behavior (closed when idle, blocked while submitting); focus trap smoke test.
- `useInvoiceSignoff.test.tsx` / `useResolveVariance.test.tsx` — data shape, error states, query-key construction, correct method/URL/payload.

**Integration tests** — `apps/web/src/__tests__/batch_ce_1/invoice_detail_signoff_variance.integration.test.tsx`: page renders (no 404); RBAC (owner sees banner+card; tech sees neither); banner→modal→resolve happy path fires `POST` to the exact URL with `{ resolution, note }` payload and the banner collapses on refetch.

## Step 9 — Manual E2E: partial-pay verification (no code — design §G-R1)

The plan card's "Pay remaining" CTA was found already built. Verify it end-to-end against your local stack and record the result in your Completion Summary:

1. Seed/create an issued invoice → generate/open its public link (`/i/[token]`).
2. Pay a **partial** amount with a variance comment → confirm the page shows payment history + remaining balance + **"Pay remaining"** and **"Pay different amount"** affordances (arch §18.6).
3. Click "Pay remaining" → complete payment → confirm fully-paid state with payment history.
4. Confirm `balance_due_cents` decremented correctly at each step and the payment records carry `amount_variance_cents` + comment.
5. Note any breakage as a `UI-BUG-x`/`INT-BUG-x` candidate in the Completion Summary — do not fix in this batch unless trivial.

---

## Final Verification

> ❌ **BANNED**: `npx vitest run` in any form. Web tests run via `pnpm --filter web test` only.

### Phase 1 — Targeted (after each step)

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -6
pnpm --filter web test -- apps/web/src/__tests__/batch_ce_1/ 2>&1 | tail -10
```

### Phase 2 — Full canonical command (once, at the end)

```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

Any failure in either phase → fix before done. Zero ESLint `no-hardcoded-design-values` warnings (token-only per spec).

---

## Definition of Done — CE-1 Part C

- [ ] Regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run; `InvoiceSignoffResponse` / `ResolveVarianceRequest` / `variance_resolution` confirmed in `api-schema.d.ts` (Part A merged)
- [ ] Both endpoints verified in `openapi_schema_map.md`
- [ ] Web UI spec + design doc fully read; all mandatory source files read
- [ ] Step 1: `PaymentSummaryEntry` extended (5 fields)
- [ ] Steps 2–3: hooks per spec §5.1 (object-form, `retry: false`, colocated keys, generated types)
- [ ] Step 4: card matches spec §2 — all four states, exact testIDs, `onError` refetch recovery, EmptyState composed (no CTA)
- [ ] Step 5: banner matches spec §3 — derived filter, three visibility states, RoleGate on Resolve, verbatim headline copy
- [ ] Step 6: modal matches spec §4 — three verbatim options, focus trap + return focus + Escape rules + `inert`, 409 composition per §4.7
- [ ] Step 7: mounts per spec §2.1/§3.2 behind `invoices.view` RoleGate
- [ ] Step 8: MSW handlers registered in barrel; unit tests per component/hook; integration in `__tests__/batch_ce_1/`; RBAC tests via `AuthContext.Provider` (tech excluded)
- [ ] Step 9: manual E2E partial-pay pass documented (4 checkpoints) in Completion Summary
- [ ] No hand-written memoization; no raw `fetch`; no new `packages/ui` components; token-only styling
- [ ] axe-core zero violations on invoice detail; WCAG spot-checks per spec §7 (target sizes, focus-visible, non-color-only status)
- [ ] **Phase 1** targeted pass; **Phase 2** full canonical command passes (`=== MVP FINAL VERIFICATION COMPLETE ===`)
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to `pilot-launch-plan.md` Appendix C

---

## Completion Summary

Add to `dev-docs/analysis/pilot-launch-plan.md` **Appendix C**:

```markdown
### CE-1 (Part C) — Web Invoice Detail: Sign-Off Card + Overpayment Review: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer (web)
**Baseline**: X passed (web)
**Final**: X+N passed (+N new tests)

#### What Was Accomplished
- …

#### Files Changed / Created
| File | Action |
|---|---|

#### Tests Added
| Test File | Type | Tests | All Pass |
|---|---|---|---|

#### Manual E2E (Partial-Pay Verification — design §G-R1)
- [checkpoints 1–4 results; any UI-BUG-x/INT-BUG-x candidates noted]

#### Follow-Ups
- `captured_by_user_id` name resolution: [useUser hook found + used | UUID fallback shipped — follow-up ticket noted]
- CE-1-FU (deferred): public `/i/[token]` signature display block (marketing-ui surface)
```

---

## After This Task — Next Step

This is **Part C of 3 — the final CE-1 implementation batch.** When done: commit + push + report. The Architect then closes CE-1 in the launch plan (§2.0 row → ✅, Appendix A registry row, card update) and files CE-1-FU (public-page signature display) as a post-beta fast-follow candidate.
