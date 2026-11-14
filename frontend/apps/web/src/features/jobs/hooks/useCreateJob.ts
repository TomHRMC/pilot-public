/**
 * useCreateJob — POST /api/v1/jobs/
 *
 * Location: apps/web/src/features/jobs/hooks/useCreateJob.ts
 *
 * RULE: Uses apiClient (never raw fetch).
 * RULE: onSuccess invalidates ["jobs"] query family.
 *
 * POST /api/v1/jobs/ — verified in openapi_schema_map.md (FE-B24 pre-work).
 * Required: customer_id, site_id
 * Optional: quote_id, scheduled_start_at, scheduled_end_at, estimated_duration_minutes
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient, getApiProblem, type ApiProblem } from "@pilot/shared-api";

export interface JobCreatePayload {
  customer_id: string;
  site_id: string;
  quote_id?: string | null;
  scheduled_start_at?: string | null; // ISO 8601
  scheduled_end_at?: string | null; // ISO 8601
  estimated_duration_minutes?: number | null;
  /** PLP-FIX-5 (Issue 12): optional job title (BE JobCreate already accepts). */
  title?: string | null;
  /** PLP-FIX-5 (Issue 12): optional job type id (BE JobCreate already accepts). */
  job_type_id?: string | null;
}

export interface JobCreateResponse {
  id: string;
  tenant_id: string;
  customer_id: string;
  site_id: string;
  status_id: string;
  /** PLP-FIX-5 (Issue 12): server-assigned human-readable id (e.g. "J-0007"). */
  job_number?: string;
  /** PLP-FIX-5 (Issue 12): assigned status code for success notification. */
  status_code?: string | null;
  scheduled_start_at: string | null;
  scheduled_end_at: string | null;
  estimated_duration_minutes: number | null;
  actual_labor_cost_cents: number;
  actual_material_cost_cents: number;
  actual_profit_cents: number;
  is_active: boolean;
}

export interface UseCreateJobOptions {
  onError?: (problem: ApiProblem) => void;
}

export function useCreateJob(options?: UseCreateJobOptions) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      payload: JobCreatePayload,
    ): Promise<JobCreateResponse> => {
      const res = await apiClient.post("/api/v1/jobs/", payload);
      return res.data as JobCreateResponse;
    },
    onSuccess: () => {
      // Invalidate all jobs queries (any options combination)
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
    onError: (error) => {
      const problem = getApiProblem(error);
      options?.onError?.(problem);
    },
  });
}
