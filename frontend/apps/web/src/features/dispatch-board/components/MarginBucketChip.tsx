/**
 * MarginBucketChip — Color chip encoding the margin bucket
 *
 * Location: apps/web/src/features/dispatch-board/components/MarginBucketChip.tsx
 *
 * Four buckets: below-low (red), low (amber), medium (green), high (deep green).
 * Reads margin_bucket from API. Token colors only — no hardcoded hex.
 *
 * Per batch-fe-b4-design.md §A.2.5 §G.7
 */

import React from "react";

type MarginBucket = "below-low" | "low" | "medium" | "high";

interface MarginBucketChipProps {
  bucket: MarginBucket;
  marginPct: number;
}

interface BucketVisual {
  bgClass: string;
  textClass: string;
  label: string;
}

const BUCKET_VISUALS: Record<MarginBucket, BucketVisual> = {
  "below-low": {
    bgClass: "bg-fault-50",
    textClass: "text-fault-600",
    label: "Below target",
  },
  low: {
    bgClass: "bg-alert-50",
    textClass: "text-alert-600",
    label: "Low margin",
  },
  medium: {
    bgClass: "bg-margin-50",
    textClass: "text-margin-600",
    label: "On target",
  },
  high: {
    bgClass: "bg-margin-100",
    textClass: "text-margin-800",
    label: "Strong margin",
  },
} as const;

/**
 * MarginBucketChip
 *
 * Small colored chip showing the job's margin bucket and percentage.
 * Uses Pass 1 token classes only.
 */
export function MarginBucketChip({ bucket, marginPct }: MarginBucketChipProps) {
  const visual = BUCKET_VISUALS[bucket];

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-caption font-medium ${visual.bgClass} ${visual.textClass}`}
      aria-label={`Margin: ${marginPct.toFixed(1)}% — ${visual.label}`}
    >
      <span>{marginPct.toFixed(1)}%</span>
      <span className="opacity-70">{visual.label}</span>
    </span>
  );
}
