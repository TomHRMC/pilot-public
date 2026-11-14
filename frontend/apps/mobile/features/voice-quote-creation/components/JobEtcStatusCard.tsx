/**
 * JobEtcStatusCard — Job profitability status card for voice session messages
 *
 * Location: apps/mobile/features/voice-quote-creation/components/JobEtcStatusCard.tsx
 *
 * Supports two render modes (per VoiceQuotePreview live/snapshot pattern):
 *   - 'live': fetches projected margin from GET /api/v1/jobs/{entityId}/projected-margin
 *   - 'snapshot': renders from frozen JSONB payload (NO API call)
 *
 * Displays:
 *   - Customer name or job identifier
 *   - Actual cost vs quoted budget (formatted as $X.XX)
 *   - Projected margin % with green/amber/red color indicator
 *   - Hours remaining (ETC)
 *
 * Per batch-mob-b6-design.md Step 6.
 * PRD §3.13 live/snapshot mode pattern.
 */

import React from "react";
import { View, Text, ActivityIndicator, StyleSheet } from "react-native";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { colors, radii, spacing } from "../../../../../packages/ui/src/tokens";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface JobEtcStatusPayload {
  job_id?: string;
  customer_name?: string;
  actual_cost_cents?: number;
  quoted_budget_cents?: number;
  projected_margin_pct?: number;
  hours_remaining?: number;
}

interface ProjectedMarginResponse {
  job_id: string;
  projected_margin_pct: number;
  actual_cost_cents: number;
  quoted_budget_cents: number;
  hours_remaining?: number;
  customer_name?: string;
}

export interface JobEtcStatusCardProps {
  mode: "live" | "snapshot";
  entityId?: string; // jobId for live mode
  payload?: JobEtcStatusPayload; // snapshot_payload for snapshot mode
  testID?: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatCents(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(cents / 100);
}

const TARGET_MARGIN_PCT = 20;
const AMBER_MARGIN_PCT = 10;

function getMarginColor(marginPct: number): string {
  if (marginPct >= TARGET_MARGIN_PCT) return colors.margin[400]; // green
  if (marginPct >= AMBER_MARGIN_PCT) return colors.alert[400]; // amber
  return colors.fault[400]; // red
}

// ── Component ─────────────────────────────────────────────────────────────────

export function JobEtcStatusCard({
  mode,
  entityId,
  payload,
  testID,
}: JobEtcStatusCardProps): React.ReactElement | null {
  const { data: liveData, isLoading } = useQuery({
    queryKey: ["jobs", entityId, "projected-margin"],
    queryFn: async (): Promise<ProjectedMarginResponse> => {
      const res = await apiClient.get(
        `/api/v1/jobs/${entityId}/projected-margin`,
      );
      return res.data as ProjectedMarginResponse;
    },
    enabled: mode === "live" && !!entityId,
    staleTime: 60_000,
    retry: false,
  });

  if (mode === "live" && isLoading) {
    return (
      <View
        style={styles.card}
        testID={testID ?? "job-etc-status-card-loading"}
      >
        <ActivityIndicator
          color={colors.brand[400]}
          size="small"
          testID="job-etc-loading-indicator"
        />
        <Text style={styles.loadingText}>Loading job status...</Text>
      </View>
    );
  }

  const display: JobEtcStatusPayload =
    mode === "snapshot"
      ? (payload ?? {})
      : {
          job_id: liveData?.job_id,
          customer_name: liveData?.customer_name,
          actual_cost_cents: liveData?.actual_cost_cents,
          quoted_budget_cents: liveData?.quoted_budget_cents,
          projected_margin_pct: liveData?.projected_margin_pct,
          hours_remaining: liveData?.hours_remaining,
        };

  const marginPct = display.projected_margin_pct ?? 0;
  const marginColor = getMarginColor(marginPct);

  return (
    <View style={styles.card} testID={testID ?? "job-etc-status-card"}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.label}>JOB STATUS</Text>
        {mode === "live" && (
          <View
            style={styles.liveIndicator}
            accessibilityLabel="Live job data"
            testID="live-indicator"
          />
        )}
      </View>

      {/* Customer name */}
      {display.customer_name ? (
        <Text style={styles.customerName} testID="customer-name">
          {display.customer_name}
        </Text>
      ) : null}

      {/* Cost row */}
      {display.actual_cost_cents !== undefined &&
      display.quoted_budget_cents !== undefined ? (
        <View style={styles.costRow}>
          <View style={styles.costItem}>
            <Text style={styles.costLabel}>Actual Cost</Text>
            <Text style={styles.costValue} testID="actual-cost">
              {formatCents(display.actual_cost_cents)}
            </Text>
          </View>
          <Text style={styles.costDivider}>vs</Text>
          <View style={styles.costItem}>
            <Text style={styles.costLabel}>Budget</Text>
            <Text style={styles.costValue} testID="quoted-budget">
              {formatCents(display.quoted_budget_cents)}
            </Text>
          </View>
        </View>
      ) : null}

      {/* Margin */}
      <View style={styles.marginRow}>
        <View
          style={[styles.marginDot, { backgroundColor: marginColor }]}
          testID="margin-indicator"
        />
        <Text style={styles.marginLabel}>Projected Margin</Text>
        <Text
          style={[styles.marginValue, { color: marginColor }]}
          testID="margin-pct"
        >
          {marginPct.toFixed(1)}%
        </Text>
      </View>

      {/* Hours remaining */}
      {display.hours_remaining !== undefined ? (
        <View style={styles.etcRow}>
          <Text style={styles.etcLabel}>ETC</Text>
          <Text style={styles.etcValue} testID="hours-remaining">
            {display.hours_remaining}h remaining
          </Text>
        </View>
      ) : null}
    </View>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.neutral[50],
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.neutral[200],
    padding: spacing[4],
    marginVertical: spacing[2],
    gap: spacing[3],
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  label: {
    fontSize: 11,
    color: colors.neutral[400],
    letterSpacing: 0.5,
    lineHeight: 14,
  },
  liveIndicator: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.margin[400],
  },
  customerName: {
    fontSize: 15,
    color: colors.neutral[900],
    lineHeight: 20,
  },
  loadingText: {
    fontSize: 13,
    color: colors.neutral[400],
    lineHeight: 18,
    marginLeft: spacing[2],
  },
  costRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[3],
  },
  costItem: {
    flex: 1,
  },
  costLabel: {
    fontSize: 11,
    color: colors.neutral[400],
    lineHeight: 14,
  },
  costValue: {
    fontSize: 15,
    color: colors.neutral[900],
    lineHeight: 20,
  },
  costDivider: {
    fontSize: 13,
    color: colors.neutral[400],
    lineHeight: 18,
  },
  marginRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[2],
  },
  marginDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    flexShrink: 0,
  },
  marginLabel: {
    fontSize: 13,
    color: colors.neutral[600],
    flex: 1,
    lineHeight: 18,
  },
  marginValue: {
    fontSize: 15,
    lineHeight: 20,
  },
  etcRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[2],
  },
  etcLabel: {
    fontSize: 11,
    color: colors.neutral[400],
    letterSpacing: 0.5,
    lineHeight: 14,
  },
  etcValue: {
    fontSize: 13,
    color: colors.neutral[600],
    lineHeight: 18,
  },
});
