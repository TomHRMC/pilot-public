/**
 * useUpdatePricebookItem — mutation hook for updating pricebook item metadata
 *
 * Location: apps/web/src/features/catalog/hooks/useUpdatePricebookItem.ts
 *
 * Endpoint: PATCH /api/v1/catalog/pricebook/{itemId}
 * Note: sku is intentionally NOT in the request body — it is immutable after creation.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { PricebookItem } from "./usePricebook";
import { PRICEBOOK_QUERY_KEY } from "./usePricebook";

export interface UpdatePricebookItemPayload {
  name?: string | null;
  description?: string | null;
  taxability_code?: string | null;
  is_active?: boolean | null;
}

export function useUpdatePricebookItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      itemId,
      payload,
    }: {
      itemId: string;
      payload: UpdatePricebookItemPayload;
    }): Promise<PricebookItem> => {
      const res = await apiClient.patch(
        `/api/v1/catalog/pricebook/${itemId}`,
        payload,
      );
      return res.data as PricebookItem;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PRICEBOOK_QUERY_KEY({}) });
    },
  });
}
