/**
 * VoiceApprovalHandler — web voice approval intent composer
 *
 * Location: apps/web/src/features/voice-approval/VoiceApprovalHandler.tsx
 *
 * Listens for approve_quote, reject_quote, request_quote_edits intents
 * from the voice session event stream. Composes <VoiceConfirmTurn> before
 * calling the approval API.
 *
 * Per §G.8: mounted at QuoteDetailPage level. No surface-specific mic button.
 * Line-item edit intents result in a refusal message — voice cannot commit edits.
 */

"use client";

import React, { useCallback } from "react";
import { useVoiceConfirmation } from "@pilot/ui/voice-confirm-turn";
import {
  useQuoteApprove,
  useQuoteKickback,
  useQuoteReject,
} from "../quote-approval/hooks/useQuoteApprove";

type ApprovalIntent = "approve_quote" | "reject_quote" | "request_quote_edits";

interface VoiceApprovalHandlerProps {
  quoteId: string;
  quoteNumber: string;
  customerName: string;
  /**
   * The detected intent from the voice session. null when no intent is active.
   * Supplied by the parent voice session event handler.
   */
  detectedIntent: ApprovalIntent | null;
  onIntentHandled: () => void;
}

const APPROVAL_PROMPTS: Record<
  ApprovalIntent,
  (quoteNumber: string, customerName: string) => string
> = {
  approve_quote: (n, c) => `Approve quote #${n} for ${c}?`,
  reject_quote: (n, c) =>
    `Reject quote #${n} for ${c}? This action is permanent.`,
  request_quote_edits: (n, c) =>
    `Kick back quote #${n} for ${c} to the technician for revisions?`,
};

/** Intents that are approval-related (supported by voice) */
const SUPPORTED_INTENTS = new Set<ApprovalIntent>([
  "approve_quote",
  "reject_quote",
  "request_quote_edits",
]);

export function VoiceApprovalHandler({
  quoteId,
  quoteNumber,
  customerName,
  detectedIntent,
  onIntentHandled,
}: VoiceApprovalHandlerProps) {
  const {
    pendingConfirmation,
    setPendingConfirmation,
    confirm,
    cancel,
    isConfirming,
  } = useVoiceConfirmation();

  const approve = useQuoteApprove(quoteId);
  const kickback = useQuoteKickback(quoteId);
  const reject = useQuoteReject(quoteId);

  // When a new intent arrives, set up the confirm turn
  React.useEffect(() => {
    if (!detectedIntent) return;
    if (!SUPPORTED_INTENTS.has(detectedIntent)) return;

    const prompt = APPROVAL_PROMPTS[detectedIntent](quoteNumber, customerName);
    setPendingConfirmation({
      intentId: detectedIntent,
      prompt,
      expiresAt: new Date(Date.now() + 30_000).toISOString(),
    });
  }, [detectedIntent, quoteNumber, customerName, setPendingConfirmation]);

  const handleConfirm = useCallback(async () => {
    if (!pendingConfirmation) return;

    await confirm(pendingConfirmation.intentId, async () => {
      switch (pendingConfirmation.intentId as ApprovalIntent) {
        case "approve_quote":
          await approve.mutateAsync({ apply_pending_edits: false });
          break;
        case "reject_quote":
          await reject.mutateAsync({ reason: "Rejected via voice command" });
          break;
        case "request_quote_edits":
          await kickback.mutateAsync({
            overall_comment: "Revisions requested via voice",
          });
          break;
      }
    });

    onIntentHandled();
  }, [
    pendingConfirmation,
    confirm,
    approve,
    reject,
    kickback,
    onIntentHandled,
  ]);

  const handleCancel = useCallback(() => {
    cancel();
    onIntentHandled();
  }, [cancel, onIntentHandled]);

  if (!pendingConfirmation) return null;

  const isProcessing =
    isConfirming || approve.isPending || reject.isPending || kickback.isPending;

  return (
    <div
      className="fixed bottom-20 left-0 right-0 mx-4 z-50"
      role="alertdialog"
      aria-labelledby="voice-approval-prompt"
      aria-live="assertive"
    >
      <div className="bg-alert-50 border border-alert-400 rounded-lg p-4 shadow-xl">
        <p
          id="voice-approval-prompt"
          className="text-body font-medium text-neutral-900 mb-3"
        >
          {pendingConfirmation.prompt}
        </p>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={handleCancel}
            disabled={isProcessing}
            className="flex-1 py-2 text-body font-medium text-neutral-800 bg-neutral-100 border border-neutral-200 rounded-md hover:bg-neutral-200 disabled:opacity-50 transition-colors"
            aria-label="Cancel voice action"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => void handleConfirm()}
            disabled={isProcessing}
            className="flex-1 py-2 text-body font-medium text-white bg-brand-600 hover:bg-brand-800 rounded-md disabled:opacity-50 transition-colors"
            aria-label="Confirm voice action"
            data-testid="voice-confirm-confirm-btn"
          >
            {isProcessing ? "Processing…" : "Confirm"}
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Refusal message component — shown when voice tries to make a line-item edit.
 * Per §G.8: voice cannot commit line-item edits. No VoiceConfirmTurn is rendered.
 */
export function VoiceLineEditRefusal() {
  return (
    <div
      className="fixed bottom-20 left-0 right-0 mx-4 z-50"
      role="status"
      aria-live="polite"
    >
      <div className="bg-neutral-100 border border-neutral-200 rounded-lg p-4">
        <p className="text-body text-neutral-600">
          Voice can approve, reject, or kick back a quote, but line edits need
          to be done on the review screen.
        </p>
      </div>
    </div>
  );
}
