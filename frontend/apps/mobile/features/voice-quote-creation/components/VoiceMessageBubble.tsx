/**
 * VoiceMessageBubble — renders a single chat message in a voice session
 *
 * Location: apps/mobile/features/voice-quote-creation/components/VoiceMessageBubble.tsx
 *
 * If the message has structured_content_json, delegates to StructuredMessage.
 * Otherwise renders plain text as a chat bubble.
 */

import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { colors, radii, spacing } from "../../../../../packages/ui/src/tokens";
import type { ConversationMessage } from "../types-stub";
import { StructuredMessage } from "./StructuredMessage";

interface VoiceMessageBubbleProps {
  message: ConversationMessage;
  onQuoteSubmit?: (quoteId: string) => void;
}

export function VoiceMessageBubble({
  message,
  onQuoteSubmit,
}: VoiceMessageBubbleProps) {
  const isUser = message.role === "user";

  // If there's structured content, render it instead of a bubble
  if (message.structured_content_json) {
    return (
      <View
        style={styles.structuredWrapper}
        testID={`msg-structured-${message.message_id}`}
      >
        <StructuredMessage
          message={{
            id: message.message_id,
            structured_content: message.structured_content_json as unknown as {
              render_mode: "live" | "snapshot";
              content_type:
                | "quote_preview"
                | "job_etc_status"
                | "conflict_summary"
                | "text";
              entity_id: string | null;
              snapshot_payload: Record<string, unknown> | null;
            },
          }}
          onQuoteSubmit={onQuoteSubmit}
        />
      </View>
    );
  }

  return (
    <View
      style={[styles.row, isUser ? styles.rowUser : styles.rowAssistant]}
      testID={`msg-bubble-${message.message_id}`}
    >
      <View
        style={[
          styles.bubble,
          isUser ? styles.bubbleUser : styles.bubbleAssistant,
        ]}
      >
        <Text
          style={[styles.text, isUser ? styles.textUser : styles.textAssistant]}
        >
          {message.content_text}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  structuredWrapper: {
    paddingHorizontal: spacing[4],
  },
  row: {
    paddingHorizontal: spacing[4],
    marginVertical: spacing[1],
  },
  rowUser: {
    alignItems: "flex-end",
  },
  rowAssistant: {
    alignItems: "flex-start",
  },
  bubble: {
    maxWidth: "80%",
    borderRadius: radii.lg,
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
  },
  bubbleUser: {
    backgroundColor: colors.brand[600],
    borderBottomRightRadius: radii.sm,
  },
  bubbleAssistant: {
    backgroundColor: colors.neutral[100],
    borderBottomLeftRadius: radii.sm,
  },
  text: {
    fontSize: 15,
    lineHeight: 22,
  },
  textUser: {
    color: colors.neutral[50],
  },
  textAssistant: {
    color: colors.neutral[900],
  },
});
