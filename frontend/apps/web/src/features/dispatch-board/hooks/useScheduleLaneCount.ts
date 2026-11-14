/**
 * useScheduleLaneCount — Returns effective schedule lane count for the tenant
 *
 * Location: apps/web/src/features/dispatch-board/hooks/useScheduleLaneCount.ts
 *
 * Reads schedule_lanes from the active subscription tier.
 * Note: tenant_product_feature_override add-on lanes are not yet exposed via
 * the subscription-tiers API. When that endpoint is available, this hook
 * should sum base tier schedule_lanes + any override lanes.
 * TODO: Add override lane resolution when GET /api/v1/tenants/{id}/overrides exposes it.
 *
 * Per batch-mkt-b11-dispatch-react-engr-prompt.md §Task 1
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient, isAxiosError } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";

type SubscriptionTiersListResponse =
  components["schemas"]["SubscriptionTiersListResponse"];

export const SCHEDULE_LANE_COUNT_QUERY_KEY = [
  "subscription-lane-count",
] as const;

/** Default lane count if API is unavailable or no active tier found */
const FALLBACK_LANE_COUNT = 5;

/**
 * useScheduleLaneCount
 *
 * Returns the effective schedule lane count from the active subscription tier.
 * Uses `staleTime: 5 min` — lane count rarely changes between page loads.
 * `retry: false` — fail fast; caller shows ErrorState.
 */
export function useScheduleLaneCount(): {
  laneCount: number;
  isLoading: boolean;
  isError: boolean;
  /** PLP-FIX-9 (INV-BUG-10): true when the subscription-tiers call 403s
   * (subscription.view gate — owner-only). Caller degrades to default lanes. */
  isForbidden: boolean;
} {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: SCHEDULE_LANE_COUNT_QUERY_KEY,
    queryFn: async () => {
      const res = await apiClient.get<SubscriptionTiersListResponse>(
        "/api/v1/subscription-tiers/",
      );
      return res.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: false,
  });

  // PLP-FIX-9 (INV-BUG-10): detect 403 (subscription.view gate — owner-only).
  // Non-owner roles degrade to default-lane rendering, never a full-page error.
  const isForbidden =
    isError && isAxiosError(error) && error.response?.status === 403;

  // Find the active tier and read schedule_lanes
  const activeTier = Array.isArray(data?.tiers)
    ? data.tiers.find((t) => t.is_active)
    : null;

  const laneCount = activeTier?.schedule_lanes ?? FALLBACK_LANE_COUNT;

  return { laneCount, isLoading, isError, isForbidden };
}
