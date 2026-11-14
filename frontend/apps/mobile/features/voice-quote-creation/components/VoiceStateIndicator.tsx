/**
 * VoiceStateIndicator — 6-state visual indicator
 *
 * Location: apps/mobile/features/voice-quote-creation/components/VoiceStateIndicator.tsx
 *
 * Visual representation of the current voice state machine state.
 * Colors come EXCLUSIVELY from voiceStateTokens — no hardcoded values.
 *
 * States: idle | listening | processing | speaking | waiting-confirm | error
 */

import React from "react";
import { View, ActivityIndicator, StyleSheet, Animated } from "react-native";
import {
  colors,
  radii,
  touchTargets,
} from "../../../../../packages/ui/src/tokens";
import { voiceStateTokens } from "../../../../../packages/ui/src/voice/types";
import type { VoiceState } from "../../../../../packages/ui/src/voice/types";

/** Maps Gluestack token strings to actual color values from tokens.ts */
function resolveToken(token: string): string {
  const map: Record<string, string> = {
    "$alert-200": colors.alert[200],
    "$alert-400": colors.alert[400],
    "$alert-500": colors.alert[400], // alert.500 → use 400 (closest ramp)
    "$alert-900": colors.alert[900],
    "$brand-600": colors.brand[600],
    "$fault-600": colors.fault[600],
    "$margin-500": colors.margin[400], // margin.500 → use 400 (closest ramp)
    "$neutral-900": colors.neutral[900],
    $white: "#FFFFFF",
  };
  return map[token] ?? colors.neutral[400];
}

interface VoiceStateIndicatorProps {
  state: VoiceState;
  fieldMode?: boolean;
  testID?: string;
}

export function VoiceStateIndicator({
  state,
  fieldMode = false,
  testID = "voice-state-indicator",
}: VoiceStateIndicatorProps) {
  const tokens = voiceStateTokens[state];
  const bg = resolveToken(tokens.bgToken);
  const iconColor = resolveToken(tokens.iconToken);

  // Field mode uses larger hit target
  const size = fieldMode ? touchTargets.mobile.lg : touchTargets.mobile.md; // 64 or 56

  return (
    <View
      testID={testID}
      accessible
      accessibilityRole="image"
      accessibilityLabel={tokens.accessibilityLabel}
      accessibilityLiveRegion="polite"
      style={[
        styles.container,
        {
          width: size,
          height: size,
          borderRadius: size / 2,
          backgroundColor: bg,
        },
        fieldMode && styles.fieldMode,
      ]}
    >
      {/* Pulse ring for listening state */}
      {state === "listening" && (
        <View
          testID="listening-waveform-anim"
          style={[
            styles.pulseRing,
            { borderColor: resolveToken("$alert-400") },
          ]}
        />
      )}

      {/* Spinner for processing state */}
      {state === "processing" && (
        <ActivityIndicator
          size="small"
          color={iconColor}
          accessibilityLabel="Processing indicator"
        />
      )}

      {/* Waveform bars for speaking state */}
      {state === "speaking" && (
        <View style={styles.waveform}>
          {[0, 1, 2].map((i) => (
            <View
              key={i}
              style={[styles.waveBar, { backgroundColor: iconColor }]}
            />
          ))}
        </View>
      )}

      {/* Mic icon placeholder for idle/error/waiting states */}
      {(state === "idle" ||
        state === "error" ||
        state === "waiting-confirm") && (
        <View
          style={[styles.iconDot, { backgroundColor: iconColor }]}
          testID={
            state === "error"
              ? "error-icon"
              : state === "waiting-confirm"
                ? "confirm-icon"
                : "mic-icon"
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: "center",
    justifyContent: "center",
    overflow: "visible",
  },
  fieldMode: {
    // Field mode: higher contrast handled via state token (idle uses alert[400] instead of alert[200])
  },
  pulseRing: {
    position: "absolute",
    width: "130%",
    height: "130%",
    borderRadius: 9999,
    borderWidth: 2,
    opacity: 0.6,
  },
  waveform: {
    flexDirection: "row",
    alignItems: "center",
    gap: 3,
  },
  waveBar: {
    width: 3,
    height: 16,
    borderRadius: radii.sm,
  },
  iconDot: {
    width: 12,
    height: 12,
    borderRadius: radii.full,
  },
});
