/**
 * useCustomerDetail — TanStack Query hook for a single customer
 *
 * Location: apps/mobile/features/customers/hooks/useCustomerDetail.ts
 *
 * API: GET /api/v1/customers/{customer_id}
 * Query key: ['customer-detail', customerId]
 * Cache: staleTime: 60_000
 *
 * Design doc Section F.2 (MOB-B3)
 *
 * NOTE: CustomerResponse does NOT include mobile_phone or preferred_contact_channel.
 * Only { id, tenant_id, type, display_name, first_name, last_name, company_name, email }
 * are available. See design doc §A.2.1, §G.1.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { CustomerListItem } from "./useCustomers";

export function useCustomerDetail(customerId: string) {
  const query = useQuery({
    queryKey: ["customer-detail", customerId],
    queryFn: async () => {
      const { data } = await apiClient.get<CustomerListItem>(
        `/api/v1/customers/${customerId}`,
      );
      return data;
    },
    staleTime: 60_000,
    enabled: Boolean(customerId),
  });

  return {
    customer: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  };
}
