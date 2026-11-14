/**
 * VoiceSessionShell — full-screen voice chat container
 *
 * Location: apps/mobile/features/voice-quote-creation/components/VoiceSessionShell.tsx
 *
 * Composes: VoiceStateIndicator, VoiceComposer, VoiceMessageBubble,
 *           VoiceConfirmTurn, ContextChip, FieldModeToggle, SessionDrawer
 *
 * Wires useVoiceStream events to Zustand store state transitions.
 */

import React, { useEffect, useRef, useState } from "react";
import {
  View,
  Text,
  Pressable,
  FlatList,
  StyleSheet,
  SafeAreaView,
} from "react-native";
import { colors, spacing } from "../../../../../packages/ui/src/tokens";
import { useVoiceStream } from "../../../../../packages/ui/src/voice/index";
import { VoiceConfirmTurn } from "../../../../../packages/ui/src/voice-confirm-turn/VoiceConfirmTurn";
import { useVoiceConfirmation } from "../../../../../packages/ui/src/voice-confirm-turn/useVoiceConfirmation";
import { useVoiceSessionStore } from "../store";
import { VoiceComposer } from "./VoiceComposer";
import { VoiceMessageBubble } from "./VoiceMessageBubble";
import { ContextChip } from "./ContextChip";
import { FieldModeToggle } from "./FieldModeToggle";
import { SessionDrawer } from "./SessionDrawer";
import { useVoiceSession } from "../hooks/useVoiceSession";
import { useVoiceSessions } from "../hooks/useVoiceSessions";
import type { ConversationMessage, VoiceSession } from "../types-stub";

interface VoiceSessionShellProps {
  sessionId: string;
  fieldMode: boolean;
}

export function VoiceSessionShell({
  sessionId,
  fieldMode,
}: VoiceSessionShellProps) {
  const {
    voiceState,
    setVoiceState,
    setTranscriptBuffer,
    pendingConfirmation,
    setPendingConfirmation,
    setFieldMode,
    currentSessionId,
    setSessionId,
  } = useVoiceSessionStore();

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [localMessages, setLocalMessages] = useState<ConversationMessage[]>([]);
  const flatListRef = useRef<FlatList>(null);
  const {
    pendingConfirmation: confirmState,
    confirm,
    cancel,
  } = useVoiceConfirmation();

  // Fetch session + messages
  const { session, messages, isLoading } = useVoiceSession(sessionId);

  // All sessions for the drawer
  const { sessions, createSession } = useVoiceSessions();

  // Set current session ID in store
  useEffect(() => {
    setSessionId(sessionId);
    return () => setSessionId(null);
  }, [sessionId, setSessionId]);

  // Voice stream
  const {
    events,
    transcriptBuffer,
    connect,
    disconnect,
    isConnected,
    clearEvents,
  } = useVoiceStream(sessionId);

  // Sync transcript buffer to store
  useEffect(() => {
    setTranscriptBuffer(transcriptBuffer);
  }, [transcriptBuffer, setTranscriptBuffer]);

  // Process incoming WebSocket events
  useEffect(() => {
    const latest = events[events.length - 1];
    if (!latest) return;

    switch (latest.type) {
      case "transcript_partial":
        setVoiceState("processing");
        break;

      case "transcript_final":
        setVoiceState("processing");
        break;

      case "intent_detected":
        setVoiceState("processing");
        break;

      case "response_streaming":
        setVoiceState("speaking");
        break;

      case "response_final": {
        setVoiceState(
          latest.payload.structured_content?.render_mode ? "speaking" : "idle",
        );
        // Add assistant message locally until TanStack Query refetches
        if (latest.payload.message_id && latest.payload.text) {
          const newMsg: ConversationMessage = {
            message_id: latest.payload.message_id,
            session_id: sessionId,
            role: "assistant",
            content_text: latest.payload.text,
            structured_content_json: latest.payload.structured_content
              ? {
                  render_mode: latest.payload.structured_content.render_mode,
                  content_type: latest.payload.structured_content
                    .content_type as ConversationMessage["structured_content_json"] extends null
                    ? never
                    : NonNullable<
                        ConversationMessage["structured_content_json"]
                      >["content_type"],
                  entity_id:
                    latest.payload.structured_content.entity_id ?? null,
                  snapshot_payload: null,
                  captured_at: new Date().toISOString(),
                }
              : null,
            created_at: new Date().toISOString(),
          };
          setLocalMessages((prev) => [...prev, newMsg]);
        }
        break;
      }

      case "action_committed":
        // snapshot_frozen: true triggers live → snapshot one-way transition
        setVoiceState("idle");
        break;

      case "error":
        setVoiceState("error");
        break;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [events]);

  // Combine fetched + local messages
  const allMessages = [...(messages ?? []), ...localMessages];

  function handleMicPress() {
    if (voiceState === "idle" || voiceState === "error") {
      connect();
      setVoiceState("listening");
    } else if (voiceState === "listening") {
      disconnect();
      setVoiceState("processing");
    }
  }

  function handleTextSubmit(text: string) {
    // Send text as a voice-equivalent WS message
    if (isConnected) {
      // In full impl, POST to session messages endpoint
    }
    const userMsg: ConversationMessage = {
      message_id: `local-${Date.now()}`,
      session_id: sessionId,
      role: "user",
      content_text: text,
      structured_content_json: null,
      created_at: new Date().toISOString(),
    };
    setLocalMessages((prev) => [...prev, userMsg]);
  }

  function handleQuoteSubmit(_quoteId: string) {
    // POST /api/v1/quotes — handled by useVoiceQuoteSubmit hook
    // snapshot_freeze triggered by action_committed WS event after submission
    setVoiceState("processing");
  }

  return (
    <SafeAreaView style={styles.root}>
      {/* Header */}
      <View style={styles.header}>
        <Pressable
          style={styles.hamburger}
          onPress={() => setDrawerOpen(true)}
          accessibilityRole="button"
          accessibilityLabel="Open sessions list"
          testID="session-drawer-trigger"
        >
          <Text style={styles.hamburgerIcon}>☰</Text>
        </Pressable>

        {session?.title && (
          <Text style={styles.sessionTitle} numberOfLines={1}>
            {session.title}
          </Text>
        )}

        <View style={styles.headerRight}>
          <ContextChip contextWindow={null} />
          <FieldModeToggle
            isEnabled={fieldMode}
            onToggle={() => setFieldMode(!fieldMode)}
          />
        </View>
      </View>

      {/* Message list */}
      {!fieldMode && (
        <FlatList
          ref={flatListRef}
          data={allMessages}
          keyExtractor={(item) => item.message_id}
          renderItem={({ item }) => (
            <VoiceMessageBubble
              message={item}
              onQuoteSubmit={handleQuoteSubmit}
            />
          )}
          contentContainerStyle={styles.messageList}
          onContentSizeChange={() =>
            flatListRef.current?.scrollToEnd({ animated: true })
          }
          testID="voice-message-list"
        />
      )}

      {/* Confirm turn */}
      {pendingConfirmation && (
        <VoiceConfirmTurn
          prompt={pendingConfirmation.prompt}
          onConfirm={async () => {
            await confirm(pendingConfirmation.intentId, async () => {
              // Execute the pending voice action
            });
            setPendingConfirmation(null);
          }}
          onCancel={() => {
            cancel();
            setPendingConfirmation(null);
            setVoiceState("idle");
          }}
          testID="voice-confirm-turn"
        />
      )}

      {/* Composer */}
      <VoiceComposer
        voiceState={voiceState}
        onMicPress={handleMicPress}
        onSubmitText={handleTextSubmit}
        fieldMode={fieldMode}
      />

      {/* Session drawer */}
      <SessionDrawer
        sessions={sessions ?? []}
        currentSessionId={currentSessionId}
        onSelect={(id) => {
          // Navigate to selected session — handled by parent route
        }}
        onNewSession={async () => {
          await createSession();
        }}
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.neutral[50],
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[200],
    gap: spacing[3],
  },
  hamburger: {
    minWidth: 44,
    minHeight: 44,
    alignItems: "center",
    justifyContent: "center",
  },
  hamburgerIcon: {
    fontSize: 20,
    color: colors.neutral[900],
  },
  sessionTitle: {
    flex: 1,
    fontSize: 15,
    color: colors.neutral[900],
  },
  headerRight: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[2],
  },
  messageList: {
    paddingVertical: spacing[4],
    flexGrow: 1,
  },
});
