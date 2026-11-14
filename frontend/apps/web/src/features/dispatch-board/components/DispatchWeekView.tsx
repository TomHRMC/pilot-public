/**
 * DispatchWeekView — Tech-as-column × Day-as-row week grid with @dnd-kit DnD
 *
 * Location: apps/web/src/features/dispatch-board/components/DispatchWeekView.tsx
 *
 * FE-B30: New week view replacing MultiDayGrid.
 * - Grid: rows = days (Mon–Fri 5-day or Mon–Sun 7-day), columns = techs
 * - Jobs in each cell stack vertically (flex column)
 * - @dnd-kit DnD: drag job card between cells → PATCH /api/v1/jobs/{id}
 * - Capacity exceeded (4+ jobs): blocks drop + shows fault chip
 * - Context menu on right-click: "View Job" + "Job Properties"
 * - Mobile fallback: "Week view is available on desktop" with Day button
 *
 * Per batch-fe-b30-react-engr-prompt.md §STEP 3
 * Per dev-docs/architecture-design/batch-designs/batch-ui-ds-b1-design-spec.md §Surface 2
 */

"use client";

import React, { useState, useCallback, useEffect, useRef } from "react";
import Image from "next/image";
import {
  DndContext,
  useDraggable,
  useDroppable,
  DragOverlay,
  useSensor,
  useSensors,
  PointerSensor,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { useQueryClient } from "@tanstack/react-query";
import type { DispatchBoardJob, DispatchBoardTech } from "../types-stub";
import type { DispatchViewTab } from "../store";

// ─── Constants ─────────────────────────────────────────────────────────────────

/** Max jobs in a cell before "capacity exceeded" state triggers */
const CAPACITY_LIMIT = 4;

// ─── Types ─────────────────────────────────────────────────────────────────────

export interface DispatchWeekViewProps {
  /** Active date in the current week (any day works — Monday is computed internally) */
  weekStartDate: string;
  /** 5 (Mon–Fri) or 7 (Mon–Sun) */
  daysToShow: 5 | 7;
  /** All technicians to show as columns */
  techs: DispatchBoardTech[];
  /** All jobs in the week range */
  jobs: DispatchBoardJob[];
  /** Called when a job is dropped — fires PATCH then invalidates query */
  onJobDrop: (
    jobId: string,
    newTechId: string,
    newDate: string,
    newStartTime: Date,
  ) => Promise<void>;
  /** Called when user clicks a job to open the properties panel */
  onJobClick: (job: DispatchBoardJob) => void;
  /** Called when user clicks "View Today" on mobile or drills from week day */
  onNavigateToDate: (dateStr: string) => void;
  /** Called when user switches away from week view */
  onViewTabChange?: (tab: DispatchViewTab) => void;
}

interface DragData {
  jobId: string;
  job: DispatchBoardJob;
}

interface DropData {
  techId: string;
  dateStr: string;
}

interface ContextMenuState {
  x: number;
  y: number;
  job: DispatchBoardJob;
}

// ─── Layout constants ──────────────────────────────────────────────────────────
// These pixel values drive dynamic inline styles for the grid table layout.
// They cannot be expressed as static Tailwind classes because they are used in
// style={{ minWidth: `${N}px` }} for table column sizing.

/** Min width (px) for each tech column in the week grid — on 4px grid (160 = 10rem) */
const COL_WIDTH_PX = 160;
/** Min width (px) for the sticky row header column — on 4px grid (96 = 6rem) */
const ROW_HEADER_WIDTH_PX = 96;

// ─── Date helpers ───────────────────────────────────────────────────────────────

/** Get the Monday (YYYY-MM-DD) for the week containing dateStr */
function getMondayOf(dateStr: string): string {
  const d = new Date(dateStr + "T12:00:00");
  const day = d.getDay(); // 0=Sun, 1=Mon...
  const diff = (day + 6) % 7;
  d.setDate(d.getDate() - diff);
  return d.toISOString().slice(0, 10);
}

/** Get N dates starting from mondayStr */
function getWeekDates(mondayStr: string, daysToShow: 5 | 7): string[] {
  return Array.from({ length: daysToShow }, (_, i) => {
    const d = new Date(mondayStr + "T12:00:00");
    d.setDate(d.getDate() + i);
    return d.toISOString().slice(0, 10);
  });
}

/** Format ISO time as "8:00 AM" */
function formatTime(isoStr: string): string {
  const d = new Date(isoStr);
  return d.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

// ─── WeekJobCard — individual job card in a week cell ────────────────────────

interface WeekJobCardProps {
  job: DispatchBoardJob;
  tech: DispatchBoardTech | null;
  onContextMenu: (e: React.MouseEvent, job: DispatchBoardJob) => void;
  onClick: (job: DispatchBoardJob) => void;
}

function WeekJobCard({ job, tech, onContextMenu, onClick }: WeekJobCardProps) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `job-${job.id}`,
    data: { jobId: job.id, job } satisfies DragData,
  });

  // display_color from API is the one legitimate inline style use per types-stub.ts §display_color.
  // When null, fall back via CSS custom property so no hex literal appears in source.
  const borderColor = tech?.display_color ?? "var(--color-neutral-400)";

  return (
    <div
      ref={setNodeRef}
      {...attributes}
      {...listeners}
      role="button"
      tabIndex={0}
      aria-label={`Job: ${job.title}`}
      onClick={(e) => {
        e.stopPropagation();
        onClick(job);
      }}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.stopPropagation();
          onClick(job);
        }
      }}
      onContextMenu={(e) => {
        e.preventDefault();
        onContextMenu(e, job);
      }}
      className={[
        "flex flex-col rounded border bg-white shadow-sm cursor-grab select-none overflow-hidden",
        "text-caption hover:shadow transition-all",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600",
        isDragging ? "opacity-30" : "opacity-100",
      ].join(" ")}
      style={{
        borderLeftWidth: 3,
        borderLeftColor: borderColor,
      }}
    >
      <div className="px-2 py-1">
        {(job.scheduled_start_at || job.scheduled_end_at) && (
          <p className="text-caption text-neutral-500 font-medium mb-0.5 leading-tight">
            {job.scheduled_start_at ? formatTime(job.scheduled_start_at) : "?"}
            {job.scheduled_end_at
              ? ` – ${formatTime(job.scheduled_end_at)}`
              : ""}
          </p>
        )}
        <p className="text-caption font-semibold text-neutral-900 leading-tight truncate">
          {job.title}
        </p>
        {job.customer_name && (
          <p className="text-caption text-neutral-500 truncate">
            {job.customer_name}
          </p>
        )}
      </div>
    </div>
  );
}

// ─── WeekCommitmentChip — read-only commitment card for non-primary techs ────
// Per DISPATCH-B1.25 §H: muted style, dashed border, cursor-default, no drag.

interface WeekCommitmentChipProps {
  job: DispatchBoardJob;
  onContextMenu: (e: React.MouseEvent, job: DispatchBoardJob) => void;
  onClick: (job: DispatchBoardJob) => void;
}

function WeekCommitmentChip({
  job,
  onContextMenu,
  onClick,
}: WeekCommitmentChipProps) {
  // Capitalize the role string for the badge label: "helper" → "Helper"
  const roleLabel = job.assignment_role
    ? job.assignment_role.charAt(0).toUpperCase() + job.assignment_role.slice(1)
    : "Helper";

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`Commitment (${roleLabel}): ${job.title}`}
      onClick={(e) => {
        e.stopPropagation();
        onClick(job);
      }}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.stopPropagation();
          onClick(job);
        }
      }}
      onContextMenu={(e) => {
        e.preventDefault();
        onContextMenu(e, job);
      }}
      // Muted: dashed border, lighter background, no grab cursor (read-only)
      className={[
        "flex flex-col rounded border border-dashed border-neutral-300",
        "bg-neutral-50 cursor-default select-none overflow-hidden",
        "text-caption transition-all",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neutral-400",
        "hover:bg-neutral-100",
      ].join(" ")}
    >
      <div className="px-2 py-1">
        {(job.scheduled_start_at || job.scheduled_end_at) && (
          <p className="text-caption text-neutral-400 font-medium mb-0.5 leading-tight">
            {job.scheduled_start_at ? formatTime(job.scheduled_start_at) : "?"}
            {job.scheduled_end_at
              ? ` – ${formatTime(job.scheduled_end_at)}`
              : ""}
          </p>
        )}
        <div className="flex items-center justify-between gap-1">
          <p className="text-caption font-medium text-neutral-600 leading-tight truncate flex-1">
            {job.title}
          </p>
          {/* Role badge — renders whatever role string the API returns */}
          <span className="flex-shrink-0 text-caption bg-neutral-100 text-neutral-500 rounded-full px-1.5 py-0 leading-tight font-normal border border-neutral-200">
            {roleLabel}
          </span>
        </div>
        {job.customer_name && (
          <p className="text-caption text-neutral-400 truncate">
            {job.customer_name}
          </p>
        )}
      </div>
    </div>
  );
}

// ─── WeekCell — droppable cell (tech × day) ────────────────────────────────

interface WeekCellProps {
  techId: string;
  dateStr: string;
  jobs: DispatchBoardJob[];
  /** DISPATCH-B1.25: non-primary commitment jobs for this tech on this day */
  commitments: DispatchBoardJob[];
  tech: DispatchBoardTech | null;
  isActiveDragOver: boolean;
  onContextMenu: (e: React.MouseEvent, job: DispatchBoardJob) => void;
  onJobClick: (job: DispatchBoardJob) => void;
}

function WeekCell({
  techId,
  dateStr,
  jobs,
  commitments,
  tech,
  isActiveDragOver,
  onContextMenu,
  onJobClick,
}: WeekCellProps) {
  const dropId = `cell-${techId}-${dateStr}`;
  const { setNodeRef, isOver } = useDroppable({
    id: dropId,
    data: { techId, dateStr } satisfies DropData,
  });

  const isOverCapacity = jobs.length >= CAPACITY_LIMIT;
  const showOverCapacity = isActiveDragOver && isOver && isOverCapacity;
  const showDropTarget = isActiveDragOver && isOver && !isOverCapacity;

  const sortedJobs = [...jobs].sort((a, b) =>
    a.scheduled_start_at.localeCompare(b.scheduled_start_at),
  );
  const sortedCommitments = [...commitments].sort((a, b) =>
    a.scheduled_start_at.localeCompare(b.scheduled_start_at),
  );

  const isEmpty = sortedJobs.length === 0 && sortedCommitments.length === 0;

  return (
    <div
      ref={setNodeRef}
      className={[
        "relative min-h-[80px] p-1.5 flex flex-col gap-1 border-r border-b border-neutral-200",
        "transition-colors",
        isEmpty
          ? "border border-dashed border-neutral-200 rounded bg-neutral-50/50"
          : "",
        showDropTarget ? "bg-brand-50/40" : "",
        showOverCapacity ? "bg-fault-50/40 border-fault-200" : "",
      ].join(" ")}
    >
      {/* Capacity exceeded chip */}
      {showOverCapacity && (
        <div className="absolute top-1 right-1 bg-fault-100 text-fault-700 text-caption rounded-full px-2 py-0.5 font-medium z-10 pointer-events-none">
          Capacity exceeded
        </div>
      )}

      {/* Primary job cards — draggable */}
      {sortedJobs.map((job) => (
        <WeekJobCard
          key={job.id}
          job={job}
          tech={tech}
          onContextMenu={onContextMenu}
          onClick={onJobClick}
        />
      ))}

      {/* Commitment chips — read-only (DISPATCH-B1.25) */}
      {sortedCommitments.map((job) => (
        <WeekCommitmentChip
          key={`commitment-${job.id}`}
          job={job}
          onContextMenu={onContextMenu}
          onClick={onJobClick}
        />
      ))}
    </div>
  );
}

// ─── TechAvatar — initials avatar for tech column header ───────────────────

function TechAvatar({ tech }: { tech: DispatchBoardTech }) {
  const initials = tech.name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  // API-driven color — legitimate inline style per types-stub.ts §display_color
  const bg = tech.display_color ?? "var(--color-neutral-400)";

  if (tech.avatar_url) {
    return (
      <Image
        src={tech.avatar_url}
        alt={tech.name}
        width={32}
        height={32}
        className="w-8 h-8 rounded-full object-cover flex-shrink-0"
      />
    );
  }

  return (
    <div
      className="w-8 h-8 rounded-full flex items-center justify-center text-caption font-bold text-white flex-shrink-0"
      style={{ backgroundColor: bg }}
      aria-hidden="true"
    >
      {initials}
    </div>
  );
}

// ─── ContextMenu ─────────────────────────────────────────────────────────────

interface ContextMenuProps {
  state: ContextMenuState;
  onClose: () => void;
  onViewJob: (job: DispatchBoardJob) => void;
  onJobProperties: (job: DispatchBoardJob) => void;
}

function ContextMenu({
  state,
  onClose,
  onViewJob,
  onJobProperties,
}: ContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [onClose]);

  return (
    <div
      ref={menuRef}
      role="menu"
      style={{ position: "fixed", top: state.y, left: state.x }}
      className="bg-white border border-neutral-200 shadow-lg rounded-md py-1 z-50 min-w-40"
    >
      <button
        role="menuitem"
        type="button"
        className="w-full text-left px-3 py-2 text-body text-neutral-700 hover:bg-neutral-50 focus:outline-none focus-visible:bg-neutral-100"
        onClick={() => {
          onViewJob(state.job);
          onClose();
        }}
      >
        View Job
      </button>
      <button
        role="menuitem"
        type="button"
        className="w-full text-left px-3 py-2 text-body text-neutral-700 hover:bg-neutral-50 focus:outline-none focus-visible:bg-neutral-100"
        onClick={() => {
          onJobProperties(state.job);
          onClose();
        }}
      >
        Job Properties
      </button>
    </div>
  );
}

// ─── DispatchWeekView ─────────────────────────────────────────────────────────

/**
 * DispatchWeekView
 *
 * Tech-as-column × day-as-row week grid with @dnd-kit DnD.
 * Mobile: shows "Week view is available on desktop" fallback.
 */
export function DispatchWeekView({
  weekStartDate,
  daysToShow,
  techs,
  jobs,
  onJobDrop,
  onJobClick,
  onNavigateToDate,
  onViewTabChange,
}: DispatchWeekViewProps) {
  const queryClient = useQueryClient();
  const [activeDragJob, setActiveDragJob] = useState<DispatchBoardJob | null>(
    null,
  );
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null);

  const mondayStr = getMondayOf(weekStartDate);
  const weekDates = getWeekDates(mondayStr, daysToShow);
  const today = new Date().toISOString().slice(0, 10);

  // ── Sensors — 8px activation distance prevents a click from triggering a drop ──
  // Without this constraint, a plain left-click (pointer-down + up with no movement)
  // on a draggable WeekJobCard registers as a zero-distance drag. Because the card
  // sits inside a useDroppable WeekCell, event.over is non-null and handleDragEnd
  // fires onJobDrop → beginMove → ConflictPreviewPane — making every click feel like
  // a "move". The 8px threshold lets normal clicks pass through to the onClick handler.
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
  );

  // ── Drag handlers ──────────────────────────────────────────────────────────

  const handleDragStart = useCallback((event: DragStartEvent) => {
    const data = event.active.data.current as DragData | undefined;
    setActiveDragJob(data?.job ?? null);
  }, []);

  const handleDragEnd = useCallback(
    async (event: DragEndEvent) => {
      setActiveDragJob(null);

      const { over, active } = event;
      if (!over) return;

      const dragData = active.data.current as DragData | undefined;
      const dropData = over.data.current as DropData | undefined;
      if (!dragData || !dropData) return;

      const job = dragData.job;
      const { techId: newTechId, dateStr: newDateStr } = dropData;

      // Check capacity — count existing jobs in that cell
      const cellJobs = jobs.filter(
        (j) =>
          j.tech_id === newTechId &&
          j.scheduled_start_at.startsWith(newDateStr),
      );
      if (cellJobs.length >= CAPACITY_LIMIT) {
        // Capacity exceeded — block drop
        return;
      }

      // Preserve the job's original time-of-day when moving to a new date.
      // Hardcoding 08:00 was wrong: dragging a 10am–3pm job to a day that already
      // has a 4am–10am job would place it at 8am, causing a false overlap conflict.
      // Extract HH:MM:SS from the existing start time and combine with newDateStr.
      let newStartTime: Date;
      if (job.scheduled_start_at) {
        const origStart = new Date(job.scheduled_start_at);
        const pad = (n: number) => String(n).padStart(2, "0");
        const timeOfDay = `T${pad(origStart.getUTCHours())}:${pad(origStart.getUTCMinutes())}:${pad(origStart.getUTCSeconds())}.000Z`;
        newStartTime = new Date(`${newDateStr}${timeOfDay}`);
      } else {
        // Fallback for jobs with no start time — use 08:00
        newStartTime = new Date(`${newDateStr}T08:00:00.000Z`);
      }

      try {
        await onJobDrop(job.id, newTechId, newDateStr, newStartTime);
        void queryClient.invalidateQueries({ queryKey: ["dispatchBoard"] });
      } catch {
        // Error handled by caller
      }
    },
    [jobs, onJobDrop, queryClient],
  );

  // ── Context menu handlers ─────────────────────────────────────────────────

  const handleContextMenu = useCallback(
    (e: React.MouseEvent, job: DispatchBoardJob) => {
      e.preventDefault();
      setContextMenu({ x: e.clientX, y: e.clientY, job });
    },
    [],
  );

  const handleCloseContextMenu = useCallback(() => {
    setContextMenu(null);
  }, []);

  const handleViewJob = useCallback((job: DispatchBoardJob) => {
    // Navigate to job detail page
    window.location.href = `/jobs/${job.id}`;
  }, []);

  const handleJobProperties = useCallback(
    (job: DispatchBoardJob) => {
      onJobClick(job);
    },
    [onJobClick],
  );

  return (
    <>
      {/* Desktop week grid */}
      <div className="hidden md:flex flex-col h-full overflow-hidden">
        <DndContext
          sensors={sensors}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          {/* Scrollable grid wrapper */}
          <div className="flex-1 overflow-auto">
            <table
              className="border-collapse w-full"
              style={{
                minWidth: ROW_HEADER_WIDTH_PX + techs.length * COL_WIDTH_PX,
              }}
            >
              <thead>
                <tr>
                  {/* Sticky top-left corner — w-24 = 6rem = 96px */}
                  <th
                    scope="col"
                    className="sticky left-0 z-20 bg-white border-r border-b border-neutral-200 min-w-24 w-24 px-2 py-2"
                    aria-label="Day"
                  />
                  {/* Tech column headers — min-w-40 = 10rem = 160px */}
                  {techs.map((tech) => (
                    <th
                      key={tech.id}
                      scope="col"
                      className="border-r border-b border-neutral-200 min-w-40 px-3 py-2 bg-white"
                    >
                      <div className="flex flex-col items-center gap-1">
                        <TechAvatar tech={tech} />
                        {/* max-w-xs = 20rem — clamps name without arbitrary px */}
                        <span className="text-caption font-semibold text-neutral-800 text-center truncate max-w-xs">
                          {tech.name}
                        </span>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {weekDates.map((dateStr) => {
                  const isToday = dateStr === today;
                  return (
                    <tr key={dateStr}>
                      {/* Sticky day row header — w-24 = 6rem = 96px */}
                      <th
                        scope="row"
                        className={[
                          "sticky left-0 z-10 border-r border-b border-neutral-200 min-w-24 w-24 px-2 py-2 text-left",
                          isToday ? "bg-brand-50" : "bg-white",
                        ].join(" ")}
                      >
                        <div className="flex flex-col gap-0.5">
                          <span
                            className={[
                              "text-caption font-semibold uppercase tracking-wide",
                              isToday ? "text-brand-600" : "text-neutral-500",
                            ].join(" ")}
                          >
                            {new Date(dateStr + "T12:00:00").toLocaleDateString(
                              "en-US",
                              { weekday: "short" },
                            )}
                          </span>
                          <span
                            className={[
                              "text-body font-bold",
                              isToday ? "text-brand-700" : "text-neutral-800",
                            ].join(" ")}
                          >
                            {new Date(dateStr + "T12:00:00").toLocaleDateString(
                              "en-US",
                              { month: "short", day: "numeric" },
                            )}
                          </span>
                        </div>
                      </th>

                      {/* Tech cells */}
                      {techs.map((tech) => {
                        const cellJobs = jobs
                          .filter(
                            (j) =>
                              j.tech_id === tech.id &&
                              j.scheduled_start_at.startsWith(dateStr),
                          )
                          .sort((a, b) =>
                            a.scheduled_start_at.localeCompare(
                              b.scheduled_start_at,
                            ),
                          );

                        // DISPATCH-B1.25: Commitment chips for this tech's non-primary jobs on this day.
                        // Filtered from tech.commitments (NOT from jobs[] — must not double-count).
                        const cellCommitments = (tech.commitments ?? []).filter(
                          (j) =>
                            j.scheduled_start_at &&
                            j.scheduled_start_at.startsWith(dateStr),
                        );

                        return (
                          <td
                            key={tech.id}
                            className="border-r border-b border-neutral-200 p-0 align-top"
                          >
                            <WeekCell
                              techId={tech.id}
                              dateStr={dateStr}
                              jobs={cellJobs}
                              commitments={cellCommitments}
                              tech={tech}
                              isActiveDragOver={activeDragJob !== null}
                              onContextMenu={handleContextMenu}
                              onJobClick={onJobClick}
                            />
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Drag overlay ghost card */}
          <DragOverlay>
            {activeDragJob ? (
              <div className="border border-brand-400 rounded px-3 py-2 bg-white shadow-lg text-caption font-medium text-brand-700 opacity-90 pointer-events-none">
                {activeDragJob.title}
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      </div>

      {/* Mobile fallback */}
      <div className="md:hidden flex flex-col items-center justify-center py-12 text-neutral-600 text-sm text-center px-4">
        <p>Week view is available on desktop.</p>
        <button
          type="button"
          className="mt-3 px-4 py-2 border border-brand-200 bg-brand-50 text-brand-700 text-sm font-medium rounded-md hover:bg-brand-100"
          onClick={() => {
            const todayStr = new Date().toISOString().slice(0, 10);
            if (onViewTabChange) onViewTabChange("day");
            onNavigateToDate(todayStr);
          }}
        >
          View Today
        </button>
      </div>

      {/* Context menu */}
      {contextMenu && (
        <ContextMenu
          state={contextMenu}
          onClose={handleCloseContextMenu}
          onViewJob={handleViewJob}
          onJobProperties={handleJobProperties}
        />
      )}
    </>
  );
}
