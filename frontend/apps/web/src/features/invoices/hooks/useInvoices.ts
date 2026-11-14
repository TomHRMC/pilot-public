/**
 * useInvoices — TanStack Query hook for invoices list
 *
 * Location: apps/web/src/features/invoices/hooks/useInvoices.ts
 *
 * RULE: Uses apiClient (never raw fetch).
 * RULE: Query key is ["invoices", { status, limit, offset, overdue, ... }].
 *
 * GET /api/v1/invoices/ supports:
 *   ?status=  — server-side status filter (DB codes: draft, issued, paid, void, writeoff)
 *   ?overdue=true — SD-06B: filter to invoices where due_at < now AND status NOT IN (paid, void, writeoff)
 *   ?customer_search= — UI-FIX-1C: ILIKE on customer.display_name
 *   ?issued_from= — UI-FIX-1C: invoice.issued_at >= date
 *   ?issued_to= — UI-FIX-1C: invoice.issued_at <= date
 * Response shape: { items, total, limit, offset } — paginated with total count.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

/** Actual DB invoice_status codes (confirmed MCP 2026-07-06) */
export type InvoiceStatusCode =
  | "draft"
  | "issued"
  | "paid"
  | "void"
  | "writeoff";

export interface InvoiceListItem {
  id: string;
  invoice_number: string;
  customer_id: string;
  /** FE-B24/B18: customer_name added to InvoiceSummary — display instead of truncated UUID */
  customer_name?: string | null;
  site_id: string;
  status_id: string;
  status_code: string;
  issued_at: string | null;
  due_at: string | null;
  /** FE-B27: total_cents added for invoice list Total column */
  total_cents?: number | null;
}

export interface InvoiceListResponse {
  items: InvoiceListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface UseInvoicesOptions {
  status?: string;
  limit?: number;
  offset?: number;
  /** SD-06B: When true, sends ?overdue=true to API — returns invoices past due_at, not paid/void/writeoff */
  overdue?: boolean;
  /** UI-FIX-1B: FIX-010 — filter invoices due before this date (YYYY-MM-DD); used by AR widget links */
  due_before?: string;
  /** UI-FIX-1C: Server-side customer name search — ILIKE on customer.display_name */
  customer_search?: string;
  /** UI-FIX-1C: Filter invoices issued on or after this date (YYYY-MM-DD) */
  issued_from?: string;
  /** UI-FIX-1C: Filter invoices issued on or before this date (YYYY-MM-DD) */
  issued_to?: string;
  /** UI-FIX-2D: exact UUID filter — when set, scopes results to this customer */
  customer_id?: string;
}

export const INVOICES_QUERY_KEY = (opts: UseInvoicesOptions) =>
  ["invoices", opts] as const;

export function useInvoices({
  status,
  limit = 50,
  offset = 0,
  overdue,
  due_before,
  customer_search,
  issued_from,
  issued_to,
  customer_id,
}: UseInvoicesOptions = {}) {
  return useQuery({
    queryKey: INVOICES_QUERY_KEY({
      status,
      limit,
      offset,
      overdue,
      due_before,
      customer_search,
      issued_from,
      issued_to,
      customer_id,
    }),
    queryFn: async (): Promise<InvoiceListResponse> => {
      const res = await apiClient.get("/api/v1/invoices/", {
        params: {
          ...(status ? { status } : {}),
          ...(overdue ? { overdue: true } : {}),
          ...(due_before ? { due_before } : {}),
          ...(customer_search?.trim()
            ? { customer_search: customer_search.trim() }
            : {}),
          ...(issued_from ? { issued_from } : {}),
          ...(issued_to ? { issued_to } : {}),
          ...(customer_id ? { customer_id } : {}),
          limit,
          offset,
        },
      });
      return res.data as InvoiceListResponse;
    },
    staleTime: 60_000,
  });
}
