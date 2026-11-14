/**
 * useSetMarkup — mutation hook for setting a markup version (temporal supersession)
 *
 * Location: apps/web/src/features/catalog/hooks/useSetMarkup.ts
 *
 * Endpoint: POST /api/v1/settings/markups
 * Pattern: temporal supersession — always POST to update; never PATCH/PUT
 * Field name: job_expense_category_code (NOT category_code)
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { TenantMarkupVersion } from "./useMarkups";
import { MARKUPS_QUERY_KEY } from "./useMarkups";

export interface SetMarkupPayload {
  job_expense_category_code: string;
  markup_pct: number;
  effective_from: string; // ISO datetime — required by backend schema
  markup_amt_cents?: number | null;
}

export function useSetMarkup() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      payload: SetMarkupPayload,
    ): Promise<TenantMarkupVersion> => {
      const res = await apiClient.post("/api/v1/settings/markups", payload);
      return res.data as TenantMarkupVersion;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: MARKUPS_QUERY_KEY });
    },
  });
}
