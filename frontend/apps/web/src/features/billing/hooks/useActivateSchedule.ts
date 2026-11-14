/**
 * useActivateSchedule — POST /api/v1/payment-schedules/{schedule_id}/activate
 *
 * Location: apps/web/src/features/billing/hooks/useActivateSchedule.ts
 *
 * BILLING-B1 Part B — Payment Schedule Builder.
 *
 * Validates sum reconciliation → sets status='active'. Returns 422 if
 * residual_cents !== 0 (defense in depth — the client already gates this).
 * The caller surfaces 422s via <NotificationBanner> fault severity with
 * the RFC 7807 detail (§16.4 / design spec §3.12).
 *
 * RULE: Uses apiClient (never raw fetch). Types from @pilot/shared-types.
 * RULE: Invalidate (don't hand-patch) in onSettled — Rule 12 / §33.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient, isAxiosError } from "@pilot/shared-api";
import {
  paymentScheduleKeys,
  type PaymentScheduleResponse,
} from "./usePaymentSchedule";

export interface UseActivateScheduleOptions {
  onSuccess?: (schedule: PaymentScheduleResponse) => void;
  /** Called when the backend returns 422 (residual !== 0) with the RFC 7807 detail */
  onResidualMismatch?: (detail: string) => void;
  onError?: (error: unknown) => void;
}

export function useActivateSchedule(options: UseActivateScheduleOptions = {}) {
  const queryClient = useQueryClient();
  const { onSuccess, onResidualMismatch, onError } = options;

  return useMutation({
    mutationFn: async (
      scheduleId: string,
    ): Promise<PaymentScheduleResponse> => {
      try {
        const res = await apiClient.post(
          `/api/v1/payment-schedules/${scheduleId}/activate`,
          {},
        );
        return res.data as PaymentScheduleResponse;
      } catch (err) {
        if (isAxiosError(err) && err.response?.status === 422) {
          const detail =
            (err.response.data as { detail?: string } | undefined)?.detail ??
            "Draws must sum to the contract total before activating.";
          onResidualMismatch?.(detail);
        }
        throw err;
      }
    },
    onSuccess: (schedule) => {
      onSuccess?.(schedule);
    },
    onError: (error) => {
      // 422 is already handled via onResidualMismatch; only surface other errors
      if (!isAxiosError(error) || error.response?.status !== 422) {
        onError?.(error);
      }
    },
    onSettled: (_data, _error, scheduleId) => {
      void queryClient.invalidateQueries({
        queryKey: paymentScheduleKeys.detail(scheduleId),
      });
    },
  });
}
