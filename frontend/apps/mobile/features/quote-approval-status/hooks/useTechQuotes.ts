/**
 * useTechQuotes — TanStack Query hook for tech's own quote list
 *
 * Location: apps/mobile/features/quote-approval-status/hooks/useTechQuotes.ts
 *
 * MOB-B1: Migrated from raw fetch() to apiClient per Rule C.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export type TechQuoteStatus =
  | "draft"
  | "pending_approval"
  | "approved"
  | "rejected"
  | "sent"
  | "accepted"
  | "declined";

export interface TechQuoteSummary {
  id: string;
  quote_number: string;
  status: TechQuoteStatus;
  customer_name: string;
  total_cents: number;
  submitted_at: string | null;
  has_owner_edits: boolean;
  quote_version_id: string;
}

interface PaginatedQuoteListResponse {
  items: TechQuoteSummary[];
  total: number;
  limit: number;
  offset: number;
}

async function fetchTechQuotes(): Promise<TechQuoteSummary[]> {
  const res = await apiClient.get<PaginatedQuoteListResponse>(
    "/api/v1/quotes",
    {
      params: {
        submitted_by: "me",
        status: "pending_approval,approved,rejected,draft",
      },
    },
  );
  // Backend returns PaginatedQuoteListResponse { items, total, limit, offset }
  return res.data.items ?? [];
}

export function useTechQuotes() {
  return useQuery({
    queryKey: ["tech-quotes"],
    queryFn: fetchTechQuotes,
    staleTime: 30_000,
    refetchInterval: 30_000,
  });
}
