/**
 * MobileSyncStatusBar — Persistent bottom sync status bar
 *
 * Location: apps/mobile/features/offline-sync/components/MobileSyncStatusBar.tsx
 *
 * Composes FE-B1 InFlightSyncIndicator (surface="mobile-sync") with
 * pending count from local WatermelonDB via useSyncQueueStore.
 *
 * Per batch-fe-b7-design.md Section A.3.5 and §16.13.
 */

import React from "react";
import { View, StyleSheet } from "react-native";
import { InFlightSyncIndicator } from "@pilot/ui/sync-indicator";
import { colors, spacing } from "@pilot/ui/tokens";
import { useSyncQueueStore } from "../store";
import { ConnectionStatePill } from "./ConnectionStatePill";

interface MobileSyncStatusBarProps {
  onSync: () => Promise<void>;
  testID?: string;
}

export function MobileSyncStatusBar({
  onSync,
  testID,
}: MobileSyncStatusBarProps): React.ReactElement {
  const { syncState, openDrawer } = useSyncQueueStore();

  const pendingCount = syncState.pendingCount;
  // FE-B15: lastSyncedAt type narrowed to Date | undefined (null removed from InFlightSyncIndicatorProps)
  const lastSyncedAt =
    syncState.status === "idle" && syncState.lastSyncedAt
      ? new Date(syncState.lastSyncedAt)
      : undefined;

  const syncIndicatorState =
    syncState.status === "syncing"
      ? "syncing"
      : syncState.status === "error"
        ? "error"
        : syncState.status === "paused"
          ? "paused"
          : pendingCount > 0
            ? "synced-pending"
            : "idle";

  return (
    <View style={styles.container} testID={testID ?? "mobile-sync-status-bar"}>
      <InFlightSyncIndicator
        surface="mobile-sync"
        pendingCount={pendingCount}
        lastSyncedAt={lastSyncedAt}
        state={syncIndicatorState}
        onManualSync={undefined} // Mobile sync is OS-scheduled foreground only
        onResolve={openDrawer}
        compact={true}
        testID="inflight-sync-indicator"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.neutral[800],
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[2],
    borderTopWidth: 1,
    borderTopColor: colors.neutral[600],
  },
});
