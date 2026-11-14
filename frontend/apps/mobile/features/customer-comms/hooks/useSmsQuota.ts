/**
 * useSmsQuota — TanStack Query hook for SMS quota status
 *
 * Location: apps/mobile/features/customer-comms/hooks/useSmsQuota.ts
 *
 * API: GET /api/v1/sms/quota?customer_id={customerId}
 * Query key: ['sms-quota', { customerId }]
 * Cache: staleTime: 60_000; refetchOnWindowFocus: true
 *
 * When customerId provided, backend also checks customer opt-out status.
 * Returns SmsQuotaStatus + derived QuotaVisualState via deriveQuotaState().
 *
 * Design doc Section C.4, D.3, D.5
 */

import { useQuery } from "@tanstack/react-query";
import { deriveQuotaState } from "@pilot/ui";
import type { SmsQuotaStatus, QuotaVisualState } from "@pilot/ui";
import { apiClient } from "@pilot/shared-api";

interface UseSmsQuotaOptions {
  customerId?: string;
  enabled?: boolean;
}

async function fetchSmsQuota(customerId?: string): Promise<SmsQuotaStatus> {
  const params = new URLSearchParams();
  if (customerId) params.set("customer_id", customerId);

  const url = `/api/v1/sms/quota${params.toString() ? `?${params.toString()}` : ""}`;
  const res = await apiClient.get<SmsQuotaStatus>(url);
  return res.data;
}

export function useSmsQuota({
  customerId,
  enabled = true,
}: UseSmsQuotaOptions = {}) {
  const query = useQuery({
    queryKey: ["sms-quota", { customerId }],
    queryFn: () => fetchSmsQuota(customerId),
    staleTime: 60_000,
    refetchOnWindowFocus: true,
    enabled,
  });

  const quota = query.data;
  const quotaState: QuotaVisualState | undefined = quota
    ? deriveQuotaState(quota)
    : undefined;

  const isSendBlocked =
    quotaState?.state === "opted_out" || quotaState?.state === "blocked_hard";

  return {
    quota,
    quotaState,
    isSendBlocked,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  };
}
