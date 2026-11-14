/**
 * useJobChangeOrders — TanStack Query hook for job change orders
 *
 * Location: apps/web/src/features/jobs/hooks/useJobChangeOrders.ts
 *
 * GET /api/v1/jobs/{jobId}/change-orders
 * Query key: ['job-change-orders', jobId]
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface ChangeOrderResponse {
  id: string;
  tenant_id: string;
  job_id: string;
  description: string;
  subtotal_cents: number;
  tax_cents: number;
  total_cents: number;
  is_active: boolean;
}

export const JOB_CHANGE_ORDERS_QUERY_KEY = (jobId: string) =>
  ["job-change-orders", jobId] as const;

export function useJobChangeOrders(jobId: string) {
  return useQuery({
    queryKey: JOB_CHANGE_ORDERS_QUERY_KEY(jobId),
    queryFn: async (): Promise<ChangeOrderResponse[]> => {
      const res = await apiClient.get(`/api/v1/jobs/${jobId}/change-orders`);
      return res.data as ChangeOrderResponse[];
    },
    enabled: !!jobId,
    staleTime: 30_000,
  });
}
