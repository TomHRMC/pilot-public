/**
 * CalcsMenuScreen — NEC Calculator Suite Menu
 *
 * Location: apps/mobile/features/nec-calcs/components/CalcsMenuScreen.tsx
 *
 * Top-level menu for the Calcs tab. 5 rows:
 *   - Voltage Drop Calculator (navigable)
 *   - Conduit Fill Calculator (navigable)
 *   - Ampacity Calculator (navigable)
 *   - NEC 2023 Reference (disabled — "Coming soon" for MVP)
 *   - Saved Calculations (navigable)
 *
 * Per batch-mob-b4-design.md §F.4 and §H.1.
 */

import React from "react";
import {
  SafeAreaView,
  View,
  Text,
  Pressable,
  ScrollView,
  StyleSheet,
} from "react-native";
import { router } from "expo-router";
import { tokens } from "@pilot/ui/tokens";

// ---------------------------------------------------------------------------
// Menu items
// ---------------------------------------------------------------------------

const MENU_ITEMS = [
  {
    icon: "⚡",
    label: "Voltage Drop Calculator",
    route: "/(tabs)/calcs/voltage-drop" as const,
    testID: "menu-voltage-drop",
    enabled: true,
  },
  {
    icon: "📐",
    label: "Conduit Fill Calculator",
    route: "/(tabs)/calcs/conduit-fill" as const,
    testID: "menu-conduit-fill",
    enabled: true,
  },
  {
    icon: "🔌",
    label: "Ampacity Calculator",
    route: "/(tabs)/calcs/ampacity" as const,
    testID: "menu-ampacity",
    enabled: true,
  },
  {
    icon: "📚",
    label: "NEC 2023 Reference",
    route: null,
    testID: "menu-nec-reference",
    enabled: false,
  },
  {
    icon: "🕐",
    label: "Saved Calculations",
    route: "/(tabs)/calcs/saved-calcs" as const,
    testID: "menu-saved-calcs",
    enabled: true,
  },
] as const;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function CalcsMenuScreen() {
  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView>
        <Text style={styles.title}>Calcs</Text>
        <View style={styles.divider} />
        {MENU_ITEMS.map((item) => {
          if (!item.enabled) {
            return (
              <View
                key={item.label}
                style={[styles.menuRow, styles.disabled]}
                testID={item.testID}
              >
                <Text style={[styles.menuIcon]}>{item.icon}</Text>
                <Text style={[styles.menuLabel, styles.disabledText]}>
                  {item.label}
                </Text>
                <Text style={styles.comingSoon}>Coming soon</Text>
              </View>
            );
          }

          return (
            <React.Fragment key={item.label}>
              <Pressable
                onPress={() => router.push(item.route as never)}
                style={({ pressed }) => [
                  styles.menuRow,
                  pressed && styles.pressed,
                ]}
                testID={item.testID}
                accessibilityRole="button"
                accessibilityLabel={item.label}
              >
                <Text style={styles.menuIcon}>{item.icon}</Text>
                <Text style={styles.menuLabel}>{item.label}</Text>
                <Text style={styles.chevron}>›</Text>
              </Pressable>
              <View style={styles.divider} />
            </React.Fragment>
          );
        })}
      </ScrollView>
    </SafeAreaView>
  );
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: tokens.colors.neutral[50],
  },
  title: {
    fontSize: tokens.webFontSizes.h1,
    fontWeight: "700" as const,
    color: tokens.colors.neutral[900],
    paddingHorizontal: tokens.spacing[4],
    paddingTop: tokens.spacing[6],
    paddingBottom: tokens.spacing[4],
  },
  divider: {
    height: 1,
    backgroundColor: tokens.colors.neutral[200],
    marginHorizontal: tokens.spacing[4],
  },
  menuRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: tokens.spacing[4],
    paddingVertical: tokens.spacing[4],
    backgroundColor: tokens.colors.neutral[50],
  },
  pressed: {
    backgroundColor: tokens.colors.neutral[100],
  },
  disabled: {
    opacity: 0.5,
  },
  menuIcon: {
    fontSize: 22,
    marginRight: tokens.spacing[3],
    width: 28,
    textAlign: "center" as const,
  },
  menuLabel: {
    flex: 1,
    fontSize: tokens.webFontSizes.bodyLg,
    color: tokens.colors.neutral[900],
  },
  disabledText: {
    color: tokens.colors.neutral[400],
  },
  chevron: {
    fontSize: 22,
    color: tokens.colors.neutral[400],
    fontWeight: "300" as const,
  },
  comingSoon: {
    fontSize: tokens.webFontSizes.caption,
    color: tokens.colors.neutral[400],
    fontStyle: "italic" as const,
  },
});
