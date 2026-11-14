/**
 * useJobDetail — TanStack Query hooks for job detail panel
 *
 * Location: apps/web/src/features/dispatch-board/hooks/useJobDetail.ts
 *
 * GET /api/v1/jobs/{job_id} + GET /api/v1/jobs/{job_id}/projected-margin
 * Both already in openapi.json.
 *
 * Per batch-fe-b4-design.md §A.2.7
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

// Full job detail — uses existing openapi.json types
// For now using a local interface until pnpm sync-api-types delivers proper types
export interface JobDetail {
  id: string;
  title: string;
  description?: string;
  customer_name: string;
  site_address: string;
  status: string;
  priority: string;
  job_type: string;
  scheduled_start_at: string | null;
  scheduled_end_at: string | null;
  tech_id: string | null;
  tech_name: string | null;
  updated_at: string;
  time_entries: TimeEntry[];
  quote_lines: QuoteLine[];
}

export interface TimeEntry {
  id: string;
  tech_id: string;
  tech_name: string;
  clock_in_at: string;
  clock_out_at: string | null;
  hours_worked: number;
}

export interface QuoteLine {
  id: string;
  description: string;
  quoted_hours: number;
  actual_hours: number;
  remaining_hours: number;
  tech_breakdowns: Array<{
    tech_id: string;
    tech_name: string;
    hours: number;
  }>;
}

export interface ProjectedMargin {
  projected_margin_pct: number;
  cost_to_date_cents: number;
  etc_hours_remaining: number;
  revenue_cents: number;
  margin_bucket: "below-low" | "low" | "medium" | "high";
  hours_worked: number;
  quoted_hours: number;
}

async function fetchJobDetail(jobId: string): Promise<JobDetail> {
  const res = await apiClient.get<JobDetail>(`/api/v1/jobs/${jobId}`);
  return res.data;
}

async function fetchProjectedMargin(jobId: string): Promise<ProjectedMargin> {
  const res = await apiClient.get<ProjectedMargin>(
    `/api/v1/jobs/${jobId}/projected-margin`,
  );
  return res.data;
}

export function useJobDetail(jobId: string | null) {
  return useQuery({
    queryKey: ["job-detail", jobId],
    queryFn: () => fetchJobDetail(jobId!),
    enabled: !!jobId,
    staleTime: 60_000,
  });
}

export function useProjectedMargin(jobId: string | null) {
  return useQuery({
    queryKey: ["projected-margin", jobId],
    queryFn: () => fetchProjectedMargin(jobId!),
    enabled: !!jobId,
    staleTime: 30_000,
  });
}
