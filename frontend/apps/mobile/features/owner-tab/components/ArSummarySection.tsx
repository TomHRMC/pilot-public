/**
 * ArSummarySection — Owner tab: accounts receivable summary
 *
 * Location: apps/mobile/features/owner-tab/components/ArSummarySection.tsx
 *
 * Shows outstanding invoice count + overdue badge (derived client-side from due_at).
 * Taps deep-link to web AR management page.
 * Empty state: "No outstanding invoices" when outstandingCount === 0.
 *
 * MOB-B5
 */

import React from "react";
import {
  View,
  Text,
  Pressable,
  ActivityIndicator,
  Linking,
  StyleSheet,
} from "react-native";
import { tokens, lightTheme } from "@pilot/ui/tokens";
import { useOwnerArSummary } from "../hooks/useOwnerArSummary";

const WEB_APP_BASE_URL =
  process.env.EXPO_PUBLIC_WEB_APP_URL ?? "https://app.pilotfortrades.com";

export function ArSummarySection() {
  const { data, isLoading } = useOwnerArSummary();

  const handlePress = () => {
    void Linking.openURL(`${WEB_APP_BASE_URL}/invoices`);
  };

  if (isLoading) {
    return (
      <View style={styles.row} testID="ar-loading">
        <ActivityIndicator size="small" color={tokens.colors.neutral[400]} />
      </View>
    );
  }

  const outstandingCount = data?.outstandingCount ?? 0;
  const overdueCount = data?.overdueCount ?? 0;

  if (outstandingCount === 0) {
    return (
      <View style={styles.row} testID="ar-summary-section">
        <Text style={styles.sectionLabel}>Accounts Receivable</Text>
        <Text style={styles.allCaughtUp}>No outstanding invoices</Text>
      </View>
    );
  }

  return (
    <Pressable
      onPress={handlePress}
      testID="ar-summary-section"
      accessibilityRole="button"
      accessibilityLabel={`${outstandingCount} outstanding invoices${overdueCount > 0 ? `, ${overdueCount} overdue` : ""}`}
    >
      <View style={styles.row}>
        <Text style={styles.sectionLabel}>Accounts Receivable</Text>
        <View style={styles.countRow}>
          <Text style={styles.valueText}>{outstandingCount} outstanding</Text>
          {overdueCount > 0 && (
            <View style={styles.overdueBadge} testID="ar-overdue-badge">
              <Text style={styles.overdueBadgeText}>
                {overdueCount} overdue
              </Text>
            </View>
          )}
        </View>
      </View>
    </Pressable>
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
  countRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing[2],
  },
  valueText: {
    fontSize: tokens.mobileFontSizes.body,
    lineHeight: tokens.mobileLineHeights.body,
    color: tokens.colors.neutral[900],
  },
  allCaughtUp: {
    fontSize: tokens.mobileFontSizes.body,
    lineHeight: tokens.mobileLineHeights.body,
    color: tokens.colors.margin[600],
  },
  overdueBadge: {
    backgroundColor: lightTheme.danger.bgMuted,
    borderRadius: 4,
    paddingHorizontal: tokens.spacing[2],
    paddingVertical: 2,
  },
  overdueBadgeText: {
    fontSize: tokens.mobileFontSizes.caption,
    color: lightTheme.danger.textOnMuted,
    fontWeight: "600",
  },
});
