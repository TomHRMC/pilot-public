/**
 * useVoiceStream — Web implementation (MediaRecorder + Web Audio API)
 *
 * Location: packages/ui/src/voice/web/useVoiceStream.ts
 *
 * Web platform implementation. Consumed by FE-B6 (comms), FE-B8 (calendar),
 * FE-B16 (help). Public API is identical to the mobile implementation.
 *
 * Uses MediaRecorder with 250ms timeslice for streaming chunks.
 * NEVER buffers the full recording before sending.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { UseVoiceStreamReturn, VoiceStreamEvent } from "../types";

/* eslint-disable turbo/no-undeclared-env-vars */
const WS_BASE_URL =
  typeof process !== "undefined" && process.env?.NEXT_PUBLIC_WS_URL
    ? process.env.NEXT_PUBLIC_WS_URL
    : "ws://localhost:8000";
/* eslint-enable turbo/no-undeclared-env-vars */

const WS_ENDPOINT = `${WS_BASE_URL}/api/v1/voice/stream`;

/** Interval (ms) at which MediaRecorder delivers audio chunks */
const CHUNK_INTERVAL_MS = 250;

export function useVoiceStream(
  sessionId: string | null,
  authToken?: string,
): UseVoiceStreamReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [events, setEvents] = useState<VoiceStreamEvent[]>([]);
  const [transcriptBuffer, setTranscriptBuffer] = useState("");
  const [isConnected, setIsConnected] = useState(false);

  const clearEvents = useCallback(() => {
    setEvents([]);
    setTranscriptBuffer("");
  }, []);

  const sendAudioChunk = useCallback((chunkBase64: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({ type: "audio_chunk", payload: { data: chunkBase64 } }),
      );
    }
  }, []);

  const startMediaRecorder = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = async (event) => {
        if (event.data.size === 0) return;
        // Convert blob to base64 and send as chunk
        const arrayBuffer = await event.data.arrayBuffer();
        const bytes = new Uint8Array(arrayBuffer);
        let binary = "";
        bytes.forEach((b) => {
          binary += String.fromCharCode(b);
        });
        const base64 = btoa(binary);
        sendAudioChunk(base64);
      };

      // timeslice = 250ms → ondataavailable fires every 250ms (streaming, never buffered)
      recorder.start(CHUNK_INTERVAL_MS);
    } catch {
      // Microphone permission denied or not available
    }
  }, [sendAudioChunk]);

  const stopMediaRecorder = useCallback(() => {
    if (mediaRecorderRef.current?.state !== "inactive") {
      mediaRecorderRef.current?.stop();
    }
    mediaRecorderRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }, []);

  const connect = useCallback(() => {
    if (!sessionId) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const url = `${WS_ENDPOINT}?session_id=${sessionId}${authToken ? `&token=${authToken}` : ""}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      startMediaRecorder();
    };

    ws.onmessage = (event) => {
      try {
        const parsed: VoiceStreamEvent = JSON.parse(event.data as string);
        setEvents((prev) => [...prev, parsed]);

        if (parsed.type === "transcript_partial" && parsed.payload.text) {
          setTranscriptBuffer(parsed.payload.text);
        } else if (parsed.type === "transcript_final") {
          setTranscriptBuffer("");
        }
      } catch {
        // Malformed server frame — ignore
      }
    };

    ws.onerror = () => setIsConnected(false);
    ws.onclose = () => {
      setIsConnected(false);
      stopMediaRecorder();
    };
  }, [sessionId, authToken, startMediaRecorder, stopMediaRecorder]);

  const disconnect = useCallback(() => {
    stopMediaRecorder();
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, [stopMediaRecorder]);

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    events,
    transcriptBuffer,
    sendAudioChunk,
    connect,
    disconnect,
    isConnected,
    clearEvents,
  };
}
