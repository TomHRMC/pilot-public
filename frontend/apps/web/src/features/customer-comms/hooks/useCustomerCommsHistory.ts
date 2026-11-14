/**
 * useCustomerCommsHistory — TanStack Query for customer comms history (web)
 *
 * Location: apps/web/src/features/customer-comms/hooks/useCustomerCommsHistory.ts
 *
 * POST-BETA fix: corrected endpoint path and response shape to match the real
 * backend. Real endpoint: GET /api/v1/customers/{customerId}/communications
 * Real response: CommunicationHistoryResponse { items: CommunicationHistoryItem[] }
 * (not { threads: SmsThread[] } — that shape was never implemented server-side)
 *
 * Query key: ['customer-comms-history', customerId]
 * Cache: staleTime: 30_000
 *
 * Design doc Section C.6, A.2.1
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

// Real backend shape per openapi.json CommunicationHistoryItem
export interface CommunicationHistoryItem {
  communication_id: string;
  template_code: string;
  actual_channel: string;
  channel_override_flag: boolean;
  customer_preferred_channel: string | null;
  rendered_message: string;
  rendered_subject: string | null;
  status: string;
  sent_at: string | null;
  sender_user_id: string;
  job_id: string | null;
}

interface RawCommunicationHistoryResponse {
  customer_id: string;
  total: number;
  page: number;
  page_size: number;
  items: CommunicationHistoryItem[];
}

async function fetchCustomerCommsHistory(
  customerId: string,
): Promise<RawCommunicationHistoryResponse> {
  const res = await apiClient.get<RawCommunicationHistoryResponse>(
    `/api/v1/customers/${customerId}/communications`,
  );
  return res.data;
}

export function useCustomerCommsHistory(customerId: string) {
  const query = useQuery({
    queryKey: ["customer-comms-history", customerId],
    queryFn: () => fetchCustomerCommsHistory(customerId),
    staleTime: 30_000,
    enabled: Boolean(customerId),
  });

  return {
    items: query.data?.items ?? [],
    // Backend does not expose opted-out status on this endpoint; default false
    customerOptedOut: false,
    optedOutAt: null as string | null,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  };
}
