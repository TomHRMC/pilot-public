/**
 * useUpdateJob — PATCH /api/v1/jobs/{job_id}
 *
 * Location: apps/web/src/features/jobs/hooks/useUpdateJob.ts
 *
 * FE-B25: Partial update of a job's scheduling and site details.
 * JOB-UI-B1: Extended to include title, priority, job_type_id, status_code.
 *
 * RULE: Uses apiClient (never raw fetch).
 * RULE: onSuccess invalidates ["job", jobId] + JOBS_QUERY_KEY.
 *
 * PATCH /api/v1/jobs/{job_id} — verified in openapi_schema_map.md.
 * Status code transitions validated by backend; illegal transitions return RFC 7807 422.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface JobUpdatePayload {
  customer_id?: string;
  site_id?: string;
  scheduled_start_at?: string | null; // ISO 8601
  scheduled_end_at?: string | null; // ISO 8601
  estimated_duration_minutes?: number | null;
  /** JOB-UI-B1: job title (null clears it) */
  title?: string | null;
  /** JOB-UI-B1: "standard" | "urgent" | "emergency" */
  priority?: "standard" | "urgent" | "emergency";
  /** JOB-UI-B1: UUID of the job_type row */
  job_type_id?: string | null;
  /**
   * JOB-UI-B1: status_code for forward-transition edits.
   * Valid codes: draft → scheduled → in_progress → completed; any → cancelled.
   * Illegal backward transitions return RFC 7807 422.
   */
  status_code?: string | null;
}

export interface JobUpdateResponse {
  id: string;
  tenant_id: string;
  customer_id: string;
  site_id: string;
  status_id: string;
  status_code?: string | null;
  job_number?: string | null;
  title?: string | null;
  priority?: string;
  job_type_id?: string | null;
  job_type_code?: string | null;
  job_type_label?: string | null;
  scheduled_start_at: string | null;
  scheduled_end_at: string | null;
  estimated_duration_minutes: number | null;
  actual_labor_cost_cents: number;
  actual_material_cost_cents: number;
  actual_profit_cents: number;
  is_active: boolean;
}

export function useUpdateJob(jobId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      payload: JobUpdatePayload,
    ): Promise<JobUpdateResponse> => {
      const res = await apiClient.patch(`/api/v1/jobs/${jobId}`, payload);
      return res.data as JobUpdateResponse;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["job", jobId] });
      // Invalidate all jobs queries (any options combination)
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}
