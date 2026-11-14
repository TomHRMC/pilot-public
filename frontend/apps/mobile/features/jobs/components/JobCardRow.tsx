/**
 * JobCardRow — Single job card in the Jobs tab list (MOB-B1)
 *
 * Location: apps/mobile/features/jobs/components/JobCardRow.tsx
 *
 * Displays: customer name, scheduled time range, status pill, estimated duration.
 * Tap → calls onPress(job.id) so the parent can navigate to the detail screen.
 *
 * Status pill colors use pilotPreset tokens (no hardcoded hex values).
 * Status codes are hardcoded for MVP (no dynamic status list endpoint exists).
 */

import React from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import { colors, spacing, radii } from "@pilot/ui/tokens";
import type { JobListItem } from "../job-types";

interface JobCardRowProps {
  job: JobListItem;
  onPress: (jobId: string) => void;
  testID?: string;
}

// ── Status pill config (MVP hardcoded — no dynamic endpoint exists) ────────────

type StatusCode = "scheduled" | "in_progress" | "completed";

interface StatusStyle {
  bg: string;
  text: string;
  label: string;
}

const STATUS_MAP: Record<StatusCode, StatusStyle> = {
  scheduled: {
    bg: colors.brand[50],
    text: colors.brand[800],
    label: "Scheduled",
  },
  in_progress: {
    bg: colors.alert[50],
    text: colors.alert[800],
    label: "In Progress",
  },
  completed: {
    bg: colors.margin[50],
    text: colors.margin[800],
    label: "Completed",
  },
};

const UNKNOWN_STATUS: StatusStyle = {
  bg: colors.neutral[100],
  text: colors.neutral[600],
  label: "Unknown",
};

function getStatusStyle(code: string | null | undefined): StatusStyle {
  if (!code) return UNKNOWN_STATUS;
  return STATUS_MAP[code as StatusCode] ?? UNKNOWN_STATUS;
}

// ── Time formatting ────────────────────────────────────────────────────────────

function formatTimeRange(
  startIso: string | null | undefined,
  endIso: string | null | undefined,
): string {
  if (!startIso) return "No time set";
  const fmt = (iso: string) =>
    new Date(iso).toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
  const start = fmt(startIso);
  if (!endIso) return start;
  return `${start} – ${fmt(endIso)}`;
}

function formatDuration(minutes: number | null | undefined): string | null {
  if (!minutes) return null;
  const h = Math.round(minutes / 60);
  return h > 0 ? `~${h}h` : null;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function JobCardRow({ job, onPress, testID }: JobCardRowProps) {
  const statusStyle = getStatusStyle(job.status_code);
  const timeRange = formatTimeRange(
    job.scheduled_start_at,
    job.scheduled_end_at,
  );
  const duration = formatDuration(job.estimated_duration_minutes);
  const customerDisplay =
    job.customer_name ?? `${job.customer_id.slice(0, 8)}…`;

  return (
    <Pressable
      onPress={() => onPress(job.id)}
      style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
      accessibilityRole="button"
      accessibilityLabel={`Job for ${customerDisplay}, ${statusStyle.label}, ${timeRange}`}
      testID={testID ?? `job-card-${job.id}`}
    >
      {/* Top row: customer name + recurring badge + status pill */}
      <View style={styles.topRow}>
        <View style={styles.customerNameRow}>
          <Text style={styles.customerName} numberOfLines={1}>
            {customerDisplay}
          </Text>
          {job.recurrence_rule_id && (
            <Text
              style={styles.recurringBadge}
              testID="recurring-badge"
              accessibilityLabel="Recurring job"
            >
              ↻
            </Text>
          )}
        </View>
        <View
          style={[styles.statusPill, { backgroundColor: statusStyle.bg }]}
          testID={`status-pill-${job.id}`}
        >
          <Text style={[styles.statusText, { color: statusStyle.text }]}>
            {statusStyle.label}
          </Text>
        </View>
      </View>

      {/* Bottom row: time + duration + chevron */}
      <View style={styles.bottomRow}>
        <Text style={styles.timeRange}>{timeRange}</Text>
        {duration && (
          <>
            <Text style={styles.dot}>·</Text>
            <Text style={styles.duration}>{duration}</Text>
          </>
        )}
        <View style={styles.chevronSpacer} />
        <Text style={styles.chevron} accessible={false}>
          ›
        </Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: radii.md,
    padding: spacing[3],
    marginBottom: spacing[2],
    borderWidth: 1,
    borderColor: colors.neutral[200],
    gap: spacing[1],
  },
  cardPressed: {
    backgroundColor: colors.neutral[50],
  },
  topRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: spacing[2],
  },
  customerNameRow: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[1],
  },
  customerName: {
    flexShrink: 1,
    fontSize: 15,
    fontWeight: "500",
    color: colors.neutral[900],
  },
  recurringBadge: {
    fontSize: 12,
    color: colors.brand[600],
    marginLeft: spacing[1],
  },
  statusPill: {
    borderRadius: 999,
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
  },
  statusText: {
    fontSize: 11,
    fontWeight: "500",
  },
  bottomRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[1],
  },
  timeRange: {
    fontSize: 13,
    color: colors.neutral[600],
  },
  dot: {
    fontSize: 13,
    color: colors.neutral[400],
  },
  duration: {
    fontSize: 13,
    color: colors.neutral[400],
  },
  chevronSpacer: {
    flex: 1,
  },
  chevron: {
    fontSize: 18,
    color: colors.neutral[400],
  },
});
