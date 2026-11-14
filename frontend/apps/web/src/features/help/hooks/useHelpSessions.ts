/**
 * useHelpSessions — TanStack Query infinite query — FE-B16
 *
 * Location: apps/web/src/features/help/hooks/useHelpSessions.ts
 *
 * GET /api/v1/help/sessions with infinite scroll + grouping.
 */

import { useInfiniteQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { HelpSessionListResponse, HelpSessionSummary } from "../types";

async function fetchHelpSessions(
  offset: number,
): Promise<HelpSessionListResponse> {
  const params = new URLSearchParams({ limit: "20", offset: String(offset) });
  const res = await apiClient.get<HelpSessionListResponse>(
    `/api/v1/help/sessions?${params}`,
  );
  return res.data;
}

export type SessionGroup = {
  label: "Today" | "Last 7 days" | "Older";
  sessions: HelpSessionSummary[];
};

/** Group sessions by recency */
export function groupSessionsByRecency(
  sessions: HelpSessionSummary[],
): SessionGroup[] {
  const now = Date.now();
  const ONE_DAY = 1000 * 60 * 60 * 24;
  const SEVEN_DAYS = ONE_DAY * 7;

  const today: HelpSessionSummary[] = [];
  const lastWeek: HelpSessionSummary[] = [];
  const older: HelpSessionSummary[] = [];

  for (const s of sessions) {
    const age = now - new Date(s.last_activity_at).getTime();
    if (age < ONE_DAY) today.push(s);
    else if (age < SEVEN_DAYS) lastWeek.push(s);
    else older.push(s);
  }

  const groups: SessionGroup[] = [];
  if (today.length > 0) groups.push({ label: "Today", sessions: today });
  if (lastWeek.length > 0)
    groups.push({ label: "Last 7 days", sessions: lastWeek });
  if (older.length > 0) groups.push({ label: "Older", sessions: older });

  return groups;
}

export function useHelpSessions() {
  const query = useInfiniteQuery({
    queryKey: ["help", "sessions"],
    queryFn: ({ pageParam = 0 }) => fetchHelpSessions(pageParam as number),
    getNextPageParam: (lastPage, pages) => {
      const loaded = pages.length * 20;
      return loaded < lastPage.total ? loaded : undefined;
    },
    initialPageParam: 0,
    staleTime: 30_000,
  });

  const allSessions = query.data?.pages.flatMap((p) => p.sessions) ?? [];
  const groups = groupSessionsByRecency(allSessions);

  return {
    ...query,
    sessions: allSessions,
    groups,
  };
}
