/**
 * useCustomerSites — fetch sites for a customer
 *
 * Location: apps/web/src/features/customers/hooks/useCustomerSites.ts
 *
 * RULE: Uses apiClient (never raw fetch).
 * RULE: Query key is ["customer-sites", customerId].
 * RULE: enabled: !!customerId — do not fetch if undefined.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface AddressResponse {
  id: string;
  line1: string | null;
  line2: string | null;
  line3: string | null;
  city: string | null;
  state: string | null;
  postal_code: string | null;
  country: string;
  latitude: number | null;
  longitude: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SiteResponse {
  id: string;
  tenant_id: string;
  customer_id: string;
  name: string | null;
  notes: string | null;
  jurisdiction_code: string | null;
  is_active: boolean;
  address: AddressResponse | null;
  site_type?: "commercial" | "residential" | "industrial" | null;
}

export const CUSTOMER_SITES_QUERY_KEY = (customerId: string | undefined) =>
  ["customer-sites", customerId] as const;

export function useCustomerSites(customerId: string | undefined) {
  return useQuery({
    queryKey: CUSTOMER_SITES_QUERY_KEY(customerId),
    queryFn: async (): Promise<SiteResponse[]> => {
      const res = await apiClient.get("/api/v1/sites/", {
        params: { customer_id: customerId },
      });
      return res.data as SiteResponse[];
    },
    enabled: !!customerId,
    staleTime: 60_000,
  });
}
