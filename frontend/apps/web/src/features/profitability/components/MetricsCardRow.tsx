/**
 * MetricsCardRow — Three large-number metric cards
 *
 * Location: apps/web/src/features/profitability/components/MetricsCardRow.tsx
 *
 * Revenue, Profit, Avg Margin each with period-over-period delta.
 * Per batch-fe-b4-design.md §A.2.6
 */

import React from "react";
import type { ProfitabilitySummary } from "../hooks/useProfitability";

interface MetricsCardRowProps {
  summary: ProfitabilitySummary;
}

function formatCents(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(cents / 100);
}

function DeltaBadge({ delta }: { delta: number }) {
  const isPositive = delta >= 0;
  return (
    <span
      className={`inline-flex items-center gap-0.5 text-caption font-medium ${
        isPositive ? "text-margin-600" : "text-fault-600"
      }`}
    >
      {isPositive ? "↑" : "↓"} {Math.abs(delta).toFixed(1)}%
    </span>
  );
}

interface MetricCardProps {
  label: string;
  value: string;
  delta: number;
  ariaLabel: string;
}

function MetricCard({ label, value, delta, ariaLabel }: MetricCardProps) {
  return (
    <div
      className="flex-1 rounded-lg border border-neutral-200 bg-white p-4"
      aria-label={ariaLabel}
    >
      <p className="text-caption font-medium text-neutral-600 uppercase tracking-wide">
        {label}
      </p>
      <p className="text-display font-medium text-neutral-900 tabular-nums mt-1">
        {value}
      </p>
      <div className="flex items-center gap-1 mt-1">
        <DeltaBadge delta={delta} />
        <span className="text-caption text-neutral-400">vs prev period</span>
      </div>
    </div>
  );
}

/**
 * MetricsCardRow
 *
 * Renders three large summary metric cards in a row.
 */
export function MetricsCardRow({ summary }: MetricsCardRowProps) {
  // Guard: summary may be absent if the API response shape is missing the key.
  // ProfitabilityPage already filters this case, but defend here as well.
  if (!summary) return null;

  return (
    <div
      className="flex gap-4"
      role="region"
      aria-label="Period summary metrics"
    >
      <MetricCard
        label="Revenue"
        value={formatCents(summary.total_revenue_cents)}
        delta={summary.period_over_period_revenue_delta_pct}
        ariaLabel={`Revenue: ${formatCents(summary.total_revenue_cents)}, ${summary.period_over_period_revenue_delta_pct >= 0 ? "up" : "down"} ${Math.abs(summary.period_over_period_revenue_delta_pct).toFixed(1)}% vs previous period`}
      />
      <MetricCard
        label="Profit"
        value={formatCents(summary.total_profit_cents)}
        delta={summary.period_over_period_profit_delta_pct}
        ariaLabel={`Profit: ${formatCents(summary.total_profit_cents)}, ${summary.period_over_period_profit_delta_pct >= 0 ? "up" : "down"} ${Math.abs(summary.period_over_period_profit_delta_pct).toFixed(1)}% vs previous period`}
      />
      <MetricCard
        label="Avg Margin"
        value={`${summary.avg_margin_pct.toFixed(1)}%`}
        delta={summary.period_over_period_margin_delta_pct}
        ariaLabel={`Average margin: ${summary.avg_margin_pct.toFixed(1)}%, ${summary.period_over_period_margin_delta_pct >= 0 ? "up" : "down"} ${Math.abs(summary.period_over_period_margin_delta_pct).toFixed(1)}% vs previous period`}
      />
    </div>
  );
}
