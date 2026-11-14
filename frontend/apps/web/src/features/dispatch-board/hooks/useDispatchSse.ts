/**
 * useDispatchSse — SSE consumer for the dispatch board
 *
 * Location: apps/web/src/features/dispatch-board/hooks/useDispatchSse.ts
 *
 * Composes useSseChannel; invalidates TanStack Query board cache on SSE events.
 * SSE messages carry cache-invalidation cues ONLY — not full payloads.
 *
 * The backend SSE endpoint /api/v1/scheduling/board/stream requires the JWT
 * as a `token` query param (EventSource cannot set auth headers per browser spec).
 *
 * BETA-B2 fix (Issue 3.3): JWT is now passed via the `getToken` prop on
 * useSseChannel rather than via manual state + URL concatenation. The hook
 * calls getToken() on every (re)connection so refreshed tokens are always used.
 *
 * Per batch-fe-b4-design.md §A.2.7
 */

"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useSseChannel } from "@pilot/ui/hooks";
import type { SseMessage } from "@pilot/ui/hooks";
import type { SseBoardEvent } from "../types-stub";

export interface UseDispatchSseOptions {
  activeDate: string;
  enabled?: boolean;
  /** Optional EventSource factory for test injection */
  eventSourceFactory?: (url: string) => EventSource;
  /** Optional getToken override for test injection */
  getToken?: () => Promise<string>;
}

async function getAmplifyToken(): Promise<string> {
  const { fetchAuthSession } = await import("aws-amplify/auth");
  const session = await fetchAuthSession();
  return session.tokens?.idToken?.toString() ?? "";
}

export function useDispatchSse({
  // activeDate kept in interface for future use (e.g. per-date SSE subscription)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  activeDate: _activeDate,
  enabled = true,
  eventSourceFactory,
  getToken,
}: UseDispatchSseOptions) {
  const queryClient = useQueryClient();

  const { isConnected, isPolling, connectionError, disconnect, reconnect } =
    useSseChannel({
      path: "/api/v1/scheduling/board/stream",
      enabled,
      getToken: getToken ?? getAmplifyToken,
      fallbackToPollingMs: 60_000,
      pollFn: () => {
        // Invalidate all dispatch board queries (prefix match covers any date range)
        queryClient.invalidateQueries({
          queryKey: ["dispatch-board"],
        });
      },
      eventSourceFactory,
      onMessage: (message: SseMessage) => {
        if (!message.data || message.data === "") return;

        let event: SseBoardEvent;
        try {
          event = JSON.parse(message.data) as SseBoardEvent;
        } catch {
          // Malformed SSE data — ignore
          return;
        }

        // All board events → invalidate the board query (refetch)
        // SSE carries the change signal; TanStack Query fetches the fresh data.
        switch (event.event_type) {
          case "job_scheduled":
          case "job_rescheduled":
          case "job_reassigned":
          case "job_unassigned":
          case "conflict_detected":
          case "conflict_cleared":
            // Invalidate all dispatch board queries (prefix match covers any date range)
            queryClient.invalidateQueries({
              queryKey: ["dispatch-board"],
            });
            break;

          case "calendar_sync_status":
            // Calendar sync status doesn't change the board data
            break;

          default:
            // Unknown event type — refetch to be safe
            queryClient.invalidateQueries({
              queryKey: ["dispatch-board"],
            });
        }
      },
    });

  return {
    sseConnected: isConnected,
    ssePolling: isPolling,
    sseError: connectionError,
    disconnect,
    reconnect,
  };
}
