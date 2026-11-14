"use client";

/**
 * useUnpublishTenantSite — POST /api/v1/tenant-site/unpublish
 *
 * Location: apps/web/src/features/tenant-site/hooks/useUnpublishTenantSite.ts
 *
 * C-B16: Unpublishes the tenant's compliance site. Does NOT clear the
 * `website` field on the 10DLC profile (§G-8). The response includes a
 * `warning` string the UI surfaces to the tenant.
 *
 * RULE 2: uses apiClient, never raw fetch().
 * RULE 33: TanStack Query v5 object-form; invalidates ["tenant-site", "config"]
 *          onSettled.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";
import { tenantSiteKeys } from "./tenantSiteQueryKeys";

type UnpublishResponse = components["schemas"]["UnpublishResponse"];

export function useUnpublishTenantSite() {
  const queryClient = useQueryClient();

  return useMutation<UnpublishResponse, unknown, void>({
    mutationFn: async () => {
      const res = await apiClient.post<UnpublishResponse>(
        "/api/v1/tenant-site/unpublish",
        {},
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
