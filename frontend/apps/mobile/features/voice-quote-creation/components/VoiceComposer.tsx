/**
 * VoiceComposer — bottom input bar (mic + text fallback)
 *
 * Location: apps/mobile/features/voice-quote-creation/components/VoiceComposer.tsx
 */

import React, { useState } from "react";
import { View, TextInput, Pressable, Text, StyleSheet } from "react-native";
import { colors, radii, spacing } from "../../../../../packages/ui/src/tokens";
import type { VoiceState } from "../../../../../packages/ui/src/voice/types";
import { MicButton } from "./MicButton";

interface VoiceComposerProps {
  voiceState: VoiceState;
  onMicPress: () => void;
  onSubmitText: (text: string) => void;
  fieldMode?: boolean;
}

export function VoiceComposer({
  voiceState,
  onMicPress,
  onSubmitText,
  fieldMode = false,
}: VoiceComposerProps) {
  const [text, setText] = useState("");

  function handleSubmit() {
    if (text.trim()) {
      onSubmitText(text.trim());
      setText("");
    }
  }

  // Field mode: show only mic button, hide text input
  if (fieldMode) {
    return (
      <View style={[styles.container, styles.fieldModeContainer]}>
        <MicButton voiceState={voiceState} onPress={onMicPress} fieldMode />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <TextInput
        style={styles.input}
        value={text}
        onChangeText={setText}
        placeholder="Type or tap the mic..."
        placeholderTextColor={colors.neutral[400]}
        onSubmitEditing={handleSubmit}
        returnKeyType="send"
        accessibilityLabel="Text input for voice session"
        testID="voice-text-input"
      />
      {text.trim().length > 0 && (
        <Pressable
          style={styles.sendBtn}
          onPress={handleSubmit}
          accessibilityLabel="Send text message"
          testID="voice-send-btn"
        >
          <Text style={styles.sendText}>Send</Text>
        </Pressable>
      )}
      <MicButton voiceState={voiceState} onPress={onMicPress} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
    backgroundColor: colors.neutral[50],
    borderTopWidth: 1,
    borderTopColor: colors.neutral[200],
    gap: spacing[2],
  },
  fieldModeContainer: {
    justifyContent: "center",
    paddingVertical: spacing[5],
  },
  input: {
    flex: 1,
    backgroundColor: colors.neutral[100],
    borderRadius: radii.full,
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[2],
    color: colors.neutral[900],
    fontSize: 15,
    minHeight: 44,
  },
  sendBtn: {
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2],
    backgroundColor: colors.brand[600],
    borderRadius: radii.md,
    minHeight: 44,
    alignItems: "center",
    justifyContent: "center",
  },
  sendText: {
    color: colors.neutral[50],
    fontSize: 14,
  },
});
