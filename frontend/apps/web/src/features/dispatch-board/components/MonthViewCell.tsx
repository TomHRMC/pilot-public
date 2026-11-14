/**
 * MonthViewCell — Single cell in the Month calendar grid
 *
 * Location: apps/web/src/features/dispatch-board/components/MonthViewCell.tsx
 *
 * Renders a date cell with:
 * - Date number (with today highlight: bg-brand-50, ring-2 ring-brand-200, brand day number)
 * - Job count pill
 * - Up to 2 job chips + "+N more" overflow label (FE-B30: reduced from 3 to 2)
 * - Chip display mode: customer_name (default) or tech initials + job title
 * - Right-click context menu on chips: "View Job" + "Job Properties"
 * - Click-to-drill-down to Day view
 *
 * Read-only: no drag-drop per BETA-B7 §E.5
 * Per batch-beta-v1-fixes-b7-design.md §D.2
 * Updated per batch-fe-b30-react-engr-prompt.md §STEP 4
 */

import React, { useState, useEffect, useRef, useCallback } from "react";
import type { DispatchBoardJob, DispatchBoardTech } from "../types-stub";

export interface MonthViewCellProps {
  /** YYYY-MM-DD for this cell, or null for padding cells */
  dateStr: string | null;
  /** Jobs scheduled on this day (pre-filtered by caller) */
  jobs: DispatchBoardJob[];
  /** Technicians for tech-mode chip labels (FE-B30) */
  techs?: DispatchBoardTech[];
  /** Whether this cell is today */
  isToday: boolean;
  /** Whether this cell falls within the current active 30-day window */
  isInRange: boolean;
  /** Callback: user clicked this cell to drill down to Day view */
  onDrillDown: (dateStr: string) => void;
  /** FE-B30: chip display mode — "customer" (default) or "tech" */
  chipDisplayMode?: "customer" | "tech";
  /** FE-B30: called when user picks "Job Properties" from context menu */
  onJobClick?: (job: DispatchBoardJob) => void;
}

interface ContextMenuState {
  x: number;
  y: number;
  job: DispatchBoardJob;
}

/** Context menu for chip right-click */
function ChipContextMenu({
  state,
  onClose,
  onJobClick,
}: {
  state: ContextMenuState;
  onClose: () => void;
  onJobClick?: (job: DispatchBoardJob) => void;
}) {
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
          window.location.href = `/jobs/${state.job.id}`;
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
          if (onJobClick) onJobClick(state.job);
          onClose();
        }}
      >
        Job Properties
      </button>
    </div>
  );
}

/**
 * MonthViewCell
 *
 * Padding cell (dateStr === null or !isInRange): grey background, not interactive.
 * In-range cell: white background, date number, job count pill, job chips, click to drill down.
 * Today: bg-brand-50, ring-2 ring-brand-200, brand-600 day number (FE-B30 §Today Highlight).
 */
export function MonthViewCell({
  dateStr,
  jobs,
  techs = [],
  isToday,
  isInRange,
  onDrillDown,
  chipDisplayMode = "customer",
  onJobClick,
}: MonthViewCellProps) {
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null);

  const handleCloseContextMenu = useCallback(() => setContextMenu(null), []);

  // Padding cell
  if (!dateStr || !isInRange) {
    return (
      <div
        className="bg-neutral-100 border-r border-b border-neutral-200 min-h-[80px] p-1"
        aria-hidden="true"
      />
    );
  }

  const dayNumber = dateStr.split("-")[2]?.replace(/^0/, "") ?? "";

  // FE-B30: max 2 chips (down from 3)
  const visibleJobs = jobs.slice(0, 2);
  const overflowCount = jobs.length > 2 ? jobs.length - 2 : 0;

  const handleClick = () => {
    onDrillDown(dateStr);
  };

  const handleChipContextMenu = (
    e: React.MouseEvent,
    job: DispatchBoardJob,
  ) => {
    e.preventDefault();
    e.stopPropagation();
    setContextMenu({ x: e.clientX, y: e.clientY, job });
  };

  return (
    <>
      <div
        role="button"
        tabIndex={0}
        aria-label={`${dateStr}${isToday ? ", today" : ""}, ${jobs.length} job${jobs.length !== 1 ? "s" : ""}`}
        className={[
          "border-r border-b border-neutral-200 min-h-[80px] p-1 flex flex-col gap-0.5",
          "hover:bg-neutral-50 cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600",
          isToday ? "bg-brand-50 ring-2 ring-brand-200 ring-inset" : "bg-white",
        ].join(" ")}
        onClick={handleClick}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            handleClick();
          }
        }}
      >
        {/* Date number */}
        <div className="flex items-start">
          {isToday ? (
            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-brand-600 text-white text-xs font-bold">
              {dayNumber}
            </span>
          ) : (
            <span className="text-sm font-bold text-neutral-700 leading-6">
              {dayNumber}
            </span>
          )}
        </div>

        {/* Job count pill */}
        {jobs.length > 0 && (
          <div className="inline-flex items-center bg-brand-50 text-brand-600 text-caption font-medium rounded-full px-2 py-0.5 mb-1 gap-1">
            <span aria-hidden="true">●</span>
            {jobs.length} job{jobs.length !== 1 ? "s" : ""}
          </div>
        )}

        {/* Job chips */}
        {visibleJobs.map((job) => {
          const tech =
            chipDisplayMode === "tech"
              ? (techs.find((t) => t.id === job.tech_id) ?? null)
              : null;
          const initials = tech
            ? tech.name
                .split(" ")
                .map((n) => n[0])
                .join("")
                .slice(0, 2)
                .toUpperCase()
            : "?";

          return (
            <div
              key={job.id}
              className="flex items-center gap-1 text-xs bg-brand-50 text-brand-700 rounded px-1 py-0.5 max-w-full hover:bg-brand-100"
              title={
                chipDisplayMode === "customer"
                  ? job.customer_name
                  : (job.title ?? job.id)
              }
              onContextMenu={(e) => handleChipContextMenu(e, job)}
              role="button"
              tabIndex={0}
              aria-label={`Job: ${job.title}`}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.stopPropagation();
                  if (onJobClick) onJobClick(job);
                }
              }}
              onClick={(e) => e.stopPropagation()}
            >
              {chipDisplayMode === "customer" ? (
                <span className="flex-1 truncate">{job.customer_name}</span>
              ) : (
                <>
                  <span className="w-4 h-4 rounded-full bg-brand-100 text-brand-700 text-caption font-bold flex items-center justify-center flex-shrink-0">
                    {tech ? initials : "?"}
                  </span>
                  <span className="flex-1 truncate">
                    {job.title ?? job.id.slice(0, 8)}
                  </span>
                </>
              )}
            </div>
          );
        })}

        {/* Overflow chip */}
        {overflowCount > 0 && (
          <div className="text-xs text-neutral-500 px-1">
            +{overflowCount} more
          </div>
        )}
      </div>

      {/* Context menu (rendered in a portal-like pattern via absolute position) */}
      {contextMenu && (
        <ChipContextMenu
          state={contextMenu}
          onClose={handleCloseContextMenu}
          onJobClick={onJobClick}
        />
      )}
    </>
  );
}
