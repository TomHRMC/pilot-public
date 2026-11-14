"use client";
/**
 * useRemoveJobAssignment — DELETE a technician assignment from a job.
 *
 * Location: apps/web/src/features/jobs/hooks/useRemoveJobAssignment.ts
 *
 * Endpoint: DELETE /api/v1/scheduling/jobs/{job_id}/assignments/{assignment_id}
 * On success: invalidates ['job-assignments', jobId]
 *
 * Note: No auto-promotion of helpers when primary is removed (MVP scope).
 *
 * Added by: UI-FIX-2B React Engineer
 */

import { apiClient } from "@pilot/shared-api";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { jobAssignmentsQueryKey } from "./useJobAssignments";

export function useRemoveJobAssignment(jobId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (assignmentId: string) => {
      await apiClient.delete(
        `/api/v1/scheduling/jobs/${jobId}/assignments/${assignmentId}`,
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: jobAssignmentsQueryKey(jobId),
      });
    },
  });
}
