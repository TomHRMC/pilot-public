"use client";

/**
 * useCreateCheckout — POST /api/v1/tenants/{tenant_id}/messaging/checkout
 *
 * Location: apps/web/src/features/messaging/hooks/useCreateCheckout.ts
 *
 * C-B9: Creates a Stripe Checkout Session for the one-time 10DLC setup charge.
 * Returns the Checkout URL for client-side redirect.
 *
 * RULE 2: uses apiClient, never raw fetch().
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { useAuth } from "@pilot/ui/auth";
import type { components } from "@pilot/shared-types";
import { PROVISIONING_STATUS_QUERY_KEY } from "./useProvisioningStatus";

type CheckoutResponse = components["schemas"]["CheckoutResponse"];

export function useCreateCheckout() {
  const { user } = useAuth();
  const tenantId = user?.tenantId;
  const queryClient = useQueryClient();

  return useMutation<CheckoutResponse, unknown, void>({
    mutationFn: async () => {
      if (!tenantId) throw new Error("No tenant ID");
      const res = await apiClient.post<CheckoutResponse>(
        `/api/v1/tenants/${tenantId}/messaging/checkout`,
        {},
        {
          headers: {
            "Idempotency-Key": `checkout-${tenantId}-${Date.now()}`,
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
