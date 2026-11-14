/**
 * useVoiceSession — TanStack Query hook for a single session + messages
 *
 * Location: apps/mobile/features/voice-quote-creation/hooks/useVoiceSession.ts
 */

import { useQuery } from "@tanstack/react-query";
import type { VoiceSession, ConversationMessage } from "../types-stub";

async function fetchSession(sessionId: string): Promise<VoiceSession> {
  const res = await fetch(`/api/v1/voice/sessions/${sessionId}`);
  if (!res.ok) throw new Error("Failed to fetch session");
  return res.json();
}

async function fetchMessages(
  sessionId: string,
): Promise<ConversationMessage[]> {
  const res = await fetch(`/api/v1/voice/sessions/${sessionId}/messages`);
  if (!res.ok) throw new Error("Failed to fetch messages");
  const data = await res.json();
  return data.messages ?? data;
}

export function useVoiceSession(sessionId: string) {
  const sessionQuery = useQuery({
    queryKey: ["voice-session", sessionId],
    queryFn: () => fetchSession(sessionId),
    enabled: !!sessionId,
  });

  const messagesQuery = useQuery({
    queryKey: ["voice-session-messages", sessionId],
    queryFn: () => fetchMessages(sessionId),
    enabled: !!sessionId,
  });

  return {
    session: sessionQuery.data,
    messages: messagesQuery.data,
    isLoading: sessionQuery.isLoading || messagesQuery.isLoading,
    error: sessionQuery.error ?? messagesQuery.error,
    refetchMessages: messagesQuery.refetch,
  };
}
