/**
 * Mobile Help Session List Screen — FE-B16
 *
 * Location: apps/mobile/app/(tabs)/more/help/history.tsx
 *
 * Route: /(tabs)/more/help/history
 */

import React from "react";
import { View, Text, FlatList, Pressable, StyleSheet } from "react-native";
import { Stack, useRouter } from "expo-router";
import { useQuery } from "@tanstack/react-query";

const API_BASE = process.env.EXPO_PUBLIC_API_URL ?? "";

interface SessionSummary {
  session_id: string;
  title: string | null;
  last_activity_at: string;
  message_count: number;
  outcome: string | null;
}

function relativeTime(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export default function HelpHistoryScreen() {
  const router = useRouter();
  const { data, isLoading } = useQuery({
    queryKey: ["help", "sessions"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/api/v1/help/sessions`);
      if (!res.ok) throw new Error("Failed to load sessions");
      return res.json() as Promise<{
        sessions: SessionSummary[];
        total: number;
      }>;
    },
    staleTime: 30_000,
  });

  return (
    <View style={styles.container} testID="help-history-screen">
      <Stack.Screen
        options={{ title: "Chat history", headerBackTitle: "Help" }}
      />

      {isLoading && (
        <View style={styles.center}>
          <Text style={styles.loadingText}>Loading…</Text>
        </View>
      )}

      {!isLoading && (!data?.sessions || data.sessions.length === 0) && (
        <View style={styles.center} testID="help-sessions-empty">
          <Text style={styles.emptyTitle}>No conversations yet</Text>
          <Text style={styles.emptySubtitle}>
            Start a chat to get help from Pilot AI.
          </Text>
        </View>
      )}

      <FlatList
        data={data?.sessions ?? []}
        keyExtractor={(item) => item.session_id}
        renderItem={({ item }) => (
          <Pressable
            onPress={() => router.push(`/(tabs)/more/help`)}
            style={({ pressed }) => [
              styles.sessionItem,
              pressed && styles.pressed,
            ]}
            testID={`help-session-item-${item.session_id}`}
          >
            <Text style={styles.sessionTitle}>
              {item.title ?? "Untitled conversation"}
            </Text>
            <Text style={styles.sessionMeta}>
              {relativeTime(item.last_activity_at)} · {item.message_count}{" "}
              messages
            </Text>
          </Pressable>
        )}
        contentContainerStyle={styles.listContent}
        testID="help-session-list"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
  },
  loadingText: { color: "#9ca3af", fontSize: 14 },
  emptyTitle: { color: "#374151", fontWeight: "500", fontSize: 14 },
  emptySubtitle: {
    color: "#9ca3af",
    fontSize: 12,
    marginTop: 4,
    textAlign: "center",
  },
  listContent: { paddingVertical: 8 },
  sessionItem: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#f3f4f6",
  },
  pressed: { backgroundColor: "#f9fafb" },
  sessionTitle: { color: "#111827", fontSize: 14, fontWeight: "500" },
  sessionMeta: { color: "#9ca3af", fontSize: 12, marginTop: 2 },
});
