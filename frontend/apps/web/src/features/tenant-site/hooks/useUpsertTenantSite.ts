"use client";

/**
 * useUpsertTenantSite — PUT /api/v1/tenant-site
 *
 * Location: apps/web/src/features/tenant-site/hooks/useUpsertTenantSite.ts
 *
 * C-B16: Upserts the tenant's site draft (site_kind, slug, display/contact
 * overrides, show_full_address). Sends an Idempotency-Key header (UUID v4).
 *
 * RULE 2: uses apiClient, never raw fetch().
 * RULE 33: TanStack Query v5 object-form; invalidates ["tenant-site", "config"]
 *          onSettled so the form re-populates fresh data after save.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";
import { tenantSiteKeys } from "./tenantSiteQueryKeys";

type TenantSiteUpsertRequest = components["schemas"]["TenantSiteUpsertRequest"];
type TenantSiteResponse = components["schemas"]["TenantSiteResponse"];

export function useUpsertTenantSite() {
  const queryClient = useQueryClient();

  return useMutation<TenantSiteResponse, unknown, TenantSiteUpsertRequest>({
    mutationFn: async (payload) => {
      const res = await apiClient.put<TenantSiteResponse>(
        "/api/v1/tenant-site",
        payload,
        {
          headers: {
            "Idempotency-Key":
              typeof crypto !== "undefined" && crypto.randomUUID
                ? crypto.randomUUID()
                : `idem-${Date.now()}-${Math.random().toString(36).slice(2)}`,
          },
        },
      );
      return res.data;
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: tenantSiteKeys.config });
    },
  });
}
