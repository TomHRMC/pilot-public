/**
 * useQuoteDetail — TanStack Query hook for quote detail with pending edits
 *
 * Location: apps/web/src/features/quote-approval/hooks/useQuoteDetail.ts
 *
 * Calls GET /api/v1/quotes/{quote_id}/detail — the aggregated endpoint
 * added in PRE-WS3-FIX-01 that returns all fields QuoteDetailPage needs
 * in a single request.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";

// Use the generated canonical types — do NOT hand-roll interfaces for these.
export type QuoteDetail = components["schemas"]["QuoteDetailResponse"];
export type QuoteLineItem = components["schemas"]["QuoteLineDetailResponse"];

async function fetchQuoteDetail(id: string): Promise<QuoteDetail> {
  const res = await apiClient.get(`/api/v1/quotes/${id}/detail`);
  return res.data as QuoteDetail;
}

export function useQuoteDetail(id: string) {
  return useQuery({
    queryKey: ["quotes", id, "detail"],
    queryFn: () => fetchQuoteDetail(id),
    staleTime: 60_000,
  });
}
