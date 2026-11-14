/**
 * KnowledgeBoundaryMessage — mobile implementation — FE-B16
 *
 * Location: packages/ui/src/knowledge-boundary-message/mobile/KnowledgeBoundaryMessage.tsx
 */

import React from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import { colors } from "../../tokens";
import type { KnowledgeBoundaryMessageProps } from "../types";

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function KnowledgeBoundaryMessage({
  content,
  timestamp,
  onEscalate,
}: KnowledgeBoundaryMessageProps) {
  return (
    <View style={styles.container} testID="knowledge-boundary-message">
      <View style={styles.header}>
        <Text style={styles.label}>Pilot AI</Text>
        <Text style={styles.dot}>{"\u00b7"}</Text>
        <Text style={styles.time}>{formatTime(timestamp)}</Text>
      </View>

      <Text style={styles.content}>{content}</Text>

      <View style={styles.divider} />
      <Pressable
        onPress={onEscalate}
        testID="knowledge-boundary-escalate-cta"
        style={({ pressed }) => (pressed ? styles.pressed : undefined)}
      >
        <Text style={styles.cta}>
          {"Didn't find what you needed? Tell us \u2192"}
        </Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.fault[50],
    borderLeftWidth: 4,
    borderLeftColor: colors.fault[400],
    borderWidth: 1,
    borderColor: colors.fault[200],
    borderRadius: 8,
    padding: 12,
    marginVertical: 4,
    maxWidth: "85%",
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    marginBottom: 8,
  },
  label: {
    color: colors.fault[600],
    fontSize: 12,
    fontWeight: "500",
  },
  dot: {
    color: colors.fault[200],
    fontSize: 12,
  },
  time: {
    color: colors.fault[200],
    fontSize: 12,
  },
  content: {
    color: colors.fault[800],
    fontSize: 14,
    lineHeight: 20,
  },
  divider: {
    borderTopWidth: 1,
    borderTopColor: colors.fault[200],
    marginTop: 8,
    marginBottom: 8,
  },
  cta: {
    color: colors.brand[600],
    fontSize: 14,
    fontWeight: "500",
    textDecorationLine: "underline",
  },
  pressed: {
    opacity: 0.7,
  },
});
