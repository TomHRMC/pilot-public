/**
 * useProjectedMargin — Fetches projected margin for a job
 *
 * Location: apps/mobile/features/jobs/hooks/useProjectedMargin.ts
 *
 * Calls GET /api/v1/jobs/{jobId}/projected-margin
 *
 * Response shape: open object (openapi.json shows additionalProperties: true,
 * no named schema "ProjectedMarginResponse"). Type is Record<string, unknown>.
 * Known fields from backend service: margin_percent, quoted_hours, actual_hours,
 * cost_delta_cents, etc_hours_remaining.
 *
 * Refreshes every time the screen gains focus via useFocusEffect.
 * staleTime: 0 — always fresh on focus (live profitability requirement).
 *
 * Per batch-mob-b2-design.md §F.2 and §D.7.
 */

import { useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { useFocusEffect } from "expo-router";
import { apiClient } from "@pilot/shared-api";

// ── Open response type (no named schema in openapi.json) ──────────────────────

export interface ProjectedMarginData {
  margin_percent?: number | null;
  quoted_hours?: number | null;
  actual_hours?: number | null;
  cost_delta_cents?: number | null;
  etc_hours_remaining?: number | null;
  [key: string]: unknown;
}

export interface UseProjectedMarginReturn {
  data: ProjectedMarginData | undefined;
  isLoading: boolean;
  isError: boolean;
  refetch: () => void;
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useProjectedMargin(jobId: string): UseProjectedMarginReturn {
  const query = useQuery({
    queryKey: ["job-projected-margin", jobId] as const,
    queryFn: () =>
      apiClient
        .get<ProjectedMarginData>(`/api/v1/jobs/${jobId}/projected-margin`)
        .then((r) => r.data),
    enabled: !!jobId,
    staleTime: 0, // Always fresh on focus — live profitability requirement
  });

  // Refresh every time screen gains focus
  useFocusEffect(
    useCallback(() => {
      if (jobId) {
        void query.refetch();
      }
    }, [jobId, query.refetch]),
  );

  return {
    data: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    refetch: query.refetch,
  };
}
