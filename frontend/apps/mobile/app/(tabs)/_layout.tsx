import { Tabs } from "expo-router";
import React from "react";

import { HapticTab } from "@/components/haptic-tab";
import { IconSymbol } from "@/components/ui/icon-symbol";
import { Colors } from "@/constants/theme";
import { useColorScheme } from "@/hooks/use-color-scheme";

export default function TabLayout() {
  const colorScheme = useColorScheme();

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: Colors[colorScheme ?? "light"].tint,
        headerShown: false,
        tabBarButton: HapticTab,
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Home",
          tabBarIcon: ({ color }) => (
            <IconSymbol size={28} name="house.fill" color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="jobs"
        options={{
          title: "Jobs",
          tabBarIcon: ({ color }) => (
            <IconSymbol size={28} name="briefcase.fill" color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="customers"
        options={{
          title: "Customers",
          tabBarIcon: ({ color }) => (
            <IconSymbol size={28} name="person.2.fill" color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="calcs"
        options={{
          title: "Calcs",
          tabBarIcon: ({ color }) => (
            <IconSymbol size={28} name="function" color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="owner"
        options={{
          title: "Owner",
          tabBarIcon: ({ color }) => (
            <IconSymbol size={28} name="person.badge.key.fill" color={color} />
          ),
        }}
      />

      {/* Hide non-tab screens that Expo Router auto-discovers from the tab bar.
          (home) is a route group — omitted here since groups are transparent.
          Only concrete file-based screens need explicit href: null suppression. */}
      <Tabs.Screen name="more/about" options={{ href: null }} />
      <Tabs.Screen name="more/help/index" options={{ href: null }} />
      <Tabs.Screen name="more/help/history" options={{ href: null }} />
      <Tabs.Screen name="more/help/feedback" options={{ href: null }} />
      <Tabs.Screen name="customers/[id]/comms" options={{ href: null }} />
      {/* MOB-B3: Customer detail screen — suppress from tab bar */}
      <Tabs.Screen name="customers/[id]/index" options={{ href: null }} />
      <Tabs.Screen name="jobs/[jobId]/comms" options={{ href: null }} />
      {/* MOB-B1: Job detail screen (built in MOB-B2) — suppress from tab bar */}
      <Tabs.Screen name="jobs/[jobId]/index" options={{ href: null }} />
      {/* CE-1 Part B: Invoice sign-off capture screen — suppress from tab bar */}
      <Tabs.Screen
        name="jobs/[jobId]/invoice-signoff"
        options={{ href: null }}
      />
      {/* MOB-B4: Calcs sub-screens — suppress from tab bar */}
      <Tabs.Screen name="calcs/voltage-drop" options={{ href: null }} />
      <Tabs.Screen name="calcs/conduit-fill" options={{ href: null }} />
      <Tabs.Screen name="calcs/ampacity" options={{ href: null }} />
      <Tabs.Screen name="calcs/saved-calcs" options={{ href: null }} />
      {/* MOB-B10: New settings deep routes — suppress from tab bar */}
      <Tabs.Screen name="(home)/settings/my-account" options={{ href: null }} />
      <Tabs.Screen
        name="(home)/settings/my-account/security"
        options={{ href: null }}
      />
      <Tabs.Screen
        name="(home)/settings/my-account/security/mfa"
        options={{ href: null }}
      />
    </Tabs>
  );
}
