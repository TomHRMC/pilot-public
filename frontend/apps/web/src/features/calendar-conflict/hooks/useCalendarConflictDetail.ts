/**
 * useCalendarConflictDetail — TanStack Query detail hook
 *
 * Location: apps/web/src/features/calendar-conflict/hooks/useCalendarConflictDetail.ts
 *
 * GET /api/v1/integrations/calendar/conflicts/{id}
 * Cache: 0s staleTime (always fresh for a decision surface); refetchOnWindowFocus
 *
 * Pattern ref: design doc batch-fe-b8-design.md §C.2
 */

import { useQuery } from "@tanstack/react-query";
import type { CalendarConflictDetail } from "@pilot/ui";
import { normalizeConflictDetail } from "../types";
import { apiClient } from "@pilot/shared-api";

export const CALENDAR_CONFLICT_DETAIL_QUERY_KEY = (id: string) =>
  ["calendar-conflict", id] as const;

async function fetchConflictDetail(
  id: string,
): Promise<CalendarConflictDetail> {
  const res = await apiClient.get(
    `/api/v1/integrations/calendar/conflicts/${encodeURIComponent(id)}`,
  );
  const data: unknown = res.data;
  return normalizeConflictDetail(data);
}

export function useCalendarConflictDetail(id: string) {
  return useQuery({
    queryKey: CALENDAR_CONFLICT_DETAIL_QUERY_KEY(id),
    queryFn: () => fetchConflictDetail(id),
    staleTime: 0, // Always fresh — this is a decision surface
    refetchOnWindowFocus: true,
    enabled: !!id,
  });
}
