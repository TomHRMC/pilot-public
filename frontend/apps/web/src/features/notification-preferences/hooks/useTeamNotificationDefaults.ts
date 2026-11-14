/**
 * useTeamNotificationDefaults — FE-UI-NAV-S1
 *
 * Location: apps/web/src/features/notification-preferences/hooks/useTeamNotificationDefaults.ts
 *
 * TanStack Query hook for tenant-level notification default policies.
 * Endpoint confirmed in openapi_schema_map.md after pnpm sync-api-types:
 *   GET    /api/v1/notifications/tenant-policy
 *   PUT    /api/v1/notifications/tenant-policy/{category_id}/{channel}
 *   DELETE /api/v1/notifications/tenant-policy           (bulk reset)
 *   DELETE /api/v1/notifications/tenant-policy/{id}/{ch} (single cell)
 *
 * Backend companion: BE-UI-NAV-S1 (endpoint exists; response shape confirmed).
 *
 * The shape mirrors useNotificationPreferences to allow reuse of
 * NotificationPreferenceMatrix with the same callback interface.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

// TODO: replace with @pilot/shared-types once BE-UI-NAV-S1 delivers OpenAPI types
export interface TeamNotificationPolicy {
  category_id: string;
  channel: string;
  enabled: boolean;
}

interface TeamNotificationPolicyResponse {
  policies: TeamNotificationPolicy[];
}

interface TeamNotificationResetResponse {
  deleted_count: number;
}

const BASE = "/api/v1/notifications/tenant-policy";
const QUERY_KEY = ["notifications", "tenant-policy"] as const;

export function useTeamNotificationDefaults() {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: QUERY_KEY,
    queryFn: async () => {
      const resp = await apiClient.get<TeamNotificationPolicyResponse>(BASE);
      return resp.data.policies ?? [];
    },
    retry: false,
  });

  // PUT single cell (set tenant default for a category+channel)
  const cellChangeMutation = useMutation({
    mutationFn: async ({
      categoryId,
      channel,
      enabled,
    }: {
      categoryId: string;
      channel: string;
      enabled: boolean;
    }) => {
      const resp = await apiClient.put(`${BASE}/${categoryId}/${channel}`, {
        enabled,
      });
      return resp.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
    retry: false,
  });

  // DELETE single cell (revert single tenant policy to system default)
  const cellRevertMutation = useMutation({
    mutationFn: async ({
      categoryId,
      channel,
    }: {
      categoryId: string;
      channel: string;
    }) => {
      const resp = await apiClient.delete(`${BASE}/${categoryId}/${channel}`);
      return resp.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
    retry: false,
  });

  // DELETE all tenant policies (bulk reset to system defaults)
  const resetMutation = useMutation({
    mutationFn: async () => {
      const resp = await apiClient.delete<TeamNotificationResetResponse>(BASE);
      return resp.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
    retry: false,
  });

  const isPending =
    cellChangeMutation.isPending ||
    cellRevertMutation.isPending ||
    resetMutation.isPending;

  return {
    policies: query.data ?? [],
    isLoading: query.isLoading,
    error: query.error,
    isPending,
    onCellChange: async (
      categoryId: string,
      channel: string,
      enabled: boolean,
    ) => {
      await cellChangeMutation.mutateAsync({ categoryId, channel, enabled });
    },
    onCellRevert: async (categoryId: string, channel: string) => {
      await cellRevertMutation.mutateAsync({ categoryId, channel });
    },
    reset: resetMutation.mutate,
    isResetting: resetMutation.isPending,
  };
}
