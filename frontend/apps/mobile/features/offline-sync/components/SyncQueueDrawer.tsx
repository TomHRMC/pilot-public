/**
 * SyncQueueDrawer — Bottom-sheet sync queue viewer
 *
 * Location: apps/mobile/features/offline-sync/components/SyncQueueDrawer.tsx
 *
 * Opened by tapping ConnectionStatePill. Four sections:
 *   1. Action Needed (conflicts requiring tech review) — shown first
 *   2. Syncing (in progress)
 *   3. Pending (queued, waiting for sync)
 *   4. Recently Synced (last 5 synced items)
 *
 * This is a bottom-sheet modal, NOT a route.
 * Accessibility: section headers use accessibilityRole="header".
 *
 * Per batch-fe-b7-design.md Section A.3.2 and design note in Section C.
 */

import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  Modal,
  Pressable,
  StyleSheet,
  ScrollView,
  SafeAreaView,
} from "react-native";
import {
  colors,
  mobileFontSizes,
  fontWeights,
  spacing,
  radii,
  touchTargets,
} from "@pilot/ui/tokens";
import { useSyncQueueStore } from "../store";
import { SyncQueueSection } from "./SyncQueueSection";
import { SyncNowButton } from "./SyncNowButton";
import { BackgroundSyncStatusRow } from "./BackgroundSyncStatusRow";
import { useBackgroundSyncStatus } from "../hooks/useBackgroundSyncStatus";
import type { SyncQueueItemData } from "./SyncQueueItem";
import type { LocalSyncStatus } from "../../../database/models/SyncableModel";

interface SyncQueueDrawerProps {
  onSync: () => Promise<void>;
  onNavigateToConflict?: (conflictId: string) => void;
  onRetry?: (recordId: string) => void;
  /** All pending/failed/conflict/syncing/recent items from WatermelonDB */
  items?: SyncQueueItemData[];
  /** Called when user taps background sync status row — navigate to sync settings */
  onNavigateToSyncSettings?: () => void;
  testID?: string;
}

export function SyncQueueDrawer({
  onSync,
  onNavigateToConflict,
  onRetry,
  items = [],
  onNavigateToSyncSettings,
  testID,
}: SyncQueueDrawerProps): React.ReactElement {
  const { isDrawerOpen, closeDrawer, syncState } = useSyncQueueStore();
  const backgroundSyncStatus = useBackgroundSyncStatus();

  const actionNeeded = items.filter((i) => i.localSyncStatus === "conflict");
  const syncing = items.filter((i) => i.localSyncStatus === "syncing");
  const pending = items.filter((i) => i.localSyncStatus === "pending");
  const failed = items.filter((i) => i.localSyncStatus === "failed");
  const recentlySynced = items
    .filter((i) => i.localSyncStatus === "synced")
    .slice(-5);

  const lastSyncedAt =
    syncState.status === "idle" && syncState.lastSyncedAt
      ? new Date(syncState.lastSyncedAt).toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        })
      : null;

  return (
    <Modal
      visible={isDrawerOpen}
      animationType="slide"
      transparent={true}
      onRequestClose={closeDrawer}
      testID={testID ?? "sync-queue-drawer"}
    >
      <Pressable
        style={styles.backdrop}
        onPress={closeDrawer}
        accessibilityLabel="Close sync queue"
        testID="drawer-backdrop"
      />

      <SafeAreaView style={styles.sheet} accessibilityViewIsModal={true}>
        {/* Handle */}
        <View style={styles.handle} />

        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.title} accessibilityRole="header">
            Sync Queue
          </Text>
          {lastSyncedAt && (
            <Text style={styles.subtitle}>Last synced {lastSyncedAt}</Text>
          )}
        </View>

        {/* Sync now button */}
        <View style={styles.syncButtonRow}>
          <SyncNowButton onSync={onSync} testID="drawer-sync-now" />
        </View>

        {/* Queue sections */}
        <ScrollView
          style={styles.scrollView}
          showsVerticalScrollIndicator={false}
        >
          {/* Background sync status — FE-B9 — ABOVE four queue sections (RULE 5: observer only) */}
          <BackgroundSyncStatusRow
            status={backgroundSyncStatus}
            onPress={onNavigateToSyncSettings ?? (() => {})}
            testID="drawer-bg-sync-status"
          />

          {/* Action needed first — conflicts */}
          <SyncQueueSection
            title="Action Needed"
            items={actionNeeded}
            onResolveConflict={onNavigateToConflict}
            testID="section-action-needed"
          />

          {/* Syncing */}
          <SyncQueueSection
            title="Syncing"
            items={syncing}
            testID="section-syncing"
          />

          {/* Failed */}
          <SyncQueueSection
            title="Failed — Retry"
            items={failed}
            onRetry={onRetry}
            testID="section-failed"
          />

          {/* Pending */}
          <SyncQueueSection
            title="Pending"
            items={pending}
            testID="section-pending"
          />

          {/* Recently synced */}
          <SyncQueueSection
            title="Recently Synced"
            items={recentlySynced}
            testID="section-recently-synced"
          />

          {/* Empty state */}
          {items.length === 0 && (
            <View style={styles.emptyState}>
              <Text style={styles.emptyIcon}>✓</Text>
              <Text style={styles.emptyText}>All caught up</Text>
              <Text style={styles.emptySubtext}>
                No pending changes to sync
              </Text>
            </View>
          )}
        </ScrollView>

        {/* Close button */}
        <View style={styles.footer}>
          <Pressable
            onPress={closeDrawer}
            style={styles.closeButton}
            accessibilityRole="button"
            accessibilityLabel="Close"
            testID="drawer-close"
          >
            <Text style={styles.closeText}>Close</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.5)",
  },
  sheet: {
    backgroundColor: colors.neutral[900],
    borderTopLeftRadius: radii.xl,
    borderTopRightRadius: radii.xl,
    maxHeight: "80%",
  },
  handle: {
    width: 40,
    height: 4,
    backgroundColor: colors.neutral[600],
    borderRadius: radii.full,
    alignSelf: "center",
    marginTop: spacing[2],
    marginBottom: spacing[3],
  },
  header: {
    paddingHorizontal: spacing[4],
    paddingBottom: spacing[3],
    gap: spacing[1],
  },
  title: {
    fontSize: mobileFontSizes.h2,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 28,
  },
  subtitle: {
    fontSize: mobileFontSizes.caption,
    color: colors.neutral[400],
    lineHeight: 16,
  },
  syncButtonRow: {
    paddingHorizontal: spacing[4],
    paddingBottom: spacing[3],
  },
  scrollView: {
    flex: 1,
  },
  emptyState: {
    alignItems: "center",
    padding: spacing[8],
    gap: spacing[2],
  },
  emptyIcon: {
    fontSize: 40,
    color: colors.margin[400],
  },
  emptyText: {
    fontSize: mobileFontSizes.h3,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 24,
  },
  emptySubtext: {
    fontSize: mobileFontSizes.body,
    color: colors.neutral[400],
    lineHeight: 20,
  },
  footer: {
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
    borderTopWidth: 1,
    borderTopColor: colors.neutral[800],
  },
  closeButton: {
    minHeight: touchTargets.mobile.sm,
    alignItems: "center",
    justifyContent: "center",
  },
  closeText: {
    fontSize: mobileFontSizes.body,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[400],
    lineHeight: 20,
  },
});
