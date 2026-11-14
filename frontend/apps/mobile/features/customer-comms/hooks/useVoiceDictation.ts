/**
 * useVoiceDictation — Single-utterance voice transcription for reply composer
 *
 * Location: apps/mobile/features/customer-comms/hooks/useVoiceDictation.ts
 *
 * RULE 3: Voice-to-text in composer is NOT a full voice session.
 * This hook captures a SINGLE utterance and places the transcript into
 * the text field. It manages a short-lived voice session (sessionId set
 * while recording, null when idle) to use useVoiceStream's existing
 * WebSocket infrastructure.
 *
 * State machine per design doc Section D.4, F.10:
 *   idle → recording → transcribing → transcribed | error
 *
 * Design doc Decision 3, Section D.4, F.10, E.7
 */

import { useState, useCallback, useEffect, useRef } from "react";
import { useVoiceStream } from "@pilot/ui";
import type { VoiceDictationState, UseVoiceDictationReturn } from "@pilot/ui";
import type { VoiceStreamEvent } from "@pilot/ui";

function generateDictationSessionId(): string {
  return `dictation-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function useVoiceDictation(): UseVoiceDictationReturn {
  const [state, setState] = useState<VoiceDictationState>({ phase: "idle" });
  // A non-null sessionId activates the useVoiceStream WebSocket connection
  const [sessionId, setSessionId] = useState<string | null>(null);
  const hasTranscribedRef = useRef(false);

  // Connect to voice stream only when recording (sessionId non-null)
  const { events, clearEvents, isConnected } = useVoiceStream(sessionId);

  // Watch for transcript events
  useEffect(() => {
    if (!sessionId || hasTranscribedRef.current) return;

    for (const event of events) {
      if (
        event.type === "transcript_final" &&
        typeof event.payload.text === "string" &&
        event.payload.text.trim().length > 0
      ) {
        hasTranscribedRef.current = true;
        setState({ phase: "transcribed", transcript: event.payload.text });
        // Close the session by clearing sessionId
        setSessionId(null);
        clearEvents();
        return;
      }

      if (event.type === "error") {
        hasTranscribedRef.current = true;
        setState({
          phase: "error",
          error: event.payload.error_message ?? "Transcription failed",
        });
        setSessionId(null);
        clearEvents();
        return;
      }

      if (event.type === "transcript_partial") {
        // Transition to transcribing phase when partial transcript arrives
        setState((prev) =>
          prev.phase === "recording" ? { phase: "transcribing" } : prev,
        );
      }
    }
  }, [events, sessionId, clearEvents]);

  const startDictating = useCallback(() => {
    hasTranscribedRef.current = false;
    clearEvents();
    setState({ phase: "recording" });
    setSessionId(generateDictationSessionId());
  }, [clearEvents]);

  const stopDictating = useCallback(() => {
    if (state.phase === "recording") {
      setState({ phase: "transcribing" });
      // Keep sessionId alive — wait for transcript_final event
    }
  }, [state.phase]);

  const reset = useCallback(() => {
    hasTranscribedRef.current = false;
    setSessionId(null);
    clearEvents();
    setState({ phase: "idle" });
  }, [clearEvents]);

  return {
    state,
    startDictating,
    stopDictating,
    reset,
  };
}
