"use client";

/**
 * useTenantSite — GET /api/v1/tenant-site
 *
 * Location: apps/web/src/features/tenant-site/hooks/useTenantSite.ts
 *
 * C-B16: Fetches the tenant's site configuration + status + computed URL +
 * effective defaults merged from the 10DLC profile. Returns
 * `{ configured: false, defaults: {...} }` when no row exists — never 404.
 *
 * RULE 2: uses apiClient, never raw fetch().
 * RULE 33: TanStack Query v5 object-form; retry: false; staleTime: 60_000
 *          (settings reference data — don't hammer the API on every mount).
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";
import { tenantSiteKeys } from "./tenantSiteQueryKeys";

type TenantSiteGetResponse = components["schemas"]["TenantSiteGetResponse"];

export function useTenantSite() {
  return useQuery<TenantSiteGetResponse>({
    queryKey: tenantSiteKeys.config,
    queryFn: async () => {
      const res = await apiClient.get<TenantSiteGetResponse>(
        "/api/v1/tenant-site",
      );
      return res.data;
    },
    retry: false,
    staleTime: 60_000,
  });
}
