/**
 * useDeleteScheduleLine — DELETE /api/v1/payment-schedules/{schedule_id}/lines/{line_id}
 *
 * Location: apps/web/src/features/billing/hooks/useDeleteScheduleLine.ts
 *
 * BILLING-B1 Part B — Payment Schedule Builder.
 *
 * Soft-deletes a draw (draft only). Returns 409 if the schedule is no
 * longer draft. The caller uses useOptimisticMutation + <PendingBadge>
 * for the optimistic removal (§16.8), and wraps the underlying call in
 * useStalenessRetry for 409 handling (§16.3).
 *
 * RULE: Uses apiClient (never raw fetch). Types from @pilot/shared-types.
 * RULE: Invalidate (don't hand-patch) in onSettled — Rule 12 / §33.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { paymentScheduleKeys } from "./usePaymentSchedule";

export interface UseDeleteScheduleLineOptions {
  onSuccess?: () => void;
  onError?: (error: unknown) => void;
}

export function useDeleteScheduleLine(
  options: UseDeleteScheduleLineOptions = {},
) {
  const queryClient = useQueryClient();
  const { onSuccess, onError } = options;

  return useMutation({
    mutationFn: async (params: {
      scheduleId: string;
      lineId: string;
    }): Promise<void> => {
      await apiClient.delete(
        `/api/v1/payment-schedules/${params.scheduleId}/lines/${params.lineId}`,
      );
    },
    onSuccess: () => {
      onSuccess?.();
    },
    onError: (error) => {
      onError?.(error);
    },
    onSettled: (_data, _error, variables) => {
      void queryClient.invalidateQueries({
        queryKey: paymentScheduleKeys.detail(variables.scheduleId),
      });
    },
  });
}
