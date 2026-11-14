"use client";

/**
 * useSlugAvailability — GET /api/v1/tenant-site/slug-availability?slug=
 *
 * Location: apps/web/src/features/tenant-site/hooks/useSlugAvailability.ts
 *
 * C-B16: Live slug availability feedback. The component debounces the input
 * (300 ms per web spec §8) and passes the debounced value here. The hook is
 * enabled only when the slug is non-empty.
 *
 * RULE 2: uses apiClient, never raw fetch().
 * RULE 33: TanStack Query v5 object-form; retry: false; staleTime: 0
 *          (always refetch on new value — slug availability is real-time).
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";
import { tenantSiteKeys } from "./tenantSiteQueryKeys";

type SlugAvailabilityResponse =
  components["schemas"]["SlugAvailabilityResponse"];

export function useSlugAvailability(slug: string) {
  return useQuery<SlugAvailabilityResponse>({
    queryKey: tenantSiteKeys.slugAvailability(slug),
    queryFn: async () => {
      const res = await apiClient.get<SlugAvailabilityResponse>(
        "/api/v1/tenant-site/slug-availability",
        { params: { slug } },
      );
      return res.data;
    },
    enabled: slug.length > 0,
    staleTime: 0,
    retry: false,
  });
}
