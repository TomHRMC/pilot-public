/**
 * useTechJobsList — Assigned jobs list for the Jobs tab (MOB-B1)
 *
 * Location: apps/mobile/features/jobs/hooks/useTechJobsList.ts
 *
 * Two TanStack Query fetches:
 *   1. Today's jobs:   GET /api/v1/jobs/?tech_id={userId}&scheduled_date={today}
 *   2. All my jobs:    GET /api/v1/jobs/?tech_id={userId}&limit=100
 *      → client-side filtered for jobs in next 7 days (excluding today)
 *
 * MOB-B1-BE complete: using generated types from @pilot/shared-types.
 *
 * Pending quote count is read from useTechQuotes (existing hook, migrated in
 * Step 0 of this batch).
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { useAuth } from "@pilot/ui/auth";
import type { JobListItem } from "../job-types";
import { useTechQuotes } from "../../quote-approval-status/hooks/useTechQuotes";
import {
  toDateStr,
  filterTodaysJobs,
  filterUpcomingJobs,
} from "./useTechJobsList.helpers";

// ── Fetchers ──────────────────────────────────────────────────────────────────

interface PaginatedJobListResponse {
  items: JobListItem[];
  total: number;
  limit: number;
  offset: number;
}

async function fetchJobsForDate(
  techId: string,
  scheduledDate: string,
): Promise<JobListItem[]> {
  const res = await apiClient.get<PaginatedJobListResponse>("/api/v1/jobs/", {
    params: {
      tech_id: techId,
      scheduled_date: scheduledDate,
      limit: 50,
    },
  });
  // Backend returns PaginatedJobListResponse { items, total, limit, offset }
  return res.data.items ?? [];
}

async function fetchAllMyJobs(techId: string): Promise<JobListItem[]> {
  const res = await apiClient.get<PaginatedJobListResponse>("/api/v1/jobs/", {
    params: {
      tech_id: techId,
      limit: 100,
    },
  });
  // Backend returns PaginatedJobListResponse { items, total, limit, offset }
  return res.data.items ?? [];
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export interface UseTechJobsListReturn {
  todaysJobs: JobListItem[];
  upcomingJobs: JobListItem[];
  pendingQuoteCount: number;
  isLoading: boolean;
  isError: boolean;
  refetch: () => Promise<unknown>;
  isFetching: boolean;
}

export function useTechJobsList(): UseTechJobsListReturn {
  const { user } = useAuth();
  const userId = user?.id ?? "";

  const today = toDateStr(new Date());

  // Today's jobs — scoped to the specific date
  const todayQuery = useQuery({
    queryKey: ["tech-jobs-today", userId, today] as const,
    queryFn: () => fetchJobsForDate(userId, today),
    enabled: !!userId,
    staleTime: 30_000,
    refetchOnWindowFocus: true,
  });

  // All my jobs — for upcoming section (next 7 days)
  const allJobsQuery = useQuery({
    queryKey: ["tech-jobs-all", userId] as const,
    queryFn: () => fetchAllMyJobs(userId),
    enabled: !!userId,
    staleTime: 60_000,
    refetchOnWindowFocus: true,
  });

  // Pending quote count from the already-migrated useTechQuotes hook
  const quotesQuery = useTechQuotes();
  const pendingQuoteCount =
    quotesQuery.data?.filter((q) => q.status === "pending_approval").length ??
    0;

  // ── Derived job lists ────────────────────────────────────────────────────

  const todaysJobs = filterTodaysJobs(todayQuery.data ?? [], today);
  const upcomingJobs = filterUpcomingJobs(allJobsQuery.data ?? [], today);

  const isLoading = todayQuery.isLoading || allJobsQuery.isLoading;
  const isError = todayQuery.isError || allJobsQuery.isError;
  const isFetching = todayQuery.isFetching || allJobsQuery.isFetching;

  const refetch = async () => {
    await Promise.all([todayQuery.refetch(), allJobsQuery.refetch()]);
  };

  return {
    todaysJobs,
    upcomingJobs,
    pendingQuoteCount,
    isLoading,
    isError,
    refetch,
    isFetching,
  };
}
