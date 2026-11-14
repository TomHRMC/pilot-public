/**
 * InvoiceSignoffCaptureScreen (S2) — Full-screen signature capture flow
 *
 * Location: apps/mobile/features/jobs/components/detail/InvoiceSignoffCaptureScreen.tsx
 *
 * Full-screen modal-style capture: header bar, invoice context, prominent
 * total, printed-name TextInput, scrollable terms, acknowledge checkbox,
 * 220px white canvas (react-native-signature-canvas), Clear + Save buttons.
 *
 * Save is gated on 3 conditions (spec §4.2):
 *   1. Name field non-empty (trimmed length ≥ 1)
 *   2. Acknowledge checkbox checked
 *   3. Canvas non-empty (at least one stroke)
 *
 * Save flow (spec §4.3): calls useCreateInvoiceSignoff.create() — local
 * WatermelonDB write only; the sync engine pushes on reconnect. Save always
 * succeeds locally. On success: haptic + green-check overlay (800ms) +
 * router.back().
 *
 * Per batch-ce-1-mobile-ui-design-spec.md §4 (verbatim pixel/state authority),
 * §5 (haptics), §6 (accessibility).
 */

import React, { useState, useRef, useCallback } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  ScrollView,
  StyleSheet,
  SafeAreaView,
  ActivityIndicator,
  Vibration,
  AccessibilityInfo,
  Dimensions,
} from "react-native";
import { useRouter, useLocalSearchParams } from "expo-router";
import SignatureCanvas from "react-native-signature-canvas";
import type { ComponentRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { useAuth } from "@pilot/ui/auth";
import {
  colors,
  mobileFontSizes,
  fontWeights,
  spacing,
  radii,
  touchTargets,
  motion,
} from "@pilot/ui/tokens";
import type { components } from "@pilot/shared-types";
import { useCreateInvoiceSignoff } from "../../../offline-sync/hooks/useCreateInvoiceSignoff";
type SignatureCanvasRef = ComponentRef<typeof SignatureCanvas>;

// ── Types ─────────────────────────────────────────────────────────────────────

type SignoffContextResponse = components["schemas"]["SignoffContextResponse"];
type SignoffContextInvoice = components["schemas"]["SignoffContextInvoice"];

// ── Money formatting ──────────────────────────────────────────────────────────

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

function formatMoney(cents: number): string {
  return currencyFormatter.format(cents / 100);
}

// ── Component ─────────────────────────────────────────────────────────────────

interface InvoiceSignoffCaptureScreenProps {
  jobId: string;
  invoiceId: string;
  testID?: string;
}

export function InvoiceSignoffCaptureScreen({
  jobId: _jobId,
  invoiceId,
  testID,
}: InvoiceSignoffCaptureScreenProps): React.ReactElement {
  const router = useRouter();
  const { user } = useAuth();
  const userId = user?.id ?? "";

  const {
    create,
    isPending: isSaving,
    error: saveError,
  } = useCreateInvoiceSignoff();

  // ── Fetch signoff context to get invoice details + terms ───────────────────
  const { data: contextData } = useQuery({
    queryKey: ["job-signoff-context", _jobId] as const,
    queryFn: async () => {
      const r = await apiClient.get<SignoffContextResponse>(
        `/api/v1/jobs/${_jobId}/signoff-context`,
      );
      return r.data;
    },
    enabled: !!_jobId,
    retry: false,
    staleTime: 30_000,
  });

  // Find the selected invoice from context
  const invoice: SignoffContextInvoice | undefined =
    contextData?.invoices?.find((inv) => inv.invoice_id === invoiceId);
  const customerName = contextData?.customer_display_name ?? "";

  // ── Gate state ─────────────────────────────────────────────────────────────
  const [name, setName] = useState("");
  const [acknowledged, setAcknowledged] = useState(false);
  const [canvasHasStrokes, setCanvasHasStrokes] = useState(false);
  const [cachedBase64, setCachedBase64] = useState<string | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);

  const signatureRef = useRef<SignatureCanvasRef | null>(null);

  // ── Gate evaluation ────────────────────────────────────────────────────────
  const nameValid = name.trim().length >= 1;
  const allGatesMet = nameValid && acknowledged && canvasHasStrokes;

  // ── Canvas callbacks ───────────────────────────────────────────────────────
  const handleOK = useCallback((base64: string) => {
    setCachedBase64(base64);
    setCanvasHasStrokes(true);
  }, []);

  const handleEmpty = useCallback(() => {
    setCachedBase64(null);
    setCanvasHasStrokes(false);
  }, []);

  const handleClear = useCallback(() => {
    signatureRef.current?.clearSignature();
    setCachedBase64(null);
    setCanvasHasStrokes(false);
  }, []);

  // ── Save flow (spec §4.3) ──────────────────────────────────────────────────
  const handleSave = useCallback(async () => {
    if (!allGatesMet) {
      // Announce which gate is unmet (spec §6.4)
      if (!nameValid) {
        AccessibilityInfo.announceForAccessibility("Enter the customer's name");
      } else if (!acknowledged) {
        AccessibilityInfo.announceForAccessibility("Acknowledge the terms");
      } else if (!canvasHasStrokes) {
        AccessibilityInfo.announceForAccessibility("Draw a signature");
      }
      return;
    }

    const base64 = cachedBase64 ?? signatureRef.current?.getData() ?? "";
    if (!base64) return;

    try {
      await create({
        invoiceId,
        signedByName: name.trim(),
        termsAcknowledged: true,
        signaturePngBase64: base64,
        capturedBy: userId,
      });

      // Success: haptic + overlay + announce (spec §5, §6.4)
      Vibration.vibrate(40);
      AccessibilityInfo.announceForAccessibility(
        `Signature captured for ${invoice?.invoice_number ?? "invoice"}. It will sync when you're back online.`,
      );
      setShowSuccess(true);

      // Dissolve overlay after 800ms, then navigate back
      setTimeout(() => {
        setShowSuccess(false);
        router.back();
      }, motion.duration.voiceSuccess);
    } catch {
      // Failure: haptic + announce (spec §5, §6.4)
      Vibration.vibrate([0, 200, 100, 200]);
      AccessibilityInfo.announceForAccessibility(
        "Save failed. Please try again.",
      );
    }
  }, [
    allGatesMet,
    nameValid,
    acknowledged,
    canvasHasStrokes,
    cachedBase64,
    create,
    invoiceId,
    name,
    userId,
    invoice?.invoice_number,
    router,
  ]);

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <SafeAreaView
      style={styles.container}
      testID={testID ?? "signoff-capture-screen"}
    >
      {/* Header bar */}
      <View style={styles.header}>
        <Pressable
          style={styles.backButton}
          onPress={() => router.back()}
          accessibilityRole="button"
          accessibilityLabel="Go back to job detail"
          testID="signoff-back-button"
        >
          <Text style={styles.backButtonText}>← Back</Text>
        </Pressable>
        <Text style={styles.headerTitle}>Sign Invoice</Text>
      </View>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        {/* Invoice context line */}
        <View style={styles.contextLine}>
          {invoice && (
            <Text style={styles.contextInvoiceNumber}>
              {invoice.invoice_number}
            </Text>
          )}
          {customerName ? (
            <Text style={styles.contextCustomerName}>{customerName}</Text>
          ) : null}
        </View>

        {/* Invoice total — prominent bold line */}
        {invoice && (
          <View style={styles.totalContainer}>
            <Text style={styles.totalLabel}>TOTAL DUE</Text>
            <Text style={styles.totalValue}>
              {formatMoney(invoice.total_cents)}
            </Text>
          </View>
        )}

        {/* Customer printed-name field */}
        <View style={styles.nameContainer}>
          <Text style={styles.fieldLabel}>Customer Printed Name</Text>
          <TextInput
            style={[styles.nameInput, saveError ? styles.nameInputError : null]}
            value={name}
            onChangeText={setName}
            placeholder="Type the customer's full name"
            placeholderTextColor={colors.neutral[400]}
            maxLength={200}
            accessibilityLabel="Customer printed name"
            testID="signoff-name-input"
          />
        </View>

        {/* Terms text (scrollable) */}
        <View style={styles.termsContainer}>
          <Text style={styles.fieldLabel}>Terms & Conditions</Text>
          <View style={styles.termsScrollWrapper}>
            <ScrollView
              style={styles.termsScroll}
              testID="signoff-terms-scroll"
              accessibilityLabel="Terms and conditions"
            >
              <Text style={styles.termsText}>
                {invoice?.terms_text ||
                  "By signing, the customer acknowledges the work described has been completed satisfactorily and agrees to the payment terms outlined above."}
              </Text>
            </ScrollView>
          </View>
        </View>

        {/* Acknowledge control */}
        <Pressable
          style={styles.acknowledgeRow}
          onPress={() => setAcknowledged(!acknowledged)}
          accessibilityRole="checkbox"
          accessibilityState={{ checked: acknowledged }}
          accessibilityLabel="Customer agrees to the terms"
          testID="signoff-acknowledge"
        >
          <View
            style={[
              styles.checkbox,
              acknowledged ? styles.checkboxChecked : styles.checkboxUnchecked,
            ]}
          >
            {acknowledged && <Text style={styles.checkmark}>✓</Text>}
          </View>
          <Text style={styles.acknowledgeLabel}>
            Customer agrees to the terms
          </Text>
        </Pressable>

        {/* Signature canvas */}
        <View style={styles.canvasContainer}>
          <Text style={styles.fieldLabel}>Signature</Text>
          <View style={styles.canvasWrapper}>
            <SignatureCanvas
              ref={signatureRef}
              onOK={handleOK}
              onEmpty={handleEmpty}
              backgroundColor={colors.neutral[50]}
              penColor={colors.neutral[900]}
              minWidth={0.5}
              maxWidth={2.5}
              style={styles.canvas}
            />
          </View>
        </View>

        {/* Clear button */}
        <Pressable
          style={[styles.clearButton, isSaving && styles.clearButtonDisabled]}
          onPress={handleClear}
          disabled={isSaving}
          accessibilityRole="button"
          accessibilityLabel="Clear signature"
          testID="signoff-clear-button"
        >
          <Text style={styles.clearButtonText}>Clear Signature</Text>
        </Pressable>

        {/* Save button */}
        <Pressable
          style={[styles.saveButton, !allGatesMet && styles.saveButtonDisabled]}
          onPress={allGatesMet ? handleSave : undefined}
          disabled={!allGatesMet || isSaving}
          accessibilityRole="button"
          accessibilityLabel={
            allGatesMet ? "Save signature" : "Save signature, disabled"
          }
          testID="signoff-save-button"
        >
          {isSaving ? (
            <ActivityIndicator color={colors.neutral[50]} size="small" />
          ) : saveError ? (
            <Text style={styles.saveErrorText}>Save failed — try again</Text>
          ) : (
            <Text style={styles.saveButtonText}>Save Signature</Text>
          )}
        </Pressable>
      </ScrollView>

      {/* Success overlay (transient) */}
      {showSuccess && (
        <View
          style={styles.successOverlay}
          testID="signoff-success-overlay"
          accessibilityRole="alert"
          accessibilityLabel="Signature captured successfully"
        >
          <Text style={styles.successCheckmark}>✓</Text>
          <Text style={styles.successText}>Signature captured</Text>
        </View>
      )}
    </SafeAreaView>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const screenWidth = Dimensions.get("window").width;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[900],
  },
  // Header
  header: {
    flexDirection: "row",
    alignItems: "center",
    padding: spacing[4],
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[800],
    gap: spacing[3],
  },
  backButton: {
    minHeight: touchTargets.mobile.sm,
    justifyContent: "center",
    paddingRight: spacing[2],
  },
  backButtonText: {
    fontSize: mobileFontSizes.body,
    color: colors.brand[400],
    lineHeight: 20,
  },
  headerTitle: {
    fontSize: mobileFontSizes.h3,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 22,
  },
  // Scroll
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: spacing[4],
  },
  // Invoice context line
  contextLine: {
    padding: spacing[4],
    gap: spacing[1],
  },
  contextInvoiceNumber: {
    fontSize: mobileFontSizes.body,
    color: colors.neutral[400],
    lineHeight: 20,
  },
  contextCustomerName: {
    fontSize: mobileFontSizes.body,
    color: colors.neutral[50],
    lineHeight: 20,
  },
  // Total
  totalContainer: {
    paddingHorizontal: spacing[4],
    paddingTop: spacing[2],
    paddingBottom: spacing[3],
  },
  totalLabel: {
    fontSize: mobileFontSizes.caption,
    color: colors.neutral[400],
    textTransform: "uppercase",
    lineHeight: 16,
  },
  totalValue: {
    fontSize: mobileFontSizes.display,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 34,
  },
  // Name field
  nameContainer: {
    paddingHorizontal: spacing[4],
    paddingBottom: spacing[3],
    gap: spacing[1],
  },
  fieldLabel: {
    fontSize: mobileFontSizes.caption,
    color: colors.neutral[400],
    textTransform: "uppercase",
    lineHeight: 16,
  },
  nameInput: {
    backgroundColor: colors.neutral[800],
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.neutral[600],
    minHeight: touchTargets.mobile.md,
    paddingHorizontal: spacing[3],
    fontSize: mobileFontSizes.bodyLg,
    color: colors.neutral[50],
  },
  nameInputError: {
    borderColor: colors.fault[400],
  },
  // Terms
  termsContainer: {
    paddingHorizontal: spacing[4],
    paddingBottom: spacing[2],
    gap: spacing[1],
  },
  termsScrollWrapper: {
    maxHeight: 200,
    backgroundColor: colors.neutral[800],
    borderRadius: radii.md,
    padding: spacing[3],
    borderWidth: 1,
    borderColor: colors.neutral[600],
  },
  termsScroll: {
    flex: 1,
  },
  termsText: {
    fontSize: mobileFontSizes.body,
    lineHeight: 20,
    color: colors.neutral[200],
  },
  // Acknowledge
  acknowledgeRow: {
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[2],
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[3],
    minHeight: touchTargets.mobile.sm,
  },
  checkbox: {
    width: 28,
    height: 28,
    borderWidth: 2,
    borderRadius: radii.sm,
    alignItems: "center",
    justifyContent: "center",
  },
  checkboxUnchecked: {
    borderColor: colors.neutral[400],
    backgroundColor: "transparent",
  },
  checkboxChecked: {
    borderColor: colors.margin[600],
    backgroundColor: colors.margin[600],
  },
  checkmark: {
    color: colors.neutral[50],
    fontSize: 16,
    fontWeight: String(fontWeights.medium) as "500",
  },
  acknowledgeLabel: {
    flex: 1,
    fontSize: mobileFontSizes.bodyLg,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 22,
  },
  // Canvas
  canvasContainer: {
    paddingHorizontal: spacing[4],
    paddingBottom: spacing[3],
    gap: spacing[1],
  },
  canvasWrapper: {
    height: 220,
    backgroundColor: colors.neutral[50],
    borderRadius: radii.md,
    borderWidth: 2,
    borderColor: colors.neutral[600],
    overflow: "hidden",
  },
  canvas: {
    flex: 1,
    width: screenWidth - spacing[4] * 2 - 4,
  },
  // Clear button
  clearButton: {
    paddingHorizontal: spacing[4],
    paddingBottom: spacing[2],
    minHeight: touchTargets.mobile.sm,
    alignSelf: "flex-start",
    justifyContent: "center",
  },
  clearButtonDisabled: {
    opacity: 0.4,
  },
  clearButtonText: {
    fontSize: mobileFontSizes.body,
    color: colors.neutral[400],
    lineHeight: 20,
  },
  // Save button
  saveButton: {
    marginHorizontal: spacing[4],
    marginBottom: spacing[4],
    backgroundColor: colors.brand[600],
    borderRadius: radii.md,
    minHeight: touchTargets.mobile.md,
    alignItems: "center",
    justifyContent: "center",
  },
  saveButtonDisabled: {
    opacity: 0.4,
  },
  saveButtonText: {
    fontSize: mobileFontSizes.body,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 20,
  },
  saveErrorText: {
    fontSize: mobileFontSizes.body,
    color: colors.fault[400],
    lineHeight: 20,
  },
  // Success overlay
  successOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: colors.margin[600],
    opacity: 0.95,
    alignItems: "center",
    justifyContent: "center",
    gap: spacing[4],
  },
  successCheckmark: {
    fontSize: 100,
    color: colors.neutral[50],
    lineHeight: 100,
  },
  successText: {
    fontSize: mobileFontSizes.h3,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 22,
  },
});
