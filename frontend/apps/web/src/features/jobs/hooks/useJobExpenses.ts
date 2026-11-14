/**
 * useJobExpenses — TanStack Query hook for job expenses
 *
 * Location: apps/web/src/features/jobs/hooks/useJobExpenses.ts
 *
 * GET /api/v1/jobs/{jobId}/expenses
 * Query key: ['job-expenses', jobId]
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface JobExpenseResponse {
  id: string;
  tenant_id: string;
  job_id: string;
  job_expense_category_code: string;
  description: string;
  vendor_name: string | null;
  incurred_at: string;
  cost_cents: number;
  markup_pct: number;
  markup_amt_cents: number;
  billable_cents: number;
  is_billable: boolean;
}

export const JOB_EXPENSES_QUERY_KEY = (jobId: string) =>
  ["job-expenses", jobId] as const;

export function useJobExpenses(jobId: string) {
  return useQuery({
    queryKey: JOB_EXPENSES_QUERY_KEY(jobId),
    queryFn: async (): Promise<JobExpenseResponse[]> => {
      const res = await apiClient.get(`/api/v1/jobs/${jobId}/expenses`);
      return res.data as JobExpenseResponse[];
    },
    enabled: !!jobId,
    staleTime: 30_000,
  });
}
