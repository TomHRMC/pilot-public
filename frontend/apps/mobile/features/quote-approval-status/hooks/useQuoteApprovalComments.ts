/**
 * useQuoteApprovalComments — mobile hook for quote comments
 *
 * Location: apps/mobile/features/quote-approval-status/hooks/useQuoteApprovalComments.ts
 */

import { useQuery } from "@tanstack/react-query";

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
  const res = await fetch(`/api/v1/quotes/${quoteId}/comments`);
  if (!res.ok) throw new Error("Failed to fetch quote comments");
  return res.json() as Promise<QuoteComment[]>;
}

export function useQuoteApprovalComments(quoteId: string) {
  return useQuery({
    queryKey: ["quotes", quoteId, "comments"],
    queryFn: () => fetchQuoteComments(quoteId),
    staleTime: 60_000,
  });
}
