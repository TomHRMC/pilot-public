/**
 * SyncQueueItem — Single queue item row in SyncQueueDrawer
 *
 * Location: apps/mobile/features/offline-sync/components/SyncQueueItem.tsx
 *
 * Shows: entity type icon, entity summary, sync status pill, timestamp, action CTA.
 * Action CTAs: retry (failed), resolve (conflict), view escalation (escalated).
 *
 * Token colors (NO hardcoded hex):
 *   pending  → colors.alert[400]
 *   syncing  → colors.brand[400]
 *   synced   → colors.margin[600]
 *   failed   → colors.fault[600]
 *   conflict → colors.fault[600]
 *
 * Per batch-fe-b7-design.md Section A.3.2.
 */

import React from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import {
  colors,
  mobileFontSizes,
  fontWeights,
  spacing,
  radii,
} from "@pilot/ui/tokens";
import type { LocalSyncStatus } from "../../../database/models/SyncableModel";
import type { OfflineEntityType } from "../../../database/sync/types";

const STATUS_COLOR: Record<LocalSyncStatus, string> = {
  pending: colors.alert[400],
  syncing: colors.brand[400],
  synced: colors.margin[600],
  failed: colors.fault[600],
  conflict: colors.fault[600],
};

const STATUS_LABEL: Record<LocalSyncStatus, string> = {
  pending: "Pending",
  syncing: "Syncing…",
  synced: "Synced",
  failed: "Failed",
  conflict: "Conflict",
};

const ENTITY_ICON: Record<OfflineEntityType | string, string> = {
  time_entry: "⏱",
  expense: "💰",
  photo: "📷",
  change_order: "📋",
  loto_check: "🔒",
  job_status_change: "🔄",
  job_note: "📝",
  voice_audio: "🎙",
};

export interface SyncQueueItemData {
  id: string;
  entityType: OfflineEntityType;
  entitySummary: string;
  localSyncStatus: LocalSyncStatus;
  clientCaptureAt: Date;
  conflictId?: string;
}

interface SyncQueueItemProps {
  item: SyncQueueItemData;
  onRetry?: (id: string) => void;
  onResolveConflict?: (conflictId: string) => void;
  testID?: string;
}

export function SyncQueueItem({
  item,
  onRetry,
  onResolveConflict,
  testID,
}: SyncQueueItemProps): React.ReactElement {
  const statusColor = STATUS_COLOR[item.localSyncStatus];
  const statusLabel = STATUS_LABEL[item.localSyncStatus];
  const icon = ENTITY_ICON[item.entityType] ?? "•";

  const showRetry = item.localSyncStatus === "failed" && onRetry;
  const showResolve =
    item.localSyncStatus === "conflict" && item.conflictId && onResolveConflict;

  return (
    <View
      style={styles.container}
      testID={testID ?? `sync-queue-item-${item.id}`}
      accessible={true}
      accessibilityLabel={`${item.entitySummary} — ${statusLabel}`}
    >
      {/* Entity icon */}
      <Text style={styles.icon}>{icon}</Text>

      {/* Main content */}
      <View style={styles.content}>
        <Text style={styles.summary} numberOfLines={1}>
          {item.entitySummary}
        </Text>
        <Text style={styles.timestamp}>
          {item.clientCaptureAt.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </Text>
      </View>

      {/* Status pill + CTA */}
      <View style={styles.statusArea}>
        <View
          style={[styles.statusPill, { backgroundColor: statusColor + "33" }]}
        >
          <Text style={[styles.statusText, { color: statusColor }]}>
            {statusLabel}
          </Text>
        </View>

        {showRetry && (
          <Pressable
            onPress={() => onRetry(item.id)}
            style={styles.cta}
            accessibilityRole="button"
            accessibilityLabel="Retry sync"
            testID={`retry-${item.id}`}
          >
            <Text style={styles.ctaText}>Retry</Text>
          </Pressable>
        )}

        {showResolve && (
          <Pressable
            onPress={() => onResolveConflict(item.conflictId!)}
            style={[styles.cta, styles.ctaConflict]}
            accessibilityRole="button"
            accessibilityLabel="Resolve conflict"
            testID={`resolve-${item.id}`}
          >
            <Text style={[styles.ctaText, { color: colors.fault[600] }]}>
              Resolve
            </Text>
          </Pressable>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: spacing[3],
    paddingHorizontal: spacing[4],
    backgroundColor: colors.neutral[800],
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[600],
    gap: spacing[3],
  },
  icon: {
    fontSize: 20,
    lineHeight: 24,
  },
  content: {
    flex: 1,
    gap: 2,
  },
  summary: {
    fontSize: mobileFontSizes.body,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 20,
  },
  timestamp: {
    fontSize: mobileFontSizes.caption,
    color: colors.neutral[400],
    lineHeight: 16,
  },
  statusArea: {
    alignItems: "flex-end",
    gap: spacing[1],
  },
  statusPill: {
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
    borderRadius: radii.sm,
  },
  statusText: {
    fontSize: mobileFontSizes.caption,
    fontWeight: String(fontWeights.medium) as "500",
    lineHeight: 16,
  },
  cta: {
    paddingVertical: 2,
    paddingHorizontal: spacing[1],
  },
  ctaConflict: {},
  ctaText: {
    fontSize: mobileFontSizes.caption,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.brand[400],
    lineHeight: 16,
  },
});
