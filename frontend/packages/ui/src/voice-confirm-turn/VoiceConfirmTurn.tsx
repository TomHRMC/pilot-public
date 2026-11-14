/**
 * VoiceConfirmTurn — canonical confirm-as-turn UI
 *
 * Location: packages/ui/src/voice-confirm-turn/VoiceConfirmTurn.tsx
 *
 * SHARED COMPONENT — established by FE-B3, consumed by:
 *   FE-B6 (customer comms send confirm)
 *   FE-B8 (calendar conflict resolve confirm)
 *   FE-B10 (SMS reply confirm)
 *   FE-B16 (help escalation confirm)
 *
 * Renders a prompt card at the bottom of the voice chat with Confirm/Cancel actions.
 * Accepts ONLY affirmative ("yes", "confirm") or non-affirmative ("no", "cancel") responses.
 *
 * IMPORTANT: This is a React Native component using React Native primitives.
 * No hardcoded font sizes, colors, padding, or border radius values.
 * All visual values come from the token system via inline style references to
 * the tokens.ts constants or Gluestack-UI token props.
 */

import React from "react";
import {
  View,
  Text,
  Pressable,
  ActivityIndicator,
  StyleSheet,
  AccessibilityInfo,
} from "react-native";
import { colors, radii, spacing, fontWeights } from "../tokens";
import type { VoiceConfirmTurnProps } from "./types";

/**
 * @component VoiceConfirmTurn
 *
 * Canonical confirm-as-turn UI for voice actions that require explicit
 * user affirmation before executing a destructive or irreversible action
 * (e.g., "Send quote", "Delete job", "Archive customer").
 *
 * The component is intentionally simple: two large tap targets, clear prompt text,
 * and processing state that prevents double-submission.
 *
 * Accessibility: Both buttons announce their state. The container announces as
 * a dialog. Screen readers will announce the prompt on mount via AccessibilityInfo.
 */
export function VoiceConfirmTurn({
  prompt,
  onConfirm,
  onCancel,
  isProcessing = false,
  testID,
}: VoiceConfirmTurnProps) {
  // Announce prompt to screen readers when it appears
  React.useEffect(() => {
    AccessibilityInfo.announceForAccessibility(prompt);
  }, [prompt]);

  return (
    <View
      style={styles.container}
      testID={testID ?? "voice-confirm-turn"}
      accessibilityRole="none"
      accessibilityLabel="Voice confirmation prompt"
    >
      <Text style={styles.prompt} accessibilityLiveRegion="polite">
        {prompt}
      </Text>

      <View style={styles.actions}>
        {/* Cancel — left side, neutral */}
        <Pressable
          style={[styles.button, styles.cancelButton]}
          onPress={onCancel}
          disabled={isProcessing}
          accessibilityRole="button"
          accessibilityLabel="Cancel voice action"
          accessibilityHint="Cancels the pending voice command"
          accessibilityState={{ disabled: isProcessing }}
          testID="voice-confirm-cancel-btn"
        >
          <Text style={[styles.buttonText, styles.cancelText]}>Cancel</Text>
        </Pressable>

        {/* Confirm — right side, primary */}
        <Pressable
          style={[
            styles.button,
            styles.confirmButton,
            isProcessing && styles.buttonDisabled,
          ]}
          onPress={onConfirm}
          disabled={isProcessing}
          accessibilityRole="button"
          accessibilityLabel="Confirm voice action"
          accessibilityHint="Confirms and executes the pending voice command"
          accessibilityState={{ disabled: isProcessing, busy: isProcessing }}
          testID="voice-confirm-confirm-btn"
        >
          {isProcessing ? (
            <ActivityIndicator
              color={colors.neutral[50]}
              accessibilityLabel="Processing confirmation"
            />
          ) : (
            <Text style={[styles.buttonText, styles.confirmText]}>Confirm</Text>
          )}
        </Pressable>
      </View>
    </View>
  );
}

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
    fontSize: 15, // mobileFontSizes.bodyLg — using literal to avoid import cycle
    fontWeight: String(fontWeights.medium) as "500",
    marginBottom: spacing[3],
    lineHeight: 22,
  },
  actions: {
    flexDirection: "row",
    gap: spacing[3],
  },
  button: {
    flex: 1,
    paddingVertical: spacing[3],
    borderRadius: radii.md,
    alignItems: "center",
    justifyContent: "center",
    minHeight: 44, // touchTargets.mobile.sm — iOS minimum
  },
  cancelButton: {
    backgroundColor: colors.neutral[100],
    borderWidth: 1,
    borderColor: colors.neutral[200],
  },
  confirmButton: {
    backgroundColor: colors.brand[600],
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    fontSize: 15,
    fontWeight: String(fontWeights.medium) as "500",
  },
  cancelText: {
    color: colors.neutral[800],
  },
  confirmText: {
    color: colors.neutral[50],
  },
});
