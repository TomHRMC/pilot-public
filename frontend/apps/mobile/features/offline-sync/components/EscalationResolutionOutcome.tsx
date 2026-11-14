/**
 * EscalationResolutionOutcome — terminal state display for resolved SyncQueueItem
 *
 * Location: apps/mobile/features/offline-sync/components/EscalationResolutionOutcome.tsx
 *
 * Established FE-B9. Renders in SyncQueueItem when escalation resolves (three terminal states).
 *
 * Resolution outcomes (design doc Decision 6):
 *   resolved_in_favor_of_tech   → success animation affordance (dismiss)
 *   resolved_in_favor_of_server → 24-hour display then auto-dismiss copy
 *   resolved_with_action        → job-restored context shown
 *
 * Tokens: colors.margin (success), colors.neutral (neutral), colors.alert (warning)
 */

import React from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import {
  colors,
  mobileFontSizes,
  mobileLineHeights,
  spacing,
  radii,
  touchTargets,
} from "@pilot/ui/tokens";

// ─── Types ─────────────────────────────────────────────────────────────────────

export type EscalationOutcome =
  | "resolved_in_favor_of_tech"
  | "resolved_in_favor_of_server"
  | "resolved_with_action";

export interface EscalationResolutionOutcomeProps {
  outcome: EscalationOutcome;
  /** Tech name — used in copy */
  techName: string;
  /** Operation type for context */
  operationType?: string;
  /** Job title for resolved_with_action */
  jobTitle?: string | null;
  /** Callback when tech dismisses the outcome card */
  onDismiss?: () => void;
  testID?: string;
}

// ─── Copy configs per outcome ─────────────────────────────────────────────────

function getOutcomeConfig(
  outcome: EscalationOutcome,
  techName: string,
  jobTitle?: string | null,
): {
  icon: string;
  title: string;
  body: string;
  dismissLabel: string;
  dotColor: string;
  borderColor: string;
  bgColor: string;
} {
  switch (outcome) {
    case "resolved_in_favor_of_tech":
      return {
        icon: "✓",
        title: "Your data was kept",
        body: `The owner reviewed your ${techName ? `${techName}'s` : ""} capture and committed your version.`,
        dismissLabel: "Got it",
        dotColor: colors.margin[400],
        borderColor: colors.margin[200],
        bgColor: colors.margin[50] ?? colors.neutral[50],
      };
    case "resolved_in_favor_of_server":
      return {
        icon: "↩",
        title: "Server version accepted",
        body: `The owner chose the server version. Your offline capture has been discarded. This notice will dismiss after 24 hours.`,
        dismissLabel: "Dismiss",
        dotColor: colors.neutral[400],
        borderColor: colors.neutral[200],
        bgColor: colors.neutral[100],
      };
    case "resolved_with_action":
      return {
        icon: "↺",
        title: "Action taken — job restored",
        body: jobTitle
          ? `The owner resolved the conflict for "${jobTitle}". Your captured data has been applied and the job is back in queue.`
          : "The owner resolved the conflict and your captured data has been applied.",
        dismissLabel: "Got it",
        dotColor: colors.margin[400],
        borderColor: colors.margin[200],
        bgColor: colors.margin[50] ?? colors.neutral[50],
      };
  }
}

// ─── Component ────────────────────────────────────────────────────────────────

export function EscalationResolutionOutcome({
  outcome,
  techName,
  operationType,
  jobTitle,
  onDismiss,
  testID,
}: EscalationResolutionOutcomeProps) {
  const config = getOutcomeConfig(outcome, techName, jobTitle);

  return (
    <View
      style={[
        styles.container,
        {
          borderColor: config.borderColor,
          backgroundColor: config.bgColor,
        },
      ]}
      testID={testID ?? `escalation-outcome-${outcome}`}
      accessibilityRole="alert"
    >
      {/* Icon + title */}
      <View style={styles.header}>
        <View style={[styles.iconCircle, { backgroundColor: config.dotColor }]}>
          <Text style={styles.icon}>{config.icon}</Text>
        </View>
        <Text style={styles.title}>{config.title}</Text>
      </View>

      {/* Body copy */}
      <Text style={styles.body}>{config.body}</Text>

      {/* Operation type tag */}
      {operationType && (
        <Text style={styles.tag}>{operationType.replace("_", " ")}</Text>
      )}

      {/* Dismiss button */}
      {onDismiss && (
        <Pressable
          onPress={onDismiss}
          style={styles.dismissButton}
          accessibilityRole="button"
          accessibilityLabel={config.dismissLabel}
          testID="escalation-outcome-dismiss"
        >
          <Text style={styles.dismissLabel}>{config.dismissLabel}</Text>
        </Pressable>
      )}
    </View>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    borderWidth: 1,
    borderRadius: radii.md,
    padding: spacing[4],
    gap: spacing[2],
    marginVertical: spacing[1],
    marginHorizontal: spacing[4],
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[3],
  },
  iconCircle: {
    width: 28,
    height: 28,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
  },
  icon: {
    fontSize: 14,
    color: colors.neutral[50],
    fontWeight: "700",
  },
  title: {
    fontSize: mobileFontSizes.body,
    lineHeight: mobileLineHeights.body,
    fontWeight: "600",
    color: colors.neutral[900],
    flex: 1,
  },
  body: {
    fontSize: mobileFontSizes.caption,
    lineHeight: mobileLineHeights.caption,
    color: colors.neutral[600],
  },
  tag: {
    fontSize: mobileFontSizes.caption,
    color: colors.neutral[400],
    textTransform: "capitalize",
  },
  dismissButton: {
    alignSelf: "flex-start",
    minHeight: touchTargets.mobile.sm,
    paddingVertical: spacing[1],
    paddingHorizontal: spacing[2],
  },
  dismissLabel: {
    fontSize: mobileFontSizes.caption,
    lineHeight: mobileLineHeights.caption,
    color: colors.neutral[600],
    fontWeight: "500",
    textDecorationLine: "underline",
  },
});
