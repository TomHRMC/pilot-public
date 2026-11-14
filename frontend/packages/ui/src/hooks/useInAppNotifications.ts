/**
 * useInAppNotifications — Shared hook for in-app notification center
 *
 * Location: packages/ui/src/hooks/useInAppNotifications.ts
 *
 * RULE: Subscribes to SSE via useSseChannel (FE-B4 locked hook) — never raw EventSource.
 * RULE: SSE path is /sse/notifications.
 * RULE: On mobile, falls back to polling (fallbackToPollingMs: 60_000).
 * RULE: unreadCount is derived from notifications.filter(n => !n.read_at).length
 *
 * State initialized from TanStack Query GET /api/v1/notifications/in-app/recent.
 * New SSE events prepend to the list; markRead updates optimistically.
 */

import { useState, useCallback } from "react";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { useSseChannel } from "./useSseChannel";
import type {
  InAppNotification,
  NotificationSseEvent,
} from "../notification-center-bell/types";
import type { UseInAppNotificationsReturn } from "../notification-center-bell/types";

const RECENT_NOTIFICATIONS_KEY = ["notifications", "in-app", "recent"] as const;
const SSE_PATH = "/sse/notifications";
const MARK_READ_URL = "/api/v1/notifications/in-app/mark-read";
const RECENT_URL = "/api/v1/notifications/in-app/recent?limit=50";

async function fetchRecentNotifications(): Promise<InAppNotification[]> {
  const res = await fetch(RECENT_URL);
  if (!res.ok) throw new Error("Failed to fetch notifications.");
  return res.json() as Promise<InAppNotification[]>;
}

async function postMarkRead(notificationIds?: string[]): Promise<void> {
  await fetch(MARK_READ_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(
      notificationIds ? { notification_ids: notificationIds } : {},
    ),
  });
}

/**
 * useInAppNotifications
 *
 * Manages notification center state. Composes useSseChannel for real-time delivery.
 * Falls back to polling at 60s intervals when SSE unavailable (mobile).
 *
 * @example
 * const { notifications, unreadCount, markRead, markAllRead, isConnected } = useInAppNotifications();
 */
export function useInAppNotifications(): UseInAppNotificationsReturn {
  const queryClient = useQueryClient();
  const [isBellOpen, setIsBellOpen] = useState(false);

  // Initialize from server
  const { data: notifications = [] } = useQuery({
    queryKey: RECENT_NOTIFICATIONS_KEY,
    queryFn: fetchRecentNotifications,
    staleTime: 30_000,
  });

  const unreadCount = notifications.filter((n) => !n.read_at).length;

  // SSE message handler ref (stable reference)
  const handleSseMessage = useCallback(
    (msg: { data: string }) => {
      try {
        const event = JSON.parse(msg.data) as NotificationSseEvent;
        const newNotification: InAppNotification = {
          notification_id: event.notification_id,
          category_id: event.category_id,
          body: event.body,
          deep_link_target: event.deep_link_target,
          priority: event.priority,
          created_at: event.created_at,
          read_at: null,
        };
        // Prepend to cached list
        queryClient.setQueryData<InAppNotification[]>(
          RECENT_NOTIFICATIONS_KEY,
          (old = []) => [newNotification, ...old].slice(0, 50),
        );
      } catch {
        // Malformed SSE payload — ignore
      }
    },
    [queryClient],
  );

  // Poll function for mobile fallback
  const pollFn = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: RECENT_NOTIFICATIONS_KEY });
  }, [queryClient]);

  // SSE subscription — RULE: always via useSseChannel, never raw EventSource
  const { isConnected } = useSseChannel({
    path: SSE_PATH,
    onMessage: handleSseMessage,
    fallbackToPollingMs: 60_000,
    pollFn,
  });

  // Mark single read
  const markReadMutation = useMutation({
    mutationFn: (notificationId: string) => postMarkRead([notificationId]),
    onMutate: async (notificationId) => {
      const now = new Date().toISOString();
      queryClient.setQueryData<InAppNotification[]>(
        RECENT_NOTIFICATIONS_KEY,
        (old = []) =>
          old.map((n) =>
            n.notification_id === notificationId ? { ...n, read_at: now } : n,
          ),
      );
    },
    onError: () => {
      void queryClient.invalidateQueries({
        queryKey: RECENT_NOTIFICATIONS_KEY,
      });
    },
  });

  // Mark all read
  const markAllReadMutation = useMutation({
    mutationFn: () => postMarkRead(),
    onMutate: async () => {
      const now = new Date().toISOString();
      queryClient.setQueryData<InAppNotification[]>(
        RECENT_NOTIFICATIONS_KEY,
        (old = []) => old.map((n) => ({ ...n, read_at: now })),
      );
    },
    onError: () => {
      void queryClient.invalidateQueries({
        queryKey: RECENT_NOTIFICATIONS_KEY,
      });
    },
  });

  const markRead = useCallback(
    async (notificationId: string) => {
      await markReadMutation.mutateAsync(notificationId);
    },
    [markReadMutation],
  );

  const markAllRead = useCallback(async () => {
    await markAllReadMutation.mutateAsync();
  }, [markAllReadMutation]);

  return {
    notifications,
    unreadCount,
    isConnected,
    isBellOpen,
    openBell: () => setIsBellOpen(true),
    closeBell: () => setIsBellOpen(false),
    markRead,
    markAllRead,
  };
}
