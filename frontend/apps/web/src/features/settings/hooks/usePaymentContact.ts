/**
 * usePaymentContact — STRIPE-CONNECT-1-C (B5)
 *
 * Location: apps/web/src/features/settings/hooks/usePaymentContact.ts
 *
 * TanStack Query v5 hook for the tenant billing-payment-contact fields.
 *   GET  /api/v1/settings/billing/payment-contact
 *   PATCH /api/v1/settings/billing/payment-contact
 *
 * Authed surface → apiClient (never raw fetch). Per-submission Idempotency-Key.
 * Invalidates the query in onSettled (rules §33).
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";

type PaymentContactResponse = components["schemas"]["PaymentContactResponse"];
type PaymentContactUpdateRequest =
  components["schemas"]["PaymentContactUpdateRequest"];

export const PAYMENT_CONTACT_QUERY_KEY = ["payment-contact"] as const;

export function usePaymentContact() {
  return useQuery({
    queryKey: PAYMENT_CONTACT_QUERY_KEY,
    queryFn: async (): Promise<PaymentContactResponse> => {
      const res = await apiClient.get<PaymentContactResponse>(
        "/api/v1/settings/billing/payment-contact",
      );
      return res.data;
    },
    staleTime: 30_000,
  });
}

export function useUpdatePaymentContact() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (
      payload: PaymentContactUpdateRequest,
    ): Promise<PaymentContactResponse> => {
      const res = await apiClient.patch<PaymentContactResponse>(
        "/api/v1/settings/billing/payment-contact",
        payload,
        {
          headers: {
            // Per-submission idempotency key (fresh uuid per save attempt)
            "Idempotency-Key": crypto.randomUUID(),
          },
        },
      );
      return res.data;
    },
    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: PAYMENT_CONTACT_QUERY_KEY,
      });
    },
  });
}
