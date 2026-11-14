/**
 * useCreateRecurrenceRule — POST /api/v1/job-recurrence-rules/
 *
 * Location: apps/web/src/features/jobs/hooks/useCreateRecurrenceRule.ts
 *
 * FE-B31: Creates a recurrence rule. Backend immediately creates the first
 * job occurrence and returns first_job_id in the response.
 *
 * RULE: Uses apiClient (never raw fetch).
 * RULE: onSuccess invalidates ["recurrence-rules"] and ["jobs"] (first job was created).
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface RecurrenceRuleCreatePayload {
  customer_id: string;
  site_id: string;
  pattern: "daily" | "weekly" | "monthly" | "annually";
  interval_count?: number; // default 1
  starts_on: string; // ISO date string "YYYY-MM-DD"
  ends_on?: string | null;
  max_occurrences?: number | null;
  estimated_duration_minutes?: number | null;
  default_tech_user_id?: string | null;
  notes_template?: string | null;
}

export interface RecurrenceRuleCreateResponse {
  id: string;
  tenant_id: string;
  customer_id: string;
  site_id: string;
  pattern: string;
  interval_count: number;
  starts_on: string;
  ends_on: string | null;
  max_occurrences: number | null;
  occurrences_created: number;
  next_job_at: string | null;
  is_active: boolean;
  first_job_id: string | null;
}

export const RECURRENCE_RULES_QUERY_KEY = ["recurrence-rules"] as const;

export function useCreateRecurrenceRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (
      payload: RecurrenceRuleCreatePayload,
    ): Promise<RecurrenceRuleCreateResponse> => {
      const response = await apiClient.post(
        "/api/v1/job-recurrence-rules/",
        payload,
      );
      return response.data as RecurrenceRuleCreateResponse;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: RECURRENCE_RULES_QUERY_KEY,
      });
      void queryClient.invalidateQueries({ queryKey: ["jobs"] }); // first job was created
    },
    retry: false,
  });
}
