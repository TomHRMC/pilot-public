/**
 * useResolveVariance — POST /api/v1/invoices/{payment_id}/resolve-variance
 *
 * Location: apps/web/src/features/invoices/hooks/useResolveVariance.ts
 *
 * CE-1 Part C — spec §4.2 / §5.1
 *
 * RULE: Uses apiClient (never raw fetch).
 * RULE: retry: false — never auto-retry a financial mutation.
 * RULE: onSuccess → invalidateQueries(['invoice', invoiceId]) so the banner
 *       re-evaluates (mirrors useRecordPayment.ts pattern).
 *
 * Endpoint verified in openapi.json (CE-1 Part C pre-work):
 *   POST /api/v1/invoices/{payment_id}/resolve-variance
 *   (Note: path is /invoices/ not /payments/ — OpenAPI is authoritative per Rule 1.2)
 *
 * 409 (already resolved) is handled by the caller (ResolveVarianceModal) per
 * spec §4.7 — the mutation's onError surfaces the error; the modal composes
 * the §16.4 409-and-refresh pattern (invalidate + close + notification).
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient, isAxiosError } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";

export type ResolveVarianceRequest =
  components["schemas"]["ResolveVarianceRequest"];

export type ResolveVariancePaymentResponse =
  components["schemas"]["PaymentResponse"];

export interface UseResolveVarianceOptions {
  invoiceId: string;
  paymentId: string;
  onSuccess?: (payment: ResolveVariancePaymentResponse) => void;
  onError?: (error: ResolveVarianceError) => void;
}

export type ResolveVarianceError =
  | { kind: "already_resolved"; status: 409; detail: string }
  | { kind: "validation"; status: 422; detail: string }
  | { kind: "network"; status: number | undefined; detail: string };

export function useResolveVariance({
  invoiceId,
  paymentId,
  onSuccess,
  onError,
}: UseResolveVarianceOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      payload: ResolveVarianceRequest,
    ): Promise<ResolveVariancePaymentResponse> => {
      const res = await apiClient.post<ResolveVariancePaymentResponse>(
        `/api/v1/invoices/${paymentId}/resolve-variance`,
        payload,
      );
      return res.data;
    },
    retry: false,
    onSuccess: (payment) => {
      void queryClient.invalidateQueries({
        queryKey: ["invoice", invoiceId],
      });
      onSuccess?.(payment);
    },
    onError: (error: unknown) => {
      let mapped: ResolveVarianceError;

      if (isAxiosError(error)) {
        const status = error.response?.status;
        const detail =
          (error.response?.data as { detail?: string })?.detail ??
          error.message;

        if (status === 409) {
          mapped = {
            kind: "already_resolved",
            status: 409,
            detail: detail || "This overpayment was already resolved.",
          };
        } else if (status === 422) {
          mapped = {
            kind: "validation",
            status: 422,
            detail: detail || "No overpayment to resolve.",
          };
        } else {
          mapped = {
            kind: "network",
            status,
            detail:
              "Could not submit resolution. Check your connection and try again.",
          };
        }
      } else {
        mapped = {
          kind: "network",
          status: undefined,
          detail:
            "Could not submit resolution. Check your connection and try again.",
        };
      }

      onError?.(mapped);
    },
  });
}
