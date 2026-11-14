/**
 * DispatchBoardLanes — Lane-as-row dispatch board layout
 *
 * Location: apps/web/src/features/dispatch-board/components/DispatchBoardLanes.tsx
 *
 * DISPATCH-B1 changes:
 *   - DndContext lifted to DispatchBoardPage (this component no longer wraps its own)
 *   - DraggableJobBlock imported from shared JobBlock.tsx (no visual change)
 *   - Time helpers imported from shared timeHelpers.ts (no behavior change)
 *   - UnscheduledJobQueue + UnscheduledJobCard removed (replaced by UnassignedTray above board)
 *   - unscheduledJobs useMemo removed
 *   - onContextMenu prop added (right-click → JobContextMenu via page)
 *   - showLaneFullCta now a prop (managed by DispatchBoardPage)
 *
 * DISPATCH-B1.5: assignJobsToLanes + checkLaneAvailability extracted to
 *   utils/laneHelpers.ts so DispatchWeekLaneView can share the same algorithm.
 *   This file now imports both from laneHelpers.ts. No behavior change.
 *
 * Per batch-mkt-b11-dispatch-react-engr-prompt.md §Task 2, §Task 3, §Task 6
 * Updated per DISPATCH-B1 design doc §I
 */

"use client";

import React, { useMemo } from "react";
import { useDroppable } from "@dnd-kit/core";
import type { DispatchBoardJob } from "../types-stub";
import { DraggableJobBlock } from "./JobBlock";
import {
  HOUR_WIDTH_PX,
  LANE_HEIGHT_PX,
  LANE_LABEL_WIDTH_PX,
  dateToPx,
  computeViewportHours,
  getHourLabels,
} from "../utils/timeHelpers";
// DISPATCH-B1.5: assignJobsToLanes + checkLaneAvailability moved to shared util
// so DispatchWeekLaneView can import the same algorithm without copying it.
import { assignJobsToLanes, checkLaneAvailability } from "../utils/laneHelpers";

// ─── Re-export constants used by DispatchBoardPage ────────────────────────────
export { LANE_LABEL_WIDTH_PX, HOUR_WIDTH_PX, LANE_HEIGHT_PX };

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ScheduledJob extends DispatchBoardJob {
  /** Client-computed lane index (0-based). Null for unscheduled jobs. */
  laneIndex?: number | null;
}

export interface DispatchBoardLanesProps {
  date: Date;
  laneCount: number;
  jobs: ScheduledJob[];
  onJobClick: (job: ScheduledJob) => void;
  onJobDrop: (jobId: string, laneIndex: number, startTime: Date) => void;
  onUpgradeClick: () => void;
  /** DISPATCH-B1: right-click context menu handler (passes through to JobBlock) */
  onJobContextMenu?: (e: React.MouseEvent, job: ScheduledJob) => void;
  /** DISPATCH-B1: show lane-full CTA, controlled by DispatchBoardPage */
  showLaneFullCta?: boolean;
}

// ─── Lane availability helpers ────────────────────────────────────────────────
// DISPATCH-B1.5: assignJobsToLanes and checkLaneAvailability are now in
// utils/laneHelpers.ts (imported above). Re-export checkLaneAvailability for
// DispatchBoardPage which currently imports it from this file.
export { checkLaneAvailability };

// Re-export computeViewportHours for backward compat (also in timeHelpers.ts)
export { computeViewportHours };
// Re-export assignJobsToLanes for any callers that may import from here
export { assignJobsToLanes };

// ─── Droppable lane row ───────────────────────────────────────────────────────

interface DroppableLaneRowProps {
  laneIndex: number;
  jobs: ScheduledJob[];
  isBlocked: boolean;
  onJobClick: (job: ScheduledJob) => void;
  onJobContextMenu?: (e: React.MouseEvent, job: ScheduledJob) => void;
  boardWidthPx: number;
  viewStartHour: number;
  hourLabels: Array<{ hour: number; label: string }>;
}

function DroppableLaneRow({
  laneIndex,
  jobs,
  isBlocked,
  onJobClick,
  onJobContextMenu,
  boardWidthPx,
  viewStartHour,
  hourLabels,
}: DroppableLaneRowProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: `lane-${laneIndex}`,
    data: { laneIndex },
  });

  return (
    <div
      ref={setNodeRef}
      role="region"
      aria-label={`Schedule lane ${laneIndex + 1}`}
      style={{
        height: `${LANE_HEIGHT_PX}px`,
        width: `${boardWidthPx}px`,
        position: "relative",
      }}
      className={`
        border-b border-neutral-100
        transition-colors
        ${isOver && !isBlocked ? "bg-brand-50/40" : ""}
        ${isBlocked ? "bg-fault-50/20" : ""}
      `}
    >
      {/* Hour grid lines */}
      {hourLabels.map(({ hour }) => (
        <div
          key={hour}
          style={{
            position: "absolute",
            left: `${(hour - viewStartHour) * HOUR_WIDTH_PX}px`,
            top: 0,
            bottom: 0,
          }}
          className="w-px bg-neutral-100"
          aria-hidden="true"
        />
      ))}

      {/* Jobs in this lane */}
      {jobs.map((job) => {
        if (!job.scheduled_start_at || !job.scheduled_end_at) return null;
        const start = new Date(job.scheduled_start_at);
        const end = new Date(job.scheduled_end_at);
        const left = dateToPx(start, viewStartHour);
        const width = Math.max(
          20,
          dateToPx(end, viewStartHour) - dateToPx(start, viewStartHour),
        );

        return (
          <DraggableJobBlock
            key={job.id}
            job={job}
            left={left}
            width={width}
            onClick={onJobClick}
            onContextMenu={onJobContextMenu}
          />
        );
      })}
    </div>
  );
}

// ─── DispatchBoardLanes ───────────────────────────────────────────────────────

/**
 * DispatchBoardLanes
 *
 * Renders the lane-as-row board.
 * DISPATCH-B1: DndContext is now owned by DispatchBoardPage.
 * This component is rendered INSIDE that DndContext.
 */
export function DispatchBoardLanes({
  date: _date, // eslint-disable-line @typescript-eslint/no-unused-vars
  laneCount,
  jobs,
  onJobClick,
  onJobContextMenu,
  onUpgradeClick,
  showLaneFullCta = false,
}: DispatchBoardLanesProps) {
  // ── Dynamic viewport: expand beyond 6am–6pm if any job falls outside ─────
  const { startHour: viewStartHour, endHour: viewEndHour } = useMemo(
    () => computeViewportHours(jobs),
    [jobs],
  );
  const totalViewHours = viewEndHour - viewStartHour;
  const boardWidthPx = totalViewHours * HOUR_WIDTH_PX;

  const laneAssignment = useMemo(
    () => assignJobsToLanes(jobs, laneCount),
    [jobs, laneCount],
  );

  const jobsByLane = useMemo<ScheduledJob[][]>(() => {
    const lanes: ScheduledJob[][] = Array.from({ length: laneCount }, () => []);
    for (const job of jobs) {
      if (!job.scheduled_start_at || job.scheduled_start_at === "null")
        continue;
      const lane = laneAssignment.get(job.id);
      if (lane !== undefined && lane < laneCount) {
        lanes[lane]?.push(job);
      }
    }
    return lanes;
  }, [jobs, laneCount, laneAssignment]);

  const hourLabels = getHourLabels(viewStartHour, viewEndHour);

  return (
    /* min-w-0: REQUIRED — allows this div to shrink below its content width
       so the inner scroll container clips and shows a horizontal scrollbar. */
    <div className="flex flex-col h-full min-w-0">
      {/* Scrollable board.
          overflow-x-scroll: always show the horizontal scrollbar track.
          overflow-y-auto: vertical scroll only when content exceeds height.
          min-h-0: prevents flex-col child from growing to intrinsic height. */}
      <div
        className="flex-1 min-h-0"
        style={{ overflowX: "scroll", overflowY: "auto" }}
      >
        <div
          style={{
            display: "flex",
            minWidth: `${LANE_LABEL_WIDTH_PX + boardWidthPx}px`,
          }}
        >
          {/* Lane label column — sticky left so it stays pinned on horizontal scroll */}
          <div
            style={{
              width: `${LANE_LABEL_WIDTH_PX}px`,
              flexShrink: 0,
              position: "sticky",
              left: 0,
              zIndex: 1,
            }}
            className="bg-neutral-50 border-r border-neutral-200"
          >
            {/* Spacer aligned with time axis header */}
            <div className="h-7 border-b border-neutral-200" />
            {Array.from({ length: laneCount }, (_, i) => (
              <div
                key={i}
                style={{ height: `${LANE_HEIGHT_PX}px` }}
                className="flex items-center justify-center border-b border-neutral-100"
              >
                <span className="text-caption font-semibold text-neutral-400 uppercase tracking-wide">
                  {`L${i + 1}`}
                </span>
              </div>
            ))}
          </div>

          {/* Grid area */}
          <div style={{ width: `${boardWidthPx}px`, flexShrink: 0 }}>
            {/* Time axis header — h-7 = 28px */}
            <div
              style={{ width: `${boardWidthPx}px` }}
              className="relative h-7 border-b border-neutral-200 bg-neutral-50"
              aria-hidden="true"
            >
              {hourLabels.map(({ hour, label }) => (
                <span
                  key={hour}
                  style={{
                    position: "absolute",
                    left: `${(hour - viewStartHour) * HOUR_WIDTH_PX}px`,
                    transform: "translateX(-50%)",
                  }}
                  className="text-caption text-neutral-400 font-medium leading-7"
                >
                  {label}
                </span>
              ))}
            </div>

            {/* Lane rows */}
            {Array.from({ length: laneCount }, (_, laneIndex) => (
              <DroppableLaneRow
                key={laneIndex}
                laneIndex={laneIndex}
                jobs={jobsByLane[laneIndex] ?? []}
                isBlocked={showLaneFullCta}
                onJobClick={onJobClick}
                onJobContextMenu={onJobContextMenu}
                boardWidthPx={boardWidthPx}
                viewStartHour={viewStartHour}
                hourLabels={hourLabels}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Lane-full upgrade CTA */}
      {showLaneFullCta && (
        <div
          role="alert"
          aria-live="assertive"
          className="mx-4 mb-3 mt-1 flex items-center justify-between rounded-lg border border-fault-300 bg-fault-50 px-4 py-3"
        >
          <div className="flex items-center gap-2">
            <svg
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="none"
              aria-hidden="true"
              className="text-fault-600 flex-shrink-0"
            >
              <circle
                cx="8"
                cy="8"
                r="7"
                stroke="currentColor"
                strokeWidth="1.5"
              />
              <path
                d="M8 5v3M8 10.5v.5"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
            <p className="text-caption font-medium text-fault-700">
              All lanes occupied at that time slot. Add more lanes to schedule
              this job.
            </p>
          </div>
          <button
            type="button"
            onClick={onUpgradeClick}
            className="ml-4 flex-shrink-0 rounded-md bg-fault-600 px-3 py-1.5 text-caption font-semibold text-white hover:bg-fault-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fault-600 focus-visible:ring-offset-2 transition-colors"
          >
            Add more lanes
          </button>
        </div>
      )}
    </div>
  );
}
