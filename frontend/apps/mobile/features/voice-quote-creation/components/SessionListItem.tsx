/**
 * SessionListItem — a single session in the voice sessions list
 *
 * Location: apps/mobile/features/voice-quote-creation/components/SessionListItem.tsx
 */

import React from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import { colors, radii, spacing } from "../../../../../packages/ui/src/tokens";
import type { VoiceSession } from "../types-stub";

interface SessionListItemProps {
  session: VoiceSession;
  isActive: boolean;
  onPress: () => void;
}

function formatSessionDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function SessionListItem({
  session,
  isActive,
  onPress,
}: SessionListItemProps) {
  const dateLabel = formatSessionDate(session.created_at);
  const displayTitle = session.title ?? `Session #${session.session_number}`;

  return (
    <Pressable
      style={[styles.item, isActive && styles.activeItem]}
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={`${displayTitle}, ${dateLabel}`}
      accessibilityState={{ selected: isActive }}
      testID={`session-item-${session.session_id}`}
    >
      <View style={styles.content}>
        <Text
          style={[styles.title, isActive && styles.titleActive]}
          numberOfLines={1}
        >
          {displayTitle}
        </Text>
        <Text style={styles.meta}>
          #{session.session_number} · {dateLabel}
        </Text>
      </View>
      <View style={styles.right}>
        <Text style={styles.msgCount}>{session.message_count}</Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  item: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[200],
    minHeight: 60,
  },
  activeItem: {
    backgroundColor: colors.brand[50],
    borderLeftWidth: 3,
    borderLeftColor: colors.brand[600],
  },
  content: {
    flex: 1,
  },
  title: {
    fontSize: 15,
    color: colors.neutral[900],
  },
  titleActive: {
    color: colors.brand[800],
  },
  meta: {
    fontSize: 11,
    color: colors.neutral[400],
    marginTop: spacing[1],
  },
  right: {
    alignItems: "flex-end",
  },
  msgCount: {
    fontSize: 11,
    color: colors.neutral[400],
  },
});
