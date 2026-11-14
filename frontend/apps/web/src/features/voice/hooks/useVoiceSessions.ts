/**
 * useVoiceSessions — voice session list hook
 *
 * Location: apps/web/src/features/voice/hooks/useVoiceSessions.ts
 *
 * GET /api/v1/voice/sessions/?limit=20
 * Endpoint verified in backend/openapi_schema_map.md.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface VoiceSession {
  session_id: string;
  session_number: number;
  title: string | null;
  title_auto_generated: boolean;
  status: string;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  message_count: number;
}

export interface VoiceSessionListResponse {
  sessions: VoiceSession[];
  next_cursor: string | null;
  has_more: boolean;
}

export function useVoiceSessions(limit = 20) {
  return useQuery<VoiceSessionListResponse>({
    queryKey: ["voice-sessions", limit],
    queryFn: async () => {
      const res = await apiClient.get("/api/v1/voice/sessions/", {
        params: { limit },
      });
      return res.data as VoiceSessionListResponse;
    },
    staleTime: 30_000,
  });
}
