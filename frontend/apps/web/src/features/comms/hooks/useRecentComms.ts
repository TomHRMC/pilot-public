/**
 * useRecentComms — TanStack Query hook for cross-customer recent communications
 *
 * Location: apps/web/src/features/comms/hooks/useRecentComms.ts
 *
 * GET /api/v1/communications/recent?limit&offset&customer_search&channel&sent_from&sent_to
 *
 * COMMS-UI-B1: Migrated from page/page_size to canonical offset/limit.
 * All filter params are included in the query key so any change refetches.
 *
 * RULE: Uses apiClient (never raw fetch).
 * RULE: TanStack Query v5 object-form; isPending not isLoading.
 * RULE: placeholderData: keepPreviousData so the table doesn't flash empty
 *       on page/filter change.
 */

import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";

export type RecentCommunicationsResponse =
  components["schemas"]["RecentCommunicationsResponse"];
export type CommunicationSummaryItem =
  components["schemas"]["CommunicationSummaryItem"];

/** Page size for the comms list — matches the backend default */
export const COMMS_PAGE_SIZE = 50;

export interface UseRecentCommsParams {
  limit: number;
  offset: number;
  customer_search?: string;
  channel?: string;
  sent_from?: string;
  sent_to?: string;
}

/**
 * Query key factory — every param the queryFn reads is included so
 * a filter change triggers a refetch with isolated cache.
 */
export const RECENT_COMMS_QUERY_KEY = (params: UseRecentCommsParams) =>
  [
    "recent-comms",
    {
      limit: params.limit,
      offset: params.offset,
      customer_search: params.customer_search ?? "",
      channel: params.channel ?? "",
      sent_from: params.sent_from ?? "",
      sent_to: params.sent_to ?? "",
    },
  ] as const;

export function useRecentComms(params: UseRecentCommsParams) {
  return useQuery({
    queryKey: RECENT_COMMS_QUERY_KEY(params),
    queryFn: async (): Promise<RecentCommunicationsResponse> => {
      const res = await apiClient.get<RecentCommunicationsResponse>(
        "/api/v1/communications/recent",
        { params },
      );
      return res.data;
    },
    staleTime: 30_000,
    placeholderData: keepPreviousData,
  });
}
