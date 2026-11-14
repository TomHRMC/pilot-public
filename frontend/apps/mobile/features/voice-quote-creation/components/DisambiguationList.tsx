/**
 * DisambiguationList — customer/entity disambiguation UI
 *
 * Location: apps/mobile/features/voice-quote-creation/components/DisambiguationList.tsx
 *
 * Renders when the voice AI finds multiple matches for an entity
 * (e.g., multiple customers named "Tom Johnson"). User selects one to proceed.
 */

import React from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import { colors, radii, spacing } from "../../../../../packages/ui/src/tokens";
import type { DisambiguationOption } from "../types-stub";

interface DisambiguationListProps {
  options: DisambiguationOption[];
  onSelect: (option: DisambiguationOption) => void;
  testID?: string;
}

export function DisambiguationList({
  options,
  onSelect,
  testID = "disambiguation-list",
}: DisambiguationListProps) {
  if (options.length === 0) {
    return (
      <View style={styles.emptyContainer} testID={`${testID}-empty`}>
        <Text style={styles.emptyText}>No matching customer found</Text>
      </View>
    );
  }

  return (
    <View style={styles.container} testID={testID} accessibilityRole="list">
      <Text style={styles.heading}>Which one did you mean?</Text>
      {options.map((option) => (
        <Pressable
          key={option.id}
          style={styles.option}
          onPress={() => onSelect(option)}
          accessibilityRole="button"
          accessibilityLabel={
            option.sublabel
              ? `${option.label}, ${option.sublabel}`
              : option.label
          }
          testID={`disambiguation-option-${option.id}`}
        >
          <Text style={styles.optionLabel}>{option.label}</Text>
          {option.sublabel && (
            <Text style={styles.optionSublabel}>{option.sublabel}</Text>
          )}
        </Pressable>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.neutral[50],
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.neutral[200],
    padding: spacing[3],
    marginHorizontal: spacing[4],
    marginVertical: spacing[2],
  },
  emptyContainer: {
    padding: spacing[4],
    alignItems: "center",
  },
  emptyText: {
    color: colors.fault[600],
    fontSize: 14,
  },
  heading: {
    fontSize: 13,
    color: colors.neutral[600],
    marginBottom: spacing[3],
  },
  option: {
    paddingVertical: spacing[3],
    paddingHorizontal: spacing[3],
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.neutral[200],
    marginBottom: spacing[2],
    minHeight: 44,
    justifyContent: "center",
  },
  optionLabel: {
    fontSize: 15,
    color: colors.neutral[900],
  },
  optionSublabel: {
    fontSize: 11,
    color: colors.neutral[400],
    marginTop: spacing[1],
  },
});
