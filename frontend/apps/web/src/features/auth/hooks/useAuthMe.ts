"use client";

/**
 * useAuthMe — GET /api/v1/operator/auth/me
 *
 * Location: apps/web/src/features/auth/hooks/useAuthMe.ts
 *
 * C-B11 Part B: Fetches the post-Cognito-auth routing discriminator.
 * Returns user_type ("platform" | "tenant") + redirect_to so the login
 * flow can route platform users to /operator/cohort and tenant users to
 * /dashboard without a second API call.
 *
 * RULE 2: uses apiClient, never raw fetch().
 * RULE 12: TanStack Query v5 object-form, colocated query key.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";

export type AuthMeResponse = components["schemas"]["AuthMeResponse"];

export const AUTH_ME_QUERY_KEY = ["auth", "me"] as const;

export function useAuthMe() {
  return useQuery<AuthMeResponse>({
    queryKey: AUTH_ME_QUERY_KEY,
    queryFn: async () => {
      const res = await apiClient.get<AuthMeResponse>(
        "/api/v1/operator/auth/me",
      );
      return res.data;
    },
    // This is a one-shot routing call — don't refetch in the background.
    staleTime: Infinity,
    gcTime: 5 * 60 * 1000,
    retry: false,
  });
}
