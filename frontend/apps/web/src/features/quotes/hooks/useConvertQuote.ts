/**
 * useConvertQuote — mutation hook to convert an accepted quote to a job
 *
 * Location: apps/web/src/features/quotes/hooks/useConvertQuote.ts
 *
 * Endpoint: POST /api/v1/quotes/{quoteId}/convert (returns 201)
 * Permission: quotes.edit (owner/operator)
 *
 * Returns: QuoteConvertResponse { job_id, quote_id, quote_status, job_status_id, quote_version_id }
 * onSuccess: invalidates ['quotes', quoteId, 'detail'] + ['quotes'], navigates to /schedule
 *
 * NOTE: Once FE-B21 builds the jobs module, update navigation to /jobs/[job_id].
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { apiClient } from "@pilot/shared-api";

export type QuoteConvertResponse = {
  job_id: string;
  quote_id: string;
  quote_status: string;
  job_status_id: string;
  quote_version_id: string | null;
};

export function useConvertQuote(quoteId: string) {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: async (): Promise<QuoteConvertResponse> => {
      const res = await apiClient.post(`/api/v1/quotes/${quoteId}/convert`);
      return res.data as QuoteConvertResponse;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["quotes", quoteId, "detail"],
      });
      void queryClient.invalidateQueries({ queryKey: ["quotes"] });
      // Navigate to dispatch board where new job will appear
      // TODO: FE-B21 — update to /jobs/[job_id] once jobs module is built
      router.push("/schedule");
    },
  });
}
