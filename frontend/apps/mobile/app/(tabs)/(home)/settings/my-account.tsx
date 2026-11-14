/**
 * My Account — Profile Settings (MOB-B10)
 * Route: /(tabs)/(home)/settings/my-account
 *
 * Endpoints verified: GET/PATCH /api/v1/users/me/profile
 * Response fields: id, first_name, last_name, email, phone_number, time_zone
 *
 * Save-on-blur pattern: onEndEditing fires PATCH with just the changed field.
 */
import React, { useState } from "react";
import {
  ScrollView,
  Text,
  TextInput,
  View,
  StyleSheet,
  ActivityIndicator,
  Pressable,
  Modal,
  FlatList,
} from "react-native";
import { useRouter } from "expo-router";
import { useMyProfile } from "../../../../features/account-settings/hooks/useMyProfile";

// 8 US timezone options for the picker modal (@react-native-picker/picker not installed — §G.2)
const TIMEZONE_OPTIONS = [
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "America/Phoenix",
  "America/Anchorage",
  "Pacific/Honolulu",
  "America/Puerto_Rico",
];

export default function MyAccountScreen() {
  const router = useRouter();
  const { profile, isLoading, isError, updateField, isPending } =
    useMyProfile();
  const [saveStatus, setSaveStatus] = useState<
    Record<string, "saved" | "error" | null>
  >({});
  const [showTimezonePicker, setShowTimezonePicker] = useState(false);
  const [localTimezone, setLocalTimezone] = useState<string | null>(null);

  const handleEndEditing = async (field: string, value: string) => {
    // phone_number: pass null when cleared, otherwise pass value
    const payload = field === "phone_number" ? value || null : value;
    try {
      await updateField(field, payload);
      setSaveStatus((prev) => ({ ...prev, [field]: "saved" }));
      setTimeout(
        () => setSaveStatus((prev) => ({ ...prev, [field]: null })),
        2000,
      );
    } catch {
      setSaveStatus((prev) => ({ ...prev, [field]: "error" }));
    }
  };

  const handleTimezoneSelect = async (tz: string) => {
    setLocalTimezone(tz);
    setShowTimezonePicker(false);
    try {
      await updateField("time_zone", tz);
      setSaveStatus((prev) => ({ ...prev, time_zone: "saved" }));
      setTimeout(
        () => setSaveStatus((prev) => ({ ...prev, time_zone: null })),
        2000,
      );
    } catch {
      setSaveStatus((prev) => ({ ...prev, time_zone: "error" }));
    }
  };

  if (isError) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>
          Failed to load profile. Please try again.
        </Text>
      </View>
    );
  }

  if (isLoading || !profile) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#4F46E5" />
      </View>
    );
  }

  const currentTimezone = localTimezone ?? profile.time_zone;

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      testID="my-account-screen"
    >
      {/* First name */}
      <View style={styles.fieldGroup}>
        <Text style={styles.label}>First name</Text>
        <TextInput
          style={styles.input}
          defaultValue={profile.first_name}
          onEndEditing={(e) =>
            handleEndEditing("first_name", e.nativeEvent.text)
          }
          autoCapitalize="words"
          returnKeyType="done"
          accessibilityLabel="First name"
          testID="first-name-input"
        />
        {saveStatus.first_name === "saved" && (
          <Text style={styles.savedText} testID="first-name-saved">
            Saved ✓
          </Text>
        )}
        {saveStatus.first_name === "error" && (
          <Text style={styles.fieldErrorText}>Failed to save. Try again.</Text>
        )}
      </View>

      {/* Last name */}
      <View style={styles.fieldGroup}>
        <Text style={styles.label}>Last name</Text>
        <TextInput
          style={styles.input}
          defaultValue={profile.last_name}
          onEndEditing={(e) =>
            handleEndEditing("last_name", e.nativeEvent.text)
          }
          autoCapitalize="words"
          returnKeyType="done"
          accessibilityLabel="Last name"
          testID="last-name-input"
        />
        {saveStatus.last_name === "saved" && (
          <Text style={styles.savedText} testID="last-name-saved">
            Saved ✓
          </Text>
        )}
        {saveStatus.last_name === "error" && (
          <Text style={styles.fieldErrorText}>Failed to save. Try again.</Text>
        )}
      </View>

      {/* Email — read-only */}
      <View style={styles.fieldGroup}>
        <Text style={styles.label}>Email</Text>
        <TextInput
          style={[styles.input, styles.inputDisabled]}
          value={profile.email}
          editable={false}
          accessibilityLabel="Email address"
          testID="email-input"
        />
        <Text style={styles.hint}>
          Contact support to change your email address.
        </Text>
      </View>

      {/* Phone number */}
      <View style={styles.fieldGroup}>
        <Text style={styles.label}>Phone number</Text>
        <TextInput
          style={styles.input}
          defaultValue={profile.phone_number ?? ""}
          onEndEditing={(e) =>
            handleEndEditing("phone_number", e.nativeEvent.text)
          }
          keyboardType="phone-pad"
          returnKeyType="done"
          accessibilityLabel="Phone number"
          testID="phone-input"
        />
        {saveStatus.phone_number === "saved" && (
          <Text style={styles.savedText} testID="phone-saved">
            Saved ✓
          </Text>
        )}
        {saveStatus.phone_number === "error" && (
          <Text style={styles.fieldErrorText}>Failed to save. Try again.</Text>
        )}
      </View>

      {/* Timezone — modal picker */}
      <View style={styles.fieldGroup}>
        <Text style={styles.label}>Timezone</Text>
        <Pressable
          style={({ pressed }) => [
            styles.input,
            styles.timezoneButton,
            pressed && styles.timezoneButtonPressed,
          ]}
          onPress={() => setShowTimezonePicker(true)}
          accessibilityLabel="Select timezone"
          accessibilityRole="button"
          testID="timezone-picker-btn"
        >
          <Text style={styles.timezoneText}>{currentTimezone}</Text>
          <Text style={styles.timezoneChevron}>▼</Text>
        </Pressable>
        {saveStatus.time_zone === "saved" && (
          <Text style={styles.savedText} testID="timezone-saved">
            Saved ✓
          </Text>
        )}
        {saveStatus.time_zone === "error" && (
          <Text style={styles.fieldErrorText}>Failed to save. Try again.</Text>
        )}
      </View>

      {isPending && (
        <Text style={styles.hint} testID="saving-indicator">
          Saving…
        </Text>
      )}

      {/* Security nav card */}
      <Pressable
        style={({ pressed }) => [
          styles.securityCard,
          pressed && styles.securityCardPressed,
        ]}
        onPress={() =>
          router.push("/(tabs)/(home)/settings/my-account/security" as any)
        }
        accessibilityRole="button"
        accessibilityLabel="Security settings"
        testID="security-nav-card"
      >
        <Text style={styles.securityCardIcon}>🔐</Text>
        <View style={styles.securityCardText}>
          <Text style={styles.securityCardTitle}>Security</Text>
          <Text style={styles.securityCardSubtitle}>
            Two-Factor Authentication, Password
          </Text>
        </View>
        <Text style={styles.securityCardChevron}>›</Text>
      </Pressable>

      {/* Timezone modal */}
      <Modal
        visible={showTimezonePicker}
        transparent
        animationType="slide"
        onRequestClose={() => setShowTimezonePicker(false)}
        testID="timezone-modal"
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalSheet}>
            <Text style={styles.modalTitle}>Select Timezone</Text>
            <FlatList
              data={TIMEZONE_OPTIONS}
              keyExtractor={(item) => item}
              renderItem={({ item }) => (
                <Pressable
                  style={({ pressed }) => [
                    styles.timezoneOption,
                    item === currentTimezone && styles.timezoneOptionSelected,
                    pressed && styles.timezoneOptionPressed,
                  ]}
                  onPress={() => handleTimezoneSelect(item)}
                  accessibilityRole="button"
                  accessibilityLabel={item}
                  testID={`tz-option-${item}`}
                >
                  <Text
                    style={[
                      styles.timezoneOptionText,
                      item === currentTimezone &&
                        styles.timezoneOptionTextSelected,
                    ]}
                  >
                    {item}
                  </Text>
                </Pressable>
              )}
            />
            <Pressable
              style={styles.modalCancel}
              onPress={() => setShowTimezonePicker(false)}
              testID="timezone-cancel-btn"
            >
              <Text style={styles.modalCancelText}>Cancel</Text>
            </Pressable>
          </View>
        </View>
      </Modal>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F9FAFB" },
  content: { padding: 16, gap: 16 },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  fieldGroup: { gap: 4 },
  label: {
    fontSize: 13,
    fontWeight: "500" as const,
    color: "#374151",
    marginBottom: 4,
  },
  input: {
    borderWidth: 1,
    borderColor: "#D1D5DB",
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 15,
    color: "#111827",
    backgroundColor: "#FFFFFF",
  },
  inputDisabled: {
    backgroundColor: "#F3F4F6",
    color: "#9CA3AF",
  },
  timezoneButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  timezoneButtonPressed: { backgroundColor: "#F3F4F6" },
  timezoneText: { fontSize: 15, color: "#111827", flex: 1 },
  timezoneChevron: { fontSize: 12, color: "#6B7280", marginLeft: 8 },
  savedText: { fontSize: 12, color: "#059669", marginTop: 2 },
  fieldErrorText: { fontSize: 12, color: "#DC2626", marginTop: 2 },
  errorText: { fontSize: 14, color: "#DC2626" },
  hint: { fontSize: 12, color: "#6B7280", marginTop: 2 },
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.4)",
    justifyContent: "flex-end",
  },
  modalSheet: {
    backgroundColor: "#FFFFFF",
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    paddingTop: 16,
    paddingBottom: 32,
    maxHeight: "60%",
  },
  modalTitle: {
    fontSize: 16,
    fontWeight: "600" as const,
    color: "#111827",
    textAlign: "center",
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#E5E7EB",
    marginBottom: 8,
    paddingHorizontal: 16,
  },
  timezoneOption: {
    paddingVertical: 14,
    paddingHorizontal: 20,
    borderBottomWidth: 1,
    borderBottomColor: "#F3F4F6",
  },
  timezoneOptionSelected: { backgroundColor: "#EEF2FF" },
  timezoneOptionPressed: { backgroundColor: "#F3F4F6" },
  timezoneOptionText: { fontSize: 15, color: "#374151" },
  timezoneOptionTextSelected: { color: "#4F46E5", fontWeight: "500" as const },
  modalCancel: {
    marginTop: 8,
    paddingVertical: 14,
    alignItems: "center",
  },
  modalCancelText: { fontSize: 15, color: "#6B7280" },
  securityCard: {
    flexDirection: "row" as const,
    alignItems: "center" as const,
    backgroundColor: "#FFFFFF",
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 14,
    borderWidth: 1,
    borderColor: "#E5E7EB",
    gap: 12,
    marginTop: 8,
  },
  securityCardPressed: { backgroundColor: "#F3F4F6" },
  securityCardIcon: { fontSize: 18 },
  securityCardText: { flex: 1 },
  securityCardTitle: {
    fontSize: 15,
    fontWeight: "500" as const,
    color: "#111827",
  },
  securityCardSubtitle: { fontSize: 12, color: "#6B7280", marginTop: 2 },
  securityCardChevron: { fontSize: 20, color: "#9CA3AF" },
});
