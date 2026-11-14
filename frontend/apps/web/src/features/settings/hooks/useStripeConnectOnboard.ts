/**
 * useStripeConnectOnboard — UI-FIX-2F
 *
 * Location: apps/web/src/features/settings/hooks/useStripeConnectOnboard.ts
 *
 * Generates a Stripe Account Link URL for onboarding.
 * POST /api/v1/settings/billing/stripe-connect/onboard
 *
 * The caller (component) performs the browser redirect:
 *   window.location.href = data.account_link_url
 * This hook does NOT redirect itself.
 */

import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";

export type StripeConnectOnboardResponse =
  components["schemas"]["StripeConnectOnboardResponse"];

export function useStripeConnectOnboard() {
  return useMutation({
    mutationFn: async (): Promise<StripeConnectOnboardResponse> => {
      const res = await apiClient.post<StripeConnectOnboardResponse>(
        "/api/v1/settings/billing/stripe-connect/onboard",
      );
      return res.data;
    },
  });
}
