/**
 * useRecordPayment — POST /api/v1/invoices/{invoiceId}/record-payment
 *
 * Location: apps/web/src/features/invoices/hooks/useRecordPayment.ts
 *
 * RULE: Uses apiClient (never raw fetch).
 *
 * POST /api/v1/invoices/{invoiceId}/record-payment — verified in openapi_schema_map.md (FE-B22 pre-work).
 * Required fields: amount_cents, paid_via, payment_method_id, payment_status_id
 *
 * Pre-work finding:
 *  - payment_method table is empty, no lookup endpoint exists
 *  - payment_method_id uses sentinel UUID "00000000-0000-0000-0000-000000000001" (manual payment)
 *  - payment_status "succeeded" UUID: "fa70374c-513a-4cc3-baca-22a54a594a4d"
 *
 * onSuccess: invalidates ['invoice', invoiceId] to refresh balance and payment history
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient, getApiProblem, type ApiProblem } from "@pilot/shared-api";

// Sentinel UUIDs from DB pre-work — payment_method table empty, no lookup endpoint
export const MANUAL_PAYMENT_METHOD_ID = "00000000-0000-0000-0000-000000000001";
export const PAYMENT_STATUS_SUCCEEDED_ID =
  "fa70374c-513a-4cc3-baca-22a54a594a4d";

export interface PaymentRecordPayload {
  amount_cents: number;
  paid_via: string;
  payment_method_id: string;
  payment_status_id: string;
  paid_at?: string | null;
  reference?: string | null;
  idempotency_key?: string | null;
  comment?: string | null;
}

export interface PaymentResponse {
  id: string;
  invoice_id: string;
  tenant_id: string;
  amount_cents: number;
  paid_via: string;
  balance_due_cents: number;
  amount_variance_cents: number;
  status_id: string;
  paid_at: string;
  idempotency_key: string | null;
  created_at: string;
}

export interface UseRecordPaymentOptions {
  invoiceId: string;
  onSuccess?: (payment: PaymentResponse) => void;
  onError?: (problem: ApiProblem) => void;
}

export function useRecordPayment({
  invoiceId,
  onSuccess,
  onError,
}: UseRecordPaymentOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      payload: PaymentRecordPayload,
    ): Promise<PaymentResponse> => {
      const res = await apiClient.post(
        `/api/v1/invoices/${invoiceId}/record-payment`,
        payload,
      );
      return res.data as PaymentResponse;
    },
    onSuccess: (payment) => {
      void queryClient.invalidateQueries({ queryKey: ["invoice", invoiceId] });
      onSuccess?.(payment);
    },
    onError: (error) => {
      const problem = getApiProblem(error);
      onError?.(problem);
    },
  });
}
