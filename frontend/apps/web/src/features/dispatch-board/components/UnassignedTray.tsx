/**
 * UnassignedTray — Horizontal strip showing unassigned jobs above the board
 *
 * Location: apps/web/src/features/dispatch-board/components/UnassignedTray.tsx
 *
 * Replaces the bottom UnscheduledJobQueue in DispatchBoardLanes.
 * Always visible — even when empty (shows "Unassigned (0)").
 * Chips are @dnd-kit useDraggable — dragging out-to-board schedules a job
 * via the unified beginMove pipeline in DispatchBoardPage.
 *
 * data-testid="unassigned-tray" is required by the architecture spec §I.
 *
 * Per DISPATCH-B1 UI spec §Surface 2
 */

"use client";

import React from "react";
import { useDraggable } from "@dnd-kit/core";
import type { DispatchBoardJob } from "../types-stub";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface UnassignedTrayProps {
  jobs: DispatchBoardJob[];
  onJobClick: (job: DispatchBoardJob) => void;
  // drag-out handled by shared DndContext in DispatchBoardPage
}

// ─── Chip component ───────────────────────────────────────────────────────────

interface UnassignedChipProps {
  job: DispatchBoardJob;
  onJobClick: (job: DispatchBoardJob) => void;
}

function UnassignedChip({ job, onJobClick }: UnassignedChipProps) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: job.id,
    data: { job, source: "unassigned-tray" },
  });

  // label: prefer job_number (B1 schema) then title
  const primaryLabel =
    (job as unknown as { job_number?: string }).job_number ??
    job.title ??
    job.id;
  const secondaryLabel = job.customer_name ?? "";

  return (
    <div
      ref={setNodeRef}
      {...attributes}
      {...listeners}
      role="button"
      tabIndex={0}
      aria-label={`Unassigned job: ${primaryLabel}`}
      onClick={(e) => {
        e.stopPropagation();
        onJobClick(job);
      }}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.stopPropagation();
          onJobClick(job);
        }
      }}
      className={`
        border border-neutral-300 rounded px-3 py-1.5 bg-white cursor-grab
        text-caption shadow-sm hover:border-brand-400 hover:shadow
        transition-all select-none max-w-[180px] flex-shrink-0
        focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:outline-none
        ${isDragging ? "opacity-30" : "opacity-100"}
      `}
    >
      <span className="text-caption font-medium text-neutral-800 truncate block">
        {primaryLabel}
      </span>
      {secondaryLabel && (
        <span className="text-caption text-neutral-500 truncate block">
          {secondaryLabel}
        </span>
      )}
    </div>
  );
}

// ─── UnassignedTray ───────────────────────────────────────────────────────────

/**
 * UnassignedTray
 *
 * Horizontal strip above the board showing jobs with no primary assignment.
 * Always rendered — even empty (shows "Unassigned (0)" + italic empty message).
 */
export function UnassignedTray({ jobs, onJobClick }: UnassignedTrayProps) {
  return (
    <div
      data-testid="unassigned-tray"
      className="flex items-center gap-2 px-4 py-2 min-h-11 border-b border-neutral-200 bg-neutral-50 flex-wrap"
    >
      {/* Label — always visible */}
      <span className="text-caption font-semibold text-neutral-500 flex-shrink-0 mr-1">
        Unassigned ({jobs.length})
      </span>

      {/* Empty state message */}
      {jobs.length === 0 && (
        <span className="text-caption text-neutral-400 italic">
          No unassigned jobs
        </span>
      )}

      {/* Draggable chips */}
      {jobs.map((job) => (
        <UnassignedChip key={job.id} job={job} onJobClick={onJobClick} />
      ))}
    </div>
  );
}
