"use client";

/**
 * useCohortOverview — GET /api/v1/operator/cohort
 *
 * Location: apps/web/src/features/operator/hooks/useCohortOverview.ts
 *
 * C-B11 Part B: Fetches all Charter members with tripwire alert data.
 * Returns cohort tier metadata + member list.
 *
 * RULE 2: uses apiClient, never raw fetch().
 * RULE 12: TanStack Query v5 object-form, colocated query key.
 */

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";

export type CohortOverviewResponse =
  components["schemas"]["CohortOverviewResponse"];

export const COHORT_OVERVIEW_QUERY_KEY = ["operator", "cohort"] as const;

export function useCohortOverview() {
  const queryClient = useQueryClient();

  const query = useQuery<CohortOverviewResponse>({
    queryKey: COHORT_OVERVIEW_QUERY_KEY,
    queryFn: async () => {
      const res = await apiClient.get<CohortOverviewResponse>(
        "/api/v1/operator/cohort",
      );
      return res.data;
    },
    // Operator checks periodically, not real-time
    staleTime: 30 * 1000,
    retry: false,
  });

  return {
    ...query,
    /** Invalidate the cohort overview query (used by mutations in onSettled). */
    invalidate: () =>
      queryClient.invalidateQueries({ queryKey: COHORT_OVERVIEW_QUERY_KEY }),
  };
}
