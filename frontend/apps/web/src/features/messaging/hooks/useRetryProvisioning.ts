"use client";

/**
 * useRetryProvisioning — POST /api/v1/tenants/{tenant_id}/messaging/retry
 *
 * Location: apps/web/src/features/messaging/hooks/useRetryProvisioning.ts
 *
 * C-B9: Retries from payment_failed back to quoting. Does NOT re-charge.
 * Re-fetches the quote (in case carrier fees changed).
 *
 * RULE 2: uses apiClient, never raw fetch().
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { useAuth } from "@pilot/ui/auth";
import type { components } from "@pilot/shared-types";
import { PROVISIONING_STATUS_QUERY_KEY } from "./useProvisioningStatus";

type RetryResponse = components["schemas"]["RetryResponse"];

export function useRetryProvisioning() {
  const { user } = useAuth();
  const tenantId = user?.tenantId;
  const queryClient = useQueryClient();

  return useMutation<RetryResponse, unknown, void>({
    mutationFn: async () => {
      if (!tenantId) throw new Error("No tenant ID");
      const res = await apiClient.post<RetryResponse>(
        `/api/v1/tenants/${tenantId}/messaging/retry`,
        {},
      );
      return res.data;
    },
    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: PROVISIONING_STATUS_QUERY_KEY,
      });
    },
  });
}
