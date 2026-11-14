/**
 * useQbConnectionStatus — BETA-B4 / STEP 5
 *
 * Location: apps/web/src/features/settings/hooks/useQbConnectionStatus.ts
 *
 * Fetches QuickBooks connection state.
 * GET /api/v1/integrations/quickbooks/status
 * DELETE /api/v1/integrations/quickbooks/disconnect
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface QbConnectionStatus {
  connected: boolean;
  companyName: string | null;
  lastSyncAt: string | null;
  expiresAt: string | null;
}

interface QbStatusRaw {
  connected: boolean;
  company_name: string | null;
  last_sync_at: string | null;
  expires_at: string | null;
}

const QUERY_KEY = ["qb-connection-status"] as const;

export function useQbConnectionStatus() {
  const qc = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: async (): Promise<QbConnectionStatus> => {
      const res = await apiClient.get<QbStatusRaw>(
        "/api/v1/integrations/quickbooks/status",
      );
      return {
        connected: res.data.connected,
        companyName: res.data.company_name,
        lastSyncAt: res.data.last_sync_at,
        expiresAt: res.data.expires_at,
      };
    },
    staleTime: 30_000,
  });

  const disconnectMutation = useMutation({
    mutationFn: async () => {
      await apiClient.delete("/api/v1/integrations/quickbooks/disconnect");
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });

  return {
    status: data ?? null,
    isLoading,
    isError,
    disconnect: async () => {
      await disconnectMutation.mutateAsync();
    },
    isDisconnecting: disconnectMutation.isPending,
  };
}
