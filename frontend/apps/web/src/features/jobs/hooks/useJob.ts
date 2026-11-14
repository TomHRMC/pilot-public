/**
 * useJob — TanStack Query hook for single job detail
 *
 * Location: apps/web/src/features/jobs/hooks/useJob.ts
 *
 * GET /api/v1/jobs/{jobId}
 * Query key: ['job', jobId]
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface JobResponse {
  id: string;
  tenant_id: string;
  customer_id: string;
  site_id: string;
  status_id: string;
  /** B19: human-readable status code (e.g. "completed", "in_progress") */
  status_code?: string | null;
  /** B19: human-readable job identifier (e.g. "JOB-000001") */
  job_number?: string | null;
  /** B19: site display name */
  site_name?: string | null;
  /** B19: customer display name */
  customer_name?: string | null;
  /** FK to quote that originated this job */
  quote_id?: string | null;
  scheduled_start_at: string | null;
  scheduled_end_at: string | null;
  estimated_duration_minutes: number | null;
  external_calendar_event_id: string | null;
  actual_labor_cost_cents: number;
  actual_material_cost_cents: number;
  actual_profit_cents: number;
  is_active: boolean;
  /** CLASS-B1 + JOB-UI-B1: priority level */
  priority?: string | null;
  /** CLASS-B1 + JOB-UI-B1: job type id */
  job_type_id?: string | null;
  /** CLASS-B1 + JOB-UI-B1: job type code */
  job_type_code?: string | null;
  /** CLASS-B1 + JOB-UI-B1: job type display label */
  job_type_label?: string | null;
  /** JOB-UI-B1: job title (fallback to job_number for display) */
  title?: string | null;
  /** JOB-UI-B1: originating quote version id */
  quote_version_id?: string | null;
  /** FE-B31: recurrence rule id */
  recurrence_rule_id?: string | null;
}

export const JOB_QUERY_KEY = (jobId: string) => ["job", jobId] as const;

export function useJob(jobId: string) {
  return useQuery({
    queryKey: JOB_QUERY_KEY(jobId),
    queryFn: async (): Promise<JobResponse> => {
      const res = await apiClient.get(`/api/v1/jobs/${jobId}`);
      return res.data as JobResponse;
    },
    enabled: !!jobId,
    staleTime: 30_000,
  });
}
