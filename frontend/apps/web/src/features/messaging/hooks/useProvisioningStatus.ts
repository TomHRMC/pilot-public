"use client";

/**
 * useProvisioningStatus — GET /api/v1/tenants/{tenant_id}/messaging/status
 *
 * Location: apps/web/src/features/messaging/hooks/useProvisioningStatus.ts
 *
 * C-B9: Fetches the current 10DLC provisioning state. Polls every 5s when
 * the status is in a pending/async state; stops polling on terminal/interactive
 * states.
 *
 * Returns null (not throws) on 404 — means provisioning not yet started.
 *
 * RULE 2: uses apiClient, never raw fetch().
 * RULE 12: TanStack Query v5 object-form, colocated query key.
 */

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { useAuth } from "@pilot/ui/auth";
import type { components } from "@pilot/shared-types";
import { POLLING_STATUSES, type MessagingStatus } from "../types";

export type ProvisioningStatusResponse =
  components["schemas"]["ProvisioningStatusResponse"];

export const PROVISIONING_STATUS_QUERY_KEY = ["messaging", "status"] as const;

export function useProvisioningStatus() {
  const { user } = useAuth();
  const tenantId = user?.tenantId;
  const queryClient = useQueryClient();

  const query = useQuery<ProvisioningStatusResponse | null>({
    queryKey: PROVISIONING_STATUS_QUERY_KEY,
    queryFn: async () => {
      if (!tenantId) return null;
      try {
        const res = await apiClient.get<ProvisioningStatusResponse>(
          `/api/v1/tenants/${tenantId}/messaging/status`,
        );
        return res.data;
      } catch (err: unknown) {
        // 404 = not started — return null instead of throwing
        if (
          typeof err === "object" &&
          err !== null &&
          "response" in err &&
          (err as { response: { status: number } }).response?.status === 404
        ) {
          return null;
        }
        throw err;
      }
    },
    enabled: !!tenantId,
    retry: false,
    // Poll every 5s when status is pending; stop on terminal/interactive
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return false;
      const status = data.status as MessagingStatus;
      return POLLING_STATUSES.has(status) ? 5000 : false;
    },
  });

  return {
    ...query,
    /** Invalidate the status query (used by mutations in onSettled). */
    invalidate: () =>
      queryClient.invalidateQueries({
        queryKey: PROVISIONING_STATUS_QUERY_KEY,
      }),
  };
}
