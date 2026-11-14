/**
 * Active voice session screen
 *
 * Location: apps/mobile/app/(tabs)/(home)/voice/[sessionId].tsx
 *
 * Wraps VoiceSessionShell — the full-screen voice chat UI.
 * Reads `sessionId` from Expo Router params.
 */

import React from "react";
import { useLocalSearchParams } from "expo-router";
import { useVoiceSessionStore } from "../../../../features/voice-quote-creation/store";
import { VoiceSessionShell } from "../../../../features/voice-quote-creation/components/VoiceSessionShell";

export default function VoiceSessionScreen() {
  const { sessionId } = useLocalSearchParams<{ sessionId: string }>();
  const { fieldMode } = useVoiceSessionStore();

  if (!sessionId) {
    return null;
  }

  return <VoiceSessionShell sessionId={sessionId} fieldMode={fieldMode} />;
}
