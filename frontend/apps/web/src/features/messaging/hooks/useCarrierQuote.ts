"use client";

/**
 * useCarrierQuote — GET /api/v1/tenants/{tenant_id}/messaging/quote
 *
 * Location: apps/web/src/features/messaging/hooks/useCarrierQuote.ts
 *
 * C-B9: Fetches the itemized 10DLC carrier cost quote. Reused from C-B8.
 * The quote is also embedded in the ProvisionResponse and RetryResponse,
 * but this standalone hook is used when the page needs to re-fetch the
 * quote independently (e.g., after a fee schedule change).
 *
 * RULE 2: uses apiClient, never raw fetch().
 * RULE 12: TanStack Query v5 object-form, colocated query key.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { useAuth } from "@pilot/ui/auth";
import type { components } from "@pilot/shared-types";

type CarrierQuoteResponse = components["schemas"]["CarrierQuoteResponse"];

export const CARRIER_QUOTE_QUERY_KEY = ["messaging", "quote"] as const;

export function useCarrierQuote() {
  const { user } = useAuth();
  const tenantId = user?.tenantId;

  return useQuery<CarrierQuoteResponse>({
    queryKey: CARRIER_QUOTE_QUERY_KEY,
    queryFn: async () => {
      if (!tenantId) throw new Error("No tenant ID");
      const res = await apiClient.get<CarrierQuoteResponse>(
        `/api/v1/tenants/${tenantId}/messaging/quote`,
      );
      return res.data;
    },
    enabled: !!tenantId,
    retry: false,
    staleTime: 60_000,
  });
}
