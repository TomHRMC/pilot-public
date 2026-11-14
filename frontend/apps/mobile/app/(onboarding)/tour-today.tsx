/**
 * Tour: Today Tab Screen
 * Location: apps/mobile/app/(onboarding)/tour-today.tsx
 */

import React from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
} from "react-native";
import { useRouter } from "expo-router";

export default function TourTodayScreen() {
  const router = useRouter();

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <View
          style={styles.illustrationContainer}
          accessibilityRole="image"
          accessibilityLabel="Today tab illustration"
        >
          <Text style={styles.illustration}>📋</Text>
        </View>

        <Text style={styles.headline}>Your day at a glance</Text>
        <Text style={styles.subheadline}>
          The Today tab shows all your jobs, quotes, and customer activity for
          the day — everything you need, right when you need it.
        </Text>

        <View style={styles.featureList}>
          {[
            "Today's job schedule",
            "Pending quote approvals",
            "New customer messages",
            "Quick voice quote button",
          ].map((item) => (
            <View key={item} style={styles.featureRow}>
              <Text style={styles.featureCheck}>✓</Text>
              <Text style={styles.featureText}>{item}</Text>
            </View>
          ))}
        </View>

        <TouchableOpacity
          style={styles.button}
          onPress={() => router.push("/(onboarding)/tour-voice" as any)}
          accessibilityRole="button"
          accessibilityLabel="Next: Voice quoting"
          testID="tour-today-next"
        >
          <Text style={styles.buttonText}>Next →</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F9FAFB" },
  content: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 28,
    gap: 16,
  },
  illustrationContainer: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: "#EEF2FF",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 8,
  },
  illustration: { fontSize: 40 },
  headline: {
    fontSize: 24,
    fontWeight: "700",
    color: "#111827",
    textAlign: "center",
  },
  subheadline: {
    fontSize: 15,
    color: "#6B7280",
    textAlign: "center",
    lineHeight: 22,
  },
  featureList: {
    width: "100%",
    gap: 10,
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: "#F3F4F6",
  },
  featureRow: { flexDirection: "row", gap: 10, alignItems: "center" },
  featureCheck: { fontSize: 16, color: "#059669" },
  featureText: { fontSize: 14, color: "#374151" },
  button: {
    backgroundColor: "#4F46E5",
    paddingVertical: 14,
    paddingHorizontal: 32,
    borderRadius: 12,
    width: "100%",
    alignItems: "center",
    marginTop: 8,
  },
  buttonText: { color: "#FFFFFF", fontSize: 15, fontWeight: "600" },
});
