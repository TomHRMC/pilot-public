/**
 * useUpdateSchedule — PATCH /api/v1/payment-schedules/{schedule_id}
 *
 * Location: apps/web/src/features/billing/hooks/useUpdateSchedule.ts
 *
 * BILLING-B1 Part B — Payment Schedule Builder.
 *
 * Edits the draft schedule header (contract_total_cents, basis_default).
 * Draft-only: a PATCH on a non-draft schedule returns 409. The caller
 * wraps this in useStalenessRetry so a 409 routes to <StalenessRefreshDialog>
 * (§16.3). This hook surfaces 409s via the standard axios error path so the
 * staleness wrapper can detect them.
 *
 * RULE: Uses apiClient (never raw fetch). Types from @pilot/shared-types.
 * RULE: Invalidate (don't hand-patch) in onSettled — Rule 12 / §33.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";
import {
  paymentScheduleKeys,
  type PaymentScheduleResponse,
} from "./usePaymentSchedule";

export type PaymentScheduleUpdate =
  components["schemas"]["PaymentScheduleUpdate"];

export interface UseUpdateScheduleOptions {
  onSuccess?: (schedule: PaymentScheduleResponse) => void;
  onError?: (error: unknown) => void;
}

export function useUpdateSchedule(options: UseUpdateScheduleOptions = {}) {
  const queryClient = useQueryClient();
  const { onSuccess, onError } = options;

  return useMutation({
    mutationFn: async (params: {
      scheduleId: string;
      payload: PaymentScheduleUpdate;
    }): Promise<PaymentScheduleResponse> => {
      const res = await apiClient.patch(
        `/api/v1/payment-schedules/${params.scheduleId}`,
        params.payload,
      );
      return res.data as PaymentScheduleResponse;
    },
    onSuccess: (schedule) => {
      onSuccess?.(schedule);
    },
    onError: (error) => {
      onError?.(error);
    },
    onSettled: (data, _error, variables) => {
      void queryClient.invalidateQueries({
        queryKey: paymentScheduleKeys.detail(variables.scheduleId),
      });
      void queryClient.invalidateQueries({ queryKey: paymentScheduleKeys.all });
    },
  });
}
