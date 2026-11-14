/**
 * useCreateSite — POST site mutation hook
 *
 * Location: apps/web/src/features/customers/hooks/useCreateSite.ts
 *
 * RULE: Uses apiClient (never raw fetch).
 * RULE: onSuccess invalidates ["customer-sites", customerId].
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { SiteResponse } from "./useCustomerSites";

export interface AddressCreateInput {
  line1?: string | null;
  line2?: string | null;
  line3?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  country?: string;
}

export interface SiteCreateRequest {
  customer_id: string;
  name?: string | null;
  notes?: string | null;
  jurisdiction_code?: string | null;
  address?: AddressCreateInput | null;
  site_type?: "commercial" | "residential" | "industrial" | null;
}

export function useCreateSite(customerId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: SiteCreateRequest): Promise<SiteResponse> => {
      const res = await apiClient.post("/api/v1/sites/", data);
      return res.data as SiteResponse;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["customer-sites", customerId],
      });
    },
  });
}
