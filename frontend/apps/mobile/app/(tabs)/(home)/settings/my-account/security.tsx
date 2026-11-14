/**
 * Security Settings Index (MOB-B10)
 * Route: /(tabs)/(home)/settings/my-account/security
 *
 * Nav cards:
 * - Two-Factor Authentication → pushes to .../security/mfa
 * - Password → Linking.openURL to web app (password change is browser-only in MVP)
 */
import React from "react";
import {
  ScrollView,
  Text,
  Pressable,
  View,
  StyleSheet,
  Linking,
} from "react-native";
import { useRouter } from "expo-router";
import { useMfaStatus } from "../../../../../features/account-settings/hooks/useMfaStatus";

const WEB_APP_URL = "https://app.pilotfortrades.com";

export default function SecurityIndexScreen() {
  const router = useRouter();
  const { data: mfaStatus, isLoading: mfaLoading } = useMfaStatus();

  const enrolledCount = mfaStatus?.enrolled_methods.length ?? 0;
  const mfaDescription = mfaLoading
    ? "Loading…"
    : enrolledCount === 0
      ? "No methods enrolled — tap to add"
      : `${enrolledCount} method${enrolledCount !== 1 ? "s" : ""} enrolled`;

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      testID="security-index-screen"
    >
      {/* MFA Card */}
      <Pressable
        style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
        onPress={() =>
          router.push("/(tabs)/(home)/settings/my-account/security/mfa" as any)
        }
        accessibilityRole="button"
        accessibilityLabel="Two-Factor Authentication settings"
        testID="mfa-nav-card"
      >
        <Text style={styles.cardIcon}>🔐</Text>
        <View style={styles.cardText}>
          <Text style={styles.cardTitle}>Two-Factor Authentication</Text>
          <Text style={styles.cardSubtitle} testID="mfa-description">
            {mfaDescription}
          </Text>
        </View>
        <Text style={styles.chevron}>›</Text>
      </Pressable>

      {/* Password Card — web link */}
      <Pressable
        style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
        onPress={() =>
          Linking.openURL(`${WEB_APP_URL}/settings/my-account/password`)
        }
        accessibilityRole="link"
        accessibilityLabel="Change password on web app"
        testID="password-nav-card"
      >
        <Text style={styles.cardIcon}>🔑</Text>
        <View style={styles.cardText}>
          <Text style={styles.cardTitle}>Password</Text>
          <Text style={styles.cardSubtitle}>Manage on the web app</Text>
        </View>
        <Text style={styles.chevron}>›</Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F9FAFB" },
  content: { padding: 16, gap: 8 },
  card: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#FFFFFF",
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 14,
    borderWidth: 1,
    borderColor: "#E5E7EB",
    marginBottom: 4,
    gap: 12,
  },
  cardPressed: { backgroundColor: "#F3F4F6" },
  cardIcon: { fontSize: 18 },
  cardText: { flex: 1 },
  cardTitle: {
    fontSize: 15,
    fontWeight: "500" as const,
    color: "#111827",
  },
  cardSubtitle: { fontSize: 12, color: "#6B7280", marginTop: 2 },
  chevron: { fontSize: 20, color: "#9CA3AF" },
});
