/**
 * useCreateChangeOrder — TanStack mutation for creating a change order
 *
 * Location: apps/web/src/features/jobs/hooks/useCreateChangeOrder.ts
 *
 * POST /api/v1/jobs/{jobId}/change-orders
 * onSuccess: invalidate ['job-change-orders', jobId]
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { JOB_CHANGE_ORDERS_QUERY_KEY } from "./useJobChangeOrders";
import type { ChangeOrderResponse } from "./useJobChangeOrders";

export interface CreateChangeOrderInput {
  description: string;
}

export function useCreateChangeOrder(jobId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      input: CreateChangeOrderInput,
    ): Promise<ChangeOrderResponse> => {
      const res = await apiClient.post(
        `/api/v1/jobs/${jobId}/change-orders`,
        input,
      );
      return res.data as ChangeOrderResponse;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: JOB_CHANGE_ORDERS_QUERY_KEY(jobId),
      });
    },
  });
}
