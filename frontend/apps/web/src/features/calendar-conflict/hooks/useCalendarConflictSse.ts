/**
 * useCalendarConflictSse — SSE-driven cache invalidation hook
 *
 * Location: apps/web/src/features/calendar-conflict/hooks/useCalendarConflictSse.ts
 *
 * Composes useSseChannel from @pilot/ui.
 * Invalidates ['calendar-conflicts'] and ['calendar-status'] on SSE events.
 * Falls back to 60s polling if SSE connection fails.
 *
 * BETA-B2 fix (Issue 3.3): added getToken prop for JWT auth via query param.
 * Browser EventSource cannot send Authorization headers.
 *
 * Pattern ref: design doc batch-fe-b8-design.md §C.5, §D.4
 * Implements: mvp-arch.md §13.11 (SSE → cache invalidation cues)
 */

import { useQueryClient } from "@tanstack/react-query";
import { useSseChannel } from "@pilot/ui";
import type { SseMessage } from "@pilot/ui";
import type { CalendarSseEvent } from "../types";

async function getAmplifyToken(): Promise<string> {
  const { fetchAuthSession } = await import("aws-amplify/auth");
  const session = await fetchAuthSession();
  return session.tokens?.idToken?.toString() ?? "";
}

export function useCalendarConflictSse(enabled = true) {
  const queryClient = useQueryClient();

  return useSseChannel({
    path: "/api/v1/integrations/calendar/conflicts/stream",
    enabled,
    getToken: getAmplifyToken,
    onMessage: (msg: SseMessage) => {
      try {
        const event = JSON.parse(msg.data) as CalendarSseEvent;

        if (
          event.type === "conflict_detected" ||
          event.type === "conflict_resolved"
        ) {
          void queryClient.invalidateQueries({
            queryKey: ["calendar-conflicts"],
          });

          if (event.conflict_id) {
            void queryClient.invalidateQueries({
              queryKey: ["calendar-conflict", event.conflict_id],
            });
          }
        }

        if (event.type === "calendar_sync_status") {
          void queryClient.invalidateQueries({
            queryKey: ["calendar-status"],
          });
        }
      } catch {
        // Malformed SSE data — ignore silently
      }
    },
    fallbackToPollingMs: 60_000,
    pollFn: () => {
      void queryClient.invalidateQueries({ queryKey: ["calendar-conflicts"] });
      void queryClient.invalidateQueries({ queryKey: ["calendar-status"] });
    },
  });
}
