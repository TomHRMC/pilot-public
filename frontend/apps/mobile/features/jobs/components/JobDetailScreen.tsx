/**
 * JobDetailScreen — Root component for the Job Detail screen (MOB-B2)
 *
 * Location: apps/mobile/features/jobs/components/JobDetailScreen.tsx
 *
 * Composes all 7 sections + header + footer actions.
 * Uses useJobDetail to load job header + time entries.
 * Uses useChangeJobStatus for "Mark Complete" (WatermelonDB offline write).
 *
 * status_code guard:
 *   - null  → "Mark Complete" disabled with note (direct deep-link, cache miss)
 *   - "completed" → "Mark Complete" hidden entirely
 *   - other → "Mark Complete" shown + confirm dialog
 *
 * Per batch-mob-b2-design.md §F.11, §G.1, and §H.1.
 */

import React, { useCallback } from "react";
import {
  View,
  Text,
  ScrollView,
  Pressable,
  ActivityIndicator,
  Alert,
  StyleSheet,
  SafeAreaView,
} from "react-native";
import { useRouter } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { useAuth } from "@pilot/ui/auth";
import {
  colors,
  mobileFontSizes,
  fontWeights,
  spacing,
  radii,
} from "@pilot/ui/tokens";
import { useJobDetail } from "../hooks/useJobDetail";
import { useChangeJobStatus } from "../../offline-sync/hooks/useChangeJobStatus";
import { ClockInOutSection } from "./detail/ClockInOutSection";
import { LotoCheckSection } from "./detail/LotoCheckSection";
import { ProjectedMarginSection } from "./detail/ProjectedMarginSection";
import { ExpenseSection } from "./detail/ExpenseSection";
import { ChangeOrderSection } from "./detail/ChangeOrderSection";
import { JobNotesSection } from "./detail/JobNotesSection";
import { PhotoSection } from "./detail/PhotoSection";
import { InvoiceSignoffSection } from "./detail/InvoiceSignoffSection";
import type { LotoConfirmation } from "./detail/LotoCheckSection";

// ── Types ─────────────────────────────────────────────────────────────────────

interface JobDetailScreenProps {
  jobId: string;
}

interface LotoConfirmationApiItem {
  id: string;
  check_type?: string;
  confirmed_at?: string;
  [key: string]: unknown;
}

// ── Status pill color helper ──────────────────────────────────────────────────

function statusPillColor(code: string | null): string {
  switch (code) {
    case "in_progress":
      return colors.brand[400];
    case "completed":
      return colors.margin[600];
    case "cancelled":
      return colors.fault[600];
    default:
      return colors.alert[400];
  }
}

function formatTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatDateRange(
  start: string | null | undefined,
  end: string | null | undefined,
): string {
  if (!start) return "Unscheduled";
  const startTime = formatTime(start);
  const endTime = end ? formatTime(end) : "";
  const dateStr = new Date(start).toLocaleDateString([], {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
  return `${dateStr}  ·  ${startTime}${endTime ? ` – ${endTime}` : ""}`;
}

// ── Root component ─────────────────────────────────────────────────────────────

export function JobDetailScreen({
  jobId,
}: JobDetailScreenProps): React.ReactElement {
  const router = useRouter();
  const { user } = useAuth();
  const userId = user?.id ?? "";

  const { data, isLoading, isError, refetch } = useJobDetail(jobId);
  const { change: changeStatus, isPending: isChangingStatus } =
    useChangeJobStatus();

  // Fetch LOTO confirmations separately so they can be refreshed after confirm
  const { data: lotoData, refetch: refetchLoto } = useQuery<LotoConfirmation[]>(
    {
      queryKey: ["job-loto-confirmations", jobId] as const,
      queryFn: async () => {
        const r = await apiClient.get<LotoConfirmationApiItem[]>(
          `/api/v1/jobs/${jobId}/loto-confirmations`,
        );
        return r.data.map((item) => ({
          id: item.id,
          check_type: item.check_type ?? "",
          confirmed_at: item.confirmed_at ?? new Date().toISOString(),
        }));
      },
      enabled: !!jobId,
      staleTime: 15_000,
    },
  );

  const handleMarkComplete = useCallback(() => {
    if (!data) return;
    const fromStatus = data.status_code ?? "scheduled";

    Alert.alert("Mark job complete?", "This action cannot be undone.", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Complete",
        style: "destructive",
        onPress: async () => {
          try {
            await changeStatus({
              jobId,
              fromStatus,
              toStatus: "completed",
            });
            void refetch();
          } catch {
            Alert.alert("Error", "Failed to mark job complete.");
          }
        },
      },
    ]);
  }, [data, changeStatus, jobId, refetch]);

  const handleMessageCustomer = useCallback(() => {
    if (!data?.job.customer_id) return;
    router.push(
      `/(tabs)/jobs/${jobId}/comms?customerId=${data.job.customer_id}` as never,
    );
  }, [router, jobId, data?.job.customer_id]);

  // ── Loading state ─────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <SafeAreaView style={styles.container} testID="job-detail-loading">
        <ActivityIndicator
          color={colors.brand[400]}
          size="large"
          style={styles.centeredLoader}
        />
      </SafeAreaView>
    );
  }

  // ── Error state ───────────────────────────────────────────────────────────
  if (isError || !data) {
    return (
      <SafeAreaView style={styles.container} testID="job-detail-error">
        <View style={styles.centeredContent}>
          <Text style={styles.errorTitle}>Failed to load job</Text>
          <Pressable
            style={styles.retryButton}
            onPress={refetch}
            accessibilityRole="button"
            testID="retry-button"
          >
            <Text style={styles.retryButtonText}>Try again</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  const { job, activeTimeEntry, status_code, customer_name } = data;
  const isCompleted = status_code === "completed";
  const statusCodeNull = status_code === null;

  return (
    <SafeAreaView style={styles.container} testID="job-detail-screen">
      {/* ── Sticky header ──────────────────────────────────────────────────── */}
      <View style={styles.header}>
        <View style={styles.headerTop}>
          <Pressable
            onPress={() => router.back()}
            style={styles.backButton}
            accessibilityRole="button"
            accessibilityLabel="Go back"
            testID="back-button"
          >
            <Text style={styles.backButtonText}>← Back</Text>
          </Pressable>

          {/* Status pill */}
          {status_code && (
            <View
              style={[
                styles.statusPill,
                { backgroundColor: statusPillColor(status_code) + "33" },
              ]}
              testID="status-pill"
            >
              <Text
                style={[
                  styles.statusPillText,
                  { color: statusPillColor(status_code) },
                ]}
              >
                {status_code.replace("_", " ")}
              </Text>
            </View>
          )}
        </View>

        <Text style={styles.customerName} testID="customer-name">
          {customer_name ?? `Job ${jobId.slice(-6).toUpperCase()}`}
        </Text>
        <Text style={styles.dateRange} testID="date-range">
          {formatDateRange(job.scheduled_start_at, job.scheduled_end_at)}
        </Text>
      </View>

      {/* ── Scrollable sections ─────────────────────────────────────────────── */}
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
      >
        {/* Recurring series banner — shown when job belongs to a recurrence rule (MOB-B9) */}
        {job.recurrence_rule_id && (
          <View style={styles.recurringBanner} testID="recurring-series-banner">
            <Text style={styles.recurringBannerText}>
              ↻ Part of a recurring series
            </Text>
            <Text style={styles.recurringBannerSubtext}>
              Manage schedule on web
            </Text>
          </View>
        )}

        {/* Section 1: Clock In / Clock Out */}
        <ClockInOutSection
          jobId={jobId}
          userId={userId}
          activeTimeEntry={activeTimeEntry}
          onRefetch={refetch}
          testID="section-clock-in-out"
        />

        {/* Section 2: LOTO Safety Check */}
        <LotoCheckSection
          jobId={jobId}
          existingConfirmations={lotoData ?? []}
          onRefetch={refetchLoto}
          testID="section-loto"
        />

        {/* Section 3: Live Profitability */}
        <ProjectedMarginSection
          jobId={jobId}
          testID="section-projected-margin"
        />

        {/* Section 4: Expenses */}
        <ExpenseSection
          jobId={jobId}
          userId={userId}
          testID="section-expenses"
        />

        {/* Section 5: Change Orders */}
        <ChangeOrderSection jobId={jobId} testID="section-change-orders" />

        {/* Section 6: Job Notes */}
        <JobNotesSection
          jobId={jobId}
          userId={userId}
          testID="section-job-notes"
        />

        {/* Section 7: Photos */}
        <PhotoSection jobId={jobId} testID="section-photos" />

        {/* Section 7.5: Invoice Sign-Off (CE-1 Part B) */}
        <InvoiceSignoffSection
          jobId={jobId}
          userId={userId}
          testID="section-invoice-signoff"
        />

        {/* Section 8: Message Customer link */}
        <Pressable
          style={styles.linkButton}
          onPress={handleMessageCustomer}
          accessibilityRole="button"
          accessibilityLabel="Message customer"
          testID="message-customer-button"
        >
          <Text style={styles.linkButtonText}>💬 Message Customer</Text>
        </Pressable>

        {/* Section 9: Mark Job Complete */}
        {!isCompleted && (
          <View style={styles.completeSection} testID="mark-complete-section">
            {statusCodeNull && (
              <Text style={styles.statusCacheNote} testID="status-cache-note">
                Refresh jobs list to enable status change
              </Text>
            )}
            <Pressable
              style={[
                styles.completeButton,
                (isChangingStatus || statusCodeNull) &&
                  styles.completeButtonDisabled,
              ]}
              onPress={statusCodeNull ? undefined : handleMarkComplete}
              disabled={isChangingStatus || statusCodeNull}
              accessibilityRole="button"
              accessibilityLabel="Mark job complete"
              testID="mark-complete-button"
            >
              {isChangingStatus ? (
                <ActivityIndicator color={colors.neutral[50]} size="small" />
              ) : (
                <Text style={styles.completeButtonText}>
                  ✓ Mark Job Complete
                </Text>
              )}
            </Pressable>
          </View>
        )}

        {/* Bottom padding */}
        <View style={{ height: spacing[8] }} />
      </ScrollView>
    </SafeAreaView>
  );
}

// ── Styles ─────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[900],
  },
  centeredLoader: {
    flex: 1,
    alignSelf: "center",
    marginTop: spacing[10],
  },
  centeredContent: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: spacing[4],
    padding: spacing[6],
  },
  errorTitle: {
    fontSize: mobileFontSizes.h2,
    color: colors.neutral[50],
    lineHeight: 28,
  },
  retryButton: {
    backgroundColor: colors.brand[600],
    borderRadius: radii.md,
    paddingHorizontal: spacing[5],
    paddingVertical: spacing[3],
    minHeight: 44,
    alignItems: "center",
    justifyContent: "center",
  },
  retryButtonText: {
    fontSize: mobileFontSizes.body,
    color: colors.neutral[50],
    lineHeight: 20,
  },
  // Header
  header: {
    backgroundColor: colors.neutral[900],
    paddingHorizontal: spacing[4],
    paddingTop: spacing[4],
    paddingBottom: spacing[3],
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[800],
    gap: spacing[1],
  },
  headerTop: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: spacing[1],
  },
  backButton: {
    paddingVertical: spacing[1],
    paddingRight: spacing[2],
    minHeight: 44,
    justifyContent: "center",
  },
  backButtonText: {
    fontSize: mobileFontSizes.body,
    color: colors.brand[400],
    lineHeight: 20,
  },
  statusPill: {
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
    borderRadius: radii.sm,
  },
  statusPillText: {
    fontSize: mobileFontSizes.caption,
    fontWeight: String(fontWeights.medium) as "500",
    lineHeight: 16,
    textTransform: "capitalize",
  },
  customerName: {
    fontSize: mobileFontSizes.h1,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 30,
  },
  dateRange: {
    fontSize: mobileFontSizes.body,
    color: colors.neutral[400],
    lineHeight: 20,
  },
  // Scroll
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: spacing[4],
  },
  // Footer actions
  linkButton: {
    backgroundColor: colors.neutral[800],
    borderRadius: radii.md,
    minHeight: 48,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: spacing[3],
    paddingHorizontal: spacing[4],
  },
  linkButtonText: {
    fontSize: mobileFontSizes.body,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.brand[400],
    lineHeight: 20,
  },
  // Recurring series banner
  recurringBanner: {
    backgroundColor: colors.brand[50],
    borderRadius: radii.md,
    padding: spacing[3],
    marginBottom: spacing[3],
  },
  recurringBannerText: {
    fontSize: 14,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.brand[600],
    lineHeight: 20,
  },
  recurringBannerSubtext: {
    fontSize: 12,
    marginTop: 2,
    color: colors.neutral[400],
    lineHeight: 16,
  },
  completeSection: {
    gap: spacing[2],
    marginBottom: spacing[3],
  },
  statusCacheNote: {
    fontSize: mobileFontSizes.caption,
    color: colors.alert[400],
    lineHeight: 16,
    textAlign: "center",
  },
  completeButton: {
    backgroundColor: colors.margin[600],
    borderRadius: radii.md,
    minHeight: 52,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: spacing[4],
  },
  completeButtonDisabled: {
    opacity: 0.4,
  },
  completeButtonText: {
    fontSize: mobileFontSizes.body,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 20,
  },
});
