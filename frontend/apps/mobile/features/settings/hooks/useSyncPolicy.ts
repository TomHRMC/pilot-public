/**
 * useSyncPolicy — MOB-B8 Part B
 *
 * Location: apps/mobile/features/settings/hooks/useSyncPolicy.ts
 *
 * Fetches the background sync policy from the backend.
 * Endpoint: GET /api/v1/settings/background-sync-policy (confirmed in openapi_schema_map.md)
 *
 * staleTime: 5 minutes — policy rarely changes mid-session.
 * retry: false — consistent with mobile hook patterns.
 * Error: non-fatal; settings screen renders gracefully without the policy.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface BackgroundSyncPolicy {
  background_sync_enabled: boolean;
  background_sync_wifi_only: boolean;
  background_sync_battery_floor_pct: number;
  background_sync_push_interval_minutes: number;
}

export const SYNC_POLICY_QUERY_KEY = ["background-sync-policy"] as const;

export function useSyncPolicy() {
  return useQuery<BackgroundSyncPolicy>({
    queryKey: SYNC_POLICY_QUERY_KEY,
    queryFn: async () => {
      const response = await apiClient.get<BackgroundSyncPolicy>(
        "/api/v1/settings/background-sync-policy",
      );
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes — policy rarely changes mid-session
    retry: false,
  });
}
