/**
 * Sync Pending Overview Route
 *
 * Location: apps/mobile/app/(tabs)/(home)/sync/index.tsx
 *
 * Route: (tabs)/(home)/sync
 * Auth: Required (tech role)
 *
 * Full-screen list of pending operations; accessible from MobileSyncStatusBar tap.
 * Renders SyncQueueSection items grouped by status.
 *
 * MOB-B6: Manual sync now calls the actual SyncOrchestrator.sync('manual') via
 * the triggerSync function registered in useSyncQueueStore by the orchestrator.
 *
 * Per batch-fe-b7-design.md Section C and Section A.4.
 */

import React, { useCallback } from "react";
import { View, Text, ScrollView, StyleSheet, SafeAreaView } from "react-native";
import { useRouter } from "expo-router";
import { RoleGate } from "@pilot/ui";
import {
  colors,
  mobileFontSizes,
  fontWeights,
  spacing,
} from "@pilot/ui/tokens";
import { useSyncQueueStore } from "../../../../features/offline-sync/store";
import { SyncQueueSection } from "../../../../features/offline-sync/components/SyncQueueSection";
import { SyncNowButton } from "../../../../features/offline-sync/components/SyncNowButton";
// MOB-B2: Real pending items from WatermelonDB (replaces PLACEHOLDER_ITEMS)
import { usePendingSyncItems } from "../../../../features/offline-sync/hooks/usePendingSyncItems";

export default function SyncPendingScreen(): React.ReactElement {
  const router = useRouter();
  const { syncState, triggerSync } = useSyncQueueStore();
  const { items } = usePendingSyncItems();

  const handleSync = useCallback(async () => {
    if (triggerSync) {
      // MOB-B6: Use actual SyncOrchestrator.sync('manual') registered in the store
      await triggerSync();
    } else {
      // SyncOrchestrator not yet initialized (app startup race) — log and no-op
      console.warn(
        "[SyncPendingScreen] triggerSync not yet available — SyncOrchestrator not initialized",
      );
    }
  }, [triggerSync]);

  const handleNavigateToConflict = useCallback(
    (conflictId: string) => {
      router.push(`/(tabs)/(home)/sync/conflict/${conflictId}` as any);
    },
    [router],
  );

  const pendingCount = syncState.pendingCount;

  return (
    <RoleGate role="technician">
      <SafeAreaView style={styles.container} testID="sync-pending-screen">
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.title} accessibilityRole="header">
            Sync Queue
          </Text>
          <Text style={styles.subtitle}>
            {pendingCount} pending{" "}
            {pendingCount === 1 ? "operation" : "operations"}
          </Text>
        </View>

        {/* Sync now */}
        <View style={styles.syncRow}>
          <SyncNowButton onSync={handleSync} testID="sync-screen-now-button" />
        </View>

        {/* Queue sections */}
        <ScrollView
          style={styles.scrollView}
          showsVerticalScrollIndicator={false}
        >
          <SyncQueueSection
            title="Action Needed"
            items={items.filter((i) => i.localSyncStatus === "conflict")}
            onResolveConflict={handleNavigateToConflict}
            testID="screen-action-needed"
          />
          <SyncQueueSection
            title="Syncing"
            items={items.filter((i) => i.localSyncStatus === "syncing")}
            testID="screen-syncing"
          />
          <SyncQueueSection
            title="Failed"
            items={items.filter((i) => i.localSyncStatus === "failed")}
            testID="screen-failed"
          />
          <SyncQueueSection
            title="Pending"
            items={items.filter((i) => i.localSyncStatus === "pending")}
            testID="screen-pending"
          />

          {items.length === 0 && (
            <View style={styles.emptyState}>
              <Text style={styles.emptyIcon}>✓</Text>
              <Text style={styles.emptyTitle}>All synced</Text>
              <Text style={styles.emptyText}>No pending operations</Text>
            </View>
          )}
        </ScrollView>
      </SafeAreaView>
    </RoleGate>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[900],
  },
  header: {
    paddingHorizontal: spacing[4],
    paddingTop: spacing[4],
    paddingBottom: spacing[3],
    gap: spacing[1],
  },
  title: {
    fontSize: mobileFontSizes.h1,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 30,
  },
  subtitle: {
    fontSize: mobileFontSizes.body,
    color: colors.neutral[400],
    lineHeight: 20,
  },
  syncRow: {
    paddingHorizontal: spacing[4],
    paddingBottom: spacing[3],
  },
  scrollView: {
    flex: 1,
  },
  emptyState: {
    alignItems: "center",
    padding: spacing[10],
    gap: spacing[3],
  },
  emptyIcon: {
    fontSize: 48,
    lineHeight: 56,
    color: colors.margin[400],
  },
  emptyTitle: {
    fontSize: mobileFontSizes.h2,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 28,
  },
  emptyText: {
    fontSize: mobileFontSizes.body,
    color: colors.neutral[400],
    lineHeight: 20,
  },
});
