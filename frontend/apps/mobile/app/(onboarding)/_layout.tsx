/**
 * Onboarding route group layout — mobile
 *
 * Location: apps/mobile/app/(onboarding)/_layout.tsx
 *
 * Full-screen, no tab bar, no back navigation into onboarding from main shell.
 * "Skip tutorial" link rendered in the top-right via screenOptions header.
 * Design doc Decision 5.
 */

import { Stack, useRouter } from "expo-router";
import React from "react";
import { TouchableOpacity, Text, StyleSheet } from "react-native";

export default function OnboardingLayout() {
  const router = useRouter();

  const handleSkip = () => {
    router.replace("/(tabs)/(home)");
  };

  return (
    <Stack
      screenOptions={{
        headerShown: true,
        headerTransparent: true,
        headerTitle: "",
        headerLeft: () => null, // No back navigation in onboarding
        headerRight: () => (
          <TouchableOpacity
            onPress={handleSkip}
            accessibilityLabel="Skip tutorial"
            accessibilityRole="button"
            testID="onboarding-skip-tutorial"
          >
            <Text style={styles.skipText}>Skip</Text>
          </TouchableOpacity>
        ),
        animation: "slide_from_right",
      }}
    >
      <Stack.Screen name="welcome" />
      <Stack.Screen name="push-permission" />
      <Stack.Screen name="tour-today" />
      <Stack.Screen name="tour-voice" />
      <Stack.Screen
        name="tour-done"
        options={{
          headerRight: () => null, // No skip on the final screen
        }}
      />
    </Stack>
  );
}

const styles = StyleSheet.create({
  skipText: {
    fontSize: 14,
    color: "#6B7280", // neutral-500 equivalent
    paddingHorizontal: 8,
  },
});
