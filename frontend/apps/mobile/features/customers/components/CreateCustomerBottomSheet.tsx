/**
 * CreateCustomerBottomSheet — Modal form for creating a new customer on mobile
 *
 * Location: apps/mobile/features/customers/components/CreateCustomerBottomSheet.tsx
 *
 * Fields (minimal — field is not the place for full customer setup):
 *   - Type: segmented control — "Person" / "Company"
 *   - Display Name (required)
 *   - Mobile Phone (optional)
 *   - Email (optional)
 *
 * Per batch-mob-b7-design.md §B5
 */

import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  Modal,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  SafeAreaView,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { colors, spacing, radii, fontWeights } from "@pilot/ui/tokens";
import { useCreateCustomer } from "../hooks/useCreateCustomer";

interface CreateCustomerBottomSheetProps {
  visible: boolean;
  onClose: () => void;
}

type CustomerType = "person" | "company";

export function CreateCustomerBottomSheet({
  visible,
  onClose,
}: CreateCustomerBottomSheetProps) {
  const [type, setType] = useState<CustomerType>("person");
  const [displayName, setDisplayName] = useState("");
  const [mobilePhone, setMobilePhone] = useState("");
  const [email, setEmail] = useState("");
  const [nameError, setNameError] = useState("");

  const { mutate: createCustomer, isPending } = useCreateCustomer();

  function resetForm() {
    setType("person");
    setDisplayName("");
    setMobilePhone("");
    setEmail("");
    setNameError("");
  }

  function handleClose() {
    resetForm();
    onClose();
  }

  function handleSubmit() {
    if (!displayName.trim()) {
      setNameError("Display name is required");
      return;
    }
    setNameError("");

    createCustomer(
      {
        type,
        display_name: displayName.trim(),
        mobile_phone: mobilePhone.trim() || undefined,
        email: email.trim() || undefined,
      },
      {
        onSuccess: () => {
          resetForm();
          onClose();
        },
      },
    );
  }

  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={handleClose}
      testID="create-customer-modal"
    >
      <SafeAreaView style={styles.safeArea}>
        <KeyboardAvoidingView
          style={styles.container}
          behavior={Platform.OS === "ios" ? "padding" : "height"}
        >
          {/* Header */}
          <View style={styles.header}>
            <Pressable
              onPress={handleClose}
              style={styles.cancelButton}
              accessibilityLabel="Cancel"
              testID="create-customer-cancel"
            >
              <Text style={styles.cancelText}>Cancel</Text>
            </Pressable>
            <Text style={styles.title}>New Customer</Text>
            <View style={styles.headerSpacer} />
          </View>

          <ScrollView
            style={styles.scroll}
            contentContainerStyle={styles.scrollContent}
            keyboardShouldPersistTaps="handled"
          >
            {/* Type Selector */}
            <Text style={styles.fieldLabel}>Type</Text>
            <View
              style={styles.segmentedControl}
              testID="customer-type-selector"
            >
              <Pressable
                style={[
                  styles.segment,
                  type === "person" && styles.segmentActive,
                ]}
                onPress={() => setType("person")}
                accessibilityRole="radio"
                accessibilityState={{ selected: type === "person" }}
                testID="type-person"
              >
                <Text
                  style={[
                    styles.segmentText,
                    type === "person" && styles.segmentTextActive,
                  ]}
                >
                  Person
                </Text>
              </Pressable>
              <Pressable
                style={[
                  styles.segment,
                  type === "company" && styles.segmentActive,
                ]}
                onPress={() => setType("company")}
                accessibilityRole="radio"
                accessibilityState={{ selected: type === "company" }}
                testID="type-company"
              >
                <Text
                  style={[
                    styles.segmentText,
                    type === "company" && styles.segmentTextActive,
                  ]}
                >
                  Company
                </Text>
              </Pressable>
            </View>

            {/* Display Name */}
            <Text style={styles.fieldLabel}>
              Display Name <Text style={styles.required}>*</Text>
            </Text>
            <TextInput
              style={[styles.input, !!nameError && styles.inputError]}
              value={displayName}
              onChangeText={(v) => {
                setDisplayName(v);
                if (v.trim()) setNameError("");
              }}
              placeholder="e.g. John Smith or Acme Corp"
              placeholderTextColor={colors.neutral[400]}
              autoCapitalize="words"
              autoCorrect={false}
              returnKeyType="next"
              testID="customer-display-name"
              accessibilityLabel="Display name"
            />
            {!!nameError && (
              <Text style={styles.errorText} testID="display-name-error">
                {nameError}
              </Text>
            )}

            {/* Mobile Phone */}
            <Text style={styles.fieldLabel}>Mobile Phone (optional)</Text>
            <TextInput
              style={styles.input}
              value={mobilePhone}
              onChangeText={setMobilePhone}
              placeholder="e.g. 555-867-5309"
              placeholderTextColor={colors.neutral[400]}
              keyboardType="phone-pad"
              returnKeyType="next"
              testID="customer-mobile-phone"
              accessibilityLabel="Mobile phone"
            />

            {/* Email */}
            <Text style={styles.fieldLabel}>Email (optional)</Text>
            <TextInput
              style={styles.input}
              value={email}
              onChangeText={setEmail}
              placeholder="e.g. john@example.com"
              placeholderTextColor={colors.neutral[400]}
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
              returnKeyType="done"
              onSubmitEditing={handleSubmit}
              testID="customer-email"
              accessibilityLabel="Email"
            />

            {/* Submit */}
            <Pressable
              style={[styles.submitButton, isPending && styles.submitDisabled]}
              onPress={handleSubmit}
              disabled={isPending}
              accessibilityRole="button"
              accessibilityLabel="Add customer"
              testID="create-customer-submit"
            >
              {isPending ? (
                <ActivityIndicator color="#FFFFFF" size="small" />
              ) : (
                <Text style={styles.submitText}>Add Customer</Text>
              )}
            </Pressable>
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: colors.neutral[50],
  },
  container: {
    flex: 1,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[200],
    backgroundColor: "#FFFFFF",
  },
  cancelButton: {
    minWidth: 60,
    minHeight: 44,
    justifyContent: "center",
  },
  cancelText: {
    color: colors.brand[600],
    fontSize: 16,
  },
  title: {
    flex: 1,
    textAlign: "center",
    fontSize: 17,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[900],
  },
  headerSpacer: {
    minWidth: 60,
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    padding: spacing[4],
    gap: spacing[2],
  },
  fieldLabel: {
    fontSize: 14,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[600],
    marginTop: spacing[3],
    marginBottom: spacing[1],
  },
  required: {
    color: "#EF4444",
  },
  segmentedControl: {
    flexDirection: "row",
    backgroundColor: colors.neutral[100],
    borderRadius: radii.md,
    padding: 2,
  },
  segment: {
    flex: 1,
    paddingVertical: spacing[2],
    alignItems: "center",
    borderRadius: radii.sm,
    minHeight: 36,
    justifyContent: "center",
  },
  segmentActive: {
    backgroundColor: "#FFFFFF",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 2,
    elevation: 2,
  },
  segmentText: {
    fontSize: 14,
    color: colors.neutral[400],
    fontWeight: String(fontWeights.medium) as "500",
  },
  segmentTextActive: {
    color: colors.neutral[900],
  },
  input: {
    backgroundColor: "#FFFFFF",
    borderWidth: 1,
    borderColor: colors.neutral[200],
    borderRadius: radii.md,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[3],
    fontSize: 16,
    color: colors.neutral[900],
    minHeight: 48,
  },
  inputError: {
    borderColor: "#EF4444",
  },
  errorText: {
    fontSize: 13,
    color: "#EF4444",
    marginTop: 2,
  },
  submitButton: {
    backgroundColor: colors.brand[600],
    borderRadius: radii.md,
    paddingVertical: spacing[4],
    alignItems: "center",
    justifyContent: "center",
    minHeight: 52,
    marginTop: spacing[4],
  },
  submitDisabled: {
    opacity: 0.6,
  },
  submitText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: String(fontWeights.medium) as "500",
  },
});
