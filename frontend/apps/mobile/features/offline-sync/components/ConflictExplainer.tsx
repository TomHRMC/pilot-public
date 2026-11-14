/**
 * ConflictExplainer — Plain-language conflict description
 *
 * Location: apps/mobile/features/offline-sync/components/ConflictExplainer.tsx
 *
 * Renders at the top of ConflictResolutionScreen.
 * Accessibility: focus is set here on mount by ConflictResolutionScreen.
 *
 * Per batch-fe-b7-design.md Section A.3.3.
 */

import React from "react";
import { View, Text, StyleSheet } from "react-native";
import {
  colors,
  mobileFontSizes,
  fontWeights,
  spacing,
  radii,
} from "@pilot/ui/tokens";
import type { OfflineEntityType } from "../../../database/sync/types";

const ENTITY_LABEL: Record<OfflineEntityType, string> = {
  time_entry: "time entry",
  expense: "expense",
  photo: "photo",
  change_order: "change order",
  loto_check: "LOTO check",
  job_status_change: "job status change",
  job_note: "job note",
  voice_audio: "voice recording",
  invoice_signoff: "invoice sign-off",
};

interface ConflictExplainerProps {
  entityType: OfflineEntityType;
  entitySummary: string;
  testID?: string;
}

export function ConflictExplainer({
  entityType,
  entitySummary,
  testID,
}: ConflictExplainerProps): React.ReactElement {
  const entityLabel = ENTITY_LABEL[entityType];

  return (
    <View
      style={styles.container}
      testID={testID ?? "conflict-explainer"}
      accessible={true}
      accessibilityLabel={`Sync conflict for ${entityLabel}: ${entitySummary}`}
    >
      <View style={styles.iconRow}>
        <Text style={styles.icon}>⚠️</Text>
        <Text style={styles.title}>Sync conflict</Text>
      </View>

      <Text style={styles.description}>
        Your {entityLabel} was updated by someone else while you were offline.
        Choose which version to keep.
      </Text>

      <View style={styles.summaryBox}>
        <Text style={styles.summaryLabel}>Affected record</Text>
        <Text style={styles.summaryText} numberOfLines={2}>
          {entitySummary}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: spacing[4],
    gap: spacing[3],
  },
  iconRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[2],
  },
  icon: {
    fontSize: 24,
    lineHeight: 28,
  },
  title: {
    fontSize: mobileFontSizes.h2,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 28,
  },
  description: {
    fontSize: mobileFontSizes.body,
    color: colors.neutral[200],
    lineHeight: 20,
  },
  summaryBox: {
    backgroundColor: colors.neutral[800],
    borderRadius: radii.md,
    padding: spacing[3],
    gap: spacing[1],
  },
  summaryLabel: {
    fontSize: mobileFontSizes.caption,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[400],
    textTransform: "uppercase",
    letterSpacing: 0.5,
    lineHeight: 16,
  },
  summaryText: {
    fontSize: mobileFontSizes.body,
    color: colors.neutral[50],
    lineHeight: 20,
  },
});
