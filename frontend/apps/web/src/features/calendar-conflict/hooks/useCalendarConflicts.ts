/**
 * useCalendarConflicts — TanStack Query list hook for calendar conflicts
 *
 * Location: apps/web/src/features/calendar-conflict/hooks/useCalendarConflicts.ts
 *
 * GET /api/v1/integrations/calendar/conflicts
 * Cache: 30s staleTime; refetchOnWindowFocus
 * Cursor-paginated.
 *
 * Pattern ref: design doc batch-fe-b8-design.md §C.1
 */

import { useQuery } from "@tanstack/react-query";
import type {
  CalendarConflictQueueItem,
  CalendarConflictsResponse,
  CalendarConflictsParams,
} from "../types";
import { normalizeConflictListItem } from "../types";
import { apiClient } from "@pilot/shared-api";

export const CALENDAR_CONFLICTS_QUERY_KEY = (params: CalendarConflictsParams) =>
  ["calendar-conflicts", params] as const;

async function fetchCalendarConflicts(
  params: CalendarConflictsParams,
): Promise<CalendarConflictsResponse> {
  const query = new URLSearchParams();
  if (params.status) query.set("status", params.status);
  if (params.cursor) query.set("cursor", params.cursor);
  if (params.limit) query.set("limit", String(params.limit));

  const res = await apiClient.get(
    `/api/v1/integrations/calendar/conflicts?${query.toString()}`,
  );

  const data = res.data as {
    conflicts: unknown[];
    next_cursor: string | null;
    total_pending: number;
  };

  return {
    conflicts: data.conflicts.map((c) =>
      normalizeConflictListItem(c),
    ) as CalendarConflictQueueItem[],
    nextCursor: data.next_cursor,
    totalPending: data.total_pending,
  };
}

export function useCalendarConflicts(params: CalendarConflictsParams = {}) {
  return useQuery({
    queryKey: CALENDAR_CONFLICTS_QUERY_KEY(params),
    queryFn: () => fetchCalendarConflicts(params),
    staleTime: 30_000, // 30 seconds
    refetchOnWindowFocus: true,
  });
}
