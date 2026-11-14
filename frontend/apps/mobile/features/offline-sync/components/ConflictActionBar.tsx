/**
 * ConflictActionBar — Bottom action bar for conflict resolution
 *
 * Location: apps/mobile/features/offline-sync/components/ConflictActionBar.tsx
 *
 * Three actions:
 *   "Use my version"    → calls onUseLocal; sends use_local resolution to API
 *   "Use server version" → calls onUseServer; sends use_server resolution
 *   "Send to owner"     → calls onEscalate; creates owner escalation
 *
 * Each button has explicit accessibilityLabel.
 * Per batch-fe-b7-design.md Section A.3.3.
 */

import React from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import {
  colors,
  mobileFontSizes,
  fontWeights,
  spacing,
  radii,
  touchTargets,
} from "@pilot/ui/tokens";

interface ConflictActionBarProps {
  onUseLocal: () => void;
  onUseServer: () => void;
  onEscalate: () => void;
  isLoading?: boolean;
  testID?: string;
}

export function ConflictActionBar({
  onUseLocal,
  onUseServer,
  onEscalate,
  isLoading = false,
  testID,
}: ConflictActionBarProps): React.ReactElement {
  return (
    <View style={styles.container} testID={testID ?? "conflict-action-bar"}>
      {/* Primary: Use my version */}
      <Pressable
        onPress={onUseLocal}
        disabled={isLoading}
        style={[
          styles.button,
          styles.primaryButton,
          isLoading && styles.buttonDisabled,
        ]}
        accessibilityRole="button"
        accessibilityLabel="Use my version — keep your offline changes"
        testID="use-local-button"
      >
        <Text style={styles.primaryButtonText}>Use my version</Text>
      </Pressable>

      {/* Secondary: Use server version */}
      <Pressable
        onPress={onUseServer}
        disabled={isLoading}
        style={[
          styles.button,
          styles.secondaryButton,
          isLoading && styles.buttonDisabled,
        ]}
        accessibilityRole="button"
        accessibilityLabel="Use server version — discard your offline changes"
        testID="use-server-button"
      >
        <Text style={styles.secondaryButtonText}>Use server version</Text>
      </Pressable>

      {/* Tertiary: Send to owner */}
      <Pressable
        onPress={onEscalate}
        disabled={isLoading}
        style={[
          styles.button,
          styles.tertiaryButton,
          isLoading && styles.buttonDisabled,
        ]}
        accessibilityRole="button"
        accessibilityLabel="Send to owner — let owner decide which version to keep"
        testID="escalate-button"
      >
        <Text style={styles.tertiaryButtonText}>Send to owner</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: spacing[4],
    gap: spacing[3],
    backgroundColor: colors.neutral[900],
    borderTopWidth: 1,
    borderTopColor: colors.neutral[600],
  },
  button: {
    minHeight: touchTargets.mobile.md,
    borderRadius: radii.md,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: spacing[4],
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  primaryButton: {
    backgroundColor: colors.brand[600],
  },
  primaryButtonText: {
    fontSize: mobileFontSizes.bodyLg,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 22,
  },
  secondaryButton: {
    backgroundColor: "transparent",
    borderWidth: 1,
    borderColor: colors.neutral[600],
  },
  secondaryButtonText: {
    fontSize: mobileFontSizes.bodyLg,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[200],
    lineHeight: 22,
  },
  tertiaryButton: {
    backgroundColor: "transparent",
  },
  tertiaryButtonText: {
    fontSize: mobileFontSizes.body,
    fontWeight: String(fontWeights.regular) as "400",
    color: colors.neutral[400],
    lineHeight: 20,
  },
});
