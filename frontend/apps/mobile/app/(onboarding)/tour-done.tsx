/**
 * Tour Done — Final onboarding screen
 * Location: apps/mobile/app/(onboarding)/tour-done.tsx
 * Transitions to (tabs)/(home) after confirmation.
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

export default function TourDoneScreen() {
  const router = useRouter();

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.celebration}>🎉</Text>
        <Text style={styles.headline}>You&apos;re all set!</Text>
        <Text style={styles.subheadline}>
          Pilot is ready to help you quote faster, manage jobs, and get paid —
          all from your phone.
        </Text>

        <TouchableOpacity
          style={styles.button}
          onPress={() => router.replace("/(tabs)/(home)" as never)}
          accessibilityRole="button"
          accessibilityLabel="Open Pilot"
          testID="tour-done-open-pilot"
        >
          <Text style={styles.buttonText}>Open Pilot →</Text>
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
    paddingHorizontal: 32,
    gap: 16,
  },
  celebration: { fontSize: 64 },
  headline: {
    fontSize: 28,
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
  button: {
    backgroundColor: "#4F46E5",
    paddingVertical: 16,
    paddingHorizontal: 32,
    borderRadius: 12,
    width: "100%",
    alignItems: "center",
    marginTop: 24,
  },
  buttonText: { color: "#FFFFFF", fontSize: 16, fontWeight: "700" },
});
