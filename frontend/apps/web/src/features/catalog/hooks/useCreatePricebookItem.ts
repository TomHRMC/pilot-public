/**
 * useCreatePricebookItem — mutation hook for creating a pricebook item
 *
 * Location: apps/web/src/features/catalog/hooks/useCreatePricebookItem.ts
 *
 * Endpoint: POST /api/v1/catalog/pricebook
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { PricebookItem } from "./usePricebook";
import { PRICEBOOK_QUERY_KEY } from "./usePricebook";

export interface CreatePricebookItemPayload {
  sku: string;
  name: string;
  description?: string | null;
  uom_id?: string | null;
  taxability_code?: string | null;
  initial_price_cents: number;
  effective_from?: string | null;
}

export function useCreatePricebookItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      payload: CreatePricebookItemPayload,
    ): Promise<PricebookItem> => {
      const res = await apiClient.post("/api/v1/catalog/pricebook", payload);
      return res.data as PricebookItem;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PRICEBOOK_QUERY_KEY({}) });
    },
  });
}
