/**
 * ConnectionStatePill — Global sync/connection status pill
 *
 * Location: apps/mobile/features/offline-sync/components/ConnectionStatePill.tsx
 *
 * Four visual states:
 *   hidden (idle, 0 pending)  → renders null
 *   amber pulsing             → pending items or syncing
 *   red solid                 → sync error / conflict
 *   red action-needed         → requires_review conflicts needing tech action
 *
 * Tapping opens the SyncQueueDrawer bottom sheet.
 * Token colors (NO hardcoded hex):
 *   syncing/pending  → colors.alert[400] amber
 *   error/conflict   → colors.fault[400] red
 *
 * Per batch-fe-b7-design.md Section A.3.2.
 */

import React from "react";
import { View, Text, Pressable, StyleSheet, Animated } from "react-native";
import {
  colors,
  mobileFontSizes,
  fontWeights,
  spacing,
  radii,
} from "@pilot/ui/tokens";
import { useSyncQueueStore } from "../store";

type PillState = "hidden" | "syncing" | "pending" | "error" | "conflict";

function getPillState(
  status: string,
  pendingCount: number,
  hasConflict: boolean,
): PillState {
  if (hasConflict) return "conflict";
  if (status === "error") return "error";
  if (status === "syncing") return "syncing";
  if (pendingCount > 0) return "pending";
  return "hidden";
}

export function ConnectionStatePill(): React.ReactElement | null {
  const { syncState, openDrawer } = useSyncQueueStore();
  const pendingCount = syncState.pendingCount;
  const hasConflict =
    "error" in syncState && syncState.error?.message.includes("conflict");

  const pillState = getPillState(syncState.status, pendingCount, !!hasConflict);

  if (pillState === "hidden") return null;

  const isAmber = pillState === "syncing" || pillState === "pending";
  const bgColor = isAmber ? colors.alert[400] : colors.fault[400];
  const textColor = colors.neutral[900];

  const label =
    pillState === "syncing"
      ? "Syncing…"
      : pillState === "conflict"
        ? `${pendingCount} action needed`
        : pillState === "error"
          ? "Sync error"
          : `${pendingCount} pending`;

  return (
    <Pressable
      onPress={openDrawer}
      style={[styles.pill, { backgroundColor: bgColor }]}
      accessibilityRole="button"
      accessibilityLabel={label}
      testID="connection-state-pill"
    >
      <View style={styles.dot} />
      <Text style={[styles.label, { color: textColor }]} numberOfLines={1}>
        {label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  pill: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[1],
    borderRadius: radii.full,
    gap: spacing[1],
    alignSelf: "center",
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: radii.full,
    backgroundColor: colors.neutral[900],
    opacity: 0.7,
  },
  label: {
    fontSize: mobileFontSizes.caption,
    fontWeight: String(fontWeights.medium) as "500",
    lineHeight: 16,
  },
});
