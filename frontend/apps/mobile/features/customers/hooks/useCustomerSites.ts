/**
 * useCustomerSites — TanStack Query hook for a customer's sites
 *
 * Location: apps/mobile/features/customers/hooks/useCustomerSites.ts
 *
 * API: GET /api/v1/sites/?customer_id={customerId}&limit=20
 * Query key: ['customer-sites', customerId]
 * Cache: staleTime: 60_000
 *
 * Design doc Section F.3 (MOB-B3)
 *
 * AddressResponse shape (verified from openapi.json):
 *   { id, line1, line2, line3, city, state, postal_code, country,
 *     latitude, longitude, is_active, created_at, updated_at }
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface SiteAddress {
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

export interface CustomerSite {
  id: string;
  tenant_id: string;
  customer_id: string;
  name: string | null;
  notes: string | null;
  jurisdiction_code: string | null;
  is_active: boolean;
  address: SiteAddress | null;
}

export function useCustomerSites(customerId: string) {
  const query = useQuery({
    queryKey: ["customer-sites", customerId],
    queryFn: async () => {
      const { data } = await apiClient.get<CustomerSite[]>("/api/v1/sites/", {
        params: { customer_id: customerId, limit: 20 },
      });
      return data;
    },
    staleTime: 60_000,
    enabled: Boolean(customerId),
  });

  return {
    sites: query.data ?? [],
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
  };
}
