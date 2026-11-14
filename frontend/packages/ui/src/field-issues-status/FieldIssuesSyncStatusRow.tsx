/**
 * FieldIssuesSyncStatusRow — mobile Owner tab status row for field issues
 *
 * Location: packages/ui/src/field-issues-status/FieldIssuesSyncStatusRow.tsx
 *
 * Established FE-B9. Mirrors CalendarSyncStatusRow (FE-B8) pattern.
 * Consumed by apps/mobile/features/owner-tab/components/FieldIssuesSyncStatusSection.tsx.
 *
 * Two states:
 *   healthy (pendingCount === 0) → green dot + "Field issues · None pending"
 *   pending (pendingCount > 0)   → amber dot + "Field issues · N pending" + "Resolve on web →"
 *
 * No error state — escalations queue, they do not fail.
 * Uses React Native primitives (mobile-only).
 * Deep-link URL from webAppBaseUrl prop — never hardcoded (RULE 0).
 *
 * Tokens (from tokens.ts):
 *   colors.margin[500] — healthy dot (green)
 *   colors.alert[500]  — pending dot (amber)
 */

import React from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Linking,
  ActivityIndicator,
} from "react-native";
import { tokens } from "../tokens";

// ─── Types ─────────────────────────────────────────────────────────────────────

export interface FieldIssuesSyncStatusRowProps {
  /** 0 = healthy/no-pending state; >0 = amber pending state */
  pendingCount: number;
  /** True while useFieldIssuesStatus is loading */
  isLoading?: boolean;
  /** Called when owner taps row — opens web URL for resolution */
  onPress: () => void;
  /** Base URL for the web app — from config constant, never hardcoded */
  webAppBaseUrl: string;
  /** Test ID for e2e and unit tests */
  testID?: string;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function FieldIssuesSyncStatusRow({
  pendingCount,
  isLoading = false,
  onPress,
  webAppBaseUrl,
  testID,
}: FieldIssuesSyncStatusRowProps) {
  const isHealthy = pendingCount === 0;

  const handlePress = () => {
    const url = `${webAppBaseUrl}/dashboard/approvals/field-issues`;
    void Linking.openURL(url);
    onPress();
  };

  if (isLoading) {
    return (
      <View
        style={styles.row}
        testID={testID ?? "field-issues-sync-status-row"}
        accessibilityLabel="Field issues status loading"
      >
        <ActivityIndicator
          size="small"
          color={tokens.colors.neutral[400]}
          testID="field-issues-loading-indicator"
        />
        <Text style={styles.title}>Field issues</Text>
      </View>
    );
  }

  const dotColor = isHealthy
    ? tokens.colors.margin[600]
    : tokens.colors.alert[600];

  const subtitle = isHealthy
    ? "None pending"
    : `${pendingCount} pending · Resolve on web →`;

  const content = (
    <View style={styles.row} testID={testID ?? "field-issues-sync-status-row"}>
      {/* Status dot */}
      <View
        style={[styles.dot, { backgroundColor: dotColor }]}
        accessibilityLabel={`Field issues ${isHealthy ? "healthy" : "pending"}`}
        testID={`field-issues-dot-${isHealthy ? "healthy" : "pending"}`}
      />

      {/* Labels */}
      <View style={styles.textBlock}>
        <Text style={styles.title} accessibilityRole="text">
          Field issues
        </Text>
        <Text
          style={[styles.subtitle, !isHealthy && styles.subtitleWarning]}
          accessibilityRole="text"
        >
          {subtitle}
        </Text>
      </View>

      {/* Chevron for pending state */}
      {!isHealthy && (
        <Text
          style={styles.chevron}
          accessibilityElementsHidden={true}
          importantForAccessibility="no"
        >
          ›
        </Text>
      )}
    </View>
  );

  if (!isHealthy) {
    return (
      <TouchableOpacity
        onPress={handlePress}
        activeOpacity={0.7}
        accessibilityLabel={`${pendingCount} field ${pendingCount === 1 ? "issue" : "issues"} pending — tap to resolve on web`}
        accessibilityRole="link"
        accessibilityHint="Opens web conflict resolution"
        testID={`${testID ?? "field-issues-sync-status-row"}-touchable`}
        style={styles.touchable}
      >
        {content}
      </TouchableOpacity>
    );
  }

  return content;
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  touchable: {
    width: "100%",
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing[3],
    paddingVertical: tokens.spacing[3],
    paddingHorizontal: tokens.spacing[4],
    minHeight: tokens.touchTargets.mobile.sm,
  },
  dot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    flexShrink: 0,
  },
  textBlock: {
    flex: 1,
    gap: tokens.spacing[0],
  },
  title: {
    fontSize: tokens.mobileFontSizes.body,
    lineHeight: tokens.mobileLineHeights.body,
    color: tokens.colors.neutral[900],
    fontWeight: "500",
  },
  subtitle: {
    fontSize: tokens.mobileFontSizes.caption,
    lineHeight: tokens.mobileLineHeights.caption,
    color: tokens.colors.neutral[600],
  },
  subtitleWarning: {
    color: tokens.colors.alert[800],
  },
  chevron: {
    fontSize: 20,
    color: tokens.colors.neutral[400],
    flexShrink: 0,
  },
});
