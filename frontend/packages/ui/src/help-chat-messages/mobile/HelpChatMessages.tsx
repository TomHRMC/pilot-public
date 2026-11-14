/**
 * HelpChatMessages — mobile implementation — FE-B16
 *
 * Location: packages/ui/src/help-chat-messages/mobile/HelpChatMessages.tsx
 *
 * RULE 2: No MessagePreviewModal.
 * RULE 3: No RAG/embedding code.
 */

import React, { useEffect, useRef, useState } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  ActivityIndicator,
} from "react-native";
import { colors, radii, spacing } from "../../tokens";
import type {
  HelpChatMessagesProps,
  HelpChatMessage,
  HelpFollowUpAction,
} from "../types";
import { KnowledgeBoundaryMessage } from "../../knowledge-boundary-message/mobile/KnowledgeBoundaryMessage";

// ── Typing indicator ────────────────────────────────────────────────────────

function TypingIndicator() {
  return (
    <View style={styles.typingContainer} testID="help-typing-indicator">
      <ActivityIndicator size="small" color={colors.neutral[400]} />
    </View>
  );
}

// ── Message bubble ──────────────────────────────────────────────────────────

interface MobileBubbleProps {
  message: HelpChatMessage;
  onFollowUpAction: (
    action: HelpFollowUpAction,
    message: HelpChatMessage,
  ) => void;
  onEscalate: () => void;
  onRequestTts: (text: string) => void;
}

function MobileMessageBubble({
  message,
  onFollowUpAction,
  onEscalate,
  onRequestTts,
}: MobileBubbleProps) {
  const time = new Date(message.created_at).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  if (message.role === "user") {
    return (
      <View style={styles.userRow} testID="help-message-user">
        <View style={styles.userBubble}>
          <Text style={styles.userContent}>{message.content}</Text>
          <Text style={styles.timestamp}>{time}</Text>
        </View>
      </View>
    );
  }

  if (message.is_knowledge_boundary) {
    return (
      <View style={styles.assistantRow}>
        <KnowledgeBoundaryMessage
          content={message.content}
          timestamp={new Date(message.created_at)}
          onEscalate={onEscalate}
        />
      </View>
    );
  }

  return (
    <View style={styles.assistantRow} testID="help-message-assistant">
      <View style={styles.assistantBubble}>
        <View style={styles.assistantHeader}>
          <Text style={styles.assistantLabel}>
            Pilot AI {"\u00b7"} {time}
          </Text>
          <Pressable onPress={() => onRequestTts(message.content)}>
            <Text style={styles.ttsButton}>&#128266;</Text>
          </Pressable>
        </View>
        <Text style={styles.assistantContent}>{message.content}</Text>
        <View style={styles.followUpRow}>
          <Pressable
            onPress={() => onFollowUpAction("that_answered_it", message)}
            style={styles.followUpBtn}
          >
            <Text style={styles.followUpBtnText}>
              {"\u2713"} That answered it
            </Text>
          </Pressable>
          <Pressable
            onPress={() => onFollowUpAction("still_confused", message)}
            style={styles.followUpBtn}
          >
            <Text style={styles.followUpBtnText}>Still confused</Text>
          </Pressable>
        </View>
      </View>
    </View>
  );
}

// ── Main component ──────────────────────────────────────────────────────────

export function HelpChatMessages({
  session,
  messages,
  isStreaming,
  isLoading,
  error,
  onSendMessage,
  onFollowUpAction,
  onEscalate,
  onRequestTts,
  keyboardOffset = 0,
}: HelpChatMessagesProps) {
  const [text, setText] = useState("");
  const flatListRef = useRef<FlatList>(null);

  useEffect(() => {
    if (messages.length > 0) {
      flatListRef.current?.scrollToEnd({ animated: true });
    }
  }, [messages, isStreaming]);

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed || isStreaming) return;
    onSendMessage(trimmed, false);
    setText("");
  };

  const handleEscalate = () => {
    if (session) onEscalate(session);
  };

  type ListItem = HelpChatMessage | { id: "typing" } | { id: "empty" };

  const data: ListItem[] = [
    ...(messages.length === 0 && !isLoading ? [{ id: "empty" as const }] : []),
    ...messages,
    ...(isStreaming ? [{ id: "typing" as const }] : []),
  ];

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      keyboardVerticalOffset={keyboardOffset}
      testID="help-chat-messages"
    >
      <FlatList
        ref={flatListRef}
        data={data}
        keyExtractor={(item) =>
          "message_id" in item ? item.message_id : item.id
        }
        renderItem={({ item }) => {
          if ("id" in item && item.id === "empty") {
            return (
              <View style={styles.emptyState} testID="help-empty-state">
                <Text style={styles.emptyIcon}>&#128172;</Text>
                <Text style={styles.emptyTitle}>
                  Hi! What can I help you with?
                </Text>
                <Text style={styles.emptySubtitle}>
                  Ask about features, settings, or anything in Pilot.
                </Text>
              </View>
            );
          }
          if ("id" in item && item.id === "typing") {
            return <TypingIndicator />;
          }
          return (
            <MobileMessageBubble
              message={item as HelpChatMessage}
              onFollowUpAction={onFollowUpAction}
              onEscalate={handleEscalate}
              onRequestTts={onRequestTts}
            />
          );
        }}
        contentContainerStyle={styles.listContent}
        testID="help-message-list"
      />

      {/* Error state */}
      {error && (
        <View style={styles.errorBanner}>
          <Text style={styles.errorText}>
            {error.message ?? "Something went wrong."}
          </Text>
        </View>
      )}

      {/* Composer */}
      <View style={styles.composer} testID="help-composer">
        <TextInput
          value={text}
          onChangeText={setText}
          placeholder="Ask a question..."
          placeholderTextColor={colors.neutral[400]}
          multiline
          editable={!isStreaming}
          style={styles.input}
          testID="help-composer-input"
          returnKeyType="send"
          onSubmitEditing={handleSend}
        />
        <Pressable
          onPress={handleSend}
          disabled={!text.trim() || isStreaming}
          style={({ pressed }) => [
            styles.sendBtn,
            (!text.trim() || isStreaming) && styles.sendBtnDisabled,
            pressed && styles.pressed,
          ]}
          testID="help-send-button"
          accessibilityLabel="Send message"
        >
          <Text style={styles.sendBtnText}>Send</Text>
        </Pressable>
      </View>

      {/* Anonymization notice */}
      <View style={styles.anonNotice} testID="help-anonymization-notice">
        <Text style={styles.anonText}>
          Pilot uses help conversations to improve our help content. Personal
          info is removed before use.
        </Text>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  listContent: {
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2],
    flexGrow: 1,
  },
  typingContainer: {
    paddingVertical: spacing[2],
    paddingHorizontal: spacing[3],
  },
  userRow: {
    flexDirection: "row",
    justifyContent: "flex-end",
    marginVertical: spacing[1],
  },
  userBubble: {
    backgroundColor: colors.brand[50],
    borderWidth: 1,
    borderColor: colors.brand[100],
    borderRadius: radii.lg,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2],
    maxWidth: "80%",
  },
  userContent: { color: colors.brand[900], fontSize: 14, lineHeight: 20 },
  assistantRow: {
    flexDirection: "row",
    justifyContent: "flex-start",
    marginVertical: spacing[1],
  },
  assistantBubble: {
    backgroundColor: colors.neutral[50],
    borderWidth: 1,
    borderColor: colors.neutral[200],
    borderRadius: radii.lg,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2],
    maxWidth: "85%",
  },
  assistantHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: spacing[1],
  },
  assistantLabel: {
    color: colors.neutral[600],
    fontSize: 11,
    fontWeight: "500",
  },
  ttsButton: { fontSize: 12 },
  assistantContent: {
    color: colors.neutral[900],
    fontSize: 14,
    lineHeight: 20,
  },
  followUpRow: {
    flexDirection: "row",
    gap: 6,
    marginTop: spacing[2],
    flexWrap: "wrap",
  },
  followUpBtn: {
    backgroundColor: colors.neutral[100],
    borderRadius: radii.sm,
    paddingHorizontal: spacing[2],
    paddingVertical: spacing[1],
  },
  followUpBtnText: { color: colors.neutral[800], fontSize: 12 },
  emptyState: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: spacing[10],
  },
  emptyIcon: { fontSize: 32, marginBottom: spacing[2] },
  emptyTitle: {
    color: colors.neutral[800],
    fontWeight: "500",
    fontSize: 14,
    textAlign: "center",
  },
  emptySubtitle: {
    color: colors.neutral[400],
    fontSize: 12,
    textAlign: "center",
    marginTop: spacing[1],
  },
  composer: {
    flexDirection: "row",
    alignItems: "flex-end",
    padding: spacing[2],
    borderTopWidth: 1,
    borderTopColor: colors.neutral[200],
    backgroundColor: colors.neutral[50],
    gap: spacing[2],
  },
  input: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.neutral[200],
    borderRadius: radii.md,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2],
    fontSize: 14,
    color: colors.neutral[900],
    maxHeight: spacing[20] + spacing[16], // 80+64=144 → closest 4px-grid to 120px
    backgroundColor: colors.neutral[50],
  },
  sendBtn: {
    backgroundColor: colors.brand[600],
    borderRadius: radii.md,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2],
  },
  sendBtnDisabled: { opacity: 0.4 },
  pressed: { opacity: 0.7 },
  sendBtnText: { color: colors.neutral[50], fontSize: 14, fontWeight: "500" },
  anonNotice: {
    backgroundColor: colors.neutral[50],
    borderTopWidth: 1,
    borderTopColor: colors.neutral[100],
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[1] + 2,
  },
  anonText: { color: colors.neutral[400], fontSize: 11, textAlign: "center" },
  errorBanner: {
    backgroundColor: colors.fault[50],
    borderTopWidth: 1,
    borderTopColor: colors.fault[200],
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2],
  },
  errorText: { color: colors.fault[600], fontSize: 12, textAlign: "center" },
  timestamp: {
    color: colors.brand[200],
    fontSize: 10,
    textAlign: "right",
    marginTop: 2,
  },
});
