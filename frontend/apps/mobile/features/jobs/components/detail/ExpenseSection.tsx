/**
 * ExpenseSection — Expense list + add expense bottom sheet
 *
 * Location: apps/mobile/features/jobs/components/detail/ExpenseSection.tsx
 *
 * Fetches GET /api/v1/jobs/{jobId}/expenses on mount.
 * Add form uses useCreateExpense (WatermelonDB write — offline-first).
 *
 * MOB-B6: Expense categories now fetched from GET /api/v1/job-expense-categories.
 * Falls back to MVP_EXPENSE_CATEGORIES hardcoded list if API fails or returns empty.
 *
 * Per batch-mob-b6-design.md Step 3.
 */

import React, { useState, useCallback } from "react";
import {
  View,
  Text,
  Pressable,
  Modal,
  TextInput,
  Switch,
  ScrollView,
  ActivityIndicator,
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
import { useCreateExpense } from "../../../offline-sync/hooks/useCreateExpense";

// ── MVP expense categories (fallback) ─────────────────────────────────────────
// Kept as resilience fallback — do NOT delete.

const MVP_EXPENSE_CATEGORIES = [
  { code: "materials", name: "Materials" },
  { code: "tools", name: "Tools & Equipment" },
  { code: "subcontractor", name: "Subcontractor" },
  { code: "fuel", name: "Fuel & Travel" },
  { code: "other", name: "Other" },
] as const;

// ── API category type ─────────────────────────────────────────────────────────

interface ExpenseCategoryItem {
  code: string;
  name: string;
  is_default: boolean;
}

// ── Hook: fetch expense categories with fallback ───────────────────────────────

function useExpenseCategories() {
  return useQuery({
    queryKey: ["job-expense-categories"],
    queryFn: async (): Promise<ExpenseCategoryItem[]> => {
      const res = await apiClient.get("/api/v1/job-expense-categories");
      return (res.data as { categories: ExpenseCategoryItem[] }).categories;
    },
    staleTime: 300_000, // 5 min — categories rarely change
    retry: 1,
  });
}

// ── API response type ─────────────────────────────────────────────────────────

interface JobExpense {
  id: string;
  tenant_id: string;
  job_id: string;
  job_expense_category_code: string;
  description: string | null;
  vendor_name: string | null;
  incurred_at: string;
  cost_cents: number;
}

// ── Component ─────────────────────────────────────────────────────────────────

interface ExpenseSectionProps {
  jobId: string;
  userId: string;
  testID?: string;
}

export function ExpenseSection({
  jobId,
  userId,
  testID,
}: ExpenseSectionProps): React.ReactElement {
  const [showAddForm, setShowAddForm] = useState(false);
  const [amountDollars, setAmountDollars] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("materials");
  const [description, setDescription] = useState("");
  const [isBillable, setIsBillable] = useState(true);

  const { create, isPending: isCreating } = useCreateExpense();

  // Fetch expense categories from API; fall back to hardcoded if API fails
  const { data: apiCategories, isError: categoriesError } =
    useExpenseCategories();

  const categories: { code: string; name: string }[] =
    apiCategories && apiCategories.length > 0
      ? apiCategories
      : MVP_EXPENSE_CATEGORIES.map((c) => ({ code: c.code, name: c.name }));

  const {
    data: expenses,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["job-expenses", jobId] as const,
    queryFn: () =>
      apiClient
        .get<JobExpense[]>(`/api/v1/jobs/${jobId}/expenses`)
        .then((r) => r.data),
    enabled: !!jobId,
    staleTime: 30_000,
  });

  const resetForm = useCallback(() => {
    setAmountDollars("");
    setSelectedCategory("materials");
    setDescription("");
    setIsBillable(true);
  }, []);

  const handleSubmit = useCallback(async () => {
    const dollars = parseFloat(amountDollars);
    if (isNaN(dollars) || dollars <= 0) {
      Alert.alert("Invalid amount", "Please enter a valid dollar amount.");
      return;
    }
    const costCents = Math.round(dollars * 100);
    try {
      await create({
        jobId,
        userId,
        jobExpenseCategoryCode: selectedCategory,
        costCents,
        description: description.trim() || undefined,
        isBillable,
        incurredAt: new Date(),
      });
      setShowAddForm(false);
      resetForm();
      void refetch();
    } catch {
      Alert.alert("Error", "Failed to save expense. Please try again.");
    }
  }, [
    amountDollars,
    create,
    description,
    isBillable,
    jobId,
    refetch,
    resetForm,
    selectedCategory,
    userId,
  ]);

  const categoryLabel =
    categories.find((c) => c.code === selectedCategory)?.name ??
    selectedCategory;

  return (
    <View style={styles.container} testID={testID ?? "expense-section"}>
      {/* Header row */}
      <View style={styles.headerRow}>
        <Text style={styles.sectionTitle}>EXPENSES</Text>
        <Pressable
          style={styles.addButton}
          onPress={() => setShowAddForm(true)}
          accessibilityRole="button"
          accessibilityLabel="Add expense"
          testID="add-expense-button"
        >
          <Text style={styles.addButtonText}>+ Add</Text>
        </Pressable>
      </View>

      {/* Expense list */}
      {isLoading && (
        <ActivityIndicator color={colors.brand[400]} style={styles.loader} />
      )}
      {!isLoading && (!expenses || expenses.length === 0) && (
        <Text style={styles.emptyText}>No expenses recorded</Text>
      )}
      {expenses?.map((expense) => (
        <View
          key={expense.id}
          style={styles.expenseRow}
          testID={`expense-row-${expense.id}`}
        >
          <View style={styles.expenseInfo}>
            <Text style={styles.expenseCategory}>
              {categories.find(
                (c) => c.code === expense.job_expense_category_code,
              )?.name ?? expense.job_expense_category_code}
            </Text>
            {expense.description ? (
              <Text style={styles.expenseDescription} numberOfLines={1}>
                {expense.description}
              </Text>
            ) : null}
          </View>
          <Text style={styles.expenseAmount}>
            ${(expense.cost_cents / 100).toFixed(2)}
          </Text>
        </View>
      ))}

      {/* Add Expense Bottom Sheet Modal */}
      <Modal
        visible={showAddForm}
        transparent
        animationType="slide"
        onRequestClose={() => {
          setShowAddForm(false);
          resetForm();
        }}
        testID="add-expense-modal"
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard} accessibilityViewIsModal>
            <Text style={styles.modalTitle}>Add Expense</Text>

            {/* Amount */}
            <View style={styles.fieldGroup}>
              <Text style={styles.fieldLabel}>Amount ($)</Text>
              <TextInput
                style={styles.textInput}
                value={amountDollars}
                onChangeText={setAmountDollars}
                placeholder="0.00"
                placeholderTextColor={colors.neutral[400]}
                keyboardType="decimal-pad"
                accessibilityLabel="Expense amount"
                testID="expense-amount-input"
              />
            </View>

            {/* Category picker */}
            <View style={styles.fieldGroup}>
              <Text style={styles.fieldLabel}>Category</Text>
              <ScrollView
                horizontal
                showsHorizontalScrollIndicator={false}
                style={styles.categoryScroll}
                contentContainerStyle={styles.categoryScrollContent}
              >
                {categories.map((cat) => (
                  <Pressable
                    key={cat.code}
                    style={[
                      styles.categoryChip,
                      selectedCategory === cat.code &&
                        styles.categoryChipSelected,
                    ]}
                    onPress={() => setSelectedCategory(cat.code)}
                    accessibilityRole="button"
                    accessibilityState={{
                      selected: selectedCategory === cat.code,
                    }}
                    testID={`category-chip-${cat.code}`}
                  >
                    <Text
                      style={[
                        styles.categoryChipText,
                        selectedCategory === cat.code &&
                          styles.categoryChipTextSelected,
                      ]}
                    >
                      {cat.name}
                    </Text>
                  </Pressable>
                ))}
              </ScrollView>
            </View>

            {/* Description */}
            <View style={styles.fieldGroup}>
              <Text style={styles.fieldLabel}>Description (optional)</Text>
              <TextInput
                style={[styles.textInput, styles.textInputMultiline]}
                value={description}
                onChangeText={setDescription}
                placeholder="e.g. 50ft 12AWG wire"
                placeholderTextColor={colors.neutral[400]}
                multiline
                numberOfLines={2}
                accessibilityLabel="Expense description"
                testID="expense-description-input"
              />
            </View>

            {/* Billable toggle */}
            <View style={styles.toggleRow}>
              <Text style={styles.fieldLabel}>Billable to customer</Text>
              <Switch
                value={isBillable}
                onValueChange={setIsBillable}
                trackColor={{
                  false: colors.neutral[600],
                  true: colors.brand[600],
                }}
                thumbColor={colors.neutral[50]}
                accessibilityLabel="Billable toggle"
                testID="billable-toggle"
              />
            </View>

            {/* Actions */}
            <View style={styles.modalActions}>
              <Pressable
                style={[styles.modalButton, styles.modalButtonSecondary]}
                onPress={() => {
                  setShowAddForm(false);
                  resetForm();
                }}
                accessibilityRole="button"
                testID="expense-cancel-button"
              >
                <Text style={styles.modalButtonSecondaryText}>Cancel</Text>
              </Pressable>
              <Pressable
                style={[
                  styles.modalButton,
                  styles.modalButtonPrimary,
                  isCreating && styles.modalButtonDisabled,
                ]}
                onPress={handleSubmit}
                disabled={isCreating}
                accessibilityRole="button"
                testID="expense-submit-button"
              >
                {isCreating ? (
                  <ActivityIndicator size="small" color={colors.neutral[50]} />
                ) : (
                  <Text style={styles.modalButtonPrimaryText}>Save</Text>
                )}
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.neutral[800],
    borderRadius: radii.md,
    padding: spacing[4],
    marginBottom: spacing[3],
    gap: spacing[3],
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
    marginVertical: spacing[2],
  },
  emptyText: {
    fontSize: mobileFontSizes.body,
    color: colors.neutral[400],
    lineHeight: 20,
  },
  expenseRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
    paddingVertical: spacing[2],
    borderTopWidth: 1,
    borderTopColor: colors.neutral[600],
    gap: spacing[2],
  },
  expenseInfo: {
    flex: 1,
    gap: spacing[1],
  },
  expenseCategory: {
    fontSize: mobileFontSizes.body,
    color: colors.neutral[200],
    lineHeight: 20,
    textTransform: "capitalize",
  },
  expenseDescription: {
    fontSize: mobileFontSizes.caption,
    color: colors.neutral[400],
    lineHeight: 16,
  },
  expenseAmount: {
    fontSize: mobileFontSizes.body,
    color: colors.neutral[50],
    fontWeight: String(fontWeights.medium) as "500",
    lineHeight: 20,
  },
  // Modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.7)",
    justifyContent: "flex-end",
    padding: spacing[4],
  },
  modalCard: {
    backgroundColor: colors.neutral[800],
    borderRadius: radii.lg,
    padding: spacing[6],
    gap: spacing[4],
  },
  modalTitle: {
    fontSize: mobileFontSizes.h2,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 28,
  },
  fieldGroup: {
    gap: spacing[2],
  },
  fieldLabel: {
    fontSize: mobileFontSizes.caption,
    color: colors.neutral[400],
    lineHeight: 16,
  },
  textInput: {
    backgroundColor: colors.neutral[900],
    borderRadius: radii.sm,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[3],
    fontSize: mobileFontSizes.body,
    color: colors.neutral[50],
    lineHeight: 20,
    borderWidth: 1,
    borderColor: colors.neutral[600],
  },
  textInputMultiline: {
    minHeight: 64,
    textAlignVertical: "top",
  },
  categoryScroll: {
    flexGrow: 0,
  },
  categoryScrollContent: {
    gap: spacing[2],
    paddingRight: spacing[1],
  },
  categoryChip: {
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2],
    borderRadius: radii.full,
    backgroundColor: colors.neutral[600],
    borderWidth: 1,
    borderColor: colors.neutral[400],
  },
  categoryChipSelected: {
    backgroundColor: colors.brand[800],
    borderColor: colors.brand[400],
  },
  categoryChipText: {
    fontSize: mobileFontSizes.caption,
    color: colors.neutral[200],
    lineHeight: 16,
  },
  categoryChipTextSelected: {
    color: colors.neutral[50],
  },
  toggleRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  modalActions: {
    flexDirection: "row",
    gap: spacing[3],
    marginTop: spacing[2],
  },
  modalButton: {
    flex: 1,
    minHeight: 44,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radii.md,
  },
  modalButtonPrimary: {
    backgroundColor: colors.brand[600],
  },
  modalButtonSecondary: {
    backgroundColor: colors.neutral[600],
  },
  modalButtonDisabled: {
    opacity: 0.5,
  },
  modalButtonPrimaryText: {
    fontSize: mobileFontSizes.body,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 20,
  },
  modalButtonSecondaryText: {
    fontSize: mobileFontSizes.body,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[200],
    lineHeight: 20,
  },
});
