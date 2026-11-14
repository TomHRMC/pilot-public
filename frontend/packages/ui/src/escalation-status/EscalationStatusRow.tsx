/**
 * EscalationStatusRow — Mobile-to-web escalation status display
 *
 * Location: packages/ui/src/escalation-status/EscalationStatusRow.tsx
 *
 * Displays the status of a conflict escalated to the owner.
 * Uses react-native primitives + token values (NO hardcoded hex).
 *
 * Token color mapping:
 *   pending  → colors.alert[400] amber — "Owner reviewing"
 *   resolved → colors.margin[600] green — "Owner resolved"
 *   rejected → colors.neutral[400] neutral — "Owner declined"
 *
 * Note: `Linking.openURL` is handled by the consumer to avoid importing
 * react-native's Linking in web builds. Pass `onViewOnWeb` callback.
 * If omitted, the component uses `window.open` (web) or is a no-op.
 *
 * Per batch-fe-b7-design.md Section F.3, §16.11, and §G.6.
 */

import React from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import {
  colors,
  mobileFontSizes,
  fontWeights,
  spacing,
  radii,
} from "../tokens";
import type { EscalationStatusRowProps, EscalationStatus } from "./types";

const ACCENT_COLOR: Record<EscalationStatus, string> = {
  pending: colors.alert[400],
  resolved: colors.margin[600],
  rejected: colors.neutral[400],
};

const STATUS_LABEL: Record<EscalationStatus, string> = {
  pending: "Owner reviewing your sync conflict",
  resolved: "Owner resolved",
  rejected: "Owner declined — your version discarded",
};

export function EscalationStatusRow({
  entitySummary,
  status,
  escalatedAt,
  webDeepLink,
  resolutionMessage,
  testID,
  onViewOnWeb,
}: EscalationStatusRowProps & {
  onViewOnWeb?: () => void;
}): React.ReactElement {
  const accentColor = ACCENT_COLOR[status];
  const statusLabel = STATUS_LABEL[status];

  const handleViewOnWeb = (): void => {
    if (onViewOnWeb) {
      onViewOnWeb();
    } else if (typeof window !== "undefined") {
      window.open(webDeepLink, "_blank");
    }
  };

  return (
    <View
      style={[styles.container, { borderLeftColor: accentColor }]}
      testID={testID ?? "escalation-status-row"}
      accessible={true}
      accessibilityLabel={`Escalation ${status}: ${entitySummary}`}
    >
      <Text style={styles.entitySummary} numberOfLines={2}>
        {entitySummary}
      </Text>

      <View style={styles.statusRow}>
        <View style={[styles.statusDot, { backgroundColor: accentColor }]} />
        <Text style={[styles.statusLabel, { color: accentColor }]}>
          {statusLabel}
        </Text>
      </View>

      {resolutionMessage &&
        (status === "resolved" || status === "rejected") && (
          <Text style={styles.resolutionMessage} numberOfLines={2}>
            {resolutionMessage}
          </Text>
        )}

      <Text style={styles.timestamp}>
        Escalated {new Date(escalatedAt).toLocaleDateString()}
      </Text>

      {status === "pending" && (
        <Pressable
          onPress={handleViewOnWeb}
          style={styles.deepLinkButton}
          accessibilityRole="link"
          accessibilityHint="Opens owner resolution page in browser"
          testID={testID ? `${testID}-web-link` : "escalation-web-link"}
        >
          <Text style={[styles.deepLinkText, { color: accentColor }]}>
            View on web →
          </Text>
        </Pressable>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.neutral[800],
    borderLeftWidth: 3,
    borderRadius: radii.md,
    padding: spacing[3],
    marginVertical: spacing[1],
    gap: spacing[1],
  },
  entitySummary: {
    fontSize: mobileFontSizes.body,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 20,
  },
  statusRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[1],
    marginTop: spacing[1],
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: radii.full,
  },
  statusLabel: {
    fontSize: mobileFontSizes.caption,
    fontWeight: String(fontWeights.regular) as "400",
    lineHeight: 16,
  },
  resolutionMessage: {
    fontSize: mobileFontSizes.caption,
    color: colors.neutral[200],
    lineHeight: 16,
  },
  timestamp: {
    fontSize: mobileFontSizes.caption,
    color: colors.neutral[400],
    lineHeight: 16,
  },
  deepLinkButton: {
    marginTop: spacing[1],
    alignSelf: "flex-start",
    paddingVertical: 2,
  },
  deepLinkText: {
    fontSize: mobileFontSizes.body,
    fontWeight: String(fontWeights.medium) as "500",
  },
});
