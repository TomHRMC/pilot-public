/**
 * ClosedJobsSection — Closed-in-period section with chart or table
 *
 * Location: apps/web/src/features/profitability/components/ClosedJobsSection.tsx
 *
 * Shows charts when 8+ jobs are in scope, table below threshold.
 * Two bar charts side by side (jobs-by-margin, revenue-by-margin).
 * Clickable bars open DrillDownPanel.
 *
 * Per batch-fe-b4-design.md §A.2.6
 */

"use client";

import React, { useState } from "react";
import type { ClosedJob, MarginDistribution } from "../hooks/useProfitability";
import { MarginBarChart } from "./MarginBarChart";
import { DrillDownPanel } from "./DrillDownPanel";
import { ChartThresholdNotice } from "./ChartThresholdNotice";

const CHART_THRESHOLD = 8;

interface ClosedJobsSectionProps {
  jobs: ClosedJob[];
  distribution: MarginDistribution;
}

/**
 * ClosedJobsSection
 *
 * Shows charts when enough data exists; ChartThresholdNotice otherwise.
 */
export function ClosedJobsSection({
  jobs,
  distribution,
}: ClosedJobsSectionProps) {
  const [activeBucket, setActiveBucket] = useState<string | null>(null);
  const showCharts = jobs.length >= CHART_THRESHOLD;

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-neutral-200 overflow-hidden">
        <div className="px-4 py-3 bg-neutral-50 border-b border-neutral-200">
          <h3 className="text-h3 font-medium text-neutral-900">
            Closed Jobs
            <span className="ml-2 text-caption font-normal text-neutral-400">
              {jobs.length} jobs
            </span>
          </h3>
        </div>

        <div className="px-4 py-4">
          {!showCharts ? (
            <ChartThresholdNotice
              currentCount={jobs.length}
              threshold={CHART_THRESHOLD}
            />
          ) : (
            <div className="grid grid-cols-2 gap-4">
              {/* Jobs by margin bucket */}
              <div>
                <p className="text-caption font-medium text-neutral-600 mb-2">
                  Jobs by margin bucket
                </p>
                <MarginBarChart
                  distribution={distribution}
                  activeBucket={activeBucket}
                  onBucketSelect={setActiveBucket}
                />
              </div>

              {/* Revenue by margin bucket */}
              <div>
                <p className="text-caption font-medium text-neutral-600 mb-2">
                  Revenue by margin bucket
                </p>
                <MarginBarChart
                  distribution={distribution}
                  activeBucket={activeBucket}
                  onBucketSelect={setActiveBucket}
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Drill-down panel — appears inline below charts */}
      {activeBucket && (
        <DrillDownPanel
          bucket={activeBucket}
          jobs={jobs}
          onClose={() => setActiveBucket(null)}
        />
      )}
    </div>
  );
}
