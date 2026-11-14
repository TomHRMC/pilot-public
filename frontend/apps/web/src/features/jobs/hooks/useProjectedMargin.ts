/**
 * useProjectedMargin — TanStack Query hook for job projected margin
 *
 * Location: apps/web/src/features/jobs/hooks/useProjectedMargin.ts
 *
 * GET /api/v1/jobs/{jobId}/projected-margin
 * Query key: ['job-projected-margin', jobId]
 *
 * Response is free-form JSON from backend (additionalProperties: true).
 * We use the shape returned by the existing MSW mock (established in FE-B4).
 * staleTime: 15_000 — refresh more often than static data
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export type MarginBucket = "below-low" | "low" | "medium" | "high";

export interface ProjectedMarginResponse {
  projected_margin_pct: number;
  cost_to_date_cents: number;
  etc_hours_remaining: number;
  revenue_cents: number;
  margin_bucket: MarginBucket;
  hours_worked: number;
  quoted_hours: number;
}

export const JOB_PROJECTED_MARGIN_QUERY_KEY = (jobId: string) =>
  ["job-projected-margin", jobId] as const;

/** Margin is "above target" if >= 20% (MVP default target) */
export const MARGIN_TARGET_PCT = 20;

export function useProjectedMargin(jobId: string) {
  return useQuery({
    queryKey: JOB_PROJECTED_MARGIN_QUERY_KEY(jobId),
    queryFn: async (): Promise<ProjectedMarginResponse> => {
      const res = await apiClient.get(`/api/v1/jobs/${jobId}/projected-margin`);
      return res.data as ProjectedMarginResponse;
    },
    enabled: !!jobId,
    staleTime: 15_000,
  });
}
