/**
 * ProjectedMarginSection — Live profitability display
 *
 * Location: apps/mobile/features/jobs/components/detail/ProjectedMarginSection.tsx
 *
 * Uses useProjectedMargin(jobId) which refreshes on every screen focus.
 * Response shape is an open object (openapi.json: additionalProperties: true).
 * Known fields: margin_percent, quoted_hours, actual_hours, cost_delta_cents,
 * etc_hours_remaining.
 *
 * Per batch-mob-b2-design.md §F.6 and §D.7.
 */

import React from "react";
import { View, Text, ActivityIndicator, StyleSheet } from "react-native";
import {
  colors,
  mobileFontSizes,
  fontWeights,
  spacing,
  radii,
} from "@pilot/ui/tokens";
import { useProjectedMargin } from "../../hooks/useProjectedMargin";

interface ProjectedMarginSectionProps {
  jobId: string;
  testID?: string;
}

export function ProjectedMarginSection({
  jobId,
  testID,
}: ProjectedMarginSectionProps): React.ReactElement {
  const { data, isLoading, isError } = useProjectedMargin(jobId);

  const marginPct =
    typeof data?.margin_percent === "number" ? data.margin_percent : null;
  const quotedHours =
    typeof data?.quoted_hours === "number" ? data.quoted_hours : null;
  const actualHours =
    typeof data?.actual_hours === "number" ? data.actual_hours : null;
  const costDeltaCents =
    typeof data?.cost_delta_cents === "number" ? data.cost_delta_cents : null;
  const etcRemaining =
    typeof data?.etc_hours_remaining === "number"
      ? data.etc_hours_remaining
      : null;

  const isOverBudget = costDeltaCents !== null && costDeltaCents > 0;
  const marginColor =
    marginPct === null
      ? colors.neutral[400]
      : marginPct >= 25
        ? colors.margin[600]
        : marginPct >= 10
          ? colors.alert[400]
          : colors.fault[600];

  const costDeltaFormatted =
    costDeltaCents !== null
      ? `${isOverBudget ? "+" : ""}$${(Math.abs(costDeltaCents) / 100).toFixed(2)}`
      : null;

  return (
    <View
      style={styles.container}
      testID={testID ?? "projected-margin-section"}
    >
      <Text style={styles.sectionTitle}>LIVE PROFITABILITY</Text>

      {isLoading && (
        <ActivityIndicator
          color={colors.brand[400]}
          testID="margin-loading"
          style={styles.loader}
        />
      )}

      {isError && !isLoading && (
        <Text style={styles.errorText} testID="margin-error">
          Unable to load profitability data
        </Text>
      )}

      {!isLoading && !isError && data && (
        <View style={styles.dataRow}>
          {/* Margin % */}
          {marginPct !== null && (
            <View style={styles.metricCard}>
              <Text style={[styles.metricValue, { color: marginColor }]}>
                {marginPct.toFixed(0)}%
              </Text>
              <Text style={styles.metricLabel}>Margin</Text>
            </View>
          )}

          {/* Actual vs Quoted hours */}
          {actualHours !== null && quotedHours !== null && (
            <View style={styles.metricCard}>
              <Text style={styles.metricValue}>{actualHours.toFixed(1)}h</Text>
              <Text style={styles.metricLabel}>
                of {quotedHours.toFixed(1)}h quoted
              </Text>
            </View>
          )}

          {/* Cost delta */}
          {costDeltaFormatted !== null && (
            <View style={styles.metricCard}>
              <Text
                style={[
                  styles.metricValue,
                  isOverBudget
                    ? { color: colors.fault[600] }
                    : { color: colors.margin[600] },
                ]}
              >
                {costDeltaFormatted}
              </Text>
              <Text style={styles.metricLabel}>Cost delta</Text>
            </View>
          )}

          {/* ETC remaining */}
          {etcRemaining !== null && (
            <View style={styles.metricCard}>
              <Text style={styles.metricValue}>{etcRemaining.toFixed(1)}h</Text>
              <Text style={styles.metricLabel}>Remaining</Text>
            </View>
          )}
        </View>
      )}

      {!isLoading && !isError && !data && (
        <Text style={styles.emptyText}>No profitability data available</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.neutral[800],
    borderRadius: radii.md,
    padding: spacing[4],
    marginBottom: spacing[3],
    gap: spacing[3],
  },
  sectionTitle: {
    fontSize: mobileFontSizes.caption,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[400],
    textTransform: "uppercase",
    letterSpacing: 0.5,
    lineHeight: 16,
  },
  loader: {
    alignSelf: "flex-start",
  },
  dataRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing[3],
  },
  metricCard: {
    minWidth: 80,
    gap: spacing[1],
  },
  metricValue: {
    fontSize: mobileFontSizes.h2,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 28,
  },
  metricLabel: {
    fontSize: mobileFontSizes.caption,
    color: colors.neutral[400],
    lineHeight: 16,
  },
  errorText: {
    fontSize: mobileFontSizes.body,
    color: colors.fault[400],
    lineHeight: 20,
  },
  emptyText: {
    fontSize: mobileFontSizes.body,
    color: colors.neutral[400],
    lineHeight: 20,
  },
});
