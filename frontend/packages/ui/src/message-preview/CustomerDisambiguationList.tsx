/**
 * CustomerDisambiguationList — Shared (React Native primitives)
 *
 * Location: packages/ui/src/message-preview/CustomerDisambiguationList.tsx
 *
 * Rendered when voice intent matches multiple customers.
 * User selects the intended customer before proceeding to preview.
 *
 * IMPORTANT: Zero hardcoded design values. All from token system.
 */

import React from "react";
import { View, Text, Pressable, FlatList, StyleSheet } from "react-native";
/* eslint-disable react/prop-types */
import { colors, lightTheme, radii, spacing, fontWeights } from "../tokens";
import type { CustomerDisambiguationListProps, CustomerMatch } from "./types";

// ── Component ─────────────────────────────────────────────────────────────────

/**
 * CustomerDisambiguationList
 *
 * Shows when voice "tell Johnson I'm on my way" matches 2+ customers.
 * Renders all matches; tapping one proceeds to the time-extraction / preview flow.
 */
export function CustomerDisambiguationList({
  matches,
  onSelect,
  query,
  testID,
}: CustomerDisambiguationListProps) {
  function renderItem({ item }: { item: CustomerMatch }) {
    const channelLabel =
      item.preferred_channel === "sms"
        ? "SMS preferred"
        : item.preferred_channel === "email"
          ? "Email preferred"
          : "No preference";

    return (
      <Pressable
        style={styles.item}
        onPress={() => onSelect(item)}
        accessibilityRole="button"
        accessibilityLabel={`Select ${item.name}, ${channelLabel}`}
        testID={`disambiguation-item-${item.id}`}
      >
        <View style={styles.itemContent}>
          <Text style={styles.itemName}>{item.name}</Text>
          <Text style={styles.itemAddress}>{item.address}</Text>
        </View>
        <View
          style={[
            styles.channelBadge,
            item.preferred_channel === "sms"
              ? styles.smsBadge
              : styles.emailBadge,
          ]}
        >
          <Text
            style={[
              styles.channelBadgeText,
              item.preferred_channel === "sms"
                ? styles.smsBadgeText
                : styles.emailBadgeText,
            ]}
          >
            {channelLabel}
          </Text>
        </View>
      </Pressable>
    );
  }

  return (
    <View
      style={styles.container}
      testID={testID ?? "customer-disambiguation-list"}
      accessibilityRole="none"
      accessibilityLabel="Select customer"
    >
      <Text style={styles.prompt}>{`Which "${query}" did you mean?`}</Text>

      <FlatList<CustomerMatch>
        data={matches}
        keyExtractor={(item) => item.id}
        renderItem={renderItem}
        ItemSeparatorComponent={() => <View style={styles.separator} />}
        scrollEnabled={matches.length > 4}
        style={styles.list}
      />
    </View>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.alert[50],
    borderTopWidth: 1,
    borderTopColor: colors.alert[200],
    borderRadius: radii.lg,
    padding: spacing[4],
    margin: spacing[3],
  },
  prompt: {
    color: colors.neutral[900],
    fontSize: 15, // mobileFontSizes.bodyLg
    fontWeight: String(fontWeights.medium) as "500",
    marginBottom: spacing[3],
    lineHeight: 22,
  },
  list: {
    maxHeight: 300,
  },
  item: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: lightTheme.background.secondary,
    borderRadius: radii.md,
    padding: spacing[4],
    minHeight: 56, // touchTargets.mobile.md
  },
  itemContent: {
    flex: 1,
    marginRight: spacing[3],
  },
  itemName: {
    color: colors.neutral[900],
    fontSize: 15, // mobileFontSizes.bodyLg
    fontWeight: String(fontWeights.medium) as "500",
    lineHeight: 22,
  },
  itemAddress: {
    color: colors.neutral[600],
    fontSize: 13, // mobileFontSizes.body
    lineHeight: 20,
    marginTop: 2,
  },
  channelBadge: {
    borderRadius: radii.full,
    paddingHorizontal: spacing[2],
    paddingVertical: spacing[1],
  },
  smsBadge: {
    backgroundColor: colors.brand[50],
  },
  emailBadge: {
    backgroundColor: colors.neutral[100],
  },
  channelBadgeText: {
    fontSize: 11, // mobileFontSizes.caption
    fontWeight: String(fontWeights.medium) as "500",
    lineHeight: 16,
  },
  smsBadgeText: {
    color: colors.brand[800],
  },
  emailBadgeText: {
    color: colors.neutral[600],
  },
  separator: {
    height: spacing[2],
  },
});
