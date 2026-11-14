/**
 * Voice module — shared types and token mapping
 *
 * Location: packages/ui/src/voice/types.ts
 *
 * Authoritative type definitions for the 6-state voice machine.
 * Consumed by ALL voice surfaces: FE-B3 (quote), FE-B6 (comms),
 * FE-B8 (calendar), FE-B10 (SMS), FE-B16 (help).
 *
 * Token values reference Gluestack-UI semantic tokens.
 * NEVER use raw hex values here. Use $-prefixed token names.
 */

// ---------------------------------------------------------------------------
// State machine
// ---------------------------------------------------------------------------

export type VoiceState =
  | "idle"
  | "listening"
  | "processing"
  | "speaking"
  | "waiting-confirm"
  | "error";

// ---------------------------------------------------------------------------
// WebSocket event types
// ---------------------------------------------------------------------------

export type VoiceStreamEventType =
  | "transcript_partial"
  | "transcript_final"
  | "intent_detected"
  | "response_streaming"
  | "response_final"
  | "action_committed"
  | "snapshot_frozen"
  | "error";

export interface VoiceStreamEvent {
  type: VoiceStreamEventType;
  payload: {
    text?: string;
    intent_type?: string;
    entities?: Record<string, unknown>;
    message_id?: string;
    structured_content?: {
      render_mode: "live" | "snapshot";
      content_type: string;
      entity_id?: string | null;
      snapshot_payload?: Record<string, unknown> | null;
    };
    quote_id?: string;
    snapshot_frozen?: boolean;
    error_code?: string;
    error_message?: string;
  };
}

// ---------------------------------------------------------------------------
// Hook return interface
// ---------------------------------------------------------------------------

export interface UseVoiceStreamReturn {
  /** All events received since connection opened */
  events: VoiceStreamEvent[];
  /** Latest partial transcript text (for entity highlighting) */
  transcriptBuffer: string;
  /** Send a base64-encoded audio chunk to the WebSocket */
  sendAudioChunk: (chunkBase64: string) => void;
  /** Open the WebSocket connection */
  connect: () => void;
  /** Close the WebSocket connection */
  disconnect: () => void;
  /** Whether the WebSocket is currently open */
  isConnected: boolean;
  /** Clear all accumulated events (e.g., on new session) */
  clearEvents: () => void;
}

// ---------------------------------------------------------------------------
// Voice state tokens
//
// Maps each of the 6 voice states to Gluestack-UI semantic token strings.
// These token strings are passed directly to Gluestack props (bg, color, etc.).
// RULE: Every value MUST start with "$" — never use raw hex values.
// ---------------------------------------------------------------------------

export const voiceStateTokens: Record<
  VoiceState,
  {
    /** Gluestack bg token for the indicator button */
    bgToken: string;
    /** Gluestack color token for the icon inside the indicator */
    iconToken: string;
    /** Short human-readable label */
    label: string;
    /** Full accessibility label announced by screen readers */
    accessibilityLabel: string;
  }
> = {
  idle: {
    bgToken: "$alert-200",
    iconToken: "$alert-900",
    label: "Tap to talk",
    accessibilityLabel: "Start voice input",
  },
  listening: {
    bgToken: "$alert-400",
    iconToken: "$white",
    label: "Listening...",
    accessibilityLabel: "Listening — tap to stop",
  },
  processing: {
    bgToken: "$brand-600",
    iconToken: "$white",
    label: "Processing...",
    accessibilityLabel: "Processing your voice command",
  },
  speaking: {
    bgToken: "$margin-500",
    iconToken: "$white",
    label: "Speaking...",
    accessibilityLabel: "AI is speaking",
  },
  "waiting-confirm": {
    bgToken: "$alert-500",
    iconToken: "$neutral-900",
    label: "Confirm?",
    accessibilityLabel: "Voice command waiting for confirmation",
  },
  error: {
    bgToken: "$fault-600",
    iconToken: "$white",
    label: "Try again",
    accessibilityLabel: "Voice error — tap to retry",
  },
};
