/**
 * useVoiceConfirmation — shared hook for confirm-as-turn pattern
 *
 * Location: packages/ui/src/voice-confirm-turn/useVoiceConfirmation.ts
 *
 * Manages the lifecycle of a pending voice confirmation.
 * Consumed by: FE-B3 (quote), FE-B6 (comms), FE-B8 (calendar),
 *              FE-B10 (SMS reply), FE-B16 (help escalation).
 */

import { useCallback, useState } from "react";
import type { PendingConfirmation, UseVoiceConfirmationReturn } from "./types";

export function useVoiceConfirmation(): UseVoiceConfirmationReturn {
  const [pendingConfirmation, setPendingConfirmation] =
    useState<PendingConfirmation | null>(null);
  const [isConfirming, setIsConfirming] = useState(false);

  const confirm = useCallback(
    async (intentId: string, executeAction: () => Promise<void>) => {
      if (!pendingConfirmation || pendingConfirmation.intentId !== intentId) {
        return;
      }
      setIsConfirming(true);
      try {
        await executeAction();
      } finally {
        setIsConfirming(false);
        setPendingConfirmation(null);
      }
    },
    [pendingConfirmation],
  );

  const cancel = useCallback(() => {
    setPendingConfirmation(null);
    setIsConfirming(false);
  }, []);

  return {
    pendingConfirmation,
    setPendingConfirmation,
    confirm,
    cancel,
    isConfirming,
  };
}
