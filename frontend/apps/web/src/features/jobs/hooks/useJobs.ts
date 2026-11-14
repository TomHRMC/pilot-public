/**
 * useJobs — TanStack Query hook for jobs list
 *
 * Location: apps/web/src/features/jobs/hooks/useJobs.ts
 *
 * RULE: Uses apiClient (never raw fetch).
 *
 * UI-FIX-1C: Complete rewrite of hook signature.
 * - Now accepts option-based params (was a static fetch with no params)
 * - Returns PaginatedResult<JobListItem> instead of JobListItem[]
 * - skip → offset (canonical)
 * - Added: status, customer_search, scheduled_from, scheduled_to
 * - Preserved: tech_id, scheduled_date (dispatch board backward compat)
 *
 * Dispatch board compatibility: useJobs({ scheduled_date: "YYYY-MM-DD", tech_id: "..." })
 * is still valid — the new object signature is backward-compatible.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { LIST_PAGE_SIZE } from "@pilot/shared-api";

export interface JobListItem {
  id: string;
  tenant_id: string;
  customer_id: string;
  site_id: string;
  status_id: string;
  status_code: string;
  customer_name: string;
  /** B19: human-readable job identifier (e.g. "JOB-000001") */
  job_number?: string | null;
  scheduled_start_at: string | null;
  scheduled_end_at: string | null;
  estimated_duration_minutes: number | null;
  /** FE-B31: present when job was created by a recurrence rule */
  recurrence_rule_id?: string | null;
  /** CLASS-B1: priority level (standard | urgent | emergency) */
  priority?: string | null;
  /** CLASS-B1: job type id */
  job_type_id?: string | null;
  /** CLASS-B1: job type code */
  job_type_code?: string | null;
  /** CLASS-B1: job type display label */
  job_type_label?: string | null;
  /** JOB-UI-B1: job title (null → fallback to job_number for display) */
  title?: string | null;
}

/** Generic paginated response shape — matches backend PaginatedResponse[T] */
export interface PaginatedResult<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface UseJobsOptions {
  offset?: number;
  limit?: number;
  /** Dispatch board: filter by technician UUID */
  tech_id?: string;
  /** Dispatch board: filter by scheduled date (YYYY-MM-DD) — kept for backward compat */
  scheduled_date?: string;
  /** UI-FIX-1C: filter by job status code (draft | scheduled | in_progress | completed | cancelled) */
  status?: string;
  /** UI-FIX-1C: ILIKE on customer.display_name */
  customer_search?: string;
  /** UI-FIX-1C: job.scheduled_start_at >= date */
  scheduled_from?: string;
  /** UI-FIX-1C: job.scheduled_start_at <= date */
  scheduled_to?: string;
  /** UI-FIX-2D: exact UUID filter — when set, scopes results to this customer */
  customer_id?: string;
}

export const JOBS_QUERY_KEY = (options?: UseJobsOptions) =>
  ["jobs", options ?? {}] as const;

export function useJobs(options: UseJobsOptions = {}) {
  return useQuery({
    queryKey: JOBS_QUERY_KEY(options),
    queryFn: async (): Promise<PaginatedResult<JobListItem>> => {
      const {
        offset = 0,
        limit = LIST_PAGE_SIZE,
        tech_id,
        scheduled_date,
        status,
        customer_search,
        scheduled_from,
        scheduled_to,
        customer_id,
      } = options;
      const params: Record<string, unknown> = { offset, limit };
      if (tech_id) params.tech_id = tech_id;
      if (scheduled_date) params.scheduled_date = scheduled_date;
      if (status) params.status = status;
      if (customer_search?.trim())
        params.customer_search = customer_search.trim();
      if (scheduled_from) params.scheduled_from = scheduled_from;
      if (scheduled_to) params.scheduled_to = scheduled_to;
      if (customer_id) params.customer_id = customer_id;
      const res = await apiClient.get("/api/v1/jobs/", { params });
      return res.data as PaginatedResult<JobListItem>;
    },
    staleTime: 30_000,
  });
}
