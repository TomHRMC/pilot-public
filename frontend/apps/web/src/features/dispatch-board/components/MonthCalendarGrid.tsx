/**
 * MonthCalendarGrid — 7-column monthly calendar grid for the Dispatch Board
 *
 * Location: apps/web/src/features/dispatch-board/components/MonthCalendarGrid.tsx
 *
 * Consumes a 30-element dateRange (rolling window from activeDate) and renders
 * a standard weekly calendar grid with padding cells to align with day-of-week headers.
 *
 * FE-B30: Added chipDisplayMode, techs, and onJobClick props per design doc §F.4.
 *
 * Read-only: no drag-drop per BETA-B7 §E.5
 * Per batch-beta-v1-fixes-b7-design.md §D.3
 * Updated per batch-fe-b30-react-engr-prompt.md §STEP 4
 */

import React from "react";
import type { DispatchBoardJob, DispatchBoardTech } from "../types-stub";
import { MonthViewCell } from "./MonthViewCell";

export interface MonthCalendarGridProps {
  /** 30 YYYY-MM-DD strings from DispatchBoardPage (activeDate to activeDate+29) */
  dateRange: string[];
  /** All jobs in the date range from useDispatchBoard */
  jobs: DispatchBoardJob[];
  /** All technicians — passed to cells for tech mode chip labels (FE-B30) */
  techs?: DispatchBoardTech[];
  /** Callback to navigate to day view for a specific date */
  onDrillDown: (dateStr: string) => void;
  /** FE-B30: Chip display mode — "customer" (default) or "tech" */
  chipDisplayMode?: "customer" | "tech";
  /** FE-B30: Called when user right-clicks a chip and picks "Job Properties" */
  onJobClick?: (job: DispatchBoardJob) => void;
}

const DAY_HEADERS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"] as const;

const TODAY = new Date().toISOString().slice(0, 10);

/**
 * MonthCalendarGrid
 *
 * Layout:
 * 1. Day-of-week header row (Sun–Sat)
 * 2. Cell grid: padding cells before first day + 30 real cells + trailing padding
 * 3. Each real cell: MonthViewCell with filtered jobs for that date
 */
export function MonthCalendarGrid({
  dateRange,
  jobs,
  techs = [],
  onDrillDown,
  chipDisplayMode = "customer",
  onJobClick,
}: MonthCalendarGridProps) {
  if (dateRange.length === 0) {
    return null;
  }

  // Compute first day of week offset
  const firstDate = dateRange[0]!;
  const [year, month, day] = firstDate.split("-").map(Number) as [
    number,
    number,
    number,
  ];
  const firstDayOfWeek = new Date(year, month - 1, day).getDay(); // 0=Sun, 6=Sat

  // Build cell array: leading padding + real dates + trailing padding
  const totalCells = firstDayOfWeek + dateRange.length;
  const trailingPadding = totalCells % 7 === 0 ? 0 : 7 - (totalCells % 7);
  const totalWithTrailing = totalCells + trailingPadding;

  return (
    <div className="flex flex-col h-full overflow-hidden p-2">
      {/* Day-of-week headers */}
      <div className="grid grid-cols-7">
        {DAY_HEADERS.map((d) => (
          <div
            key={d}
            className="text-xs font-medium text-neutral-500 uppercase text-center py-1"
          >
            {d}
          </div>
        ))}
      </div>

      {/* Calendar cell grid */}
      <div className="grid grid-cols-7 border-l border-t border-neutral-200 flex-1 overflow-y-auto">
        {Array.from({ length: totalWithTrailing }, (_, idx) => {
          const dateIndex = idx - firstDayOfWeek;

          // Padding cell (before first day or after last day)
          if (dateIndex < 0 || dateIndex >= dateRange.length) {
            return (
              <div
                key={`pad-${idx}`}
                className="bg-neutral-100 border-r border-b border-neutral-200 min-h-[80px]"
                aria-hidden="true"
              />
            );
          }

          const dateStr = dateRange[dateIndex]!;
          const cellJobs = jobs.filter((j) =>
            j.scheduled_start_at?.startsWith(dateStr),
          );

          return (
            <MonthViewCell
              key={dateStr}
              dateStr={dateStr}
              jobs={cellJobs}
              techs={techs}
              isToday={dateStr === TODAY}
              isInRange
              onDrillDown={onDrillDown}
              chipDisplayMode={chipDisplayMode}
              onJobClick={onJobClick}
            />
          );
        })}
      </div>
    </div>
  );
}
