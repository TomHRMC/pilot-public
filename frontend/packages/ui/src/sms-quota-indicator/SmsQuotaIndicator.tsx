/**
 * SmsQuotaIndicator — SMS quota footer for the reply composer
 *
 * Location: packages/ui/src/sms-quota-indicator/SmsQuotaIndicator.tsx
 * Platform: Mobile (React Native / Gluestack primitives)
 * Exported from: packages/ui/src/index.ts under // ── FE-B10 Exports ──
 *
 * Visual states per design doc Section D.5 and E:
 *   normal    → neutral[600] text (subdued annotation)
 *   warning   → alert[600] text, alert[50] bg
 *   blocked_soft  → fault[800] text, fault[50] bg
 *   blocked_hard  → fault[800] text, fault[50] bg + Send disabled externally
 *   opted_out → fault[800] text, fault[50] bg
 *
 * RULE: No hex values or raw pixel values. All from tokens.ts color ramp stops.
 */

import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { colors, spacing, mobileFontSizes, fontWeights } from "../tokens";
import { deriveQuotaState } from "./utils";
import type { SmsQuotaIndicatorProps } from "./types";

export function SmsQuotaIndicator({
  quota,
  currentMessageSegmentCount,
  isLoading = false,
  testID,
}: SmsQuotaIndicatorProps) {
  const visualState = deriveQuotaState(quota);

  if (isLoading) {
    return (
      <View style={styles.container} testID={testID}>
        <Text style={styles.normalText}>Loading quota…</Text>
      </View>
    );
  }

  if (visualState.state === "opted_out") {
    return (
      <View style={[styles.container, styles.blockedContainer]} testID={testID}>
        <Text style={styles.blockedText}>
          Customer has opted out — they cannot be reached via SMS
        </Text>
      </View>
    );
  }

  if (visualState.state === "blocked_hard") {
    return (
      <View style={[styles.container, styles.blockedContainer]} testID={testID}>
        <Text style={styles.blockedText}>
          Monthly SMS limit reached — contact your owner to adjust your plan
        </Text>
      </View>
    );
  }

  if (visualState.state === "blocked_soft") {
    return (
      <View style={[styles.container, styles.warningContainer]} testID={testID}>
        <Text style={styles.warningText}>
          Monthly quota reached — overages billed at $0.05/segment
        </Text>
        {currentMessageSegmentCount > 0 && (
          <Text style={styles.segmentAnnotationWarning}>
            {`This message: ${currentMessageSegmentCount} segment${currentMessageSegmentCount !== 1 ? "s" : ""}`}
          </Text>
        )}
      </View>
    );
  }

  if (visualState.state === "warning") {
    return (
      <View style={[styles.container, styles.warningContainer]} testID={testID}>
        <Text style={styles.warningText}>
          {`⚠ ${visualState.remaining} segment${visualState.remaining !== 1 ? "s" : ""} left this month`}
        </Text>
        {currentMessageSegmentCount > 0 && (
          <Text style={styles.segmentAnnotationWarning}>
            {`This message: ${currentMessageSegmentCount} segment${currentMessageSegmentCount !== 1 ? "s" : ""}`}
          </Text>
        )}
      </View>
    );
  }

  // normal state
  return (
    <View style={styles.container} testID={testID}>
      <Text style={styles.normalText}>
        {`${visualState.remaining} segment${visualState.remaining !== 1 ? "s" : ""} remaining this month`}
        {currentMessageSegmentCount > 0
          ? ` · This message: ${currentMessageSegmentCount}`
          : ""}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[2],
  },
  warningContainer: {
    backgroundColor: colors.alert[50],
    borderTopWidth: 1,
    borderTopColor: colors.alert[200],
  },
  blockedContainer: {
    backgroundColor: colors.fault[50],
    borderTopWidth: 1,
    borderTopColor: colors.fault[200],
  },
  normalText: {
    fontSize: mobileFontSizes.caption,
    color: colors.neutral[600], // neutral-600 = subdued annotation text
  },
  warningText: {
    fontSize: mobileFontSizes.caption,
    color: colors.alert[600],
    fontWeight: String(fontWeights.medium) as "500",
  },
  blockedText: {
    fontSize: mobileFontSizes.caption,
    color: colors.fault[800], // fault[800] — closest to design doc fault-700
    fontWeight: String(fontWeights.medium) as "500",
  },
  segmentAnnotationWarning: {
    fontSize: mobileFontSizes.caption,
    color: colors.alert[600],
    marginTop: 2,
  },
});
