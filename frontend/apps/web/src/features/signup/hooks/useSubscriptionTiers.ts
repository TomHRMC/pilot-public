/**
 * useSubscriptionTiers — TanStack Query hook for subscription tiers
 *
 * Location: apps/web/src/features/signup/hooks/useSubscriptionTiers.ts
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type {
  SubscriptionTiersListResponse,
  SubscriptionTierAPI,
} from "../types";

export const SUBSCRIPTION_TIERS_QUERY_KEY = ["subscription-tiers"] as const;

/** Recommend tier by business size */
export function getRecommendedTierName(
  businessSize: string | undefined,
): string {
  switch (businessSize) {
    case "solo":
    case "small":
      return "starter";
    case "medium":
      return "professional";
    case "large":
      return "enterprise";
    default:
      return "starter";
  }
}

export function useSubscriptionTiers() {
  return useQuery({
    queryKey: SUBSCRIPTION_TIERS_QUERY_KEY,
    queryFn: async (): Promise<SubscriptionTierAPI[]> => {
      const response = await apiClient.get<SubscriptionTiersListResponse>(
        "/api/v1/subscription-tiers",
      );
      return response.data.tiers.filter((t) => t.is_active);
    },
    staleTime: 5 * 60 * 1000, // 5 min — tier list rarely changes
  });
}
