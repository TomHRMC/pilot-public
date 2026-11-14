/**
 * Onboarding Welcome Screen
 * Location: apps/mobile/app/(onboarding)/welcome.tsx
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

export default function OnboardingWelcomeScreen() {
  const router = useRouter();

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        {/* Icon */}
        <View
          style={styles.iconContainer}
          accessibilityRole="image"
          accessibilityLabel="Pilot logo"
        >
          <Text style={styles.icon}>⚡</Text>
        </View>

        {/* Copy */}
        <Text style={styles.headline}>Welcome to Pilot</Text>
        <Text style={styles.subheadline}>
          Your field operations, simplified.{"\n"}
          Let&apos;s get you set up in a minute.
        </Text>

        {/* CTA */}
        <TouchableOpacity
          style={styles.button}
          onPress={() => router.push("/(onboarding)/push-permission" as any)}
          accessibilityRole="button"
          accessibilityLabel="Get started"
          testID="onboarding-welcome-continue"
        >
          <Text style={styles.buttonText}>Get started →</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F9FAFB",
  },
  content: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 32,
    gap: 16,
  },
  iconContainer: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: "#EEF2FF",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 8,
  },
  icon: {
    fontSize: 40,
  },
  headline: {
    fontSize: 28,
    fontWeight: "700",
    color: "#111827",
    textAlign: "center",
  },
  subheadline: {
    fontSize: 16,
    color: "#6B7280",
    textAlign: "center",
    lineHeight: 24,
  },
  button: {
    marginTop: 24,
    backgroundColor: "#4F46E5",
    paddingVertical: 14,
    paddingHorizontal: 32,
    borderRadius: 12,
    width: "100%",
    alignItems: "center",
  },
  buttonText: {
    color: "#FFFFFF",
    fontSize: 15,
    fontWeight: "600",
  },
});
