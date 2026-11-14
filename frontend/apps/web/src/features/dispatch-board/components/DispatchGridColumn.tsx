/**
 * DispatchGridColumn — Single tech column with drop target
 *
 * Location: apps/web/src/features/dispatch-board/components/DispatchGridColumn.tsx
 *
 * Renders job blocks as draggable items.
 * Drop target for inbound job moves.
 * Calls check-conflicts then useMoveJob on drop.
 *
 * Per batch-fe-b4-design.md §A.2.1
 */

"use client";

import React, { useCallback } from "react";
import { useDrop } from "react-dnd";
import type { DispatchBoardJob, DispatchBoardTech } from "../types-stub";
import {
  JobBlock,
  JOB_BLOCK_DND_TYPE,
  type JobBlockDragItem,
} from "./JobBlock";
import { TechColumnHeader } from "./TechColumnHeader";

const GRID_START_HOUR = 6; // 6 AM
const GRID_END_HOUR = 19; // 7 PM
const GRID_HOURS = GRID_END_HOUR - GRID_START_HOUR;
const HOUR_HEIGHT_PX = 60;
const GRID_HEIGHT_PX = GRID_HOURS * HOUR_HEIGHT_PX;
const COLUMN_MIN_WIDTH_PX = 140;

/** Convert ISO string to pixels from grid top */
function isoToTopPx(isoStr: string | null): number {
  if (!isoStr) return 0;
  const date = new Date(isoStr);
  const minutes = date.getHours() * 60 + date.getMinutes();
  const startMinutes = GRID_START_HOUR * 60;
  return Math.max(0, ((minutes - startMinutes) / 60) * HOUR_HEIGHT_PX);
}

function isoToHeightPx(startIso: string | null, endIso: string | null): number {
  if (!startIso || !endIso) return HOUR_HEIGHT_PX;
  const startMs = new Date(startIso).getTime();
  const endMs = new Date(endIso).getTime();
  const durationMinutes = Math.max(30, (endMs - startMs) / 60000);
  return (durationMinutes / 60) * HOUR_HEIGHT_PX;
}

interface DispatchGridColumnProps {
  tech: DispatchBoardTech | null; // null = Unassigned column
  jobs: DispatchBoardJob[];
  isUnassigned?: boolean;
  /** Optional — omit for read-only columns (multi-day panels) */
  onDrop?: (
    item: JobBlockDragItem,
    targetTechId: string | null,
    dropTopPx: number,
  ) => void;
  onJobSelect: (jobId: string) => void;
}

/** Time labels on Y axis */
function TimeAxis() {
  const hours = Array.from(
    { length: GRID_HOURS + 1 },
    (_, i) => GRID_START_HOUR + i,
  );
  return (
    <div className="absolute inset-0 pointer-events-none">
      {hours.map((h) => (
        <div
          key={h}
          className="absolute left-0 right-0 border-t border-neutral-100"
          style={{ top: `${(h - GRID_START_HOUR) * HOUR_HEIGHT_PX}px` }}
          aria-hidden="true"
        >
          <span className="text-caption text-neutral-400 pl-1">
            {h === 12 ? "12 PM" : h > 12 ? `${h - 12} PM` : `${h} AM`}
          </span>
        </div>
      ))}
    </div>
  );
}

/**
 * DispatchGridColumn
 *
 * Single column for one tech (or the Unassigned column).
 * Acts as a react-dnd drop target. On drop, calls onDrop with the dragged item
 * and the target tech ID so the parent can run conflict-check → move.
 */
export function DispatchGridColumn({
  tech,
  jobs,
  isUnassigned = false,
  onDrop,
  onJobSelect,
}: DispatchGridColumnProps) {
  const [{ isOver, canDrop }, dropRef] = useDrop<
    JobBlockDragItem,
    void,
    { isOver: boolean; canDrop: boolean }
  >({
    accept: JOB_BLOCK_DND_TYPE,
    drop: (item, monitor) => {
      const clientOffset = monitor.getClientOffset();
      const dropElem = document.getElementById(
        `grid-column-${tech?.id ?? "unassigned"}`,
      );
      const dropElemRect = dropElem?.getBoundingClientRect();
      const dropTopPx =
        clientOffset && dropElemRect ? clientOffset.y - dropElemRect.top : 0;
      onDrop?.(item, tech?.id ?? null, dropTopPx);
    },
    collect: (monitor) => ({
      isOver: monitor.isOver(),
      canDrop: monitor.canDrop(),
    }),
  });

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const handleDrop = useCallback(
    (item: JobBlockDragItem, dropTopPx: number) => {
      onDrop?.(item, tech?.id ?? null, dropTopPx);
    },
    [onDrop, tech?.id],
  );

  const techJobs = jobs.filter((j) =>
    isUnassigned ? j.tech_id === null : j.tech_id === tech?.id,
  );

  return (
    <div
      className="flex flex-col flex-shrink-0"
      style={{ minWidth: `${COLUMN_MIN_WIDTH_PX}px` }}
    >
      {/* Column header */}
      {tech ? (
        <TechColumnHeader tech={tech} jobCount={techJobs.length} />
      ) : (
        <div className="flex flex-col items-center gap-1 py-2 px-2 border-b border-neutral-200">
          <div className="w-8 h-8 rounded-full bg-neutral-100 flex items-center justify-center">
            <span className="text-caption text-neutral-400">?</span>
          </div>
          <span className="text-caption font-medium text-neutral-600">
            Unassigned
          </span>
          <span className="text-caption text-neutral-400">
            {techJobs.length} jobs
          </span>
        </div>
      )}

      {/* Grid area — drop target */}
      <div
        ref={dropRef as unknown as React.Ref<HTMLDivElement>}
        id={`grid-column-${tech?.id ?? "unassigned"}`}
        className={[
          "relative border-r border-neutral-100",
          isOver && canDrop ? "bg-brand-50" : "bg-white",
        ].join(" ")}
        style={{ height: `${GRID_HEIGHT_PX}px` }}
        role="gridcell"
        aria-label={`${tech?.name ?? "Unassigned"} column`}
      >
        {/* Time grid lines */}
        <TimeAxis />

        {/* Job blocks */}
        {techJobs.map((job) => {
          // DISPATCH-B1: deprecated component — JobBlock is now DraggableJobBlock (@dnd-kit).
          // Map legacy vertical layout (topPx/heightPx) to horizontal (left/width) for compat.
          // The visual position is wrong in this deprecated view, but click handler works.
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const LegacyJobBlock = JobBlock as any;
          return (
            <LegacyJobBlock
              key={job.id}
              job={job}
              left={isoToTopPx(job.scheduled_start_at)}
              width={isoToHeightPx(
                job.scheduled_start_at,
                job.scheduled_end_at,
              )}
              onClick={(clickedJob: { id: string }) =>
                onJobSelect(clickedJob.id)
              }
            />
          );
        })}

        {/* Drop indicator overlay */}
        {isOver && canDrop && (
          <div
            className="absolute inset-0 border-2 border-brand-400 border-dashed rounded-sm pointer-events-none"
            aria-hidden="true"
          />
        )}
      </div>
    </div>
  );
}

// Export constants for use in parent components
export {
  GRID_START_HOUR,
  GRID_END_HOUR,
  GRID_HOURS,
  HOUR_HEIGHT_PX,
  GRID_HEIGHT_PX,
  COLUMN_MIN_WIDTH_PX,
};
