/**
 * useDeleteChangeOrder — TanStack mutation for deleting a change order
 *
 * Location: apps/web/src/features/jobs/hooks/useDeleteChangeOrder.ts
 *
 * DELETE /api/v1/jobs/{jobId}/change-orders/{coId}
 * onSuccess: invalidate ['job-change-orders', jobId]
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { JOB_CHANGE_ORDERS_QUERY_KEY } from "./useJobChangeOrders";

export function useDeleteChangeOrder(jobId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (coId: string): Promise<void> => {
      await apiClient.delete(`/api/v1/jobs/${jobId}/change-orders/${coId}`);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: JOB_CHANGE_ORDERS_QUERY_KEY(jobId),
      });
    },
  });
}
