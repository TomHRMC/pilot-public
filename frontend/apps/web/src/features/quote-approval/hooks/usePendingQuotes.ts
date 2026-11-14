/**
 * usePendingQuotes — TanStack Query hook for pending approval inbox
 *
 * Location: apps/web/src/features/quote-approval/hooks/usePendingQuotes.ts
 *
 * API: GET /api/v1/quotes?status=pending_approval
 * Response: QuoteListItem[] (plain array — no pagination wrapper)
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface PendingQuoteFilters {
  customerSearch?: string;
  sortBy?: "newest" | "oldest";
}

/** Matches QuoteListItem from GET /api/v1/quotes */
export interface PendingQuoteSummary {
  id: string;
  customer_id: string;
  customer_name: string | null;
  quote_number: string | null;
  title: string | null;
  status_code: string | null;
  total_cents: number;
  subtotal_cents: number;
  tax_cents: number;
}

export interface PendingQuotesResponse {
  items: PendingQuoteSummary[];
  total: number;
}

async function fetchPendingQuotes(
  filters: PendingQuoteFilters,
): Promise<PendingQuotesResponse> {
  const res = await apiClient.get<PendingQuoteSummary[]>("/api/v1/quotes", {
    params: { status: "pending_approval" },
  });

  let items: PendingQuoteSummary[] = res.data;

  // Client-side customer search filter (API doesn't support it server-side)
  if (filters.customerSearch) {
    const q = filters.customerSearch.toLowerCase();
    items = items.filter(
      (item) =>
        item.customer_name?.toLowerCase().includes(q) ||
        item.quote_number?.toLowerCase().includes(q) ||
        item.title?.toLowerCase().includes(q),
    );
  }

  // Client-side sort (API returns newest-first by default)
  if (filters.sortBy === "oldest") {
    items = [...items].reverse();
  }

  return { items, total: items.length };
}

export function usePendingQuotes(filters: PendingQuoteFilters = {}) {
  return useQuery({
    queryKey: ["quotes", "pending-approval", filters],
    queryFn: () => fetchPendingQuotes(filters),
    staleTime: 30_000,
    refetchInterval: 30_000,
  });
}
