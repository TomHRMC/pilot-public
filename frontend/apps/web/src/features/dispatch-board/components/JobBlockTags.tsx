/**
 * JobBlockTags — Priority / Drive-time-warning tags on job blocks
 *
 * Location: apps/web/src/features/dispatch-board/components/JobBlockTags.tsx
 *
 * DISPATCH-B3: updated from rush/warranty to urgent/emergency per CLASS-B1 schema.
 * Per batch-fe-b4-design.md §A.2.2
 * Uses token colors only — no hardcoded hex or pixel values.
 */

import React from "react";

interface JobBlockTagsProps {
  /** DISPATCH-B3: real priority values from backend — standard/urgent/emergency */
  priority: "standard" | "urgent" | "emergency";
  hasDriveTimeWarning?: boolean;
}

/**
 * JobBlockTags
 *
 * Renders small tags in the top-right of a job block for emergency, urgent,
 * and drive-time-warning states.
 */
export function JobBlockTags({
  priority,
  hasDriveTimeWarning,
}: JobBlockTagsProps) {
  return (
    <div className="flex items-center gap-1 flex-shrink-0">
      {priority === "emergency" && (
        <span
          className="inline-flex items-center px-1 py-0.5 rounded-sm bg-fault-50 text-fault-600 text-caption font-medium leading-none"
          aria-label="Emergency priority"
        >
          Emergency
        </span>
      )}
      {priority === "urgent" && (
        <span
          className="inline-flex items-center px-1 py-0.5 rounded-sm bg-alert-50 text-alert-600 text-caption font-medium leading-none"
          aria-label="Urgent priority"
        >
          Urgent
        </span>
      )}
      {hasDriveTimeWarning && (
        <span
          className="inline-flex items-center text-alert-400"
          aria-label="Drive time warning"
          title="Drive time to this job may be infeasible"
        >
          <svg
            width="12"
            height="12"
            viewBox="0 0 12 12"
            fill="currentColor"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M5.091 1.497C5.449.834 6.55.834 6.909 1.497l4.34 7.503c.359.625-.09 1.406-.824 1.406H1.576c-.734 0-1.183-.781-.824-1.406L5.09 1.497zM6 3.75a.5.5 0 01.5.5v2.333a.5.5 0 01-1 0V4.25A.5.5 0 016 3.75zm0 5.25a.667.667 0 100-1.333.667.667 0 000 1.333z"
              clipRule="evenodd"
            />
          </svg>
        </span>
      )}
    </div>
  );
}
