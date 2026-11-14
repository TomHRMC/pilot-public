"use client";
/**
 * useJobAssignments — Fetch all active technician assignments for a job.
 *
 * Location: apps/web/src/features/jobs/hooks/useJobAssignments.ts
 *
 * Endpoint: GET /api/v1/scheduling/jobs/{job_id}/assignments
 * staleTime: 0 — real-time accuracy required for dispatch board
 *
 * Added by: UI-FIX-2B React Engineer
 */

import { apiClient } from "@pilot/shared-api";
import { useQuery } from "@tanstack/react-query";

export interface JobAssignment {
  id: string;
  job_id: string;
  user_id: string;
  role: "primary" | "helper";
  ordinal: number;
  assigned_at: string;
  is_active: boolean;
}

export function jobAssignmentsQueryKey(jobId: string) {
  return ["job-assignments", jobId] as const;
}

export function useJobAssignments(jobId: string | undefined) {
  return useQuery({
    queryKey: jobId
      ? jobAssignmentsQueryKey(jobId)
      : (["job-assignments", "disabled"] as const),
    queryFn: async (): Promise<JobAssignment[]> => {
      const resp = await apiClient.get(
        `/api/v1/scheduling/jobs/${jobId}/assignments`,
      );
      const raw: unknown = resp.data;
      const items: JobAssignment[] = Array.isArray(raw)
        ? (raw as JobAssignment[])
        : ((raw as { items?: JobAssignment[] }).items ?? []);
      return items;
    },
    enabled: !!jobId,
    staleTime: 0,
  });
}
