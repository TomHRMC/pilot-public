/**
 * useCustomers — TanStack Query hook for customer list
 *
 * Location: apps/web/src/features/customers/hooks/useCustomers.ts
 *
 * RULE: Uses apiClient (never raw fetch).
 * RULE: Query key is ["customers", offset, limit, search, status].
 *
 * UI-FIX-1C: Updated to return PaginatedResult<CustomerListItem>.
 * - skip → offset (canonical; skip kept as alias on backend)
 * - Added status filter (active | inactive)
 * - Added LIST_PAGE_SIZE = 25 as default limit
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { LIST_PAGE_SIZE } from "@pilot/shared-api";

export interface CustomerListItem {
  id: string;
  tenant_id: string;
  type: string;
  display_name: string;
  first_name: string | null;
  last_name: string | null;
  company_name: string | null;
  email: string | null;
  mobile_phone: string | null;
}

/** Generic paginated response shape — matches backend PaginatedResponse[T] */
export interface PaginatedResult<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface UseCustomersOptions {
  offset?: number;
  limit?: number;
  search?: string;
  /** active | inactive | "" (empty = All) */
  status?: "active" | "inactive" | "";
}

export const CUSTOMERS_QUERY_KEY = (
  offset: number,
  limit: number,
  search?: string,
  status?: string,
) => ["customers", offset, limit, search ?? "", status ?? ""] as const;

export function useCustomers({
  offset = 0,
  limit = LIST_PAGE_SIZE,
  search,
  status,
}: UseCustomersOptions = {}) {
  return useQuery({
    queryKey: CUSTOMERS_QUERY_KEY(offset, limit, search, status),
    queryFn: async (): Promise<PaginatedResult<CustomerListItem>> => {
      const params: Record<string, unknown> = { offset, limit };
      if (search?.trim()) params.search = search.trim();
      if (status) params.status = status;
      const res = await apiClient.get("/api/v1/customers/", { params });
      return res.data as PaginatedResult<CustomerListItem>;
    },
    staleTime: 60_000,
  });
}
