/**
 * usePaymentSchedule — GET /api/v1/payment-schedules/{schedule_id}
 *
 * Location: apps/web/src/features/billing/hooks/usePaymentSchedule.ts
 *
 * BILLING-B1 Part B — Payment Schedule Builder.
 *
 * RULE: Uses apiClient (never raw fetch). Types from @pilot/shared-types.
 * RULE: TQ v5 object-form; colocated query keys including every variable.
 *
 * Returns the full schedule with lines + computed reconciliation totals
 * (scheduled_total_cents, residual_cents). The UI displays these verbatim —
 * never recomputes them (design doc §F).
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";

export type PaymentScheduleResponse =
  components["schemas"]["PaymentScheduleResponse"];
export type PaymentScheduleLineResponse =
  components["schemas"]["PaymentScheduleLineResponse"];

/**
 * Query-key factory for payment schedules.
 * Colocated here per Rule 12 (§33). Every variable the queryFn reads
 * is included in the key array so caches stay isolated and refetch correctly.
 */
export const paymentScheduleKeys = {
  all: ["payment-schedules"] as const,
  list: (params: {
    quote_id?: string;
    job_id?: string;
    limit?: number;
    offset?: number;
  }) => [...paymentScheduleKeys.all, "list", params] as const,
  detail: (id: string) => [...paymentScheduleKeys.all, "detail", id] as const,
};

interface UsePaymentScheduleOptions {
  enabled?: boolean;
}

export function usePaymentSchedule(
  scheduleId: string,
  options: UsePaymentScheduleOptions = {},
) {
  const { enabled = true } = options;
  return useQuery({
    queryKey: paymentScheduleKeys.detail(scheduleId),
    queryFn: async (): Promise<PaymentScheduleResponse> => {
      const res = await apiClient.get(
        `/api/v1/payment-schedules/${scheduleId}`,
      );
      return res.data as PaymentScheduleResponse;
    },
    enabled: enabled && Boolean(scheduleId),
    staleTime: 0,
  });
}
