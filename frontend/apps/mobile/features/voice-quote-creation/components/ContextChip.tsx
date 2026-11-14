/**
 * ContextChip — shows active entity context window
 *
 * Location: apps/mobile/features/voice-quote-creation/components/ContextChip.tsx
 */

import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { colors, radii, spacing } from "../../../../../packages/ui/src/tokens";
import type { ContextWindowJson } from "../types-stub";

interface ContextChipProps {
  contextWindow: ContextWindowJson | null;
}

export function ContextChip({ contextWindow }: ContextChipProps) {
  if (!contextWindow?.active_customer_name) return null;

  return (
    <View
      style={styles.chip}
      accessibilityLabel={`Active context: ${contextWindow.active_customer_name}`}
      accessibilityHint="Current customer context for voice commands"
      accessible
      testID="context-chip"
    >
      <Text style={styles.label} numberOfLines={1}>
        {contextWindow.active_customer_name}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  chip: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.brand[50],
    borderRadius: radii.full,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[1],
    borderWidth: 1,
    borderColor: colors.brand[200],
    maxWidth: 200,
  },
  label: {
    color: colors.brand[800],
    fontSize: 12,
  },
});
