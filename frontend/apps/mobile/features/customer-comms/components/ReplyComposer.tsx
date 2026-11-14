/**
 * ReplyComposer — Bottom-anchored SMS reply composer
 *
 * Location: apps/mobile/features/customer-comms/components/ReplyComposer.tsx
 *
 * RULE 1: Composes usePreviewBeforeSend (LOCKED FE-B6) for the send path.
 * RULE 3: Mic button uses single-utterance voice dictation (NOT a full session).
 * RULE 4: Segment counter uses useSegmentCount — no inline calculation.
 * RULE 7: TCPA — Send button disabled when opted out. NO force-send path exists.
 * RULE 8: Optimistic send via useOptimisticMutation (through useReplyToThread).
 *
 * Token refs (ZERO TOLERANCE):
 *   Opted-out/blocked: fault[50] bg, fault[200] border, fault[800] text
 *   Warning: alert[600] text
 *
 * Design doc Section A.3.1, Decisions 3, 7, D.3, E.1-E.7
 */

import React, { useState, useCallback, useEffect, useId } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  StyleSheet,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import {
  usePreviewBeforeSend,
  SmsQuotaIndicator,
  useSegmentCount,
  NotificationBanner,
  MessagePreviewModal,
} from "@pilot/ui";
import {
  colors,
  spacing,
  mobileFontSizes,
  fontWeights,
  radii,
} from "../../../../../packages/ui/src/tokens";
import type { NotificationItem } from "@pilot/ui";
import { useReplyToThread } from "../hooks/useReplyToThread";
import { useSmsQuota } from "../hooks/useSmsQuota";
import { useVoiceDictation } from "../hooks/useVoiceDictation";

interface ReplyComposerProps {
  threadId: string;
  customerId: string;
  /** When true, renders Send as disabled + opted-out banner */
  isOptedOut?: boolean;
  testID?: string;
}

let errorCounter = 0;

export function ReplyComposer({
  threadId,
  customerId,
  isOptedOut = false,
  testID,
}: ReplyComposerProps) {
  const [text, setText] = useState("");
  const [errorNotification, setErrorNotification] =
    useState<NotificationItem | null>(null);

  // Segment count — RULE 4: always computed, never hardcoded
  const segmentResult = useSegmentCount(text);

  // Quota
  const { quota, isSendBlocked, quotaState } = useSmsQuota({ customerId });

  // Send via optimistic mutation
  const replyMutation = useReplyToThread(threadId);

  // Voice dictation — single-utterance only (RULE 3)
  const {
    state: dictationState,
    startDictating,
    stopDictating,
    reset: resetDictation,
  } = useVoiceDictation();

  // usePreviewBeforeSend LOCKED from FE-B6 — always-preview-before-send pattern
  const { preview, send, isSending, isModalOpen, closeModal, previewData } =
    usePreviewBeforeSend({
      onSendSuccess: () => {
        setText("");
        resetDictation();
      },
      onSendError: (err: Error) => {
        const errorId = `composer-error-${++errorCounter}`;
        if (err.message === "OPTED_OUT") {
          setErrorNotification({
            id: errorId,
            severity: "error",
            title: "Customer has opted out — they cannot be reached via SMS",
            createdAt: new Date(),
          });
        } else if (err.message === "QUOTA_EXHAUSTED") {
          setErrorNotification({
            id: errorId,
            severity: "error",
            title:
              "Monthly SMS limit reached — contact your owner to adjust your plan",
            createdAt: new Date(),
          });
        } else {
          setErrorNotification({
            id: errorId,
            severity: "warning",
            title: "Couldn't send — check your connection and try again",
            createdAt: new Date(),
          });
        }
      },
    });

  // Populate text field from voice dictation transcript
  useEffect(() => {
    if (dictationState.phase === "transcribed") {
      setText(dictationState.transcript);
    }
    if (dictationState.phase === "error") {
      const errorId = `dictation-error-${++errorCounter}`;
      setErrorNotification({
        id: errorId,
        severity: "warning",
        title: "Voice transcription failed — type your message instead",
        createdAt: new Date(),
      });
    }
  }, [dictationState]);

  // TCPA RULE 7: isOptedOut OR quota blocks send — NO override path
  const effectivelySendBlocked =
    isOptedOut || isSendBlocked || quotaState?.state === "opted_out";

  const canSend =
    text.trim().length > 0 && !effectivelySendBlocked && !isSending;

  const handleSend = useCallback(async () => {
    if (!canSend || !quota) return;
    setErrorNotification(null);

    // Always-preview-before-send (LOCKED RULE 1)
    await preview({
      mode: "free-form",
      customerId,
      freeFormBody: text.trim(),
      threadId,
    });
  }, [canSend, preview, text, threadId, customerId, quota]);

  const handleConfirmSend = useCallback(async () => {
    await send();

    // Trigger optimistic mutation for immediate UI feedback
    replyMutation.mutate({
      threadId,
      request: {
        body: text.trim(),
        composition_method:
          dictationState.phase === "transcribed"
            ? "free_form_voice"
            : "free_form_text",
      },
      estimatedSegmentCount: segmentResult.segmentCount,
    });
  }, [
    send,
    text,
    threadId,
    replyMutation,
    dictationState.phase,
    segmentResult.segmentCount,
  ]);

  const handleMicPress = useCallback(() => {
    if (dictationState.phase === "recording") {
      stopDictating();
    } else {
      startDictating();
    }
  }, [dictationState.phase, startDictating, stopDictating]);

  const isRecording = dictationState.phase === "recording";
  const isTranscribing = dictationState.phase === "transcribing";

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      testID={testID ?? "reply-composer"}
    >
      {/* Error/warning notification banner */}
      {errorNotification && (
        <NotificationBanner
          notification={errorNotification}
          onDismiss={() => setErrorNotification(null)}
        />
      )}

      {/* TCPA: Opted-out banner — RULE 7: NO force-send affordance anywhere */}
      {(isOptedOut || quotaState?.state === "opted_out") && (
        <View style={styles.optedOutBanner} testID="opted-out-banner">
          <Text style={styles.optedOutText}>
            Customer has opted out — they cannot be reached via SMS
          </Text>
        </View>
      )}

      {/* Composer row */}
      <View style={styles.composerRow}>
        {/* Mic button — single-utterance dictation only (RULE 3) */}
        <Pressable
          style={[styles.micButton, isRecording && styles.micButtonActive]}
          onPress={handleMicPress}
          disabled={effectivelySendBlocked}
          accessibilityLabel={
            isRecording ? "Stop recording" : "Start voice dictation"
          }
          testID="mic-button"
        >
          {isTranscribing ? (
            <ActivityIndicator color={colors.brand[600]} size="small" />
          ) : (
            <Text style={[styles.micIcon, isRecording && styles.micIconActive]}>
              🎤
            </Text>
          )}
        </Pressable>

        {/* Text input */}
        <TextInput
          style={styles.textInput}
          value={text}
          onChangeText={setText}
          placeholder="Type a message…"
          placeholderTextColor={colors.neutral[400]}
          multiline
          maxLength={1600}
          editable={!effectivelySendBlocked}
          testID="composer-text-input"
          accessibilityLabel="SMS reply text"
        />

        {/* Send button — disabled when TCPA opt-out OR hard-cap (RULE 7) */}
        <Pressable
          style={[styles.sendButton, !canSend && styles.sendButtonDisabled]}
          onPress={() => void handleSend()}
          disabled={!canSend}
          accessibilityLabel="Send message"
          testID="send-button"
        >
          {isSending ? (
            <ActivityIndicator color={colors.neutral[50]} size="small" />
          ) : (
            <Text style={styles.sendIcon}>↑</Text>
          )}
        </Pressable>
      </View>

      {/* Quota indicator footer — RULE 4: live segment count from useSegmentCount */}
      {quota && (
        <SmsQuotaIndicator
          quota={quota}
          currentMessageSegmentCount={
            text.length > 0 ? segmentResult.segmentCount : 0
          }
          testID="quota-indicator"
        />
      )}

      {/* MessagePreviewModal — ALWAYS-PREVIEW-BEFORE-SEND (LOCKED FE-B6 RULE 1) */}
      {isModalOpen && previewData && (
        <MessagePreviewModal
          isOpen={isModalOpen}
          previewData={previewData}
          isSending={isSending}
          onConfirm={() => void handleConfirmSend()}
          onCancel={closeModal}
        />
      )}
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  composerRow: {
    flexDirection: "row",
    alignItems: "flex-end",
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
    backgroundColor: colors.neutral[50],
    borderTopWidth: 1,
    borderTopColor: colors.neutral[200],
    gap: spacing[2],
  },
  micButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.neutral[100],
    alignItems: "center",
    justifyContent: "center",
  },
  micButtonActive: {
    backgroundColor: colors.alert[100],
  },
  micIcon: {
    fontSize: 18,
  },
  micIconActive: {},
  textInput: {
    flex: 1,
    minHeight: 40,
    maxHeight: 120,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.neutral[200],
    backgroundColor: colors.neutral[100],
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2],
    fontSize: mobileFontSizes.body,
    color: colors.neutral[900],
  },
  sendButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.brand[600],
    alignItems: "center",
    justifyContent: "center",
  },
  sendButtonDisabled: {
    backgroundColor: colors.neutral[400],
  },
  sendIcon: {
    fontSize: 18,
    color: colors.neutral[50],
    fontWeight: String(fontWeights.medium) as "500",
  },
  optedOutBanner: {
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
    backgroundColor: colors.fault[50],
    borderTopWidth: 1,
    borderTopColor: colors.fault[200],
  },
  optedOutText: {
    fontSize: mobileFontSizes.caption,
    color: colors.fault[800],
    fontWeight: String(fontWeights.medium) as "500",
  },
});
