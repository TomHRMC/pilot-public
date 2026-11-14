"use client";

/**
 * useInitiateProvisioning — POST /api/v1/tenants/{tenant_id}/messaging/provision
 *
 * Location: apps/web/src/features/messaging/hooks/useInitiateProvisioning.ts
 *
 * C-B9: Initiates or restarts 10DLC provisioning. Creates/updates the
 * tenant_messaging_registration row with entity_type and status='quoting'.
 * Upserts tenant_10dlc_profile with brand data.
 *
 * Supports Idempotency-Key header (24h TTL).
 *
 * RULE 2: uses apiClient, never raw fetch().
 * RULE 12: TanStack Query v5 object-form.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { useAuth } from "@pilot/ui/auth";
import type { components } from "@pilot/shared-types";
import { PROVISIONING_STATUS_QUERY_KEY } from "./useProvisioningStatus";

type ProvisionRequest = components["schemas"]["ProvisionRequest"];
type ProvisionResponse = components["schemas"]["ProvisionResponse"];

export function useInitiateProvisioning() {
  const { user } = useAuth();
  const tenantId = user?.tenantId;
  const queryClient = useQueryClient();

  return useMutation<ProvisionResponse, unknown, ProvisionRequest>({
    mutationFn: async (payload) => {
      if (!tenantId) throw new Error("No tenant ID");
      const res = await apiClient.post<ProvisionResponse>(
        `/api/v1/tenants/${tenantId}/messaging/provision`,
        payload,
        {
          headers: {
            "Idempotency-Key": `provision-${tenantId}-${Date.now()}`,
          },
        },
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
