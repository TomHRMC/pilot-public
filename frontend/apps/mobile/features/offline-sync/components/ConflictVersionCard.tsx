/**
 * ConflictVersionCard — "Your version" or "Server version" card
 *
 * Location: apps/mobile/features/offline-sync/components/ConflictVersionCard.tsx
 *
 * Composes <DiffView variant="entity"> from FE-B5 to show field-level diffs.
 * Uses showToggle={true} and defaultShowChanges={true} (fields visible by default
 * in conflict context per design doc §G.5).
 *
 * Per batch-fe-b7-design.md Section A.3.3 and §G.5.
 */

import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { DiffView } from "@pilot/ui/diff-view";
import {
  colors,
  mobileFontSizes,
  fontWeights,
  spacing,
  radii,
} from "@pilot/ui/tokens";
import type { DiffField } from "@pilot/ui";
import type { OfflineEntityType } from "../../../database/sync/types";

interface ConflictVersionCardProps {
  /** 'local' = "Your version", 'server' = "Server version" */
  perspective: "local" | "server";
  entityType: OfflineEntityType;
  fieldDiffs: DiffField[];
  isSelected?: boolean;
  testID?: string;
}

export function ConflictVersionCard({
  perspective,
  fieldDiffs,
  isSelected = false,
  testID,
}: ConflictVersionCardProps): React.ReactElement {
  const label = perspective === "local" ? "Your version" : "Server version";
  const borderColor = isSelected ? colors.brand[400] : colors.neutral[600];

  return (
    <View
      style={[styles.card, { borderColor }]}
      testID={testID ?? `conflict-card-${perspective}`}
      accessible={true}
      accessibilityLabel={label}
    >
      <View style={styles.cardHeader}>
        <Text style={styles.cardTitle}>{label}</Text>
        {isSelected && (
          <View style={styles.selectedBadge}>
            <Text style={styles.selectedBadgeText}>Selected</Text>
          </View>
        )}
      </View>

      <DiffView variant="entity" fieldDiffs={fieldDiffs} entityLabel={label} />
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 2,
    borderRadius: radii.lg,
    overflow: "hidden",
    backgroundColor: colors.neutral[800],
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[600],
  },
  cardTitle: {
    fontSize: mobileFontSizes.bodyLg,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 22,
  },
  selectedBadge: {
    backgroundColor: colors.brand[400] + "33",
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
    borderRadius: radii.sm,
  },
  selectedBadgeText: {
    fontSize: mobileFontSizes.caption,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.brand[400],
    lineHeight: 16,
  },
});
