/**
 * useRecentInAppNotifications — BETA-B4 / STEP 9
 *
 * Location: apps/web/src/features/notification-preferences/hooks/useRecentInAppNotifications.ts
 *
 * Fetches recent in-app notifications and provides bulk mark-read action.
 * GET  /api/v1/notifications/in-app/recent?limit=50
 * POST /api/v1/notifications/in-app/mark-read
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface InAppNotification {
  notificationId: string;
  category: string;
  title: string;
  body: string;
  isRead: boolean;
  createdAt: string;
  deepLinkHref: string | null;
}

interface InAppNotificationRaw {
  notification_id: string;
  category: string;
  title: string;
  body: string;
  is_read: boolean;
  created_at: string;
  deep_link_href: string | null;
}

export interface UseRecentInAppNotificationsReturn {
  notifications: InAppNotification[];
  isLoading: boolean;
  isError: boolean;
  markAllRead: () => Promise<void>;
  isMarkingRead: boolean;
}

const QUERY_KEY = ["notifications", "in-app", "recent"] as const;

function normalizeNotification(raw: InAppNotificationRaw): InAppNotification {
  return {
    notificationId: raw.notification_id,
    category: raw.category,
    title: raw.title,
    body: raw.body,
    isRead: raw.is_read,
    createdAt: raw.created_at,
    deepLinkHref: raw.deep_link_href,
  };
}

export function useRecentInAppNotifications(): UseRecentInAppNotificationsReturn {
  const qc = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: async (): Promise<InAppNotification[]> => {
      const res = await apiClient.get<InAppNotificationRaw[]>(
        "/api/v1/notifications/in-app/recent",
        { params: { limit: 50 } },
      );
      return res.data.map(normalizeNotification);
    },
    staleTime: 30_000,
  });

  const markReadMutation = useMutation({
    mutationFn: async () => {
      const notificationIds = (data ?? [])
        .filter((n) => !n.isRead)
        .map((n) => n.notificationId);
      if (notificationIds.length === 0) return;
      await apiClient.post("/api/v1/notifications/in-app/mark-read", {
        notification_ids: notificationIds,
      });
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });

  return {
    notifications: data ?? [],
    isLoading,
    isError,
    markAllRead: async () => {
      await markReadMutation.mutateAsync();
    },
    isMarkingRead: markReadMutation.isPending,
  };
}
