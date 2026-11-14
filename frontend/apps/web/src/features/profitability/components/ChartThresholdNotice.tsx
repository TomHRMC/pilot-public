/**
 * ChartThresholdNotice — Inline notice when job count is below chart threshold
 *
 * Location: apps/web/src/features/profitability/components/ChartThresholdNotice.tsx
 *
 * "Charts appear when 8+ jobs are in scope. Adjust threshold in Settings → Reports."
 * Per batch-fe-b4-design.md §A.2.6
 */

import React from "react";

interface ChartThresholdNoticeProps {
  currentCount: number;
  threshold: number;
}

/**
 * ChartThresholdNotice
 *
 * Shown instead of charts when the job count is below threshold.
 */
export function ChartThresholdNotice({
  currentCount,
  threshold,
}: ChartThresholdNoticeProps) {
  return (
    <div
      className="rounded-lg border border-neutral-200 bg-neutral-50 px-4 py-3 flex items-start gap-3"
      role="status"
      aria-live="polite"
    >
      <span className="flex-shrink-0 text-neutral-400 mt-0.5">
        <svg
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M8 1a7 7 0 100 14A7 7 0 008 1zM8 3.5a.75.75 0 110 1.5.75.75 0 010-1.5zM7.25 6.5h1.5v4.5h-1.5V6.5z"
            clipRule="evenodd"
          />
        </svg>
      </span>
      <div>
        <p className="text-body text-neutral-700">
          Charts appear when <span className="font-medium">{threshold}+</span>{" "}
          jobs are in scope. Currently {currentCount} job
          {currentCount !== 1 ? "s" : ""} in period.
        </p>
        <p className="text-caption text-neutral-400 mt-0.5">
          Adjust threshold in{" "}
          <span className="text-brand-600">Settings → Reports</span>
        </p>
      </div>
    </div>
  );
}
