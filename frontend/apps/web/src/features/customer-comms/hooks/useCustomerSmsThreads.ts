/**
 * useCustomerSmsThreads — TanStack Query for customer SMS threads (web)
 *
 * Location: apps/web/src/features/customer-comms/hooks/useCustomerSmsThreads.ts
 *
 * Fetches SMS thread list for a specific customer.
 * Endpoint: GET /api/v1/customers/{customerId}/threads
 *
 * This endpoint surfaces SD-02 seeded data (customer_communication_thread +
 * customer_communication_message) so SD-02 messages are visible from the
 * customer comms tab when navigating from the inbox.
 *
 * TODO [COMPANION-BE]: Backend must implement
 *   GET /api/v1/customers/{customer_id}/threads
 *   returning { threads: SmsThread[], total: number }
 *   This is the customer-scoped thread listing needed to surface SD-02 seed data.
 *   MSW handler bridges the gap for dev/test until then.
 *
 * Query key: ['customer-sms-threads', customerId]
 * Cache: staleTime: 30_000
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { SmsThread } from "@pilot/ui";

interface CustomerSmsThreadsResponse {
  threads: SmsThread[];
  total: number;
}

async function fetchCustomerSmsThreads(
  customerId: string,
): Promise<CustomerSmsThreadsResponse> {
  const res = await apiClient.get<CustomerSmsThreadsResponse>(
    `/api/v1/customers/${customerId}/threads`,
  );
  return res.data;
}

export function useCustomerSmsThreads(customerId: string) {
  const query = useQuery({
    queryKey: ["customer-sms-threads", customerId],
    queryFn: () => fetchCustomerSmsThreads(customerId),
    staleTime: 30_000,
    enabled: Boolean(customerId),
  });

  return {
    threads: query.data?.threads ?? [],
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  };
}
