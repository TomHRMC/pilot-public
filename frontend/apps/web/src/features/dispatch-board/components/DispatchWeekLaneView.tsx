/**
 * DispatchWeekLaneView — Week-lane grid (days-as-rows × lane-columns)
 *
 * Location: apps/web/src/features/dispatch-board/components/DispatchWeekLaneView.tsx
 *
 * DISPATCH-B1.5 (NEW):
 *   - Grid: rows = days (Mon–Fri 5-day or Mon–Sun 7-day), columns = lanes (L1…L5)
 *   - Lane columns are anonymous schedule slots — no tech identity
 *   - Per-day assignJobsToLanes() populates cells from shared laneHelpers.ts
 *   - DndContext is owned by DispatchBoardPage (NOT internal) — Impl Note 1
 *   - DISPATCH-B1.5: Lane mode — no WeekCommitmentChip. Commitment chips are
 *     tech-mode only (DISPATCH-B1.25). — Impl Note 2
 *   - Registered as JobContextMenu consumer via onJobContextMenu prop — Impl Note
 *   - Mobile fallback: "Week view is available on desktop." with day button
 *
 * Per dispatch-b1.5-ui-design-spec.md §Surface 1
 */

"use client";

import React, { useState, useMemo } from "react";
import { useDraggable, useDroppable, DragOverlay } from "@dnd-kit/core";
import type { DispatchBoardJob } from "../types-stub";
import type { DispatchViewTab } from "../store";
import { assignJobsToLanes } from "../utils/laneHelpers";

// ─── Layout constants ──────────────────────────────────────────────────────────

/** Min width per lane column (px) — matches COL_WIDTH_PX in DispatchWeekView */
const LANE_COL_WIDTH_PX = 160;
/** Min width for the sticky day row header column (px) — matches DispatchWeekView */
const ROW_HEADER_WIDTH_PX = 96;
/** Max stacked job cards in one day×lane cell before drop is blocked */
const CAPACITY_LIMIT = 4;

// ─── Types ─────────────────────────────────────────────────────────────────────

export interface DispatchWeekLaneViewProps {
  /** Any date in the target week — Monday is computed internally */
  weekStartDate: string;
  /** 5 (Mon–Fri) or 7 (Mon–Sun) */
  daysToShow: 5 | 7;
  /** Number of lanes from useScheduleLaneCount — max 5 (Charter cap) */
  laneCount: number;
  /** All jobs in the week range (scheduled + unassigned with dates) */
  jobs: DispatchBoardJob[];
  /**
   * Called when a job card is dropped onto a cell.
   * laneIndex is 0-based. Fires → beginMove unified pipeline in DispatchBoardPage.
   */
  onJobDrop: (
    jobId: string,
    laneIndex: number,
    dateStr: string,
    newStartTime: Date,
  ) => Promise<void>;
  /** Left-click → JobPropertiesPanel */
  onJobClick: (job: DispatchBoardJob) => void;
  /** Right-click → JobContextMenu (shared component, rendered by DispatchBoardPage) */
  onJobContextMenu: (e: React.MouseEvent, job: DispatchBoardJob) => void;
  /** Called when user taps "View Today" on mobile fallback */
  onNavigateToDate: (dateStr: string) => void;
  /** Called when user switches away from week view on mobile fallback */
  onViewTabChange?: (tab: DispatchViewTab) => void;
}

interface DragData {
  jobId: string;
  job: DispatchBoardJob;
}

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

/** YYYY-MM-DD → {weekday, date} display labels */
function getDayLabels(dateStr: string): { weekday: string; date: string } {
  const d = new Date(dateStr + "T12:00:00");
  return {
    weekday: d.toLocaleDateString("en-US", { weekday: "short" }).toUpperCase(),
    date: d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    }),
  };
}

/** Today's date as YYYY-MM-DD (local) */
function getTodayStr(): string {
  const today = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${today.getFullYear()}-${pad(today.getMonth() + 1)}-${pad(today.getDate())}`;
}

// ─── WeekLaneJobCard — Draggable job card inside a lane cell ─────────────────

interface WeekLaneJobCardProps {
  job: DispatchBoardJob;
  onClick: (job: DispatchBoardJob) => void;
  onContextMenu: (e: React.MouseEvent, job: DispatchBoardJob) => void;
}

function WeekLaneJobCard({
  job,
  onClick,
  onContextMenu,
}: WeekLaneJobCardProps) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `job-${job.id}`,
    data: { jobId: job.id, job } satisfies DragData,
  });

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
      // Lane mode: neutral left border — no tech color (lane mode is tech-agnostic).
      // Using inline style (same pattern as WeekJobCard in DispatchWeekView which uses
      // borderLeftWidth/borderLeftColor inline to handle dynamic colors cleanly).
      style={{
        borderLeftWidth: 3,
        borderLeftColor: "var(--color-neutral-300)",
      }}
    >
      <div className="px-2 py-1">
        {/* Time range — shown when scheduled_start_at present */}
        {job.scheduled_start_at && (
          <p className="text-caption text-neutral-500 font-medium mb-0.5 leading-tight">
            {formatTime(job.scheduled_start_at)}
            {job.scheduled_end_at
              ? ` – ${formatTime(job.scheduled_end_at)}`
              : ""}
          </p>
        )}
        {/* Primary label: title ?? job_number (forward-compat) */}
        <p className="text-caption font-semibold text-neutral-900 leading-tight truncate">
          {job.title}
        </p>
        {/* Customer name */}
        {job.customer_name && (
          <p className="text-caption text-neutral-500 truncate">
            {job.customer_name}
          </p>
        )}
      </div>
      {/* DISPATCH-B1.5: Lane mode — no WeekCommitmentChip. Commitment chips
          are tech-mode only (DISPATCH-B1.25). */}
    </div>
  );
}

// ─── WeekLaneCell — Droppable lane×day cell ───────────────────────────────────

interface WeekLaneCellProps {
  laneIndex: number;
  dateStr: string;
  jobs: DispatchBoardJob[];
  dayLabel: string;
  isActiveDrag: boolean;
  onJobDrop: (
    jobId: string,
    laneIndex: number,
    dateStr: string,
    newStartTime: Date,
  ) => void;
  onJobClick: (job: DispatchBoardJob) => void;
  onJobContextMenu: (e: React.MouseEvent, job: DispatchBoardJob) => void;
  dragJob: DispatchBoardJob | null;
}

function WeekLaneCell({
  laneIndex,
  dateStr,
  jobs,
  dayLabel,
  isActiveDrag,
  onJobClick,
  onJobContextMenu,
}: WeekLaneCellProps) {
  const isOverCapacity = jobs.length >= CAPACITY_LIMIT;
  const [showCapacityFlash, setShowCapacityFlash] = useState(false);

  const { setNodeRef, isOver } = useDroppable({
    id: `cell-lane${laneIndex}-${dateStr}`,
    data: { laneIndex, dateStr },
  });

  // Over-capacity chip: derive visibility from drag/capacity state,
  // then schedule a fade-out when the drag leaves the cell.
  // Using a ref to avoid synchronous setState in effect body (lint rule).
  const capacityTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );
  React.useEffect(() => {
    if (capacityTimerRef.current) {
      clearTimeout(capacityTimerRef.current);
      capacityTimerRef.current = null;
    }
    if (isOver && isOverCapacity && isActiveDrag) {
      // Defer setState to avoid synchronous setState-in-effect
      capacityTimerRef.current = setTimeout(() => {
        setShowCapacityFlash(true);
        // Auto-hide after 1.5s when drag leaves
        capacityTimerRef.current = setTimeout(
          () => setShowCapacityFlash(false),
          1500,
        );
      }, 0);
    } else if (!isOver) {
      capacityTimerRef.current = setTimeout(
        () => setShowCapacityFlash(false),
        500,
      );
    }
    return () => {
      if (capacityTimerRef.current) clearTimeout(capacityTimerRef.current);
    };
  }, [isOver, isOverCapacity, isActiveDrag]);

  const isEmpty = jobs.length === 0;
  const isHovered = isOver && isActiveDrag;
  const isHoveredFull = isHovered && isOverCapacity;
  const isHoveredFree = isHovered && !isOverCapacity;

  return (
    <td
      ref={setNodeRef}
      role="gridcell"
      aria-label={`Lane ${laneIndex + 1}, ${dayLabel}`}
      className={[
        "min-h-[80px] p-1.5 align-top relative transition-colors",
        isEmpty
          ? "border border-dashed border-neutral-200 rounded bg-neutral-50/50"
          : "border-r border-b border-neutral-200",
        isHoveredFull ? "bg-fault-50/40 border-fault-200" : "",
        isHoveredFree ? "bg-brand-50/40" : "",
      ].join(" ")}
    >
      <div className="flex flex-col gap-1">
        {/* Sort jobs by start time ascending */}
        {[...jobs]
          .sort((a, b) => {
            if (!a.scheduled_start_at) return 1;
            if (!b.scheduled_start_at) return -1;
            return (
              new Date(a.scheduled_start_at).getTime() -
              new Date(b.scheduled_start_at).getTime()
            );
          })
          .map((job) => (
            <WeekLaneJobCard
              key={job.id}
              job={job}
              onClick={onJobClick}
              onContextMenu={onJobContextMenu}
            />
          ))}
      </div>

      {/* Over-capacity chip */}
      {(isHoveredFull || showCapacityFlash) && (
        <div
          className={[
            "absolute top-1 right-1 bg-fault-100 text-fault-700 text-caption",
            "rounded-full px-2 py-0.5 font-medium z-10 pointer-events-none",
            showCapacityFlash && !isHoveredFull
              ? "transition-opacity duration-500 opacity-0"
              : "opacity-100",
          ].join(" ")}
        >
          Capacity exceeded
        </div>
      )}
    </td>
  );
}

// ─── DispatchWeekLaneView ─────────────────────────────────────────────────────

/**
 * DispatchWeekLaneView
 *
 * Week grid with days-as-rows × lane-columns. Mounted by DispatchBoardPage
 * when viewTab === "week" && layoutMode === "lane".
 *
 * DndContext is owned by DispatchBoardPage — this component registers
 * useDroppable / useDraggable inside that context. NO internal DndContext.
 * (Impl Note 1)
 *
 * DISPATCH-B1.5: Lane mode — no WeekCommitmentChip. (Impl Note 2)
 */
export function DispatchWeekLaneView({
  weekStartDate,
  daysToShow,
  laneCount,
  jobs,
  onJobDrop,
  onJobClick,
  onJobContextMenu,
  onNavigateToDate,
  onViewTabChange,
}: DispatchWeekLaneViewProps) {
  const todayStr = getTodayStr();
  const mondayStr = getMondayOf(weekStartDate);
  const weekDates = getWeekDates(mondayStr, daysToShow);

  // Track active drag job for DragOverlay ghost card
  const [activeDragJob, setActiveDragJob] = useState<DispatchBoardJob | null>(
    null,
  );

  // ── Per-day lane assignment ────────────────────────────────────────────────
  // For each dateStr: filter jobs to that day, run assignJobsToLanes.
  // Result: jobsByDayAndLane[dateStr][laneIndex] = DispatchBoardJob[]
  const jobsByDayAndLane = useMemo<Record<string, DispatchBoardJob[][]>>(() => {
    const result: Record<string, DispatchBoardJob[][]> = {};
    for (const dateStr of weekDates) {
      const dayJobs = jobs.filter((j) =>
        j.scheduled_start_at?.startsWith(dateStr),
      );
      const assignment = assignJobsToLanes(dayJobs, laneCount);
      // Build [laneIndex] → jobs array
      const lanes: DispatchBoardJob[][] = Array.from(
        { length: laneCount },
        () => [],
      );
      for (const job of dayJobs) {
        if (!job.scheduled_start_at || job.scheduled_start_at === "null")
          continue;
        const lane = assignment.get(job.id);
        if (lane !== undefined && lane < laneCount) {
          lanes[lane]?.push(job);
        }
      }
      result[dateStr] = lanes;
    }
    return result;
  }, [jobs, laneCount, weekDates]);

  // ── Drop handler — time-of-day preservation ───────────────────────────────
  const handleCellDrop = async (
    jobId: string,
    laneIndex: number,
    dateStr: string,
  ) => {
    const job = jobs.find((j) => j.id === jobId);
    if (!job) return;

    let newStartTime: Date;
    // Mirror time-of-day preservation from DispatchWeekView.tsx:537
    if (job.scheduled_start_at) {
      const origStart = new Date(job.scheduled_start_at);
      const pad = (n: number) => String(n).padStart(2, "0");
      const timeOfDay = `T${pad(origStart.getUTCHours())}:${pad(origStart.getUTCMinutes())}:${pad(origStart.getUTCSeconds())}.000Z`;
      newStartTime = new Date(`${dateStr}${timeOfDay}`);
    } else {
      newStartTime = new Date(`${dateStr}T08:00:00.000Z`); // fallback: 8 AM UTC
    }

    await onJobDrop(jobId, laneIndex, dateStr, newStartTime);
  };

  // ── No lanes configured ───────────────────────────────────────────────────
  if (laneCount === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-neutral-500 text-sm text-center px-4">
        <p className="font-medium text-neutral-700">
          No schedule lanes configured
        </p>
        <p className="mt-1 text-caption">
          <a
            href="/settings/billing"
            className="text-brand-600 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 rounded"
          >
            Go to Settings
          </a>{" "}
          to configure your schedule lanes.
        </p>
      </div>
    );
  }

  const tableMinWidth = ROW_HEADER_WIDTH_PX + laneCount * LANE_COL_WIDTH_PX;

  return (
    <>
      {/* ── Mobile fallback — mirrors DispatchWeekView.tsx:725 ─────────────── */}
      <div className="md:hidden flex flex-col items-center justify-center py-12 text-neutral-600 text-sm text-center px-4">
        <p>Week view is available on desktop.</p>
        <button
          type="button"
          className="mt-3 px-4 py-2 border border-brand-200 bg-brand-50 text-brand-700 text-sm font-medium rounded-md hover:bg-brand-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
          onClick={() => {
            onViewTabChange?.("day");
            onNavigateToDate(todayStr);
          }}
        >
          View Today
        </button>
      </div>

      {/* ── Desktop grid ───────────────────────────────────────────────────── */}
      <div className="hidden md:flex flex-col h-full overflow-hidden">
        <div
          className="flex-1 overflow-auto"
          // DragOverlay from page-level DndContext will render the ghost card
          onDragStart={(e) => {
            // Sync activeDragJob for overlay — the drag data is sourced from
            // the page-level DndContext; we read job from the element dataset.
            // Actual overlay is handled by page-level DragOverlay in DndContext.
            const jobId = (e.target as HTMLElement)
              .closest("[data-job-id]")
              ?.getAttribute("data-job-id");
            if (jobId) {
              const found = jobs.find((j) => j.id === jobId);
              setActiveDragJob(found ?? null);
            }
          }}
        >
          <table
            style={{
              minWidth: `${tableMinWidth}px`,
              borderCollapse: "collapse",
              width: "100%",
            }}
            role="grid"
            aria-label="Week lane schedule grid"
          >
            {/* ── Column headers — sticky top ──────────────────────────────── */}
            <thead className="sticky top-0 z-20">
              <tr>
                {/* Corner cell */}
                <th
                  scope="col"
                  className="sticky left-0 z-30 bg-white border-r border-b border-neutral-200 px-2 py-2"
                  style={{
                    minWidth: ROW_HEADER_WIDTH_PX,
                    width: ROW_HEADER_WIDTH_PX,
                  }}
                />
                {/* Lane column headers L1…L5 */}
                {Array.from({ length: laneCount }, (_, i) => (
                  <th
                    key={i}
                    scope="col"
                    aria-label={`Lane ${i + 1}`}
                    className="border-r border-b border-neutral-200 bg-white px-3 py-3 text-center"
                    style={{ minWidth: LANE_COL_WIDTH_PX }}
                  >
                    <span className="text-caption font-semibold text-neutral-500 uppercase tracking-wide">
                      {`L${i + 1}`}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>

            {/* ── Day rows ─────────────────────────────────────────────────── */}
            <tbody>
              {weekDates.map((dateStr) => {
                const isToday = dateStr === todayStr;
                const labels = getDayLabels(dateStr);
                const dayLanes = jobsByDayAndLane[dateStr] ?? [];

                return (
                  <tr key={dateStr}>
                    {/* Sticky row header */}
                    <th
                      scope="row"
                      className={[
                        "sticky left-0 z-10 border-r border-b border-neutral-200",
                        "px-2 py-2 text-left",
                        "min-w-24 w-24",
                        isToday ? "bg-brand-50" : "bg-white",
                      ].join(" ")}
                      style={{
                        minWidth: ROW_HEADER_WIDTH_PX,
                        width: ROW_HEADER_WIDTH_PX,
                      }}
                    >
                      <span
                        className={[
                          "block text-caption font-semibold uppercase tracking-wide",
                          isToday ? "text-brand-600" : "text-neutral-500",
                        ].join(" ")}
                      >
                        {labels.weekday}
                      </span>
                      <span
                        className={[
                          "block text-body font-bold",
                          isToday ? "text-brand-700" : "text-neutral-800",
                        ].join(" ")}
                      >
                        {labels.date}
                      </span>
                    </th>

                    {/* Lane cells — always render all laneCount columns */}
                    {Array.from({ length: laneCount }, (_, laneIndex) => {
                      const cellJobs = dayLanes[laneIndex] ?? [];

                      return (
                        <WeekLaneCell
                          key={laneIndex}
                          laneIndex={laneIndex}
                          dateStr={dateStr}
                          jobs={cellJobs}
                          dayLabel={`${labels.weekday} ${labels.date}`}
                          isActiveDrag={activeDragJob !== null}
                          onJobDrop={handleCellDrop}
                          onJobClick={onJobClick}
                          onJobContextMenu={onJobContextMenu}
                          dragJob={activeDragJob}
                        />
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* DragOverlay ghost card — same visual as DispatchWeekView */}
      {activeDragJob && (
        <DragOverlay>
          <div className="border border-brand-400 rounded px-3 py-2 bg-white shadow-lg text-caption font-medium text-brand-700 opacity-90 pointer-events-none">
            {activeDragJob.title}
          </div>
        </DragOverlay>
      )}
    </>
  );
}
