/**
 * CalcResultDisplay — Shared pass/fail result component for NEC calculators
 *
 * Location: apps/mobile/features/nec-calcs/components/CalcResultDisplay.tsx
 *
 * Renders for all 3 calc types (voltage_drop, conduit_fill, ampacity).
 * Shows green ✓ PASS or red ✗ FAIL badge + primary value + NEC citation.
 *
 * Per batch-mob-b4-design.md §F.6.
 */

import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { tokens } from "@pilot/ui/tokens";
import type { NecCalcResult } from "../hooks/useNecCalculate";

interface CalcResultDisplayProps {
  result: NecCalcResult;
  testID?: string;
}

function formatResultValue(result: NecCalcResult): string {
  switch (result.calc_type) {
    case "voltage_drop": {
      const vdPct = (result as NecCalcResult & { voltage_drop_pct?: number })
        .voltage_drop_pct;
      return `Voltage Drop: ${result.result_value.toFixed(2)} V${vdPct != null ? ` (${vdPct.toFixed(2)}%)` : ""}`;
    }
    case "conduit_fill":
      return `Fill: ${result.result_value.toFixed(1)}%`;
    case "ampacity":
      return `Adjusted Ampacity: ${result.result_value.toFixed(1)} A`;
    default:
      return `Result: ${result.result_value}`;
  }
}

export function CalcResultDisplay({ result, testID }: CalcResultDisplayProps) {
  const isPass = result.is_compliant;

  return (
    <View style={styles.container} testID={testID ?? "calc-result-display"}>
      {/* Pass / Fail badge */}
      <View
        style={[styles.badge, isPass ? styles.passBadge : styles.failBadge]}
      >
        <Text
          style={[styles.badgeText, isPass ? styles.passText : styles.failText]}
          testID={isPass ? "result-pass-badge" : "result-fail-badge"}
        >
          {isPass ? "✓ PASS" : "✗ FAIL"}
        </Text>
      </View>

      {/* Primary value */}
      <Text style={styles.primaryValue}>{formatResultValue(result)}</Text>

      {/* NEC citation */}
      <Text style={styles.citation}>{result.nec_citation}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginTop: tokens.spacing[4],
    marginHorizontal: tokens.spacing[4],
    padding: tokens.spacing[4],
    backgroundColor: tokens.colors.neutral[50],
    borderRadius: tokens.radii.lg,
    borderWidth: 1,
    borderColor: tokens.colors.neutral[200],
  },
  badge: {
    alignSelf: "flex-start",
    borderRadius: tokens.radii.full,
    paddingHorizontal: tokens.spacing[3],
    paddingVertical: tokens.spacing[1],
    marginBottom: tokens.spacing[3],
  },
  passBadge: {
    backgroundColor: tokens.colors.margin[100],
  },
  failBadge: {
    backgroundColor: tokens.colors.fault[100],
  },
  badgeText: {
    fontSize: tokens.webFontSizes.body,
    fontWeight: "700" as const,
    letterSpacing: 0.5,
  },
  passText: {
    color: tokens.colors.margin[800],
  },
  failText: {
    color: tokens.colors.fault[800],
  },
  primaryValue: {
    fontSize: tokens.webFontSizes.bodyLg,
    fontWeight: "600" as const,
    color: tokens.colors.neutral[900],
    marginBottom: tokens.spacing[2],
  },
  citation: {
    fontSize: tokens.webFontSizes.caption,
    color: tokens.colors.neutral[600],
    lineHeight: 18,
  },
});
