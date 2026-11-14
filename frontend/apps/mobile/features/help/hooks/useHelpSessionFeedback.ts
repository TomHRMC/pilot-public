/**
 * useHelpSessionFeedback — mobile — FE-B16
 *
 * Location: apps/mobile/features/help/hooks/useHelpSessionFeedback.ts
 *
 * POST /api/v1/help/sessions/{session_id}/feedback — mobile version.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";

const API_BASE = process.env.EXPO_PUBLIC_API_URL ?? "";

export function useHelpSessionFeedback(sessionId: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (signal: "resolved" | "escalated" | "abandoned") => {
      if (!sessionId) throw new Error("No session ID");
      const res = await fetch(
        `${API_BASE}/api/v1/help/sessions/${sessionId}/feedback`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ signal }),
        },
      );
      if (!res.ok) throw new Error(`Session feedback failed: ${res.status}`);
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["help", "sessions"] });
    },
  });
}
