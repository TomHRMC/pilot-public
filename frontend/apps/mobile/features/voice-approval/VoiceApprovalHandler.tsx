/**
 * VoiceApprovalHandler — mobile voice approval intent composer
 *
 * Location: apps/mobile/features/voice-approval/VoiceApprovalHandler.tsx
 *
 * Composes <VoiceConfirmTurn> from FE-B3 for approval intents.
 * Per §G.8: mounted at the global voice session shell level.
 */

import React, { useCallback } from "react";
import { View, Text, StyleSheet } from "react-native";
import {
  VoiceConfirmTurn,
  useVoiceConfirmation,
} from "@pilot/ui/voice-confirm-turn";
import { colors, spacing, radii } from "@pilot/ui/tokens";

type ApprovalIntent = "approve_quote" | "reject_quote" | "request_quote_edits";

interface VoiceApprovalHandlerProps {
  quoteId: string;
  quoteNumber: string;
  customerName: string;
  detectedIntent: ApprovalIntent | null;
  onApprove: () => Promise<void>;
  onReject: () => Promise<void>;
  onKickback: () => Promise<void>;
  onIntentHandled: () => void;
}

const APPROVAL_PROMPTS: Record<
  ApprovalIntent,
  (n: string, c: string) => string
> = {
  approve_quote: (n, c) => `Approve quote #${n} for ${c}?`,
  reject_quote: (n, c) => `Reject quote #${n} for ${c}? This is permanent.`,
  request_quote_edits: (n, c) =>
    `Kick back quote #${n} for ${c} to the tech for revisions?`,
};

const SUPPORTED_INTENTS = new Set<ApprovalIntent>([
  "approve_quote",
  "reject_quote",
  "request_quote_edits",
]);

export function VoiceApprovalHandler({
  quoteId: _quoteId,
  quoteNumber,
  customerName,
  detectedIntent,
  onApprove,
  onReject,
  onKickback,
  onIntentHandled,
}: VoiceApprovalHandlerProps) {
  const {
    pendingConfirmation,
    setPendingConfirmation,
    confirm,
    cancel,
    isConfirming,
  } = useVoiceConfirmation();

  React.useEffect(() => {
    if (!detectedIntent || !SUPPORTED_INTENTS.has(detectedIntent)) return;
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
          await onApprove();
          break;
        case "reject_quote":
          await onReject();
          break;
        case "request_quote_edits":
          await onKickback();
          break;
      }
    });
    onIntentHandled();
  }, [
    pendingConfirmation,
    confirm,
    onApprove,
    onReject,
    onKickback,
    onIntentHandled,
  ]);

  const handleCancel = useCallback(() => {
    cancel();
    onIntentHandled();
  }, [cancel, onIntentHandled]);

  if (!pendingConfirmation) return null;

  return (
    <VoiceConfirmTurn
      prompt={pendingConfirmation.prompt}
      onConfirm={() => void handleConfirm()}
      onCancel={handleCancel}
      isProcessing={isConfirming}
      testID="voice-approval-confirm-turn"
    />
  );
}

/**
 * Shown when voice tries to make a line-item edit.
 * Per §G.8: voice cannot commit edits. No VoiceConfirmTurn is rendered.
 */
export function VoiceLineEditRefusal() {
  return (
    <View
      style={styles.container}
      accessibilityRole="none"
      accessibilityLiveRegion="polite"
    >
      <Text style={styles.text}>
        Voice can approve, reject, or kick back a quote, but line edits need to
        be done on the review screen.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.neutral[100],
    borderRadius: radii.md,
    padding: spacing[4],
    margin: spacing[3],
    borderWidth: 1,
    borderColor: colors.neutral[200],
  },
  text: {
    fontSize: 13,
    color: colors.neutral[600],
    lineHeight: 20,
  },
});
