/**
 * useSendInvoice — POST /api/v1/invoices/{invoiceId}/send
 *
 * Location: apps/web/src/features/invoices/hooks/useSendInvoice.ts
 *
 * RULE: Uses apiClient (never raw fetch).
 * RULE: always-preview-before-send — this hook is ONLY called from the
 *       SendInvoicePreviewModal "Confirm Send" button handler. Never pre-emptively.
 *
 * POST /api/v1/invoices/{invoiceId}/send — verified in openapi_schema_map.md (FE-B22 pre-work).
 * Returns: InvoicePublicLinkResponse (signed_token, expires_at, etc.)
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient, getApiProblem, type ApiProblem } from "@pilot/shared-api";

export interface InvoicePublicLinkResponse {
  id: string;
  tenant_id: string;
  invoice_id: string;
  contact_id: string;
  signed_token: string;
  expires_at: string;
  max_uses: number;
  used_count: number;
  status: string;
  last_used_at: string | null;
  created_at: string;
}

export interface UseSendInvoiceOptions {
  invoiceId: string;
  onSuccess?: (result: InvoicePublicLinkResponse) => void;
  onError?: (problem: ApiProblem) => void;
}

export function useSendInvoice({
  invoiceId,
  onSuccess,
  onError,
}: UseSendInvoiceOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (): Promise<InvoicePublicLinkResponse> => {
      const res = await apiClient.post(`/api/v1/invoices/${invoiceId}/send`);
      return res.data as InvoicePublicLinkResponse;
    },
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ["invoice", invoiceId] });
      onSuccess?.(result);
    },
    onError: (error) => {
      const problem = getApiProblem(error);
      onError?.(problem);
    },
  });
}
