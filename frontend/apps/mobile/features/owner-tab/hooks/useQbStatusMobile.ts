import { Platform } from "react-native";
/**
 * useQbStatusMobile — TanStack Query hook for QuickBooks connection status
 *
 * Location: apps/mobile/features/owner-tab/hooks/useQbStatusMobile.ts
 *
 * GET /api/v1/integrations/quickbooks/status
 * Response: QuickBooksConnectionStatus (no last_sync_at — do not display it)
 *
 * connection_status values: "active" | "pending" | "disconnected" | "expired" | "not_configured"
 * Only "active" with is_connected=true should show "Connected" state.
 *
 * Pattern: follows useCalendarStatus.ts (staleTime, refetchInterval, enabled)
 * MOB-B5
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export const QB_STATUS_MOBILE_QUERY_KEY = ["qb-status-mobile"] as const;

export interface QbConnectionStatus {
  is_connected: boolean;
  realm_id: string | null;
  company_name: string | null;
  connected_at: string | null;
  expires_at: string | null;
  connection_status: string; // "active" | "pending" | "disconnected" | "expired" | "not_configured"
}

async function fetchQbStatus(): Promise<QbConnectionStatus> {
  const res = await apiClient.get<QbConnectionStatus>(
    "/api/v1/integrations/quickbooks/status",
  );
  return res.data;
}

export function useQbStatusMobile() {
  const isMockAuth =
    Platform.OS === "web" && process.env.EXPO_PUBLIC_USE_MOCK_AUTH === "true";

  return useQuery({
    queryKey: QB_STATUS_MOBILE_QUERY_KEY,
    queryFn: fetchQbStatus,
    staleTime: 60_000, // 60 seconds
    refetchOnWindowFocus: false, // Mobile: no window focus events
    refetchInterval: 5 * 60 * 1000, // 5-minute background refresh
    retry: 1,
    enabled: !isMockAuth,
  });
}
