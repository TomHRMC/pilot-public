/**
 * useCustomers — TanStack Query hook for the customer list
 *
 * Location: apps/mobile/features/customers/hooks/useCustomers.ts
 *
 * API: GET /api/v1/customers/?search={query}&limit=50
 * Query key: ['customers', searchQuery]
 * Cache: staleTime: 60_000 (customer list changes infrequently)
 *
 * Design doc Section F.1 (MOB-B3)
 *
 * Note: Debouncing is handled by CustomersTabScreen — this hook
 * receives the already-debounced query string.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface CustomerListItem {
  id: string;
  tenant_id: string;
  type: string; // "residential" | "commercial"
  display_name: string;
  first_name: string | null;
  last_name: string | null;
  company_name: string | null;
  email: string | null;
}

interface PaginatedCustomerResponse {
  items: CustomerListItem[];
  total: number;
  limit: number;
  offset: number;
}

export function useCustomers(searchQuery: string = "") {
  const query = useQuery({
    queryKey: ["customers", searchQuery],
    queryFn: async () => {
      const params: Record<string, unknown> = { limit: 50 };
      if (searchQuery.trim()) {
        params.search = searchQuery.trim();
      }
      const { data } = await apiClient.get<PaginatedCustomerResponse>(
        "/api/v1/customers/",
        { params },
      );
      // Backend returns PaginatedCustomerResponse { items, total, limit, offset }
      return data.items ?? [];
    },
    staleTime: 60_000,
  });

  return {
    customers: query.data ?? [],
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    isFetching: query.isFetching,
  };
}
