/**
 * useJobTimeEntries — TanStack Query hook for job time entries
 *
 * Location: apps/web/src/features/jobs/hooks/useJobTimeEntries.ts
 *
 * GET /api/v1/jobs/{jobId}/time-entries
 * Query key: ['job-time-entries', jobId]
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface JobTimeEntryResponse {
  id: string;
  job_id: string;
  user_id: string;
  started_at: string;
  ended_at: string | null;
  hours: number | null;
  notes: string | null;
  hourly_rate_cents: number | null;
  total_cost_cents: number | null;
  hours_remaining_estimate: number | null;
  hours_remaining_was_overridden: boolean;
  override_note: string | null;
  quote_line_id: string | null;
  etc_captured_at: string | null;
}

export const JOB_TIME_ENTRIES_QUERY_KEY = (jobId: string) =>
  ["job-time-entries", jobId] as const;

export function useJobTimeEntries(jobId: string) {
  return useQuery({
    queryKey: JOB_TIME_ENTRIES_QUERY_KEY(jobId),
    queryFn: async (): Promise<JobTimeEntryResponse[]> => {
      const res = await apiClient.get(`/api/v1/jobs/${jobId}/time-entries`);
      return res.data as JobTimeEntryResponse[];
    },
    enabled: !!jobId,
    staleTime: 30_000,
  });
}
