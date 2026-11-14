/**
 * useMarkups — TanStack Query hook for active markup versions
 *
 * Location: apps/web/src/features/catalog/hooks/useMarkups.ts
 *
 * Endpoint: GET /api/v1/settings/markups
 * Query key: ['catalog-markups']
 * Returns: TenantMarkupVersionListResponse { items: [...], total: N }
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface TenantMarkupVersion {
  id: number;
  tenant_id: string;
  job_expense_category_code: string;
  markup_pct: number;
  markup_amt_cents: number | null;
  valid_period_lower: string;
  valid_period_upper: string | null;
  recorded_at: string;
  created_by: string | null;
}

export interface TenantMarkupVersionListResponse {
  items: TenantMarkupVersion[];
  total: number;
}

export const MARKUPS_QUERY_KEY = ["catalog-markups"] as const;

export function useMarkups() {
  return useQuery({
    queryKey: MARKUPS_QUERY_KEY,
    queryFn: async (): Promise<TenantMarkupVersionListResponse> => {
      const res = await apiClient.get("/api/v1/settings/markups");
      return res.data as TenantMarkupVersionListResponse;
    },
    staleTime: 60_000,
  });
}
