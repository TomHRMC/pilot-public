/**
 * useHelpChat — TanStack Query mutation — FE-B16
 *
 * Location: apps/web/src/features/help/hooks/useHelpChat.ts
 *
 * Manages the POST /api/v1/help/chat request + accumulated message state.
 * RULE 3: No client-side RAG/embedding code.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useCallback } from "react";
import type { HelpChatMessage, HelpChatSession } from "@pilot/ui";
import type { HelpChatRequest, HelpChatResponse } from "../types";
import { apiClient } from "@pilot/shared-api";

async function postHelpChat(req: HelpChatRequest): Promise<HelpChatResponse> {
  const res = await apiClient.post<HelpChatResponse>(`/api/v1/help/chat`, req);
  return res.data;
}

/** Derive is_knowledge_boundary client-side from retrieved_article_ids */
function deriveKnowledgeBoundary(response: HelpChatResponse): boolean {
  return response.retrieved_article_ids.length === 0;
}

export function useHelpChat() {
  const queryClient = useQueryClient();
  const [messages, setMessages] = useState<HelpChatMessage[]>([]);
  const [session, setSession] = useState<HelpChatSession | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);

  const mutation = useMutation({
    mutationFn: postHelpChat,
    onMutate: (variables) => {
      setIsStreaming(true);
      // Optimistically add user message
      const userMessage: HelpChatMessage = {
        message_id: `temp-${Date.now()}`,
        session_id: variables.session_id ?? "pending",
        role: "user",
        content: variables.message,
        created_at: new Date().toISOString(),
        context_payload: variables.context_payload ?? null,
        voice_used: false,
        retrieved_article_ids: undefined,
        is_knowledge_boundary: false,
      };
      setMessages((prev) => [...prev, userMessage]);
    },
    onSuccess: (data) => {
      setIsStreaming(false);

      // Update session
      setSession((prev) => ({
        session_id: data.session_id,
        title: data.session_title,
        started_at: prev?.started_at ?? new Date().toISOString(),
        last_activity_at: new Date().toISOString(),
        message_count: (prev?.message_count ?? 0) + 2,
        outcome: prev?.outcome ?? null,
      }));

      // Add assistant message (with knowledge boundary derivation)
      const assistantMessage: HelpChatMessage = {
        message_id: data.message_id,
        session_id: data.session_id,
        role: "assistant",
        content: data.content,
        created_at: new Date().toISOString(),
        context_payload: null,
        retrieved_article_ids: data.retrieved_article_ids,
        voice_used: false,
        is_knowledge_boundary: deriveKnowledgeBoundary(data),
      };
      setMessages((prev) => [...prev, assistantMessage]);

      // Invalidate session list so history reflects new session
      queryClient.invalidateQueries({ queryKey: ["help", "sessions"] });
    },
    onError: () => {
      setIsStreaming(false);
      // Remove optimistic user message on error
      setMessages((prev) => prev.slice(0, -1));
    },
  });

  const sendMessage = useCallback(
    (text: string, voiceUsed = false) => {
      mutation.mutate({
        session_id: session?.session_id,
        message: text,
        context_payload: undefined,
      });
      void voiceUsed; // used by HelpChatMessages onSendMessage signature
    },
    [mutation, session?.session_id],
  );

  const sendMessageWithContext = useCallback(
    (text: string, contextPayload: import("@pilot/ui").HelpContextPayload) => {
      mutation.mutate({
        session_id: session?.session_id,
        message: text,
        context_payload: contextPayload,
      });
    },
    [mutation, session?.session_id],
  );

  const clearSession = useCallback(() => {
    setMessages([]);
    setSession(null);
  }, []);

  return {
    messages,
    session,
    isStreaming,
    error: mutation.error,
    sendMessage,
    sendMessageWithContext,
    clearSession,
  };
}
