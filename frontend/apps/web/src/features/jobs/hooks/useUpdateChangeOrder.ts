/**
 * useUpdateChangeOrder — TanStack mutation for updating a change order
 *
 * Location: apps/web/src/features/jobs/hooks/useUpdateChangeOrder.ts
 *
 * PATCH /api/v1/jobs/{jobId}/change-orders/{coId}
 * onSuccess: invalidate ['job-change-orders', jobId]
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { JOB_CHANGE_ORDERS_QUERY_KEY } from "./useJobChangeOrders";
import type { ChangeOrderResponse } from "./useJobChangeOrders";

export interface UpdateChangeOrderInput {
  description?: string;
  is_active?: boolean;
}

export function useUpdateChangeOrder(jobId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      coId,
      input,
    }: {
      coId: string;
      input: UpdateChangeOrderInput;
    }): Promise<ChangeOrderResponse> => {
      const res = await apiClient.patch(
        `/api/v1/jobs/${jobId}/change-orders/${coId}`,
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
