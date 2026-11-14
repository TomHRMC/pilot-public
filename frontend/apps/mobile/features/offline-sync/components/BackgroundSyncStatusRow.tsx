/**
 * BackgroundSyncStatusRow — background sync status display in SyncQueueDrawer
 *
 * Location: apps/mobile/features/offline-sync/components/BackgroundSyncStatusRow.tsx
 *
 * Established FE-B9. Six states per design doc Decision 5.
 * RULE 5: Pure observer — NO OS API calls. Reads SyncOrchestrator state only.
 *
 * Tokens (all from tokens.ts):
 *   colors.margin[400] — healthy dot (green)
 *   colors.alert[400]  — degraded dot (amber)
 *   colors.neutral[400] — disabled dot (neutral)
 */

import React from "react";
import { View, Text, Pressable, StyleSheet, Linking } from "react-native";
import {
  colors,
  mobileFontSizes,
  mobileLineHeights,
  spacing,
  touchTargets,
} from "@pilot/ui/tokens";
import type { BackgroundSyncStatus } from "../hooks/useBackgroundSyncStatus";

// ─── OS Settings deep-link (permission request path) ─────────────────────────
// On iOS: App settings. On Android: App notification settings.
// SyncOrchestrator/native infra handles the actual OS API — we only deep-link (RULE 5).
const SETTINGS_DEEP_LINK = "app-settings:"; // Linking.openSettings() equivalent

// ─── State configs ────────────────────────────────────────────────────────────

interface StateConfig {
  dotColor: string;
  title: string;
  subtitle: (status: BackgroundSyncStatus) => string;
  isActionable: boolean;
}

function formatTimeAgo(date: Date): string {
  const diffMs = Date.now() - date.getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 1) return "just now";
  if (diffMin === 1) return "1 min ago";
  if (diffMin < 60) return `${diffMin} min ago`;
  const diffHr = Math.floor(diffMin / 60);
  return `${diffHr}h ago`;
}

const STATE_CONFIGS: Record<BackgroundSyncStatus["state"], StateConfig> = {
  recent_success: {
    dotColor: colors.margin[400],
    title: "Background sync",
    subtitle: (s) =>
      `Last sync: ${s.lastAttemptAt ? formatTimeAgo(s.lastAttemptAt) : "—"}${
        s.itemsSynced !== null && s.itemsSynced > 0
          ? ` (${s.itemsSynced} item${s.itemsSynced === 1 ? "" : "s"})`
          : ""
      }`,
    isActionable: false,
  },
  recent_success_no_work: {
    dotColor: colors.margin[400],
    title: "Background sync",
    subtitle: (s) =>
      `Last sync: ${s.lastAttemptAt ? formatTimeAgo(s.lastAttemptAt) : "—"} · Nothing to sync`,
    isActionable: false,
  },
  recent_failed: {
    dotColor: colors.alert[400],
    title: "Background sync degraded",
    subtitle: (s) =>
      `Last attempt: ${s.lastAttemptAt ? formatTimeAgo(s.lastAttemptAt) : "—"} · Will retry`,
    isActionable: false,
  },
  disabled: {
    dotColor: colors.neutral[400],
    title: "Background sync off",
    subtitle: () => "Items will sync when you open the app",
    isActionable: true,
  },
  never_run: {
    dotColor: colors.neutral[400],
    title: "Background sync ready",
    subtitle: () => "Syncs automatically when enabled",
    isActionable: false,
  },
  no_permission: {
    dotColor: colors.alert[400],
    title: "Background sync limited",
    subtitle: () => "Enable notifications for best performance",
    isActionable: true,
  },
};

// ─── Props ─────────────────────────────────────────────────────────────────────

export interface BackgroundSyncStatusRowProps {
  status: BackgroundSyncStatus;
  /** Deep-link to sync settings page. Tapped when state is actionable. */
  onPress: () => void;
  testID?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function BackgroundSyncStatusRow({
  status,
  onPress,
  testID,
}: BackgroundSyncStatusRowProps) {
  const config = STATE_CONFIGS[status.state];

  const handlePress = () => {
    if (status.state === "no_permission") {
      void Linking.openSettings();
    }
    onPress();
  };

  const content = (
    <View
      style={styles.row}
      testID={testID ?? "background-sync-status-row"}
      accessibilityLabel={`Background sync: ${config.subtitle(status)}`}
    >
      {/* Status dot */}
      <View
        style={[styles.dot, { backgroundColor: config.dotColor }]}
        testID={`bg-sync-dot-${status.state}`}
      />

      {/* Labels */}
      <View style={styles.textBlock}>
        <Text style={styles.title}>{config.title}</Text>
        <Text
          style={[
            styles.subtitle,
            (status.state === "recent_failed" ||
              status.state === "no_permission") &&
              styles.subtitleWarning,
          ]}
          testID="bg-sync-subtitle"
        >
          {config.subtitle(status)}
        </Text>
      </View>

      {/* Chevron for actionable states */}
      {config.isActionable && (
        <Text style={styles.chevron} accessibilityElementsHidden={true}>
          ›
        </Text>
      )}
    </View>
  );

  if (config.isActionable) {
    return (
      <Pressable
        onPress={handlePress}
        style={styles.pressable}
        accessibilityRole="button"
        accessibilityLabel={`Background sync — ${config.subtitle(status)}. Tap to open settings.`}
        testID={`${testID ?? "background-sync-status-row"}-pressable`}
      >
        {content}
      </Pressable>
    );
  }

  return content;
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  pressable: {
    width: "100%",
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[3],
    paddingVertical: spacing[3],
    paddingHorizontal: spacing[4],
    minHeight: touchTargets.mobile.sm,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    flexShrink: 0,
  },
  textBlock: {
    flex: 1,
    gap: spacing[0],
  },
  title: {
    fontSize: mobileFontSizes.body,
    lineHeight: mobileLineHeights.body,
    color: colors.neutral[50],
    fontWeight: "500",
  },
  subtitle: {
    fontSize: mobileFontSizes.caption,
    lineHeight: mobileLineHeights.caption,
    color: colors.neutral[400],
  },
  subtitleWarning: {
    color: colors.alert[400],
  },
  chevron: {
    fontSize: 20,
    color: colors.neutral[400],
    flexShrink: 0,
  },
});
