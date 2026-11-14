/**
 * SyncNowButton — Manual sync trigger button
 *
 * Location: apps/mobile/features/offline-sync/components/SyncNowButton.tsx
 *
 * Disabled while a sync is in flight (syncState.status === 'syncing').
 * Calls the SyncOrchestrator with trigger 'manual'.
 *
 * Per batch-fe-b7-design.md Section A.3.2.
 */

import React from "react";
import { Pressable, Text, StyleSheet, ActivityIndicator } from "react-native";
import {
  colors,
  mobileFontSizes,
  fontWeights,
  spacing,
  radii,
  touchTargets,
} from "@pilot/ui/tokens";
import { useSyncQueueStore } from "../store";

interface SyncNowButtonProps {
  onSync: () => Promise<void>;
  testID?: string;
}

export function SyncNowButton({
  onSync,
  testID,
}: SyncNowButtonProps): React.ReactElement {
  const { syncState } = useSyncQueueStore();
  const isSyncing = syncState.status === "syncing";

  const handlePress = (): void => {
    if (!isSyncing) void onSync();
  };

  return (
    <Pressable
      onPress={handlePress}
      disabled={isSyncing}
      style={[styles.button, isSyncing && styles.buttonDisabled]}
      accessibilityRole="button"
      accessibilityLabel={isSyncing ? "Sync in progress" : "Sync now"}
      accessibilityState={{ disabled: isSyncing }}
      testID={testID ?? "sync-now-button"}
    >
      {isSyncing ? (
        <ActivityIndicator
          size="small"
          color={colors.neutral[400]}
          testID="sync-activity-indicator"
        />
      ) : (
        <Text style={styles.label}>Sync now</Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    minHeight: touchTargets.mobile.sm,
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[2],
    backgroundColor: colors.brand[600],
    borderRadius: radii.md,
    alignItems: "center",
    justifyContent: "center",
  },
  buttonDisabled: {
    backgroundColor: colors.neutral[600],
    opacity: 0.6,
  },
  label: {
    fontSize: mobileFontSizes.body,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 20,
  },
});
