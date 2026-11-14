/**
 * useStripeConnectDisconnect — UI-FIX-2F
 *
 * Location: apps/web/src/features/settings/hooks/useStripeConnectDisconnect.ts
 *
 * Disconnects the Stripe connected account.
 * DELETE /api/v1/settings/billing/stripe-connect
 *
 * On success: invalidates STRIPE_CONNECT_STATUS_QUERY_KEY so the
 * status card re-fetches immediately and transitions to Disconnected state.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";
import { STRIPE_CONNECT_STATUS_QUERY_KEY } from "./useStripeConnectStatus";

export type StripeConnectDisconnectResponse =
  components["schemas"]["StripeConnectDisconnectResponse"];

export function useStripeConnectDisconnect() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (): Promise<StripeConnectDisconnectResponse> => {
      const res = await apiClient.delete<StripeConnectDisconnectResponse>(
        "/api/v1/settings/billing/stripe-connect",
      );
      return res.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: STRIPE_CONNECT_STATUS_QUERY_KEY,
      });
    },
  });
}
