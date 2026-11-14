/**
 * useMobileInboxSse — SSE live updates for the mobile inbox
 *
 * Location: apps/mobile/features/customer-comms/hooks/useMobileInboxSse.ts
 *
 * Composes useSseChannel with the onMessage callback pattern.
 * Invalidates ['customer-threads'] on customer_message_received event.
 * Appends new message to ['thread-messages', threadId] if thread is open.
 *
 * BETA-B2 fix (Issue 3.3): added getToken prop for JWT auth via query param.
 * Browser/native EventSource cannot send Authorization headers.
 *
 * Design doc Section C.10, D.7, Decision 1
 *
 * ARCHITECTURE NOTE: useSseChannel on mobile requires react-native-sse
 * eventSourceFactory per design doc Key Facts table.
 */

import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useSseChannel } from "@pilot/ui";
import type { SseMessage } from "@pilot/ui";

const INBOX_STREAM_PATH = "/api/v1/mobile/inbox/stream";

interface InboundMessageEvent {
  type: "customer_message_received" | "thread_read";
  data: {
    thread_id: string;
    customer_id?: string;
    message_id?: string;
    direction?: "inbound" | "outbound";
    body_preview?: string;
    received_at?: string;
  };
}

interface UseMobileInboxSseOptions {
  /** Currently active thread ID — if set, also invalidates thread messages */
  activeThreadId?: string;
  enabled?: boolean;
}

async function getAmplifyToken(): Promise<string> {
  const { fetchAuthSession } = await import("aws-amplify/auth");
  const session = await fetchAuthSession();
  return session.tokens?.idToken?.toString() ?? "";
}

export function useMobileInboxSse({
  activeThreadId,
  enabled = true,
}: UseMobileInboxSseOptions = {}) {
  const queryClient = useQueryClient();

  const handleMessage = useCallback(
    (msg: SseMessage) => {
      let event: InboundMessageEvent;
      try {
        event = JSON.parse(msg.data) as InboundMessageEvent;
      } catch {
        return;
      }

      if (event.type === "customer_message_received") {
        // Always invalidate the thread list (unread counts change)
        void queryClient.invalidateQueries({ queryKey: ["customer-threads"] });

        // If the active thread is the one receiving a message, refresh it too
        if (activeThreadId && event.data.thread_id === activeThreadId) {
          void queryClient.invalidateQueries({
            queryKey: ["thread-messages", activeThreadId],
          });
        }
      }

      if (event.type === "thread_read") {
        void queryClient.invalidateQueries({ queryKey: ["customer-threads"] });
      }
    },
    [queryClient, activeThreadId],
  );

  // useSseChannel handles connection management, reconnection, and cleanup.
  // Mobile builds: eventSourceFactory resolves to react-native-sse via Metro.
  const { isConnected } = useSseChannel({
    path: INBOX_STREAM_PATH,
    enabled,
    getToken: getAmplifyToken,
    fallbackToPollingMs: 60_000,
    onMessage: handleMessage,
  });

  return { isConnected };
}
