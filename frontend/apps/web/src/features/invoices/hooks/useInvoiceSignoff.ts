/**
 * useInvoiceSignoff — GET /api/v1/invoices/{invoice_id}/signoff
 *
 * Location: apps/web/src/features/invoices/hooks/useInvoiceSignoff.ts
 *
 * CE-1 Part C — spec §2.2 / §5.1
 *
 * RULE: Uses apiClient (never raw fetch).
 * RULE: Query key is ['invoice', invoiceId, 'signoff'] — sibling to useInvoice's
 *       ['invoice', invoiceId]; the card manages its own refetch.
 * RULE: staleTime: 0 so a re-mount (tab return) always refetches a fresh
 *       presigned signature_url (1h TTL per §D.3).
 * RULE: retry: false — a failed presigned-URL fetch shouldn't hammer.
 *
 * Endpoint verified in openapi_schema_map.md (CE-1 Part C pre-work).
 * Response: InvoiceSignoffDetailResponse — { signoff: InvoiceSignoffResponse | null, superseded_count: number }
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";

export type InvoiceSignoffResponse =
  components["schemas"]["InvoiceSignoffResponse"];

export type InvoiceSignoffDetailResponse =
  components["schemas"]["InvoiceSignoffDetailResponse"];

export const SIGNOFF_QUERY_KEY = (invoiceId: string) =>
  ["invoice", invoiceId, "signoff"] as const;

export interface UseInvoiceSignoffResult {
  signoff: InvoiceSignoffResponse | null;
  supersededCount: number;
}

export function useInvoiceSignoff(invoiceId: string | null | undefined) {
  return useQuery({
    queryKey: SIGNOFF_QUERY_KEY(invoiceId ?? ""),
    queryFn: async (): Promise<UseInvoiceSignoffResult> => {
      const res = await apiClient.get<InvoiceSignoffDetailResponse>(
        `/api/v1/invoices/${invoiceId}/signoff`,
      );
      const data = res.data;
      return {
        signoff: data.signoff ?? null,
        supersededCount: data.superseded_count ?? 0,
      };
    },
    enabled: !!invoiceId,
    retry: false,
    staleTime: 0,
  });
}
