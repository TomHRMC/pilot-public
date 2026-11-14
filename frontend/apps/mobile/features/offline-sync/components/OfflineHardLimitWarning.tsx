/**
 * OfflineHardLimitWarning — 72-hour hard offline limit full-screen warning
 *
 * Location: apps/mobile/features/offline-sync/components/OfflineHardLimitWarning.tsx
 *
 * Shown when device has been offline for >72 hours and has pending writes.
 * Blocks new writes until the device syncs.
 *
 * Soft limit (24h): NotificationBanner fires (handled by SyncOrchestrator).
 * Hard limit (72h): This screen blocks interaction.
 *
 * The hard limit hours value is configurable (null = disabled).
 * Per batch-fe-b7-design.md Section A.3.6 and §15.11.
 */

import React from "react";
import {
  View,
  Text,
  Pressable,
  StyleSheet,
  SafeAreaView,
  ActivityIndicator,
} from "react-native";
import {
  colors,
  mobileFontSizes,
  fontWeights,
  spacing,
  radii,
  touchTargets,
} from "@pilot/ui/tokens";

interface OfflineHardLimitWarningProps {
  hoursOffline: number;
  pendingCount: number;
  onSyncNow: () => Promise<void>;
  isSyncing?: boolean;
  testID?: string;
}

export function OfflineHardLimitWarning({
  hoursOffline,
  pendingCount,
  onSyncNow,
  isSyncing = false,
  testID,
}: OfflineHardLimitWarningProps): React.ReactElement {
  return (
    <SafeAreaView
      style={styles.container}
      testID={testID ?? "offline-hard-limit-warning"}
      accessible={true}
      accessibilityLabel="Offline too long — sync required"
    >
      {/* Warning icon */}
      <Text style={styles.icon}>⚡</Text>

      <Text style={styles.title}>Sync required</Text>

      <Text style={styles.description}>
        You've been offline for {Math.round(hoursOffline)} hours.
        {"\n\n"}
        You have {pendingCount} unsynced{" "}
        {pendingCount === 1 ? "change" : "changes"} that need to be saved before
        you can continue working.
        {"\n\n"}
        Please connect to the internet and tap Sync Now.
      </Text>

      {/* Stats */}
      <View style={styles.statsRow}>
        <View style={styles.stat}>
          <Text style={styles.statValue}>{Math.round(hoursOffline)}h</Text>
          <Text style={styles.statLabel}>Offline</Text>
        </View>
        <View style={styles.statDivider} />
        <View style={styles.stat}>
          <Text style={styles.statValue}>{pendingCount}</Text>
          <Text style={styles.statLabel}>Pending</Text>
        </View>
      </View>

      {/* Sync now button */}
      <Pressable
        onPress={onSyncNow}
        disabled={isSyncing}
        style={[styles.syncButton, isSyncing && styles.buttonDisabled]}
        accessibilityRole="button"
        accessibilityLabel="Sync now — upload pending changes"
        testID="hard-limit-sync-button"
      >
        {isSyncing ? (
          <ActivityIndicator size="small" color={colors.neutral[50]} />
        ) : (
          <Text style={styles.syncButtonText}>Sync now</Text>
        )}
      </Pressable>

      <Text style={styles.footer}>
        You won't lose any data. All your offline work will be saved when you
        sync.
      </Text>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[900],
    padding: spacing[6],
    alignItems: "center",
    justifyContent: "center",
    gap: spacing[5],
  },
  icon: {
    fontSize: 64,
    lineHeight: 72,
  },
  title: {
    fontSize: mobileFontSizes.h1,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.alert[400],
    lineHeight: 30,
    textAlign: "center",
  },
  description: {
    fontSize: mobileFontSizes.body,
    color: colors.neutral[200],
    lineHeight: 22,
    textAlign: "center",
  },
  statsRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[6],
    backgroundColor: colors.neutral[800],
    borderRadius: radii.lg,
    padding: spacing[4],
  },
  stat: {
    alignItems: "center",
    gap: spacing[1],
  },
  statValue: {
    fontSize: mobileFontSizes.display,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.alert[400],
    lineHeight: 36,
  },
  statLabel: {
    fontSize: mobileFontSizes.caption,
    color: colors.neutral[400],
    lineHeight: 16,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  statDivider: {
    width: 1,
    height: 40,
    backgroundColor: colors.neutral[600],
  },
  syncButton: {
    minHeight: touchTargets.mobile.lg,
    width: "100%",
    backgroundColor: colors.brand[600],
    borderRadius: radii.md,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: spacing[4],
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  syncButtonText: {
    fontSize: mobileFontSizes.h3,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 24,
  },
  footer: {
    fontSize: mobileFontSizes.caption,
    color: colors.neutral[600],
    lineHeight: 16,
    textAlign: "center",
  },
});
