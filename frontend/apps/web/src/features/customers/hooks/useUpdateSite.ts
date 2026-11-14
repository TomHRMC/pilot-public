/**
 * useUpdateSite — PATCH site mutation hook
 *
 * Location: apps/web/src/features/customers/hooks/useUpdateSite.ts
 *
 * RULE: Uses apiClient (never raw fetch).
 * RULE: onSuccess invalidates ["customer-sites", customerId].
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { SiteResponse } from "./useCustomerSites";
import type { AddressCreateInput } from "./useCreateSite";

export interface SiteUpdateRequest {
  name?: string | null;
  notes?: string | null;
  jurisdiction_code?: string | null;
  address?: AddressCreateInput | null;
  site_type?: "commercial" | "residential" | "industrial" | null;
}

export function useUpdateSite(siteId: string, customerId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: SiteUpdateRequest): Promise<SiteResponse> => {
      const res = await apiClient.patch(`/api/v1/sites/${siteId}`, data);
      return res.data as SiteResponse;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["customer-sites", customerId],
      });
    },
  });
}
