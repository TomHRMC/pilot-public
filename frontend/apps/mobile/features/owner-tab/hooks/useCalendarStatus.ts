import { Platform } from "react-native";
/**
 * useCalendarStatus (mobile) — TanStack Query hook for calendar connection status
 *
 * Location: apps/mobile/features/owner-tab/hooks/useCalendarStatus.ts
 *
 * GET /api/v1/integrations/calendar/status
 * Cache: 60s staleTime
 *
 * Uses apiClient (JWT-intercepted) instead of raw fetch.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { CalendarConnectionStatus } from "@pilot/ui";

export const CALENDAR_STATUS_QUERY_KEY = ["calendar-status"] as const;

// ─── Config constants — never hardcoded in components ─────────────────────────

/** Deep-link URL to the web calendar conflict resolution surface */
export const CALENDAR_RESOLVE_WEB_URL = process.env.EXPO_PUBLIC_WEB_APP_URL
  ? `${process.env.EXPO_PUBLIC_WEB_APP_URL}/settings/integrations/calendar#conflicts`
  : "https://app.pilotfortrades.com/settings/integrations/calendar#conflicts";

/** Deep-link URL to web calendar settings (reconnect) */
export const CALENDAR_SETTINGS_WEB_URL = process.env.EXPO_PUBLIC_WEB_APP_URL
  ? `${process.env.EXPO_PUBLIC_WEB_APP_URL}/settings/integrations/calendar`
  : "https://app.pilotfortrades.com/settings/integrations/calendar";

// ─── API fetcher ──────────────────────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function normalizeConnectionStatus(raw: any): CalendarConnectionStatus {
  return {
    isConnected: raw.is_connected as boolean,
    providerCode: raw.provider_code as string | null,
    syncStatus: raw.sync_status as string | null,
    connectionStatus:
      raw.connection_status as CalendarConnectionStatus["connectionStatus"],
    connectedAt: raw.connected_at as string | null,
    tokenExpiresAt: raw.token_expires_at as string | null,
    lastSyncAt: raw.last_sync_at as string | null,
    lastSuccessfulSyncAt: raw.last_successful_sync_at as string | null,
    pendingConflictsCount: raw.pending_conflicts_count as number,
    requiresReconnect: raw.requires_reconnect as boolean,
  };
}

async function fetchCalendarStatus(): Promise<CalendarConnectionStatus> {
  const res = await apiClient.get<unknown>(
    "/api/v1/integrations/calendar/status",
  );
  return normalizeConnectionStatus(res.data);
}

// ─── Hook ──────────────────────────────────────────────────────────────────────

export function useCalendarStatus() {
  const isMockAuth =
    Platform.OS === "web" && process.env.EXPO_PUBLIC_USE_MOCK_AUTH === "true";

  return useQuery({
    queryKey: CALENDAR_STATUS_QUERY_KEY,
    queryFn: fetchCalendarStatus,
    staleTime: 60_000, // 60 seconds
    refetchOnWindowFocus: false, // Mobile: no window focus events
    refetchInterval: 5 * 60 * 1000, // 5-minute background refresh
    retry: 1,
    // In mock auth mode there is no real Cognito session — skip the fetch entirely
    enabled: !isMockAuth,
  });
}
