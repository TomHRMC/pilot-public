/**
 * useLaborRates — TanStack Query hook for active labor rate versions
 *
 * Location: apps/web/src/features/catalog/hooks/useLaborRates.ts
 *
 * CRITICAL: Labor rates are mounted at GET /api/v1/settings (NOT /settings/labor-rates).
 * The labor_rates router uses prefix="/api/v1/settings" in main.py.
 *
 * Query key: ['catalog-labor-rates']
 * Response: raw dict list (not Pydantic schema) — field names from labor_rates.py:
 *   id, skill_level_code, hourly_rate_cents, burden_pct (string), burdened_rate_cents,
 *   valid_period_lower, valid_period_upper, created_at, created_by
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface LaborRateVersion {
  id: number;
  skill_level_code: string;
  hourly_rate_cents: number;
  burden_pct: string; // stored as string from Decimal — e.g. "0.15"
  burdened_rate_cents: number;
  valid_period_lower: string | null;
  valid_period_upper: string | null;
  created_at: string | null;
  created_by: string | null;
}

export const LABOR_RATES_QUERY_KEY = ["catalog-labor-rates"] as const;

export function useLaborRates(skillLevelCode?: string) {
  return useQuery({
    queryKey: LABOR_RATES_QUERY_KEY,
    queryFn: async (): Promise<LaborRateVersion[]> => {
      const params: Record<string, unknown> = {};
      if (skillLevelCode) {
        params.skill_level_code = skillLevelCode;
      }
      const res = await apiClient.get("/api/v1/settings", { params });
      return res.data as LaborRateVersion[];
    },
    staleTime: 60_000,
  });
}
