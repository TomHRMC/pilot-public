/**
 * useInAppNotifications — Notification bell data hook
 *
 * Location: apps/web/src/features/notifications-center/hooks/useInAppNotifications.ts
 *
 * GET /api/v1/notifications/in-app/recent?limit=50
 * Endpoint verified in backend/openapi_schema_map.md.
 * staleTime: 0 — SSE invalidation keeps this fresh.
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type { InAppNotification } from "../types";

interface InAppNotificationsResponse {
  notifications: InAppNotification[];
}

export function useInAppNotifications() {
  return useQuery<InAppNotification[]>({
    queryKey: ["notifications-recent"],
    queryFn: async () => {
      const res = await apiClient.get("/api/v1/notifications/in-app/recent", {
        params: { limit: 50 },
      });
      const data = res.data as InAppNotificationsResponse;
      return data.notifications ?? [];
    },
    staleTime: 0,
  });
}
