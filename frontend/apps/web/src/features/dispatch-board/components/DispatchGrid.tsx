/**
 * @deprecated FE-B30 (2026-07-12): DispatchBoardPage no longer uses DispatchGrid for
 * week/month views. Week → DispatchWeekView; Month → MonthCalendarGrid (direct).
 * This file is kept to avoid breaking existing tests.
 * Do not use in new code.
 *
 * DispatchGrid — Main calendar grid with tech columns × time rows
 *
 * Location: apps/web/src/features/dispatch-board/components/DispatchGrid.tsx
 *
 * Wraps react-dnd DndProvider with HTML5 backend.
 * Renders tech columns side-by-side with NowLine overlay.
 * On drop: runs check-conflicts → shows ConflictPreviewPane → confirms move.
 *
 * Per batch-fe-b4-design.md §A.2.1 §G.1
 * Updated per batch-beta-v1-fixes-b5-design.md — added viewMode/dateRange routing
 */

"use client";

import React, { useCallback, useState } from "react";
import { DndProvider } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import type { DispatchBoardJob, DispatchBoardTech } from "../types-stub";
import {
  DispatchGridColumn,
  GRID_START_HOUR,
  HOUR_HEIGHT_PX,
} from "./DispatchGridColumn";
import { NowLine } from "./NowLine";
import { ConflictPreviewPane } from "./ConflictPreviewPane";
import { useCheckConflicts } from "../hooks/useCheckConflicts";
import type { JobBlockDragItem } from "./JobBlock";
import type { MoveJobVariables } from "../hooks/useMoveJob";
import type { DispatchViewTab } from "../store";
import { useDispatchBoardStore } from "../store";
import { MultiDayGrid } from "./MultiDayGrid";
import { MonthCalendarGrid } from "./MonthCalendarGrid";

interface DispatchGridProps {
  techs: DispatchBoardTech[];
  jobs: DispatchBoardJob[];
  activeDate: string;
  onJobSelect: (jobId: string) => void;
  onMoveJob: (variables: MoveJobVariables) => void;
  isMoveJobPending?: boolean;
  /** Active view tab — defaults to 'day' for backward compatibility */
  viewMode?: DispatchViewTab;
  /** YYYY-MM-DD array for multi-day panels; required when viewMode is 'week' */
  dateRange?: string[];
}

/** Convert drop top-px offset to ISO start time */
function dropPxToIso(topPx: number, dateStr: string): string {
  const totalMinutes = Math.round((topPx / HOUR_HEIGHT_PX) * 60);
  const startMinutes = GRID_START_HOUR * 60;
  const offsetMinutes = Math.max(0, totalMinutes + startMinutes);
  // Snap to 15-minute grid
  const snappedMinutes = Math.round(offsetMinutes / 15) * 15;
  const hours = Math.floor(snappedMinutes / 60);
  const mins = snappedMinutes % 60;
  const date = new Date(`${dateStr}T00:00:00.000Z`);
  date.setUTCHours(hours, mins, 0, 0);
  return date.toISOString();
}

/** Derive ISO end time by preserving original job duration */
function computeEndIso(
  newStartIso: string,
  originalStartIso: string,
  originalEndIso: string,
): string {
  const durationMs =
    new Date(originalEndIso).getTime() - new Date(originalStartIso).getTime();
  return new Date(new Date(newStartIso).getTime() + durationMs).toISOString();
}

interface PendingMove {
  item: JobBlockDragItem;
  targetTechId: string | null;
  newStartAt: string;
  newEndAt: string;
}

/**
 * DispatchGridDayView — Day view inner component
 *
 * Extracted into its own component so that hooks are always called
 * unconditionally, satisfying the Rules of Hooks. DispatchGrid routes to
 * this component when viewMode === 'day' (or default).
 *
 * Flow on drop:
 *   1. Compute new start/end from drop position
 *   2. Run check-conflicts (preview-only)
 *   3. Show ConflictPreviewPane
 *   4. On confirm: call onMoveJob with expected_updated_at
 *   5. On cancel: discard pending move
 */
function DispatchGridDayView({
  techs,
  jobs,
  activeDate,
  onJobSelect,
  onMoveJob,
  isMoveJobPending = false,
}: {
  techs: DispatchBoardTech[];
  jobs: DispatchBoardJob[];
  activeDate: string;
  onJobSelect: (jobId: string) => void;
  onMoveJob: (variables: MoveJobVariables) => void;
  isMoveJobPending?: boolean;
}) {
  const checkConflicts = useCheckConflicts();
  const [pendingMove, setPendingMove] = useState<PendingMove | null>(null);
  const [showConflictPane, setShowConflictPane] = useState(false);

  const handleDrop = useCallback(
    async (
      item: JobBlockDragItem,
      targetTechId: string | null,
      dropTopPx: number,
    ) => {
      const newStartAt = dropPxToIso(dropTopPx, activeDate);
      const newEndAt = computeEndIso(
        newStartAt,
        item.scheduledStartAt,
        item.scheduledEndAt,
      );

      const move: PendingMove = { item, targetTechId, newStartAt, newEndAt };
      setPendingMove(move);

      // Run conflict check before showing pane
      // DISPATCH-B1: deprecated component — cast to any to avoid type errors

      checkConflicts.mutate({
        jobId: item.jobId,
        request: {
          tech_user_id: targetTechId ?? "",
          scheduled_start_at: newStartAt,
          scheduled_end_at: newEndAt,
        },
      });

      setShowConflictPane(true);
    },
    [activeDate, checkConflicts],
  );

  const handleProceed = useCallback(() => {
    if (!pendingMove) return;

    // DISPATCH-B1: deprecated component — route through /move (no operation split)
    onMoveJob({
      jobId: pendingMove.item.jobId,
      tech_user_id: pendingMove.targetTechId ?? "",
      scheduled_start_at: pendingMove.newStartAt,
      scheduled_end_at: pendingMove.newEndAt,
      expected_job_version: 1, // deprecated component — version unknown, fallback
    });

    setShowConflictPane(false);
    setPendingMove(null);
  }, [pendingMove, onMoveJob]);

  const handleCancelMove = useCallback(() => {
    setShowConflictPane(false);
    setPendingMove(null);
    checkConflicts.reset();
  }, [checkConflicts]);

  return (
    <DndProvider backend={HTML5Backend}>
      <div className="flex flex-1 overflow-hidden">
        {/* Grid columns */}
        <div className="flex-1 overflow-x-auto overflow-y-auto relative">
          <div className="flex relative" style={{ minWidth: "fit-content" }}>
            {/* NowLine spans all columns */}
            <div className="absolute inset-0 pointer-events-none z-10">
              <NowLine />
            </div>

            {/* Tech columns */}
            {techs.map((tech) => (
              <DispatchGridColumn
                key={tech.id}
                tech={tech}
                jobs={jobs}
                onDrop={handleDrop}
                onJobSelect={onJobSelect}
              />
            ))}

            {/* Unassigned column */}
            <DispatchGridColumn
              tech={null}
              jobs={jobs}
              isUnassigned
              onDrop={handleDrop}
              onJobSelect={onJobSelect}
            />
          </div>
        </div>

        {/* Conflict preview pane (right side) */}
        {showConflictPane && (
          <div className="w-72 flex-shrink-0 border-l border-neutral-200 bg-white">
            <ConflictPreviewPane
              conflicts={checkConflicts.data ?? null}
              isLoading={checkConflicts.isPending}
              onProceed={handleProceed}
              onCancel={handleCancelMove}
              isPending={isMoveJobPending}
            />
          </div>
        )}
      </div>
    </DndProvider>
  );
}

/**
 * DispatchGrid
 *
 * View router: delegates to MultiDayGrid (4day/week), MonthDeferredState,
 * or DispatchGridDayView (day default). All props are passed through unchanged.
 */
export function DispatchGrid({
  techs,
  jobs,
  activeDate,
  onJobSelect,
  onMoveJob,
  isMoveJobPending = false,
  viewMode = "day",
  dateRange,
}: DispatchGridProps) {
  const { setActiveDate, setViewTab } = useDispatchBoardStore();

  if (viewMode === "week") {
    return (
      <MultiDayGrid
        dateRange={dateRange ?? [activeDate]}
        techs={techs}
        jobs={jobs}
        onJobSelect={onJobSelect}
      />
    );
  }

  if (viewMode === "month") {
    const handleDrillDown = (dateStr: string) => {
      setActiveDate(dateStr);
      setViewTab("day");
    };
    return (
      <MonthCalendarGrid
        dateRange={dateRange ?? []}
        jobs={jobs}
        onDrillDown={handleDrillDown}
      />
    );
  }

  // viewMode === 'day' (or default)
  return (
    <DispatchGridDayView
      techs={techs}
      jobs={jobs}
      activeDate={activeDate}
      onJobSelect={onJobSelect}
      onMoveJob={onMoveJob}
      isMoveJobPending={isMoveJobPending}
    />
  );
}
