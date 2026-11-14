/**
 * usePricebook — TanStack Query hook for pricebook item list
 *
 * Location: apps/web/src/features/catalog/hooks/usePricebook.ts
 *
 * Endpoint: GET /api/v1/catalog/pricebook
 *
 * UI-FIX-1C: Updated to return PaginatedResult<PricebookItem>.
 * - skip → offset (canonical)
 * - Added status filter (active | inactive | "")
 * - is_active param: active→true, inactive→false, ""→omitted (all)
 * - Returns paginated response shape
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { LIST_PAGE_SIZE } from "@pilot/shared-api";

export interface PricebookItemCurrentPrice {
  id: number;
  default_unit_price_cents: number;
  valid_period_lower: string | null;
  valid_period_upper: string | null;
  recorded_at: string;
}

export interface PricebookItem {
  id: string;
  tenant_id: string;
  sku: string;
  name: string;
  description: string | null;
  uom_id: string | null;
  taxability_code: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  updated_by: string | null;
  current_price: PricebookItemCurrentPrice | null;
}

/** Generic paginated response shape — matches backend PaginatedResponse[T] */
export interface PaginatedResult<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface UsePricebookOptions {
  search?: string;
  offset?: number;
  limit?: number;
  /** active | inactive | "" (empty = All) */
  status?: "active" | "inactive" | "";
}

export const PRICEBOOK_QUERY_KEY = (options: UsePricebookOptions) =>
  ["catalog-pricebook", options] as const;

export function usePricebook({
  search,
  offset = 0,
  limit = LIST_PAGE_SIZE,
  status,
}: UsePricebookOptions = {}) {
  return useQuery({
    queryKey: PRICEBOOK_QUERY_KEY({ search, offset, limit, status }),
    queryFn: async (): Promise<PaginatedResult<PricebookItem>> => {
      const params: Record<string, unknown> = { offset, limit };
      if (search?.trim()) params.search = search.trim();
      // Map status string to is_active boolean param
      if (status === "active") params.is_active = true;
      else if (status === "inactive") params.is_active = false;
      // "" or undefined → omit is_active (return all)
      const res = await apiClient.get("/api/v1/catalog/pricebook", { params });
      return res.data as PaginatedResult<PricebookItem>;
    },
    staleTime: 60_000,
  });
}
