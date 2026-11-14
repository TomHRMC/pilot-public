/**
 * useIntegrationsDashboard — BETA-B4 / STEP 6
 *
 * Location: apps/web/src/features/settings/hooks/useIntegrationsDashboard.ts
 *
 * Fan-out fetches for all integration statuses + sync dashboard summary.
 * GET /api/v1/integrations/sync-dashboard/
 * GET /api/v1/integrations/quickbooks/status
 * GET /api/v1/integrations/calendar/status
 * GET /api/v1/tenants/{tenant_id}/phone-numbers/ (SMS provisioning state)
 */

import { useQueries } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { useAuth } from "@pilot/ui/auth";

export interface IntegrationStatus {
  connected: boolean;
  displayName: string;
  lastSyncAt: string | null;
  settingsHref: string;
}

export interface IntegrationsDashboard {
  quickbooks: IntegrationStatus;
  calendar: IntegrationStatus;
  sms: IntegrationStatus;
  syncDashboard: {
    pendingCount: number;
    errorCount: number;
  } | null;
}

export interface UseIntegrationsDashboardReturn {
  dashboard: IntegrationsDashboard | null;
  isLoading: boolean;
  isError: boolean;
}

export function useIntegrationsDashboard(): UseIntegrationsDashboardReturn {
  const { user } = useAuth();
  const tenantId = user?.tenantId ?? "";

  const results = useQueries({
    queries: [
      {
        queryKey: ["integrations", "sync-dashboard"],
        queryFn: async () => {
          const res = await apiClient.get<{
            pending_count?: number;
            error_count?: number;
          }>("/api/v1/integrations/sync-dashboard/");
          return res.data;
        },
        staleTime: 30_000,
      },
      {
        queryKey: ["integrations", "qb-status"],
        queryFn: async () => {
          const res = await apiClient.get<{
            connected: boolean;
            last_sync_at: string | null;
          }>("/api/v1/integrations/quickbooks/status");
          return res.data;
        },
        staleTime: 30_000,
      },
      {
        queryKey: ["integrations", "calendar-status"],
        queryFn: async () => {
          const res = await apiClient.get<{
            connected: boolean;
            last_sync_at: string | null;
          }>("/api/v1/integrations/calendar/status");
          return res.data;
        },
        staleTime: 30_000,
      },
      {
        queryKey: ["integrations", "phone-numbers", tenantId],
        queryFn: async () => {
          const res = await apiClient.get<unknown[]>(
            `/api/v1/tenants/${tenantId}/phone-numbers/`,
          );
          return res.data;
        },
        enabled: Boolean(tenantId),
        staleTime: 60_000,
      },
    ],
  });

  const [syncDashResult, qbResult, calResult, phoneResult] = results;

  const isLoading = results.some((r) => r.isLoading);
  const isError = results.some((r) => r.isError);

  if (
    isLoading ||
    (!syncDashResult.data && !qbResult.data && !calResult.data)
  ) {
    return { dashboard: null, isLoading, isError };
  }

  const dashboard: IntegrationsDashboard = {
    quickbooks: {
      connected: qbResult.data?.connected ?? false,
      displayName: "QuickBooks",
      lastSyncAt: qbResult.data?.last_sync_at ?? null,
      settingsHref: "/settings/integrations/quickbooks",
    },
    calendar: {
      connected: calResult.data?.connected ?? false,
      displayName: "Calendar",
      lastSyncAt: calResult.data?.last_sync_at ?? null,
      settingsHref: "/settings/integrations/calendar",
    },
    sms: {
      connected: Array.isArray(phoneResult.data) && phoneResult.data.length > 0,
      displayName: "SMS",
      lastSyncAt: null,
      settingsHref: "/settings/communications/sms",
    },
    syncDashboard: syncDashResult.data
      ? {
          pendingCount: syncDashResult.data.pending_count ?? 0,
          errorCount: syncDashResult.data.error_count ?? 0,
        }
      : null,
  };

  return { dashboard, isLoading: false, isError };
}
