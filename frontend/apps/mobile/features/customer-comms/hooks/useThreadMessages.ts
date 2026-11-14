/**
 * useThreadMessages — TanStack Query infinite hook for thread messages
 *
 * Location: apps/mobile/features/customer-comms/hooks/useThreadMessages.ts
 *
 * API: GET /api/v1/communications/threads/{threadId}/messages
 * Query key: ['thread-messages', threadId, { page }]
 * Cache: staleTime: 0 (always fresh); cursor-paginated infinite query
 *
 * Design doc Section C.2, D.2
 */

import { useInfiniteQuery } from "@tanstack/react-query";
import type { SmsMessage, SmsThread } from "@pilot/ui";

interface ThreadMessagesResponse {
  messages: SmsMessage[];
  next_cursor: string | null;
  thread: SmsThread;
}

async function fetchThreadMessages(
  threadId: string,
  cursor?: string,
): Promise<ThreadMessagesResponse> {
  const params = new URLSearchParams();
  params.set("limit", "50");
  if (cursor) params.set("cursor", cursor);

  const res = await fetch(
    `/api/v1/communications/threads/${threadId}/messages?${params.toString()}`,
  );
  if (!res.ok) {
    const detail = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(
      `Failed to fetch thread messages: ${res.status} ${detail.detail ?? res.statusText}`,
    );
  }
  return res.json() as Promise<ThreadMessagesResponse>;
}

export function useThreadMessages(threadId: string) {
  const query = useInfiniteQuery({
    queryKey: ["thread-messages", threadId],
    queryFn: ({ pageParam }) =>
      fetchThreadMessages(threadId, pageParam as string | undefined),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    staleTime: 0, // Always fresh — thread messages must be current
    enabled: Boolean(threadId),
  });

  // Flatten all pages into a single chronological array
  const messages: SmsMessage[] =
    query.data?.pages.flatMap((page) => page.messages) ?? [];

  // Thread metadata comes from the first page
  const thread: SmsThread | undefined = query.data?.pages[0]?.thread;

  return {
    messages,
    thread,
    hasNextPage: query.hasNextPage,
    fetchNextPage: query.fetchNextPage,
    isFetchingNextPage: query.isFetchingNextPage,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  };
}
