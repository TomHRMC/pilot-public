/**
 * useQuotes — TanStack Query hook for quotes list
 *
 * Location: apps/web/src/features/quotes/hooks/useQuotes.ts
 *
 * RULE: Uses apiClient (never raw fetch).
 *
 * UI-FIX-1C: Updated to return PaginatedResult<QuoteListItem>.
 * - skip → offset (canonical; skip kept as alias on backend)
 * - Added customer_search, title_search, date_from, date_to filters
 * - Added LIST_PAGE_SIZE = 25 as default limit
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { LIST_PAGE_SIZE } from "@pilot/shared-api";

/** Current backend response shape — status_code and customer_name available since B17; quote_number added B19 */
export interface QuoteListItem {
  id: string;
  tenant_id: string;
  customer_id: string;
  customer_name: string | null;
  site_id: string;
  status_id: string;
  status_code: string | null;
  /** B19: human-readable quote identifier (e.g. "QUO-000001") */
  quote_number?: string | null;
  /** Quote title / description */
  title?: string | null;
  /** ISO 8601 UTC — when the quote record was created */
  created_at?: string | null;
  subtotal_cents: number;
  tax_cents: number;
  total_cents: number;
}

/** Generic paginated response shape — matches backend PaginatedResponse[T] */
export interface PaginatedResult<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface UseQuotesOptions {
  offset?: number;
  limit?: number;
  /** Server-side status filter — passed as ?status= query param */
  status?: string;
  /** Server-side customer name search — ILIKE on customer.display_name */
  customer_search?: string;
  /** Server-side title search — ILIKE on quote.title */
  title_search?: string;
  /** Filter quotes created on or after this date (YYYY-MM-DD) */
  date_from?: string;
  /** Filter quotes created on or before this date (YYYY-MM-DD) */
  date_to?: string;
  /** UI-FIX-2D: exact UUID filter — when set, scopes results to this customer */
  customer_id?: string;
}

export const QUOTES_QUERY_KEY = (options: UseQuotesOptions) =>
  ["quotes", options] as const;

export function useQuotes({
  offset = 0,
  limit = LIST_PAGE_SIZE,
  status,
  customer_search,
  title_search,
  date_from,
  date_to,
  customer_id,
}: UseQuotesOptions = {}) {
  return useQuery({
    queryKey: QUOTES_QUERY_KEY({
      offset,
      limit,
      status,
      customer_search,
      title_search,
      date_from,
      date_to,
      customer_id,
    }),
    queryFn: async (): Promise<PaginatedResult<QuoteListItem>> => {
      const params: Record<string, unknown> = { offset, limit };
      if (status) params.status = status;
      if (customer_search?.trim())
        params.customer_search = customer_search.trim();
      if (title_search?.trim()) params.title_search = title_search.trim();
      if (date_from) params.date_from = date_from;
      if (date_to) params.date_to = date_to;
      if (customer_id) params.customer_id = customer_id;
      const res = await apiClient.get("/api/v1/quotes", { params });
      return res.data as PaginatedResult<QuoteListItem>;
    },
    staleTime: 60_000,
  });
}
