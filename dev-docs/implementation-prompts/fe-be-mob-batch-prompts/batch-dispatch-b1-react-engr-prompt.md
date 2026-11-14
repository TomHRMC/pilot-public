# Implementation Prompt: DISPATCH-B1 (Part B) — Day Board: Lane/Tech Toggle + Unassigned Tray + Unified Move Pipeline

**Mode**: Pilot React Engineer
**Batch**: DISPATCH-B1 (Part B — Frontend web)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 DISPATCH-B1
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-dispatch-b1-design.md` — every section (A–I)
**UI design spec**: `dev-docs/architecture-design/batch-designs/dispatch-b1-ui-design-spec.md` — all 5 surfaces
**Estimated session**: 4–5 hours
**Platform**: Web only (`apps/web`)
**Backend companion**: DISPATCH-B1 (Part A — Pilot Python Engineer). **Part A MUST be complete + OpenAPI regenerated before you start.**

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`batch-dispatch-b1-design.md`** — every section (A–I), especially §D.2/§D.3 (real contracts), §E (patterns), §G (locked decisions)
- **`dispatch-b1-ui-design-spec.md`** — all 5 surfaces + Implementation Notes

Critical rules for this batch:

- **Rule 1.1**: Before writing ANY hook, verify the endpoint exists in `backend/openapi_schema_map.md`. The current `useMoveJob`/`useCheckConflicts` target **non-existent** `/schedule/...` paths — you are FIXING them to the real `/scheduling/...` paths. If a path is not in the map → STOP and ask Tom.
- **Rule 1.3**: Run `pnpm sync-api-types` FIRST — all backend payload types come from `@pilot/shared-types`, never hand-written. Part A added new `DispatchBoardJobEntry` fields you must consume.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned for `/api/v1/...`. **You will delete a raw `apiClient.patch('/api/v1/jobs/{id}')` double-write** — do not replace it with another raw PATCH; route through the move pipeline.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any component — `<LoadingState>`, `<ErrorState>`, `<EmptyState>`, `<RoleGate>` are available.
- **Rule 8**: No new npm dependencies. `@dnd-kit/core` and `@heroicons/react` are already installed (used by `DispatchBoardLanes`/`DispatchWeekView`) — confirm in `package.json`.
- **Rule 9**: Route files in `apps/web/src/app/(authed)/` stay thin — no logic here. All work is in `features/dispatch-board/`.
- **Rule 10**: If ANY test fails during your work — even apparently pre-existing — fix it before declaring done. If you can't find the root cause → STOP and ask Tom.

---

## Design Decisions (Do Not Re-Litigate)

From design doc §G — these are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Move pipeline | Unify ALL day DnD (day-lane + day-tech + tray drag-out) through `check-conflicts → ConflictPreviewPane → confirm → move`; **delete the raw-PATCH double-write** | Coherent UX; fixes double-write bug (§G.1) |
| Day-tech DnD library | Build `DispatchGridDayView` on **`@dnd-kit`** — do NOT extract the deprecated `react-dnd` `DispatchGrid.tsx` | Single-library board (§G.2) |
| Click behavior | Left-click → `JobPropertiesPanel`; right-click → `JobContextMenu` (only). Add context menu to day-lane (has none today) | Parity across views (§G.4) |
| Unassigned | Single top `UnassignedTray` (`data-testid="unassigned-tray"`) — **replaces** day view's bottom queue | One canonical surface (§G.5) |
| Toggle persistence | `layoutMode: 'lane'\|'tech'`, default `'lane'`, **no persist middleware** — survives view-tab switch, resets on reload | §G.6 |
| Right rail | ONE 320px slot — `ConflictPreviewPane` has strict priority over `JobPropertiesPanel`; never both | UI spec §4 |
| Week views | **OUT OF SCOPE** — DISPATCH-B1.5. Do not touch `DispatchWeekView`/`MonthCalendarGrid` beyond what the lifted `DndContext` requires | Batch split (§Split) |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```

Record the exact count. Must still pass at the end.

> If any tests are already failing before you start: confirm with Tom it's a known accepted failure, or fix it before touching batch files. Do not proceed on an unexplained red suite.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

This regenerates `packages/shared-types/src/api-schema.d.ts` from Part A's OpenAPI. Confirm the new `DispatchBoardJobEntry` fields (`version`, `primary_assignment_id`, `assignment_version`, `job_number`, `customer_name`, `site_address`, `title`) are present:

```bash
grep -A 20 "DispatchBoardJobEntry" frontend/packages/shared-types/src/api-schema.d.ts | grep -E "version|assignment|job_number|customer_name|site_address|title"
```

> If `pnpm sync-api-types` does NOT show these fields → Part A is not deployed/committed. STOP and confirm with Tom before proceeding (do not hand-write the types).

After syncing, retire the stale hand-written stubs in `types-stub.ts` that the synced types now cover (`version`, assignment ids, labels). Keep only what the synced schema still doesn't provide, and mark each remaining stub `// TODO: delete when api-schema covers this`.

---

## Pre-Work: Verify Endpoints

The move/conflict hooks currently target **wrong** paths. Confirm the REAL endpoints before rewriting:

```bash
grep -A 5 "scheduling/jobs" backend/openapi_schema_map.md | grep -E "move|check-conflicts"
```

Verified endpoints for this batch:
| Hook | Endpoint | Verified |
|---|---|---|
| `useMoveJob` | `POST /api/v1/scheduling/jobs/{id}/move` | grep openapi_schema_map.md |
| `useCheckConflicts` | `POST /api/v1/scheduling/jobs/{id}/check-conflicts` | grep openapi_schema_map.md |
| `useDispatchBoard` | `GET /api/v1/scheduling/dispatch-board` | already exists |

**Real request/response shapes** (design doc §D.2/§D.3):
- **move** request: `{ tech_user_id, scheduled_start_at, scheduled_end_at, expected_job_version, expected_assignment_version? }`
- **move** response: `{ job_id, job_version, assignment_id, assignment_version, tech_user_id, scheduled_start_at, scheduled_end_at, conflicts[] }`
- **move** 409 body (RFC7807): `{ ..., current_job_version, current_state: { scheduled_start_at, scheduled_end_at } }`
- **check-conflicts** request: `{ tech_user_id, scheduled_start_at, scheduled_end_at }`
- **check-conflicts** response: `{ is_feasible, conflicts: dict[], drive_time_to_next_minutes?, drive_time_from_prev_minutes? }` — conflict dicts use `conflict_type` (NOT `conflict_class`)

> If any endpoint is NOT in `openapi_schema_map.md` → STOP. Do not invent a URL. Ask Tom.

---

## Pre-Work: Read These Source Files

Read each with `read_file` before writing any code:

```
frontend/apps/web/src/features/dispatch-board/store.ts                              ← add layoutMode; activate conflictPreview* fields
frontend/apps/web/src/features/dispatch-board/hooks/useMoveJob.ts                   ← REWRITE to /move contract
frontend/apps/web/src/features/dispatch-board/hooks/useCheckConflicts.ts            ← REWRITE to /check-conflicts contract
frontend/apps/web/src/features/dispatch-board/components/DispatchBoardPage.tsx      ← lift DndContext, beginMove pipeline, right-rail arbitration, mount tray + menu
frontend/apps/web/src/features/dispatch-board/components/DispatchBoardLanes.tsx     ← extract JobBlock, remove bottom queue + own DndContext, add onContextMenu
frontend/apps/web/src/features/dispatch-board/components/ConflictPreviewPane.tsx    ← add w-80 shell class; XMarkIcon; consume adapter output
frontend/apps/web/src/features/dispatch-board/components/JobPropertiesPanel.tsx     ← reference for right-rail box geometry (w-80)
frontend/apps/web/src/features/dispatch-board/components/DispatchWeekView.tsx       ← reference for the inline context-menu pattern to extract
frontend/apps/web/src/features/dispatch-board/components/DispatchToolbar.tsx        ← add Lane|Tech PillToggle (reuse existing PillToggle)
frontend/apps/web/src/features/dispatch-board/hooks/useMoveJob.ts                   ← useStalenessRetry usage
frontend/apps/web/src/mocks/handlers/index.ts                                       ← how to register MSW handlers
frontend/apps/web/src/mocks/handlers/dispatchBoardHandlers.ts                       ← existing dispatch handlers to extend
frontend/packages/ui/src/index.ts                                                   ← confirm LoadingState/ErrorState/EmptyState exports
```

Locate related files:
```bash
find frontend/apps/web/src/features/dispatch-board -name "*.ts" -o -name "*.tsx" | head -40
grep -n "useStalenessRetry" frontend/packages/ui/src/index.ts
grep -n "PillToggle" frontend/apps/web/src/features/dispatch-board/components/DispatchToolbar.tsx
```

---

## Context: What This Batch Does

| Area | Change |
|---|---|
| Store | Add `layoutMode` (`'lane'`/`'tech'`, default lane, no persist); consume orphaned `conflictPreviewOpen`/`conflictPreviewJobId` |
| Hooks | Rewrite `useMoveJob` → `/scheduling/jobs/{id}/move`; rewrite `useCheckConflicts` → `/scheduling/jobs/{id}/check-conflicts` + response adapter |
| New util | `mapConflictResponse` (adapt `{is_feasible,conflicts[]}` → `ConflictPreviewPane` shape); `timeHelpers.ts` (extract snap/px helpers) |
| New components | `DispatchGridDayView` (day-tech, @dnd-kit), `UnassignedTray`, `JobContextMenu`, `JobBlock` (extracted) |
| Modified | `DispatchToolbar` (Lane\|Tech toggle), `DispatchBoardLanes` (remove bottom queue + own DndContext, add context menu), `ConflictPreviewPane` (w-80 shell), `DispatchBoardPage` (lift DndContext, beginMove pipeline, right-rail arbitration) |
| Deleted | Raw-PATCH double-write in `DispatchBoardPage`; `UnscheduledJobQueue` in `DispatchBoardLanes` |

Follow the **UI design spec** for every pixel/class value. Follow the **architecture design doc** for every contract/pipeline behavior. Code examples below are **starting points** — read each file first and adjust prop names, import paths, and logic to match what you actually find.

---

## STEP 1 — Store: `layoutMode` + activate conflict-preview state

**File**: `store.ts`

Add to `DispatchBoardState` (read the file first — match the existing action style):
```ts
layoutMode: 'lane' | 'tech';                 // default 'lane', NOT persisted
setLayoutMode: (m: 'lane' | 'tech') => void;
```
Initial value `layoutMode: 'lane'`. No `persist` middleware (leave the store plain — resets on reload by design). The existing `conflictPreviewOpen`/`conflictPreviewJobId` + `openConflictPreview`/`closeConflictPreview` are already present — you will now actually consume them.

Intermediate check (store is imported widely):
```bash
pnpm --filter web test -- apps/web/src/features/dispatch-board 2>&1 | tail -10
```

---

## STEP 2 — Rewrite `useCheckConflicts` + add `mapConflictResponse`

**Files**: `useCheckConflicts.ts`, new `features/dispatch-board/utils/mapConflictResponse.ts`

Point the hook at `POST /api/v1/scheduling/jobs/{jobId}/check-conflicts` with body `{ tech_user_id, scheduled_start_at, scheduled_end_at }`. The response is `{ is_feasible, conflicts: dict[], drive_time_to_next_minutes?, drive_time_from_prev_minutes? }`.

`ConflictPreviewPane` expects `{ conflicts: {conflict_class, severity, ...}[], has_blocking_conflicts }`. Add `mapConflictResponse` to adapt:
- `has_blocking_conflicts` = `!is_feasible && conflicts.some(c => c.conflict_type === 'drive_time')` — **MVP is warn-only** (design doc §D.3 / §13.4); treat everything else as `warn`.
- Map each raw conflict's `conflict_type` → the `conflict_class`/`severity` the pane's `ConflictItem` renders. Confirm the exact `conflict_type` values the backend emits (`overlap`, `availability`, `drive_time`, …) by reading `scheduling_service.py` `check_slot_feasibility` — do not guess the strings.

Keep the pane's four-class visual contract unchanged; the adapter feeds it the shape it already consumes.

---

## STEP 3 — Rewrite `useMoveJob` to the `/move` contract

**File**: `useMoveJob.ts`

- Single endpoint: `POST /api/v1/scheduling/jobs/{jobId}/move`. Drop the `operation: 'reschedule'|'assign'` split — `/move` is one atomic reassign+reschedule.
- Body: `{ tech_user_id, scheduled_start_at, scheduled_end_at, expected_job_version, expected_assignment_version? }`.
- Keep `useStalenessRetry` + `mutationKey: ["moveJob"]` (the toolbar's in-flight indicator counts this key — do not rename it).
- `onConflict` (409): read `current_job_version` from the RFC7807 body and re-send it as `expected_job_version`; use `current_state.scheduled_start_at/end` for the refreshed display.
- Optimistic cache patch: key off the board query; on success re-key from `job_version` in the response.

> Read the current `useMoveJob` first — preserve the `useStalenessRetry` wiring and optimistic `onMutate`/`onError`/`onSettled` structure; only the endpoint, body, and 409-field names change.

Intermediate check (hooks are widely imported):
```bash
pnpm --filter web test -- apps/web/src/features/dispatch-board 2>&1 | tail -10
```

---

## STEP 4 — Extract shared helpers + `JobBlock`

**New files**: `features/dispatch-board/utils/timeHelpers.ts`, `features/dispatch-board/components/JobBlock.tsx`

- Move `snapTo15Min`, `dateToPx`, `pxToDate`, `computeViewportHours` out of `DispatchBoardLanes.tsx` into `timeHelpers.ts`; update `DispatchBoardLanes` to import them. **No behavior change.**
- Extract `DraggableJobBlock` into `JobBlock.tsx` (add an `onContextMenu` prop). Both `DispatchBoardLanes` and the new `DispatchGridDayView` import it. **No visual change** (UI spec §Surface 1).

---

## STEP 5 — `UnassignedTray` (new)

**File**: `features/dispatch-board/components/UnassignedTray.tsx` — build to UI spec §Surface 2 exactly (`data-testid="unassigned-tray"`, `min-h-[44px]`, always visible incl. `Unassigned (0)` + italic empty message, draggable chips via `@dnd-kit useDraggable`, left-click → `onJobClick`). Chips label with `title ?? job_number` + `customer_name`.

---

## STEP 6 — `JobContextMenu` (new) + wire into day-lane

**File**: `features/dispatch-board/components/JobContextMenu.tsx` — build to UI spec §Surface 5 (fixed at cursor, `z-50`, `w-44`, `View Job`/`Job Properties`, Heroicons `ArrowTopRightOnSquareIcon`/`AdjustmentsHorizontalIcon`, Escape/click-outside/scroll close, `role="menu"`). Rendered **once** in `DispatchBoardPage`; state `{x,y,job}|null` lives there. Add `onContextMenu` to `JobBlock` and thread it through `DispatchBoardLanes` + `DispatchGridDayView`.

---

## STEP 7 — `DispatchGridDayView` (new, @dnd-kit)

**File**: `features/dispatch-board/components/DispatchGridDayView.tsx` — build to UI spec §Surface 1. Time-across-horizontal × **one row per tenant tech (always rendered, even empty)**; `TECH_HEADER_WIDTH_PX = 128`; reuse `LANE_HEIGHT_PX=72`, `HOUR_WIDTH_PX=80`, time-axis `h-7`; sticky tech header col; `useDroppable` per tech row (`id: "tech-row-{techId}"`, `data:{techId}`); client-side over-capacity (overlap) detection blocks drop + flashes "Conflict" chip; mobile fallback below `md`. Props per spec's `DispatchGridDayViewProps`.

> The single `DndContext` lives in `DispatchBoardPage` (STEP 8) — this component does NOT wrap its own.

---

## STEP 8 — `DispatchToolbar`: Lane|Tech toggle

**File**: `DispatchToolbar.tsx` — add `layoutMode?`/`onLayoutModeToggle?` props; render the existing `PillToggle` with `Lane`/`Tech` options when `viewTab === "day"`, placed after the date-nav group (UI spec §Surface 3). Reuse `PillToggle` — no new component.

---

## STEP 9 — `ConflictPreviewPane` shell + icon

**File**: `ConflictPreviewPane.tsx` — add `w-80 flex-shrink-0 border-l border-neutral-200 bg-white shadow-lg` to the root `<div>` (line ~54) so it matches `JobPropertiesPanel`'s box; replace the hand-drawn close `<path>` with `XMarkIcon` from `@heroicons/react/24/outline`. Internal layout unchanged.

---

## STEP 10 — `DispatchBoardPage`: lift DndContext, beginMove pipeline, right-rail arbitration

**File**: `DispatchBoardPage.tsx`

1. **Lift `DndContext` to the page** — wrap `UnassignedTray` + the active grid (`DispatchBoardLanes` OR `DispatchGridDayView`) in ONE `DndContext`. Remove the `DndContext` from inside `DispatchBoardLanes`.
2. **`beginMove(jobId, techUserId, start, end)`** unified handler (design doc §F, UI spec Note 7):
   - `checkConflicts.mutate({ jobId, request:{tech_user_id, scheduled_start_at, scheduled_end_at} })`
   - `store.openConflictPreview(jobId)` → pane mounts
   - Proceed → `moveJob.mutate({ jobId, tech_user_id, scheduled_start_at, scheduled_end_at, expected_job_version, expected_assignment_version })` using `version`/`primary_assignment_id`/`assignment_version` from the board entry
   - Cancel → `store.closeConflictPreview()`
3. **DELETE the raw `apiClient.patch('/api/v1/jobs/{id}')` double-write** in both the day (`handleJobDrop`) and week (`handleWeekJobDrop`) handlers — route day through `beginMove`. (Week handler: leave a thin passthrough that still works via `moveJob`, but do NOT expand week scope — B1.5 owns week. Minimal change to keep week functional.)
4. **Right-rail arbitration** (UI spec §4): render exactly one — `conflictPreviewOpen ? <ConflictPreviewPane/> : selectedJob ? <JobPropertiesPanel/> : null`.
5. **Render `DispatchGridDayView` vs `DispatchBoardLanes`** on `layoutMode` when `viewTab === "day"`. Mount `UnassignedTray` between toolbar and board. Mount `JobContextMenu` at page level.
6. Pass `layoutMode`/`setLayoutMode` to `DispatchToolbar`.

Intermediate check (page is the integration point):
```bash
pnpm --filter web test -- apps/web/src/features/dispatch-board 2>&1 | tail -10
```

---

## STEP 11 — `DispatchBoardLanes` cleanup

**File**: `DispatchBoardLanes.tsx` — remove `<UnscheduledJobQueue>` + `UnscheduledJobCard` + the `unscheduledJobs` memo; remove its own `DndContext` (now lifted to page); import `JobBlock`/`timeHelpers` from the shared files; add `onContextMenu` passthrough. Keep lane assignment/positioning logic intact.

---

## MSW Handlers

Extend `dispatchBoardHandlers.ts` with the real endpoints, then register in `index.ts` (the barrel — mandatory):

```ts
http.post("/api/v1/scheduling/jobs/:id/check-conflicts", async () =>
  HttpResponse.json({ is_feasible: true, conflicts: [], drive_time_to_next_minutes: null, drive_time_from_prev_minutes: null }),
),
http.post("/api/v1/scheduling/jobs/:id/move", async ({ request, params }) => {
  const body = (await request.json()) as any;
  return HttpResponse.json({
    job_id: params.id, job_version: (body.expected_job_version ?? 1) + 1,
    assignment_id: "mock-assignment", assignment_version: 2,
    tech_user_id: body.tech_user_id,
    scheduled_start_at: body.scheduled_start_at, scheduled_end_at: body.scheduled_end_at,
    conflicts: [],
  });
}),
```
Check the existing file first — don't duplicate a path that already has a handler. Add a 409 override variant inside the staleness test using `server.use(...)`.

---

## Test Requirements

Per `react-engineer-rules.md` and the std test patterns. **Web = Vitest + `@testing-library/react`**; mock `next/navigation` + `next/link`; QueryClient with `retry: false`; MSW at HTTP level (never mock `apiClient`); `afterEach(server.resetHandlers())`.

**Unit tests** (co-located `__tests__/`):
- `useMoveJob` — fires `POST /scheduling/jobs/:id/move` with correct body incl. `expected_job_version`; 409 re-sends refreshed version.
- `useCheckConflicts` + `mapConflictResponse` — maps `{is_feasible,conflicts[]}` → pane shape; `has_blocking_conflicts` derivation.
- `UnassignedTray` — renders `data-testid="unassigned-tray"`; shows `Unassigned (0)` empty; chips render + are draggable.
- `JobContextMenu` — renders 2 items at cursor; Escape/click-outside close.
- `DispatchGridDayView` — renders one row per tech incl. empty; drop on free row fires `onJobDrop`; over-capacity blocks.

**Integration tests** (`apps/web/src/__tests__/batch_dispatch_b1/`):
- Lane↔Tech toggle swaps day render; survives a view-tab switch; resets to Lane after remount (no persist).
- Full pipeline happy path: drag → check-conflicts fires → `ConflictPreviewPane` appears in right rail (JobPropertiesPanel hidden) → Proceed → `/move` fires. And Cancel closes the pane.
- Right-rail arbitration: selecting a job shows properties; a pending move overrides it with the conflict pane.
- Day-lane right-click opens `JobContextMenu`.
- Tray drag-out onto a day-tech row fires `beginMove`.

Assert by IDs/content from MSW fixtures — never total counts.

---

## Final Verification

> ❌ **BANNED**: `npx vitest run` — never use it. Only `pnpm --filter web test`.

### Phase 1 — Targeted (during development)
```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/features/dispatch-board 2>&1 | tail -10
pnpm --filter web test -- apps/web/src/__tests__/batch_dispatch_b1/ 2>&1 | tail -10
```

### Phase 2 — Full verification (once, at the end)
```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

> Any failure in either phase must be fixed before done. No "pre-existing" exception without Tom's written confirmation.

---

## Definition of Done — DISPATCH-B1 (Part B)

- [ ] Regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — new `DispatchBoardJobEntry` fields present; stale `types-stub.ts` entries retired
- [ ] Design doc + UI spec fully read before coding
- [ ] All mandatory source files read
- [ ] All endpoint URLs verified in `openapi_schema_map.md` (`/scheduling/jobs/{id}/move` + `/check-conflicts`)
- [ ] **STEP 1**: `store.ts` — `layoutMode` (default lane, no persist) + conflict-preview state consumed
- [ ] **STEP 2**: `useCheckConflicts` rewritten + `mapConflictResponse` util
- [ ] **STEP 3**: `useMoveJob` rewritten to `/move`; 409 uses `current_job_version`
- [ ] **STEP 4**: `timeHelpers.ts` + `JobBlock.tsx` extracted (no visual change)
- [ ] **STEP 5**: `UnassignedTray` (`data-testid="unassigned-tray"`, always visible)
- [ ] **STEP 6**: `JobContextMenu` + wired into day-lane
- [ ] **STEP 7**: `DispatchGridDayView` (@dnd-kit, always-render tech rows)
- [ ] **STEP 8**: `DispatchToolbar` Lane|Tech toggle (day only)
- [ ] **STEP 9**: `ConflictPreviewPane` w-80 shell + `XMarkIcon`
- [ ] **STEP 10**: `DispatchBoardPage` — lifted `DndContext`, `beginMove` pipeline, right-rail arbitration, raw-PATCH double-write DELETED
- [ ] **STEP 11**: `DispatchBoardLanes` — bottom queue + own DndContext removed; shared imports
- [ ] All new MSW handlers registered in `mocks/handlers/index.ts`
- [ ] Unit + integration tests pass (targeted)
- [ ] Zero TypeScript errors; zero `no-hardcoded-design-values` lint warnings
- [ ] **Phase 2 FULL verification passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`)
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to launch plan Appendix B

---

## Completion Summary

After all DoD items are complete, add a Completion Summary to `pilot-launch-plan.md` Appendix B (React Engineer template). Note in it that **DISPATCH-B1.5 (Week board) is the fast-follow** — the unified pipeline, `UnassignedTray`, `JobBlock`, `timeHelpers`, `JobContextMenu`, and `layoutMode` are now in place for B1.5 to reuse when building `DispatchWeekLaneView` + transposing `DispatchWeekView`.
