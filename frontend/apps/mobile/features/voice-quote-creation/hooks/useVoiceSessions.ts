/**
 * useVoiceSessions — TanStack Query hook for sessions list + CRUD
 *
 * Location: apps/mobile/features/voice-quote-creation/hooks/useVoiceSessions.ts
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { VoiceSession } from "../types-stub";

interface SessionListResponse {
  sessions: VoiceSession[];
  next_cursor: string | null;
  has_more: boolean;
}

async function fetchSessions(): Promise<SessionListResponse> {
  const res = await fetch("/api/v1/voice/sessions/");
  if (!res.ok) throw new Error("Failed to fetch sessions");
  return res.json();
}

async function createNewSession(): Promise<VoiceSession> {
  const res = await fetch("/api/v1/voice/sessions/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!res.ok) throw new Error("Failed to create session");
  return res.json();
}

async function deleteSessionById(sessionId: string): Promise<void> {
  const res = await fetch(`/api/v1/voice/sessions/${sessionId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete session");
}

export function useVoiceSessions() {
  const queryClient = useQueryClient();

  const sessionsQuery = useQuery({
    queryKey: ["voice-sessions"],
    queryFn: fetchSessions,
  });

  const createMutation = useMutation({
    mutationFn: createNewSession,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["voice-sessions"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteSessionById,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["voice-sessions"] });
    },
  });

  return {
    sessions: sessionsQuery.data?.sessions ?? [],
    hasMore: sessionsQuery.data?.has_more ?? false,
    isLoading: sessionsQuery.isLoading,
    error: sessionsQuery.error,
    createSession: () => createMutation.mutateAsync(),
    deleteSession: (id: string) => deleteMutation.mutateAsync(id),
    isCreating: createMutation.isPending,
  };
}
