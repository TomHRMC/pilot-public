/**
 * DrillDownPanel — Inline drill-down panel below charts
 *
 * Location: apps/web/src/features/profitability/components/DrillDownPanel.tsx
 *
 * Shows jobs in selected margin bucket with close date, revenue, margin.
 * Per batch-fe-b4-design.md §A.2.6
 */

import React from "react";
import type { ClosedJob } from "../hooks/useProfitability";
import { MarginBucketChip } from "../../dispatch-board/components/MarginBucketChip";

interface DrillDownPanelProps {
  bucket: string | null;
  jobs: ClosedJob[];
  onClose: () => void;
}

function formatCents(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(cents / 100);
}

const BUCKET_LABELS: Record<string, string> = {
  "below-low": "Below target",
  low: "Low margin",
  medium: "On target",
  high: "Strong margin",
};

/**
 * DrillDownPanel
 *
 * Renders an inline table of closed jobs in the selected margin bucket.
 */
export function DrillDownPanel({ bucket, jobs, onClose }: DrillDownPanelProps) {
  if (!bucket) return null;

  const bucketJobs = jobs.filter((j) => j.margin_bucket === bucket);

  return (
    <div
      className="rounded-lg border border-neutral-200 overflow-hidden"
      role="region"
      aria-label={`Jobs in ${BUCKET_LABELS[bucket] ?? bucket} bucket`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-neutral-50 border-b border-neutral-200">
        <h4 className="text-h3 font-medium text-neutral-900">
          {BUCKET_LABELS[bucket] ?? bucket}
          <span className="ml-2 text-caption font-normal text-neutral-400">
            {bucketJobs.length} job{bucketJobs.length !== 1 ? "s" : ""}
          </span>
        </h4>
        <button
          type="button"
          onClick={onClose}
          className="text-neutral-400 hover:text-neutral-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 rounded-sm"
          aria-label="Close drill-down"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 14 14"
            fill="currentColor"
            aria-hidden="true"
          >
            <path
              d="M3 3l8 8M11 3l-8 8"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          </svg>
        </button>
      </div>

      {/* Table */}
      {bucketJobs.length === 0 ? (
        <div className="px-4 py-4 text-center">
          <p className="text-body text-neutral-400">
            No jobs in this bucket for the selected period.
          </p>
        </div>
      ) : (
        <table
          className="w-full"
          aria-label={`${BUCKET_LABELS[bucket] ?? bucket} jobs detail`}
        >
          <thead>
            <tr className="border-b border-neutral-100">
              {/* FE-B26: Renamed from "Job" → "Job #" */}
              <th className="py-2 pl-4 pr-2 text-left text-caption font-medium text-neutral-600">
                Job #
              </th>
              {/* FE-B26: New "Customer" column */}
              <th className="py-2 px-2 text-left text-caption font-medium text-neutral-600">
                Customer
              </th>
              <th className="py-2 px-2 text-right text-caption font-medium text-neutral-600">
                Closed
              </th>
              <th className="py-2 px-2 text-right text-caption font-medium text-neutral-600">
                Revenue
              </th>
              <th className="py-2 pl-2 pr-4 text-right text-caption font-medium text-neutral-600">
                Margin
              </th>
            </tr>
          </thead>
          <tbody>
            {bucketJobs.map((job) => (
              <tr
                key={job.id}
                className="border-b border-neutral-50 hover:bg-neutral-50"
              >
                {/* FE-B26: Render job_number (fallback to title/group_label) */}
                <td className="py-2 pl-4 pr-2">
                  <p className="text-body text-neutral-900 truncate max-w-32">
                    {job.job_number ?? job.title}
                  </p>
                </td>
                {/* FE-B26: Render customer_name (fallback to "—") */}
                <td className="py-2 px-2">
                  <p className="text-body text-neutral-600 truncate max-w-32">
                    {job.customer_name ?? "—"}
                  </p>
                </td>
                <td className="py-2 px-2 text-right text-body text-neutral-600 tabular-nums whitespace-nowrap">
                  {new Date(job.close_date).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                  })}
                </td>
                <td className="py-2 px-2 text-right text-body text-neutral-900 tabular-nums">
                  {formatCents(job.revenue_cents)}
                </td>
                <td className="py-2 pl-2 pr-4 text-right">
                  <MarginBucketChip
                    bucket={job.margin_bucket}
                    marginPct={job.margin_pct}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
