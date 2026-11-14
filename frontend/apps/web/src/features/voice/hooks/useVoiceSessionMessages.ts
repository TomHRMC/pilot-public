/**
 * useVoiceSessionMessages — voice session message history hook
 *
 * Location: apps/web/src/features/voice/hooks/useVoiceSessionMessages.ts
 *
 * GET /api/v1/voice/sessions/{sessionId}/messages?limit=50
 * Endpoint verified in backend/openapi_schema_map.md.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface VoiceMessage {
  message_id: string;
  session_id: string;
  role: "user" | "assistant" | "system";
  content_text: string;
  structured_content_json: Record<string, unknown> | null;
  created_at: string;
}

export interface VoiceSessionMessagesResponse {
  messages: VoiceMessage[];
  next_cursor: string | null;
  has_more: boolean;
}

export function useVoiceSessionMessages(
  sessionId: string | null | undefined,
  limit = 50,
) {
  return useQuery<VoiceSessionMessagesResponse>({
    queryKey: ["voice-session-messages", sessionId, limit],
    queryFn: async () => {
      const res = await apiClient.get(
        `/api/v1/voice/sessions/${sessionId}/messages`,
        { params: { limit } },
      );
      return res.data as VoiceSessionMessagesResponse;
    },
    enabled: !!sessionId,
    staleTime: 30_000,
  });
}
