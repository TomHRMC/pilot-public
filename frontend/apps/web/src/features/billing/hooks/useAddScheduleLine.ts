/**
 * useAddScheduleLine — POST /api/v1/payment-schedules/{schedule_id}/lines
 *
 * Location: apps/web/src/features/billing/hooks/useAddScheduleLine.ts
 *
 * BILLING-B1 Part B — Payment Schedule Builder.
 *
 * Adds a draw to a draft schedule. Draft-only: returns 409 if the schedule
 * is no longer draft. The caller uses useOptimisticMutation + <PendingBadge>
 * for the optimistic insert (§16.8), and wraps the underlying call in
 * useStalenessRetry for 409 handling (§16.3).
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

export type PaymentScheduleLineCreate =
  components["schemas"]["PaymentScheduleLineCreate"];

export interface UseAddScheduleLineOptions {
  onSuccess?: (line: PaymentScheduleLineResponse) => void;
  onError?: (error: unknown) => void;
}

export function useAddScheduleLine(options: UseAddScheduleLineOptions = {}) {
  const queryClient = useQueryClient();
  const { onSuccess, onError } = options;

  return useMutation({
    mutationFn: async (params: {
      scheduleId: string;
      payload: PaymentScheduleLineCreate;
    }): Promise<PaymentScheduleLineResponse> => {
      const res = await apiClient.post(
        `/api/v1/payment-schedules/${params.scheduleId}/lines`,
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
