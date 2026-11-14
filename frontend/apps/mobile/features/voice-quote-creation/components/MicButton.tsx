/**
 * MicButton — primary voice trigger button
 *
 * Location: apps/mobile/features/voice-quote-creation/components/MicButton.tsx
 *
 * The main interactive element for starting/stopping voice input.
 * Composes VoiceStateIndicator to show current state visually.
 * Minimum 44×44pt touch target (56 default, 64 in field mode).
 */

import React from "react";
import { Pressable, StyleSheet } from "react-native";
import { touchTargets } from "../../../../../packages/ui/src/tokens";
import { voiceStateTokens } from "../../../../../packages/ui/src/voice/types";
import type { VoiceState } from "../../../../../packages/ui/src/voice/types";
import { VoiceStateIndicator } from "./VoiceStateIndicator";

interface MicButtonProps {
  voiceState: VoiceState;
  onPress: () => void;
  fieldMode?: boolean;
  testID?: string;
}

export function MicButton({
  voiceState,
  onPress,
  fieldMode = false,
  testID = "voice-trigger-btn",
}: MicButtonProps) {
  const { accessibilityLabel } = voiceStateTokens[voiceState];
  const size = fieldMode ? touchTargets.mobile.lg : touchTargets.mobile.md;

  return (
    <Pressable
      onPress={onPress}
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      accessibilityHint={
        voiceState === "idle"
          ? "Double tap to start voice input"
          : "Double tap to stop voice input"
      }
      style={[
        styles.pressable,
        { width: size, height: size, borderRadius: size / 2 },
      ]}
    >
      <VoiceStateIndicator
        state={voiceState}
        fieldMode={fieldMode}
        testID={`${testID}-indicator`}
      />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  pressable: {
    alignItems: "center",
    justifyContent: "center",
    overflow: "visible",
  },
});
