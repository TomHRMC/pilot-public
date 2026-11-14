/**
 * ApprovalsQueueSection — Owner tab: pending quote approvals
 *
 * Location: apps/mobile/features/owner-tab/components/ApprovalsQueueSection.tsx
 *
 * Shows pending quote count with a badge. Taps navigate to /(tabs)/(home)/quotes/pending.
 * Renders "All caught up ✓" when pendingCount === 0.
 * Fails silently on error (section collapses).
 *
 * MOB-B5
 */

import React from "react";
import {
  View,
  Text,
  Pressable,
  ActivityIndicator,
  StyleSheet,
} from "react-native";
import { useRouter } from "expo-router";
import { tokens, lightTheme } from "@pilot/ui/tokens";
import { useOwnerPendingQuotes } from "../hooks/useOwnerPendingQuotes";

export function ApprovalsQueueSection() {
  const { pendingCount, isLoading, isError } = useOwnerPendingQuotes();
  const router = useRouter();

  const handlePress = () => {
    router.push("/(tabs)/(home)/quotes/pending" as never);
  };

  if (isLoading) {
    return (
      <View style={styles.row} testID="approvals-loading">
        <ActivityIndicator size="small" color={tokens.colors.neutral[400]} />
      </View>
    );
  }

  // Fail silently on error — section collapses
  if (isError) return null;

  return (
    <Pressable
      onPress={handlePress}
      testID="approvals-queue-section"
      accessibilityRole="button"
      accessibilityLabel={
        pendingCount > 0
          ? `${pendingCount} quotes awaiting approval`
          : "Approvals queue"
      }
    >
      <View style={styles.row}>
        <View style={styles.labelRow}>
          <Text style={styles.sectionLabel}>Approvals</Text>
          {pendingCount > 0 && (
            <View style={styles.badge} testID="approvals-badge">
              <Text style={styles.badgeText}>{pendingCount}</Text>
            </View>
          )}
        </View>
        {pendingCount > 0 ? (
          <Text style={styles.valueText}>
            {pendingCount} quotes awaiting approval
          </Text>
        ) : (
          <Text style={styles.allCaughtUp}>All caught up ✓</Text>
        )}
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    backgroundColor: "#FFFFFF",
    borderRadius: 8,
    padding: tokens.spacing[3],
    gap: tokens.spacing[1],
  },
  labelRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing[2],
  },
  sectionLabel: {
    fontSize: tokens.mobileFontSizes.caption,
    lineHeight: tokens.mobileLineHeights.caption,
    color: tokens.colors.neutral[600],
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  badge: {
    backgroundColor: lightTheme.danger.bg,
    borderRadius: 10,
    minWidth: 20,
    height: 20,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: tokens.spacing[1],
  },
  badgeText: {
    fontSize: tokens.mobileFontSizes.caption,
    color: "#FFFFFF",
    fontWeight: "600",
  },
  valueText: {
    fontSize: tokens.mobileFontSizes.body,
    lineHeight: tokens.mobileLineHeights.body,
    color: tokens.colors.neutral[900],
  },
  allCaughtUp: {
    fontSize: tokens.mobileFontSizes.body,
    lineHeight: tokens.mobileLineHeights.body,
    color: tokens.colors.margin[600],
  },
});
