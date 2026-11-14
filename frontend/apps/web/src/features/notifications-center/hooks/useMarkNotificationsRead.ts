/**
 * useMarkNotificationsRead — mutation hook
 *
 * Location: apps/web/src/features/notifications-center/hooks/useMarkNotificationsRead.ts
 *
 * POST /api/v1/notifications/in-app/mark-read
 * Body: { notification_ids: string[] }  OR  {} for mark-all
 * onSuccess: invalidate ['notifications-recent']
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

interface MarkReadPayload {
  notification_ids?: string[];
}

export function useMarkNotificationsRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: MarkReadPayload = {}) => {
      const res = await apiClient.post(
        "/api/v1/notifications/in-app/mark-read",
        payload,
      );
      return res.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["notifications-recent"],
      });
    },
  });
}
