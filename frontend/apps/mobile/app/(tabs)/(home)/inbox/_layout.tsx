/**
 * Inbox stack layout — sub-navigation within the (home) group
 *
 * Location: apps/mobile/app/(tabs)/(home)/inbox/_layout.tsx
 *
 * Design doc Decision 1: SMS inbox lives as a sub-surface within
 * the existing (home) stack group — NOT a new dedicated tab.
 */

import { Stack } from "expo-router";
import React from "react";

export default function InboxLayout() {
  return (
    <Stack
      screenOptions={{
        headerShown: true,
      }}
    >
      <Stack.Screen
        name="index"
        options={{
          title: "Customer Messages",
          headerShown: true,
        }}
      />
      <Stack.Screen
        name="[threadId]"
        options={{
          headerShown: true,
          // Title set dynamically per thread in ThreadConversationScreen
        }}
      />
    </Stack>
  );
}
