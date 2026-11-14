/**
 * useMarginBucketConfig — Tenant margin bucket configuration
 *
 * Location: apps/web/src/features/profitability/hooks/useMarginBucketConfig.ts
 *
 * Reads margin_bucket_boundaries + margin_target_pct from tenant settings API.
 * NOT hardcoded constants — tenant can override per §G.7.
 * Cached once; updates when tenant setting changes.
 *
 * Per batch-fe-b4-design.md §A.2.7 §G.7
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

interface MarginBucketConfig {
  /** e.g. [10, 20, 30] — below-low/low/medium/high boundaries in percent */
  margin_bucket_boundaries: number[];
  /** Default target margin percentage (shown as line on charts) */
  margin_target_pct: number;
}

async function fetchMarginBucketConfig(): Promise<MarginBucketConfig> {
  const res = await apiClient.get("/api/v1/settings/reports");
  return res.data as MarginBucketConfig;
}

export const MARGIN_CONFIG_DEFAULTS: MarginBucketConfig = {
  margin_bucket_boundaries: [10, 20, 30],
  margin_target_pct: 20,
};

/**
 * Get the margin bucket for a given margin percentage.
 * Boundaries come from tenant settings, not hardcoded.
 */
export function getMarginBucket(
  marginPct: number,
  boundaries: number[] = MARGIN_CONFIG_DEFAULTS.margin_bucket_boundaries,
): "below-low" | "low" | "medium" | "high" {
  if (marginPct < (boundaries[0] ?? 10)) return "below-low";
  if (marginPct < (boundaries[1] ?? 20)) return "low";
  if (marginPct < (boundaries[2] ?? 30)) return "medium";
  return "high";
}

export function useMarginBucketConfig() {
  return useQuery({
    queryKey: ["margin-bucket-config"],
    queryFn: fetchMarginBucketConfig,
    staleTime: 10 * 60_000, // 10 minutes — tenant settings rarely change
    initialData: MARGIN_CONFIG_DEFAULTS,
  });
}
