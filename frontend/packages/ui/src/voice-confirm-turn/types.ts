/**
 * VoiceConfirmTurn — shared types
 *
 * Location: packages/ui/src/voice-confirm-turn/types.ts
 */

export interface VoiceConfirmTurnProps {
  /**
   * The confirmation prompt text to display (AI's summary of the pending action).
   * Example: "Send the Johnson panel quote to tom@johnson.example.com?"
   */
  prompt: string;
  /**
   * Called when user provides affirmative response (voice "yes" or tap).
   */
  onConfirm: () => void;
  /**
   * Called when user provides non-affirmative response (voice "no", "cancel", or dismiss tap).
   */
  onCancel: () => void;
  /**
   * Whether the confirm action is in-flight (mutation pending).
   * Disables both buttons while true.
   */
  isProcessing?: boolean;
  /** For Maestro/Detox e2e targeting */
  testID?: string;
}

export interface PendingConfirmation {
  intentId: string;
  prompt: string;
  expiresAt: string;
}

export interface UseVoiceConfirmationReturn {
  pendingConfirmation: PendingConfirmation | null;
  setPendingConfirmation: (confirmation: PendingConfirmation | null) => void;
  /** Execute the confirmed action — clears pending state */
  confirm: (
    intentId: string,
    executeAction: () => Promise<void>,
  ) => Promise<void>;
  /** Cancel the pending action — clears pending state */
  cancel: () => void;
  /** Whether confirmation is currently processing */
  isConfirming: boolean;
}
