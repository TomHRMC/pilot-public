/**
 * useUnroutedMessages — TanStack Query for unrouted SMS queue
 *
 * Location: apps/web/src/features/sms-unrouted/hooks/useUnroutedMessages.ts
 *
 * API: GET /api/v1/communications/unrouted
 * Query key: ['unrouted-messages', { cursor, limit }]
 * Cache: staleTime: 30_000
 *
 * Design doc Section C.8, A.2.3
 */

import { useQuery } from "@tanstack/react-query";
import type { UnroutedMessage } from "@pilot/ui";
import { apiClient } from "@pilot/shared-api";

interface UnroutedMessagesResponse {
  messages: UnroutedMessage[];
  next_cursor: string | null;
  total_count: number;
}

async function fetchUnroutedMessages(
  cursor?: string,
  limit = 20,
): Promise<UnroutedMessagesResponse> {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  if (cursor) params.set("cursor", cursor);

  const res = await apiClient.get<UnroutedMessagesResponse>(
    `/api/v1/communications/unrouted?${params.toString()}`,
  );
  return res.data;
}

export function useUnroutedMessages(cursor?: string) {
  const query = useQuery({
    queryKey: ["unrouted-messages", { cursor, limit: 20 }],
    queryFn: () => fetchUnroutedMessages(cursor),
    staleTime: 30_000,
  });

  return {
    messages: query.data?.messages ?? [],
    nextCursor: query.data?.next_cursor ?? null,
    totalCount: query.data?.total_count ?? 0,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  };
}
