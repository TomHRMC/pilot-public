/**
 * useCreateQuote — mutation hook to create a new quote
 *
 * Location: apps/web/src/features/quotes/hooks/useCreateQuote.ts
 *
 * Endpoint: POST /api/v1/quotes/
 * Generates a crypto.randomUUID() idempotency key on each call.
 * onSuccess: invalidates ['quotes'] queries.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";

export type QuoteCreateInput = {
  customer_id: string;
  site_id: string;
  currency?: string;
  expires_at?: string | null;
};

export type QuoteResponse = components["schemas"]["QuoteResponse"];

export function useCreateQuote() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: QuoteCreateInput): Promise<QuoteResponse> => {
      const idempotency_key = crypto.randomUUID();
      const res = await apiClient.post(
        "/api/v1/quotes/",
        {
          ...data,
          currency: data.currency ?? "USD",
          idempotency_key,
        },
        {
          headers: { "Idempotency-Key": idempotency_key },
        },
      );
      return res.data as QuoteResponse;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["quotes"] });
    },
  });
}
