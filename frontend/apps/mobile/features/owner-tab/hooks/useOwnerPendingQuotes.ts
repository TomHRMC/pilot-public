import { Platform } from "react-native";
/**
 * useOwnerPendingQuotes — TanStack Query hook for owner approvals queue
 *
 * Location: apps/mobile/features/owner-tab/hooks/useOwnerPendingQuotes.ts
 *
 * GET /api/v1/quotes?status=pending_approval&limit=100
 * Returns ALL pending quotes across the entire tenant (no submitted_by filter).
 * Owner sees all tech submissions awaiting approval.
 *
 * Pattern: follows useCalendarStatus.ts (staleTime, refetchInterval, enabled)
 * MOB-B5
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export const OWNER_PENDING_QUOTES_QUERY_KEY = ["owner-pending-quotes"] as const;

export interface OwnerPendingQuote {
  id: string;
  tenant_id: string;
  customer_id: string;
  customer_name: string | null;
  site_id: string;
  status_id: string;
  status_code: string | null;
  subtotal_cents: number;
}

interface PaginatedQuoteListResponse {
  items: OwnerPendingQuote[];
  total: number;
  limit: number;
  offset: number;
}

async function fetchOwnerPendingQuotes(): Promise<OwnerPendingQuote[]> {
  const res = await apiClient.get<PaginatedQuoteListResponse>(
    "/api/v1/quotes",
    {
      params: { status: "pending_approval", limit: 100 },
      // NOTE: NO submitted_by param — owner sees ALL pending quotes across all techs
    },
  );
  // Backend returns PaginatedQuoteListResponse { items, total, limit, offset }
  return res.data.items ?? [];
}

export function useOwnerPendingQuotes() {
  const isMockAuth =
    Platform.OS === "web" && process.env.EXPO_PUBLIC_USE_MOCK_AUTH === "true";

  const query = useQuery({
    queryKey: OWNER_PENDING_QUOTES_QUERY_KEY,
    queryFn: fetchOwnerPendingQuotes,
    staleTime: 60_000, // 60 seconds
    refetchOnWindowFocus: false, // Mobile: no window focus events
    refetchInterval: 5 * 60 * 1000, // 5-minute background refresh
    retry: 1,
    // In mock auth mode there is no real Cognito session — skip the fetch entirely
    enabled: !isMockAuth,
  });

  return {
    quotes: query.data ?? [],
    pendingCount: query.data?.length ?? 0,
    isLoading: query.isLoading,
    isError: query.isError,
    refetch: query.refetch,
  };
}
