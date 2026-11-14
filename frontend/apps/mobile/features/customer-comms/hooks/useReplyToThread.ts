/**
 * useReplyToThread — Send a reply to an SMS thread with optimistic UI
 *
 * Location: apps/mobile/features/customer-comms/hooks/useReplyToThread.ts
 *
 * RULE 8: Uses useOptimisticMutation from packages/ui (established FE-B7).
 * No custom optimistic state.
 *
 * Optimistic flow per design doc Section D.6:
 *   1. onMutate: inject SmsMessage{ status: 'pending_send' } into cache
 *               decrement ['sms-quota'].remaining_segments by estimated segmentCount
 *   2. POST /threads/{threadId}/reply
 *   3. onSuccess: replace optimistic message with server response; invalidate quota
 *   4. onError: remove optimistic message; rollback quota snapshot
 *
 * Design doc Section C.3, D.6, Rules 8
 */

import { useQueryClient } from "@tanstack/react-query";
import { useOptimisticMutation } from "@pilot/ui";
import type {
  SmsMessage,
  SmsReplyRequest,
  SmsReplyResponse,
  SmsQuotaStatus,
} from "@pilot/ui";
import { apiClient } from "@pilot/shared-api";

interface ReplyVariables {
  threadId: string;
  request: SmsReplyRequest;
  estimatedSegmentCount: number;
}

async function sendReply(variables: ReplyVariables): Promise<SmsReplyResponse> {
  try {
    const res = await apiClient.post<SmsReplyResponse>(
      `/api/v1/communications/threads/${variables.threadId}/reply`,
      variables.request,
    );
    return res.data;
  } catch (err: any) {
    const status = err.response?.status;
    const detail = err.response?.data?.detail;

    if (status === 422 && detail === "customer_opted_out") {
      throw new Error("OPTED_OUT");
    }
    if (status === 429 || detail === "monthly_quota_reached") {
      throw new Error("QUOTA_EXHAUSTED");
    }

    throw new Error(`Reply failed: ${status} ${detail ?? err.message}`);
  }
}

export function useReplyToThread(threadId: string) {
  const queryClient = useQueryClient();

  return useOptimisticMutation<ReplyVariables, { optimisticMessageId: string }>(
    {
      deferToOrchestrator: false, // Online-only — SMS requires active connection

      optimisticUpdate: async (variables) => {
        const optimisticMessageId = `optimistic-${Date.now()}`;

        // Inject optimistic message into thread messages cache
        const optimisticMessage: SmsMessage = {
          message_id: optimisticMessageId,
          thread_id: variables.threadId,
          direction: "outbound",
          channel: "sms",
          body: variables.request.body,
          segment_count: variables.estimatedSegmentCount,
          status: "pending_send",
          carrier_message_id: null,
          composition_method: variables.request.composition_method,
          template_id: null,
          voice_audio_id: variables.request.voice_audio_id ?? null,
          sent_at: null,
          delivered_at: null,
          received_at: null,
          audit_user_id: "current-user",
        };

        queryClient.setQueryData(
          ["thread-messages", variables.threadId],
          (old: { pages: { messages: SmsMessage[] }[] } | undefined) => {
            if (!old) return old;
            return {
              ...old,
              pages: old.pages.map((page, idx) =>
                idx === old.pages.length - 1
                  ? { ...page, messages: [...page.messages, optimisticMessage] }
                  : page,
              ),
            };
          },
        );

        // Optimistically decrement quota
        queryClient.setQueryData(
          ["sms-quota", { customerId: undefined }],
          (old: SmsQuotaStatus | undefined) => {
            if (!old) return old;
            return {
              ...old,
              remaining_segments: Math.max(
                0,
                old.remaining_segments - variables.estimatedSegmentCount,
              ),
              used_segments:
                old.used_segments + variables.estimatedSegmentCount,
            };
          },
        );

        return { optimisticMessageId };
      },

      rollbackFn: async (localRecord) => {
        // Remove optimistic message on failure
        queryClient.setQueryData(
          ["thread-messages", threadId],
          (old: { pages: { messages: SmsMessage[] }[] } | undefined) => {
            if (!old) return old;
            return {
              ...old,
              pages: old.pages.map((page) => ({
                ...page,
                messages: page.messages.filter(
                  (m) => m.message_id !== localRecord.optimisticMessageId,
                ),
              })),
            };
          },
        );

        // Invalidate quota to restore actual value
        void queryClient.invalidateQueries({ queryKey: ["sms-quota"] });
      },

      mutationFn: async (variables) => {
        const response = await sendReply(variables);

        // Replace optimistic message with server response
        queryClient.setQueryData(
          ["thread-messages", variables.threadId],
          (old: { pages: { messages: SmsMessage[] }[] } | undefined) => {
            if (!old) return old;
            // Find and update the optimistic message that matches
            return {
              ...old,
              pages: old.pages.map((page) => ({
                ...page,
                messages: page.messages.map((m) =>
                  m.status === "pending_send" &&
                  m.body === variables.request.body
                    ? {
                        ...m,
                        message_id: response.message_id,
                        status: response.status,
                        sent_at: response.sent_at,
                      }
                    : m,
                ),
              })),
            };
          },
        );

        // Refresh actual quota from server
        void queryClient.invalidateQueries({ queryKey: ["sms-quota"] });
      },
    },
  );
}
