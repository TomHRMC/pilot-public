/**
 * ConflictItem — Single conflict row in the conflict preview pane
 *
 * Location: apps/web/src/features/dispatch-board/components/ConflictItem.tsx
 *
 * Renders conflict class badge + description + suggested resolution.
 * Banner treatment varies by conflict class (§G.6).
 *
 * Per batch-fe-b4-design.md §A.2.3 §G.6
 */

import React from "react";
import { CONFLICT_CLASS_TOKENS } from "@pilot/ui";
import type { SchedulingConflict } from "../types-stub";
import { ConflictSeverityBadge } from "./ConflictSeverityBadge";

interface ConflictItemProps {
  conflict: SchedulingConflict;
}

/**
 * ConflictItem
 *
 * Single conflict row with severity-class visual treatment.
 * Uses token-based banner colors from CONFLICT_CLASS_TOKENS.
 */
export function ConflictItem({ conflict }: ConflictItemProps) {
  const tokens = CONFLICT_CLASS_TOKENS[conflict.conflict_class];
  const detail = conflict.detail as {
    overlapping_job_title?: string;
    overlapping_job_id?: string;
  };

  return (
    <div
      className={`rounded-md border p-3 ${tokens.bannerBgClass} ${tokens.bannerBorderClass}`}
      role="listitem"
    >
      <div className="flex items-start gap-2">
        <div className="flex-shrink-0 mt-0.5">
          <ConflictSeverityBadge conflictClass={conflict.conflict_class} />
        </div>
        <div className="flex-1 min-w-0">
          {/* Description */}
          <p className={`text-body ${tokens.bannerTextClass}`}>
            {detail.overlapping_job_title
              ? `Overlaps with "${detail.overlapping_job_title}"`
              : getConflictDescription(conflict.conflict_class)}
          </p>

          {/* Suggested resolution */}
          {conflict.suggested_resolution && (
            <p className="text-caption text-neutral-600 mt-1">
              {conflict.suggested_resolution}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function getConflictDescription(
  conflictClass: SchedulingConflict["conflict_class"],
): string {
  switch (conflictClass) {
    case "overlap":
      return "This tech is already scheduled during this time.";
    case "availability":
      return "This time is outside the tech's working hours.";
    case "travel":
      return "Drive time to this job may be infeasible.";
    case "info":
      return "Informational note about this scheduling action.";
  }
}
