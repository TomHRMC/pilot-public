/**
 * useAtRiskJobs — Dashboard BI hook
 *
 * Location: apps/web/src/features/dashboard/hooks/useAtRiskJobs.ts
 *
 * GET /api/v1/dashboard/at-risk-jobs?limit=5
 * Endpoint verified in backend/openapi_schema_map.md (FE-B23 Part A).
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface AtRiskJobItem {
  job_id: string;
  customer_name: string;
  site_name: string | null;
  status_code: string | null;
  scheduled_start_at: string | null;
  actual_cost_cents: number;
  quoted_budget_cents: number | null;
  projected_margin_pct: number | null;
}

export interface AtRiskJobsResponse {
  jobs: AtRiskJobItem[];
  total: number;
}

export function useAtRiskJobs(limit = 5) {
  return useQuery<AtRiskJobsResponse>({
    queryKey: ["dashboard-at-risk-jobs", limit],
    queryFn: async () => {
      const res = await apiClient.get("/api/v1/dashboard/at-risk-jobs", {
        params: { limit },
      });
      return res.data as AtRiskJobsResponse;
    },
    staleTime: 60_000,
  });
}
