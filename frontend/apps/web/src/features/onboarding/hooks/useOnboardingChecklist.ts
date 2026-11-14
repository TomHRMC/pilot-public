/**
 * useOnboardingChecklist — TanStack Query hook for setup checklist
 *
 * Location: apps/web/src/features/onboarding/hooks/useOnboardingChecklist.ts
 *
 * Design doc Section D.3: server-driven checklist; 30s staleTime; refetchOnWindowFocus.
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { mapChecklistResponse } from "../types";
import type {
  OnboardingChecklistResponse,
  OnboardingChecklistState,
} from "../types";

export const CHECKLIST_QUERY_KEY = (tenantId: string) =>
  ["onboarding-checklist", tenantId] as const;

export function useOnboardingChecklist(tenantId: string | null | undefined) {
  return useQuery({
    queryKey: CHECKLIST_QUERY_KEY(tenantId ?? ""),
    queryFn: async (): Promise<OnboardingChecklistState> => {
      const response = await apiClient.get<OnboardingChecklistResponse>(
        `/api/v1/tenants/${tenantId}/onboarding/checklist`,
      );
      return mapChecklistResponse(response.data);
    },
    staleTime: 30_000,
    refetchOnWindowFocus: true,
    enabled: !!tenantId,
  });
}
