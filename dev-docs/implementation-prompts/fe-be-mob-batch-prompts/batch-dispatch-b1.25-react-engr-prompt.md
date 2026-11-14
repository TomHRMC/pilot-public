# Implementation Prompt: DISPATCH-B1.25 (Part B) — Render Multi-Tech Commitment Chips (Day-Tech View)

**Mode**: Pilot React Engineer
**Batch**: DISPATCH-B1.25 (Part B — Frontend web)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-dispatch-b1.25-design.md` — every section (esp. §F, §H, §I)
**Estimated session**: 2–3 hours
**Platform**: Web only (`apps/web`)
**Backend companion**: DISPATCH-B1.25 (Part A). **Part A MUST be complete + OpenAPI regenerated before you start.**
**Depends on**: DISPATCH-B1 (Part B) — `DispatchGridDayView` + `JobBlock` this batch modifies must already exist.

---

## ⚠️ MANDATORY STOP: Read These First

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`batch-dispatch-b1.25-design.md`** — all sections
- **`dispatch-b1-ui-design-spec.md`** — §Surface 1 (day-tech row structure this extends)

Critical rules for this batch:

- **Rule 1.3**: Run `pnpm sync-api-types` FIRST — Part A added `additional_job_commitments` + `assignment_role`. Consume from `@pilot/shared-types`, never hand-write.
- **Rule 2**: All API via `apiClient`. `fetch()` banned.
- **Rule 7**: Reuse existing components — this batch adds a **variant** to the existing `JobBlock`, it does not create a new block component.
- **Rule 8**: No new npm deps.
- **Rule 10**: Any failing test — even apparently pre-existing — fixed before done. Root cause unclear → STOP and ask Tom.

---

## Design Decisions (Do Not Re-Litigate)

From design doc §E/§G — final:

| Decision | Outcome |
|---|---|
| Data model | `jobs[]` stays primary-only; commitments come from the NEW `additional_job_commitments` per tech. **Never flatten commitments into the canonical `jobs[]`** (breaks lane/month/week-lane). |
| Draggability | Only **primary** job blocks are draggable (a move reschedules the whole crew). Commitment chips are **read-only** — no drag, no `/move`. |
| Reassignment | Out of scope — crew changes go through the existing `TechAssignmentSection` in `JobPropertiesPanel`. |
| Role display | Show the `assignment_role` string as a badge ("Helper", etc.). Do NOT hardcode a closed enum — render whatever string the API returns (capitalize for display). |
| Scope | **Day-tech only** (`DispatchGridDayView`). Lane mode + month untouched. Week-tech inherits this in DISPATCH-B1.5. |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```
Record the count. Fix any pre-existing failure (or confirm with Tom) before starting.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```
Confirm the new fields:
```bash
grep -A 25 "DispatchBoardTechGroup" frontend/packages/shared-types/src/api-schema.d.ts | grep "additional_job_commitments"
grep -A 20 "DispatchBoardJobEntry" frontend/packages/shared-types/src/api-schema.d.ts | grep "assignment_role"
```
Both must appear. If not → Part A isn't deployed/committed. STOP and confirm with Tom.

---

## Pre-Work: Verify Endpoints

No new endpoints — this batch consumes new **fields** on the existing `GET /api/v1/scheduling/dispatch-board` response. Confirm:
```bash
grep -A 5 "dispatch-board" backend/openapi_schema_map.md
```

---

## Pre-Work: Read These Source Files

```
frontend/apps/web/src/features/dispatch-board/hooks/useDispatchBoard.ts             ← normalization: keep jobs[] primary-only; carry commitments per tech + assignment_role
frontend/apps/web/src/features/dispatch-board/components/DispatchGridDayView.tsx     ← render commitment chips per tech row
frontend/apps/web/src/features/dispatch-board/components/JobBlock.tsx                ← add read-only commitment variant + role badge
frontend/apps/web/src/features/dispatch-board/components/DispatchBoardLanes.tsx      ← confirm it consumes jobs[] only (must stay untouched)
frontend/apps/web/src/features/dispatch-board/types-stub.ts                          ← align to synced types
frontend/apps/web/src/mocks/handlers/dispatchBoardHandlers.ts                        ← add commitments to a mock tech group
frontend/apps/web/src/mocks/handlers/index.ts                                        ← barrel
```

---

## Context: What This Batch Does

| Area | Change |
|---|---|
| `useDispatchBoard` | Carry `additional_job_commitments` per tech into the normalized shape (as `commitments`), WITHOUT flattening into `jobs[]`; carry `assignment_role` on normalized jobs |
| `JobBlock` | Add `variant="commitment"` (muted, `cursor-default`, no drag listeners) + a role badge slot |
| `DispatchGridDayView` | Render each tech's `commitments` as read-only chips at their scheduled positions, alongside the tech's draggable primary blocks |

Follow the design doc §H for the chip visual. Code examples are starting points — read each file first.

---

## STEP 1 — `useDispatchBoard` normalization

**File**: `useDispatchBoard.ts`

- Keep `jobs[]` exactly as today: `assignedJobs = techs.flatMap(g => g.jobs)` + `unassigned`. **Do not add commitments here.**
- Carry `assignment_role` through `normalizeJob` (add the field to the normalized job shape).
- Add commitments to the normalized per-tech data so `DispatchGridDayView` can read them. Two options — pick the one that fits the existing normalized shape after reading the file:
  - (a) Return a `commitmentsByTechId: Record<string, DispatchBoardJob[]>` map alongside `techs`/`jobs`, OR
  - (b) Attach `commitments: DispatchBoardJob[]` onto each normalized tech object.
- Normalize each commitment via the same `normalizeJob` (pass the helper tech's id + `assignment_role` from the raw entry). Enrich labels the same way (`job_number`/`customer_name` already populate from Part A/B1).

> Verify the raw response shape post-sync — `RawTechGroup` now includes `additional_job_commitments: RawJobEntry[]` and `RawJobEntry` includes `assignment_role`. Update the raw interfaces to match.

Intermediate (hook widely consumed):
```bash
pnpm --filter web test -- apps/web/src/features/dispatch-board 2>&1 | tail -10
```

---

## STEP 2 — `JobBlock` commitment variant

**File**: `JobBlock.tsx`

Add a `variant?: 'primary' | 'commitment'` prop (default `'primary'`). When `'commitment'`:
- Do NOT attach `@dnd-kit` `useDraggable` listeners/attributes — render as a static positioned div. `cursor-default`, muted style (lighter/dashed border, e.g. `border-dashed border-neutral-300 opacity-90`) per design §H.
- Render a small **role badge** (from `assignment_role`, capitalized) in a corner: `text-caption` pill `bg-neutral-100 text-neutral-600 rounded px-1`.
- Left-click still calls `onClick` (→ `JobPropertiesPanel`); `onContextMenu` still fires the shared menu. Only drag is removed.

> Read the file first — `JobBlock` currently always wires `useDraggable`. Guard that behind `variant === 'primary'`. Keep the primary path pixel-identical to today.

---

## STEP 3 — Render commitments in `DispatchGridDayView`

**File**: `DispatchGridDayView.tsx`

For each tech row, in addition to the tech's primary jobs (existing), render their `commitments` as `<JobBlock variant="commitment" ...>` using the **same** absolute-positioning math (`dateToPx` for `left`/`width`). Commitment chips coexist with primary blocks in the same row — stack/overlay per the existing positioning; do not add them to any droppable payload.

- Commitment-only techs (empty `jobs[]`, populated `commitments`) already render as a row because Part A returns them in `techs[]` — confirm the row appears and shows only commitment chips.
- Do NOT include commitment chips in the drop/over-capacity detection — they are not moveable and their presence should not block a primary drop (design intent: they're informational availability markers; MVP keeps capacity logic on primary jobs).

Intermediate:
```bash
pnpm --filter web test -- apps/web/src/features/dispatch-board 2>&1 | tail -10
```

---

## MSW Handlers

Extend the existing tech-group fixture in `dispatchBoardHandlers.ts` so at least one tech has `additional_job_commitments: [ ... ]` (a job entry with `assignment_role: "helper"`), and add a commitment-only tech group (empty `jobs`, populated `additional_job_commitments`). Keep the barrel registration in `index.ts` intact. Don't duplicate an existing path handler.

---

## Test Requirements

Web = Vitest + `@testing-library/react`; mock `next/navigation`; QueryClient `retry: false`; MSW at HTTP level; `afterEach(server.resetHandlers())`.

**Unit tests**:
- `JobBlock` — `variant="commitment"` renders the role badge, has NO drag attributes (`cursor-default`), still fires `onClick`/`onContextMenu`.
- `useDispatchBoard` — commitments are carried per tech and are NOT present in the flattened `jobs[]` (assert the commitment job id does not appear in `jobs`).

**Integration tests** (`apps/web/src/__tests__/batch_dispatch_b1_25/`):
- Day-tech view: a helper tech's row shows the commitment chip with a "Helper" badge; the same job also shows (draggable) under its primary tech.
- Commitment-only tech renders a row with only a read-only chip.
- Lane mode (`layoutMode="lane"`) does NOT render commitment chips (consumes `jobs[]` only) — the commitment job id is absent from the lane render.
- Commitment chip is not draggable (no `@dnd-kit` drag start on pointer-move ≥8px) — assert no `/move` fires.

Assert by IDs/content from MSW fixtures, never total counts.

---

## Final Verification

> ❌ BANNED: `npx vitest run`. Only `pnpm --filter web test`.

### Phase 1 — Targeted
```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/features/dispatch-board 2>&1 | tail -10
pnpm --filter web test -- apps/web/src/__tests__/batch_dispatch_b1_25/ 2>&1 | tail -10
```
### Phase 2 — Full
```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```
Any failure in either phase fixed before done.

---

## Definition of Done — DISPATCH-B1.25 (Part B)

- [ ] Regression baseline captured (zero pre-existing failures or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — `additional_job_commitments` + `assignment_role` present
- [ ] Design doc + UI spec §Surface 1 read
- [ ] All mandatory source files read
- [ ] **STEP 1**: `useDispatchBoard` carries commitments per tech + `assignment_role`; `jobs[]` stays primary-only (commitments NOT flattened in)
- [ ] **STEP 2**: `JobBlock` `variant="commitment"` — muted, no drag, role badge, click/context-menu preserved
- [ ] **STEP 3**: `DispatchGridDayView` renders commitment chips per tech row; commitment-only techs render
- [ ] Lane mode + month view untouched (no commitment chips there)
- [ ] Commitment chips excluded from drop/over-capacity detection
- [ ] MSW fixtures updated (helper commitment + commitment-only tech); barrel intact
- [ ] Unit + integration tests pass (targeted)
- [ ] **Phase 2 FULL verification passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`)
- [ ] Final test count documented
- [ ] Completion Summary added to launch plan Appendix B

---

## Completion Summary

Add to `pilot-launch-plan.md` Appendix B (React template). Note that **DISPATCH-B1.5 (week-tech)** must render the same `JobBlock variant="commitment"` chips from `additional_job_commitments` when it builds the transposed week-tech view — the field + component variant are now in place.
