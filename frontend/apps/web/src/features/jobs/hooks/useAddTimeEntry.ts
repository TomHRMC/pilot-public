/**
 * useAddTimeEntry — TanStack mutation for adding a time entry to a job
 *
 * Location: apps/web/src/features/jobs/hooks/useAddTimeEntry.ts
 *
 * POST /api/v1/jobs/{jobId}/time-entries
 * onSuccess: invalidate ['job-time-entries', jobId]
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { JOB_TIME_ENTRIES_QUERY_KEY } from "./useJobTimeEntries";
import type { JobTimeEntryResponse } from "./useJobTimeEntries";

export interface AddTimeEntryInput {
  started_at: string;
  ended_at?: string | null;
  hours?: number | null;
  notes?: string | null;
  hourly_rate_cents?: number | null;
  hours_remaining_estimate?: number | null;
  hours_remaining_was_overridden?: boolean;
  override_note?: string | null;
  quote_line_id?: string | null;
}

export function useAddTimeEntry(jobId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      input: AddTimeEntryInput,
    ): Promise<JobTimeEntryResponse> => {
      const res = await apiClient.post(
        `/api/v1/jobs/${jobId}/time-entries`,
        input,
      );
      return res.data as JobTimeEntryResponse;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: JOB_TIME_ENTRIES_QUERY_KEY(jobId),
      });
    },
  });
}
