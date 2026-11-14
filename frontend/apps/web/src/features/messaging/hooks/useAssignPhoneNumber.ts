"use client";

/**
 * useAssignPhoneNumber — POST /api/v1/tenants/{tenant_id}/messaging/assign-number
 *
 * Location: apps/web/src/features/messaging/hooks/useAssignPhoneNumber.ts
 *
 * C-B9: Provisions the selected phone number via the carrier and transitions
 * the registration to number_assigned → active.
 *
 * Supports Idempotency-Key header.
 *
 * RULE 2: uses apiClient, never raw fetch().
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { useAuth } from "@pilot/ui/auth";
import type { components } from "@pilot/shared-types";
import { PROVISIONING_STATUS_QUERY_KEY } from "./useProvisioningStatus";

type AssignNumberRequest = components["schemas"]["AssignNumberRequest"];
type AssignNumberResponse = components["schemas"]["AssignNumberResponse"];

export function useAssignPhoneNumber() {
  const { user } = useAuth();
  const tenantId = user?.tenantId;
  const queryClient = useQueryClient();

  return useMutation<AssignNumberResponse, unknown, AssignNumberRequest>({
    mutationFn: async (payload) => {
      if (!tenantId) throw new Error("No tenant ID");
      const res = await apiClient.post<AssignNumberResponse>(
        `/api/v1/tenants/${tenantId}/messaging/assign-number`,
        payload,
        {
          headers: {
            "Idempotency-Key": `assign-${tenantId}-${Date.now()}`,
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
