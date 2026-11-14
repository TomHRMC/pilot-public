/**
 * useUpdateJobNotes — TanStack mutation for updating job notes
 *
 * Location: apps/web/src/features/jobs/hooks/useUpdateJobNotes.ts
 *
 * PUT /api/v1/jobs/{jobId}/notes  (note: PUT not PATCH)
 * Request body: { notes: string }
 * onSuccess: invalidate ['job-notes', jobId]
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { JOB_NOTES_QUERY_KEY } from "./useJobNotes";
import type { JobNotesResponse } from "./useJobNotes";

export interface UpdateJobNotesInput {
  notes: string;
}

export function useUpdateJobNotes(jobId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      input: UpdateJobNotesInput,
    ): Promise<JobNotesResponse> => {
      const res = await apiClient.put(`/api/v1/jobs/${jobId}/notes`, input);
      return res.data as JobNotesResponse;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: JOB_NOTES_QUERY_KEY(jobId),
      });
    },
  });
}
