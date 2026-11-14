/**
 * usePaymentSchedules — GET /api/v1/payment-schedules
 *
 * Location: apps/web/src/features/billing/hooks/usePaymentSchedules.ts
 *
 * BILLING-B1 Part B — Payment Schedule Builder.
 *
 * Lists schedules for a quote or job (?quote_id= / ?job_id=).
 * Paginated with limit/offset. Uses placeholderData: keepPreviousData
 * so the list does not flash empty between pages (Rule 12 / §33).
 *
 * RULE: Uses apiClient (never raw fetch). Types from @pilot/shared-types.
 */

import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";
import { paymentScheduleKeys } from "./usePaymentSchedule";

export type PaymentScheduleListResponse =
  components["schemas"]["PaymentScheduleListResponse"];
export type PaymentScheduleListItem =
  components["schemas"]["PaymentScheduleListItem"];

export interface UsePaymentSchedulesOptions {
  quote_id?: string;
  job_id?: string;
  limit?: number;
  offset?: number;
  enabled?: boolean;
}

export function usePaymentSchedules({
  quote_id,
  job_id,
  limit = 50,
  offset = 0,
  enabled = true,
}: UsePaymentSchedulesOptions = {}) {
  return useQuery({
    queryKey: paymentScheduleKeys.list({ quote_id, job_id, limit, offset }),
    queryFn: async (): Promise<PaymentScheduleListResponse> => {
      const res = await apiClient.get("/api/v1/payment-schedules", {
        params: {
          ...(quote_id ? { quote_id } : {}),
          ...(job_id ? { job_id } : {}),
          limit,
          offset,
        },
      });
      return res.data as PaymentScheduleListResponse;
    },
    enabled,
    placeholderData: keepPreviousData,
    staleTime: 30_000,
  });
}
