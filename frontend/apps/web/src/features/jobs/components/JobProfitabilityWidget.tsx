/**
 * JobProfitabilityWidget — persistent profitability section above tabs
 *
 * Location: apps/web/src/features/jobs/components/JobProfitabilityWidget.tsx
 *
 * Shows:
 *   Actual Labor / Materials from useJob (actual_*_cost_cents)
 *   Projected Margin % from useProjectedMargin
 *   Above/below 20% target indicator
 *
 * Always visible regardless of active tab.
 */

"use client";

import React from "react";
import { useJob } from "../hooks/useJob";
import {
  useProjectedMargin,
  MARGIN_TARGET_PCT,
} from "../hooks/useProjectedMargin";

interface JobProfitabilityWidgetProps {
  jobId: string;
}

function centsToDisplay(cents: number): string {
  return `$${(cents / 100).toLocaleString("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })}`;
}

function SkeletonRow() {
  return (
    <div className="animate-pulse">
      <div className="h-4 bg-neutral-200 rounded w-24 mb-1" />
      <div className="h-6 bg-neutral-200 rounded w-32" />
    </div>
  );
}

export function JobProfitabilityWidget({ jobId }: JobProfitabilityWidgetProps) {
  const { data: job, isLoading: isJobLoading } = useJob(jobId);
  const { data: margin, isLoading: isMarginLoading } =
    useProjectedMargin(jobId);

  const isLoading = isJobLoading || isMarginLoading;

  const marginPct = margin?.projected_margin_pct ?? null;
  const isAboveTarget = marginPct !== null && marginPct >= MARGIN_TARGET_PCT;

  return (
    <div className="bg-white border-b border-neutral-200 px-6 py-4">
      <h2 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-3">
        Profitability
      </h2>

      <div className="grid grid-cols-3 gap-6">
        {/* Labor */}
        <div>
          <p className="text-xs text-neutral-500 mb-1">Actual Labor</p>
          {isLoading ? (
            <SkeletonRow />
          ) : (
            <p className="text-lg font-semibold text-neutral-900">
              {centsToDisplay(job?.actual_labor_cost_cents ?? 0)}
            </p>
          )}
        </div>

        {/* Materials */}
        <div>
          <p className="text-xs text-neutral-500 mb-1">Actual Materials</p>
          {isLoading ? (
            <SkeletonRow />
          ) : (
            <p className="text-lg font-semibold text-neutral-900">
              {centsToDisplay(job?.actual_material_cost_cents ?? 0)}
            </p>
          )}
        </div>

        {/* Projected Margin */}
        <div>
          <p className="text-xs text-neutral-500 mb-1">Projected Margin</p>
          {isMarginLoading ? (
            <SkeletonRow />
          ) : (
            <div className="flex items-center gap-2">
              <p className="text-lg font-semibold text-neutral-900">
                {marginPct !== null ? `${marginPct}%` : "—"}
              </p>
              {marginPct !== null && (
                <span
                  className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${
                    isAboveTarget
                      ? "bg-green-100 text-green-700"
                      : "bg-red-100 text-red-700"
                  }`}
                  data-testid={isAboveTarget ? "above-target" : "below-target"}
                >
                  {isAboveTarget ? "✅" : "⚠️"}{" "}
                  {isAboveTarget ? "Above target" : "Below target"}
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
