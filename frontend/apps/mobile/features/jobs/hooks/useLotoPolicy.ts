/**
 * useLotoPolicy — TanStack Query hook for tenant LOTO policy
 *
 * Location: apps/mobile/features/jobs/hooks/useLotoPolicy.ts
 *
 * API: GET /api/v1/settings/loto-policy
 * Query key: ['loto-policy']
 * Cache: staleTime: 300_000 (5 min — tenant settings rarely change mid-session)
 *
 * Graceful degradation: On error, returns { loto_confirmation_required: false }
 * (optional mode). Never hides the LOTO section on error.
 *
 * Per batch-mob-b7-design.md §F.1
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface LotoPolicyResponse {
  loto_confirmation_required: boolean;
}

const LOTO_POLICY_DEFAULT: LotoPolicyResponse = {
  loto_confirmation_required: false,
};

export function useLotoPolicy() {
  return useQuery<LotoPolicyResponse>({
    queryKey: ["loto-policy"],
    queryFn: async (): Promise<LotoPolicyResponse> => {
      const res = await apiClient.get<LotoPolicyResponse>(
        "/api/v1/settings/loto-policy",
      );
      return res.data;
    },
    staleTime: 300_000,
    // Graceful degradation: on error, fall back to default (optional mode)
    placeholderData: LOTO_POLICY_DEFAULT,
  });
}
