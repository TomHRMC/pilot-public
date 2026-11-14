/**
 * useVoiceQuoteSubmit — quote submission mutation
 *
 * Location: apps/mobile/features/voice-quote-creation/hooks/useVoiceQuoteSubmit.ts
 *
 * Calls POST /api/v1/quotes or PATCH /api/v1/quotes/{id} depending on context.
 * After submission, the backend sends action_committed WS event with snapshot_frozen=true.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";

interface SubmitQuotePayload {
  quoteId: string;
  action: "submit_for_approval" | "send";
}

async function submitQuoteAction({
  quoteId,
  action,
}: SubmitQuotePayload): Promise<void> {
  const endpoint =
    action === "send"
      ? `/api/v1/quotes/${quoteId}/send`
      : `/api/v1/quotes/${quoteId}/submit`;

  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error(`Failed to ${action} quote`);
}

export function useVoiceQuoteSubmit() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: submitQuoteAction,
    onSuccess: (_, variables) => {
      // Invalidate quote cache so live-mode cards refresh
      queryClient.invalidateQueries({
        queryKey: ["quotes", variables.quoteId],
      });
    },
  });

  return {
    submitQuote: (
      quoteId: string,
      action: SubmitQuotePayload["action"] = "submit_for_approval",
    ) => mutation.mutateAsync({ quoteId, action }),
    isSubmitting: mutation.isPending,
    error: mutation.error,
  };
}
