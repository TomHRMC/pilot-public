/**
 * useJobNotes — TanStack Query hook for job notes
 *
 * Location: apps/web/src/features/jobs/hooks/useJobNotes.ts
 *
 * GET /api/v1/jobs/{jobId}/notes
 * Query key: ['job-notes', jobId]
 *
 * Note: backend response field is `notes` (not `notes_text`)
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface JobNotesResponse {
  id: string;
  tenant_id: string;
  job_id: string;
  notes: string;
  audio_object_key: string | null;
  customer_visible: boolean;
  client_capture_at: string | null;
  server_received_at: string | null;
  created_at: string;
  updated_at: string;
  created_by: string;
}

export const JOB_NOTES_QUERY_KEY = (jobId: string) =>
  ["job-notes", jobId] as const;

export function useJobNotes(jobId: string) {
  return useQuery({
    queryKey: JOB_NOTES_QUERY_KEY(jobId),
    queryFn: async (): Promise<JobNotesResponse> => {
      const res = await apiClient.get(`/api/v1/jobs/${jobId}/notes`);
      return res.data as JobNotesResponse;
    },
    enabled: !!jobId,
    staleTime: 30_000,
  });
}
