/**
 * useFieldIssuesSse — SSE hook for field issues real-time updates
 *
 * Location: apps/web/src/features/field-issues/hooks/useFieldIssuesSse.ts
 *
 * Established FE-B9. Composes useSseChannel from packages/ui.
 * Channel: GET /api/v1/owner/mobile-sync-escalations/stream
 * Events: escalation_created | escalation_resolved | escalation_auto_recovered
 * On any event: invalidate ['field-issues'] cache.
 * Fallback to polling at 60s when SSE unsupported.
 *
 * BETA-B2 fix (Issue 3.3): added getToken prop for JWT auth via query param.
 * Browser EventSource cannot send Authorization headers.
 */

import { useQueryClient } from "@tanstack/react-query";
import { useSseChannel } from "@pilot/ui";
import type { SseMessage } from "@pilot/ui";

async function getAmplifyToken(): Promise<string> {
  const { fetchAuthSession } = await import("aws-amplify/auth");
  const session = await fetchAuthSession();
  return session.tokens?.idToken?.toString() ?? "";
}

export function useFieldIssuesSse() {
  const queryClient = useQueryClient();

  const { isConnected, isPolling } = useSseChannel({
    path: "/api/v1/owner/mobile-sync-escalations/stream",
    getToken: getAmplifyToken,
    fallbackToPollingMs: 60_000,
    pollFn: () => {
      void queryClient.invalidateQueries({ queryKey: ["field-issues"] });
    },
    onMessage: (message: SseMessage) => {
      // Parse SSE data as JSON to check event type
      let parsed: { type?: string } = {};
      try {
        parsed = JSON.parse(message.data) as { type?: string };
      } catch {
        // Ignore parse errors (heartbeats, etc.)
        return;
      }

      if (
        parsed.type === "escalation_created" ||
        parsed.type === "escalation_resolved" ||
        parsed.type === "escalation_auto_recovered"
      ) {
        void queryClient.invalidateQueries({ queryKey: ["field-issues"] });
      }
    },
  });

  return { isConnected, isPolling };
}
