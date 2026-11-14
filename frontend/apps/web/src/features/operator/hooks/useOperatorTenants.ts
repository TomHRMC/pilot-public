"use client";

/**
 * useOperatorTenants — GET /api/v1/operator/tenants
 *
 * Location: apps/web/src/features/operator/hooks/useOperatorTenants.ts
 *
 * C-B15 Part B: Fetches the tenant list for the operator tenant selector.
 * All tenants (not just Charter), active first, alphabetical. No pagination
 * at MVP scale (< 200 tenants).
 *
 * RULE 1.1: endpoint verified in openapi_schema_map.md.
 * RULE 2: uses apiClient, never raw fetch().
 * RULE 12: TanStack Query v5 object-form, colocated query key.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";

type OperatorTenantListResponse =
  components["schemas"]["OperatorTenantListResponse"];

export const OPERATOR_TENANTS_QUERY_KEY = ["operator-tenants"] as const;

export function useOperatorTenants() {
  return useQuery<OperatorTenantListResponse>({
    queryKey: OPERATOR_TENANTS_QUERY_KEY,
    queryFn: async () => {
      const res = await apiClient.get<OperatorTenantListResponse>(
        "/api/v1/operator/tenants",
      );
      return res.data;
    },
    // Reference data — doesn't change frequently. 5-minute stale time
    // prevents hammering the API on every selector open.
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}
