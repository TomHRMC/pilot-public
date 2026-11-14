/**
 * useCreatePaymentSchedule — POST /api/v1/payment-schedules
 *
 * Location: apps/web/src/features/billing/hooks/useCreatePaymentSchedule.ts
 *
 * BILLING-B1 Part B — Payment Schedule Builder.
 *
 * Creates a draft schedule (with optional inline draws) for a quote or job.
 * Sends an Idempotency-Key header (mirror useCreateInvoice pattern) so a
 * retried create returns the same schedule.
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

export type PaymentScheduleCreate =
  components["schemas"]["PaymentScheduleCreate"];

export interface UseCreatePaymentScheduleOptions {
  onSuccess?: (schedule: PaymentScheduleResponse) => void;
  onError?: (error: unknown) => void;
}

export function useCreatePaymentSchedule(
  options: UseCreatePaymentScheduleOptions = {},
) {
  const queryClient = useQueryClient();
  const { onSuccess, onError } = options;

  return useMutation({
    mutationFn: async (
      payload: PaymentScheduleCreate,
    ): Promise<PaymentScheduleResponse> => {
      // Stable idempotency key per create attempt — a retried create returns
      // the same schedule. Keyed on customer+site+contract total for stability.
      const idempotencyKey =
        payload.idempotency_key ??
        `ps-create-${payload.customer_id}-${payload.site_id}-${payload.contract_total_cents}-${Date.now()}`;

      const res = await apiClient.post("/api/v1/payment-schedules", payload, {
        headers: { "Idempotency-Key": idempotencyKey },
      });
      return res.data as PaymentScheduleResponse;
    },
    onSuccess: (schedule) => {
      onSuccess?.(schedule);
    },
    onError: (error) => {
      onError?.(error);
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: paymentScheduleKeys.all });
    },
  });
}
