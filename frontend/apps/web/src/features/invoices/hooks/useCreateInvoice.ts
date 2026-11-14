/**
 * useCreateInvoice — POST /api/v1/invoices/
 *
 * Location: apps/web/src/features/invoices/hooks/useCreateInvoice.ts
 *
 * RULE: Uses apiClient (never raw fetch).
 * RULE: 412 Precondition Required MUST open TaxSetupSubFlowModal, NOT surface a generic error.
 *
 * POST /api/v1/invoices/ — verified in openapi_schema_map.md (FE-B22 pre-work).
 * On 412: calls onTaxSetupRequired callback with response detail
 * On 201: calls onSuccess with created InvoiceResponse
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient, isAxiosError } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";
import type { InvoiceResponse } from "./useInvoice";

export interface InvoiceCreatePayload {
  quote_id?: string | null;
  job_id?: string | null;
  customer_notes?: string | null;
  terms_and_conditions?: string | null;
  due_at?: string | null;
  issued_at?: string | null;
  idempotency_key?: string | null;
  // B20 fields — added FE-B29 (verified in openapi.json InvoiceCreate schema)
  customer_id?: string | null;
  site_id?: string | null;
  payment_terms?: string | null; // 'due_on_receipt' | 'net_15' | 'net_30' | 'custom_date'
  billing_mode?: string; // 'line_item' | 'progress' (default 'line_item')
  progress_pct?: number | null; // 0–100 when billing_mode='progress'
  internal_memo?: string | null;
  // PLP-FIX-2 / FE-B29-1: custom ad-hoc lines (backend defaults qco_line_type to 'misc' by code)
  line_items?: components["schemas"]["InvoiceLineItemCreate"][] | null;
}

export interface UseCreateInvoiceOptions {
  onTaxSetupRequired: (detail: string) => void;
  onSuccess?: (invoice: InvoiceResponse) => void;
}

export function useCreateInvoice({
  onTaxSetupRequired,
  onSuccess,
}: UseCreateInvoiceOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      payload: InvoiceCreatePayload,
    ): Promise<InvoiceResponse> => {
      try {
        const res = await apiClient.post("/api/v1/invoices/", payload);
        return res.data as InvoiceResponse;
      } catch (err) {
        if (isAxiosError(err) && err.response?.status === 412) {
          // 412 must be caught here — not surfaced as a generic error
          const detail =
            (err.response.data as { detail?: string } | undefined)?.detail ??
            "Tax rates must be configured before creating invoices.";
          onTaxSetupRequired(detail);
          // Return a sentinel to signal interception (caller ignores this)
          throw err;
        }
        throw err;
      }
    },
    onSuccess: (invoice) => {
      void queryClient.invalidateQueries({ queryKey: ["invoices"] });
      onSuccess?.(invoice);
    },
  });
}
