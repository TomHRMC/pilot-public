# Implementation Prompt: DISPATCH-B1.5 (Part B) — Week-Lane Grid + Week Toggle + Site Name in Panel

**Mode**: Pilot React Engineer
**Batch**: DISPATCH-B1.5 (Part B — Frontend web)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 DISPATCH-B1.5
**Design doc**: `batch-dispatch-b1-design.md §Split` (corrected geometry 2026-07-26)
**UI design spec**: `dispatch-b1.5-ui-design-spec.md` — every section (authoritative for all pixels/classes)
**Estimated session**: 3–4 hours
**Platform**: Web only (`apps/web`)
**Backend companion**: DISPATCH-B1.5 (Part A — `site_name`). **Part A must be complete + OpenAPI regenerated before you start.**
**Depends on**: DISPATCH-B1 (pipeline, `UnassignedTray`, `layoutMode`, `JobContextMenu`, lane helpers) + DISPATCH-B1.25 — all merged.

---

## ⚠️ MANDATORY STOP: Read These First

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dispatch-b1.5-ui-design-spec.md`** — every section (Surface 1 `DispatchWeekLaneView`, Surface 2 toggle, Surface 3 page routing, Reuse Inventory, all 12 Implementation Notes)
- **`dispatch-b1-ui-design-spec.md`** — the day-board spec the B1.5 spec mirrors (JobBlock, UnassignedTray, right-rail arbitration)

Critical rules for this batch:

- **Rule 1.3**: Run `pnpm sync-api-types` FIRST — Part A added `site_name`.
- **Rule 2**: All API via `apiClient`. `fetch()` banned.
- **Rule 7**: Reuse existing components — `UnassignedTray`, `JobContextMenu`, `ConflictPreviewPane`, `useMoveJob`, `useCheckConflicts`, and the lane helpers are all built (B1). Do NOT recreate them.
- **Rule 8**: No new npm deps (`@dnd-kit/core` already installed).
- **Rule 9**: Route files stay thin — all work in `features/dispatch-board/`.
- **Rule 10**: Any failing test — even apparently pre-existing — fixed before done. Root cause unclear → STOP and ask Tom.

---

## Design Decisions (Do Not Re-Litigate)

From the UI spec + design doc — final:

| Decision | Outcome |
|---|---|
| Week geometry | **Days = rows, columns = lanes** (`DispatchWeekLaneView`). Lane/Tech toggle swaps the column dimension. |
| Week-tech view | **UNTOUCHED** — do NOT modify `DispatchWeekView.tsx`. It keeps its own inline `ContextMenu`, its own `DndContext` gets reconciled only via page routing, and its `WeekCommitmentChip`. (See Impl Note 11.) |
| Commitment chips in lane mode | **NONE** — lane mode shows primary jobs only. No `WeekCommitmentChip`. (Impl Note 2 — add the confirming code comment.) |
| 5-day/7-day toggle | Retained in week mode for both lane and tech. |
| Lane drop `tech_user_id` | **Preserve the job's existing tech** (from `primary_assignment_id`'s tech); omit `tech_user_id` if unassigned. A lane move is a **time-only reschedule** — lanes are client-computed, never stored. (Impl Note 6 — this supersedes the earlier `null` sketch in Surface 3.) |
| DnD context | Single `DndContext` at `DispatchBoardPage` (B1). `DispatchWeekLaneView` registers droppables/draggables inside it — no internal context. (Impl Note 1.) |
| Lane helpers | Import `assignJobsToLanes` from the shared util B1 extracted (`utils/laneHelpers.ts` or `timeHelpers.ts`) — do NOT copy inline. (Impl Note 3.) |

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
grep -A 25 "DispatchBoardJobEntry" frontend/packages/shared-types/src/api-schema.d.ts | grep "site_name"
```
`site_name` must appear. If not → Part A isn't deployed/committed. STOP and confirm with Tom.

---

## Pre-Work: Verify Endpoints

No new endpoints — week-lane drops reuse B1's `/api/v1/scheduling/jobs/{id}/move` + `/check-conflicts`. Confirm they're present:
```bash
grep -E "scheduling/jobs.*(move|check-conflicts)" backend/openapi_schema_map.md
```

---

## Pre-Work: Read These Source Files

```
frontend/apps/web/src/features/dispatch-board/components/DispatchWeekView.tsx          ← structural template (days-rows × tech-cols); mirror for week-lane. DO NOT MODIFY.
frontend/apps/web/src/features/dispatch-board/components/DispatchBoardLanes.tsx         ← assignJobsToLanes usage + lane label pattern
frontend/apps/web/src/features/dispatch-board/components/DispatchBoardPage.tsx          ← week routing to modify; beginMove pipeline; handlers to reuse
frontend/apps/web/src/features/dispatch-board/components/DispatchToolbar.tsx            ← extend Lane|Tech toggle condition to week
frontend/apps/web/src/features/dispatch-board/components/JobPropertiesPanel.tsx         ← add site name line (customer + site name + address)
frontend/apps/web/src/features/dispatch-board/components/JobContextMenu.tsx             ← reuse (add DispatchWeekLaneView as a consumer)
frontend/apps/web/src/features/dispatch-board/utils/laneHelpers.ts (or timeHelpers.ts) ← where assignJobsToLanes lives after B1 (confirm path)
frontend/apps/web/src/features/dispatch-board/store.ts                                  ← layoutMode already exists (B1); no new fields
frontend/apps/web/src/features/dispatch-board/hooks/useDispatchBoard.ts                 ← confirm site_name carried through normalizeJob
```

Locate the lane helper:
```bash
grep -rn "assignJobsToLanes" frontend/apps/web/src/features/dispatch-board/
```

---

## Context: What This Batch Does

| Area | Change |
|---|---|
| `DispatchWeekLaneView` | **New** — days-as-rows × lane-columns grid (UI spec Surface 1) |
| `DispatchToolbar` | One-line condition: render Lane\|Tech toggle in week too (Surface 2) |
| `DispatchBoardPage` | Route week → lane vs tech on `layoutMode`; add `handleWeekLaneDrop` (Surface 3) |
| `JobPropertiesPanel` | Add site name line so panel shows customer + site name + address |
| `useDispatchBoard` | Carry `site_name` through `normalizeJob` (if not already) |
| `laneHelpers.ts` | Confirm `assignJobsToLanes` is exported from a shared util (extract if B1 left it inline in `DispatchBoardLanes`) |

Follow the UI spec for every pixel/class. Code examples are starting points — read each file first.

---

## STEP 1 — Confirm/extract shared `assignJobsToLanes`

Per UI spec Impl Note 3: `DispatchWeekLaneView` imports `assignJobsToLanes` from a shared util. If B1 already extracted it to `utils/laneHelpers.ts` (or `timeHelpers.ts`), import from there. If it's still inline in `DispatchBoardLanes.tsx`, extract it to `utils/laneHelpers.ts` and update `DispatchBoardLanes` to import it — no behavior change. Verify with the grep above before deciding.

---

## STEP 2 — `useDispatchBoard`: carry `site_name`

**File**: `useDispatchBoard.ts`. Confirm `normalizeJob` carries `site_name` from the raw entry onto the normalized job (B1 added `site_address`/`customer_name` here — add `site_name` alongside). Update the `RawJobEntry` interface to include `site_name`.

---

## STEP 3 — `DispatchWeekLaneView` (new)

**File**: `features/dispatch-board/components/DispatchWeekLaneView.tsx` — build to UI spec **Surface 1** exactly. Key points:
- `<table>`: sticky day-row headers (left, `z-10`), sticky lane-column headers `L1…L5` (top, `z-20`), corner `z-30`. Constants `LANE_COL_WIDTH_PX=160`, `ROW_HEADER_WIDTH_PX=96`, `CAPACITY_LIMIT=4`.
- **Always render all `laneCount` columns** even when empty.
- Per-day `assignJobsToLanes(dayJobs, laneCount)` in a `useMemo` keyed to `[jobs, laneCount, weekDates]` → `jobsByDayAndLane[dateStr][laneIndex]`.
- `WeekLaneCell` = `useDroppable` `id: "cell-lane{laneIndex}-{dateStr}"`, `data: { laneIndex, dateStr }`; over-capacity when `jobs.length >= CAPACITY_LIMIT`.
- `WeekLaneJobCard` = same visual as `WeekJobCard` but **neutral left border** (`border-l-neutral-300`, no tech color); label = time range + `title ?? job_number` + `customer_name`; `useDraggable` `id: "job-{id}"`.
- **No `WeekCommitmentChip`** — add the confirming comment from Impl Note 2.
- Time-of-day preservation on drop (Impl Note / Surface 1 "Drop Handler Logic").
- Mobile fallback (`md:hidden`) mirroring `DispatchWeekView`.
- Accessibility: `role="gridcell"` + `aria-label` per Impl Note 12.

Intermediate:
```bash
pnpm --filter web test -- apps/web/src/features/dispatch-board 2>&1 | tail -10
```

---

## STEP 4 — `DispatchToolbar` toggle in week mode

**File**: `DispatchToolbar.tsx` — per Surface 2, change the Lane|Tech render condition from `viewTab === "day"` to `viewTab === "day" || viewTab === "week"`. The 5d/7d toggle already renders in week — leave it. No other change.

---

## STEP 5 — `DispatchBoardPage` week routing + `handleWeekLaneDrop`

**File**: `DispatchBoardPage.tsx` — per Surface 3:
- Replace the single `{viewTab === "week" && <DispatchWeekView .../>}` with two branches: `layoutMode === "lane"` → `DispatchWeekLaneView`; `layoutMode === "tech"` → existing `DispatchWeekView`.
- Add `handleWeekLaneDrop(jobId, laneIndex, dateStr, newStartTime)` → computes `end` from the job's duration, then calls the unified `beginMove`. **Per Impl Note 6**: pass the job's **existing** tech (resolve from the job's `tech_id`/`primary_assignment_id`), NOT `null`; if the job is unassigned, omit `tech_user_id`. A lane move is a time-only reschedule.
- `DispatchWeekLaneView` registers inside the page-level `DndContext` (already lifted in B1). Ensure the page's `handleDragEnd` routes drops whose `over.data` carries `{ laneIndex, dateStr }` to `handleWeekLaneDrop` (distinguish from day-lane's `{ laneIndex }`-only and day-tech's `{ techId }` payloads).
- Add `DispatchWeekLaneView` as a `JobContextMenu` consumer (pass `onJobContextMenu`).

Intermediate:
```bash
pnpm --filter web test -- apps/web/src/features/dispatch-board 2>&1 | tail -10
```

---

## STEP 6 — `JobPropertiesPanel`: customer + site name + address

**File**: `JobPropertiesPanel.tsx` — in the Customer & Site section (which already shows `customer_name` + `site_address` from B1), add a **site name** line between them so the order is: customer name → **site name** → site address. Render the site-name line only when `site_name` is present. Use the existing caption/label styling in that section — read the file and match. No new component.

---

## Test Requirements

Web = Vitest + `@testing-library/react`; mock `next/navigation`; QueryClient `retry: false`; MSW at HTTP level; `afterEach(server.resetHandlers())`. Per UI spec §Tests:

**Unit / integration** (`apps/web/src/__tests__/batch_dispatch_b1_5/`):
- `DispatchWeekLaneView` renders `laneCount` columns (`laneCount=5` → 5 `L1…L5` headers).
- Per-day `assignJobsToLanes`: 2 non-overlapping Monday jobs → same lane column; 2 overlapping → split across L1/L2.
- Empty cell renders dashed border.
- Over-capacity (4 jobs) blocks a 5th drop — "Capacity exceeded" chip, `onJobDrop` NOT called.
- Under-capacity drop calls `onJobDrop(jobId, laneIndex, dateStr, newStartTime)` once.
- No commitment chips in lane mode (assert none of the `border-dashed` commitment indicators render).
- Lane|Tech toggle in week: `layoutMode="lane"` → `DispatchWeekLaneView`; click "Tech" → `DispatchWeekView`.
- 5d/7d retained: switch to 7d → 7 day rows.
- Mobile fallback text visible < `md`.
- `JobPropertiesPanel` renders customer + site name + address when `site_name` present; omits the site-name line when null.
- Lane drop fires `beginMove` → `/move` with the job's existing tech (not null) — assert the mutation body.

MSW: no new handlers (B1's `/move` + `/check-conflicts` cover it); reuse existing dispatch fixtures, ensure at least one has `site_name`.

---

## Final Verification

> ❌ BANNED: `npx vitest run`. Only `pnpm --filter web test`.

### Phase 1 — Targeted
```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/features/dispatch-board 2>&1 | tail -10
pnpm --filter web test -- apps/web/src/__tests__/batch_dispatch_b1_5/ 2>&1 | tail -10
```
### Phase 2 — Full
```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```
Any failure in either phase fixed before done.

---

## Definition of Done — DISPATCH-B1.5 (Part B)

- [ ] Regression baseline captured (zero pre-existing failures or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — `site_name` present
- [ ] UI spec + day-board spec read
- [ ] All mandatory source files read
- [ ] **STEP 1**: `assignJobsToLanes` imported from a shared util (extracted if needed)
- [ ] **STEP 2**: `useDispatchBoard` carries `site_name`
- [ ] **STEP 3**: `DispatchWeekLaneView` — days-rows × lane-cols, always-render lanes, per-day lane assignment, no commitment chips (+ confirming comment), mobile fallback, a11y
- [ ] **STEP 4**: `DispatchToolbar` Lane|Tech toggle renders in week; 5d/7d retained
- [ ] **STEP 5**: `DispatchBoardPage` week routing on `layoutMode`; `handleWeekLaneDrop` preserves existing tech (Impl Note 6); drop routing distinguishes week-lane payload; `DispatchWeekLaneView` added as `JobContextMenu` consumer
- [ ] **STEP 6**: `JobPropertiesPanel` shows customer + site name + address (site-name line conditional)
- [ ] `DispatchWeekView.tsx` NOT modified (untouched constraint)
- [ ] Tests pass (targeted)
- [ ] **Phase 2 FULL verification passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`)
- [ ] Final test count documented
- [ ] Completion Summary added to launch plan Appendix B

---

## Completion Summary

Add to `pilot-launch-plan.md` Appendix B (React template). This closes the DISPATCH-B1 → B1.25 → B1.5 sequence: the dispatch board now has full Day + Week parity in both Lane and Tech modes, a unified move/conflict pipeline, shared unassigned tray, multi-tech commitment visibility, and customer/site-name/address in the properties panel. Note that **DISPATCH-B2** (filter bar redesign) is the next dispatch batch.
