/**
 * DispatchBoardPage — Top-level dispatch board composition
 *
 * Location: apps/web/src/features/dispatch-board/components/DispatchBoardPage.tsx
 *
 * DISPATCH-B1 changes:
 *   - DndContext lifted to page level (wraps UnassignedTray + active grid)
 *   - beginMove() unified handler replaces the raw PATCH double-write
 *   - Right-rail arbitration: ConflictPreviewPane has strict priority over JobPropertiesPanel
 *   - UnassignedTray mounted between toolbar and board
 *   - JobContextMenu mounted once at page level
 *   - DispatchBoardLanes vs DispatchGridDayView based on layoutMode
 *   - useCheckConflicts wired into the move pipeline
 *   - showLaneFullCta state managed here (passed to DispatchBoardLanes)
 *   - DELETED: raw apiClient.patch('/api/v1/jobs/{id}') double-write
 *
 * Per batch-fe-b4-design.md §A.2.1 + DISPATCH-B1 design doc §F / UI spec §4
 */

"use client";

import React, { useCallback, useState } from "react";
import {
  DndContext,
  useSensor,
  useSensors,
  PointerSensor,
  type DragEndEvent,
} from "@dnd-kit/core";

import { LoadingState, ErrorState } from "@pilot/ui";
import { useDispatchBoard } from "../hooks/useDispatchBoard";
import { useMoveJob } from "../hooks/useMoveJob";
import { useCheckConflicts } from "../hooks/useCheckConflicts";
import { useDispatchSse } from "../hooks/useDispatchSse";
import { useScheduleLaneCount } from "../hooks/useScheduleLaneCount";
import { useTenantUsers } from "../../users/hooks/useTenantUsers";
import { useDispatchBoardStore, getTabDays } from "../store";
import { DispatchToolbar } from "./DispatchToolbar";
import { FilterBar } from "./FilterBar";
import { DispatchBoardLanes } from "./DispatchBoardLanes";
import { DispatchWeekView } from "./DispatchWeekView";
import { DispatchWeekLaneView } from "./DispatchWeekLaneView";
import { MonthCalendarGrid } from "./MonthCalendarGrid";
import { JobPropertiesPanel } from "./JobPropertiesPanel";
import { DispatchInfoBar } from "./DispatchInfoBar";
import { ConflictPreviewPane } from "./ConflictPreviewPane";
import { UnassignedTray } from "./UnassignedTray";
import {
  DispatchGridDayView,
  checkTechOverCapacity,
} from "./DispatchGridDayView";
import { JobContextMenu, type JobContextMenuState } from "./JobContextMenu";
import { RoleGate } from "@pilot/ui/role-gate";
import type { DispatchBoardFilters } from "../store";
import type { ScheduledJob } from "./DispatchBoardLanes";
import type { DispatchBoardJob } from "../types-stub";
import {
  pxToDate,
  snapTo15Min,
  LANE_LABEL_WIDTH_PX,
} from "../utils/timeHelpers";
import { checkLaneAvailability } from "./DispatchBoardLanes";

/** Add N days to a YYYY-MM-DD string, returns YYYY-MM-DD */
function addDays(dateStr: string, days: number): string {
  const d = new Date(dateStr + "T12:00:00");
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

/** Get the Monday (YYYY-MM-DD) for the week containing dateStr */
function getMondayOf(dateStr: string): string {
  const d = new Date(dateStr + "T12:00:00");
  const day = d.getDay(); // 0=Sun, 1=Mon...
  const diff = (day + 6) % 7;
  d.setDate(d.getDate() - diff);
  return d.toISOString().slice(0, 10);
}

/**
 * Filter visible jobs based on active filter state.
 * Hidden items remain in DB — pure visibility filtering.
 */
function applyFilters(
  jobs: ReturnType<typeof useDispatchBoard>["data"] extends infer T
    ? T extends { jobs: infer J }
      ? J
      : never
    : never,
  filters: DispatchBoardFilters,
) {
  if (!jobs) return [];
  return jobs.filter((job) => {
    if (
      filters.techIds.length > 0 &&
      !filters.techIds.includes(job.tech_id ?? "")
    ) {
      if (job.tech_id !== null) return false;
    }
    if (filters.statuses.length > 0 && !filters.statuses.includes(job.status)) {
      return false;
    }
    // null-safe: a job with no customer_type is excluded when a type filter is active
    if (
      filters.customerTypes.length > 0 &&
      !filters.customerTypes.includes(job.customer_type as "person" | "company")
    ) {
      return false;
    }
    // DISPATCH-B3: job type filter now uses job_type_code (real data from CLASS-B1)
    if (
      filters.jobTypes.length > 0 &&
      !filters.jobTypes.includes(job.job_type_code ?? "")
    ) {
      return false;
    }
    if (
      filters.priorities.length > 0 &&
      !filters.priorities.includes(job.priority)
    ) {
      return false;
    }
    return true;
  });
}

/**
 * DispatchBoardPage
 *
 * The full dispatch board page. Protected by RoleGate (schedule.view_all
 * permission — PLP-FIX-10 / INV-BUG-13: converted from the legacy
 * role={["owner","accountant"]} list to the server-authoritative permission
 * gate that matches the BE read gates on the board's data).
 * Orchestrates all sub-components with data from TanStack Query + Zustand store.
 *
 * Day view: DispatchBoardLanes (lane-as-row, layoutMode=lane) OR
 *           DispatchGridDayView (tech-as-row, layoutMode=tech)
 * Week view: DispatchWeekView (tech-as-column, FE-B30)
 * Month view: MonthCalendarGrid
 */
export function DispatchBoardPage() {
  // ── Lane count for MKT-B11 lane board ─────────────────────────────────────
  const {
    laneCount,
    isLoading: laneCountLoading,
    isError: laneCountError,
    isForbidden: laneCountForbidden,
  } = useScheduleLaneCount();

  // ── DISPATCH-B2 fix: use all tenant users as canonical tech list for FilterBar ──
  // board.techs only contains techs with jobs in the current date window.
  // When all jobs are unassigned the array is empty → popover appears empty.
  // useTenantUsers returns ALL active users regardless of job assignments.
  const { data: tenantUsers = [] } = useTenantUsers();
  const filterBarTechs = tenantUsers
    .filter((u) => u.is_active)
    .map((u) => ({
      id: u.user_id,
      tech_id: u.user_id,
      name: u.display_name,
      display_color: u.display_color,
      avatar_url: null as string | null,
    }));

  // ── Zustand store ──────────────────────────────────────────────────────────
  const {
    viewTab,
    activeDate,
    filters,
    layoutMode,
    conflictPreviewOpen,
    setViewTab,
    setActiveDate,
    navigatePrev,
    navigateNext,
    navigateToToday,
    toggleTechFilter,
    toggleStatusFilter,
    toggleCustomerTypeFilter,
    toggleJobTypeFilter,
    togglePriorityFilter,
    clearAllFilters,
    resetStatusFilter,
    setLayoutMode,
    openConflictPreview,
    closeConflictPreview,
  } = useDispatchBoardStore();

  // ── DISPATCH-B2: FilterBar collapse state (in-memory only, not persisted) ──
  const [filterBarCollapsed, setFilterBarCollapsed] = useState(false);

  // ── FE-B30: Week/Month view local state ────────────────────────────────────
  const [weekDaysToShow, setWeekDaysToShow] = useState<5 | 7>(5);
  const [chipDisplayMode, setChipDisplayMode] = useState<"customer" | "tech">(
    "customer",
  );

  // ── Job properties panel state ─────────────────────────────────────────────
  const [selectedJob, setSelectedJob] = useState<ScheduledJob | null>(null);

  // ── Context menu state ─────────────────────────────────────────────────────
  const [contextMenuState, setContextMenuState] =
    useState<JobContextMenuState | null>(null);

  // ── Pending move state (for beginMove pipeline) ────────────────────────────
  const [pendingMove, setPendingMove] = useState<{
    jobId: string;
    techUserId: string;
    start: Date;
    end: Date;
  } | null>(null);

  // ── Lane-full CTA state ────────────────────────────────────────────────────
  const [showLaneFullCta, setShowLaneFullCta] = useState(false);

  // ── Date range ─────────────────────────────────────────────────────────────
  const tabDays = getTabDays(viewTab, activeDate);

  // For week view, always anchor the start to Monday so the query window
  // matches what DispatchWeekView renders. getMondayOf is a no-op for day/month.
  const queryStartDate =
    viewTab === "week" ? getMondayOf(activeDate) : activeDate;
  const endDate = addDays(queryStartDate, tabDays - 1);
  const dateRange = Array.from({ length: tabDays }, (_, i) =>
    addDays(queryStartDate, i),
  );

  // ── Board data ─────────────────────────────────────────────────────────────
  const { data: board, dataUpdatedAt } = useDispatchBoard(
    queryStartDate,
    endDate,
  );
  const {
    moveJob,
    StalenessDialog,
    isPending: isMoveJobPending,
  } = useMoveJob(activeDate, endDate);
  const checkConflicts = useCheckConflicts();
  const { sseConnected } = useDispatchSse({ activeDate });

  const lastBoardFetch = dataUpdatedAt ? new Date(dataUpdatedAt) : null;
  const filteredJobs = applyFilters(
    board?.jobs ?? [],
    filters,
  ) as ScheduledJob[];

  // ── Optimistic preview for pending move ────────────────────────────────────
  // When a drag is in progress (pendingMove set, ConflictPreviewPane open),
  // optimistically apply the move to the job list so the grid shows the job
  // in its target cell during the confirmation step. If the user cancels,
  // pendingMove → null and the list reverts to its original state.
  // This matches the DISPATCH-B1 spec §E "always-preview-before-commit" pattern.
  const visibleJobs: ScheduledJob[] = pendingMove
    ? filteredJobs.map((j) => {
        if (j.id !== pendingMove.jobId) return j;
        return {
          ...j,
          tech_id: pendingMove.techUserId || j.tech_id,
          scheduled_start_at: pendingMove.start.toISOString(),
          scheduled_end_at: pendingMove.end.toISOString(),
        };
      })
    : filteredJobs;

  // Unassigned jobs: tech_id is null (set to null by normalizeJob for raw.unassigned entries).
  // primary_assignment_id is now also passed through from the B1 board response and could be
  // used as an alternative signal, but tech_id === null is the canonical indicator since
  // normalizeJob() explicitly sets it to null for all unassigned board entries.
  const unassignedJobs = visibleJobs.filter(
    (j) => j.tech_id === null,
  ) as unknown as DispatchBoardJob[];

  // ── DnD sensors — PointerSensor with 8px activation distance ──────────────
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    }),
  );

  // ── beginMove — unified pipeline (check-conflicts → preview → confirm → move) ──
  const beginMove = useCallback(
    (jobId: string, techUserId: string, start: Date, end: Date) => {
      setPendingMove({ jobId, techUserId, start, end });

      checkConflicts.mutate(
        {
          jobId,
          request: {
            tech_user_id: techUserId,
            scheduled_start_at: start.toISOString(),
            scheduled_end_at: end.toISOString(),
          },
        },
        {
          onSettled: () => {
            openConflictPreview(jobId);
          },
        },
      );
    },
    [checkConflicts, openConflictPreview],
  );

  const handleConflictProceed = useCallback(() => {
    if (!pendingMove) return;
    const { jobId, techUserId, start, end } = pendingMove;

    // Get version fields from the board job entry
    const boardJob = board?.jobs?.find((j) => j.id === jobId) as
      | (DispatchBoardJob & {
          version?: number;
          primary_assignment_id?: string | null;
          assignment_version?: number | null;
        })
      | undefined;

    moveJob({
      jobId,
      tech_user_id: techUserId,
      scheduled_start_at: start.toISOString(),
      scheduled_end_at: end.toISOString(),
      expected_job_version: boardJob?.version ?? 1,
      expected_assignment_version: boardJob?.assignment_version ?? undefined,
    });

    closeConflictPreview();
    setPendingMove(null);
  }, [pendingMove, board, moveJob, closeConflictPreview]);

  const handleConflictCancel = useCallback(() => {
    closeConflictPreview();
    setPendingMove(null);
  }, [closeConflictPreview]);

  // ── DnD handlers ──────────────────────────────────────────────────────────

  function handleDragStart() {
    setShowLaneFullCta(false);
  }

  function handleDragEnd(event: DragEndEvent) {
    const { over, active } = event;
    if (!over) return;

    const job = active.data.current?.job as ScheduledJob | undefined;
    if (!job) return;

    const overId = over.id as string;

    // ── Week-lane drop (DISPATCH-B1.5 — cell-lane{N}-{YYYY-MM-DD}) ────────
    // Distinguish from day-lane drops (which start with "lane-") by checking
    // for both laneIndex AND dateStr in the drop data payload.
    if (overId.startsWith("cell-lane")) {
      const laneIndex = over.data.current?.laneIndex as number | undefined;
      const dateStr = over.data.current?.dateStr as string | undefined;
      if (laneIndex === undefined || !dateStr) return;

      // Time-of-day preservation: mirror DispatchWeekView.tsx:537 logic
      let newStartTime: Date;
      if (job.scheduled_start_at) {
        const origStart = new Date(job.scheduled_start_at);
        const pad = (n: number) => String(n).padStart(2, "0");
        const timeOfDay = `T${pad(origStart.getUTCHours())}:${pad(origStart.getUTCMinutes())}:${pad(origStart.getUTCSeconds())}.000Z`;
        newStartTime = new Date(`${dateStr}${timeOfDay}`);
      } else {
        newStartTime = new Date(`${dateStr}T08:00:00.000Z`);
      }

      void handleWeekLaneDrop(job.id, laneIndex, dateStr, newStartTime);
      return;
    }

    // ── Lane drop (day-lane mode) ──────────────────────────────────────────
    if (overId.startsWith("lane-")) {
      const laneIndex = over.data.current?.laneIndex as number | undefined;
      if (laneIndex === undefined) return;

      const dropX = Math.max(
        0,
        (active.rect.current?.translated?.left ?? 0) - LANE_LABEL_WIDTH_PX,
      );
      const boardDate = new Date(activeDate + "T12:00:00");
      const rawStart = pxToDate(
        dropX,
        boardDate,
        6, // will use viewport hours in real usage
      );
      const snappedStart = snapTo15Min(rawStart);
      const durationMs = job.scheduled_end_at
        ? new Date(job.scheduled_end_at).getTime() -
          new Date(job.scheduled_start_at).getTime()
        : 2 * 60 * 60 * 1000;
      const snappedEnd = new Date(snappedStart.getTime() + durationMs);

      const { available } = checkLaneAvailability(
        visibleJobs,
        laneCount,
        snappedStart,
        snappedEnd,
      );

      if (!available) {
        setShowLaneFullCta(true);
        return;
      }

      setShowLaneFullCta(false);
      // Use tech_id from job (lane mode keeps same tech)
      beginMove(job.id, job.tech_id ?? "", snappedStart, snappedEnd);
    }

    // ── Tech row drop (day-tech mode) ──────────────────────────────────────
    if (overId.startsWith("tech-row-")) {
      const techId = over.data.current?.techId as string | undefined;
      if (!techId) return;

      const dropX = Math.max(
        0,
        (active.rect.current?.translated?.left ?? 0) - 128, // TECH_HEADER_WIDTH_PX
      );
      const boardDate = new Date(activeDate + "T12:00:00");
      const rawStart = pxToDate(dropX, boardDate, 6);
      const snappedStart = snapTo15Min(rawStart);
      const durationMs = job.scheduled_end_at
        ? new Date(job.scheduled_end_at).getTime() -
          new Date(job.scheduled_start_at).getTime()
        : 2 * 60 * 60 * 1000;
      const snappedEnd = new Date(snappedStart.getTime() + durationMs);

      // Client-side over-capacity check for tech mode
      const techJobs = visibleJobs.filter((j) => j.tech_id === techId);
      const overCapacity = checkTechOverCapacity(
        techJobs,
        snappedStart,
        snappedEnd,
        job.id,
      );

      if (overCapacity) {
        // Blocked client-side — no API call
        return;
      }

      beginMove(job.id, techId, snappedStart, snappedEnd);
    }
  }

  // ── Week view tech-mode drop handler (DispatchWeekView passthrough) ────────
  const handleWeekJobDrop = useCallback(
    async (
      jobId: string,
      newTechId: string,
      _newDate: string,
      newStartTime: Date,
    ) => {
      const job = visibleJobs.find((j) => j.id === jobId);
      if (!job) return;
      const durationMs =
        new Date(job.scheduled_end_at).getTime() -
        new Date(job.scheduled_start_at).getTime();
      const newEnd = new Date(newStartTime.getTime() + durationMs);
      beginMove(jobId, newTechId || job.tech_id || "", newStartTime, newEnd);
    },
    [visibleJobs, beginMove],
  );

  // ── Week-lane drop handler (DISPATCH-B1.5) ─────────────────────────────────
  // Per Impl Note 6: lane drops preserve the job's existing tech.
  // tech_user_id is the job's current tech_id (not null), or omitted (empty
  // string → backend treats as time-only reschedule) when the job is unassigned.
  // Lane index is client-computed — NOT stored server-side.
  const handleWeekLaneDrop = useCallback(
    async (
      jobId: string,
      _laneIndex: number,
      _dateStr: string,
      newStartTime: Date,
    ) => {
      const job = visibleJobs.find((j) => j.id === jobId);
      if (!job) return;
      const durationMs =
        job.scheduled_end_at && job.scheduled_start_at
          ? new Date(job.scheduled_end_at).getTime() -
            new Date(job.scheduled_start_at).getTime()
          : 2 * 60 * 60 * 1000; // fallback: 2h
      const newEnd = new Date(newStartTime.getTime() + durationMs);
      // Pass the job's existing tech (preserve assignment on lane move).
      // If unassigned (tech_id === null), pass "" so backend treats as time-only.
      beginMove(jobId, job.tech_id ?? "", newStartTime, newEnd);
    },
    [visibleJobs, beginMove],
  );

  // ── Event handlers ─────────────────────────────────────────────────────────

  const handleJobClick = useCallback((job: ScheduledJob) => {
    setSelectedJob(job);
  }, []);

  const handleClosePanel = useCallback(() => {
    setSelectedJob(null);
  }, []);

  const handleJobUpdated = useCallback((updatedJob: ScheduledJob) => {
    setSelectedJob(updatedJob);
  }, []);

  const handleUpgradeClick = useCallback(() => {
    window.location.href = "/settings/billing";
  }, []);

  const handleJobContextMenu = useCallback(
    (e: React.MouseEvent, job: ScheduledJob) => {
      e.preventDefault();
      setContextMenuState({ x: e.clientX, y: e.clientY, job });
    },
    [],
  );

  const handleContextMenuViewJob = useCallback((job: ScheduledJob) => {
    window.location.href = `/jobs/${job.id}`;
  }, []);

  const handleContextMenuJobProperties = useCallback((job: ScheduledJob) => {
    setSelectedJob(job);
  }, []);

  // ── Render guards ──────────────────────────────────────────────────────────

  if (laneCountLoading) {
    return (
      <div className="flex flex-col h-full bg-white items-center justify-center">
        <LoadingState type="full-page" label="Loading schedule…" />
      </div>
    );
  }

  // PLP-FIX-9 (INV-BUG-10): a 403 on the lane-count call (subscription.view
  // gate — owner-only) degrades to default-lane rendering. The full-page
  // ErrorState may only fire on non-403 failures (genuine 5xx).
  if (laneCountError && !laneCountForbidden) {
    return (
      <div className="flex flex-col h-full bg-white items-center justify-center">
        <ErrorState
          type="server"
          title="Failed to load schedule"
          description="Unable to load subscription lane count. Please refresh and try again."
          onRetry={() => window.location.reload()}
        />
      </div>
    );
  }

  // ── Right-rail: conflict pane has strict priority over properties panel ────
  const rightRail = conflictPreviewOpen ? (
    <ConflictPreviewPane
      conflicts={checkConflicts.data ?? null}
      isLoading={checkConflicts.isPending}
      onProceed={handleConflictProceed}
      onCancel={handleConflictCancel}
      isPending={isMoveJobPending}
    />
  ) : selectedJob ? (
    <JobPropertiesPanel
      job={selectedJob}
      onClose={handleClosePanel}
      onJobUpdated={handleJobUpdated}
      techs={board?.techs ?? []}
    />
  ) : null;

  return (
    <RoleGate permission="schedule.view_all">
      <DndContext
        sensors={sensors}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className="flex flex-col h-full bg-white overflow-hidden">
          {/* Toolbar */}
          <DispatchToolbar
            viewTab={viewTab}
            activeDate={activeDate}
            sseConnected={sseConnected}
            lastBoardFetch={lastBoardFetch}
            onViewTabChange={setViewTab}
            onNavigatePrev={navigatePrev}
            onNavigateNext={navigateNext}
            onNavigateToToday={navigateToToday}
            weekDaysToShow={weekDaysToShow}
            onWeekDaysToggle={setWeekDaysToShow}
            chipDisplayMode={chipDisplayMode}
            onChipDisplayModeToggle={setChipDisplayMode}
            layoutMode={layoutMode}
            onLayoutModeToggle={setLayoutMode}
          />

          {/* UnassignedTray — always visible between toolbar and board */}
          <UnassignedTray
            jobs={unassignedJobs}
            onJobClick={(job) => handleJobClick(job as unknown as ScheduledJob)}
          />

          {/* DISPATCH-B2: FilterBar — docked between UnassignedTray and board grid */}
          <FilterBar
            techs={filterBarTechs}
            jobs={board?.jobs ?? []}
            filters={filters}
            collapsed={filterBarCollapsed}
            onToggleCollapsed={() => setFilterBarCollapsed((v) => !v)}
            onToggleTech={toggleTechFilter}
            onToggleStatus={toggleStatusFilter}
            onToggleCustomerType={toggleCustomerTypeFilter}
            onToggleJobType={toggleJobTypeFilter}
            onTogglePriority={togglePriorityFilter}
            onResetStatus={resetStatusFilter}
            onClearAll={clearAllFilters}
          />

          {/* Main content area — board grid + right rail (no left aside) */}
          <div className="flex flex-1 overflow-hidden">
            {/* Board + right rail */}
            <div className="flex flex-row flex-1 min-h-0 overflow-hidden">
              {/* Board grid — takes remaining space */}
              <div className="flex-1 min-w-0 overflow-hidden">
                {/* ── Day view — Lane mode (default) ──────────────────────── */}
                {viewTab === "day" && layoutMode === "lane" && (
                  <DispatchBoardLanes
                    date={new Date(activeDate + "T12:00:00")}
                    laneCount={laneCount}
                    jobs={visibleJobs}
                    onJobClick={handleJobClick}
                    onJobDrop={() => {
                      // handled by DndContext onDragEnd above
                    }}
                    onJobContextMenu={handleJobContextMenu}
                    onUpgradeClick={handleUpgradeClick}
                    showLaneFullCta={showLaneFullCta}
                  />
                )}

                {/* ── Day view — Tech mode ─────────────────────────────────── */}
                {viewTab === "day" && layoutMode === "tech" && (
                  <DispatchGridDayView
                    date={new Date(activeDate + "T12:00:00")}
                    techs={board?.techs ?? []}
                    jobs={visibleJobs}
                    onJobClick={handleJobClick}
                    onJobDrop={() => {
                      // handled by DndContext onDragEnd above
                    }}
                    onJobContextMenu={handleJobContextMenu}
                  />
                )}

                {/* ── Week view — Lane mode (DISPATCH-B1.5 DispatchWeekLaneView) ── */}
                {viewTab === "week" && layoutMode === "lane" && (
                  <DispatchWeekLaneView
                    weekStartDate={activeDate}
                    daysToShow={weekDaysToShow}
                    laneCount={laneCount}
                    jobs={visibleJobs}
                    onJobDrop={handleWeekLaneDrop}
                    onJobClick={handleJobClick}
                    onJobContextMenu={handleJobContextMenu}
                    onNavigateToDate={(dateStr) => {
                      setViewTab("day");
                      setActiveDate(dateStr);
                    }}
                    onViewTabChange={setViewTab}
                  />
                )}

                {/* ── Week view — Tech mode (FE-B30 DispatchWeekView — untouched) ── */}
                {viewTab === "week" && layoutMode === "tech" && (
                  <DispatchWeekView
                    weekStartDate={activeDate}
                    daysToShow={weekDaysToShow}
                    techs={board?.techs ?? []}
                    jobs={visibleJobs}
                    onJobDrop={handleWeekJobDrop}
                    onJobClick={handleJobClick}
                    onNavigateToDate={(dateStr) => {
                      setViewTab("day");
                      setActiveDate(dateStr);
                    }}
                    onViewTabChange={setViewTab}
                  />
                )}

                {/* ── Month view ───────────────────────────────────────────── */}
                {viewTab === "month" && (
                  <MonthCalendarGrid
                    dateRange={dateRange}
                    jobs={board?.jobs ?? []}
                    techs={board?.techs ?? []}
                    onDrillDown={(dateStr) => {
                      setActiveDate(dateStr);
                      setViewTab("day");
                    }}
                    chipDisplayMode={chipDisplayMode}
                    onJobClick={handleJobClick}
                  />
                )}
              </div>

              {/* Right rail — exclusive 320px slot, never both panels */}
              {rightRail}
            </div>
          </div>

          {/* Info bar */}
          <DispatchInfoBar
            techs={board?.techs ?? []}
            jobs={board?.jobs ?? []}
            lastUpdated={lastBoardFetch}
          />

          {/* Staleness dialog */}
          <StalenessDialog />

          {/* Context menu — rendered once at page level, fixed position */}
          <JobContextMenu
            state={contextMenuState}
            onClose={() => setContextMenuState(null)}
            onViewJob={handleContextMenuViewJob}
            onJobProperties={handleContextMenuJobProperties}
          />
        </div>
      </DndContext>
    </RoleGate>
  );
}
