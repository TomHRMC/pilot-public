/**
 * useBillableItems — GET /api/v1/jobs/{job_id}/billable-items
 *
 * Location: apps/web/src/features/invoices/hooks/useBillableItems.ts
 *
 * FE-B29: Fetches billable time entries + expenses from a job for invoice pre-fill.
 * Enabled only when jobId is set. staleTime: 60s.
 *
 * Endpoint verified in openapi_schema_map.md (FE-B29 pre-work).
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface BillableTimeEntry {
  id: string;
  user_id: string;
  tech_name: string | null;
  started_at: string;
  ended_at: string | null;
  hours: string | null; // Decimal as string from backend
  hourly_rate_cents: number;
  total_cost_cents: number;
  notes: string | null;
  is_already_invoiced: boolean;
}

export interface BillableExpense {
  id: string;
  description: string;
  cost_cents: number;
  billable_cents: number;
  is_billable: boolean;
  is_already_invoiced: boolean;
  incurred_at: string;
}

export interface BillableItemsResponse {
  job_id: string;
  job_number: string | null;
  customer_name: string | null;
  time_entries: BillableTimeEntry[];
  expenses: BillableExpense[];
}

export const BILLABLE_ITEMS_QUERY_KEY = (jobId: string) =>
  ["billable-items", jobId] as const;

export function useBillableItems(jobId: string | null | undefined) {
  return useQuery({
    queryKey: BILLABLE_ITEMS_QUERY_KEY(jobId ?? ""),
    queryFn: async (): Promise<BillableItemsResponse> => {
      const res = await apiClient.get(`/api/v1/jobs/${jobId}/billable-items`);
      return res.data as BillableItemsResponse;
    },
    enabled: !!jobId,
    staleTime: 60_000,
  });
}
