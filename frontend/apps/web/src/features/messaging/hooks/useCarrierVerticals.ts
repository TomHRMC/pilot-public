"use client";

/**
 * useCarrierVerticals — GET /api/v1/tenants/{tenant_id}/messaging/verticals
 *
 * Location: apps/web/src/features/messaging/hooks/useCarrierVerticals.ts
 *
 * C-B9: Returns valid business verticals from the carrier's 10DLC API.
 * Cached for 1 hour (staleTime: 3600000) — verticals rarely change.
 *
 * RULE 2: uses apiClient, never raw fetch().
 * RULE 12: TanStack Query v5 object-form, colocated query key.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { useAuth } from "@pilot/ui/auth";
import type { components } from "@pilot/shared-types";

type VerticalsResponse = components["schemas"]["VerticalsResponse"];

export const CARRIER_VERTICALS_QUERY_KEY = ["messaging", "verticals"] as const;

export function useCarrierVerticals() {
  const { user } = useAuth();
  const tenantId = user?.tenantId;

  return useQuery<VerticalsResponse>({
    queryKey: CARRIER_VERTICALS_QUERY_KEY,
    queryFn: async () => {
      if (!tenantId) throw new Error("No tenant ID");
      const res = await apiClient.get<VerticalsResponse>(
        `/api/v1/tenants/${tenantId}/messaging/verticals`,
      );
      return res.data;
    },
    enabled: !!tenantId,
    staleTime: 3_600_000, // 1 hour — verticals rarely change
    retry: false,
  });
}
