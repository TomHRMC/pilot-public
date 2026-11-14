/**
 * useCustomerCommsSse — SSE live updates for web customer comms history
 *
 * Location: apps/web/src/features/customer-comms/hooks/useCustomerCommsSse.ts
 *
 * Composes useSseChannel. Invalidates history query on new message event.
 * SSE path: /api/v1/customers/{customerId}/comms/stream
 *
 * BETA-B2 fix (Issue 3.3): added getToken prop for JWT auth via query param.
 * Browser EventSource cannot send Authorization headers.
 *
 * Design doc Section C.10, A.2.1
 */

import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useSseChannel } from "@pilot/ui";
import type { SseMessage } from "@pilot/ui";

interface CustomerCommsSseEvent {
  type: "customer_message_received";
  data: {
    thread_id: string;
    message_id: string;
    direction: "inbound" | "outbound";
    body_preview: string;
    received_at: string;
  };
}

async function getAmplifyToken(): Promise<string> {
  const { fetchAuthSession } = await import("aws-amplify/auth");
  const session = await fetchAuthSession();
  return session.tokens?.idToken?.toString() ?? "";
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export function useCustomerCommsSse(customerId: string, _enabled = true) {
  const queryClient = useQueryClient();

  const handleMessage = useCallback(
    (msg: SseMessage) => {
      let event: CustomerCommsSseEvent;
      try {
        event = JSON.parse(msg.data) as CustomerCommsSseEvent;
      } catch {
        return;
      }

      if (event.type === "customer_message_received") {
        void queryClient.invalidateQueries({
          queryKey: ["customer-comms-history", customerId],
        });
      }
    },
    [queryClient, customerId],
  );

  // POST-BETA: /api/v1/customers/{id}/comms/stream does not exist in the backend.
  // The global notifications SSE (/api/v1/notifications/sse/notifications) is the
  // correct channel — customer message events are emitted there. Disabling this
  // customer-scoped SSE to stop the 404 cascade; the hook stays in place for
  // when a dedicated customer-comms stream endpoint is added.
  const { isConnected } = useSseChannel({
    path: `/api/v1/customers/${customerId}/comms/stream`,
    enabled: false, // disabled — endpoint not yet implemented
    getToken: getAmplifyToken,
    fallbackToPollingMs: 60_000,
    onMessage: handleMessage,
  });

  return { isConnected };
}
