/**
 * QuoteStatusPill — mobile status badge for quote status
 *
 * Location: apps/mobile/features/quote-approval-status/components/QuoteStatusPill.tsx
 */

import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { colors } from "@pilot/ui/tokens";
import type { TechQuoteStatus } from "../hooks/useTechQuotes";

interface QuoteStatusPillProps {
  status: TechQuoteStatus;
  testID?: string;
}

type StatusConfig = {
  label: string;
  bgColor: string;
  textColor: string;
};

const STATUS_CONFIG: Record<TechQuoteStatus, StatusConfig> = {
  draft: {
    label: "Draft",
    bgColor: colors.neutral[100],
    textColor: colors.neutral[600],
  },
  pending_approval: {
    label: "Pending Approval",
    bgColor: colors.alert[100],
    textColor: colors.alert[800],
  },
  approved: {
    label: "Approved",
    bgColor: colors.margin[100],
    textColor: colors.margin[800],
  },
  rejected: {
    label: "Rejected",
    bgColor: colors.fault[100],
    textColor: colors.fault[800],
  },
  sent: {
    label: "Sent",
    bgColor: colors.brand[100],
    textColor: colors.brand[800],
  },
  accepted: {
    label: "Accepted",
    bgColor: colors.margin[100],
    textColor: colors.margin[800],
  },
  declined: {
    label: "Declined",
    bgColor: colors.fault[100],
    textColor: colors.fault[800],
  },
};

export function QuoteStatusPill({ status, testID }: QuoteStatusPillProps) {
  const config = STATUS_CONFIG[status];

  return (
    <View
      testID={testID ?? `status-pill-${status}`}
      style={[styles.pill, { backgroundColor: config.bgColor }]}
      accessibilityLabel={`Status: ${config.label}`}
    >
      <Text style={[styles.text, { color: config.textColor }]}>
        {config.label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 9999,
    alignSelf: "flex-start",
  },
  text: {
    fontSize: 11,
    fontWeight: "500",
  },
});
