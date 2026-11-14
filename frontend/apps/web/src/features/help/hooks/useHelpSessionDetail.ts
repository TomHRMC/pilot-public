/**
 * useHelpSessionDetail — TanStack Query — FE-B16
 *
 * Location: apps/web/src/features/help/hooks/useHelpSessionDetail.ts
 *
 * GET /api/v1/help/sessions/{session_id}
 */

import { useQuery } from "@tanstack/react-query";
import type { HelpSessionDetailResponse } from "../types";
import { apiClient } from "@pilot/shared-api";

async function fetchHelpSessionDetail(
  sessionId: string,
): Promise<HelpSessionDetailResponse> {
  const res = await apiClient.get<HelpSessionDetailResponse>(
    `/api/v1/help/sessions/${sessionId}`,
  );
  return res.data;
}

export function useHelpSessionDetail(sessionId: string | null) {
  return useQuery({
    queryKey: ["help", "sessions", sessionId],
    queryFn: () => fetchHelpSessionDetail(sessionId!),
    enabled: !!sessionId,
    staleTime: 60_000,
  });
}
