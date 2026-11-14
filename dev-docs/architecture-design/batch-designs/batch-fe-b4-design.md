# FE-B4 Batch Design — Dispatch Board + Profitability Drill-Down (Pass 3 Flows 2 & 3)

**Version**: 1.0  
**Date**: 2026-05-22  
**Batch**: FE-B4  
**Prerequisite Batches**: FE-B1 ✅, FE-B2 ✅, FE-B3 ✅  
**Backend Gate**: BE-B3 (dispatch + ETC) — develop against MSW until it lands  
**Gates Downstream**: FE-B5 (staleness retry pattern), FE-B8 (SSE channel pattern), FE-B9 (staleness + SSE reuse), FE-B10 (staleness), FE-B15 (in-flight indicator extends)  
**Estimated Effort**: 16–22 days  
**Test Subfolder**: `apps/web/__tests__/batch_fe_b4/`  
**Platform**: Web-only (Next.js 16 + shadcn/ui)  
**Status**: Design phase — no implementation code written yet  

---

## Pre-Design Verification Summary

All prerequisites confirmed via codebase inspection:

| Check | Result |
|:---|:---|
| `useStalenessRetry` exists | ❌ Not yet — only a comment placeholder in `packages/ui/src/hooks/index.ts` |
| `StalenessRefreshDialog` exists | ❌ Not yet |
| `useSseChannel` exists | ❌ Not yet |
| `<InFlightSyncIndicator>` skeleton | ✅ Exists at `packages/ui/src/sync-indicator/` and exported from `packages/ui/src/index.ts` |
| `/schedule` route exists | ✅ `apps/web/src/app/(authed)/schedule/` placeholder present |
| `VoiceConfirmTurn`, `useVoiceStream` (FE-B3) | ✅ Exported from `packages/ui/src/index.ts` |
| Schedule API endpoints in openapi.json | ❌ BE-B3 not yet landed — all `/api/v1/schedule/*` require MSW stubs |
| `/api/v1/jobs/{job_id}/projected-margin` | ✅ Present in openapi.json (line 5987) |
| `/api/v1/reports/profitability` | ✅ Present in openapi.json (line 15178) |

---

## A. Component Implementation Plan

### A.1 Shared Modules — New (established in FE-B4, consumed by FE-B5/B8/B9/B10)

These are **cross-batch shared modules**. Their TypeScript interfaces are locked in this design and must not be changed without a downstream impact review. See **Section F** for full interface definitions.

#### A.1.1 `useStalenessRetry()` — Pre-Commit 409 Retry Hook

| Property | Value |
|:---|:---|
| **File path** | `packages/ui/src/hooks/useStalenessRetry.ts` |
| **Exported from** | `packages/ui/src/index.ts` + `packages/ui/src/hooks/index.ts` |
| **Established in** | FE-B4 (dispatch board move mutation) |
| **Consumed by** | FE-B5 (quote approval), FE-B8 (calendar conflict resolve), FE-B9 (QB conflict), FE-B10 (SMS reply) |
| **Pattern ref** | `mvp-arch.md` §16.4; `pilot-react-engineer-methods.md` §9.3 |

The hook wraps any mutation function that can receive a `409 Conflict` response from the backend's pre-commit staleness check (`expected_updated_at` mismatch). On 409, it fetches refreshed state, surfaces `<StalenessRefreshDialog>`, and allows retry with new version data.

#### A.1.2 `<StalenessRefreshDialog>` — 409 Dialog Component

| Property | Value |
|:---|:---|
| **File path** | `packages/ui/src/staleness-refresh-dialog/StalenessRefreshDialog.tsx` |
| **Types file** | `packages/ui/src/staleness-refresh-dialog/types.ts` |
| **Exported from** | `packages/ui/src/index.ts` |
| **Established in** | FE-B4 |
| **Consumed by** | FE-B5, FE-B8, FE-B9, FE-B10 (all via `useStalenessRetry()` — consumers never render this directly) |

Renders "this record was updated while you were working" UI. For FE-B4 it shows refreshed job slot state (not a diff — `<DiffView>` is not yet built, that's FE-B5). Designed so FE-B5+ can extend via the `renderConflictContent` prop.

#### A.1.3 `useSseChannel()` — Server-Sent Events Hook

| Property | Value |
|:---|:---|
| **File path** | `packages/ui/src/hooks/useSseChannel.ts` |
| **Exported from** | `packages/ui/src/hooks/index.ts` and `packages/ui/src/index.ts` |
| **Established in** | FE-B4 (dispatch board stream) |
| **Consumed by** | FE-B8 (calendar conflicts SSE), FE-B10 (SMS thread SSE), FE-B12 (in-app notifications SSE) |
| **Pattern ref** | `mvp-arch.md` §13.11; `pilot-react-engineer-methods.md` §10.4 |
| **Platform** | Web-only (native `EventSource`). Mobile uses `react-native-sse` polyfill — if a mobile consumer arises, add a platform-detected branch to this hook following the `packages/ui/src/voice/mobile/` pattern |

**Platform decision**: The hook lives in `packages/ui/src/hooks/` (shared location) but the MVP implementation uses `EventSource` which is web-native. A comment in the hook file documents the mobile extension path (`react-native-sse`) so FE-B10 mobile SMS (if needed) has a clear upgrade path. This avoids forking the pattern.

---

### A.2 Surface-Scoped Components — New (live in `apps/web/src/features/dispatch-board/`)

#### A.2.1 Dispatch Board Shell Components

| Component | File Path | Purpose |
|:---|:---|:---|
| `DispatchBoardPage` | `features/dispatch-board/components/DispatchBoardPage.tsx` | Top-level page composition: toolbar + filter sidebar + grid |
| `DispatchToolbar` | `features/dispatch-board/components/DispatchToolbar.tsx` | Day/4-Day/Week/Month tab switcher, date navigation (prev/next/today), Voice button, calendar sync status indicator |
| `DispatchGrid` | `features/dispatch-board/components/DispatchGrid.tsx` | The calendar grid; renders tech columns × time rows; wraps `react-dnd` `DndProvider` with HTML5 backend |
| `DispatchGridColumn` | `features/dispatch-board/components/DispatchGridColumn.tsx` | Single tech column; renders job blocks as draggable items; drop target for inbound moves |
| `TechColumnHeader` | `features/dispatch-board/components/TechColumnHeader.tsx` | Tech avatar + name + color dot at top of column |
| `AvailabilityZone` | `features/dispatch-board/components/AvailabilityZone.tsx` | Visual rendering of working hours (white), outside-hours (gray), PTO (striped) within a column |
| `NowLine` | `features/dispatch-board/components/NowLine.tsx` | Red horizontal line spanning all columns at current time; updates every 60s via `setInterval` |
| `UnassignedColumn` | `features/dispatch-board/components/UnassignedColumn.tsx` | Virtual "Unassigned" column on the right edge; shows jobs from accepted quotes with no tech yet |
| `FilterSidebar` | `features/dispatch-board/components/FilterSidebar.tsx` | Left sidebar with 5 filter groups (Tech, Status, Customer, Job Type, Priority); each checkbox with count |
| `DispatchInfoBar` | `features/dispatch-board/components/DispatchInfoBar.tsx` | Bottom bar showing techs-working-today, jobs-scheduled, warnings-count, conflicts-blocked-count, last-updated timestamp |

#### A.2.2 Job Block Components

| Component | File Path | Purpose |
|:---|:---|:---|
| `JobBlock` | `features/dispatch-board/components/JobBlock.tsx` | Draggable job card placed on the grid; renders four-tier content hierarchy; left border with tech color; click to open job detail panel |
| `JobBlockTags` | `features/dispatch-board/components/JobBlockTags.tsx` | Rush/Warranty/Drive-time-warning tags rendered top-right of job block |
| `DragPreviewBlock` | `features/dispatch-board/components/DragPreviewBlock.tsx` | Ghost block following cursor during drag; shows conflict indicators in real-time via `useDragConflictPreview` |
| `DriveTimeMarker` | `features/dispatch-board/components/DriveTimeMarker.tsx` | Horizontal dotted line between consecutive jobs showing drive time in minutes; turns red with label when infeasible |
| `MonthViewCell` | `features/dispatch-board/components/MonthViewCell.tsx` | Single day cell in Month view; shows job count + capacity bar (green→amber→red) |

#### A.2.3 Conflict Preview Components

| Component | File Path | Purpose |
|:---|:---|:---|
| `ConflictPreviewPane` | `features/dispatch-board/components/ConflictPreviewPane.tsx` | Side panel shown before confirming a move; renders conflict list from `check-conflicts` endpoint |
| `ConflictItem` | `features/dispatch-board/components/ConflictItem.tsx` | Single conflict row with severity-class visual treatment (see §G.6) |
| `ConflictSeverityBadge` | `features/dispatch-board/components/ConflictSeverityBadge.tsx` | Color-coded badge encoding `overlap`, `availability`, `travel`, `info` class per §13.4 |

#### A.2.4 Job Detail Panel Components

| Component | File Path | Purpose |
|:---|:---|:---|
| `JobDetailPanel` | `features/dispatch-board/components/JobDetailPanel.tsx` | Slide-in side panel on job block click; composes `JobProfitabilityCard` + `ETCDrillDown` + time entries list |
| `JobDetailHeader` | `features/dispatch-board/components/JobDetailHeader.tsx` | Job title, customer, site, status pill, scheduled times |
| `TimeEntryList` | `features/dispatch-board/components/TimeEntryList.tsx` | List of time entries per job with tech name, clock-in/out, hours logged |

#### A.2.5 Profitability Widget Components

| Component | File Path | Purpose |
|:---|:---|:---|
| `JobProfitabilityCard` | `features/dispatch-board/components/JobProfitabilityCard.tsx` | Renders current revenue, cost-to-date, ETC-derived projected margin, margin bucket color chip; composes within JobDetailPanel |
| `MarginBucketChip` | `features/dispatch-board/components/MarginBucketChip.tsx` | Color chip encoding the margin bucket (red/amber/green/deep-green); reads `margin_bucket` from API; visual token from Pass 1 |
| `ProgressWithOverrun` | `features/dispatch-board/components/ProgressWithOverrun.tsx` | Progress bar using `hours_worked / (hours_worked + hours_remaining)` formula; shows red fill + warning glyph when projected total > quoted hours |
| `ETCDrillDown` | `features/dispatch-board/components/ETCDrillDown.tsx` | Quote line × hours captured / hours remaining table; tech-by-tech breakdown; click to filter time entries |
| `ETCLineRow` | `features/dispatch-board/components/ETCLineRow.tsx` | Single row in ETC drill-down; shows labor line name, quoted hours, actual hours, remaining ETC |

#### A.2.6 Reports Surface Components (Profitability Page)

| Component | File Path | Purpose |
|:---|:---|:---|
| `ProfitabilityPage` | `features/profitability/components/ProfitabilityPage.tsx` | Top-level `/reports` sub-surface; composes live + closed sections |
| `PeriodSelector` | `features/profitability/components/PeriodSelector.tsx` | 7d / 30d / MTD / YTD / Custom pill selector; establishes the canonical reports period selector pattern |
| `LiveJobsSection` | `features/profitability/components/LiveJobsSection.tsx` | Live jobs table (open jobs with activity); hot indicator on below-target rows |
| `LiveJobRow` | `features/profitability/components/LiveJobRow.tsx` | Single live job row: name, customer, hours progress bar, projected margin, red-dot hot indicator |
| `ClosedJobsSection` | `features/profitability/components/ClosedJobsSection.tsx` | Closed-in-period section; chart-or-table threshold logic; two bar charts side by side |
| `MetricsCardRow` | `features/profitability/components/MetricsCardRow.tsx` | Three large-number metric cards: Revenue, Profit, Avg Margin each with period-over-period delta |
| `MarginBarChart` | `features/profitability/components/MarginBarChart.tsx` | Single bar chart for jobs-by-margin or revenue-by-margin; clickable bars triggering drill-down panel |
| `DrillDownPanel` | `features/profitability/components/DrillDownPanel.tsx` | Inline drill-down panel below charts; shows jobs in selected bucket with close date, revenue, margin |
| `ChartThresholdNotice` | `features/profitability/components/ChartThresholdNotice.tsx` | "Charts appear when 8+ jobs are in scope. Adjust threshold in Settings → Reports." inline notice |
| `PinToDashboardButton` | `features/profitability/components/PinToDashboardButton.tsx` | Toggle "Pin to dashboard" button in page header |

#### A.2.7 Surface-Scoped Hooks

| Hook | File Path | Purpose |
|:---|:---|:---|
| `useDispatchBoard` | `features/dispatch-board/hooks/useDispatchBoard.ts` | TanStack Query: GET `/api/v1/schedule/board`; date range + filter params |
| `useMoveJob` | `features/dispatch-board/hooks/useMoveJob.ts` | Mutation: POST `.../reschedule` + POST `.../assign` with `expected_updated_at`; wraps `useStalenessRetry()` |
| `useCheckConflicts` | `features/dispatch-board/hooks/useCheckConflicts.ts` | Mutation (preview-only): POST `/api/v1/schedule/jobs/{id}/check-conflicts`; no side effects |
| `useDispatchSse` | `features/dispatch-board/hooks/useDispatchSse.ts` | Composes `useSseChannel`; invalidates TanStack Query board cache on SSE events |
| `useDragConflictPreview` | `features/dispatch-board/hooks/useDragConflictPreview.ts` | Debounced conflict check during drag; feeds `DragPreviewBlock` with real-time severity |
| `useDriveTime` | `features/dispatch-board/hooks/useDriveTime.ts` | GET `POST /api/v1/schedule/drive-times`; reads from TanStack Query cache |
| `useJobDetail` | `features/dispatch-board/hooks/useJobDetail.ts` | TanStack Query: GET `/api/v1/jobs/{job_id}` + GET `/api/v1/jobs/{job_id}/projected-margin` |
| `useProfitability` | `features/profitability/hooks/useProfitability.ts` | TanStack Query: GET `/api/v1/reports/profitability`; period + filter params |
| `useMarginBucketConfig` | `features/profitability/hooks/useMarginBucketConfig.ts` | Reads `margin_bucket_boundaries` + `margin_target_pct` from tenant settings API (fetched once, cached) |
| `useDispatchBoardStore` | `features/dispatch-board/store.ts` | Zustand: filter state (checked techs/statuses/customers/job-types/priorities), active view tab (day/4-day/week/month), active date, selected job ID, conflict preview open state |

#### A.2.8 `<InFlightSyncIndicator>` First Consumer Integration

The FE-B1 skeleton at `packages/ui/src/sync-indicator/` is already exported. FE-B4 is its first consumer. The integration point is `DispatchToolbar.tsx`:

```tsx
// apps/web/src/features/dispatch-board/components/DispatchToolbar.tsx
import { InFlightSyncIndicator } from '@pilot/ui/sync-indicator';

// In toolbar JSX:
<InFlightSyncIndicator
  surface="dispatch"
  pendingCount={optimisticMoveCount}
  syncState={sseConnected ? 'idle' : 'error'}
  lastSyncedAt={lastBoardFetch}
/>
```

Data flow: `pendingCount` comes from `useMoveJob`'s optimistic mutation queue length (TanStack Query `useMutationState`). `sseConnected` comes from `useDispatchSse`. This validates the FE-B1 skeleton API with real data before FE-B15 generalizes it.

---

## B. Execution Order

Strict intra-batch dependency order. Each item must be complete before the next begins (unless marked "parallel-safe").

| # | Item | Dependency Rationale | Est. Days |
|:---|:---|:---|:---:|
| 1 | **MSW stubs** — `apps/web/src/mocks/handlers/schedule.ts`; stubs for all BE-B3 endpoints per §13.7 contract | Nothing else in FE-B4 can run against tests without mocks | 0.5 |
| 2 | **Dispatch board base view** — `DispatchGrid`, `DispatchGridColumn`, `TechColumnHeader`, `AvailabilityZone`, `NowLine`, `FilterSidebar`, `DispatchInfoBar`; static layout with mock data | Core visual foundation; items 3–9 attach here | 3 |
| 3 | **Drag-drop + optimistic locking** — install `react-dnd` + HTML5 backend; wire `DndProvider`, `JobBlock` draggable, `DispatchGridColumn` drop target; `useMoveJob` with `useStalenessRetry()` integration point (hook created in item 4) | Drag-drop provides the UX frame; items 4–5 provide correctness | 3 |
| 4 | **`useStalenessRetry()` + `<StalenessRefreshDialog>`** — shared hook + component in `packages/ui/src/hooks/useStalenessRetry.ts` and `packages/ui/src/staleness-refresh-dialog/` | Must exist before item 3's `useMoveJob` wires it; establishes the shared interface locked for FE-B5/B8/B9/B10 | 1.5 |
| 5 | **`useSseChannel()` hook + `useDispatchSse`** — shared hook in `packages/ui/src/hooks/useSseChannel.ts`; dispatch consumer in `features/dispatch-board/hooks/useDispatchSse.ts`; connects SSE events to TanStack Query cache invalidation | Real-time updates require SSE channel; builds on the static board from item 2 | 2 |
| 6 | **`<InFlightSyncIndicator>` first consumer** — wire `DispatchToolbar` to read pending move count from `useMutationState`; compose the FE-B1 skeleton with live data | Validates skeleton API before FE-B15 generalization; small once items 3–5 exist | 1 |
| 7 | **Conflict preview pane** — `ConflictPreviewPane`, `ConflictItem`, `ConflictSeverityBadge`, `useDragConflictPreview`, four-class severity visual treatment | Conflict UI requires drag-drop (item 3) and data from check-conflicts API | 2 |
| 8 | **Drive-time visualization** — `DriveTimeMarker`, `useDriveTime`; inline between consecutive tech jobs; tooltip on drag ghost | Layered onto the dispatch grid from item 2; requires job positions from item 3 | 1 |
| 9 | **Job detail panel** — `JobDetailPanel`, `JobDetailHeader`, `TimeEntryList`; slide-in on job block click; composing `useJobDetail` hook | Required before profitability items can be composed; the panel is the mount point | 2 |
| 10 | **Profitability widget** — `JobProfitabilityCard`, `MarginBucketChip`, `ProgressWithOverrun`, `ETCDrillDown`, `ETCLineRow`; composed inside `JobDetailPanel` | Requires job detail panel (item 9) and `useMarginBucketConfig` with tenant settings | 2 |
| 11 | **Profitability reports page** — `ProfitabilityPage`, `PeriodSelector`, `LiveJobsSection`, `LiveJobRow`, `ClosedJobsSection`, `MetricsCardRow`, `MarginBarChart`, `DrillDownPanel`, `ChartThresholdNotice`, `PinToDashboardButton`; route at `/reports` sub-surface | Standalone surface; depends on `useProfitability` + margin bucket config; last because profitability widget (item 10) shares hooks and types | 2 |

---

## C. New Routes

All routes are under the existing `apps/web/src/app/(authed)/` layout which applies `<RequireAuth>` + `NotificationQueueProvider`.

| Route | File | Auth | RBAC Gate | Notes |
|:---|:---|:---:|:---|:---|
| `/schedule` | `apps/web/src/app/(authed)/schedule/page.tsx` | ✅ | `<RoleGate role={['owner', 'operator']}>` via `schedule.manage` permission | **Replaces the existing placeholder** created in FE-B0. Renders `<DispatchBoardPage>`. |
| `/reports` | `apps/web/src/app/(authed)/reports/page.tsx` | ✅ | `<RoleGate role={['owner', 'operator']}>` | **Replaces placeholder**. Renders `<ProfitabilityPage>` (other report types are FTU state for MVP). |

**No new sub-routes** are introduced in FE-B4. The job detail panel is a **slide-in panel** rendered at the `/schedule` route (not a separate route) to preserve grid context. This is consistent with the spec's "drill-down as inline panel" pattern (profitability spec §7).

**URL state**: Active date, view mode (day/4day/week/month), and filter state are stored in URL search params (via `useRouter` + `useSearchParams`) so the dispatcher can share a specific board view via URL. Filter state in URL is serialized as a comma-separated list of active filter values.

---

## D. API Endpoint Consumption

### D.1 Endpoint → TanStack Query Hook Mapping

| Endpoint | Method | Hook | MSW Handler | Notes |
|:---|:---|:---|:---|:---|
| `/api/v1/schedule/board` | GET | `useDispatchBoard()` | ✅ Required | Returns jobs × techs × date range. **Not yet in openapi.json** — BE-B3 pending. MSW stub returns mock `DispatchBoardResponse`. |
| `/api/v1/schedule/jobs/{id}/reschedule` | POST | `useMoveJob()` via `useStalenessRetry()` | ✅ Required | Accepts `expected_updated_at`. Returns 409 on staleness. **Not yet in openapi.json**. |
| `/api/v1/schedule/jobs/{id}/assign` | POST | `useMoveJob()` via `useStalenessRetry()` | ✅ Required | Tech assignment change (cross-column drag). **Not yet in openapi.json**. |
| `/api/v1/schedule/jobs/{id}/check-conflicts` | POST | `useCheckConflicts()` + `useDragConflictPreview()` | ✅ Required | Preview-only; no side effects. Returns `SchedulingConflict[]`. **Not yet in openapi.json**. |
| `/api/v1/schedule/drive-times` | POST | `useDriveTime()` | ✅ Required | Batch drive-time matrix request. **Not yet in openapi.json**. |
| `/api/v1/schedule/board/stream` | GET (SSE) | `useSseChannel()` → `useDispatchSse()` | ✅ Required (SSE mock) | SSE endpoint per §13.11. JWT passed as URL query param. **Not yet in openapi.json**. |
| `/api/v1/schedule/availability/{user_id}` | GET | `useAvailability()` (surface-scoped) | ✅ Required | Tech availability for column zone rendering. |
| `/api/v1/jobs/{job_id}` | GET | `useJobDetail()` | Already in openapi.json ✅ | Full job detail including time entries. |
| `/api/v1/jobs/{job_id}/projected-margin` | GET | `useJobDetail()` (combined query) | Already in openapi.json ✅ | Returns `projected_margin_pct`, `cost_to_date_cents`, `etc_hours_remaining` aggregate. |
| `/api/v1/reports/profitability` | GET | `useProfitability()` | Already in openapi.json ✅ | Returns live jobs + closed-period buckets with margin data. |

### D.2 Backend Dependency Status

> **BE-B3 is not yet landed.** All `/api/v1/schedule/*` endpoints require MSW stubs for development and unit/integration tests. The `/api/v1/jobs/{job_id}/projected-margin` and `/api/v1/reports/profitability` endpoints are already present in `backend/openapi.json` and will use real generated types once `pnpm sync-api-types` is run.

### D.3 MSW Handler Stub Architecture

```
apps/web/src/mocks/handlers/
  schedule.ts       ← NEW: all /api/v1/schedule/* stubs including SSE
  jobs.ts           ← NEW: projected-margin stub (existing jobs stubs are in place)
  reports.ts        ← NEW: profitability stub
```

**SSE mock strategy**: The SSE endpoint (`/api/v1/schedule/board/stream`) cannot be intercepted by MSW's standard HTTP handlers. Use a `ReadableStream` mock in the MSW handler returning a mock SSE text stream. For unit tests that exercise SSE event handling, use a direct event emitter approach: `useDispatchSse` accepts an optional `eventSourceFactory` prop for test injection.

### D.4 TypeScript Interface Stubs (BE-B3 Not Yet In openapi.json)

Until `pnpm sync-api-types` delivers BE-B3 types, these stubs live in:
`apps/web/src/features/dispatch-board/types-stub.ts`

```typescript
// DELETE this file once pnpm sync-api-types delivers BE-B3 types

export interface TechDisplayColor {
  hex: string;
  name: string;
}

export interface DispatchBoardJob {
  id: string;
  title: string;
  customer_name: string;
  site_address: string;
  scheduled_start_at: string; // ISO 8601
  scheduled_end_at: string;
  tech_id: string | null;
  status: 'unassigned' | 'scheduled' | 'in_progress' | 'confirmed';
  priority: 'rush' | 'standard' | 'warranty';
  customer_type: 'commercial' | 'residential';
  job_type: string;
  updated_at: string;           // version field for staleness check
}

export interface DispatchBoardTech {
  id: string;
  name: string;
  display_color: TechDisplayColor;
  avatar_url: string | null;
}

export interface DispatchBoardResponse {
  date: string;                 // YYYY-MM-DD
  techs: DispatchBoardTech[];
  jobs: DispatchBoardJob[];
}

export interface MoveJobRequest {
  tech_id: string | null;
  scheduled_start_at: string;
  scheduled_end_at: string;
  expected_updated_at: string;  // §16.4 staleness check field
}

export interface SchedulingConflict {
  conflict_class: 'overlap' | 'availability' | 'travel' | 'info';
  severity: 'block' | 'warn' | 'info';
  detail: Record<string, unknown>;
  affected_job_id: string;
  suggested_resolution: string | null;
}

export interface CheckConflictsRequest {
  tech_id: string | null;
  scheduled_start_at: string;
  scheduled_end_at: string;
}

export interface CheckConflictsResponse {
  conflicts: SchedulingConflict[];
  has_blocking_conflicts: boolean;
}

export interface DriveTimeRequest {
  segments: Array<{ from_job_id: string; to_job_id: string }>;
  date: string;
}

export interface DriveTimeSegment {
  from_job_id: string;
  to_job_id: string;
  drive_time_seconds: number;
  drive_distance_meters: number;
  is_feasible: boolean;         // false when drive time > scheduled gap
  cached: boolean;
}

export interface DriveTimeResponse {
  segments: DriveTimeSegment[];
}

export interface SseBoardEvent {
  event_type:
    | 'job_scheduled'
    | 'job_rescheduled'
    | 'job_reassigned'
    | 'job_unassigned'
    | 'conflict_detected'
    | 'conflict_cleared'
    | 'calendar_sync_status';
  job_id?: string;
  tech_id?: string;
  prev_tech_id?: string;
  new_tech_id?: string;
  scheduled_start_at?: string;
  prev_start_at?: string;
  new_start_at?: string;
  conflict_class?: SchedulingConflict['conflict_class'];
  severity?: SchedulingConflict['severity'];
}
```

---

## E. Pattern Reuse Decisions

### E.1 Patterns Consumed from Prior Batches

| Pattern | Shared Module | Import Path | How Used in FE-B4 |
|:---|:---|:---|:---|
| States catalog | `EmptyState`, `LoadingState`, `ErrorState` | `@pilot/ui/states` or `@pilot/ui` | `DispatchBoardPage` shows `<LoadingState type="full-page">` while board loads; `<EmptyState type="no-data">` when no jobs in period |
| Notification banner | `NotificationBanner`, `useNotificationQueue` | `@pilot/ui/notification-banner` | Dispatch move success/failure; conflict override confirmation; SSE reconnect warning |
| Auth + RBAC | `RoleGate`, `useRequiresPermission` | `@pilot/ui` | `/schedule` and `/reports` routes gated to `schedule.manage` permission |
| In-flight sync indicator | `InFlightSyncIndicator` | `@pilot/ui/sync-indicator` | First real consumer in `DispatchToolbar`; validates FE-B1 skeleton API |
| Voice confirm-as-turn | `VoiceConfirmTurn`, `useVoiceConfirmation` | `@pilot/ui/voice-confirm-turn` | Voice-dispatched job moves confirm via confirm-as-turn before committing |

### E.2 Patterns Established in FE-B4 (Consumed by Downstream Batches)

| Pattern | Shared Module | File Path | First Downstream Consumer |
|:---|:---|:---|:---|
| 409 staleness retry | `useStalenessRetry()` + `<StalenessRefreshDialog>` | `packages/ui/src/hooks/useStalenessRetry.ts` + `packages/ui/src/staleness-refresh-dialog/` | FE-B5 (quote approval) |
| SSE channel | `useSseChannel()` | `packages/ui/src/hooks/useSseChannel.ts` | FE-B8 (calendar conflicts), FE-B10 (SMS threads), FE-B12 (notifications) |
| Four-class conflict severity visual | `ConflictSeverityBadge` + token mapping | `packages/ui/src/conflict-severity/` (shared) | FE-B7 (offline sync), FE-B8 (calendar), FE-B9 (QB) |
| Dispatch board Zustand store pattern | `useDispatchBoardStore` | `apps/web/src/features/dispatch-board/store.ts` | FE-B8 extends the store pattern for calendar conflict UI state |

### E.3 What FE-B4 Does NOT Establish (Intentional Deferrals)

| Item | Deferred To | Why |
|:---|:---|:---|
| `<DiffView>` | FE-B5 | Not needed in FE-B4's staleness dialog (we show refreshed slot state, not a diff). Diff view is FE-B5's canonical output. |
| `<PendingBadge>` / `useOptimisticMutation()` | FE-B7 | FE-B4 uses TanStack Query's built-in optimistic update + `useMutationState` for pending count. Full offline-first `<PendingBadge>` pattern is FE-B7's domain. |
| Mobile dispatch view | Phase 2 | Spec explicitly defers mobile dispatch (field-mode tablet view is Phase 2). |

---

## F. Shared Module Interfaces

These interfaces are **canonical and locked for downstream batch consumption**. Any change requires explicit downstream impact review.

### F.1 `useStalenessRetry<TVariables, TRefreshedState>`

**File**: `packages/ui/src/hooks/useStalenessRetry.ts`  
**Export path**: `@pilot/ui/hooks` + `@pilot/ui`

```typescript
import type { UseMutationOptions, UseMutationResult } from '@tanstack/react-query';

/** The raw 409 Conflict response body from any backend endpoint using the §16.4 pattern */
export interface StalenessConflictPayload<TRefreshedState> {
  status: 409;
  title: string;                    // "Record updated since last view"
  detail: string;                   // Human-readable explanation
  refreshed_state: TRefreshedState; // Freshly fetched server state
}

/**
 * Options passed to useStalenessRetry.
 *
 * @template TVariables - The mutation variables type (must include a version field, e.g., expected_updated_at)
 * @template TData - The mutation success response type
 * @template TRefreshedState - The refreshed server state type returned in the 409 body
 */
export interface UseStalenessRetryOptions<TVariables, TData, TRefreshedState> {
  /** The underlying mutation function — identical signature to useMutation's mutationFn */
  mutationFn: (variables: TVariables) => Promise<TData>;

  /**
   * Called when a 409 is received with refreshed state.
   * Return updated variables for the retry attempt, or null to cancel.
   * If null, the dialog remains open awaiting user decision.
   */
  onConflict?: (
    refreshedState: TRefreshedState,
    previousVariables: TVariables
  ) => TVariables | null;

  /**
   * Optional: override the dialog's title text.
   * Default: "This record was updated while you were working"
   */
  dialogTitle?: string;

  /**
   * Optional: custom content rendered inside the dialog above the action buttons.
   * Receives refreshed state + original variables. Used by FE-B5+ to render <DiffView>.
   * FE-B4 (dispatch board) renders a simple slot summary — no diff needed here.
   */
  renderConflictContent?: (params: {
    refreshedState: TRefreshedState;
    previousVariables: TVariables;
  }) => React.ReactNode;

  /** Any additional UseMutation options (onSuccess, onError, etc.) */
  mutationOptions?: Omit<
    UseMutationOptions<TData, unknown, TVariables>,
    'mutationFn'
  >;
}

/**
 * Return value of useStalenessRetry.
 *
 * The StalenessDialog component MUST be rendered in the same tree.
 * It is null when no staleness conflict is pending.
 */
export interface UseStalenessRetryReturn<TVariables, TData> {
  /** Call this like useMutation's mutate — staleness handling is transparent */
  mutate: (variables: TVariables) => void;

  /** Async version for use in event handlers that await the result */
  mutateAsync: (variables: TVariables) => Promise<TData>;

  /** True when a 409 was received and the dialog is open */
  isStalenessDialogOpen: boolean;

  /**
   * The dialog component. Must be rendered somewhere in the component tree.
   * Typically rendered adjacent to the trigger button.
   */
  StalenessDialog: React.FC;

  /** Forward the full TanStack Query mutation result for status tracking */
  mutation: UseMutationResult<TData, unknown, TVariables>;
}

export declare function useStalenessRetry<TVariables, TData, TRefreshedState>(
  options: UseStalenessRetryOptions<TVariables, TData, TRefreshedState>
): UseStalenessRetryReturn<TVariables, TData>;
```

---

### F.2 `<StalenessRefreshDialog>`

**File**: `packages/ui/src/staleness-refresh-dialog/StalenessRefreshDialog.tsx`  
**Types file**: `packages/ui/src/staleness-refresh-dialog/types.ts`  
**Export path**: `@pilot/ui`

```typescript
export interface StalenessRefreshDialogProps {
  /** Whether the dialog is open */
  isOpen: boolean;

  /** Called when user clicks "Retry with updated data" */
  onRetry: () => void;

  /** Called when user clicks "Cancel" or closes the dialog */
  onCancel: () => void;

  /** Dialog title — defaults to "This record was updated while you were working" */
  title?: string;

  /**
   * Custom content to render in the dialog body above action buttons.
   * FE-B4: renders refreshed slot info (date, tech, time range).
   * FE-B5+: renders <DiffView> showing what changed.
   * If omitted, dialog renders a generic explanation paragraph.
   */
  children?: React.ReactNode;

  /**
   * If true, the "Retry" button is disabled (used while useStalenessRetry is
   * preparing the retry variables). Default false.
   */
  isRetrying?: boolean;
}

export declare const StalenessRefreshDialog: React.FC<StalenessRefreshDialogProps>;
```

**Visual spec for FE-B4 dispatch context** (no `<DiffView>` yet):
```
┌──────────────────────────────────────────────────────────┐
│  ⚠️  Schedule changed while you were working              │
│                                                           │
│  The job was moved since you loaded the board.            │
│  Current assignment:                                      │
│  • Tech: Mike Chen                                        │
│  • Time: Tue Jun 10, 9:00 AM – 11:00 AM                  │
│                                                           │
│  Would you like to retry your move with the latest info?  │
│                                                           │
│  [Cancel]                    [Retry with updated data]    │
└──────────────────────────────────────────────────────────┘
```
Uses shadcn/ui `<Dialog>` component. Amber `⚠️` icon from Pass 1 warning token.

---

### F.3 `useSseChannel()`

**File**: `packages/ui/src/hooks/useSseChannel.ts`  
**Export path**: `@pilot/ui/hooks` + `@pilot/ui`

```typescript
export interface SseMessage {
  /** SSE event `id` field (used for Last-Event-ID reconnection header) */
  id?: string;
  /** SSE event `event` field (the named event type) */
  type?: string;
  /** SSE event `data` field (raw string — parse as JSON in onMessage) */
  data: string;
}

export interface UseSseChannelOptions {
  /**
   * The SSE endpoint path (without origin). JWT is appended as ?token= query param.
   * Example: '/api/v1/schedule/board/stream'
   */
  path: string;

  /**
   * Called for each received SSE message. Parse event.data as JSON for structured events.
   * SSE messages carry cache-invalidation cues, NOT full payloads.
   */
  onMessage: (message: SseMessage) => void;

  /**
   * If set (milliseconds), the hook falls back to polling at this interval
   * when the EventSource connection fails or is unsupported.
   * Polling calls `pollFn` — if pollFn is omitted, fallback polling is a no-op.
   * Recommended: 60_000 (60 seconds) per mvp-arch.md §13.11.
   */
  fallbackToPollingMs?: number;

  /**
   * Optional polling function invoked when SSE is unavailable.
   * Receives no arguments; should invalidate TanStack Query keys directly.
   */
  pollFn?: () => void;

  /**
   * Whether the channel should be active. Set to false to disconnect
   * (e.g., when tab is backgrounded). Default: true.
   */
  enabled?: boolean;

  /**
   * Retry delay in milliseconds between reconnection attempts.
   * Uses exponential backoff up to this maximum. Default: 60_000.
   */
  maxRetryDelayMs?: number;

  /**
   * Optional factory function for creating EventSource instances.
   * Used for test injection to replace native EventSource with a mock.
   * Default: (url) => new EventSource(url)
   */
  eventSourceFactory?: (url: string) => EventSource;
}

export interface UseSseChannelReturn {
  /** True when EventSource is open and receiving messages */
  isConnected: boolean;
  /** True when in fallback polling mode */
  isPolling: boolean;
  /** Last received message, or null */
  lastMessage: SseMessage | null;
  /** Error from last connection attempt, or null */
  connectionError: Event | null;
  /** Manually close the connection */
  disconnect: () => void;
  /** Manually reconnect (resets backoff) */
  reconnect: () => void;
}

export declare function useSseChannel(
  options: UseSseChannelOptions
): UseSseChannelReturn;
```

**Behavior contract**:
1. On mount: opens `EventSource` at `${API_BASE_URL}${path}?token=${jwtToken}`
2. JWT token read from `useAuth()` context — never stored in URL more than the initial handshake
3. On message: calls `onMessage` with parsed `SseMessage`
4. On error: exponential backoff up to `maxRetryDelayMs`; if `fallbackToPollingMs` is set, starts polling after 3 failed reconnect attempts
5. On unmount: closes `EventSource` cleanly
6. `Last-Event-ID` header sent on reconnect (native `EventSource` behavior)

---

### F.4 Additional Shared Types: `ConflictSeverityClass`

**File**: `packages/ui/src/conflict-severity/types.ts`  
(New shared location for the four-class severity visual mapping established in FE-B4)

```typescript
/** Per mvp-arch.md §13.4 — dispatch conflict classification */
export type DispatchConflictClass = 'overlap' | 'availability' | 'travel' | 'info';

/** Per mvp-arch.md §16.6 — four-tier severity routing */
export type FourClassSeverity = 'block' | 'warn' | 'info';

/** Visual token keys for each conflict class (resolve to Pass 1 tokens) */
export interface ConflictVisualTokens {
  badgeColor: string;       // Token key e.g. 'color.semantic.error'
  badgeText: string;        // Display label
  bannerVariant: 'error' | 'warning' | 'info' | 'neutral';
  iconName: string;         // Icon from Pass 1 icon system
  isBlocking: boolean;      // Whether drag snap-back occurs
}

export const CONFLICT_CLASS_TOKENS: Record<DispatchConflictClass, ConflictVisualTokens> = {
  overlap: {
    badgeColor: 'color.semantic.error',
    badgeText: 'Overlap',
    bannerVariant: 'error',
    iconName: 'alert-circle',
    isBlocking: false,  // MVP: warn-only per §13.4; block available Phase 2
  },
  availability: {
    badgeColor: 'color.semantic.warning',
    badgeText: 'Availability',
    bannerVariant: 'warning',
    iconName: 'clock',
    isBlocking: false,
  },
  travel: {
    badgeColor: 'color.semantic.warning',
    badgeText: 'Drive time',
    bannerVariant: 'warning',
    iconName: 'map-pin',
    isBlocking: false,
  },
  info: {
    badgeColor: 'color.semantic.info',
    badgeText: 'Note',
    bannerVariant: 'neutral',
    iconName: 'info',
    isBlocking: false,
  },
};
```

---

## G. Open Questions Resolved

### G.1 Drag-Drop Library: `react-dnd` with HTML5 Backend

**Decision**: Use `react-dnd` with `react-dnd-html5-backend`.

**Rationale**: The impl plan explicitly specifies `react-dnd` with HTML5 backend. This is appropriate for a shadcn/Tailwind dashboard because:
- `react-dnd` is headless — it provides drag state and drop target logic with zero visual opinions. All visual feedback (ghost block, drop target highlight, conflict indicators) is implemented as Tailwind/token-based components.
- The HTML5 backend uses native drag-and-drop events which have better browser support and performance than pointer-event alternatives for desktop web.
- Alternative `@dnd-kit/core` was considered but `react-dnd` is more battle-tested for the calendar grid pattern (multiple overlapping drop targets at different grid granularities).

**Install target**: `apps/web/package.json` only (web-only surface per spec).

```
pnpm --filter web add react-dnd react-dnd-html5-backend
```

### G.2 `useStalenessRetry()` TypeScript Interface — LOCKED

**Decision**: The interface in §F.1 above is the canonical interface. Key design choices:

1. **`StalenessDialog` as a returned React.FC**, not a separate import. The hook owns the dialog state; consumers don't manage dialog open/close directly. This encapsulates the 409 retry loop fully within the hook.
2. **`renderConflictContent` prop on the dialog** allows FE-B5+ to inject `<DiffView>` without changing the hook interface (backward-compatible extension).
3. **`onConflict` returns `TVariables | null`**, not a boolean. Returning updated variables allows the hook to automatically retry with version-bumped data without a second user interaction. Returning `null` keeps the dialog open for explicit user decision.
4. **Generic triple `<TVariables, TData, TRefreshedState>`** keeps the hook type-safe across all consumers (dispatch move, quote approve, calendar resolve, QB resolve).

### G.3 `<StalenessRefreshDialog>` for FE-B4 — No Diff View Yet

**Decision**: For FE-B4 specifically, the dialog shows the **refreshed job slot state** (new tech, new time window) — not a diff between the user's intended move and the current state. This is appropriate because:
- The user's intent was "move to slot X". The refreshed state shows "slot X is now occupied by job Y at time Z."
- A field-level diff would need `<DiffView>` which is established in FE-B5.
- The `renderConflictContent` prop is the escape hatch for FE-B5+ to inject diff rendering without changing the dialog's interface.

### G.4 `useSseChannel()` Placement — Shared with Platform Detection Comment

**Decision**: Lives in `packages/ui/src/hooks/useSseChannel.ts` (shared location). MVP implementation uses native `EventSource` (web-native). A clear comment documents the mobile extension path:

```typescript
// MOBILE EXTENSION NOTE (FE-B10 or later):
// Mobile does not support native EventSource. If useSseChannel is needed on mobile,
// replace the eventSourceFactory default with react-native-sse:
//   import EventSource from 'react-native-sse';
// The public API is identical; only the factory differs.
// Pattern: packages/ui/src/voice/ web/mobile split for reference.
```

This avoids a premature platform split while making the extension path explicit and non-forking.

### G.5 `<InFlightSyncIndicator>` Data Flow

**Decision**: In FE-B4 (dispatch board), the `<InFlightSyncIndicator>` receives its data from:

1. **`pendingCount`**: derived from TanStack Query `useMutationState({ filters: { mutationKey: ['moveJob'] } })` — counts mutations in `pending` state. This reflects optimistic moves that haven't received server confirmation yet.
2. **`syncState`**: derived from `useSseChannel`'s `isConnected` return value. `isConnected = true` → `'idle'`; `isPolling = true` → `'syncing'`; `connectionError` present → `'error'`.
3. **`lastSyncedAt`**: derived from TanStack Query's `dataUpdatedAt` on the board query.

The FE-B1 skeleton accepts these as direct props. FE-B15 will generalize the data-fetching into a unified backend endpoint (`BE-B15/A79`). **FE-B4 does not call a sync-status backend endpoint** — it derives everything from local mutation/SSE state.

### G.6 Conflict Preview Pane — Four-Class Severity Visual Treatment

**Decision**: The four classes map to the following shadcn/ui + Pass 1 token visual treatment:

| Class | Visual Treatment | User Can Proceed |
|:---|:---|:---:|
| `overlap` | Red banner + "Overlap" badge. Toast: "[Tech] is already on [other job]…". Confirm button visible but labeled "Move anyway (not recommended)" with red styling. | ✅ (warn-only in MVP per §13.4) |
| `availability` | Amber banner + "Availability" badge. Toast: "[Tech]'s working hours are X–Y." Standard "Move anyway" CTA. | ✅ |
| `travel` | Amber banner + "Drive time" badge. Inline drive-time marker turns red. "Tight" or "Infeasible" label. "Move anyway" CTA. | ✅ |
| `info` | Blue/neutral pill annotation on the conflict pane. No modal, no blocking. | ✅ (no confirmation needed) |

**No hard blocks in MVP** (per §13.4): all conflicts are `warn` or `info` severity. The `block` severity is reserved for Phase 2 with tenant `strict_mode` configuration.

The conflict pane appears as a **right-side panel** (not modal) so the dispatcher can see both the grid and the conflicts simultaneously. This matches the "inline panel" pattern from the profitability spec §7.

### G.7 `<JobProfitabilityCard>` — Margin Bucket Boundaries Source

**Decision**: `margin_bucket_boundaries` config (default `[10, 20, 30]` percent) comes from the **backend API** — specifically the tenant settings endpoint. Not frontend constants.

**Why**: The profitability spec §4 explicitly states: "Tenant can override boundaries. Tenant can also override the target line (default 20%)." Hardcoding constants would break the configurability contract.

**Implementation**: `useMarginBucketConfig()` hook calls the tenant settings endpoint (BE-B9/A52 catalog pattern — available since settings infrastructure gates FE-B11, not FE-B4). For FE-B4, this becomes a simple GET to a settings endpoint that reads `margin_bucket_boundaries` and `margin_target_pct`. Since BE-B9 is not yet landed, an MSW stub returns the defaults.

**Boundary evaluation logic** (client-side, given the boundaries from the API):
```typescript
function getMarginBucket(
  marginPct: number,
  boundaries: number[] // e.g. [10, 20, 30]
): 'below-low' | 'low' | 'medium' | 'high' {
  if (marginPct < boundaries[0]) return 'below-low';  // red
  if (marginPct < boundaries[1]) return 'low';         // amber
  if (marginPct < boundaries[2]) return 'medium';      // green
  return 'high';                                        // deep green
}
```

### G.8 Drive-Time Visualization — Display Strategy and Missing Data

**Decision**:

1. **Display location**: Drive-time shown as an **inline marker between consecutive tech jobs** on the grid (the `DriveTimeMarker` component). Also displayed in the **conflict preview pane** when a travel conflict exists. This matches the spec's §7 "Between two consecutive jobs…a horizontal dotted line renders with the drive-time label inline."

2. **Tooltip on dragged ghost**: During drag, the `DragPreviewBlock` shows drive time from the prior job to the proposed drop slot **if** a cached value exists in the TanStack Query cache. This is a read-only display — no new API call is triggered during drag itself (prevents API cost explosion per §13.8 caching rationale).

3. **If drive-time data is not yet cached**: `DriveTimeMarker` renders as a neutral "–" placeholder with a subtle "drive time loading" spinner. Drive time is batch-requested when the board loads via `useDriveTime()` for all consecutive job pairs in the current view. If the batch call hasn't resolved yet, the placeholder is shown. If the map provider is unavailable (§13.9 failure mode), the placeholder shows "drive time unavailable" without blocking the dispatch action.

4. **"Tight" vs "Infeasible" labels**: `infeasible` when `drive_time_seconds > gap_seconds`; `tight` when `drive_time_seconds > gap_seconds * 0.8` (20% buffer threshold is a frontend constant, not a backend config, since it's a visual affordance not a business rule).

---

## H. External Dependency Status

### H.1 React-DND

| Item | Status | Action Required |
|:---|:---|:---|
| `react-dnd` + `react-dnd-html5-backend` | ❌ Not installed | `pnpm --filter web add react-dnd react-dnd-html5-backend` during FE-B4 implementation |
| `@types/react-dnd` | Included in `react-dnd` package (ships own types) | No separate install needed |

### H.2 Chart Library

The profitability page requires bar charts. **Decision**: Use **Recharts** (already common in shadcn/ui ecosystem; tree-shakeable; accessible).

| Item | Status | Action Required |
|:---|:---|:---|
| `recharts` | ❌ Not installed | `pnpm --filter web add recharts` during FE-B4 implementation |

Recharts `<BarChart>` with custom `<Cell>` components for margin bucket color coding. The chart uses Pass 1 token values (not hardcoded hex) accessed via CSS custom properties.

### H.3 Backend Gate: BE-B3

| Item | Status | Blocks |
|:---|:---|:---|
| BE-B3 (dispatch + ETC endpoints) | ❌ Not yet landed | Integration tests against real backend |
| MSW stubs for BE-B3 | Must be built in FE-B4 | Component implementation + unit tests |
| `/api/v1/jobs/{job_id}/projected-margin` | ✅ In openapi.json | Real types available |
| `/api/v1/reports/profitability` | ✅ In openapi.json | Real types available |

**Development strategy**: All `/api/v1/schedule/*` endpoint calls go through MSW during FE-B4 development. The `apps/web/src/features/dispatch-board/types-stub.ts` file (§D.4) bridges until `pnpm sync-api-types` delivers the generated types. Integration tests marked with `@jest-environment msw` use the MSW handlers. Real integration tests are marked `@skip-without-be-b3` and run only after BE-B3 lands.

### H.4 Tom Action Items (Pre-Production Delivery)

| Item | Why Required | Urgency |
|:---|:---|:---|
| Google Maps Distance Matrix API key | Drive-time computation in BE-B3 | Pre-production only; MSW mock covers dev |
| Google Calendar OAuth credentials | Calendar sync status indicator in dispatch toolbar | Pre-production; not blocking FE-B4 dev |
| BE-B3 deployment to dev environment | Real integration tests for dispatch board | Required before FE-B4 integration tests |

---

## I. Test Plan

**Test Count Targets**: 80+ unit, 18+ integration, 4+ e2e  
**Test Runner (web)**: Vitest + `@testing-library/react` + MSW  
**E2E**: Playwright  
**Accessibility**: `@axe-core/react` in integration test suite

### I.1 Unit Tests

**New test files** (all co-located with components unless noted):

| File | Component/Hook | Target Tests | Key Scenarios |
|:---|:---|:---:|:---|
| `packages/ui/src/hooks/useStalenessRetry.test.ts` | `useStalenessRetry` | 15 | 409 received → dialog opens; retry with new variables succeeds; cancel closes dialog; non-409 errors propagate; `onConflict` returning null keeps dialog open; `onConflict` returning variables auto-retries; concurrent calls queue correctly |
| `packages/ui/src/hooks/useSseChannel.test.ts` | `useSseChannel` | 12 | Connects on mount; disconnects on unmount; calls `onMessage` on event; exponential backoff on error; fallback to polling after max retries; `enabled=false` prevents connection; `Last-Event-ID` forwarded on reconnect; `reconnect()` resets backoff |
| `packages/ui/src/staleness-refresh-dialog/StalenessRefreshDialog.test.tsx` | `StalenessRefreshDialog` | 8 | Opens/closes correctly; Retry button calls `onRetry`; Cancel calls `onCancel`; `isRetrying=true` disables Retry button; `renderConflictContent` renders children; default title shown when no title prop; accessible dialog role |
| `packages/ui/src/conflict-severity/tokens.test.ts` | `CONFLICT_CLASS_TOKENS` | 4 | All four classes have non-null token values; `isBlocking` is false for all MVP classes; token keys reference valid Pass 1 tokens |
| `features/dispatch-board/components/JobBlock.test.tsx` | `JobBlock` | 8 | Renders title, customer, time range; graceful truncation when block is short; tech color applied as left border; rush/warranty tags show; click opens job detail panel; drag initiates; ARIA draggable attribute set |
| `features/dispatch-board/components/ConflictPreviewPane.test.tsx` | `ConflictPreviewPane` | 6 | Shows all four conflict classes with correct visual treatment; "overlap" shows red badge; "info" shows no blocking state; "Proceed anyway" button renders for all warn classes; empty state when no conflicts |
| `features/dispatch-board/components/DriveTimeMarker.test.tsx` | `DriveTimeMarker` | 5 | Normal state shows drive time in minutes; "tight" state renders amber label; "infeasible" renders red label; loading state renders placeholder; unavailable state renders "–" |
| `features/dispatch-board/hooks/useMoveJob.test.ts` | `useMoveJob` | 8 | Happy path mutation completes; 409 triggers `useStalenessRetry`; optimistic update shown on board; rollback on non-409 error; `expected_updated_at` field included in request body |
| `features/dispatch-board/hooks/useDispatchSse.test.ts` | `useDispatchSse` | 8 | `job_rescheduled` event invalidates board query; `job_reassigned` event invalidates board query; `conflict_detected` event adds conflict to local state; SSE disconnect triggers fallback polling; reconnect restores SSE |
| `features/profitability/components/JobProfitabilityCard.test.tsx` | `JobProfitabilityCard` | 6 | Renders revenue, cost, projected margin; `margin_bucket: 'below-low'` shows red chip; `margin_bucket: 'high'` shows deep green chip; over-quote shows red progress bar + warning glyph; target met shows green progress |
| `features/profitability/components/MarginBarChart.test.tsx` | `MarginBarChart` | 6 | Renders bars for each bucket; clicking bar calls `onBucketSelect`; active bucket shows outline; empty bucket renders visually but doesn't show count tooltip; accessible chart title + role |
| `features/profitability/components/ETCDrillDown.test.tsx` | `ETCDrillDown` | 6 | Renders quote lines; shows hours-logged vs hours-remaining; shows tech breakdown; click row filters time entries; empty state when no ETC data; over-quote line highlighted |
| `features/profitability/hooks/useMarginBucketConfig.test.ts` | `useMarginBucketConfig` | 4 | Returns default boundaries `[10, 20, 30]` from MSW; uses cached data on second call; updates when tenant setting changes |
| `features/dispatch-board/store.test.ts` | `useDispatchBoardStore` | 6 | Filter toggle updates selected filters; view tab changes; date navigation (prev/next/today); selected job ID updates on click; conflict preview state toggles |

**Total unit test target: 102** (exceeds 80+ minimum)

### I.2 Integration Tests

**Location**: `apps/web/__tests__/batch_fe_b4/`

| File | Surface | Target Tests | Key Scenarios |
|:---|:---|:---:|:---|
| `dispatch-board-happy-path.integration.test.tsx` | Dispatch board | 4 | Board loads → techs + jobs render correctly; job drag to new slot → move mutation fires → optimistic update → board re-renders; filter sidebar checkboxes hide/show jobs; date navigation changes board date |
| `staleness-retry-flow.integration.test.tsx` | Dispatch board | 3 | Two simulated concurrent moves: second gets 409 → dialog opens with refreshed slot info → user clicks Retry → mutation fires with new `expected_updated_at` → succeeds; user clicks Cancel → board reverts to pre-drag state |
| `sse-live-updates.integration.test.tsx` | Dispatch board | 3 | SSE `job_rescheduled` event → board rerenders without user action; SSE `conflict_detected` event → conflict badge appears on job block; SSE connection drop → fallback polling activates → board still updates |
| `conflict-preview-pane.integration.test.tsx` | Dispatch board | 2 | Drag job → conflict check → overlap conflict shown with red badge → "Proceed anyway" click fires move mutation; info conflict shows no blocking affordance |
| `drive-time-visualization.integration.test.tsx` | Dispatch board | 2 | Drive times loaded on board init → markers render between consecutive jobs; infeasible drive time → red marker + "infeasible" label; loading state → placeholder shown |
| `job-detail-panel.integration.test.tsx` | Dispatch board | 2 | Click job block → panel slides in with job data + time entries; profitability widget renders margin bucket + ETC breakdown |
| `profitability-page-happy-path.integration.test.tsx` | Profitability reports | 2 | Page loads with default 30d period → live jobs + closed charts render; period selector changes from 30d to MTD → data refetches + charts update |
| `profitability-chart-threshold.integration.test.tsx` | Profitability reports | 2 | Below threshold (4 jobs) → table view with notice; at threshold (8 jobs) → charts render; clicking bar → drill-down panel opens with correct bucket jobs |
| `in-flight-indicator-dispatch.integration.test.tsx` | Dispatch toolbar | 2 | Pending move → indicator shows pending count + "Syncing..."; move completes → count clears + "Synced"; SSE error → indicator shows "Sync error" state |
| `rbac-dispatch-board.integration.test.tsx` | Auth gates | 1 | Tech role user cannot see `/schedule` route (RoleGate hides it); owner role user sees full board |

**Total integration test target: 23** (exceeds 18+ minimum)

### I.3 E2E Tests

**Location**: `e2e/web/batch_fe_b4/`

| File | Flow | Scenario |
|:---|:---|:---|
| `dispatch-board-move.e2e.spec.ts` | Full dispatch move | Load board → drag job to new tech column → confirm → board reflects new assignment → `InFlightSyncIndicator` returns to idle |
| `concurrent-staleness.e2e.spec.ts` | Concurrent staleness | Two browser tabs open same board → Tab 1 moves job → Tab 2 tries to move same job → Tab 2 gets 409 → staleness dialog appears with refreshed state → user retries → succeeds |
| `sse-latency.e2e.spec.ts` | SSE delivery | Move job in Tab 1 → verify Tab 2's board updates within 1000ms via SSE (not refresh) |
| `profitability-drill-down.e2e.spec.ts` | Profitability flow | Open `/reports` → see live jobs with margin indicators → change period → charts update → click bar → drill-down shows correct jobs |

**Total e2e target: 4** (meets 4+ minimum)

### I.4 Accessibility Audit Checkpoints

- `@axe-core/react` runs against `DispatchBoardPage`, `ProfitabilityPage`, `JobDetailPanel`, `ConflictPreviewPane`, and `StalenessRefreshDialog` in integration tests
- Manual keyboard navigation check: dispatch board tabs (Day/4-Day/Week/Month) accessible via arrow keys; filter checkboxes accessible via space bar; job blocks focusable with Enter to open detail panel
- `BarChart` must have `aria-label` and `role="img"` with descriptive title per WCAG 2.1 AA
- `<StalenessRefreshDialog>` must trap focus per WAI-ARIA dialog pattern
- Drag-drop: keyboard alternative for job moves (a "Move Job" button inside the detail panel that opens a slot picker dialog) — ensures accessibility for users who cannot drag

---

## Batch Completion Gate Checklist

Before FE-B4 is marked ✅ COMPLETE in `pilot-app-mvp-frontend-impl-plan.md` §7:

- [ ] All 11 items in §B executed and individually complete
- [ ] `/schedule` route renders full dispatch board (not placeholder)
- [ ] `/reports` route renders profitability page (not placeholder)
- [ ] `useStalenessRetry()`, `<StalenessRefreshDialog>`, `useSseChannel()` exported from `packages/ui/src/index.ts`
- [ ] `CONFLICT_CLASS_TOKENS` exported from `packages/ui/src/conflict-severity/`
- [ ] `packages/ui/src/hooks/index.ts` updated: exports `useStalenessRetry`, `useSseChannel`
- [ ] `react-dnd`, `react-dnd-html5-backend`, `recharts` installed in `apps/web`
- [ ] `apps/web/src/features/dispatch-board/types-stub.ts` created (BE-B3 stubs)
- [ ] MSW handlers: `apps/web/src/mocks/handlers/schedule.ts` + `jobs.ts` + `reports.ts`
- [ ] 102+ unit tests passing
- [ ] 23+ integration tests passing
- [ ] 4+ e2e tests passing (against MSW or real backend)
- [ ] ESLint `no-hardcoded-design-values` zero violations on all new files
- [ ] `@axe-core/react` zero violations on all new surfaces
- [ ] FE-B4 row in §7 tracker updated with component manifest, test file references, test count delta

---

## Downstream Impact Summary

This table captures the contracts FE-B4 locks for downstream batches. **These interfaces MUST NOT be changed without coordinating with the batch that consumes them.**

| Locked Interface | Consuming Batch | Usage |
|:---|:---|:---|
| `useStalenessRetry<TVariables, TData, TRefreshedState>()` signature | FE-B5, FE-B8, FE-B9, FE-B10 | Each batch wraps its primary mutation with this hook; `renderConflictContent` used by FE-B5+ to inject `<DiffView>` |
| `<StalenessRefreshDialog>` props | FE-B5, FE-B8, FE-B9, FE-B10 | Never rendered directly by consumers (rendered by `useStalenessRetry`'s returned `StalenessDialog`); only the `renderConflictContent` escape hatch matters |
| `useSseChannel()` options + return | FE-B8 (calendar SSE), FE-B10 (SMS SSE), FE-B12 (notifications SSE) | Each batch provides its own `path` and `onMessage`; shared reconnect and fallback behavior |
| `CONFLICT_CLASS_TOKENS` mapping | FE-B7, FE-B8, FE-B9 | Import and use directly; do not re-define severity-to-color mappings |
| `<InFlightSyncIndicator>` data contract (pendingCount from mutationState, syncState from SSE) | FE-B15 | FE-B15 will replace the `pendingCount` prop with a backend-driven count; the prop interface must remain backward compatible |
| `PeriodSelector` component | FE-B8+ (any reports surface) | Establishes the canonical 7d/30d/MTD/YTD/Custom selector pattern for all subsequent report surfaces |

---

*Design session completed: 2026-05-22. All 8 required reads completed; all 8 key design decisions resolved. Ready for Phase 2 implementation.*
