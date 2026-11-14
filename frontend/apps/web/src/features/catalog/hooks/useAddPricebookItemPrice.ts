/**
 * useAddPricebookItemPrice — mutation for adding a new price version to a pricebook item
 *
 * Location: apps/web/src/features/catalog/hooks/useAddPricebookItemPrice.ts
 *
 * Endpoint: POST /api/v1/catalog/pricebook/{itemId}/price
 * Pattern: temporal versioning — creates a new price version
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { PricebookItemCurrentPrice } from "./usePricebook";
import { PRICEBOOK_QUERY_KEY } from "./usePricebook";

export interface AddPricebookItemPricePayload {
  unit_price_cents: number;
  effective_from: string; // ISO datetime — required
}

export function useAddPricebookItemPrice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      itemId,
      payload,
    }: {
      itemId: string;
      payload: AddPricebookItemPricePayload;
    }): Promise<PricebookItemCurrentPrice> => {
      const res = await apiClient.post(
        `/api/v1/catalog/pricebook/${itemId}/price`,
        payload,
      );
      return res.data as PricebookItemCurrentPrice;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PRICEBOOK_QUERY_KEY({}) });
    },
  });
}
