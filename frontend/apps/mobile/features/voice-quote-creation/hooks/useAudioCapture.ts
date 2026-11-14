/**
 * useAudioCapture — expo-av microphone wrapper
 *
 * Location: apps/mobile/features/voice-quote-creation/hooks/useAudioCapture.ts
 *
 * Manages Audio.Recording lifecycle: permission, start, stop.
 * Cleanup: stops recording on unmount if still active.
 *
 * Uses static import for expo-av so jest.mock('expo-av') works in tests.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Audio } from "expo-av";

interface UseAudioCaptureReturn {
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<string | null>;
  isRecording: boolean;
  permissionGranted: boolean;
}

export function useAudioCapture(): UseAudioCaptureReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [permissionGranted, setPermissionGranted] = useState(false);
  const recordingRef = useRef<InstanceType<typeof Audio.Recording> | null>(
    null,
  );

  const startRecording = useCallback(async () => {
    try {
      const { status } = await Audio.requestPermissionsAsync();

      if (status !== "granted") {
        setPermissionGranted(false);
        return;
      }

      setPermissionGranted(true);
      await Audio.setAudioModeAsync({ allowsRecordingIOS: true });

      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY,
      );
      recordingRef.current = recording;
      setIsRecording(true);
    } catch {
      setIsRecording(false);
    }
  }, []);

  const stopRecording = useCallback(async (): Promise<string | null> => {
    if (!recordingRef.current) return null;
    try {
      await recordingRef.current.stopAndUnloadAsync();
      const uri = recordingRef.current.getURI() ?? null;
      recordingRef.current = null;
      setIsRecording(false);
      return uri;
    } catch {
      recordingRef.current = null;
      setIsRecording(false);
      return null;
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (recordingRef.current) {
        recordingRef.current.stopAndUnloadAsync().catch(() => {});
        recordingRef.current = null;
      }
    };
  }, []);

  return { startRecording, stopRecording, isRecording, permissionGranted };
}
