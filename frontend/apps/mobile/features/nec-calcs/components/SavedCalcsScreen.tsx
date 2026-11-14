/**
 * SavedCalcsScreen — List of previously saved NEC calculations
 *
 * Location: apps/mobile/features/nec-calcs/components/SavedCalcsScreen.tsx
 *
 * Fetches from GET /api/v1/nec/calc-logs (max 50).
 * Each row shows: calc type badge, result_value, pass/fail dot, offline chip, timestamp.
 *
 * Per batch-mob-b4-design.md §F.8.
 */

import React from "react";
import {
  SafeAreaView,
  View,
  Text,
  FlatList,
  Pressable,
  RefreshControl,
  ActivityIndicator,
  StyleSheet,
} from "react-native";
import { router } from "expo-router";
import { tokens } from "@pilot/ui/tokens";
import { useNecCalcLogs } from "../hooks/useNecCalcLogs";
import type { SavedNecCalcLog } from "../hooks/useNecCalcLogs";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const CALC_TYPE_LABELS: Record<string, string> = {
  voltage_drop: "Voltage Drop",
  conduit_fill: "Conduit Fill",
  ampacity: "Ampacity",
};

function formatResultValue(log: SavedNecCalcLog): string {
  const rv = (log.result_json as { result_value?: number }).result_value;
  if (rv == null) return "—";
  switch (log.calc_type) {
    case "voltage_drop": {
      const pct = (log.result_json as { voltage_drop_pct?: number })
        .voltage_drop_pct;
      return pct != null
        ? `${rv.toFixed(2)} V (${pct.toFixed(2)}%)`
        : `${rv.toFixed(2)} V`;
    }
    case "conduit_fill":
      return `${rv.toFixed(1)}%`;
    case "ampacity":
      return `${rv.toFixed(1)} A`;
    default:
      return String(rv);
  }
}

function formatTimestamp(ts: string | null): string {
  if (!ts) return "Unknown time";
  try {
    const d = new Date(ts);
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return ts;
  }
}

// ---------------------------------------------------------------------------
// SavedCalcRow
// ---------------------------------------------------------------------------

function SavedCalcRow({ log }: { log: SavedNecCalcLog }) {
  const isCompliant = (log.result_json as { is_compliant?: boolean })
    .is_compliant;

  return (
    <View style={rowStyles.container} testID={`saved-calc-row-${log.id}`}>
      {/* Calc type badge */}
      <View style={rowStyles.badge}>
        <Text style={rowStyles.badgeText}>
          {CALC_TYPE_LABELS[log.calc_type] ?? log.calc_type}
        </Text>
      </View>

      {/* Result value */}
      <Text style={rowStyles.resultValue}>{formatResultValue(log)}</Text>

      <View style={rowStyles.metaRow}>
        {/* Pass/fail indicator */}
        <View
          style={[
            rowStyles.passDot,
            isCompliant ? rowStyles.passDotGreen : rowStyles.passDotRed,
          ]}
        />
        <Text style={rowStyles.metaText}>{isCompliant ? "Pass" : "Fail"}</Text>

        {/* Offline chip */}
        {log.is_offline_calc && (
          <View style={rowStyles.offlineChip}>
            <Text style={rowStyles.offlineChipText}>Offline</Text>
          </View>
        )}

        {/* Timestamp */}
        <Text style={rowStyles.timestamp}>
          {formatTimestamp(log.client_capture_at)}
        </Text>
      </View>
    </View>
  );
}

const rowStyles = StyleSheet.create({
  container: {
    paddingHorizontal: tokens.spacing[4],
    paddingVertical: tokens.spacing[3],
    borderBottomWidth: 1,
    borderBottomColor: tokens.colors.neutral[200],
    backgroundColor: "#fff",
  },
  badge: {
    alignSelf: "flex-start",
    backgroundColor: tokens.colors.brand[100],
    borderRadius: tokens.radii.full,
    paddingHorizontal: tokens.spacing[2],
    paddingVertical: 2,
    marginBottom: tokens.spacing[1],
  },
  badgeText: {
    fontSize: tokens.webFontSizes.caption,
    fontWeight: "600" as const,
    color: tokens.colors.brand[800],
  },
  resultValue: {
    fontSize: tokens.webFontSizes.bodyLg,
    fontWeight: "600" as const,
    color: tokens.colors.neutral[900],
    marginBottom: tokens.spacing[1],
  },
  metaRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing[2],
  },
  passDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  passDotGreen: { backgroundColor: tokens.colors.margin[400] },
  passDotRed: { backgroundColor: tokens.colors.fault[400] },
  metaText: {
    fontSize: tokens.webFontSizes.caption,
    color: tokens.colors.neutral[600],
  },
  offlineChip: {
    backgroundColor: tokens.colors.alert[100],
    borderRadius: tokens.radii.full,
    paddingHorizontal: tokens.spacing[2],
    paddingVertical: 1,
  },
  offlineChipText: {
    fontSize: tokens.webFontSizes.caption,
    color: tokens.colors.alert[800],
    fontWeight: "500" as const,
  },
  timestamp: {
    fontSize: tokens.webFontSizes.caption,
    color: tokens.colors.neutral[400],
    marginLeft: "auto",
  },
});

// ---------------------------------------------------------------------------
// Main Screen
// ---------------------------------------------------------------------------

export function SavedCalcsScreen() {
  const { data: logs, isLoading, isError, refetch } = useNecCalcLogs();

  return (
    <SafeAreaView style={styles.safeArea}>
      {/* Header */}
      <View style={styles.header}>
        <Pressable
          onPress={() => router.back()}
          style={styles.backBtn}
          accessibilityRole="button"
          accessibilityLabel="Back to Calcs"
          testID="back-button"
        >
          <Text style={styles.backText}>← Calcs</Text>
        </Pressable>
        <Text style={styles.title}>🕐 Saved Calculations</Text>
      </View>

      {isLoading && (
        <View style={styles.centered}>
          <ActivityIndicator size="large" testID="loading-indicator" />
        </View>
      )}

      {isError && !isLoading && (
        <View style={styles.centered} testID="error-state">
          <Text style={styles.errorText}>
            Failed to load saved calculations
          </Text>
          <Pressable onPress={() => refetch()} style={styles.retryBtn}>
            <Text style={styles.retryText}>Try Again</Text>
          </Pressable>
        </View>
      )}

      {!isLoading && !isError && (
        <FlatList
          data={logs ?? []}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => <SavedCalcRow log={item} />}
          ListEmptyComponent={
            <View style={styles.centered} testID="empty-state">
              <Text style={styles.emptyText}>No saved calculations yet</Text>
              <Text style={styles.emptySubtext}>
                Complete a calculation to see it here
              </Text>
            </View>
          }
          refreshControl={
            <RefreshControl
              refreshing={isLoading}
              onRefresh={refetch}
              testID="refresh-control"
            />
          }
          testID="saved-calcs-list"
        />
      )}
    </SafeAreaView>
  );
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: tokens.colors.neutral[50] },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: tokens.spacing[4],
    paddingVertical: tokens.spacing[3],
    borderBottomWidth: 1,
    borderBottomColor: tokens.colors.neutral[200],
  },
  backBtn: { marginRight: tokens.spacing[3] },
  backText: {
    fontSize: tokens.webFontSizes.body,
    color: tokens.colors.brand[600],
    fontWeight: "500" as const,
  },
  title: {
    fontSize: tokens.webFontSizes.h2,
    fontWeight: "700" as const,
    color: tokens.colors.neutral[900],
  },
  centered: {
    flex: 1,
    alignItems: "center" as const,
    justifyContent: "center" as const,
    padding: tokens.spacing[8],
  },
  errorText: {
    fontSize: tokens.webFontSizes.bodyLg,
    color: tokens.colors.fault[800],
    textAlign: "center" as const,
    marginBottom: tokens.spacing[3],
  },
  retryBtn: {
    paddingHorizontal: tokens.spacing[4],
    paddingVertical: tokens.spacing[2],
    backgroundColor: tokens.colors.brand[600],
    borderRadius: tokens.radii.md,
  },
  retryText: {
    fontSize: tokens.webFontSizes.body,
    color: "#fff",
    fontWeight: "600" as const,
  },
  emptyText: {
    fontSize: tokens.webFontSizes.bodyLg,
    color: tokens.colors.neutral[800],
    fontWeight: "600" as const,
    textAlign: "center" as const,
    marginBottom: tokens.spacing[2],
  },
  emptySubtext: {
    fontSize: tokens.webFontSizes.body,
    color: tokens.colors.neutral[400],
    textAlign: "center" as const,
  },
});
