/**
 * useHelpSessionFeedback — TanStack Query mutation — FE-B16
 *
 * Location: apps/web/src/features/help/hooks/useHelpSessionFeedback.ts
 *
 * POST /api/v1/help/sessions/{session_id}/feedback
 * Fire-and-forget: resolved / escalated / abandoned signals.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type {
  HelpSessionFeedbackRequest,
  HelpSessionFeedbackResponse,
} from "../types";

async function submitSessionFeedback(
  sessionId: string,
  req: HelpSessionFeedbackRequest,
): Promise<HelpSessionFeedbackResponse> {
  const res = await apiClient.post<HelpSessionFeedbackResponse>(
    `/api/v1/help/sessions/${sessionId}/feedback`,
    req,
  );
  return res.data;
}

export function useHelpSessionFeedback(sessionId: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (signal: HelpSessionFeedbackRequest["signal"]) => {
      if (!sessionId) throw new Error("No session ID");
      return submitSessionFeedback(sessionId, { signal });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["help", "sessions"] });
    },
  });
}
