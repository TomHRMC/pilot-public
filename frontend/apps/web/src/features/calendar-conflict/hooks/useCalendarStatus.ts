/**
 * useCalendarStatus — TanStack Query hook for calendar connection status
 *
 * Location: apps/web/src/features/calendar-conflict/hooks/useCalendarStatus.ts
 *
 * GET /api/v1/integrations/calendar/status
 * Cache: 60s staleTime; refetchOnWindowFocus
 *
 * Pattern ref: design doc batch-fe-b8-design.md §C.4
 */

import { useQuery } from "@tanstack/react-query";
import type { CalendarConnectionStatus } from "@pilot/ui";
import { normalizeConnectionStatus } from "../types";
import { apiClient } from "@pilot/shared-api";

export const CALENDAR_STATUS_QUERY_KEY = ["calendar-status"] as const;

async function fetchCalendarStatus(): Promise<CalendarConnectionStatus> {
  const res = await apiClient.get("/api/v1/integrations/calendar/status");
  const data: unknown = res.data;
  return normalizeConnectionStatus(data);
}

export function useCalendarStatus() {
  return useQuery({
    queryKey: CALENDAR_STATUS_QUERY_KEY,
    queryFn: fetchCalendarStatus,
    staleTime: 60_000, // 60 seconds
    refetchOnWindowFocus: true,
  });
}
