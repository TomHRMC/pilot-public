# DISPATCH-B1 — Schedule Board (Day): Lane/Tech Toggle + Unassigned Tray + Unified Move Pipeline

**Batch**: DISPATCH-B1
**Type**: Mixed (Backend + Frontend web) — **Python Engineer runs first**
**Owner(s)**: Pilot Python Engineer (Part A) → Pilot React Engineer (Part B)
**Plan**: `pilot-launch-plan.md §2.3 DISPATCH-B1`
**Prerequisite**: dispatch board ✅, FE-B30 week view ✅, UI-FIX-2B multi-tech ✅
**Design spec (UI)**: `batch-ui-ds-b1-design-spec.md` §Surface 2 (patterns reused)
**Estimate**: Part A ~2–3h · Part B ~4–5h
**Status**: Design complete — awaiting UI Designer spec (Part B surfaces) + implementation

---

## Scope Boundary (READ FIRST)

DISPATCH-B1 delivers a **fully coherent DAY board in both layout modes**, plus the **shared move pipeline** the whole board depends on. The **WEEK board is explicitly deferred to DISPATCH-B1.5** (see §Split below).

**In scope (B1)**:
- **Part A (Backend)** — enrich `DispatchBoardJobEntry` so the frontend can drive the real optimistic-locking `/move` contract and render real job labels (retiring the fragile second-fetch hack).
- **Part B (Frontend)** —
  1. Rewrite `useMoveJob` + `useCheckConflicts` to the **real** `/api/v1/scheduling/...` contracts.
  2. Wire the **`check-conflicts → ConflictPreviewPane → confirm → move`** pre-commit pipeline into the unified drop handler.
  3. **Lane | Tech** `PillToggle` (default **Lane**) controlling the day board's vertical axis.
  4. New **`DispatchGridDayView`** (day-tech mode) built on **`@dnd-kit`**.
  5. Shared **`UnassignedTray`** horizontal strip above the board (replaces the day view's bottom queue).
  6. Right-click **context menu** on day-lane job cards (parity with week-tech).

**Deferred to DISPATCH-B1.5 (Week board)**:
- `DispatchWeekLaneView` (net-new week-lane grid: **days-as-rows × lane-columns**).
- The existing `DispatchWeekView` (week-tech: days-as-rows × tech-columns) stays **as-is** — no transpose. The Lane/Tech toggle swaps the **column** set (techs ↔ lanes); the 5-day/7-day toggle is retained.
- Both week modes reuse B1's move pipeline, `UnassignedTray`, and `layoutMode` store field unchanged.

> **Rationale (Rule 9.6)**: Splitting keeps B1 shippable and demoable (a complete Day board) while B1.5 adds the week-lane column variant on top of B1's now-proven pipeline. Week-tech already works (FE-B30) and is not rebuilt.
>
> **Geometry correction (2026-07-26)**: An earlier draft of this doc specified "days-as-columns × lane/tech-rows" with a week-tech transpose. That was wrong — Tom's locked model keeps **days as rows** and swaps **columns** (tech ↔ lane) via the pill toggle, matching the existing `DispatchWeekView`. Week-tech is therefore untouched; week-lane is the only net-new week grid.

---

## A. Input Read Summary

| Input | Section(s) read | Why it mattered |
|---|---|---|
| `pilot-launch-plan.md` | §2.3 DISPATCH-B1 card, §2.1 execution order | The four gaps + component matrix (day-lane/day-tech/week-lane/week-tech) |
| `batch-ui-ds-b1-design-spec.md` | §Surface 2 (Week), context-menu spec | Reusable JobBlock/DragOverlay/context-menu class guidance |
| `DispatchBoardPage.tsx` | full | Orchestration; found **day drop double-write** (raw PATCH + moveJob) |
| `DispatchBoardLanes.tsx` | full | Day-lane view (`@dnd-kit`); bottom `UnscheduledJobQueue`; no context menu |
| `DispatchWeekView.tsx` | full | Week-tech view; right-click menu pattern to reuse |
| `DispatchGrid.tsx` | full | Deprecated `react-dnd` day-tech grid — **NOT reused** (rebuild on @dnd-kit) |
| `DispatchToolbar.tsx` | full | `PillToggle` pattern to reuse for Lane\|Tech |
| `store.ts` | full | No persist middleware (matches "reset on reload"); has orphaned conflict-preview state |
| `useMoveJob.ts` | full | Targets **non-existent** `/schedule/.../reschedule`+`/assign`; wrong body shape |
| `useCheckConflicts.ts` | full | Targets **non-existent** `/schedule/.../check-conflicts`; orphaned (no callers) |
| `ConflictPreviewPane.tsx` | full | Built but **never rendered**; expects `conflict_class`/`severity`/`has_blocking_conflicts` |
| `useDispatchBoard.ts` | full | Second `/jobs/?scheduled_date=` fetch hack for titles; normalizes raw→component shape |
| `scheduling.py` | `/move`, `/check-conflicts`, `_dispatch_board_impl` | **Real** contracts: `/scheduling/jobs/{id}/move`, integer `expected_job_version` |
| `schemas.py` | `DispatchBoardJobEntry/TechGroup/Response` | Board entry omits `version`/assignment/title — the root FE gap |
| `scheduling_service.py` | `check_slot_feasibility` return | Returns `{is_feasible, conflicts[]}`; conflict dicts use `conflict_type` |
| Live DB (MCP) | `job`, `job_tech_assignment` columns | `job.version` + `job_tech_assignment.version` **exist** → **no migration**; `job.title` absent → use `job_number` |

---

## B. Migration Plan

**No migration required.** MCP verification (2026-07-26) confirms all fields Part A surfaces already exist on the live schema:

```
job.version                   integer NOT NULL   ✅ (optimistic lock — already maintained by /move)
job.job_number                varchar NOT NULL   ✅ (label fallback until JOB-UI-B1 adds job.title)
job_tech_assignment.version   integer NOT NULL   ✅
job_tech_assignment.role      text NOT NULL      ✅ ('primary' filter)
job_tech_assignment.is_active boolean NOT NULL   ✅
```

Part A is a **pure response-schema (Pydantic) change** — it exposes existing columns/joins that `_dispatch_board_impl` already loads. There is **no** `lane_number` column (confirmed absent) — lanes remain **client-computed** via the existing `assignJobsToLanes` earliest-free-slot algorithm.

**MCP verification queries (Python Engineer must re-run before coding Part A)**:
```sql
-- 1. Confirm job.version + job_number still present (label + optimistic lock source)
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema='public' AND table_name='job'
  AND column_name IN ('version','job_number','title') ORDER BY column_name;
-- Expect: version(integer,NO), job_number(varchar,NO). title = 0 rows until JOB-UI-B1.

-- 2. Confirm assignment version + role filter columns
SELECT column_name, data_type, is_nullable FROM information_schema.columns
WHERE table_schema='public' AND table_name='job_tech_assignment'
  AND column_name IN ('version','role','is_active','user_id') ORDER BY column_name;
```

---

## C. Execution Order

| # | Step | Owner | Notes |
|---|---|---|---|
| 1 | MCP verify `job`/`job_tech_assignment` columns (§B) | Python | Rule 3 gate before any schema edit |
| 2 | Extend `DispatchBoardJobEntry` (+`version`, `primary_assignment_id`, `assignment_version`, `job_number`, `customer_name`, `site_address`) | Python | §D.1 |
| 3 | Populate new fields in `_dispatch_board_impl` (batch-join customer/site names; assignment map already built) | Python | Avoid N+1 — one batched query per relation |
| 4 | Backend unit tests (board entry now carries version + labels; unassigned entries too) | Python | §Tests |
| 5 | `python export_openapi_json.py` → commit → **handoff** to React Engineer | Python | Rule 9.3 |
| 6 | `pnpm sync-api-types` (FE first step) | React | Rule 8/9.3 |
| 7 | Rewrite `useMoveJob` → `POST /scheduling/jobs/{id}/move`; map 409 body → staleness retry | React | §D.2 |
| 8 | Rewrite `useCheckConflicts` → `POST /scheduling/jobs/{id}/check-conflicts`; adapt response | React | §D.3 |
| 9 | Add `layoutMode` to store (`'lane'\|'tech'`, default `'lane'`, no persist) | React | §E.5 |
| 10 | Build `UnassignedTray` (shared) + mount above board; remove day bottom queue | React | §I |
| 11 | Rebuild `DispatchGridDayView` on `@dnd-kit` (day-tech mode) | React | §I |
| 12 | Add right-click context menu to day-lane cards (extract shared `JobContextMenu`) | React | §I |
| 13 | Wire unified drop handler: check-conflicts → ConflictPreviewPane → confirm → move; delete raw-PATCH double-write | React | §E.1 |
| 14 | Add Lane\|Tech `PillToggle` to `DispatchToolbar` (day only) | React | §I |
| 15 | FE tests (pipeline, toggle, tray, day-tech DnD, context menu) + MSW handlers | React | §Tests |
| 16 | Two-phase verification gate + openapi contract check | React | — |

---

## D. New / Changed API Contracts

### D.1 — Part A: `DispatchBoardJobEntry` (CHANGED — additive, backward-compatible)

File: `backend/api/schemas/schemas.py`

```python
class DispatchBoardJobEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    customer_id: UUID
    site_id: UUID
    status_id: UUID
    scheduled_start_at: datetime | None
    scheduled_end_at: datetime | None
    estimated_duration_minutes: int | None
    external_calendar_event_id: str | None
    is_active: bool
    eta_minutes: int | None = None
    # ── DISPATCH-B1 additions ──────────────────────────────────────────────
    version: int                              # optimistic lock → FE sends as expected_job_version
    primary_assignment_id: UUID | None = None # active primary JobTechAssignment.id (null = unassigned)
    assignment_version: int | None = None     # → FE sends as expected_assignment_version
    job_number: str                           # label (until JOB-UI-B1 adds title)
    customer_name: str | None = None          # enrichment — retires FE second-fetch
    site_address: str | None = None           # enrichment
    title: str | None = None                  # FORWARD-COMPAT: null now; populated once JOB-UI-B1 lands
```

**Populate in `_dispatch_board_impl`** (`scheduling.py`):
- `version`, `job_number` — already on the `Job` rows loaded.
- `primary_assignment_id` / `assignment_version` — from the **existing** `assignments` query; extend `job_to_tech` map to also carry `(assignment.id, assignment.version)`.
- `customer_name` — batch-load `Customer.display_name` for the job set (one `WHERE id IN (...)` query).
- `site_address` — batch-load `Address` for the sites (one query). Reuse the `Address` import already present.
- `title` — set to `None` for now (forward-compatible; no `job.title` column yet).

> **Anti-N+1**: add exactly two batched lookups (customers, sites) keyed by the already-fetched `job_ids`. Do not query per-job.

### D.2 — Part B: `useMoveJob` rewrite → real `/move` contract

| | Old (wrong) | New (real) |
|---|---|---|
| Endpoint | `POST /api/v1/schedule/jobs/{id}/reschedule` + `/assign` | `POST /api/v1/scheduling/jobs/{id}/move` |
| Request | `{tech_id, scheduled_start_at, scheduled_end_at, expected_updated_at}` | `{tech_user_id, scheduled_start_at, scheduled_end_at, expected_job_version, expected_assignment_version?}` |
| Response | `{id, tech_id, scheduled_start_at, scheduled_end_at, updated_at}` | `{job_id, job_version, assignment_id, assignment_version, tech_user_id, scheduled_start_at, scheduled_end_at, conflicts[]}` |
| 409 shape | `refreshedState.updated_at` | RFC7807 dict: `current_job_version` + `current_state.{scheduled_start_at,scheduled_end_at}` |

- `move` is a **single atomic reassign+reschedule** — drop the `operation: 'reschedule'\|'assign'` split entirely.
- Staleness retry (`useStalenessRetry`) `onConflict` now reads `current_job_version` and re-sends it as `expected_job_version`.
- Optimistic cache update keyed on `job_id`/`job_version` from the response.

### D.3 — Part B: `useCheckConflicts` rewrite → real `/check-conflicts` contract

| | Old (wrong) | New (real) |
|---|---|---|
| Endpoint | `POST /api/v1/schedule/jobs/{id}/check-conflicts` | `POST /api/v1/scheduling/jobs/{id}/check-conflicts` |
| Request | `{tech_id, scheduled_start_at, scheduled_end_at}` | `{tech_user_id, scheduled_start_at, scheduled_end_at}` |
| Response | `{conflicts[], has_blocking_conflicts}` (`conflict_class`,`severity`) | `{is_feasible, conflicts: dict[], drive_time_to_next_minutes?, drive_time_from_prev_minutes?}` |

**Adapter required** — `ConflictPreviewPane` expects `conflict_class` + `severity` + `has_blocking_conflicts`, but the backend returns `is_feasible` + raw `conflicts[]` whose dicts use `conflict_type`. Add a small mapping layer in the hook (or a `mapConflictResponse` util) that:
- derives `has_blocking_conflicts = !is_feasible && conflicts.some(c => c.conflict_type === 'drive_time')` — **MVP is warn-only** (spec §13.4); treat all as `warn` except explicit blocks. Confirm the `conflict_type → conflict_class/severity` mapping table with the exact values `check_slot_feasibility` emits (`overlap`, `availability`, `drive_time`, …).
- Keep `ConflictPreviewPane`'s existing four-class visual contract unchanged; the adapter feeds it the shape it already expects.

> **Endpoint auth note**: both real endpoints require `schedule.manage`. The board GET requires `schedule.view_all`. No RBAC change — the dispatch board is already `RoleGate role={["owner","operator"]}`.

---

## E. Pattern Reuse Decisions (`mvp-arch.md` §16)

| Pattern | Applies | How |
|---|---|---|
| §16.4 pre-commit staleness (409-and-refresh) | ✅ | `/move` integer `expected_job_version`; `useStalenessRetry` re-sends refreshed version |
| Always-preview-before-commit | ✅ | check-conflicts → `ConflictPreviewPane` → confirm gates every DnD move |
| Optimistic UI | ✅ | `useMoveJob.onMutate` cache patch; rollback on error (kept, re-keyed to `job_version`) |
| §16 system-default/tenant-override | ✅ | Lane count from `useScheduleLaneCount` (subscription tier) — unchanged |
| Four-class severity | ✅ | `ConflictPreviewPane` reused as-is via the D.3 adapter |
| `apiClient` mandatory | ✅ | All calls via `@pilot/shared-api`; **delete the raw `apiClient.patch('/api/v1/jobs/{id}')` double-write** |
| Idempotency-Key | ⚠️ | `/move` is not currently idempotency-keyed server-side; out of scope for B1 (no offline mobile path for dispatch moves). Flag only. |

**Store note (§E.5)**: add `layoutMode: 'lane' | 'tech'` (default `'lane'`) + `setLayoutMode`. **No persist middleware** — survives Day/Week/Month view-tab switches (in-memory), resets to `'lane'` on full reload. The orphaned `conflictPreviewOpen`/`conflictPreviewJobId` fields become **live** in B1 (finally consumed by the pipeline).

---

## F. Shared Module Interfaces

```ts
// store.ts additions
layoutMode: 'lane' | 'tech';               // default 'lane', NOT persisted
setLayoutMode: (m: 'lane' | 'tech') => void;

// UnassignedTray.tsx (NEW — shared day+week)
interface UnassignedTrayProps {
  jobs: DispatchBoardJob[];                 // board.jobs where tech_id === null
  onJobClick: (job: DispatchBoardJob) => void;
  // drag-out handled by shared DndContext; cards are @dnd-kit useDraggable
}
// data-testid="unassigned-tray"

// JobContextMenu.tsx (NEW — extracted from DispatchWeekView's inline menu)
interface JobContextMenuProps {
  state: { x: number; y: number; job: DispatchBoardJob } | null;
  onClose: () => void;
  onViewJob: (job: DispatchBoardJob) => void;      // → /jobs/{id}
  onJobProperties: (job: DispatchBoardJob) => void; // → JobPropertiesPanel
}

// DispatchGridDayView.tsx (NEW — day-tech, @dnd-kit)
interface DispatchGridDayViewProps {
  date: Date;
  techs: DispatchBoardTech[];              // ALWAYS render a row per tenant tech (even empty)
  jobs: ScheduledJob[];
  onJobClick: (job: ScheduledJob) => void; // left-click → panel
  onJobDrop: (jobId: string, techId: string, startTime: Date) => void; // → unified pipeline
  onJobContextMenu: (e: React.MouseEvent, job: ScheduledJob) => void;   // right-click → menu
}

// Unified drop handler (DispatchBoardPage) — replaces handleJobDrop + handleWeekJobDrop double-write
async function beginMove(jobId, techUserId, start, end):
  1. setPendingMove({jobId, techUserId, start, end})
  2. checkConflicts.mutate({ jobId, request:{tech_user_id, scheduled_start_at, scheduled_end_at} })
  3. open ConflictPreviewPane (store.openConflictPreview(jobId))
  4. onProceed → moveJob.mutate({ jobId, tech_user_id, scheduled_start_at, scheduled_end_at,
                                  expected_job_version, expected_assignment_version })
  5. onCancel → closeConflictPreview(); rollback optimistic (none applied until proceed)
```

No new Celery tasks. No SSE change (existing `useDispatchSse` events already cover move outcomes).

---

## G. Open Questions Resolved

1. **Pipeline breadth** → Unify **all** DnD views through `move` + check-conflicts + `ConflictPreviewPane`; delete the raw-PATCH double-write. (B1 implements it for the Day board; B1.5 reuses it for Week.)
2. **Day-tech DnD library** → **Rebuild on `@dnd-kit`**; do not extract the `react-dnd` `DispatchGrid.tsx`. Board becomes single-library; deprecated grid + `MultiDayGrid` may be soft-deleted once tests migrate.
3. **Week geometry** (B1.5) → **days-as-rows × columns that toggle between techs and lanes** (matching the existing `DispatchWeekView`). Week-tech stays as-is (no transpose); week-lane is the only net-new week grid. 5-day/7-day toggle retained. **Implemented in B1.5.** *(Corrected 2026-07-26 from an earlier "days-as-columns × rows / transpose" draft.)*
4. **Click behavior** → Left-click opens `JobPropertiesPanel` everywhere; context menu is **right-click only** everywhere (added to day-lane, which has none today).
5. **Unassigned** → Single **top** `UnassignedTray` shared by day+week; **replaces** the day view's bottom `UnscheduledJobQueue`. Drag-out-to-schedule works in day (B1) and week (B1.5).
6. **Toggle persistence** → `layoutMode`, default `'lane'`, no persist. "Tabs" = Day/Week/Month view tabs.
7. **Backend gap** → DISPATCH-B1 reclassified **mixed BE+FE (Python first)**; Part A adds the version/assignment/enrichment fields the FE needs — **no migration** (fields exist).
8. **`job.title`** → Not yet in schema; B1 labels with `job_number` and exposes a forward-compatible `title: null` field. JOB-UI-B1 populates it later with zero FE change.

---

## H. Surface Mockup Reference (Frontend)

**Platform scope**: web only (`apps/web`). Mobile dispatch is out of scope.

**UI Designer must produce spec surfaces for** (B1 only):
- **Day-Tech grid** (`DispatchGridDayView`) — time-across-horizontal × **one row per tenant tech (always rendered, even empty)** + an Unassigned handling via the top tray. Reuse day-lane's time-axis metrics (`HOUR_WIDTH_PX=80`, `LANE_HEIGHT_PX=72`) and JobBlock visual.
- **UnassignedTray** — horizontal strip above the board; `data-testid="unassigned-tray"`; draggable chips; collapses gracefully when empty (still visible with count `Unassigned (0)`).
- **Lane | Tech PillToggle** — in `DispatchToolbar`, rendered when `viewTab === "day"` (B1); reuse existing `PillToggle` styling (`DispatchToolbar.tsx`).
- **ConflictPreviewPane docking** — right-side inline panel (not modal) so the grid stays visible; component already styled — spec only its **mount position** relative to `JobPropertiesPanel` (they must not both occupy the right rail simultaneously).

**§16 patterns consumed**: always-preview-before-commit, 409-and-refresh, optimistic UI, four-class severity, system-default/tenant-override (lane count).

---

## I. Component Manifest (Frontend)

| Component / File | Action | Destination |
|---|---|---|
| `store.ts` | Modify — add `layoutMode`+`setLayoutMode`; consume existing conflict-preview state | `features/dispatch-board/store.ts` |
| `useMoveJob.ts` | Rewrite — real `/scheduling/jobs/{id}/move`; integer version 409 | `features/dispatch-board/hooks/` |
| `useCheckConflicts.ts` | Rewrite — real `/scheduling/jobs/{id}/check-conflicts` + response adapter | `features/dispatch-board/hooks/` |
| `mapConflictResponse.ts` | New — adapt `{is_feasible,conflicts[]}` → `ConflictPreviewPane` shape | `features/dispatch-board/utils/` |
| `UnassignedTray.tsx` | New — shared top strip (`data-testid="unassigned-tray"`) | `features/dispatch-board/components/` |
| `JobContextMenu.tsx` | New — extracted shared right-click menu | `features/dispatch-board/components/` |
| `DispatchGridDayView.tsx` | New — day-tech mode, `@dnd-kit` | `features/dispatch-board/components/` |
| `DispatchToolbar.tsx` | Modify — add Lane\|Tech `PillToggle` (day) | `features/dispatch-board/components/` |
| `DispatchBoardLanes.tsx` | Modify — remove bottom `UnscheduledJobQueue`; add `onContextMenu` to cards | `features/dispatch-board/components/` |
| `DispatchBoardPage.tsx` | Modify — unified `beginMove` pipeline; render `UnassignedTray` + `ConflictPreviewPane`; route day-lane vs day-tech on `layoutMode`; delete raw-PATCH | `features/dispatch-board/components/` |
| `DispatchGrid.tsx` / `MultiDayGrid.tsx` | Soft-delete candidates (after test migration) | deprecated `react-dnd` |
| `types-stub.ts` | Modify/retire — align to synced `api-schema.d.ts` after Part A (`version`, assignment ids, labels) | `features/dispatch-board/` |

**Tests (targeted, then full suite)**:
- Backend: `DispatchBoardJobEntry` now returns `version`/`primary_assignment_id`/`assignment_version`/`job_number`/`customer_name`/`site_address` for assigned + unassigned entries; no N+1 (query count assertion optional).
- FE: unified pipeline (check→preview→proceed→move happy path + cancel); 409 staleness re-send; Lane↔Tech toggle swaps day render + persists across view-tab switch + resets on remount; `UnassignedTray` renders `data-testid` + drag-out; day-lane right-click opens `JobContextMenu`; day-tech `@dnd-kit` drop fires `beginMove`.
- MSW: register real `/api/v1/scheduling/jobs/:id/move` + `/check-conflicts` handlers (+ `index.ts` barrel).

---

## Split — DISPATCH-B1.5 (Week board, fast-follow)

| | DISPATCH-B1 (this doc) | DISPATCH-B1.5 |
|---|---|---|
| Views | Day-lane + Day-tech | Week-lane (**new**) + Week-tech (**unchanged, no transpose**) |
| Pipeline | Builds unified move/conflict pipeline | Reuses B1 pipeline unchanged |
| Tray / Toggle | Builds `UnassignedTray` + `layoutMode` | Reuses both; Lane/Tech toggle now also drives week (swaps columns) |
| Geometry | — | **days-as-rows**; columns toggle **techs(N) ↔ lanes(5)**; 5/7-day toggle retained; always render full empty column set |
| Commitments (B1.25) | — | Week-tech renders B1.25 read-only commitment chips |
| Backend | Part A schema enrichment (covers week too) | None (B1 + B1.25 `DispatchBoardJobEntry` already sufficient) |

B1.5 is **frontend-only** and depends on B1's merged pipeline + tray + store field, plus B1.25's commitment chips. Only `DispatchWeekLaneView` is net-new; `DispatchWeekView` (week-tech) is reused as-is.

---

*Design authored by Pilot Architect, 2026-07-26. Part A (Python) must run first and hand off via `python export_openapi_json.py` + `pnpm sync-api-types` per Rule 9.3.*
