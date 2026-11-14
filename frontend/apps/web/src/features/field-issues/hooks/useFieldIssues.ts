/**
 * useFieldIssues — TanStack Query list hook for field issues
 *
 * Location: apps/web/src/features/field-issues/hooks/useFieldIssues.ts
 *
 * API: GET /api/v1/owner/mobile-sync-escalations
 * Params: escalation_status, operation_type, sort, cursor, limit
 * Response: EscalationListResponse { items, next_cursor, total_pending }
 */

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import type {
  FieldIssuesParams,
  FieldIssuesResponse,
  FieldIssueQueueItem,
} from "../types";

export const FIELD_ISSUES_QUERY_KEY = (params: FieldIssuesParams) =>
  ["field-issues", params] as const;

async function fetchFieldIssues(
  params: FieldIssuesParams,
): Promise<FieldIssuesResponse> {
  const query = new URLSearchParams();
  // API uses 'escalation_status', not 'status'
  if (params.status) query.set("escalation_status", params.status);
  if (params.operation_type) query.set("operation_type", params.operation_type);
  if (params.cursor) query.set("cursor", params.cursor);
  if (params.limit) query.set("limit", String(params.limit));

  const res = await apiClient.get<{
    items: Record<string, unknown>[];
    next_cursor: string | null;
    total_pending: number;
  }>(`/api/v1/owner/mobile-sync-escalations?${query.toString()}`);

  const data = res.data;

  // Map backend operation_type values to frontend FieldIssueOperationType
  const OPERATION_TYPE_MAP: Record<
    string,
    FieldIssueQueueItem["operationType"]
  > = {
    time_entry: "time_entry",
    expense: "expense",
    photo: "photo",
    status_change: "status_change",
    update_job_status: "status_change", // backend alias
    loto: "loto",
  };

  // Normalize EscalationListItem → FieldIssueQueueItem
  const issues = data.items.map((raw): FieldIssueQueueItem => {
    const backendOpType = raw.operation_type as string | null;
    const operationType: FieldIssueQueueItem["operationType"] =
      (backendOpType ? OPERATION_TYPE_MAP[backendOpType] : undefined) ??
      "time_entry";
    return {
      id: raw.id as string,
      status: raw.status as FieldIssueQueueItem["status"],
      operationType,
      techId: raw.originating_user_id as string,
      techName: (raw.originating_user_name as string | null) ?? "",
      capturedAt: raw.escalated_at as string,
      escalatedAt: raw.escalated_at as string,
      explainerSummary: raw.escalation_reason_explainer as string,
      conflictType:
        (raw.conflict_severity as FieldIssueQueueItem["conflictType"]) ??
        "modified_modified",
    };
  });

  return {
    issues,
    next_cursor: data.next_cursor,
    total_pending: data.total_pending,
  };
}

export function useFieldIssues(params: FieldIssuesParams = {}) {
  return useQuery({
    queryKey: FIELD_ISSUES_QUERY_KEY(params),
    queryFn: () => fetchFieldIssues(params),
    staleTime: 30_000, // 30s
    refetchOnWindowFocus: true,
  });
}
