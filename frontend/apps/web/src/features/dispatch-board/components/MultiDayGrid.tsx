/**
 * @deprecated FE-B30 (2026-07-12): DispatchBoardPage no longer uses MultiDayGrid for
 * week views. Week → DispatchWeekView (tech-as-column, @dnd-kit).
 * This file is kept to avoid breaking existing tests.
 * Do not use in new code.
 *
 * MultiDayGrid — Side-by-side day panels for 4-Day and Week views
 *
 * Location: apps/web/src/features/dispatch-board/components/MultiDayGrid.tsx
 *
 * Renders N day panels side by side. Each panel shows one date's
 * tech-column × time-row grid. Read-only — no drag-drop targets.
 *
 * Wraps in DndProvider so JobBlock's useDrag hooks are satisfied without
 * console warnings, but no useDrop targets exist — blocks are draggable
 * but drops are no-ops.
 *
 * Per batch-beta-v1-fixes-b5-design.md §C.3
 */

"use client";

import React from "react";
import { DndProvider } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import type { DispatchBoardJob, DispatchBoardTech } from "../types-stub";
import { DispatchGridColumn, GRID_HEIGHT_PX } from "./DispatchGridColumn";

export interface MultiDayGridProps {
  /** YYYY-MM-DD strings for each panel, length 4 (4day) or 7 (week) */
  dateRange: string[];
  techs: DispatchBoardTech[];
  jobs: DispatchBoardJob[];
  onJobSelect: (jobId: string) => void;
}

/** Format a YYYY-MM-DD string as "Mon Jun 9" */
function formatPanelDate(dateStr: string): string {
  // Use T12:00:00 to avoid timezone-induced date shifts
  const d = new Date(dateStr + "T12:00:00");
  return d.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

/**
 * MultiDayGrid
 *
 * N side-by-side day panels for 4-Day and Week views.
 * Each panel filters jobs by date and renders a read-only grid
 * (DispatchGridColumn instances without onDrop).
 */
export function MultiDayGrid({
  dateRange,
  techs,
  jobs,
  onJobSelect,
}: MultiDayGridProps) {
  const today = new Date().toISOString().slice(0, 10);

  return (
    <DndProvider backend={HTML5Backend}>
      <div className="flex overflow-x-auto h-full">
        {dateRange.map((dateStr) => {
          const panelJobs = jobs.filter((j) =>
            j.scheduled_start_at?.startsWith(dateStr),
          );
          const isToday = dateStr === today;
          const displayDate = formatPanelDate(dateStr);

          return (
            <div
              key={dateStr}
              className="flex-shrink-0 border-r border-neutral-200 last:border-r-0"
            >
              {/* Date header */}
              <div
                className={[
                  "px-3 py-2 text-xs font-medium border-b border-neutral-200 text-center",
                  isToday
                    ? "bg-brand-50 text-brand-700"
                    : "bg-neutral-50 text-neutral-600",
                ].join(" ")}
              >
                {displayDate}
              </div>

              {/* Tech columns for this day — read-only (no onDrop) */}
              <div
                className="flex relative overflow-y-auto"
                style={{ height: `${GRID_HEIGHT_PX}px` }}
              >
                {/* Tech columns */}
                {techs.map((tech) => (
                  <DispatchGridColumn
                    key={tech.id}
                    tech={tech}
                    jobs={panelJobs}
                    onJobSelect={onJobSelect}
                    // onDrop intentionally omitted — read-only mode
                  />
                ))}

                {/* Unassigned column */}
                <DispatchGridColumn
                  tech={null}
                  jobs={panelJobs}
                  isUnassigned
                  onJobSelect={onJobSelect}
                  // onDrop intentionally omitted — read-only mode
                />
              </div>
            </div>
          );
        })}
      </div>
    </DndProvider>
  );
}
