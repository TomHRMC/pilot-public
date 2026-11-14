/**
 * useAddExpense — TanStack mutation for adding an expense to a job
 *
 * Location: apps/web/src/features/jobs/hooks/useAddExpense.ts
 *
 * POST /api/v1/jobs/{jobId}/expenses
 * onSuccess: invalidate ['job-expenses', jobId]
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { JOB_EXPENSES_QUERY_KEY } from "./useJobExpenses";
import type { JobExpenseResponse } from "./useJobExpenses";

export interface AddExpenseInput {
  job_expense_category_code: string;
  description: string;
  vendor_name?: string | null;
  incurred_at: string;
  cost_cents: number;
  is_billable?: boolean;
}

export function useAddExpense(jobId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: AddExpenseInput): Promise<JobExpenseResponse> => {
      const res = await apiClient.post(`/api/v1/jobs/${jobId}/expenses`, input);
      return res.data as JobExpenseResponse;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: JOB_EXPENSES_QUERY_KEY(jobId),
      });
    },
  });
}
