/**
 * Home tab nested stack navigator
 *
 * Location: apps/mobile/app/(tabs)/(home)/_layout.tsx
 *
 * Per Decision 1 in batch-fe-b3-design.md:
 * Voice quote creation lives as a nested stack route within the Home tab.
 * This layout provides the Stack navigator for the (home) route group.
 *
 * MOB-B10: Added 7 Stack.Screen registrations for settings/* routes,
 * gear icon headerRight on the Home index screen, and headerShown: true
 * for all settings sub-screens.
 */

import { Stack, useRouter } from "expo-router";
import React from "react";
import { Pressable, Text } from "react-native";

function GearButton() {
  const router = useRouter();
  return (
    <Pressable
      onPress={() => router.push("/(tabs)/(home)/settings" as any)}
      style={{ paddingRight: 16, paddingVertical: 8 }}
      hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
      accessibilityLabel="Open settings"
      accessibilityRole="button"
      testID="home-gear-button"
    >
      <Text style={{ fontSize: 20 }}>⚙️</Text>
    </Pressable>
  );
}

export default function HomeLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }}>
      {/* Home screen — shows header with gear icon */}
      <Stack.Screen
        name="index"
        options={{
          title: "Home",
          headerShown: true,
          headerRight: () => <GearButton />,
        }}
      />
      {/* Voice routes */}
      <Stack.Screen
        name="voice/index"
        options={{ title: "Voice Sessions", headerShown: true }}
      />
      <Stack.Screen
        name="voice/[sessionId]"
        options={{ title: "Voice Session", headerShown: false }}
      />
      {/* MOB-B10: Settings stack — all 7 routes registered */}
      <Stack.Screen
        name="settings/index"
        options={{ title: "Settings", headerShown: true }}
      />
      <Stack.Screen
        name="settings/my-account"
        options={{ title: "My Account", headerShown: true }}
      />
      <Stack.Screen
        name="settings/my-account/security"
        options={{ title: "Security", headerShown: true }}
      />
      <Stack.Screen
        name="settings/my-account/security/mfa"
        options={{ title: "Two-Factor Authentication", headerShown: true }}
      />
      <Stack.Screen
        name="settings/operations"
        options={{ title: "Operations", headerShown: true }}
      />
      <Stack.Screen
        name="settings/sync-storage"
        options={{ title: "Sync & Storage", headerShown: true }}
      />
      <Stack.Screen
        name="settings/voice"
        options={{ title: "Voice & AI", headerShown: true }}
      />
    </Stack>
  );
}
