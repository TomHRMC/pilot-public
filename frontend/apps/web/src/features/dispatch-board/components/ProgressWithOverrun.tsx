/**
 * ProgressWithOverrun — Hours progress bar with overrun indicator
 *
 * Location: apps/web/src/features/dispatch-board/components/ProgressWithOverrun.tsx
 *
 * Formula: hours_worked / (hours_worked + hours_remaining)
 * Shows red fill + warning glyph when projected total > quoted hours.
 * Uses token colors only.
 *
 * Per batch-fe-b4-design.md §A.2.5
 */

import React from "react";

interface ProgressWithOverrunProps {
  hoursWorked: number;
  hoursRemaining: number;
  quotedHours: number;
}

/**
 * ProgressWithOverrun
 *
 * Renders a progress bar for ETC tracking.
 * Red fill and warning icon when the projected total exceeds quoted hours.
 */
export function ProgressWithOverrun({
  hoursWorked,
  hoursRemaining,
  quotedHours,
}: ProgressWithOverrunProps) {
  const projectedTotal = hoursWorked + hoursRemaining;
  const isOverQuote = projectedTotal > quotedHours;

  // Progress = how much of the projected total has been worked
  const progressPct =
    projectedTotal > 0
      ? Math.min(100, (hoursWorked / projectedTotal) * 100)
      : 0;

  // How far over quote we are (for visual overrun bar)
  const overrunPct =
    isOverQuote && quotedHours > 0
      ? Math.min(100, ((projectedTotal - quotedHours) / quotedHours) * 100)
      : 0;

  const fillClass = isOverQuote ? "bg-fault-400" : "bg-margin-400";
  const trackClass = isOverQuote ? "bg-fault-100" : "bg-neutral-200";

  return (
    <div className="space-y-1">
      {/* Progress bar */}
      <div
        className={`h-1.5 rounded-full overflow-hidden ${trackClass}`}
        role="progressbar"
        aria-valuenow={Math.round(progressPct)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${hoursWorked.toFixed(1)} of ${projectedTotal.toFixed(1)} projected hours worked`}
      >
        <div
          className={`h-full rounded-full transition-all ${fillClass}`}
          style={{ width: `${progressPct}%` }}
        />
      </div>

      {/* Labels */}
      <div className="flex items-center justify-between text-caption text-neutral-600">
        <span>
          <span className="font-medium text-neutral-900">
            {hoursWorked.toFixed(1)}h
          </span>
          {" worked"}
        </span>

        <div className="flex items-center gap-1">
          {isOverQuote && (
            <span
              className="text-fault-600"
              aria-label="Over quoted hours"
              title="Over quote"
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
          <span className={isOverQuote ? "text-fault-600 font-medium" : ""}>
            {projectedTotal.toFixed(1)}h / {quotedHours.toFixed(1)}h quoted
          </span>
          {isOverQuote && overrunPct > 0 && (
            <span className="text-fault-600">
              (+{(projectedTotal - quotedHours).toFixed(1)}h)
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
