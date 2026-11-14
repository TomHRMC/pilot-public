/**
 * useUpdateQuote — PATCH /api/v1/quotes/{quote_id}
 *
 * Location: apps/web/src/features/quotes/hooks/useUpdateQuote.ts
 *
 * FE-B24: Used by QuoteMetadataEditModal to update expires_at and currency on draft quotes.
 *
 * RULE: Uses apiClient (never raw fetch).
 * RULE: onSuccess invalidates ["quote", quoteId] and ["quotes"] query families.
 *
 * PATCH /api/v1/quotes/{quote_id} — verified in openapi_schema_map.md (FE-B24 pre-work).
 * Only expires_at and currency are editable via this hook (status transitions go through approval workflow).
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface QuoteUpdatePayload {
  expires_at?: string | null; // ISO 8601 date string
  currency?: string;
}

export function useUpdateQuote(quoteId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: QuoteUpdatePayload): Promise<unknown> => {
      const res = await apiClient.patch(`/api/v1/quotes/${quoteId}`, payload);
      return res.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["quote", quoteId] });
      void queryClient.invalidateQueries({ queryKey: ["quotes"] });
    },
  });
}
