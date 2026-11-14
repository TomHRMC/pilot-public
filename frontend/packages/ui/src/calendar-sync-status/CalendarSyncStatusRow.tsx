/**
 * CalendarSyncStatusRow — mobile Owner tab status row for calendar sync health
 *
 * Location: packages/ui/src/calendar-sync-status/CalendarSyncStatusRow.tsx
 *
 * Three-state display:
 *   connected (no pending conflicts) → green dot + "Calendar sync · Up to date"
 *   pending_conflicts                → amber dot + "Calendar sync · N conflicts to resolve → web"
 *   error / requires_reconnect       → red dot + "Calendar sync · Reconnect needed → Settings"
 *
 * Uses React Native primitives (mobile-only component).
 * Deep-link URL from resolveWebUrl prop — never hardcoded.
 *
 * Tokens: colors.margin[500] (green), colors.alert[500] (amber), colors.fault[500] (red)
 * from packages/ui/src/tokens.ts.
 *
 * Pattern ref: mvp-arch.md §16.9; design doc batch-fe-b8-design.md §A.1.2
 */

import React from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Linking,
  ActivityIndicator,
} from "react-native";
import { tokens } from "../tokens";
import type { CalendarSyncStatusRowProps } from "../integration-conflict-resolver/types";

// ─── Dot state config ─────────────────────────────────────────────────────────

type DotState = "healthy" | "pending_conflicts" | "error" | "loading";

function getDotState(
  status: CalendarSyncStatusRowProps["status"],
  isLoading: boolean,
): DotState {
  if (isLoading || !status) return "loading";
  if (status.requiresReconnect || status.connectionStatus === "error")
    return "error";
  if (status.pendingConflictsCount > 0) return "pending_conflicts";
  return "healthy";
}

const DOT_COLOR: Record<Exclude<DotState, "loading">, string> = {
  healthy: tokens.colors.margin[400],
  pending_conflicts: tokens.colors.alert[400],
  error: tokens.colors.fault[600],
};

// ─── Component ────────────────────────────────────────────────────────────────

export function CalendarSyncStatusRow({
  status,
  isLoading,
  resolveWebUrl,
  pendingCount: pendingCountProp,
  testID,
}: CalendarSyncStatusRowProps) {
  const dotState = getDotState(status, isLoading);

  const handlePress = () => {
    if (resolveWebUrl) {
      void Linking.openURL(resolveWebUrl);
    }
  };

  if (dotState === "loading") {
    return (
      <View
        style={styles.row}
        testID={testID ?? "calendar-sync-status-row"}
        accessibilityLabel="Calendar sync status loading"
      >
        <ActivityIndicator
          size="small"
          color={tokens.colors.neutral[400]}
          testID="calendar-sync-loading-indicator"
        />
        <Text style={styles.title}>Calendar sync</Text>
      </View>
    );
  }

  const dotColor = DOT_COLOR[dotState];

  let subtitle: string;
  let isActionable = false;

  if (dotState === "error") {
    subtitle = "Reconnect needed → Settings";
    isActionable = true;
  } else if (dotState === "pending_conflicts" && status) {
    // FE-B15: prefer pendingCount from hook (fresher BE-B15 data); fallback to local
    const count = pendingCountProp ?? status.pendingConflictsCount;
    subtitle = `${count} conflict${count === 1 ? "" : "s"} to resolve → web`;
    isActionable = true;
  } else {
    subtitle = "Up to date";
    isActionable = false;
  }

  const content = (
    <View style={styles.row} testID={testID ?? "calendar-sync-status-row"}>
      {/* Status dot */}
      <View
        style={[styles.dot, { backgroundColor: dotColor }]}
        accessibilityLabel={`Calendar sync ${dotState.replace("_", " ")}`}
        testID={`calendar-sync-dot-${dotState}`}
      />

      {/* Labels */}
      <View style={styles.textBlock}>
        <Text style={styles.title} accessibilityRole="text">
          Calendar sync
        </Text>
        <Text
          style={[
            styles.subtitle,
            dotState === "error" && styles.subtitleError,
            dotState === "pending_conflicts" && styles.subtitleWarning,
          ]}
          accessibilityRole="text"
        >
          {subtitle}
        </Text>
      </View>

      {/* Chevron for actionable states */}
      {isActionable && (
        <Text
          style={styles.chevron}
          accessibilityElementsHidden={true}
          importantForAccessibility="no"
        >
          ›
        </Text>
      )}
    </View>
  );

  if (isActionable) {
    return (
      <TouchableOpacity
        onPress={handlePress}
        activeOpacity={0.7}
        accessibilityLabel={subtitle}
        accessibilityRole="link"
        accessibilityHint={`Opens ${dotState === "error" ? "settings" : "web conflict resolution"}`}
        testID={`${testID ?? "calendar-sync-status-row"}-touchable`}
        style={styles.touchable}
      >
        {content}
      </TouchableOpacity>
    );
  }

  return content;
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  touchable: {
    width: "100%",
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing[3],
    paddingVertical: tokens.spacing[3],
    paddingHorizontal: tokens.spacing[4],
    minHeight: tokens.touchTargets.mobile.sm,
  },
  dot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    flexShrink: 0,
  },
  textBlock: {
    flex: 1,
    gap: tokens.spacing[0],
  },
  title: {
    fontSize: tokens.mobileFontSizes.body,
    lineHeight: tokens.mobileLineHeights.body,
    color: tokens.colors.neutral[900],
    fontWeight: "500",
  },
  subtitle: {
    fontSize: tokens.mobileFontSizes.caption,
    lineHeight: tokens.mobileLineHeights.caption,
    color: tokens.colors.neutral[600],
  },
  subtitleError: {
    color: tokens.colors.fault[600],
  },
  subtitleWarning: {
    color: tokens.colors.alert[800],
  },
  chevron: {
    fontSize: 20,
    color: tokens.colors.neutral[400],
    flexShrink: 0,
  },
});
