/**
 * useDeleteHelpSession — TanStack Query mutation — FE-B16
 *
 * Location: apps/web/src/features/help/hooks/useDeleteHelpSession.ts
 *
 * DELETE /api/v1/help/sessions/{session_id}
 * Uses optimistic removal from the session list cache.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { HelpSessionDeleteResponse } from "../types";
import { apiClient } from "@pilot/shared-api";

async function deleteHelpSession(
  sessionId: string,
): Promise<HelpSessionDeleteResponse> {
  const res = await apiClient.delete(`/api/v1/help/sessions/${sessionId}`);
  return res.data as HelpSessionDeleteResponse;
}

export function useDeleteHelpSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteHelpSession,
    onSuccess: () => {
      // Invalidate to refresh the session list
      queryClient.invalidateQueries({ queryKey: ["help", "sessions"] });
    },
  });
}
