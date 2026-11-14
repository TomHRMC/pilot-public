/**
 * useTechJobsList helpers — pure date filtering functions (MOB-B1)
 *
 * Location: apps/mobile/features/jobs/hooks/useTechJobsList.helpers.ts
 *
 * Extracted from useTechJobsList to enable unit testing without React/TanStack Query.
 * MOB-B1-BE complete: using generated types from @pilot/shared-types.
 */

import type { JobListItem } from "../job-types";

export function toDateStr(date: Date): string {
  return date.toISOString().slice(0, 10);
}

/**
 * Returns jobs whose scheduled_start_at falls on the given dateStr (YYYY-MM-DD).
 * Jobs with null scheduled_start_at are excluded.
 */
export function filterTodaysJobs(
  jobs: JobListItem[],
  todayStr: string,
): JobListItem[] {
  return jobs.filter(
    (job) =>
      !!job.scheduled_start_at && job.scheduled_start_at.startsWith(todayStr),
  );
}

/**
 * Returns jobs scheduled between tomorrow and 7 days from today (inclusive).
 * Jobs with null scheduled_start_at and today's jobs are excluded.
 */
export function filterUpcomingJobs(
  jobs: JobListItem[],
  todayStr: string,
): JobListItem[] {
  const tomorrowStr = toDateStr(new Date(Date.now() + 1 * 86_400_000));
  const sevenDaysStr = toDateStr(new Date(Date.now() + 7 * 86_400_000));

  return jobs.filter((job) => {
    if (!job.scheduled_start_at) return false;
    const jobDate = job.scheduled_start_at.slice(0, 10);
    return jobDate >= tomorrowStr && jobDate <= sevenDaysStr;
  });
}
