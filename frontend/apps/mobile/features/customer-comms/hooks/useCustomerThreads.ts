/**
 * useCustomerThreads — TanStack Query hook for the tech's SMS thread list
 *
 * Location: apps/mobile/features/customer-comms/hooks/useCustomerThreads.ts
 *
 * API: GET /api/v1/mobile/inbox/customer-threads
 * Query key: ['customer-threads', { techId }]
 * Cache: staleTime: 30_000; refetchOnWindowFocus
 *
 * Design doc Section C.1, A.3.1
 *
 * NOTE: The /api/v1/mobile/inbox/customer-threads endpoint may return 404 if it
 * hasn't been implemented in the backend yet. The queryFn handles this gracefully
 * by returning empty data instead of throwing, so the home screen renders without
 * an error state while the backend endpoint is pending implementation.
 */

import { useQuery } from "@tanstack/react-query";
import type { SmsThreadListItem } from "@pilot/ui";
import { apiClient } from "@pilot/shared-api";

interface CustomerThreadsResponse {
  threads: SmsThreadListItem[];
  next_cursor: string | null;
  total_unread: number;
}

const EMPTY_RESPONSE: CustomerThreadsResponse = {
  threads: [],
  next_cursor: null,
  total_unread: 0,
};

async function fetchCustomerThreads(): Promise<CustomerThreadsResponse> {
  try {
    const { data } = await apiClient.get<CustomerThreadsResponse>(
      "/api/v1/mobile/inbox/customer-threads",
    );
    return data;
  } catch (err) {
    // 404 = endpoint not yet implemented in backend.
    // Return empty data silently so the home screen renders without an error state.
    // Any other error (401, 500, network) is rethrown to trigger isError=true.
    const axiosError = err as { response?: { status?: number } };
    if (axiosError?.response?.status === 404) {
      return EMPTY_RESPONSE;
    }
    throw err;
  }
}

interface UseCustomerThreadsOptions {
  techId?: string;
}

export function useCustomerThreads({ techId }: UseCustomerThreadsOptions = {}) {
  const query = useQuery({
    queryKey: ["customer-threads", { techId }],
    queryFn: fetchCustomerThreads,
    staleTime: 30_000,
    refetchOnWindowFocus: true,
    // 404 is handled inside queryFn (returns empty data, doesn't throw).
    // No custom retry logic needed — let QueryClient defaultOptions decide.
  });

  const totalUnread = query.data?.total_unread ?? 0;

  return {
    threads: query.data?.threads ?? [],
    nextCursor: query.data?.next_cursor ?? null,
    totalUnread,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  };
}
