/**
 * useUpdateRecurrenceRule — PATCH /api/v1/job-recurrence-rules/{rule_id}
 *
 * Location: apps/web/src/features/jobs/hooks/useUpdateRecurrenceRule.ts
 *
 * FE-B31: Used for pause/resume (is_active toggle) and other partial updates.
 *
 * RULE: Uses apiClient (never raw fetch).
 * RULE: onSuccess invalidates ["recurrence-rules"] query family.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { RECURRENCE_RULES_QUERY_KEY } from "./useCreateRecurrenceRule";
import type { RecurrenceRuleListItem } from "./useListRecurrenceRules";

export interface RecurrenceRuleUpdatePayload {
  is_active?: boolean;
  ends_on?: string | null;
  max_occurrences?: number | null;
  default_tech_user_id?: string | null;
  notes_template?: string | null;
  estimated_duration_minutes?: number | null;
}

export function useUpdateRecurrenceRule(ruleId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (
      payload: RecurrenceRuleUpdatePayload,
    ): Promise<RecurrenceRuleListItem> => {
      const response = await apiClient.patch(
        `/api/v1/job-recurrence-rules/${ruleId}`,
        payload,
      );
      return response.data as RecurrenceRuleListItem;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: RECURRENCE_RULES_QUERY_KEY,
      });
    },
    retry: false,
  });
}
