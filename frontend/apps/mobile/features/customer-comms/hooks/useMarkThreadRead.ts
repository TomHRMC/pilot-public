/**
 * useMarkThreadRead — Mutation to mark all messages in a thread as read
 *
 * Location: apps/mobile/features/customer-comms/hooks/useMarkThreadRead.ts
 *
 * API: POST /api/v1/communications/threads/{threadId}/mark-read
 * Invalidates: ['customer-threads'] on success (unread count decrements)
 *
 * Design doc Section C.5, D.2
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";

interface MarkReadResponse {
  thread_id: string;
  marked_read_count: number;
}

async function markThreadRead(threadId: string): Promise<MarkReadResponse> {
  const res = await fetch(
    `/api/v1/communications/threads/${threadId}/mark-read`,
    { method: "POST" },
  );
  if (!res.ok) {
    const detail = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(
      `Failed to mark thread read: ${res.status} ${detail.detail ?? res.statusText}`,
    );
  }
  return res.json() as Promise<MarkReadResponse>;
}

export function useMarkThreadRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: markThreadRead,
    onSuccess: () => {
      // Unread count changed — invalidate thread list
      void queryClient.invalidateQueries({ queryKey: ["customer-threads"] });
    },
  });
}
