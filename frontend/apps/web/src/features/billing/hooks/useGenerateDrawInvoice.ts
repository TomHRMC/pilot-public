/**
 * useGenerateDrawInvoice — POST /api/v1/payment-schedules/{schedule_id}/lines/{line_id}/generate-invoice
 *
 * Location: apps/web/src/features/billing/hooks/useGenerateDrawInvoice.ts
 *
 * BILLING-B1 Part B — Payment Schedule Builder.
 *
 * Generates the draw's `progress` invoice. Sends an Idempotency-Key header
 * (mirror useCreateInvoice pattern) so a retried generation returns the same
 * invoice. Returns 409 if the draw is already invoiced (Integrity rule 4) —
 * the caller surfaces this via <NotificationBanner> fault severity (NOT the
 * staleness dialog — this is a rule-4 conflict, not a staleness conflict).
 *
 * RULE: Uses apiClient (never raw fetch). Types from @pilot/shared-types.
 * RULE: Invalidate (don't hand-patch) in onSettled — Rule 12 / §33.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient, isAxiosError } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";
import { paymentScheduleKeys } from "./usePaymentSchedule";

export type InvoiceResponse = components["schemas"]["InvoiceResponse"];

export interface UseGenerateDrawInvoiceOptions {
  onSuccess?: (invoice: InvoiceResponse) => void;
  /** Called when the backend returns 409 (draw already invoiced) with the RFC 7807 detail */
  onAlreadyInvoiced?: (detail: string) => void;
  onError?: (error: unknown) => void;
}

export function useGenerateDrawInvoice(
  options: UseGenerateDrawInvoiceOptions = {},
) {
  const queryClient = useQueryClient();
  const { onSuccess, onAlreadyInvoiced, onError } = options;

  return useMutation({
    mutationFn: async (params: {
      scheduleId: string;
      lineId: string;
    }): Promise<InvoiceResponse> => {
      // Stable per-line idempotency key — a retried generation returns the
      // same invoice. Keyed on schedule+line for retry safety.
      const idempotencyKey = `draw-gen-${params.scheduleId}-${params.lineId}`;
      try {
        const res = await apiClient.post(
          `/api/v1/payment-schedules/${params.scheduleId}/lines/${params.lineId}/generate-invoice`,
          { idempotency_key: idempotencyKey },
          { headers: { "Idempotency-Key": idempotencyKey } },
        );
        return res.data as InvoiceResponse;
      } catch (err) {
        if (isAxiosError(err) && err.response?.status === 409) {
          const detail =
            (err.response.data as { detail?: string } | undefined)?.detail ??
            "This draw already has an invoice. Void the existing invoice before re-generating.";
          onAlreadyInvoiced?.(detail);
        }
        throw err;
      }
    },
    onSuccess: (invoice) => {
      onSuccess?.(invoice);
    },
    onError: (error) => {
      // 409 is already handled via onAlreadyInvoiced; only surface other errors
      if (!isAxiosError(error) || error.response?.status !== 409) {
        onError?.(error);
      }
    },
    onSettled: (_data, _error, variables) => {
      void queryClient.invalidateQueries({
        queryKey: paymentScheduleKeys.detail(variables.scheduleId),
      });
    },
  });
}
