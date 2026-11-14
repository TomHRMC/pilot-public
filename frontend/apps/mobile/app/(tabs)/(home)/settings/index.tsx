/**
 * Mobile Settings entry point — FE-B11
 *
 * Location: apps/mobile/app/(tabs)/(home)/settings/index.tsx
 *
 * Sections: My Account, Sync & Storage, Operations, Voice
 * Accessible from the Today tab header settings icon.
 */

import React from "react";
import { ScrollView, Text, Pressable, StyleSheet } from "react-native";
import { useRouter } from "expo-router";

const SETTINGS_GROUPS = [
  {
    label: "My Account",
    href: "/(tabs)/(home)/settings/my-account",
    icon: "👤",
  },
  {
    label: "Sync & Storage",
    href: "/(tabs)/(home)/settings/sync-storage",
    icon: "🔄",
  },
  {
    label: "Operations",
    href: "/(tabs)/(home)/settings/operations",
    icon: "⚙️",
  },
  { label: "Voice", href: "/(tabs)/(home)/settings/voice", icon: "🎙️" },
];

export default function MobileSettingsIndex() {
  const router = useRouter();

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      testID="mobile-settings-index"
    >
      <Text style={styles.heading}>Settings</Text>

      {SETTINGS_GROUPS.map((group) => (
        <Pressable
          key={group.href}
          style={({ pressed }) => [
            styles.groupItem,
            pressed && styles.groupItemPressed,
          ]}
          onPress={() =>
            router.push(group.href as Parameters<typeof router.push>[0])
          }
          accessibilityRole="button"
          accessibilityLabel={`Navigate to ${group.label} settings`}
          testID={`settings-group-${group.label.replace(/\s+/g, "-").toLowerCase()}`}
        >
          <Text style={styles.groupIcon}>{group.icon}</Text>
          <Text style={styles.groupLabel}>{group.label}</Text>
          <Text style={styles.groupChevron}>›</Text>
        </Pressable>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F9FAFB", // neutral-50
  },
  content: {
    padding: 16,
    gap: 4,
  },
  heading: {
    fontSize: 24,
    fontWeight: "500",
    color: "#111827", // neutral-900
    marginBottom: 16,
  },
  groupItem: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#FFFFFF",
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 14,
    borderWidth: 1,
    borderColor: "#E5E7EB", // neutral-200
    marginBottom: 4,
    gap: 12,
  },
  groupItemPressed: {
    backgroundColor: "#F3F4F6", // neutral-100
  },
  groupIcon: {
    fontSize: 18,
  },
  groupLabel: {
    flex: 1,
    fontSize: 16,
    fontWeight: "500",
    color: "#111827", // neutral-900
  },
  groupChevron: {
    fontSize: 20,
    color: "#9CA3AF", // neutral-400
  },
});
