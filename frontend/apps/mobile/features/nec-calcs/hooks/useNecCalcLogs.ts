/**
 * useNecCalcLogs — Saved NEC Calculations Hook
 *
 * Location: apps/mobile/features/nec-calcs/hooks/useNecCalcLogs.ts
 *
 * Fetches the list of previously saved NEC calculation logs from the API.
 * Used by the SavedCalcsScreen.
 *
 * Endpoint: GET /api/v1/nec/calc-logs (confirmed in openapi_schema_map.md)
 *
 * Per batch-mob-b4-design.md §F.2.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SavedNecCalcLog {
  id: string;
  calc_type: string;
  nec_guide_version: string;
  inputs_json: Record<string, unknown>;
  result_json: Record<string, unknown>;
  is_offline_calc: boolean;
  client_capture_at: string | null;
  job_id: string | null;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useNecCalcLogs() {
  return useQuery({
    queryKey: ["nec-calc-logs"],
    queryFn: async () => {
      const res = await apiClient.get<SavedNecCalcLog[]>(
        "/api/v1/nec/calc-logs",
        {
          params: { limit: 50 },
        },
      );
      return res.data;
    },
    staleTime: 30_000,
  });
}
