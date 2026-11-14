/**
 * useSubmitForApproval — mutation hook to submit a quote for owner approval
 *
 * Location: apps/web/src/features/quotes/hooks/useSubmitForApproval.ts
 *
 * Endpoint: POST /api/v1/quotes/{quoteId}/submit-for-approval
 * Permission: quote.submit_for_approval (tech role)
 * onSuccess: invalidates ['quotes', quoteId, 'detail'] + ['quotes']
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export function useSubmitForApproval(quoteId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const res = await apiClient.post(
        `/api/v1/quotes/${quoteId}/submit-for-approval`,
      );
      return res.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["quotes", quoteId, "detail"],
      });
      void queryClient.invalidateQueries({ queryKey: ["quotes"] });
    },
  });
}
