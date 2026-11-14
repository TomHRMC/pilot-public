/**
 * Mobile Operations settings — FE-B11
 *
 * Location: apps/mobile/app/(tabs)/(home)/settings/operations.tsx
 */

import React from "react";
import {
  ScrollView,
  Text,
  View,
  StyleSheet,
  ActivityIndicator,
} from "react-native";
import { useMobileSettingsCatalog } from "../../../../features/settings/hooks/useMobileSettingsCatalog";
import { OperationsSettingsSection } from "../../../../features/settings/components/OperationsSettingsSection";

export default function MobileOperationsSettings() {
  const { catalogMap, isLoading, isError } = useMobileSettingsCatalog();

  if (isError) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>
          Failed to load settings. Pull to refresh.
        </Text>
      </View>
    );
  }

  if (isLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#4F46E5" />
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      testID="mobile-operations-settings"
    >
      <Text style={styles.heading}>Operations</Text>
      <Text style={styles.hint}>
        These settings are configured by your company admin and are shown here
        for reference.
      </Text>

      <OperationsSettingsSection
        catalogEntries={catalogMap}
        testID="mobile-operations-section"
      />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F9FAFB" },
  content: { padding: 16, gap: 8 },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  heading: {
    fontSize: 22,
    fontWeight: "500",
    color: "#111827",
    marginBottom: 4,
  },
  hint: { fontSize: 12, color: "#6B7280", marginBottom: 8 },
  errorText: { fontSize: 14, color: "#DC2626" },
});
