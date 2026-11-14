/**
 * InvoiceSignoffSection (S1) — Job-detail entry point for invoice sign-off
 *
 * Location: apps/mobile/features/jobs/components/detail/InvoiceSignoffSection.tsx
 *
 * Fetches GET /api/v1/jobs/{job_id}/signoff-context (D.1, auth jobs.view).
 * Renders the CTA to capture a signature, or the signed summary if already
 * signed. Hides entirely (returns null) when no signable invoices exist.
 *
 * States (spec §3.3): loading, hidden/empty, error, ready-to-capture (single),
 * ready-to-capture (multi), already-signed, pending-sync, sync-error/retry.
 *
 * Per batch-ce-1-mobile-ui-design-spec.md §3 (verbatim pixel/state authority).
 */

import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  Pressable,
  ActivityIndicator,
  ScrollView,
  StyleSheet,
} from "react-native";
import { useRouter } from "expo-router";
import { Q } from "@nozbe/watermelondb";
import {
  colors,
  mobileFontSizes,
  fontWeights,
  spacing,
  radii,
  touchTargets,
} from "@pilot/ui/tokens";
import { PendingBadge } from "@pilot/ui";
import { useSignoffContext } from "../../../jobs/hooks/useSignoffContext";
import { database } from "../../../../database";
import type { InvoiceSignoff } from "../../../../database/models/InvoiceSignoff";

// ── Money formatting (money-from-cents, spec §3.2) ────────────────────────────

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

function formatMoney(cents: number): string {
  return currencyFormatter.format(cents / 100);
}

function formatSignedAt(iso: string): string {
  return new Date(iso).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

// ── Local pending sign-off record (from WatermelonDB) ─────────────────────────

interface LocalSignoffRecord {
  id: string;
  localSyncStatus: string;
  signedByName: string;
  syncError: string | null;
}

// ── Component ─────────────────────────────────────────────────────────────────

interface InvoiceSignoffSectionProps {
  jobId: string;
  userId: string;
  testID?: string;
}

export function InvoiceSignoffSection({
  jobId,
  userId: _userId,
  testID,
}: InvoiceSignoffSectionProps): React.ReactElement | null {
  const router = useRouter();
  const { data, isPending, isError, refetch } = useSignoffContext(jobId);

  // Selected invoice index (default 0 = newest, server-ordered)
  const [selectedIndex, setSelectedIndex] = useState(0);

  // Local pending sign-off records from WatermelonDB
  const [localSignoffs, setLocalSignoffs] = useState<
    Record<string, LocalSignoffRecord>
  >({});

  // Reset selection when data changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [data?.invoices.length]);

  // Load local pending sign-offs from WatermelonDB for the invoices in context
  useEffect(() => {
    let cancelled = false;

    async function loadLocalSignoffs() {
      if (!data?.invoices?.length) return;
      try {
        const invoiceIds = data.invoices.map((inv) => inv.invoice_id);
        const records = await database
          .get<InvoiceSignoff>("invoice_signoffs")
          .query(Q.where("invoice_id", Q.oneOf(invoiceIds)))
          .fetch();

        if (cancelled) return;

        const map: Record<string, LocalSignoffRecord> = {};
        for (const record of records) {
          // Keep only the most recent per invoice (by created_at desc)
          const existing = map[record.invoiceId];
          if (
            !existing ||
            record.createdAt.getTime() > new Date(existing.id).getTime()
          ) {
            map[record.invoiceId] = {
              id: record.id,
              localSyncStatus: record.localSyncStatus,
              signedByName: record.signedByName,
              syncError: record.syncError,
            };
          }
        }
        setLocalSignoffs(map);
      } catch {
        // Database not ready — ignore
      }
    }

    void loadLocalSignoffs();
    return () => {
      cancelled = true;
    };
  }, [data?.invoices]);

  // ── Loading state ──────────────────────────────────────────────────────────
  if (isPending) {
    return (
      <View
        style={styles.container}
        testID={testID ?? "section-invoice-signoff"}
      >
        <Text style={styles.sectionTitle} accessibilityRole="header">
          INVOICE SIGN-OFF
        </Text>
        <ActivityIndicator
          color={colors.brand[400]}
          style={styles.loader}
          testID="signoff-section-loading"
        />
      </View>
    );
  }

  // ── Error state ────────────────────────────────────────────────────────────
  if (isError) {
    return (
      <View
        style={styles.container}
        testID={testID ?? "section-invoice-signoff"}
      >
        <Text style={styles.sectionTitle} accessibilityRole="header">
          INVOICE SIGN-OFF
        </Text>
        <View testID="signoff-section-error">
          <Text style={styles.errorText}>Couldn't load invoice sign-off.</Text>
          <Pressable
            style={styles.retryButton}
            onPress={() => refetch()}
            accessibilityRole="button"
            accessibilityLabel="Try again"
            testID="signoff-retry-button"
          >
            <Text style={styles.retryButtonText}>Try again</Text>
          </Pressable>
        </View>
      </View>
    );
  }

  // ── Hidden / empty state ───────────────────────────────────────────────────
  const invoices = data?.invoices;
  if (!invoices || invoices.length === 0) {
    return null;
  }

  const selectedInvoice = invoices[selectedIndex] ?? invoices[0]!;
  const localRecord = localSignoffs[selectedInvoice.invoice_id];
  const isPendingSync = localRecord?.localSyncStatus === "pending";
  const isSyncing = localRecord?.localSyncStatus === "syncing";
  const isSyncFailed = localRecord?.localSyncStatus === "failed";
  const hasActiveSignoff = selectedInvoice.active_signoff !== null;

  // ── Pending-sync state ─────────────────────────────────────────────────────
  if (isPendingSync || isSyncing) {
    return (
      <View
        style={styles.container}
        testID={testID ?? "section-invoice-signoff"}
      >
        <View style={styles.signedHeaderRow}>
          <Text style={styles.sectionTitle} accessibilityRole="header">
            INVOICE SIGN-OFF
          </Text>
          <PendingBadge
            count={1}
            variant={isSyncing ? "syncing" : "pending"}
            testID="signoff-section-pending"
          />
        </View>
        <View style={styles.signedSummary}>
          <Text style={styles.signedName}>
            {localRecord?.signedByName ?? "Customer"}
          </Text>
          <Text style={styles.signedAt}>Captured — syncing…</Text>
        </View>
      </View>
    );
  }

  // ── Sync-error / retry state ───────────────────────────────────────────────
  if (isSyncFailed) {
    return (
      <View
        style={styles.container}
        testID={testID ?? "section-invoice-signoff"}
      >
        <View style={styles.signedHeaderRow}>
          <Text style={styles.sectionTitle} accessibilityRole="header">
            INVOICE SIGN-OFF
          </Text>
          <PendingBadge
            count={1}
            variant="failed"
            testID="signoff-section-sync-error"
          />
        </View>
        <View style={styles.signedSummary}>
          <Text style={styles.signedName}>
            {localRecord?.signedByName ?? "Customer"}
          </Text>
          <Text style={styles.signedAt}>Sync failed — will retry</Text>
        </View>
        <Pressable
          style={styles.retrySyncButton}
          onPress={() => refetch()}
          accessibilityRole="button"
          accessibilityLabel="Retry syncing signature"
          testID="signoff-retry-sync-button"
        >
          <Text style={styles.retrySyncText}>Retry sync</Text>
        </Pressable>
      </View>
    );
  }

  // ── Already-signed state ───────────────────────────────────────────────────
  if (hasActiveSignoff) {
    const signoff = selectedInvoice.active_signoff!;
    return (
      <View
        style={styles.container}
        testID={testID ?? "section-invoice-signoff"}
      >
        <View style={styles.signedHeaderRow}>
          <Text style={styles.sectionTitle} accessibilityRole="header">
            INVOICE SIGN-OFF
          </Text>
        </View>

        {invoices.length > 1 && (
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            style={styles.pillRow}
            contentContainerStyle={styles.pillRowContent}
          >
            {invoices.map((inv, idx) => (
              <Pressable
                key={inv.invoice_id}
                style={[
                  styles.pill,
                  idx === selectedIndex
                    ? styles.pillSelected
                    : styles.pillUnselected,
                ]}
                onPress={() => setSelectedIndex(idx)}
                accessibilityRole="button"
                accessibilityLabel={`Select invoice ${inv.invoice_number}`}
                testID={`signoff-pill-${idx}`}
              >
                <Text
                  style={[
                    styles.pillText,
                    idx === selectedIndex
                      ? styles.pillTextSelected
                      : styles.pillTextUnselected,
                  ]}
                >
                  {inv.invoice_number}
                </Text>
              </Pressable>
            ))}
          </ScrollView>
        )}

        <View style={styles.signedSummary} testID="signoff-section-signed">
          <Text style={styles.signedName}>{signoff.signed_by_name}</Text>
          <Text style={styles.signedAt}>
            Signed {formatSignedAt(signoff.signed_at)}
          </Text>
        </View>

        <Pressable
          style={styles.recaptureButton}
          onPress={() => {
            router.push(
              `/(tabs)/jobs/${jobId}/invoice-signoff?invoiceId=${selectedInvoice.invoice_id}` as never,
            );
          }}
          accessibilityRole="button"
          accessibilityLabel="Re-capture signature"
          testID="signoff-recapture-button"
        >
          <Text style={styles.recaptureText}>Re-capture</Text>
        </Pressable>
      </View>
    );
  }

  // ── Ready-to-capture state (single or multi) ───────────────────────────────
  const isMulti = invoices.length > 1;

  return (
    <View style={styles.container} testID={testID ?? "section-invoice-signoff"}>
      <Text style={styles.sectionTitle} accessibilityRole="header">
        INVOICE SIGN-OFF
      </Text>

      {isMulti && (
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          style={styles.pillRow}
          contentContainerStyle={styles.pillRowContent}
          testID="signoff-section-multi"
        >
          {invoices.map((inv, idx) => (
            <Pressable
              key={inv.invoice_id}
              style={[
                styles.pill,
                idx === selectedIndex
                  ? styles.pillSelected
                  : styles.pillUnselected,
              ]}
              onPress={() => setSelectedIndex(idx)}
              accessibilityRole="button"
              accessibilityLabel={`Select invoice ${inv.invoice_number}`}
              testID={`signoff-pill-${idx}`}
            >
              <Text
                style={[
                  styles.pillText,
                  idx === selectedIndex
                    ? styles.pillTextSelected
                    : styles.pillTextUnselected,
                ]}
              >
                {inv.invoice_number}
              </Text>
            </Pressable>
          ))}
        </ScrollView>
      )}

      <View style={styles.invoiceRow} testID="signoff-section-ready">
        <Text style={styles.invoiceNumber}>
          {selectedInvoice.invoice_number}
        </Text>
        <Text style={styles.invoiceAmount}>
          {formatMoney(selectedInvoice.total_cents)}
        </Text>
      </View>
      <Text style={styles.statusSubLine}>
        {selectedInvoice.status === "partial"
          ? `Partial · ${formatMoney(selectedInvoice.balance_due_cents)} due`
          : `Issued · ${formatMoney(selectedInvoice.balance_due_cents)} due`}
      </Text>

      <Pressable
        style={styles.captureButton}
        onPress={() => {
          router.push(
            `/(tabs)/jobs/${jobId}/invoice-signoff?invoiceId=${selectedInvoice.invoice_id}` as never,
          );
        }}
        accessibilityRole="button"
        accessibilityLabel={`Capture customer signature for invoice ${selectedInvoice.invoice_number}`}
        testID="signoff-capture-button"
      >
        <Text style={styles.captureButtonText}>✍ Capture Signature</Text>
      </Pressable>
    </View>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.neutral[800],
    borderRadius: radii.lg,
    padding: spacing[4],
    marginBottom: spacing[3],
    gap: spacing[3],
  },
  sectionTitle: {
    fontSize: mobileFontSizes.caption,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[400],
    textTransform: "uppercase",
    letterSpacing: 0.5,
    lineHeight: 16,
  },
  loader: {
    alignSelf: "flex-start",
  },
  errorText: {
    fontSize: mobileFontSizes.body,
    color: colors.neutral[400],
    lineHeight: 20,
  },
  retryButton: {
    backgroundColor: colors.brand[600],
    borderRadius: radii.md,
    minHeight: touchTargets.mobile.sm,
    paddingHorizontal: spacing[4],
    alignItems: "center",
    justifyContent: "center",
    alignSelf: "flex-start",
  },
  retryButtonText: {
    fontSize: mobileFontSizes.body,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 20,
  },
  // Signed header row (title + badge)
  signedHeaderRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  // Pill selector row
  pillRow: {
    marginBottom: spacing[1],
  },
  pillRowContent: {
    gap: spacing[2],
  },
  pill: {
    minHeight: touchTargets.mobile.sm,
    paddingHorizontal: spacing[3],
    borderRadius: radii.full,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  pillSelected: {
    backgroundColor: colors.brand[600],
    borderColor: colors.brand[600],
  },
  pillUnselected: {
    backgroundColor: colors.neutral[900],
    borderColor: colors.neutral[600],
  },
  pillText: {
    fontSize: mobileFontSizes.body,
    fontWeight: String(fontWeights.medium) as "500",
  },
  pillTextSelected: {
    color: colors.neutral[50],
  },
  pillTextUnselected: {
    color: colors.neutral[400],
  },
  // Invoice number + amount row
  invoiceRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  invoiceNumber: {
    fontSize: mobileFontSizes.body,
    color: colors.neutral[50],
    lineHeight: 20,
  },
  invoiceAmount: {
    fontSize: mobileFontSizes.bodyLg,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 22,
  },
  statusSubLine: {
    fontSize: mobileFontSizes.caption,
    color: colors.neutral[400],
    lineHeight: 16,
  },
  // Capture CTA
  captureButton: {
    backgroundColor: colors.brand[600],
    borderRadius: radii.md,
    minHeight: touchTargets.mobile.md,
    alignItems: "center",
    justifyContent: "center",
  },
  captureButtonText: {
    fontSize: mobileFontSizes.body,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 20,
  },
  // Signed summary block
  signedSummary: {
    backgroundColor: colors.neutral[900],
    borderRadius: radii.md,
    padding: spacing[3],
    gap: spacing[1],
  },
  signedName: {
    fontSize: mobileFontSizes.h2,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 26,
  },
  signedAt: {
    fontSize: mobileFontSizes.caption,
    color: colors.neutral[400],
    lineHeight: 16,
  },
  // Re-capture text button
  recaptureButton: {
    minHeight: touchTargets.mobile.sm,
    alignItems: "center",
    justifyContent: "center",
    alignSelf: "flex-start",
  },
  recaptureText: {
    fontSize: mobileFontSizes.body,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.brand[400],
    lineHeight: 20,
  },
  // Retry-sync text button
  retrySyncButton: {
    minHeight: touchTargets.mobile.sm,
    alignItems: "center",
    justifyContent: "center",
    alignSelf: "flex-start",
  },
  retrySyncText: {
    fontSize: mobileFontSizes.body,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.fault[400],
    lineHeight: 20,
  },
});
