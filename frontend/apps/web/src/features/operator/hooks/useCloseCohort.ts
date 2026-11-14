"use client";

/**
 * useCloseCohort — POST /api/v1/operator/cohort/close
 *
 * Location: apps/web/src/features/operator/hooks/useCloseCohort.ts
 *
 * C-B11 Part B: Closes the Charter cohort — archives the Charter price,
 * deactivates the Charter tier, activates trial/starter/teams tiers.
 * Existing members keep their locked rate.
 *
 * On success: invalidates the cohort overview query (cohort_is_active
 * becomes false, button hides).
 * retry: false.
 *
 * RULE 2: uses apiClient, never raw fetch().
 * RULE 12: TanStack Query v5 object-form.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";
import { COHORT_OVERVIEW_QUERY_KEY } from "./useCohortOverview";

type CloseCohortResponse = components["schemas"]["CloseCohortResponse"];

export function useCloseCohort() {
  const queryClient = useQueryClient();

  return useMutation<CloseCohortResponse, unknown, void>({
    mutationFn: async () => {
      const res = await apiClient.post<CloseCohortResponse>(
        "/api/v1/operator/cohort/close",
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
