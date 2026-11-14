/**
 * FieldModeToggle — high-contrast field mode switcher
 *
 * Location: apps/mobile/features/voice-quote-creation/components/FieldModeToggle.tsx
 *
 * Always visible in the session header regardless of current field mode state.
 * Persisted to AsyncStorage via the Zustand store's setFieldMode action.
 */

import React from "react";
import { Pressable, Text, StyleSheet } from "react-native";
import { colors, radii, spacing } from "../../../../../packages/ui/src/tokens";

interface FieldModeToggleProps {
  isEnabled: boolean;
  onToggle: () => void;
  testID?: string;
}

export function FieldModeToggle({
  isEnabled,
  onToggle,
  testID = "field-mode-toggle",
}: FieldModeToggleProps) {
  return (
    <Pressable
      onPress={onToggle}
      testID={testID}
      accessibilityRole="switch"
      accessibilityLabel="Field mode"
      accessibilityHint={
        isEnabled
          ? "Field mode is on. Tap to disable"
          : "Field mode is off. Tap to enable high-contrast large-button mode"
      }
      accessibilityState={{ checked: isEnabled }}
      style={[styles.chip, isEnabled && styles.chipActive]}
    >
      <Text style={[styles.label, isEnabled && styles.labelActive]}>
        {isEnabled ? "Field ✓" : "Field"}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  chip: {
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[1],
    borderRadius: radii.full,
    borderWidth: 1,
    borderColor: colors.neutral[200],
    backgroundColor: colors.neutral[100],
  },
  chipActive: {
    backgroundColor: colors.alert[400],
    borderColor: colors.alert[400],
  },
  label: {
    fontSize: 12,
    color: colors.neutral[600],
  },
  labelActive: {
    color: colors.neutral[900],
  },
});
