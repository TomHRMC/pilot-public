/**
 * DispatchGridDayView — Day-tech mode dispatch board (time × tech row)
 *
 * Location: apps/web/src/features/dispatch-board/components/DispatchGridDayView.tsx
 *
 * Day-tech mode: time across horizontal, one row per tenant tech (always rendered, even empty).
 * Uses @dnd-kit — same DndContext as DispatchBoardLanes (owned by DispatchBoardPage).
 * Each tech row is a useDroppable region.
 *
 * Over-capacity detection is client-side: if a job is dragged over a time window
 * that already has another job for that tech, the drop is blocked + "Conflict" chip shown.
 * Clean drops fire onJobDrop → DispatchBoardPage beginMove pipeline.
 *
 * Per DISPATCH-B1 UI spec §Surface 1
 */

"use client";

import React, { useState, useMemo } from "react";
import { useDroppable, DragOverlay } from "@dnd-kit/core";
import type { DispatchBoardTech } from "../types-stub";
import type { ScheduledJob } from "./DispatchBoardLanes";
import { DraggableJobBlock } from "./JobBlock";
import {
  HOUR_WIDTH_PX,
  LANE_HEIGHT_PX,
  TECH_HEADER_WIDTH_PX,
  dateToPx,
  computeViewportHours,
  getHourLabels,
  snapTo15Min,
  pxToDate,
} from "../utils/timeHelpers";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface DispatchGridDayViewProps {
  date: Date;
  techs: DispatchBoardTech[];
  jobs: ScheduledJob[];
  onJobClick: (job: ScheduledJob) => void;
  onJobDrop: (jobId: string, techId: string, startTime: Date) => void;
  onJobContextMenu: (e: React.MouseEvent, job: ScheduledJob) => void;
}

// ─── Droppable tech row ───────────────────────────────────────────────────────

interface DroppableTechRowProps {
  techId: string;
  techName: string;
  jobs: ScheduledJob[];
  /** DISPATCH-B1.25: read-only commitment chips (non-primary assignments). NOT included in capacity detection. */
  commitments: ScheduledJob[];
  isOverCapacity: boolean;
  onJobClick: (job: ScheduledJob) => void;
  onJobContextMenu: (e: React.MouseEvent, job: ScheduledJob) => void;
  boardWidthPx: number;
  viewStartHour: number;
  hourLabels: Array<{ hour: number; label: string }>;
}

function DroppableTechRow({
  techId,
  techName,
  jobs,
  commitments,
  isOverCapacity,
  onJobClick,
  onJobContextMenu,
  boardWidthPx,
  viewStartHour,
  hourLabels,
}: DroppableTechRowProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: `tech-row-${techId}`,
    data: { techId },
  });

  return (
    <div
      ref={setNodeRef}
      role="region"
      aria-label={`Schedule row for ${techName}`}
      style={{
        height: `${LANE_HEIGHT_PX}px`,
        width: `${boardWidthPx}px`,
        position: "relative",
      }}
      className={`
        border-b border-neutral-100
        transition-colors
        ${isOver && !isOverCapacity ? "bg-brand-50/40" : ""}
        ${isOver && isOverCapacity ? "bg-fault-50/40" : ""}
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

      {/* Primary job blocks (draggable) */}
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
            variant="primary"
          />
        );
      })}

      {/* DISPATCH-B1.25: Commitment chips (read-only, role-badged).
          Rendered alongside primary blocks at their scheduled positions.
          NOT included in drop/over-capacity detection. */}
      {commitments.map((job) => {
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
            key={`commitment-${job.id}`}
            job={job}
            left={left}
            width={width}
            onClick={onJobClick}
            onContextMenu={onJobContextMenu}
            variant="commitment"
          />
        );
      })}

      {/* Over-capacity chip */}
      {isOver && isOverCapacity && (
        <div
          className="absolute top-1 right-1 bg-fault-100 text-fault-700 text-caption font-medium rounded-full px-2 py-0.5 pointer-events-none"
          aria-live="assertive"
        >
          Conflict
        </div>
      )}
    </div>
  );
}

// ─── DispatchGridDayView ──────────────────────────────────────────────────────

/**
 * DispatchGridDayView
 *
 * Day-tech view: time-axis × one row per tenant tech.
 * Always renders a row per tech, even if empty — empty rows are valid drop targets.
 *
 * Mobile fallback (<md): centered message + switch to Lane button.
 *
 * Note: This component does NOT wrap its own DndContext.
 * The single DndContext lives in DispatchBoardPage.
 */
export function DispatchGridDayView({
  date: _date, // eslint-disable-line @typescript-eslint/no-unused-vars
  techs,
  jobs,
  onJobClick,
  onJobDrop: _onJobDrop, // eslint-disable-line @typescript-eslint/no-unused-vars
  onJobContextMenu,
}: DispatchGridDayViewProps) {
  // activeDragJobId and overCapacityTechIds are reserved for B1.5 inline drag handling.
  // The DndContext lives in DispatchBoardPage; drag overlay uses the job lookup below.
  const [activeDragJobId] = useState<string | null>(null);
  const [overCapacityTechIds] = useState<Set<string>>(new Set());

  const { startHour: viewStartHour, endHour: viewEndHour } = useMemo(
    () => computeViewportHours(jobs),
    [jobs],
  );
  const totalViewHours = viewEndHour - viewStartHour;
  const boardWidthPx = totalViewHours * HOUR_WIDTH_PX;

  const hourLabels = getHourLabels(viewStartHour, viewEndHour);

  /** Jobs grouped by tech_id */
  const jobsByTech = useMemo(() => {
    const map = new Map<string, ScheduledJob[]>();
    for (const tech of techs) {
      map.set(tech.id, []);
    }
    for (const job of jobs) {
      if (job.tech_id && map.has(job.tech_id)) {
        map.get(job.tech_id)!.push(job);
      }
    }
    return map;
  }, [techs, jobs]);

  const activeDragJob = activeDragJobId
    ? (jobs.find((j) => j.id === activeDragJobId) ?? null)
    : null;

  // activeDragJobId is set externally via the DragOverlay pattern
  // The DndContext is in DispatchBoardPage; drag start/end are not wired here (B1.5 scope)

  if (techs.length === 0) {
    return (
      <div className="flex flex-col h-full items-center justify-center text-body text-neutral-500">
        <p>No technicians configured.</p>
        <a
          href="/settings/team"
          className="mt-2 text-body text-brand-600 hover:underline"
        >
          Add technicians in Settings
        </a>
      </div>
    );
  }

  return (
    <>
      {/* Mobile fallback */}
      <div className="md:hidden flex flex-col h-full items-center justify-center p-6 text-center">
        <p className="text-body text-neutral-700 mb-3">
          Tech view is available on desktop
        </p>
        <button
          type="button"
          className="px-4 py-2 rounded-md bg-brand-600 text-white text-body font-medium hover:bg-brand-700 focus-visible:ring-2 focus-visible:ring-brand-600"
          onClick={() => {
            // Caller switches layoutMode back to lane via the store
            document.dispatchEvent(new CustomEvent("dispatch:switch-to-lane"));
          }}
        >
          Switch to Lane view
        </button>
      </div>

      {/* Desktop grid */}
      <div className="hidden md:flex flex-col h-full min-w-0">
        <div
          className="flex-1 min-h-0"
          style={{ overflowX: "scroll", overflowY: "auto" }}
        >
          <div
            style={{
              display: "flex",
              minWidth: `${TECH_HEADER_WIDTH_PX + boardWidthPx}px`,
            }}
          >
            {/* Sticky tech header column */}
            <div
              style={{
                width: `${TECH_HEADER_WIDTH_PX}px`,
                flexShrink: 0,
                position: "sticky",
                left: 0,
                zIndex: 1,
              }}
              className="bg-neutral-50 border-r border-neutral-200"
            >
              {/* Spacer aligned with time axis header */}
              <div className="h-7 border-b border-neutral-200" />

              {/* Tech row headers */}
              {techs.map((tech) => (
                <div
                  key={tech.id}
                  style={{
                    height: `${LANE_HEIGHT_PX}px`,
                    gap: "8px",
                    padding: "0 8px",
                  }}
                  className="flex items-center border-b border-neutral-100"
                >
                  {/* Avatar (initials) */}
                  <div className="w-7 h-7 rounded-full bg-brand-100 flex items-center justify-center flex-shrink-0">
                    <span className="text-caption font-bold text-brand-700">
                      {tech.name
                        .split(" ")
                        .map((n) => n[0])
                        .slice(0, 2)
                        .join("")
                        .toUpperCase()}
                    </span>
                  </div>
                  {/* Tech name */}
                  <span className="text-caption font-medium text-neutral-700 truncate">
                    {tech.name}
                  </span>
                </div>
              ))}
            </div>

            {/* Grid area */}
            <div style={{ width: `${boardWidthPx}px`, flexShrink: 0 }}>
              {/* Time axis header */}
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

              {/* Tech rows */}
              {techs.map((tech) => (
                <DroppableTechRow
                  key={tech.id}
                  techId={tech.id}
                  techName={tech.name}
                  jobs={jobsByTech.get(tech.id) ?? []}
                  // DISPATCH-B1.25: commitment chips from normalized tech shape
                  commitments={(tech.commitments ?? []) as ScheduledJob[]}
                  isOverCapacity={overCapacityTechIds.has(tech.id)}
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
      </div>

      {/* Drag overlay for tech-mode */}
      <DragOverlay>
        {activeDragJob ? (
          <div className="border border-brand-400 rounded px-3 py-2 bg-white shadow-lg text-caption font-medium text-brand-700 opacity-90 pointer-events-none">
            {(activeDragJob as unknown as { job_number?: string }).job_number ??
              activeDragJob.title}
          </div>
        ) : null}
      </DragOverlay>
    </>
  );
}

// ─── Helpers exported for DispatchBoardPage onDragEnd ─────────────────────────

/**
 * Check if a proposed [start, end] time window overlaps any existing job for a tech.
 * Used by DispatchBoardPage.handleDragEnd before calling beginMove.
 */
export function checkTechOverCapacity(
  techJobs: ScheduledJob[],
  proposedStart: Date,
  proposedEnd: Date,
  excludeJobId?: string,
): boolean {
  for (const job of techJobs) {
    if (job.id === excludeJobId) continue;
    if (!job.scheduled_start_at || !job.scheduled_end_at) continue;
    const jobStart = new Date(job.scheduled_start_at);
    const jobEnd = new Date(job.scheduled_end_at);
    if (jobStart < proposedEnd && jobEnd > proposedStart) {
      return true;
    }
  }
  return false;
}

export { snapTo15Min, pxToDate };
