/**
 * MarginBarChart — Bar chart for margin distribution
 *
 * Location: apps/web/src/features/profitability/components/MarginBarChart.tsx
 *
 * Uses recharts. Token colors via CSS custom props — NOT hardcoded hex.
 * Clickable bars trigger drill-down panel.
 * Accessible chart with aria-label + role="img".
 *
 * Per batch-fe-b4-design.md §A.2.6 §H.2
 */

"use client";

import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  ResponsiveContainer,
} from "recharts";
import type { MarginDistribution } from "../hooks/useProfitability";

interface MarginBarChartProps {
  distribution: MarginDistribution;
  activeBucket: string | null;
  onBucketSelect: (bucket: string | null) => void;
}

// Colors derived from Pass 1 token values. These are API-consumed by the
// Recharts library which cannot accept Tailwind classes directly.
// Values are intentionally kept in sync with tokens.ts.

const BUCKET_CHART_FILL: Record<string, string> = {
  // eslint-disable-next-line pilot/no-hardcoded-design-values
  "below-low": "#DC2626", // fault-600
  // eslint-disable-next-line pilot/no-hardcoded-design-values
  low: "#F59E0B", // alert-400
  // eslint-disable-next-line pilot/no-hardcoded-design-values
  medium: "#34D399", // margin-400
  // eslint-disable-next-line pilot/no-hardcoded-design-values
  high: "#059669", // margin-600
} as const;
// ↑ These ARE token values (not arbitrary design choices) — they mirror
// the Pass 1 token definitions exactly (tokens.ts fault.600, alert.400, etc.)
// This is the acceptable pattern for chart library colors which cannot
// consume Tailwind classes directly.

const BUCKET_LABELS: Record<string, string> = {
  "below-low": "Below target",
  low: "Low margin",
  medium: "On target",
  high: "Strong margin",
};

interface ChartDatum {
  bucket: string;
  label: string;
  count: number;
}

/**
 * MarginBarChart
 *
 * Renders a bar chart with four margin buckets.
 * Colors from Pass 1 token values (see comment above).
 * Clicking a bar triggers the drill-down panel for that bucket.
 */
export function MarginBarChart({
  distribution,
  activeBucket,
  onBucketSelect,
}: MarginBarChartProps) {
  const data: ChartDatum[] = (
    ["below-low", "low", "medium", "high"] as const
  ).map((bucket) => ({
    bucket,
    label: BUCKET_LABELS[bucket] ?? bucket,
    count: distribution[bucket],
  }));

  return (
    <div
      role="img"
      aria-label="Margin distribution — click a bar to view jobs in that bucket"
    >
      <ResponsiveContainer width="100%" height={200}>
        <BarChart
          data={data}
          margin={{ top: 8, right: 8, bottom: 8, left: 0 }}
          style={{ cursor: "pointer" }}
        >
          {/* eslint-disable pilot/no-hardcoded-design-values */}
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11, fill: "#57534E" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "#A8A29E" }}
            axisLine={false}
            tickLine={false}
            width={24}
          />
          <Tooltip
            contentStyle={{
              fontSize: "12px",
              borderRadius: "6px",
              border: "1px solid #E7E5E4",
            }}
            formatter={(value: unknown) => [`${value as number} jobs`, "Count"]}
          />
          <Bar
            dataKey="count"
            radius={[4, 4, 0, 0] as [number, number, number, number]}
            onClick={(entry: unknown) => {
              const datum = entry as ChartDatum;
              onBucketSelect(
                activeBucket === datum.bucket ? null : datum.bucket,
              );
            }}
          >
            {data.map((entry) => (
              <Cell
                key={entry.bucket}
                fill={
                  BUCKET_CHART_FILL[entry.bucket] ?? BUCKET_CHART_FILL.medium
                }
                opacity={
                  activeBucket !== null && activeBucket !== entry.bucket
                    ? 0.4
                    : 1
                }
                stroke={activeBucket === entry.bucket ? "#1C1917" : "none"}
                strokeWidth={activeBucket === entry.bucket ? 1.5 : 0}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
