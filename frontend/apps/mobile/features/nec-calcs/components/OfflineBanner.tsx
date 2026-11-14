/**
 * OfflineBanner — Shown when NEC calc used the offline TypeScript engine
 *
 * Location: apps/mobile/features/nec-calcs/components/OfflineBanner.tsx
 *
 * Renders only when isOfflineCalc=true. Copy exactly per design doc §F.7.
 * No "verify online" language — user decides when to recalculate.
 *
 * Per batch-mob-b4-design.md §F.7.
 */

import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { tokens } from "@pilot/ui/tokens";

interface OfflineBannerProps {
  testID?: string;
}

export function OfflineBanner({
  testID = "offline-banner",
}: OfflineBannerProps) {
  return (
    <View style={styles.banner} testID={testID}>
      <Text style={styles.text}>⚠️ Offline — using NEC 2023 code formulas</Text>
      <Text style={styles.subtext}>
        Result saved locally and will sync when online
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    backgroundColor: tokens.colors.alert[50],
    borderWidth: 1,
    borderColor: tokens.colors.alert[200],
    borderRadius: tokens.radii.md,
    paddingHorizontal: tokens.spacing[4],
    paddingVertical: tokens.spacing[3],
    marginHorizontal: tokens.spacing[4],
    marginBottom: tokens.spacing[3],
  },
  text: {
    fontSize: tokens.webFontSizes.body,
    fontWeight: "600" as const,
    color: tokens.colors.alert[800],
    marginBottom: tokens.spacing[1],
  },
  subtext: {
    fontSize: tokens.webFontSizes.caption,
    color: tokens.colors.alert[600],
  },
});
