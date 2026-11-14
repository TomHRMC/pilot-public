"use client";

/**
 * useAvailablePhoneNumbers — GET /api/v1/tenants/{tenant_id}/messaging/available-numbers
 *
 * Location: apps/web/src/features/messaging/hooks/useAvailablePhoneNumbers.ts
 *
 * C-B9: Returns available phone numbers for a given area code from the carrier.
 * Enabled only when an area code is provided.
 *
 * RULE 2: uses apiClient, never raw fetch().
 * RULE 12: TanStack Query v5 object-form, colocated query key.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { useAuth } from "@pilot/ui/auth";
import type { components } from "@pilot/shared-types";

type AvailableNumbersResponse =
  components["schemas"]["AvailableNumbersResponse"];

export const AVAILABLE_NUMBERS_QUERY_KEY = [
  "messaging",
  "available-numbers",
] as const;

export function useAvailablePhoneNumbers(areaCode: string | null) {
  const { user } = useAuth();
  const tenantId = user?.tenantId;

  return useQuery<AvailableNumbersResponse>({
    queryKey: [...AVAILABLE_NUMBERS_QUERY_KEY, areaCode],
    queryFn: async () => {
      if (!tenantId || !areaCode)
        throw new Error("Missing tenant ID or area code");
      const res = await apiClient.get<AvailableNumbersResponse>(
        `/api/v1/tenants/${tenantId}/messaging/available-numbers`,
        { params: { area_code: areaCode, limit: 10 } },
      );
      return res.data;
    },
    enabled: !!tenantId && !!areaCode && areaCode.length === 3,
    retry: false,
  });
}
