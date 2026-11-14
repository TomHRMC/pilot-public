/**
 * useJobDetail — Fetches job header + time entries for the Job Detail screen
 *
 * Location: apps/mobile/features/jobs/hooks/useJobDetail.ts
 *
 * Two parallel TanStack Query calls:
 *   1. GET /api/v1/jobs/{jobId}         → job header data
 *   2. GET /api/v1/jobs/{jobId}/time-entries → time entries
 *
 * status_code + customer_name are NOT in JobResponse (GET /api/v1/jobs/{jobId}).
 * They are resolved from the TanStack Query cache populated by useTechJobsList
 * (MOB-B1). If the user navigated directly (cache miss), both are null.
 *
 * Per batch-mob-b2-design.md §F.1 and §G.1.
 */

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { apiClient } from "@pilot/shared-api";
import { useAuth } from "@pilot/ui/auth";
import type { JobListItem } from "../job-types";

// ── Local types ────────────────────────────────────────────────────────────────

export interface JobResponse {
  id: string;
  tenant_id: string;
  customer_id: string;
  site_id: string;
  status_id: string;
  scheduled_start_at: string | null;
  scheduled_end_at: string | null;
  estimated_duration_minutes: number | null;
  /** UUID of the recurrence rule — non-null when this job is part of a recurring series (MOB-B9) */
  recurrence_rule_id?: string | null;
}

export interface JobTimeEntry {
  id: string;
  job_id: string;
  user_id: string;
  started_at: string;
  ended_at: string | null;
  hours: number | null;
  notes: string | null;
  hourly_rate_cents: number | null;
}

export interface JobDetailData {
  /** From GET /api/v1/jobs/{jobId} */
  job: JobResponse;
  /** From GET /api/v1/jobs/{jobId}/time-entries */
  timeEntries: JobTimeEntry[];
  /** Resolved from TanStack Query cache (MOB-B1); null on direct navigation */
  status_code: string | null;
  /** Resolved from TanStack Query cache (MOB-B1); null on direct navigation */
  customer_name: string | null;
  /** First entry where ended_at === null and user_id === currentUserId */
  activeTimeEntry: JobTimeEntry | null;
}

export interface UseJobDetailReturn {
  data: JobDetailData | undefined;
  isLoading: boolean;
  isError: boolean;
  refetch: () => void;
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useJobDetail(jobId: string): UseJobDetailReturn {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const userId = user?.id ?? "";
  const todayStr = new Date().toISOString().slice(0, 10);

  // ── Fetch job header data ────────────────────────────────────────────────
  const {
    data: job,
    isLoading: isJobLoading,
    isError: isJobError,
    refetch: refetchJob,
  } = useQuery({
    queryKey: ["job-detail", jobId] as const,
    queryFn: () =>
      apiClient.get<JobResponse>(`/api/v1/jobs/${jobId}`).then((r) => r.data),
    enabled: !!jobId,
    staleTime: 30_000,
  });

  // ── Fetch time entries ───────────────────────────────────────────────────
  const {
    data: timeEntries,
    isLoading: isEntriesLoading,
    isError: isEntriesError,
    refetch: refetchEntries,
  } = useQuery({
    queryKey: ["job-time-entries", jobId] as const,
    queryFn: () =>
      apiClient
        .get<JobTimeEntry[]>(`/api/v1/jobs/${jobId}/time-entries`)
        .then((r) => r.data),
    enabled: !!jobId,
    staleTime: 15_000,
  });

  // ── Resolve status_code + customer_name from MOB-B1 cache ───────────────
  // Try today's cache first, then the all-jobs cache.
  // If cache is empty (direct deep-link navigation), both are null — acceptable MVP edge case.
  const cachedToday =
    queryClient.getQueryData<JobListItem[]>([
      "tech-jobs-today",
      userId,
      todayStr,
    ]) ?? [];
  const cachedAll =
    queryClient.getQueryData<JobListItem[]>(["tech-jobs-all", userId]) ?? [];
  const cachedJob = [...cachedToday, ...cachedAll].find((j) => j.id === jobId);

  const status_code = cachedJob?.status_code ?? null;
  const customer_name = cachedJob?.customer_name ?? null;

  // ── Derive activeTimeEntry ───────────────────────────────────────────────
  const activeTimeEntry =
    (timeEntries ?? []).find(
      (e) => e.ended_at === null && e.user_id === userId,
    ) ?? null;

  // ── Combine refetch ──────────────────────────────────────────────────────
  const refetch = useCallback(() => {
    void refetchJob();
    void refetchEntries();
  }, [refetchJob, refetchEntries]);

  const data: JobDetailData | undefined =
    job && timeEntries
      ? {
          job,
          timeEntries,
          status_code: status_code ?? null,
          customer_name: customer_name ?? null,
          activeTimeEntry,
        }
      : undefined;

  return {
    data,
    isLoading: isJobLoading || isEntriesLoading,
    isError: isJobError || isEntriesError,
    refetch,
  };
}
