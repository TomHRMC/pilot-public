/**
 * Voice sessions list view
 *
 * Location: apps/mobile/app/(tabs)/(home)/voice/index.tsx
 *
 * Lists all prior voice sessions. Entry point to the voice feature.
 * New session → POST /api/v1/voice/sessions → push to [sessionId].
 */

import React from "react";
import { View, Text, Pressable, FlatList, StyleSheet } from "react-native";
import { useRouter } from "expo-router";
import {
  colors,
  radii,
  spacing,
} from "../../../../../../packages/ui/src/tokens";
import { useVoiceSessions } from "../../../../features/voice-quote-creation/hooks/useVoiceSessions";
import { SessionListItem } from "../../../../features/voice-quote-creation/components/SessionListItem";
import type { VoiceSession } from "../../../../features/voice-quote-creation/types-stub";

type AnyHref = Parameters<ReturnType<typeof useRouter>["push"]>[0];
function toHref(path: string): AnyHref {
  return path as AnyHref;
}

export default function VoiceSessionListScreen() {
  const router = useRouter();
  const { sessions, isLoading, createSession, isCreating } = useVoiceSessions();

  async function handleNewSession() {
    try {
      const newSession = await createSession();
      if (newSession && "session_id" in newSession) {
        router.push(
          toHref(
            `/(tabs)/(home)/voice/${(newSession as VoiceSession).session_id}`,
          ),
        );
      }
    } catch {
      // Error handled by TanStack Query
    }
  }

  function handleSelectSession(sessionId: string) {
    router.push(toHref(`/(tabs)/(home)/voice/${sessionId}`));
  }

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <Text style={styles.loadingText}>Loading sessions...</Text>
      </View>
    );
  }

  return (
    <View style={styles.root}>
      {/* New session button */}
      <Pressable
        style={[styles.newSessionBtn, isCreating && styles.disabled]}
        onPress={handleNewSession}
        disabled={isCreating}
        accessibilityRole="button"
        accessibilityLabel="Start new voice session"
        testID="new-session-btn"
      >
        <Text style={styles.newSessionText}>
          {isCreating ? "Creating..." : "+ New Session"}
        </Text>
      </Pressable>

      {/* Sessions list */}
      <FlatList
        data={sessions}
        keyExtractor={(item) => item.session_id}
        renderItem={({ item }) => (
          <SessionListItem
            session={item}
            isActive={false}
            onPress={() => handleSelectSession(item.session_id)}
          />
        )}
        ListEmptyComponent={
          <View style={styles.emptyContainer} testID="sessions-empty-state">
            <Text style={styles.emptyTitle}>No sessions yet</Text>
            <Text style={styles.emptyDetail}>
              {`Tap "+ New Session" to start your first voice quote`}
            </Text>
          </View>
        }
        testID="sessions-list"
        contentContainerStyle={sessions.length === 0 && styles.emptyList}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.neutral[50],
  },
  centered: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  loadingText: {
    color: colors.neutral[400],
    fontSize: 15,
  },
  newSessionBtn: {
    margin: spacing[4],
    backgroundColor: colors.brand[600],
    borderRadius: radii.md,
    paddingVertical: spacing[3],
    alignItems: "center",
    minHeight: 44,
    justifyContent: "center",
  },
  disabled: {
    opacity: 0.6,
  },
  newSessionText: {
    color: colors.neutral[50],
    fontSize: 15,
  },
  emptyContainer: {
    alignItems: "center",
    padding: spacing[8],
    gap: spacing[3],
  },
  emptyTitle: {
    fontSize: 17,
    color: colors.neutral[900],
  },
  emptyDetail: {
    fontSize: 13,
    color: colors.neutral[400],
    textAlign: "center",
  },
  emptyList: {
    flexGrow: 1,
    justifyContent: "center",
  },
});
