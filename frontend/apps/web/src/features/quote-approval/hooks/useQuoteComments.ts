/**
 * useQuoteApprovalComments — TanStack Query hook for quote comments/annotations
 *
 * Location: apps/web/src/features/quote-approval/hooks/useQuoteComments.ts
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface QuoteComment {
  id: string;
  quote_id: string;
  user_id: string;
  user_name: string;
  user_role: "owner" | "technician" | "customer";
  annotation_type: "overall" | "line_item" | "header";
  affected_line_item_id: string | null;
  comment: string;
  created_at: string;
}

async function fetchQuoteComments(quoteId: string): Promise<QuoteComment[]> {
  const res = await apiClient.get(`/api/v1/quotes/${quoteId}/comments`);
  return res.data as QuoteComment[];
}

export function useQuoteApprovalComments(quoteId: string) {
  return useQuery({
    queryKey: ["quotes", quoteId, "comments"],
    queryFn: () => fetchQuoteComments(quoteId),
    staleTime: 60_000,
  });
}
