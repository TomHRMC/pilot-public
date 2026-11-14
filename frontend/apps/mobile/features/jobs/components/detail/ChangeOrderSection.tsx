/**
 * ChangeOrderSection — Change order list + add modal
 *
 * Location: apps/mobile/features/jobs/components/detail/ChangeOrderSection.tsx
 *
 * Fetches GET /api/v1/jobs/{jobId}/change-orders on mount.
 * Add form uses useCreateChangeOrder (WatermelonDB write — offline-first).
 *
 * API response `description` field is displayed in the list.
 * Hook input uses `title` (maps to `description` on sync via SyncOrchestrator).
 *
 * Per batch-mob-b2-design.md §F.8 and §G.2.
 */

import React, { useState, useCallback } from "react";
import {
  View,
  Text,
  Pressable,
  Modal,
  TextInput,
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Alert,
} from "react-native";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import {
  colors,
  mobileFontSizes,
  fontWeights,
  spacing,
  radii,
} from "@pilot/ui/tokens";
import { useCreateChangeOrder } from "../../../offline-sync/hooks/useCreateChangeOrder";

// ── API response type ─────────────────────────────────────────────────────────

interface ChangeOrderItem {
  id: string;
  tenant_id: string;
  job_id: string;
  description: string | null;
  subtotal_cents: number | null;
  tax_cents: number | null;
  total_cents: number | null;
  is_active: boolean;
}

// ── Component ─────────────────────────────────────────────────────────────────

interface ChangeOrderSectionProps {
  jobId: string;
  testID?: string;
}

export function ChangeOrderSection({
  jobId,
  testID,
}: ChangeOrderSectionProps): React.ReactElement {
  const [showAddModal, setShowAddModal] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [totalDollars, setTotalDollars] = useState("");

  const { create, isPending: isCreating } = useCreateChangeOrder();

  const {
    data: changeOrders,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["job-change-orders", jobId] as const,
    queryFn: () =>
      apiClient
        .get<ChangeOrderItem[]>(`/api/v1/jobs/${jobId}/change-orders`)
        .then((r) => r.data),
    enabled: !!jobId,
    staleTime: 30_000,
  });

  const resetForm = useCallback(() => {
    setTitle("");
    setDescription("");
    setTotalDollars("");
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!title.trim()) {
      Alert.alert("Required", "Please enter a title for the change order.");
      return;
    }
    const dollars = parseFloat(totalDollars);
    if (isNaN(dollars) || dollars < 0) {
      Alert.alert("Invalid amount", "Please enter a valid total amount.");
      return;
    }
    const totalAmountCents = Math.round(dollars * 100);
    try {
      await create({
        jobId,
        title: title.trim(),
        description: description.trim() || undefined,
        totalAmountCents,
      });
      setShowAddModal(false);
      resetForm();
      void refetch();
    } catch {
      Alert.alert("Error", "Failed to save change order. Please try again.");
    }
  }, [title, totalDollars, description, create, jobId, refetch, resetForm]);

  const activeOrders = changeOrders?.filter((co) => co.is_active) ?? [];

  return (
    <View style={styles.container} testID={testID ?? "change-order-section"}>
      {/* Header row */}
      <View style={styles.headerRow}>
        <Text style={styles.sectionTitle}>CHANGE ORDERS</Text>
        <Pressable
          style={styles.addButton}
          onPress={() => setShowAddModal(true)}
          accessibilityRole="button"
          accessibilityLabel="Add change order"
          testID="add-change-order-button"
        >
          <Text style={styles.addButtonText}>+ Add</Text>
        </Pressable>
      </View>

      {/* Change order list */}
      {isLoading && (
        <ActivityIndicator color={colors.brand[400]} style={styles.loader} />
      )}
      {!isLoading && activeOrders.length === 0 && (
        <Text style={styles.emptyText}>No change orders recorded</Text>
      )}
      {activeOrders.map((co) => (
        <View key={co.id} style={styles.coRow} testID={`co-row-${co.id}`}>
          <Text style={styles.coDescription} numberOfLines={2}>
            {co.description ?? "Change order"}
          </Text>
          {co.total_cents !== null && (
            <Text style={styles.coTotal}>
              ${(co.total_cents / 100).toFixed(2)}
            </Text>
          )}
        </View>
      ))}

      {/* Add Change Order Modal */}
      <Modal
        visible={showAddModal}
        transparent
        animationType="slide"
        onRequestClose={() => {
          setShowAddModal(false);
          resetForm();
        }}
        testID="add-co-modal"
      >
        <View style={styles.modalOverlay}>
          <View style={styles.bottomSheet}>
            {/* Sheet header */}
            <View style={styles.sheetHeader}>
              <Text style={styles.sheetTitle}>Add Change Order</Text>
              <Pressable
                onPress={() => {
                  setShowAddModal(false);
                  resetForm();
                }}
                accessibilityRole="button"
                accessibilityLabel="Close"
                testID="close-co-form"
              >
                <Text style={styles.closeButton}>✕</Text>
              </Pressable>
            </View>

            <ScrollView
              keyboardShouldPersistTaps="handled"
              showsVerticalScrollIndicator={false}
            >
              {/* Title (required) */}
              <Text style={styles.fieldLabel}>Title *</Text>
              <TextInput
                style={styles.input}
                value={title}
                onChangeText={setTitle}
                placeholder="e.g. Panel upgrade addition"
                placeholderTextColor={colors.neutral[400]}
                accessibilityLabel="Change order title"
                testID="co-title-input"
              />

              {/* Description (optional) */}
              <Text style={styles.fieldLabel}>Description (optional)</Text>
              <TextInput
                style={[styles.input, styles.inputMultiline]}
                value={description}
                onChangeText={setDescription}
                placeholder="Additional details..."
                placeholderTextColor={colors.neutral[400]}
                multiline
                numberOfLines={3}
                accessibilityLabel="Change order description"
                testID="co-description-input"
              />

              {/* Total amount */}
              <Text style={styles.fieldLabel}>Total Amount ($)</Text>
              <TextInput
                style={styles.input}
                value={totalDollars}
                onChangeText={setTotalDollars}
                placeholder="0.00"
                placeholderTextColor={colors.neutral[400]}
                keyboardType="decimal-pad"
                accessibilityLabel="Change order total amount"
                testID="co-total-input"
              />

              {/* Submit */}
              <Pressable
                style={[
                  styles.submitButton,
                  isCreating && styles.submitButtonDisabled,
                ]}
                onPress={handleSubmit}
                disabled={isCreating}
                accessibilityRole="button"
                accessibilityLabel="Add change order"
                testID="submit-co-button"
              >
                {isCreating ? (
                  <ActivityIndicator color={colors.neutral[50]} />
                ) : (
                  <Text style={styles.submitButtonText}>Add Change Order</Text>
                )}
              </Pressable>
            </ScrollView>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.neutral[800],
    borderRadius: radii.md,
    padding: spacing[4],
    marginBottom: spacing[3],
    gap: spacing[2],
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  sectionTitle: {
    fontSize: mobileFontSizes.caption,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[400],
    textTransform: "uppercase",
    letterSpacing: 0.5,
    lineHeight: 16,
  },
  addButton: {
    paddingVertical: spacing[1],
    paddingHorizontal: spacing[2],
  },
  addButtonText: {
    fontSize: mobileFontSizes.body,
    color: colors.brand[400],
    lineHeight: 20,
  },
  loader: {
    alignSelf: "flex-start",
  },
  emptyText: {
    fontSize: mobileFontSizes.body,
    color: colors.neutral[400],
    lineHeight: 20,
  },
  coRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
    paddingVertical: spacing[2],
    borderTopWidth: 1,
    borderTopColor: colors.neutral[600],
    gap: spacing[2],
  },
  coDescription: {
    flex: 1,
    fontSize: mobileFontSizes.body,
    color: colors.neutral[50],
    lineHeight: 20,
  },
  coTotal: {
    fontSize: mobileFontSizes.body,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 20,
  },
  // Modal / bottom sheet
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.6)",
    justifyContent: "flex-end",
  },
  bottomSheet: {
    backgroundColor: colors.neutral[800],
    borderTopLeftRadius: radii.lg,
    borderTopRightRadius: radii.lg,
    padding: spacing[4],
    maxHeight: "80%",
    gap: spacing[2],
  },
  sheetHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: spacing[2],
  },
  sheetTitle: {
    fontSize: mobileFontSizes.h2,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 28,
  },
  closeButton: {
    fontSize: 18,
    color: colors.neutral[400],
    padding: spacing[1],
  },
  fieldLabel: {
    fontSize: mobileFontSizes.caption,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[400],
    lineHeight: 16,
    marginBottom: spacing[1],
    marginTop: spacing[3],
  },
  input: {
    backgroundColor: colors.neutral[900],
    borderRadius: radii.sm,
    borderWidth: 1,
    borderColor: colors.neutral[600],
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[3],
    fontSize: mobileFontSizes.body,
    color: colors.neutral[50],
    lineHeight: 20,
  },
  inputMultiline: {
    minHeight: 80,
    textAlignVertical: "top",
  },
  submitButton: {
    backgroundColor: colors.brand[600],
    borderRadius: radii.md,
    minHeight: 44,
    alignItems: "center",
    justifyContent: "center",
    marginTop: spacing[4],
    marginBottom: spacing[6],
  },
  submitButtonDisabled: {
    opacity: 0.5,
  },
  submitButtonText: {
    fontSize: mobileFontSizes.body,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 20,
  },
});
