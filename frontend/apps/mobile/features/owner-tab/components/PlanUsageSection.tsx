/**
 * PlanUsageSection — Owner tab: subscription tier + usage summary
 *
 * Location: apps/mobile/features/owner-tab/components/PlanUsageSection.tsx
 *
 * Shows current tier name, trial expiry (if applicable), and usage stats.
 * Fails silently — returns null if data unavailable (non-critical section).
 *
 * UsageSummaryResponse fields (confirmed from openapi.json):
 *   { current_user_count, current_sms_segment_count, period_start, period_end }
 *
 * MOB-B5
 */

import React from "react";
import { View, Text, ActivityIndicator, StyleSheet } from "react-native";
import { tokens } from "@pilot/ui/tokens";
import { useOwnerPlanUsage } from "../hooks/useOwnerPlanUsage";

export function PlanUsageSection() {
  const { data, isLoading } = useOwnerPlanUsage();

  if (isLoading) {
    return (
      <View style={styles.row} testID="plan-loading">
        <ActivityIndicator size="small" color={tokens.colors.neutral[400]} />
      </View>
    );
  }

  // Fail silently — plan section is non-critical
  if (!data) return null;

  const tier = data.current_tier;
  const trialEndsAt = data.trial_ends_at
    ? new Date(data.trial_ends_at).toLocaleDateString()
    : null;
  const usage = data.usage;

  return (
    <View style={styles.row} testID="plan-usage-section">
      <Text style={styles.sectionLabel}>Plan</Text>
      <Text style={styles.valueText}>{tier.display_label}</Text>

      {trialEndsAt && (
        <Text style={styles.trialText}>Trial ends {trialEndsAt}</Text>
      )}

      {usage && (
        <View style={styles.usageRow}>
          <Text style={styles.usageStat}>
            {usage.current_user_count}
            {tier.max_users != null ? `/${tier.max_users}` : ""} users
          </Text>
          {tier.max_sms_segments_per_month != null && (
            <Text style={styles.usageStat}>
              SMS: {usage.current_sms_segment_count}/
              {tier.max_sms_segments_per_month} this month
            </Text>
          )}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    backgroundColor: "#FFFFFF",
    borderRadius: 8,
    padding: tokens.spacing[3],
    gap: tokens.spacing[1],
  },
  sectionLabel: {
    fontSize: tokens.mobileFontSizes.caption,
    lineHeight: tokens.mobileLineHeights.caption,
    color: tokens.colors.neutral[600],
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  valueText: {
    fontSize: tokens.mobileFontSizes.body,
    lineHeight: tokens.mobileLineHeights.body,
    color: tokens.colors.neutral[900],
  },
  trialText: {
    fontSize: tokens.mobileFontSizes.caption,
    lineHeight: tokens.mobileLineHeights.caption,
    color: tokens.colors.alert[600],
  },
  usageRow: {
    flexDirection: "row",
    gap: tokens.spacing[3],
    marginTop: tokens.spacing[1],
  },
  usageStat: {
    fontSize: tokens.mobileFontSizes.caption,
    lineHeight: tokens.mobileLineHeights.caption,
    color: tokens.colors.neutral[600],
  },
});
