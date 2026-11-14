/**
 * CustomerListItem — Row card for a customer in the customers list
 *
 * Location: apps/mobile/features/customers/components/CustomerListItem.tsx
 *
 * Design doc Section F.4 (MOB-B3)
 *
 * Displays:
 *   - display_name (primary text)
 *   - type badge: "residential" → neutral, "commercial" → brand
 *   - email (if not null)
 *   - right chevron
 *   - minimum 44pt touch target
 */

import React from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import { colors, radii, spacing, fontWeights } from "@pilot/ui/tokens";
import type { CustomerListItem as CustomerListItemData } from "../hooks/useCustomers";

interface CustomerListItemProps {
  customer: CustomerListItemData;
  onPress: (customerId: string) => void;
  testID?: string;
}

// Hardcoded type badge map — no enum endpoint. See design doc §A.2.2.
const TYPE_BADGE: Record<string, { label: string; isBrand: boolean }> = {
  residential: { label: "Residential", isBrand: false },
  commercial: { label: "Commercial", isBrand: true },
};

function getTypeBadge(type: string): { label: string; isBrand: boolean } {
  return TYPE_BADGE[type] ?? { label: type, isBrand: false };
}

export function CustomerListItem({
  customer,
  onPress,
  testID,
}: CustomerListItemProps) {
  const badge = getTypeBadge(customer.type);

  return (
    <Pressable
      style={styles.container}
      onPress={() => onPress(customer.id)}
      accessibilityRole="button"
      accessibilityLabel={`Customer ${customer.display_name}`}
      testID={testID ?? `customer-row-${customer.id}`}
    >
      <View style={styles.content}>
        <View style={styles.nameRow}>
          <Text style={styles.displayName} numberOfLines={1}>
            {customer.display_name}
          </Text>
          <View
            style={[
              styles.typeBadge,
              badge.isBrand ? styles.brandBadge : styles.neutralBadge,
            ]}
          >
            <Text
              style={[
                styles.typeBadgeText,
                badge.isBrand ? styles.brandBadgeText : styles.neutralBadgeText,
              ]}
            >
              {badge.label}
            </Text>
          </View>
        </View>
        {customer.email != null && (
          <Text style={styles.email} numberOfLines={1}>
            {customer.email}
          </Text>
        )}
      </View>
      <Text style={styles.chevron} aria-hidden>
        {">"}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing[6],
    paddingVertical: spacing[3],
    backgroundColor: "#FFFFFF",
    minHeight: 44,
    gap: spacing[3],
  },
  content: {
    flex: 1,
    gap: spacing[1],
  },
  nameRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[2],
    flexWrap: "wrap",
  },
  displayName: {
    flex: 1,
    color: colors.neutral[900],
    fontSize: 15,
    fontWeight: String(fontWeights.medium) as "500",
    lineHeight: 22,
  },
  email: {
    color: colors.neutral[400],
    fontSize: 13,
    lineHeight: 18,
  },
  typeBadge: {
    borderRadius: radii.full,
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
  },
  brandBadge: {
    backgroundColor: colors.brand[50],
  },
  neutralBadge: {
    backgroundColor: colors.neutral[100],
  },
  typeBadgeText: {
    fontSize: 11,
    fontWeight: String(fontWeights.medium) as "500",
  },
  brandBadgeText: {
    color: colors.brand[800],
  },
  neutralBadgeText: {
    color: colors.neutral[600],
  },
  chevron: {
    color: colors.neutral[400],
    fontSize: 16,
    fontWeight: String(fontWeights.medium) as "500",
  },
});
