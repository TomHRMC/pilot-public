/**
 * useDataExport — TanStack Query hook
 *
 * Location: apps/web/src/features/account-settings/hooks/useDataExport.ts
 *
 * RULE: TanStack Query polling (refetchInterval) while status is pending/processing.
 *       NOT useOptimisticMutation — data export is a purely online async task.
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient, isAxiosError } from "@pilot/shared-api";
import type {
  DataExportCreateResponse,
  DataExportStatusResponse,
  DataExportStatus,
} from "../types";

const EXPORTS_LIST_KEY = ["users", "me", "data-exports"] as const;
const BASE = "/api/v1/users/me/data-exports";

async function requestExport(): Promise<DataExportCreateResponse> {
  try {
    const res = await apiClient.post<DataExportCreateResponse>(BASE);
    return res.data;
  } catch (err) {
    if (isAxiosError(err) && err.response?.status === 429) {
      const retryAfter =
        (err.response.headers as Record<string, string>)["retry-after"] ?? "24";
      throw new Error(
        `You already requested an export recently. You can request another in ${retryAfter}h.`,
      );
    }
    throw err;
  }
}

async function fetchExportStatus(
  exportId: string,
): Promise<DataExportStatusResponse> {
  const res = await apiClient.get<DataExportStatusResponse>(
    `${BASE}/${exportId}`,
  );
  return res.data;
}

async function fetchExportList(): Promise<DataExportStatusResponse[]> {
  const res = await apiClient.get<DataExportStatusResponse[]>(BASE);
  return res.data;
}

const ACTIVE_STATUSES: DataExportStatus[] = ["pending", "processing"];

export function useDataExport() {
  const queryClient = useQueryClient();
  const [activeExportId, setActiveExportId] = useState<string | null>(null);

  // Poll active export while processing
  const { data: activeExportStatus, isLoading: statusLoading } = useQuery({
    queryKey: ["users", "me", "data-exports", activeExportId] as const,
    queryFn: () => fetchExportStatus(activeExportId!),
    enabled: !!activeExportId,
    // RULE: refetchInterval active when status === 'pending' | 'processing'
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && ACTIVE_STATUSES.includes(status) ? 10_000 : false;
    },
    staleTime: 5_000,
  });

  // Recent exports list
  const { data: recentExports = [], isLoading: listLoading } = useQuery({
    queryKey: EXPORTS_LIST_KEY,
    queryFn: fetchExportList,
    staleTime: 60_000,
  });

  // POST new export
  const requestExportMutation = useMutation({
    mutationFn: requestExport,
    onSuccess: (data) => {
      setActiveExportId(data.export_id);
      void queryClient.invalidateQueries({ queryKey: EXPORTS_LIST_KEY });
    },
  });

  const currentStatus: DataExportStatus | "idle" =
    activeExportStatus?.status ?? "idle";

  return {
    activeExportId,
    activeExportStatus,
    currentStatus,
    recentExports,
    isLoading: listLoading || statusLoading,
    isRequesting: requestExportMutation.isPending,
    requestError: requestExportMutation.error,
    requestExport: async () => {
      await requestExportMutation.mutateAsync();
    },
    clearActiveExport: () => setActiveExportId(null),
  };
}
