/**
 * WipSummaryRow — 4 metric cards for the WIP report
 *
 * Location: apps/web/src/features/wip/components/WipSummaryRow.tsx
 *
 * Pure presentational — takes summary + marginTargetPct.
 * Cards 2 & 3 (Over Budget / Below Margin Target) get emotional-hook accents
 * (left border + colored value + icon). Color is never the only signal (WCAG 1.4.1).
 *
 * Per batch-up-1-ui-design-spec.md §2.2.
 */

import {
  BriefcaseIcon,
  ExclamationTriangleIcon,
  ChartBarSquareIcon,
  ScaleIcon,
} from "@heroicons/react/24/outline";
import type { components } from "@pilot/shared-types";
import { formatCents } from "../lib/wip-format";

type WipSummary = components["schemas"]["WipSummary"];

interface WipSummaryRowProps {
  summary: WipSummary;
}

const cardBase = "rounded-lg border border-neutral-200 bg-white p-4";
const labelClass =
  "text-caption font-medium text-neutral-500 uppercase tracking-wide";
const valueClass = "text-h2 font-semibold text-neutral-900 mt-1";

export function WipSummaryRow({ summary }: WipSummaryRowProps) {
  const projected = formatCents(summary.total_projected_cost_cents);
  const budget = formatCents(summary.total_quoted_budget_cents);
  const noBudget = summary.total_quoted_budget_cents === 0;

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {/* Card 1 — Active Jobs (neutral) */}
      <div className={cardBase}>
        <div className="flex items-center gap-2">
          <BriefcaseIcon
            className="w-5 h-5 text-neutral-500"
            aria-hidden="true"
          />
          <span className={labelClass}>Active Jobs</span>
        </div>
        <p className={valueClass}>{summary.active_job_count}</p>
      </div>

      {/* Card 2 — Over Budget (fault accent) */}
      <div className={`${cardBase} border-l-4 border-l-fault-400`}>
        <div className="flex items-center gap-2">
          <ExclamationTriangleIcon
            className="w-5 h-5 text-fault-600"
            aria-hidden="true"
          />
          <span className={labelClass}>Over Budget</span>
        </div>
        <p className={`${valueClass} text-fault-600`}>
          {summary.jobs_over_budget_count}
        </p>
      </div>

      {/* Card 3 — Below Margin Target (alert accent) */}
      <div className={`${cardBase} border-l-4 border-l-alert-400`}>
        <div className="flex items-center gap-2">
          <ChartBarSquareIcon
            className="w-5 h-5 text-alert-600"
            aria-hidden="true"
          />
          <span className={labelClass}>Below Margin Target</span>
        </div>
        <p className={`${valueClass} text-alert-600`}>
          {summary.jobs_below_margin_target_count}
        </p>
      </div>

      {/* Card 4 — Projected vs Budget (neutral, two-line) */}
      <div className={cardBase}>
        <div className="flex items-center gap-2">
          <ScaleIcon className="w-5 h-5 text-neutral-500" aria-hidden="true" />
          <span className={labelClass}>Projected vs Budget</span>
        </div>
        <p className="text-h3 font-semibold text-neutral-900 mt-1">
          {projected}
        </p>
        {noBudget ? (
          <p className="text-caption text-neutral-400">No quoted budgets</p>
        ) : (
          <p className="text-caption text-neutral-500">of {budget} budget</p>
        )}
      </div>
    </div>
  );
}
