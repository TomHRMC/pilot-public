/**
 * useAddQuoteLine — mutation hook to add a line item to an existing quote
 *
 * Location: apps/web/src/features/quotes/hooks/useAddQuoteLine.ts
 *
 * Endpoint: POST /api/v1/quotes/{quoteId}/lines
 *
 * IMPORTANT: QuoteLineCreate requires:
 *   - position (int): ordinal position in the list
 *   - qco_line_type_id (UUID): from qco_line_type table (labor/material/misc/discount)
 *   - description (string)
 *
 * onSuccess: invalidates ['quotes', quoteId, 'detail']
 *
 * NOTE: No DELETE/PATCH endpoints exist for quote lines — add-only.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export type AddQuoteLineInput = {
  position: number;
  qco_line_type_id: string;
  description: string;
  quantity: number;
  unit_price_cents: number;
  customer_visible?: boolean;
  pricebook_item_id?: string | null;
  unit?: string | null;
};

export function useAddQuoteLine(quoteId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: AddQuoteLineInput) => {
      const res = await apiClient.post(`/api/v1/quotes/${quoteId}/lines`, {
        ...data,
        customer_visible: data.customer_visible ?? true,
      });
      return res.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["quotes", quoteId, "detail"],
      });
    },
  });
}
