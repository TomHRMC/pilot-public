/**
 * MyQuotesEntryRow — Navigation entry for "My Quotes" on the Jobs tab (MOB-B1)
 *
 * Location: apps/mobile/features/jobs/components/MyQuotesEntryRow.tsx
 *
 * Shows pending quote count badge. When count = 0 shows "All caught up."
 * Taps through to (home)/quotes/pending — the existing TechPendingQuotesList.
 */

import React from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import { colors, spacing } from "@pilot/ui/tokens";

interface MyQuotesEntryRowProps {
  pendingCount: number;
  onPress: () => void;
  testID?: string;
}

export function MyQuotesEntryRow({
  pendingCount,
  onPress,
  testID,
}: MyQuotesEntryRowProps) {
  const accessibilityLabel =
    pendingCount > 0
      ? `My Quotes, ${pendingCount} pending approval`
      : "My Quotes, all caught up";

  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.row, pressed && styles.rowPressed]}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      testID={testID ?? "my-quotes-entry-row"}
    >
      {/* Left: label */}
      <Text style={styles.label}>My Quotes</Text>

      {/* Right: badge or "all caught up" + chevron */}
      <View style={styles.right}>
        {pendingCount > 0 ? (
          <View style={styles.badge} testID="my-quotes-badge">
            <Text style={styles.badgeText}>
              {pendingCount > 99 ? "99+" : pendingCount}
            </Text>
          </View>
        ) : (
          <Text style={styles.allCaughtUp}>All caught up</Text>
        )}
        <Text style={styles.chevron} accessible={false}>
          ›
        </Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
    backgroundColor: "#FFFFFF",
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.neutral[200],
    minHeight: 48,
  },
  rowPressed: {
    backgroundColor: colors.neutral[50],
  },
  label: {
    fontSize: 15,
    fontWeight: "500",
    color: colors.neutral[900],
  },
  right: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[2],
  },
  badge: {
    backgroundColor: colors.brand[600],
    borderRadius: 999,
    minWidth: 22,
    height: 22,
    paddingHorizontal: spacing[1],
    alignItems: "center",
    justifyContent: "center",
  },
  badgeText: {
    fontSize: 12,
    fontWeight: "500",
    color: "#FFFFFF",
  },
  allCaughtUp: {
    fontSize: 13,
    color: colors.neutral[400],
  },
  chevron: {
    fontSize: 18,
    color: colors.neutral[400],
  },
});
