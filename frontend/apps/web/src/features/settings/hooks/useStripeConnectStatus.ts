/**
 * useStripeConnectStatus — UI-FIX-2F
 *
 * Location: apps/web/src/features/settings/hooks/useStripeConnectStatus.ts
 *
 * Fetches Stripe Connect account status.
 * GET /api/v1/settings/billing/stripe-connect/status
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";

export type StripeConnectStatusResponse =
  components["schemas"]["StripeConnectStatusResponse"];

export const STRIPE_CONNECT_STATUS_QUERY_KEY = [
  "stripe-connect-status",
] as const;

export function useStripeConnectStatus() {
  return useQuery({
    queryKey: STRIPE_CONNECT_STATUS_QUERY_KEY,
    queryFn: async (): Promise<StripeConnectStatusResponse> => {
      const res = await apiClient.get<StripeConnectStatusResponse>(
        "/api/v1/settings/billing/stripe-connect/status",
      );
      return res.data;
    },
    staleTime: 30_000,
  });
}
