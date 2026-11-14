"use client";

/**
 * useExtendFreePeriod — POST /api/v1/operator/cohort/{tenant_id}/extend
 *
 * Location: apps/web/src/features/operator/hooks/useExtendFreePeriod.ts
 *
 * C-B11 Part B: Silently extends a Charter member's free period.
 * Sets override_free_period_ends_at + override_reason, calls Stripe.
 * No customer notification (D16).
 *
 * On success: invalidates the cohort overview query (refresh the table).
 * retry: false — operator sees the error immediately.
 *
 * RULE 2: uses apiClient, never raw fetch().
 * RULE 12: TanStack Query v5 object-form.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";
import { COHORT_OVERVIEW_QUERY_KEY } from "./useCohortOverview";

type ExtendFreePeriodRequest = components["schemas"]["ExtendFreePeriodRequest"];
type ExtendFreePeriodResponse =
  components["schemas"]["ExtendFreePeriodResponse"];

export interface ExtendFreePeriodVariables {
  tenantId: string;
  newFreePeriodEndsAt: string;
  overrideReason: string;
}

export function useExtendFreePeriod() {
  const queryClient = useQueryClient();

  return useMutation<
    ExtendFreePeriodResponse,
    unknown,
    ExtendFreePeriodVariables
  >({
    mutationFn: async (vars) => {
      const res = await apiClient.post<ExtendFreePeriodResponse>(
        `/api/v1/operator/cohort/${vars.tenantId}/extend`,
        {
          new_free_period_ends_at: vars.newFreePeriodEndsAt,
          override_reason: vars.overrideReason,
        } satisfies ExtendFreePeriodRequest,
      );
      return res.data;
    },
    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: COHORT_OVERVIEW_QUERY_KEY,
      });
    },
    retry: false,
  });
}
