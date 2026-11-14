/**
 * useQbConflictsSse — SSE hook for QB conflicts real-time updates
 *
 * Location: apps/web/src/features/quickbooks-conflict/hooks/useQbConflictsSse.ts
 *
 * Established FE-B9. Composes useSseChannel from packages/ui.
 * Channel: GET /api/v1/integrations/quickbooks/conflicts/stream
 * Events: conflict_detected | conflict_resolved | conflict_auto_recovered
 * On any event: invalidate ['qb-conflicts'] cache.
 * Fallback to polling at 60s.
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

export function useQbConflictsSse() {
  const queryClient = useQueryClient();

  const { isConnected, isPolling } = useSseChannel({
    path: "/api/v1/integrations/quickbooks/conflicts/stream",
    getToken: getAmplifyToken,
    fallbackToPollingMs: 60_000,
    pollFn: () => {
      void queryClient.invalidateQueries({ queryKey: ["qb-conflicts"] });
    },
    onMessage: (message: SseMessage) => {
      let parsed: { type?: string } = {};
      try {
        parsed = JSON.parse(message.data) as { type?: string };
      } catch {
        return;
      }

      if (
        parsed.type === "conflict_detected" ||
        parsed.type === "conflict_resolved" ||
        parsed.type === "conflict_auto_recovered"
      ) {
        void queryClient.invalidateQueries({ queryKey: ["qb-conflicts"] });
      }
    },
  });

  return { isConnected, isPolling };
}
