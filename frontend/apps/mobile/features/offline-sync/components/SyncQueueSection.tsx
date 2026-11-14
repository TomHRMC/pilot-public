/**
 * SyncQueueSection — Section header + items within SyncQueueDrawer
 *
 * Location: apps/mobile/features/offline-sync/components/SyncQueueSection.tsx
 *
 * Per batch-fe-b7-design.md Section A.3.2.
 */

import React from "react";
import { View, Text, StyleSheet } from "react-native";
import {
  colors,
  mobileFontSizes,
  fontWeights,
  spacing,
} from "@pilot/ui/tokens";
import { SyncQueueItem, type SyncQueueItemData } from "./SyncQueueItem";

interface SyncQueueSectionProps {
  title: string;
  items: SyncQueueItemData[];
  onRetry?: (id: string) => void;
  onResolveConflict?: (conflictId: string) => void;
  testID?: string;
}

export function SyncQueueSection({
  title,
  items,
  onRetry,
  onResolveConflict,
  testID,
}: SyncQueueSectionProps): React.ReactElement | null {
  if (items.length === 0) return null;

  return (
    <View testID={testID ?? `sync-section-${title}`}>
      <View
        style={styles.header}
        accessibilityRole="header"
        accessibilityLabel={`${title} — ${items.length} items`}
      >
        <Text style={styles.headerText}>{title}</Text>
        <Text style={styles.countBadge}>{items.length}</Text>
      </View>

      {items.map((item) => (
        <SyncQueueItem
          key={item.id}
          item={item}
          onRetry={onRetry}
          onResolveConflict={onResolveConflict}
          testID={`${testID}-item-${item.id}`}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[2],
    backgroundColor: colors.neutral[900],
  },
  headerText: {
    fontSize: mobileFontSizes.caption,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[400],
    textTransform: "uppercase",
    letterSpacing: 0.5,
    lineHeight: 16,
  },
  countBadge: {
    fontSize: mobileFontSizes.caption,
    color: colors.neutral[400],
    lineHeight: 16,
  },
});
