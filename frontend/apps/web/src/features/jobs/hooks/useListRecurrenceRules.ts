/**
 * useListRecurrenceRules — GET /api/v1/job-recurrence-rules/
 *
 * Location: apps/web/src/features/jobs/hooks/useListRecurrenceRules.ts
 *
 * FE-B31: Fetches the list of recurrence rules for the tenant.
 *
 * RULE: Uses apiClient (never raw fetch).
 * Query key: ['recurrence-rules', { isActive }]
 * staleTime: 30_000
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { RECURRENCE_RULES_QUERY_KEY } from "./useCreateRecurrenceRule";

export interface RecurrenceRuleListItem {
  id: string;
  tenant_id: string;
  customer_id: string;
  site_id: string;
  pattern: "daily" | "weekly" | "monthly" | "annually";
  interval_count: number;
  starts_on: string;
  ends_on: string | null;
  max_occurrences: number | null;
  occurrences_created: number;
  next_job_at: string | null;
  is_active: boolean;
  customer_name?: string | null;
  site_address?: string | null;
  default_tech_user_id?: string | null;
  default_tech_display_name?: string | null;
}

export interface RecurrenceRuleListResponse {
  items: RecurrenceRuleListItem[];
  total: number;
}

export function useListRecurrenceRules(isActive?: boolean) {
  return useQuery({
    queryKey: [...RECURRENCE_RULES_QUERY_KEY, { isActive }] as const,
    queryFn: async (): Promise<RecurrenceRuleListResponse> => {
      const params = isActive !== undefined ? { is_active: isActive } : {};
      const response = await apiClient.get("/api/v1/job-recurrence-rules/", {
        params,
      });
      return response.data as RecurrenceRuleListResponse;
    },
    staleTime: 30_000,
    retry: false,
  });
}
