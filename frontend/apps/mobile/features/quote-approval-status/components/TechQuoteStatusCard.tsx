/**
 * TechQuoteStatusCard — single card in tech's quote status list
 *
 * Location: apps/mobile/features/quote-approval-status/components/TechQuoteStatusCard.tsx
 */

import React from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import { colors, spacing, radii } from "@pilot/ui/tokens";
import { QuoteStatusPill } from "./QuoteStatusPill";
import type { TechQuoteSummary } from "../hooks/useTechQuotes";

interface TechQuoteStatusCardProps {
  quote: TechQuoteSummary;
  onPress: (quoteId: string) => void;
}

function formatCents(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(cents / 100);
}

function formatDate(iso: string | null): string {
  if (!iso) return "Not submitted";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function TechQuoteStatusCard({
  quote,
  onPress,
}: TechQuoteStatusCardProps) {
  return (
    <Pressable
      onPress={() => onPress(quote.id)}
      style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
      accessibilityRole="button"
      accessibilityLabel={`Quote ${quote.quote_number} for ${quote.customer_name}, ${quote.status}`}
      testID={`tech-quote-card-${quote.id}`}
    >
      <View style={styles.header}>
        <Text style={styles.quoteNumber}>#{quote.quote_number}</Text>
        <QuoteStatusPill
          status={quote.status}
          testID={`status-pill-${quote.id}`}
        />
      </View>

      <Text style={styles.customerName}>{quote.customer_name}</Text>

      <View style={styles.footer}>
        <Text style={styles.total}>{formatCents(quote.total_cents)}</Text>
        <Text style={styles.date}>{formatDate(quote.submitted_at)}</Text>
      </View>

      {quote.has_owner_edits && (
        <View style={styles.ownerEditsBadge}>
          <Text style={styles.ownerEditsText}>Owner made changes →</Text>
        </View>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: radii.lg,
    padding: spacing[4],
    marginBottom: spacing[3],
    borderWidth: 1,
    borderColor: colors.neutral[200],
  },
  cardPressed: {
    backgroundColor: colors.neutral[50],
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: spacing[1],
  },
  quoteNumber: {
    fontSize: 15,
    fontWeight: "500",
    color: colors.neutral[900],
  },
  customerName: {
    fontSize: 13,
    color: colors.neutral[600],
    marginBottom: spacing[2],
  },
  footer: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  total: {
    fontSize: 15,
    fontWeight: "500",
    color: colors.neutral[900],
  },
  date: {
    fontSize: 11,
    color: colors.neutral[400],
  },
  ownerEditsBadge: {
    marginTop: spacing[2],
    backgroundColor: colors.brand[50],
    borderRadius: radii.sm,
    paddingHorizontal: spacing[2],
    paddingVertical: spacing[1],
    alignSelf: "flex-start",
  },
  ownerEditsText: {
    fontSize: 11,
    color: colors.brand[800],
    fontWeight: "500",
  },
});
