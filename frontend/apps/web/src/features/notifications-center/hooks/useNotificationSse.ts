/**
 * useNotificationSse — SSE connection for real-time notification bell updates
 *
 * Location: apps/web/src/features/notifications-center/hooks/useNotificationSse.ts
 *
 * SSE endpoint: GET /api/v1/notifications/sse/notifications?token={JWT}
 * (verified in backend/openapi_schema_map.md)
 *
 * On any new notification event:
 *   1. Increments unread count in notificationBellStore
 *   2. Invalidates ['notifications-recent'] query
 *
 * Rule 3: SSE endpoints require ?token=JWT — uses useSseChannel with getToken prop.
 * Note: getToken is part of useSseChannel options (added BETA-B2).
 */

import { useQueryClient } from "@tanstack/react-query";
import { useSseChannel } from "@pilot/ui";
import { fetchAuthSession } from "aws-amplify/auth";
import { useNotificationBellStore } from "../store/notificationBellStore";

export function useNotificationSse() {
  const queryClient = useQueryClient();
  const incrementUnread = useNotificationBellStore(
    (s: { incrementUnread: () => void }) => s.incrementUnread,
  );

  const getToken = async (): Promise<string> => {
    try {
      const session = await fetchAuthSession();
      return session.tokens?.accessToken?.toString() ?? "";
    } catch {
      return "";
    }
  };

  return useSseChannel({
    path: "/api/v1/notifications/sse/notifications",
    // getToken is in UseSseChannelOptions but the exported type may lag behind source.
    // Cast options to any to pass getToken without type error.
    ...({ getToken } as object),
    fallbackToPollingMs: 60_000,
    pollFn: () => {
      void queryClient.invalidateQueries({
        queryKey: ["notifications-recent"],
      });
    },
    onMessage: (message) => {
      if (
        message.type === "in_app_notification" ||
        (message.data && message.data !== "{}")
      ) {
        incrementUnread();
        void queryClient.invalidateQueries({
          queryKey: ["notifications-recent"],
        });
      }
    },
  } as Parameters<typeof useSseChannel>[0]);
}
