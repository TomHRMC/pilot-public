/**
 * Tour: Voice Quoting Screen
 * Location: apps/mobile/app/(onboarding)/tour-voice.tsx
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

export default function TourVoiceScreen() {
  const router = useRouter();

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <View
          style={styles.iconContainer}
          accessibilityRole="image"
          accessibilityLabel="Microphone icon"
        >
          <Text style={styles.icon}>🎙️</Text>
        </View>

        <Text style={styles.headline}>Quote by voice in 30 seconds</Text>
        <Text style={styles.subheadline}>
          Just tap the mic and describe the job. Pilot turns your words into a
          professional quote — parts, labor, and all.
        </Text>

        <View style={styles.stepList}>
          {[
            {
              step: "1",
              text: 'Tap the mic and say "Install 20A circuit for kitchen"',
            },
            {
              step: "2",
              text: "Pilot extracts materials, labor, and NEC code requirements",
            },
            { step: "3", text: "Review and send the quote in seconds" },
          ].map((item) => (
            <View key={item.step} style={styles.stepRow}>
              <View style={styles.stepBadge}>
                <Text style={styles.stepNumber}>{item.step}</Text>
              </View>
              <Text style={styles.stepText}>{item.text}</Text>
            </View>
          ))}
        </View>

        <TouchableOpacity
          style={styles.button}
          onPress={() => router.push("/(onboarding)/tour-done" as any)}
          accessibilityRole="button"
          accessibilityLabel="Next: Finish setup"
          testID="tour-voice-next"
        >
          <Text style={styles.buttonText}>Almost done →</Text>
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
  iconContainer: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: "#EEF2FF",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 8,
  },
  icon: { fontSize: 40 },
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
  stepList: {
    width: "100%",
    gap: 12,
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: "#F3F4F6",
  },
  stepRow: { flexDirection: "row", gap: 12, alignItems: "flex-start" },
  stepBadge: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: "#4F46E5",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
  },
  stepNumber: { color: "#FFFFFF", fontSize: 12, fontWeight: "700" },
  stepText: { flex: 1, fontSize: 13, color: "#374151", lineHeight: 20 },
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
