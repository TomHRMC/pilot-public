/**
 * useArSummary — AR aging summary for dashboard widget
 *
 * Location: apps/web/src/features/dashboard/hooks/useArSummary.ts
 *
 * RULE: Uses apiClient (never raw fetch).
 *
 * GET /api/v1/reports/ar-aging — confirmed to exist (FE-B22 pre-work).
 * Returns ARAgingReportResponse with summary.{current_cents, bucket_31_60_cents, ...}
 *
 * staleTime: 5 minutes (dashboard data ok to be slightly stale)
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface ArAgingSummary {
  current_cents: number;
  bucket_31_60_cents: number;
  bucket_61_90_cents: number;
  bucket_91_plus_cents: number;
  total_outstanding_cents: number;
}

export interface ArAgingReportResponse {
  report_type: string;
  as_of_date: string;
  display_mode: string;
  row_count: number;
  report_chart_threshold: number;
  summary: ArAgingSummary;
  data: unknown[];
}

export const AR_SUMMARY_QUERY_KEY = ["ar-summary"] as const;

export function useArSummary() {
  return useQuery({
    queryKey: AR_SUMMARY_QUERY_KEY,
    queryFn: async (): Promise<ArAgingReportResponse> => {
      const today = new Date();
      const date_to = today.toISOString().split("T")[0];
      // date_from is unused by the AR aging calculation (per API docs)
      // but is required by the endpoint for API consistency — set to 1 year ago
      const oneYearAgo = new Date(today);
      oneYearAgo.setFullYear(today.getFullYear() - 1);
      const date_from = oneYearAgo.toISOString().split("T")[0];

      const res = await apiClient.get("/api/v1/reports/ar-aging", {
        params: { date_from, date_to },
      });
      return res.data as ArAgingReportResponse;
    },
    staleTime: 5 * 60_000,
  });
}
