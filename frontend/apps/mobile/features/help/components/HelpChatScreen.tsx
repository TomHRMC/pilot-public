/**
 * HelpChatScreen — mobile — FE-B16
 *
 * Location: apps/mobile/features/help/components/HelpChatScreen.tsx
 *
 * Full-screen help chat for mobile. Renders HelpChatMessages from packages/ui.
 * RULE 2: No MessagePreviewModal.
 * RULE 3: No RAG/embedding code.
 * TTS: no-op for MVP (expo-speech not installed; Phase 2 enhancement).
 */

import React, { useCallback } from "react";
import { View, StyleSheet } from "react-native";
import { Stack } from "expo-router";
import { HelpChatMessages } from "@pilot/ui";
import type {
  HelpChatMessage,
  HelpChatSession,
  HelpFollowUpAction,
} from "@pilot/ui";
import { useHelpChat } from "../hooks/useHelpChat";
import { useHelpSessionFeedback } from "../hooks/useHelpSessionFeedback";

interface HelpChatScreenProps {
  /** Context payload passed via route params when opened from a contextual anchor */
  initialContext?: unknown;
}

export function HelpChatScreen({ initialContext }: HelpChatScreenProps) {
  const { messages, session, isStreaming, error, sendMessage } = useHelpChat();
  const sessionFeedback = useHelpSessionFeedback(session?.session_id ?? null);

  const handleSendMessage = useCallback(
    (text: string, _voiceUsed?: boolean) => {
      sendMessage(text);
    },
    [sendMessage],
  );

  const handleFollowUpAction = useCallback(
    (action: HelpFollowUpAction, _message: HelpChatMessage) => {
      if (action === "that_answered_it") {
        sessionFeedback.mutate("resolved");
      } else if (action === "still_confused") {
        sessionFeedback.mutate("escalated");
      } else if (action === "walk_me_through_it") {
        sendMessage("Can you walk me through this step by step?");
      }
    },
    [sessionFeedback, sendMessage],
  );

  const handleEscalate = useCallback(
    (_session: HelpChatSession) => {
      sessionFeedback.mutate("escalated");
    },
    [sessionFeedback],
  );

  // TTS no-op for MVP — expo-speech not installed; Phase 2 enhancement
  const handleRequestTts = useCallback((_text: string) => {
    // Silent no-op per design doc E: TTS is enhancement, not critical path
  }, []);

  return (
    <View style={styles.container} testID="help-chat-screen">
      <Stack.Screen options={{ title: "Help", headerBackTitle: "Back" }} />
      <HelpChatMessages
        session={session}
        messages={messages}
        isStreaming={isStreaming}
        isLoading={false}
        error={error}
        onSendMessage={handleSendMessage}
        onFollowUpAction={handleFollowUpAction}
        onEscalate={handleEscalate}
        onRequestTts={handleRequestTts}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#fff",
  },
});
