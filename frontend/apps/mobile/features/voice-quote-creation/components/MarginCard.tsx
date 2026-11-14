/**
 * MarginCard — profit margin indicator
 *
 * Location: apps/mobile/features/voice-quote-creation/components/MarginCard.tsx
 */

import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { colors, radii, spacing } from "../../../../../packages/ui/src/tokens";

interface MarginCardProps {
  marginPct: number;
  tenantTargetPct: number;
  testID?: string;
}

export function MarginCard({
  marginPct,
  tenantTargetPct,
  testID = "margin-card",
}: MarginCardProps) {
  const isOnTarget = marginPct >= tenantTargetPct;
  const bg = isOnTarget ? colors.margin[50] : colors.alert[50];
  const textColor = isOnTarget ? colors.margin[800] : colors.alert[800];

  return (
    <View
      style={[
        styles.card,
        {
          backgroundColor: bg,
          borderColor: isOnTarget ? colors.margin[200] : colors.alert[200],
        },
      ]}
      testID={testID}
      accessibilityLabel={`Margin ${marginPct.toFixed(0)}% — ${isOnTarget ? "on target" : "below target"}`}
      accessible
    >
      <Text style={[styles.pct, { color: textColor }]}>
        {marginPct.toFixed(0)}%
      </Text>
      <Text style={[styles.label, { color: textColor }]}>
        {isOnTarget ? "On Target" : `Target: ${tenantTargetPct}%`}
      </Text>
      {!isOnTarget && (
        <Text style={[styles.advisory, { color: colors.alert[600] }]}>
          Below target margin
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: radii.md,
    borderWidth: 1,
    padding: spacing[3],
    alignItems: "center",
    minWidth: 80,
  },
  pct: {
    fontSize: 20,
  },
  label: {
    fontSize: 11,
    marginTop: spacing[1],
  },
  advisory: {
    fontSize: 10,
    marginTop: spacing[1],
  },
});
