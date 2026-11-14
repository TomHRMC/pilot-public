/**
 * useInvoice — single invoice detail with nested lines
 *
 * Location: apps/web/src/features/invoices/hooks/useInvoice.ts
 *
 * RULE: Uses apiClient (never raw fetch).
 * RULE: Query key is ['invoice', invoiceId].
 *
 * GET /api/v1/invoices/{invoiceId} — verified in openapi_schema_map.md (FE-B22 pre-work).
 * Response: InvoiceResponse — includes nested lines[].
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

// TODO: replace with @pilot/shared-types InvoiceResponse when pnpm sync-api-types delivers this type
export interface PaymentSummaryEntry {
  id: string;
  amount_cents: number;
  paid_at: string | null;
  paid_via: string | null;
  psp_provider: string | null;
  customer_payment_comment: string | null;
  status_id: string;
  // CE-1 Part C — overpayment variance tracking (spec §5.3)
  amount_variance_cents: number;
  variance_resolution: string | null;
  variance_resolution_note: string | null;
  variance_resolved_at: string | null;
  variance_resolved_by_user_id: string | null;
}

export interface InvoiceLineResponse {
  id: string;
  invoice_id: string;
  source_type: string | null;
  source_id: string | null;
  description: string;
  quantity: number;
  unit_price_cents: number;
  subtotal_cents: number;
  tax_amount_cents: number;
  total_cents: number;
  sort_order: number;
}

export interface InvoiceResponse {
  id: string;
  tenant_id: string;
  invoice_number: string;
  customer_id: string;
  site_id: string | null;
  status_id: string;
  status_code: string;
  quote_id: string | null;
  job_id: string | null;
  idempotency_key: string | null;
  issued_at: string | null;
  due_at: string | null;
  subtotal_cents: number;
  tax_cents: number;
  total_cents: number;
  balance_due_cents: number;
  currency: string;
  customer_notes: string | null;
  terms_and_conditions: string | null;
  pdf_object_key: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  updated_by: string | null;
  lines: InvoiceLineResponse[];
  payments: PaymentSummaryEntry[];
}

export const INVOICE_QUERY_KEY = (invoiceId: string) =>
  ["invoice", invoiceId] as const;

export function useInvoice(invoiceId: string | null | undefined) {
  return useQuery({
    queryKey: INVOICE_QUERY_KEY(invoiceId ?? ""),
    queryFn: async (): Promise<InvoiceResponse> => {
      const res = await apiClient.get(`/api/v1/invoices/${invoiceId}`);
      return res.data as InvoiceResponse;
    },
    enabled: !!invoiceId,
    staleTime: 60_000,
  });
}
