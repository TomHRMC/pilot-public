/**
 * useUpdateScheduleLine — PATCH /api/v1/payment-schedules/{schedule_id}/lines/{line_id}
 *
 * Location: apps/web/src/features/billing/hooks/useUpdateScheduleLine.ts
 *
 * BILLING-B1 Part B — Payment Schedule Builder.
 *
 * Edits/reorders a draw (draft only). Returns 409 if the schedule is no
 * longer draft. The caller wraps this in useStalenessRetry (§16.3) so a
 * 409 routes to <StalenessRefreshDialog>.
 *
 * RULE: Uses apiClient (never raw fetch). Types from @pilot/shared-types.
 * RULE: Invalidate (don't hand-patch) in onSettled — Rule 12 / §33.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";
import {
  paymentScheduleKeys,
  type PaymentScheduleLineResponse,
} from "./usePaymentSchedule";

export type PaymentScheduleLineUpdate =
  components["schemas"]["PaymentScheduleLineUpdate"];

export interface UseUpdateScheduleLineOptions {
  onSuccess?: (line: PaymentScheduleLineResponse) => void;
  onError?: (error: unknown) => void;
}

export function useUpdateScheduleLine(
  options: UseUpdateScheduleLineOptions = {},
) {
  const queryClient = useQueryClient();
  const { onSuccess, onError } = options;

  return useMutation({
    mutationFn: async (params: {
      scheduleId: string;
      lineId: string;
      payload: PaymentScheduleLineUpdate;
    }): Promise<PaymentScheduleLineResponse> => {
      const res = await apiClient.patch(
        `/api/v1/payment-schedules/${params.scheduleId}/lines/${params.lineId}`,
        params.payload,
      );
      return res.data as PaymentScheduleLineResponse;
    },
    onSuccess: (line) => {
      onSuccess?.(line);
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
