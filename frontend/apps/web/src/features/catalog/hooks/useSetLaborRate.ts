/**
 * useSetLaborRate — mutation hook for creating/superseding a labor rate version
 *
 * Location: apps/web/src/features/catalog/hooks/useSetLaborRate.ts
 *
 * CRITICAL: Mounted at POST /api/v1/settings (NOT /settings/labor-rates).
 * Pattern: temporal supersession — always POST to update; never PATCH/PUT
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { LaborRateVersion } from "./useLaborRates";
import { LABOR_RATES_QUERY_KEY } from "./useLaborRates";

export interface SetLaborRatePayload {
  skill_level_code: string;
  hourly_rate_cents: number; // must be > 0
  burden_pct: number; // 0.0 to 9.9999
  effective_from?: string | null; // ISO datetime; defaults to now() on backend
}

export function useSetLaborRate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      payload: SetLaborRatePayload,
    ): Promise<LaborRateVersion> => {
      const res = await apiClient.post("/api/v1/settings", payload);
      return res.data as LaborRateVersion;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: LABOR_RATES_QUERY_KEY });
    },
  });
}
