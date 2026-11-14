/**
 * useSignoffContext — TanStack Query wrapper for GET /api/v1/jobs/{job_id}/signoff-context
 *
 * Location: apps/mobile/features/jobs/hooks/useSignoffContext.ts
 *
 * Fetches the job's signable invoices (status issued/partial) for the
 * InvoiceSignoffSection (S1) entry point. Auth: jobs.view (techs hold this).
 *
 * Per batch-ce-1-mobile-ui-design-spec.md §8.1 and batch-ce-1-design.md §D.1.
 */

import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";

type SignoffContextResponse = components["schemas"]["SignoffContextResponse"];

export const SIGNOFF_CONTEXT_QUERY_KEY = "job-signoff-context" as const;

export interface UseSignoffContextReturn {
  data: SignoffContextResponse | undefined;
  isPending: boolean;
  isError: boolean;
  refetch: () => void;
}

export function useSignoffContext(jobId: string): UseSignoffContextReturn {
  const { data, isPending, isError, refetch } = useQuery({
    queryKey: [SIGNOFF_CONTEXT_QUERY_KEY, jobId] as const,
    queryFn: async () => {
      const r = await apiClient.get<SignoffContextResponse>(
        `/api/v1/jobs/${jobId}/signoff-context`,
      );
      return r.data;
    },
    enabled: !!jobId,
    retry: false,
    staleTime: 30_000,
    placeholderData: keepPreviousData,
  });

  return { data, isPending, isError, refetch };
}
