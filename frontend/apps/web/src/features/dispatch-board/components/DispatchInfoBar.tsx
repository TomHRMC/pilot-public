/**
 * DispatchInfoBar — Bottom status bar for the dispatch board
 *
 * Location: apps/web/src/features/dispatch-board/components/DispatchInfoBar.tsx
 *
 * Shows techs-working-today, jobs-scheduled, warnings-count,
 * conflicts-blocked-count, last-updated timestamp.
 *
 * Per batch-fe-b4-design.md §A.2.1
 */

import React from "react";
import type { DispatchBoardJob, DispatchBoardTech } from "../types-stub";

interface DispatchInfoBarProps {
  techs: DispatchBoardTech[];
  jobs: DispatchBoardJob[];
  lastUpdated: Date | null;
}

/**
 * DispatchInfoBar
 *
 * Displays a summary of the day's dispatch state at the bottom of the board.
 */
export function DispatchInfoBar({
  techs,
  jobs,
  lastUpdated,
}: DispatchInfoBarProps) {
  const scheduledJobs = jobs.filter(
    (j) => j.status !== "unassigned" && j.tech_id !== null,
  );
  const unassignedJobs = jobs.filter((j) => j.tech_id === null);
  // DISPATCH-B3: emergency + urgent (was "rush" — removed from schema)
  const urgentOrEmergencyJobs = jobs.filter(
    (j) => j.priority === "emergency" || j.priority === "urgent",
  );
  const activeTechs = new Set(
    jobs.filter((j) => j.tech_id).map((j) => j.tech_id),
  ).size;

  return (
    <div
      className="flex items-center gap-6 px-4 py-2 border-t border-neutral-200 bg-neutral-50 text-caption text-neutral-600"
      aria-label="Dispatch board summary"
    >
      <span>
        <span className="font-medium text-neutral-900">{activeTechs}</span>
        {" / "}
        {techs.length} techs working today
      </span>

      <span>
        <span className="font-medium text-neutral-900">
          {scheduledJobs.length}
        </span>
        {" jobs scheduled"}
      </span>

      {unassignedJobs.length > 0 && (
        <span className="text-alert-600">
          <span className="font-medium">{unassignedJobs.length}</span>
          {" unassigned"}
        </span>
      )}

      {urgentOrEmergencyJobs.length > 0 && (
        <span className="text-fault-600">
          <span className="font-medium">{urgentOrEmergencyJobs.length}</span>
          {" urgent/emergency"}
        </span>
      )}

      <div className="flex-1" />

      {lastUpdated && (
        <span className="text-neutral-400">
          Updated{" "}
          {lastUpdated.toLocaleTimeString("en-US", {
            hour: "numeric",
            minute: "2-digit",
          })}
        </span>
      )}
    </div>
  );
}
