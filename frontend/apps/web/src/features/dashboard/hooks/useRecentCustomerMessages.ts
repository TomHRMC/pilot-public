/**
 * useRecentCustomerMessages — TanStack Query for dashboard widget
 *
 * Location: apps/web/src/features/dashboard/hooks/useRecentCustomerMessages.ts
 *
 * API: GET /api/v1/dashboard/widgets/recent-customer-messages?limit=10
 * Query key: ['dashboard-widget-recent-messages', { limit }]
 * Cache: staleTime: 30_000, refetchInterval: 60s
 *
 * Uses apiClient (JWT-intercepted Axios) so the Cognito token is attached.
 * /api/v1/dashboard/stream does not exist in the backend — using polling instead.
 *
 * Design doc Section C.7, A.2.2, Decision 5b
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

interface RecentCustomerMessage {
  thread_id: string; // unique per row — used as React list key
  customer_id: string;
  customer_name: string;
  tech_id: string;
  tech_name: string;
  direction: "outbound" | "inbound";
  body_preview: string;
  last_message_at: string; // backend field name — was incorrectly typed as received_at
  unread_count: number;
}

interface RecentCustomerMessagesResponse {
  messages: RecentCustomerMessage[];
}

async function fetchRecentMessages(
  limit: number,
): Promise<RecentCustomerMessagesResponse> {
  const res = await apiClient.get<RecentCustomerMessagesResponse>(
    `/api/v1/dashboard/widgets/recent-customer-messages?limit=${limit}`,
  );
  return res.data;
}

export function useRecentCustomerMessages({
  limit = 10,
}: { limit?: number } = {}) {
  const query = useQuery({
    queryKey: ["dashboard-widget-recent-messages", { limit }],
    queryFn: () => fetchRecentMessages(limit),
    staleTime: 30_000,
    refetchInterval: 60_000, // Poll every 60s — no SSE stream available
  });

  return {
    messages: query.data?.messages ?? [],
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  };
}
