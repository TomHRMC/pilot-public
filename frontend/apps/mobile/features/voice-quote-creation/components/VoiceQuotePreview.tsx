/**
 * VoiceQuotePreview — quote card rendered inside voice session messages
 *
 * Location: apps/mobile/features/voice-quote-creation/components/VoiceQuotePreview.tsx
 *
 * Supports two render modes:
 *   - 'live': fetches current quote data via TanStack Query
 *   - 'snapshot': renders from frozen JSONB payload (NO API call)
 *
 * CRITICAL INVARIANT: live → snapshot transition is ONE-WAY and PERMANENT.
 * Once mode='snapshot', the component NEVER goes back to 'live'.
 * This is enforced by the useRef guard below.
 */

import React, { useRef } from "react";
import { View, Text, Pressable, ScrollView, StyleSheet } from "react-native";
import { useQuery } from "@tanstack/react-query";
import { colors, radii, spacing } from "../../../../../packages/ui/src/tokens";
import type { SnapshotPayload, QuoteLineItem } from "../types-stub";
import { QuoteLineItemRow } from "./QuoteLineItemRow";
import { MarginCard } from "./MarginCard";

const MAX_VISIBLE_LINES = 5;
const DEFAULT_TARGET_MARGIN = 20;

interface VoiceQuotePreviewProps {
  mode: "live" | "snapshot";
  entityId?: string;
  payload?: SnapshotPayload;
  onSubmit?: (quoteId: string) => void;
  readOnly?: boolean;
}

/** Formats cents to USD display string */
function formatCents(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(cents / 100);
}

export function VoiceQuotePreview({
  mode,
  entityId,
  payload,
  onSubmit,
  readOnly = false,
}: VoiceQuotePreviewProps) {
  // INVARIANT: once we've seen 'snapshot', mode can never go back to 'live'
  const hasFrozenRef = useRef(false);
  if (mode === "snapshot") {
    hasFrozenRef.current = true;
  }
  const effectiveMode = hasFrozenRef.current ? "snapshot" : mode;

  // Live mode: fetch current quote data
  const { data: liveData, isLoading } = useQuery({
    queryKey: ["quotes", entityId],
    queryFn: async () => {
      const res = await fetch(`/api/v1/quotes/${entityId}`);
      if (!res.ok) throw new Error("Failed to fetch quote");
      return res.json() as Promise<SnapshotPayload>;
    },
    enabled: effectiveMode === "live" && !!entityId,
  });

  const displayData = effectiveMode === "snapshot" ? payload : liveData;

  if (effectiveMode === "live" && isLoading) {
    return (
      <View style={styles.loadingCard} testID="voice-quote-preview-loading">
        <Text style={styles.loadingText}>Loading quote...</Text>
      </View>
    );
  }

  if (!displayData) {
    return null;
  }

  const visibleLines = displayData.line_items.slice(0, MAX_VISIBLE_LINES);
  const hiddenCount = displayData.line_items.length - MAX_VISIBLE_LINES;
  const submitLabel = displayData.is_tech_role ? "Submit for Approval" : "Send";

  return (
    <View style={styles.card} testID="voice-quote-preview-card">
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.customerName}>{displayData.customer_name}</Text>
          {displayData.customer_address && (
            <Text style={styles.address}>{displayData.customer_address}</Text>
          )}
        </View>
        {effectiveMode === "live" && (
          <View
            style={styles.liveIndicator}
            accessibilityLabel="Live quote data"
          />
        )}
      </View>

      {/* Line items */}
      <ScrollView
        style={styles.lineItems}
        scrollEnabled={false}
        accessibilityRole="list"
        accessibilityLabel="Quote line items"
      >
        {visibleLines.map((line: QuoteLineItem) => (
          <QuoteLineItemRow key={line.id} line={line} isNew={line.is_new} />
        ))}
        {hiddenCount > 0 && (
          <Text style={styles.moreLines}>+{hiddenCount} more items</Text>
        )}
      </ScrollView>

      {/* Footer: total + margin */}
      <View style={styles.footer}>
        <View style={styles.totalRow}>
          <Text style={styles.totalLabel}>Total</Text>
          <Text style={styles.totalValue}>
            {formatCents(displayData.total_cents)}
          </Text>
        </View>
        <MarginCard
          marginPct={displayData.margin_pct}
          tenantTargetPct={DEFAULT_TARGET_MARGIN}
        />
      </View>

      {/* Submit / Send button */}
      {!readOnly && effectiveMode !== "snapshot" && onSubmit && (
        <Pressable
          style={styles.submitBtn}
          onPress={() => onSubmit(displayData.quote_id)}
          accessibilityRole="button"
          accessibilityLabel={submitLabel}
          testID="voice-quote-submit-btn"
        >
          <Text style={styles.submitText}>{submitLabel}</Text>
        </Pressable>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.neutral[50],
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.neutral[200],
    padding: spacing[4],
    marginVertical: spacing[2],
  },
  loadingCard: {
    backgroundColor: colors.neutral[100],
    borderRadius: radii.lg,
    padding: spacing[4],
    alignItems: "center",
  },
  loadingText: {
    color: colors.neutral[400],
    fontSize: 13,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: spacing[3],
  },
  customerName: {
    fontSize: 15,
    color: colors.neutral[900],
  },
  address: {
    fontSize: 11,
    color: colors.neutral[400],
    marginTop: spacing[1],
  },
  liveIndicator: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.margin[400],
    marginTop: spacing[1],
  },
  lineItems: {
    marginBottom: spacing[3],
  },
  moreLines: {
    fontSize: 11,
    color: colors.neutral[400],
    paddingVertical: spacing[2],
    textAlign: "center",
  },
  footer: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: spacing[3],
  },
  totalRow: {
    flex: 1,
  },
  totalLabel: {
    fontSize: 11,
    color: colors.neutral[400],
  },
  totalValue: {
    fontSize: 20,
    color: colors.neutral[900],
  },
  submitBtn: {
    backgroundColor: colors.brand[600],
    borderRadius: radii.md,
    paddingVertical: spacing[3],
    alignItems: "center",
    minHeight: 44,
    justifyContent: "center",
  },
  submitText: {
    color: colors.neutral[50],
    fontSize: 15,
  },
});
