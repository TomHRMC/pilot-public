"use client";
/**
 * useAddJobAssignment — POST a new technician assignment to a job.
 *
 * Location: apps/web/src/features/jobs/hooks/useAddJobAssignment.ts
 *
 * Endpoint: POST /api/v1/scheduling/jobs/{job_id}/assignments
 * Body: { user_id, role, ordinal? }
 * On success: invalidates ['job-assignments', jobId]
 *
 * Role auto-computation (caller's responsibility):
 *   - first addition → role = 'primary'
 *   - subsequent     → role = 'helper'
 *
 * Added by: UI-FIX-2B React Engineer
 */

import { apiClient } from "@pilot/shared-api";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { jobAssignmentsQueryKey } from "./useJobAssignments";

export interface AddJobAssignmentPayload {
  user_id: string;
  role: "primary" | "helper";
  ordinal?: number;
}

export function useAddJobAssignment(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: AddJobAssignmentPayload) => {
      const resp = await apiClient.post(
        `/api/v1/scheduling/jobs/${jobId}/assignments`,
        payload,
      );
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: jobAssignmentsQueryKey(jobId),
      });
    },
  });
}
