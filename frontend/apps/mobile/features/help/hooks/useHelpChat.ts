/**
 * useHelpChat — mobile — FE-B16
 *
 * Location: apps/mobile/features/help/hooks/useHelpChat.ts
 *
 * Mobile version of the help chat hook.
 * Shares the same API contract as the web version.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useCallback } from "react";
import type {
  HelpChatMessage,
  HelpChatSession,
  HelpContextPayload,
} from "@pilot/ui";

const API_BASE = process.env.EXPO_PUBLIC_API_URL ?? "";

interface HelpChatRequest {
  session_id?: string;
  message: string;
  context_payload?: HelpContextPayload;
}

interface HelpChatResponse {
  session_id: string;
  message_id: string;
  role: "assistant";
  content: string;
  retrieved_article_ids: string[];
  session_title: string | null;
}

async function postHelpChat(req: HelpChatRequest): Promise<HelpChatResponse> {
  const res = await fetch(`${API_BASE}/api/v1/help/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`Help chat failed: ${res.status}`);
  return res.json() as Promise<HelpChatResponse>;
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
      const userMessage: HelpChatMessage = {
        message_id: `temp-${Date.now()}`,
        session_id: variables.session_id ?? "pending",
        role: "user",
        content: variables.message,
        created_at: new Date().toISOString(),
        context_payload: variables.context_payload ?? null,
        voice_used: false,
        is_knowledge_boundary: false,
      };
      setMessages((prev) => [...prev, userMessage]);
    },
    onSuccess: (data) => {
      setIsStreaming(false);
      setSession((prev) => ({
        session_id: data.session_id,
        title: data.session_title,
        started_at: prev?.started_at ?? new Date().toISOString(),
        last_activity_at: new Date().toISOString(),
        message_count: (prev?.message_count ?? 0) + 2,
        outcome: prev?.outcome ?? null,
      }));
      const assistantMessage: HelpChatMessage = {
        message_id: data.message_id,
        session_id: data.session_id,
        role: "assistant",
        content: data.content,
        created_at: new Date().toISOString(),
        context_payload: null,
        retrieved_article_ids: data.retrieved_article_ids,
        voice_used: false,
        is_knowledge_boundary: data.retrieved_article_ids.length === 0,
      };
      setMessages((prev) => [...prev, assistantMessage]);
      queryClient.invalidateQueries({ queryKey: ["help", "sessions"] });
    },
    onError: () => {
      setIsStreaming(false);
      setMessages((prev) => prev.slice(0, -1));
    },
  });

  const sendMessage = useCallback(
    (text: string) => {
      mutation.mutate({ session_id: session?.session_id, message: text });
    },
    [mutation, session?.session_id],
  );

  const sendMessageWithContext = useCallback(
    (text: string, contextPayload: HelpContextPayload) => {
      mutation.mutate({
        session_id: session?.session_id,
        message: text,
        context_payload: contextPayload,
      });
    },
    [mutation, session?.session_id],
  );

  return {
    messages,
    session,
    isStreaming,
    error: mutation.error,
    sendMessage,
    sendMessageWithContext,
  };
}
