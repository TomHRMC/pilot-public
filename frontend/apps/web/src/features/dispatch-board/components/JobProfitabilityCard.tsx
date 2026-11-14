/**
 * JobProfitabilityCard — Profitability widget within the job detail panel
 *
 * Location: apps/web/src/features/dispatch-board/components/JobProfitabilityCard.tsx
 *
 * Shows: revenue, cost-to-date, projected margin, margin bucket color chip.
 * Composes MarginBucketChip + ProgressWithOverrun + ETCDrillDown.
 *
 * Per batch-fe-b4-design.md §A.2.5
 */

"use client";

import React, { useState } from "react";
import type { ProjectedMargin, QuoteLine } from "../hooks/useJobDetail";
import { MarginBucketChip } from "./MarginBucketChip";
import { ProgressWithOverrun } from "./ProgressWithOverrun";
import { ETCDrillDown } from "./ETCDrillDown";

interface JobProfitabilityCardProps {
  projectedMargin: ProjectedMargin;
  quoteLines: QuoteLine[];
}

function formatCents(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(cents / 100);
}

/**
 * JobProfitabilityCard
 *
 * Renders the job's current financial health inside the job detail panel.
 * ETC drill-down is collapsible to save vertical space.
 */
export function JobProfitabilityCard({
  projectedMargin,
  quoteLines,
}: JobProfitabilityCardProps) {
  const [showEtcDrillDown, setShowEtcDrillDown] = useState(false);

  const profitCents =
    projectedMargin.revenue_cents - projectedMargin.cost_to_date_cents;

  return (
    <div className="rounded-lg border border-neutral-200 overflow-hidden">
      {/* Card header */}
      <div className="px-4 py-3 bg-neutral-50 border-b border-neutral-200 flex items-center justify-between">
        <h3 className="text-h3 font-medium text-neutral-900">Profitability</h3>
        <MarginBucketChip
          bucket={projectedMargin.margin_bucket}
          marginPct={projectedMargin.projected_margin_pct}
        />
      </div>

      <div className="px-4 py-3 space-y-4">
        {/* Key metrics row */}
        <div className="grid grid-cols-3 gap-3">
          <div>
            <p className="text-caption text-neutral-600">Revenue</p>
            <p className="text-body font-medium text-neutral-900 tabular-nums">
              {formatCents(projectedMargin.revenue_cents)}
            </p>
          </div>
          <div>
            <p className="text-caption text-neutral-600">Cost to date</p>
            <p className="text-body font-medium text-neutral-900 tabular-nums">
              {formatCents(projectedMargin.cost_to_date_cents)}
            </p>
          </div>
          <div>
            <p className="text-caption text-neutral-600">Projected profit</p>
            <p
              className={`text-body font-medium tabular-nums ${profitCents >= 0 ? "text-margin-600" : "text-fault-600"}`}
            >
              {formatCents(profitCents)}
            </p>
          </div>
        </div>

        {/* ETC hours progress */}
        <div>
          <p className="text-caption text-neutral-600 mb-1.5">Hours tracking</p>
          <ProgressWithOverrun
            hoursWorked={projectedMargin.hours_worked}
            hoursRemaining={projectedMargin.etc_hours_remaining}
            quotedHours={projectedMargin.quoted_hours}
          />
        </div>

        {/* ETC drill-down toggle */}
        <div>
          <button
            type="button"
            onClick={() => setShowEtcDrillDown(!showEtcDrillDown)}
            className="flex items-center gap-1 text-caption font-medium text-brand-600 hover:text-brand-800 focus:outline-none focus-visible:ring-1 focus-visible:ring-brand-600 rounded"
            aria-expanded={showEtcDrillDown}
          >
            <svg
              width="12"
              height="12"
              viewBox="0 0 12 12"
              fill="currentColor"
              className={`transition-transform ${showEtcDrillDown ? "rotate-90" : ""}`}
              aria-hidden="true"
            >
              <path
                d="M4 2l4 4-4 4"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                fill="none"
              />
            </svg>
            {showEtcDrillDown ? "Hide" : "Show"} line-item breakdown
          </button>

          {showEtcDrillDown && (
            <div className="mt-2">
              <ETCDrillDown quoteLines={quoteLines} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
