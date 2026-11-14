/**
 * QuoteLineItemRow — single line item in a quote preview
 *
 * Location: apps/mobile/features/voice-quote-creation/components/QuoteLineItemRow.tsx
 */

import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { colors, spacing } from "../../../../../packages/ui/src/tokens";
import type { QuoteLineItem } from "../types-stub";

interface QuoteLineItemRowProps {
  line: QuoteLineItem;
  isNew?: boolean;
}

function formatCents(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(cents / 100);
}

export function QuoteLineItemRow({
  line,
  isNew = false,
}: QuoteLineItemRowProps) {
  return (
    <View
      style={[styles.row, isNew && styles.newRow]}
      accessible
      accessibilityLabel={`${line.description}, quantity ${line.quantity}, total ${formatCents(line.total_cents)}`}
      testID={`quote-line-${line.id}`}
    >
      <View style={styles.descCol}>
        <Text style={styles.description} numberOfLines={2}>
          {line.description}
        </Text>
        <Text style={styles.qty}>Qty: {line.quantity}</Text>
      </View>
      <Text style={styles.total}>{formatCents(line.total_cents)}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    paddingVertical: spacing[2],
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[200],
  },
  newRow: {
    backgroundColor: colors.margin[50],
  },
  descCol: {
    flex: 1,
    marginRight: spacing[3],
  },
  description: {
    fontSize: 13,
    color: colors.neutral[900],
  },
  qty: {
    fontSize: 11,
    color: colors.neutral[400],
    marginTop: spacing[1],
  },
  total: {
    fontSize: 13,
    color: colors.neutral[900],
  },
});
